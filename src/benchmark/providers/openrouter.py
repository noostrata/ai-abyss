"""Provider-ready OpenRouter adapter whose live boundary is closed by default."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.benchmark.enums import ExecutionMode
from src.benchmark.models import AGENT_ACTION_ADAPTER, ProviderUsage
from src.benchmark.providers.base import (
    PaidExecutionRefused,
    ProviderError,
    ProviderMalformedResponse,
    ProviderRateLimit,
    ProviderRequest,
    ProviderResponse,
    ProviderTimeout,
)


class LiveProviderControls(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_mode: ExecutionMode = ExecutionMode.MOCK
    allow_paid: bool = False
    paid_gate_approved: bool = False
    authorization_id: str | None = None
    model_id: str = Field(min_length=1)
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


def _environment_credential() -> str:
    value = os.environ.get("OPENROUTER_API_KEY", "")
    if not value:
        raise PaidExecutionRefused("authorised live path has no local credential")
    return value


class OpenRouterProvider:
    name = "openrouter"
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        controls: LiveProviderControls,
        client: httpx.AsyncClient,
        credential_loader: Callable[[], str] = _environment_credential,
    ) -> None:
        self.controls = controls
        self.model_id = controls.model_id
        self.client = client
        self.credential_loader = credential_loader
        self.closed = False

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        self._guard_live_boundary()
        credential = self.credential_loader()
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {
                    "role": "user",
                    "content": request.task_prompt
                    + "\n\nObservation JSON:\n"
                    + request.observation.model_dump_json(),
                },
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.controls.max_output_tokens,
            "reasoning": {"max_tokens": self.controls.max_reasoning_tokens},
            "temperature": request.sampling.temperature,
            "top_p": request.sampling.top_p,
        }
        if request.sampling.seed is not None:
            payload["seed"] = request.sampling.seed
        try:
            response = await self.client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {credential}"},
                json=payload,
            )
        except httpx.TimeoutException as error:
            raise ProviderTimeout("OpenRouter request timed out") from error
        except httpx.HTTPError as error:
            raise ProviderError("OpenRouter transport error") from error
        if response.status_code == 429:
            raise ProviderRateLimit("OpenRouter rate limit")
        if response.status_code >= 400:
            raise ProviderError(f"OpenRouter HTTP {response.status_code}")
        try:
            body = response.json()
            raw_content = body["choices"][0]["message"]["content"]
            action = AGENT_ACTION_ADAPTER.validate_python(json.loads(raw_content))
            native = body["usage"]
            details = native.get("completion_tokens_details") or {}
            prompt_details = native.get("prompt_tokens_details") or {}
            usage = ProviderUsage(
                prompt_tokens=native.get("prompt_tokens", 0),
                completion_tokens=native.get("completion_tokens", 0),
                reasoning_tokens=details.get("reasoning_tokens", 0),
                cache_read_tokens=prompt_details.get("cached_tokens", 0),
                cache_write_tokens=prompt_details.get("cache_write_tokens", 0),
                total_tokens=native.get("total_tokens", 0),
                provider_reported_cost_usd=native.get("cost"),
            )
            request_id = str(body.get("id") or response.headers.get("x-request-id") or "unknown")
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderMalformedResponse("malformed OpenRouter response") from error
        return ProviderResponse(
            request_id=request_id,
            action=action,
            usage=usage,
            raw_content=raw_content,
        )

    def _guard_live_boundary(self) -> None:
        controls = self.controls
        requirements = (
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

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            await self.client.aclose()
