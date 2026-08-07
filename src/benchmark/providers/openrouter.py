"""Strict OpenRouter-compatible adapter with a closed hosted boundary."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.benchmark.enums import ExecutionMode
from src.benchmark.models import AGENT_ACTION_ADAPTER, ProviderUsage, canonical_json
from src.benchmark.providers.base import (
    PaidExecutionRefused,
    ProviderAttemptObserver,
    ProviderError,
    ProviderIdentityMismatch,
    ProviderMalformedResponse,
    ProviderRateLimit,
    ProviderRejected,
    ProviderRequest,
    ProviderResponse,
    ProviderTimeout,
)

HOSTED_OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class LiveProviderControls(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_mode: ExecutionMode = ExecutionMode.MOCK
    transport_mode: Literal["hosted", "local_fake"] = "hosted"
    allow_paid: bool = False
    paid_gate_approved: bool = False
    authorization_id: str | None = None
    model_id: str = Field(min_length=1)
    provider_route: str = Field(min_length=1)
    price_snapshot_id: str | None = None
    trial_cost_cap_usd: float | None = Field(default=None, gt=0)
    batch_cost_cap_usd: float | None = Field(default=None, gt=0)
    provider_spending_limit_usd: float | None = Field(default=None, gt=0)
    price_snapshot_source: str | None = None
    dedicated_credential_confirmed: bool = False
    worst_case_reservation_id: str | None = None
    dual_layer_egress_evidence_id: str | None = None
    kill_switch_id: str | None = None
    artifact_policy_id: str | None = None
    retry_policy: Literal["no_retry"] = "no_retry"
    max_output_tokens: int = Field(default=512, ge=1)
    max_reasoning_tokens: int = Field(default=512, ge=0)


class OpenRouterProvider:
    name = "openrouter"
    endpoint = HOSTED_OPENROUTER_ENDPOINT

    def __init__(
        self,
        controls: LiveProviderControls,
        client: httpx.AsyncClient,
        credential_loader: Callable[[], str] | None = None,
        *,
        endpoint: str = HOSTED_OPENROUTER_ENDPOINT,
    ) -> None:
        self.controls = controls
        self.model_id = controls.model_id
        self.provider_route = controls.provider_route
        self.execution_boundary = (
            "local_fake" if controls.transport_mode == "local_fake" else "hosted"
        )
        self.client = client
        self.credential_loader = credential_loader
        self.endpoint = endpoint
        self.closed = False

    async def complete(
        self,
        request: ProviderRequest,
        attempt_observer: ProviderAttemptObserver | None = None,
    ) -> ProviderResponse:
        credential = self._guard_execution_boundary()
        payload = self.request_envelope(request)
        try:
            if attempt_observer is not None:
                await attempt_observer("sent")
            response = await self.client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {credential}",
                    "X-OpenRouter-Metadata": "enabled",
                },
                json=payload,
            )
        except httpx.TimeoutException as error:
            raise ProviderTimeout("OpenRouter-compatible request timed out") from error
        except httpx.HTTPError as error:
            raise ProviderError("OpenRouter-compatible transport error") from error
        if attempt_observer is not None:
            await attempt_observer("acknowledged")
        if response.status_code == 429:
            raise ProviderRateLimit("OpenRouter-compatible rate limit")
        if 400 <= response.status_code < 500:
            raise ProviderRejected(
                f"OpenRouter-compatible HTTP {response.status_code} rejected before inference"
            )
        if response.status_code >= 400:
            raise ProviderError(f"OpenRouter-compatible HTTP {response.status_code}")
        try:
            body = response.json()
            raw_content = body["choices"][0]["message"]["content"]
            if not isinstance(raw_content, str):
                raise TypeError("message content is not a string")
            action = AGENT_ACTION_ADAPTER.validate_python(json.loads(raw_content))
            native = body["usage"]
            if not isinstance(native, dict):
                raise TypeError("usage is not an object")
            details = native.get("completion_tokens_details") or {}
            prompt_details = native.get("prompt_tokens_details") or {}
            usage = ProviderUsage(
                prompt_tokens=native["prompt_tokens"],
                completion_tokens=native["completion_tokens"],
                reasoning_tokens=details.get("reasoning_tokens", 0),
                cache_read_tokens=prompt_details.get("cached_tokens", 0),
                cache_write_tokens=prompt_details.get("cache_write_tokens", 0),
                total_tokens=native["total_tokens"],
                provider_reported_cost_usd=native.get("cost"),
            )
            request_id = str(
                body.get("id") or response.headers.get("x-request-id") or "unknown"
            )
            actual_model = str(body["model"])
            metadata = body.get("openrouter_metadata") or {}
            actual_route = str(
                metadata.get("provider_name")
                or body.get("provider")
                or response.headers.get("x-provider-name")
                or ""
            )
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderMalformedResponse(
                "malformed OpenRouter-compatible response"
            ) from error
        if actual_model != self.model_id or actual_route != self.provider_route:
            raise ProviderIdentityMismatch(
                "returned model or provider route does not match the manifest"
            )
        return ProviderResponse(
            request_id=request_id,
            action=action,
            usage=usage,
            raw_content=raw_content,
            actual_model_id=actual_model,
            actual_provider_route=actual_route,
            system_fingerprint=body.get("system_fingerprint"),
            service_tier=body.get("service_tier"),
            routing_metadata=metadata,
        )

    def request_envelope(self, request: ProviderRequest) -> dict:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.task_prompt},
        ]
        if request.truncated_turns:
            messages.append(
                {
                    "role": "user",
                    "content": canonical_json(
                        {
                            "trajectory_notice": {
                                "policy": request.trajectory_policy_version,
                                "truncated_turns": request.truncated_turns,
                            }
                        }
                    ),
                }
            )
        for turn in request.trajectory:
            messages.append(
                {
                    "role": "user",
                    "content": canonical_json(
                        {
                            "observation": turn.observation.model_dump(mode="json"),
                        }
                    ),
                }
            )
            if turn.action is not None:
                messages.append(
                    {
                        "role": "assistant",
                        "content": canonical_json(turn.action),
                    }
                )
        payload: dict = {
            "model": self.model_id,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "benchmark_agent_action",
                    "strict": True,
                    "schema": request.action_schema,
                },
            },
            "provider": {
                "order": [self.provider_route],
                "only": [self.provider_route],
                "allow_fallbacks": False,
                "require_parameters": True,
                "data_collection": "deny",
            },
            "max_completion_tokens": request.max_output_tokens,
            "reasoning": {"max_tokens": request.max_reasoning_tokens},
            "temperature": request.sampling.temperature,
            "top_p": request.sampling.top_p,
            "stream": False,
        }
        if request.sampling.seed is not None:
            payload["seed"] = request.sampling.seed
        return payload

    def _guard_execution_boundary(self) -> str:
        controls = self.controls
        if controls.transport_mode == "local_fake":
            parts = urlsplit(self.endpoint)
            if (
                controls.execution_mode is not ExecutionMode.MOCK
                or controls.allow_paid
                or parts.scheme != "http"
                or parts.hostname not in {"127.0.0.1", "localhost"}
                or parts.port is None
            ):
                raise PaidExecutionRefused("local fake-provider boundary is closed")
            return "local-fake-no-secret"
        requirements = (
            self.endpoint == HOSTED_OPENROUTER_ENDPOINT,
            controls.execution_mode is ExecutionMode.LIVE,
            controls.allow_paid,
            controls.paid_gate_approved,
            bool(controls.authorization_id),
            bool(controls.price_snapshot_id),
            controls.trial_cost_cap_usd is not None,
            controls.batch_cost_cap_usd is not None,
            controls.provider_spending_limit_usd is not None,
            bool(controls.price_snapshot_source),
            controls.dedicated_credential_confirmed,
            bool(controls.worst_case_reservation_id),
            bool(controls.dual_layer_egress_evidence_id),
            bool(controls.kill_switch_id),
            bool(controls.artifact_policy_id),
            controls.model_id not in {"mock", "auto", "openrouter/auto"},
        )
        if not all(requirements):
            raise PaidExecutionRefused("live provider gate is closed")
        if self.credential_loader is None:
            raise PaidExecutionRefused("authorised live path has no injected credential")
        return self.credential_loader()

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            await self.client.aclose()
