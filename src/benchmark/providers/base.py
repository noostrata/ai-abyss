"""Narrow provider protocol shared by mock and live-disabled adapters."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from src.benchmark.models import AgentAction, ProviderUsage, SamplingConfig
from src.benchmark.scaffold import Observation


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system_prompt: str
    task_prompt: str
    observation: Observation
    action_schema: dict
    max_output_tokens: int = Field(ge=1)
    max_reasoning_tokens: int = Field(ge=0)
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    action: AgentAction
    usage: ProviderUsage
    raw_content: str


class ProviderError(RuntimeError):
    code = "provider_error"


class ProviderTimeout(ProviderError):
    code = "timeout"


class ProviderRateLimit(ProviderError):
    code = "rate_limit"


class ProviderMalformedResponse(ProviderError):
    code = "malformed_response"


class ProviderRefused(ProviderError):
    code = "refused"


class PaidExecutionRefused(ProviderError):
    code = "paid_execution_refused"


class Provider(Protocol):
    name: str
    model_id: str

    async def complete(self, request: ProviderRequest) -> ProviderResponse: ...

    async def close(self) -> None: ...
