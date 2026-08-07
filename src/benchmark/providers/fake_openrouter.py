"""Local OpenRouter-compatible server used to qualify the complete HTTP adapter."""

from __future__ import annotations

import asyncio
import json
import secrets
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.benchmark.enums import MockProfile
from src.benchmark.models import AGENT_ACTION_ADAPTER, ProviderUsage, canonical_json
from src.benchmark.providers.base import ProviderTurn
from src.benchmark.providers.mock import choose_mock_action
from src.benchmark.scaffold import Observation

FakeScenario = Literal[
    "valid",
    "malformed_json",
    "schema_invalid",
    "delayed",
    "provider_error",
    "rejected",
    "rate_limited",
    "disconnect_before_receipt",
    "disconnect_after_receipt",
    "missing_usage",
    "missing_cost",
    "reasoning_tokens",
    "wrong_model",
    "wrong_provider",
]


def create_fake_openrouter_app(
    profile: MockProfile,
    *,
    model_id: str = "fake/exact-model-v1",
    provider_route: str = "FakeLocal",
    scenario: FakeScenario = "valid",
    delay_seconds: float = 0.1,
) -> FastAPI:
    """Create an isolated fake server with a deterministic scenario and receipt log."""

    app = FastAPI()
    app.state.received_requests = []

    @app.post("/api/v1/chat/completions")
    async def chat_completion(request: Request):
        body = await request.json()
        app.state.received_requests.append(body)
        _validate_request(body, model_id, provider_route)
        if scenario == "provider_error":
            raise HTTPException(status_code=503, detail="synthetic provider failure")
        if scenario == "rejected":
            raise HTTPException(status_code=400, detail="synthetic rejected request")
        if scenario == "rate_limited":
            raise HTTPException(status_code=429, detail="synthetic rate limit")
        if scenario == "delayed":
            await asyncio.sleep(delay_seconds)
        turns = _trajectory_from_messages(body["messages"])
        action = choose_mock_action(profile, turns)
        raw_content = canonical_json(action)
        if scenario == "malformed_json":
            raw_content = "{not-json"
        elif scenario == "schema_invalid":
            raw_content = canonical_json({"action": "unknown"})
        prompt_tokens = max(1, len(canonical_json(body).encode()) // 4)
        completion_tokens = max(1, len(raw_content.encode()) // 4)
        response_model = "fake/unexpected-model" if scenario == "wrong_model" else model_id
        response_route = "UnexpectedRoute" if scenario == "wrong_provider" else provider_route
        response_body: dict = {
            "id": f"fake-request-{secrets.token_hex(6)}",
            "model": response_model,
            "provider": response_route,
            "system_fingerprint": "fake-openrouter-v1",
            "service_tier": "local",
            "openrouter_metadata": {"provider_name": response_route},
            "choices": [{"message": {"role": "assistant", "content": raw_content}}],
        }
        if scenario != "missing_usage":
            reasoning_tokens = 2 if scenario == "reasoning_tokens" else 0
            usage = ProviderUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                provider_reported_cost_usd=0.0,
            )
            response_body["usage"] = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "completion_tokens_details": {
                    "reasoning_tokens": usage.reasoning_tokens,
                },
                "prompt_tokens_details": {
                    "cached_tokens": 0,
                    "cache_write_tokens": 0,
                },
            }
            if scenario != "missing_cost":
                response_body["usage"]["cost"] = 0.0
        return JSONResponse(response_body)

    return app


class FakeOpenRouterTransport(httpx.AsyncBaseTransport):
    """ASGI transport with deterministic disconnect boundaries."""

    def __init__(self, app: FastAPI, scenario: FakeScenario) -> None:
        self.inner = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        self.scenario = scenario

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self.scenario == "disconnect_before_receipt":
            raise httpx.ConnectError("synthetic disconnect before receipt", request=request)
        response = await self.inner.handle_async_request(request)
        if self.scenario == "disconnect_after_receipt":
            await response.aclose()
            raise httpx.ReadError("synthetic disconnect after receipt", request=request)
        return response

    async def aclose(self) -> None:
        await self.inner.aclose()


def _validate_request(body: dict, model_id: str, provider_route: str) -> None:
    if body.get("model") != model_id:
        raise HTTPException(status_code=422, detail="unexpected model")
    provider = body.get("provider")
    expected_provider = {
        "order": [provider_route],
        "only": [provider_route],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
    }
    if provider != expected_provider:
        raise HTTPException(status_code=422, detail="routing is not exact")
    response_format = body.get("response_format") or {}
    json_schema = response_format.get("json_schema") or {}
    if (
        response_format.get("type") != "json_schema"
        or json_schema.get("strict") is not True
        or json_schema.get("schema") != AGENT_ACTION_ADAPTER.json_schema()
    ):
        raise HTTPException(status_code=422, detail="action schema is not strict and exact")
    if "max_tokens" in body or not isinstance(body.get("max_completion_tokens"), int):
        raise HTTPException(status_code=422, detail="output bound is absent or deprecated")
    if body.get("stream") is not False:
        raise HTTPException(status_code=422, detail="streaming must be disabled")


def _trajectory_from_messages(messages: list[dict]) -> list[ProviderTurn]:
    if len(messages) < 3:
        raise HTTPException(status_code=422, detail="trajectory messages are absent")
    if messages[0].get("role") != "system" or messages[1].get("role") != "user":
        raise HTTPException(status_code=422, detail="prompt roles are invalid")
    turns: list[ProviderTurn] = []
    cursor = 2
    if cursor < len(messages):
        candidate = _json_content(messages[cursor])
        if "trajectory_notice" in candidate:
            cursor += 1
    while cursor < len(messages):
        message = messages[cursor]
        content = _json_content(message)
        if message.get("role") != "user" or "observation" not in content:
            raise HTTPException(status_code=422, detail="observation message is invalid")
        observation = Observation.model_validate(content["observation"])
        cursor += 1
        action = None
        if cursor < len(messages) and messages[cursor].get("role") == "assistant":
            action = AGENT_ACTION_ADAPTER.validate_python(_json_content(messages[cursor]))
            cursor += 1
        turns.append(ProviderTurn(observation=observation, action=action))
    if not turns or turns[-1].action is not None:
        raise HTTPException(status_code=422, detail="current observation is absent")
    if any(turn.action is None for turn in turns[:-1]):
        raise HTTPException(status_code=422, detail="trajectory alternation is invalid")
    return turns


def _json_content(message: dict) -> dict:
    try:
        value = json.loads(message["content"])
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=422, detail="message content is not JSON") from error
    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail="message JSON is not an object")
    return value
