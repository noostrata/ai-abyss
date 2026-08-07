"""Versioned provider protocol shared by every benchmark execution path."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.benchmark.enums import MockProfile
from src.benchmark.models import AgentAction, ProviderUsage, SamplingConfig, TrialManifest
from src.benchmark.scaffold import Observation

TRAJECTORY_POLICY_VERSION = "trajectory-v1"
MAX_TRAJECTORY_TURNS = 16


class ProviderTurn(BaseModel):
    """One model-visible observation and the action selected from it, if any."""

    model_config = ConfigDict(extra="forbid")
    observation: Observation
    action: AgentAction | None = None


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system_prompt: str
    task_prompt: str
    trajectory_policy_version: Literal[TRAJECTORY_POLICY_VERSION] = (
        TRAJECTORY_POLICY_VERSION
    )
    trajectory: list[ProviderTurn] = Field(min_length=1, max_length=MAX_TRAJECTORY_TURNS)
    truncated_turns: int = Field(default=0, ge=0)
    action_schema: dict
    max_output_tokens: int = Field(ge=1)
    max_reasoning_tokens: int = Field(ge=0)
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)

    @model_validator(mode="after")
    def validate_trajectory(self) -> ProviderRequest:
        if self.trajectory[-1].action is not None:
            raise ValueError("the current trajectory turn must not contain an action")
        if any(turn.action is None for turn in self.trajectory[:-1]):
            raise ValueError("only the current trajectory turn may omit its action")
        return self

    @property
    def observation(self) -> Observation:
        """The observation on which the provider must act."""

        return self.trajectory[-1].observation


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    action: AgentAction
    usage: ProviderUsage
    raw_content: str
    actual_model_id: str
    actual_provider_route: str
    system_fingerprint: str | None = None
    service_tier: str | None = None
    routing_metadata: dict = Field(default_factory=dict)


class ProviderIdentity(BaseModel):
    """Expected identity pinned into the manifest before provider construction."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    model_id: str = Field(min_length=1, max_length=256)
    provider_route: str = Field(min_length=1, max_length=256)
    execution_boundary: Literal["local_mock", "local_fake", "hosted_authorized"]


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


class ProviderRejected(ProviderError):
    """The provider acknowledged that it rejected the call before inference."""

    code = "rejected_before_inference"


class ProviderIdentityMismatch(ProviderError):
    code = "identity_mismatch"


class PaidExecutionRefused(ProviderError):
    code = "paid_execution_refused"


class Provider(Protocol):
    name: str
    model_id: str
    provider_route: str
    execution_boundary: str

    def request_envelope(self, request: ProviderRequest) -> dict: ...

    async def complete(
        self,
        request: ProviderRequest,
        attempt_observer: ProviderAttemptObserver | None = None,
    ) -> ProviderResponse: ...

    async def close(self) -> None: ...


ProviderFactory = Callable[[TrialManifest, MockProfile], Provider]
ProviderAttemptObserver = Callable[[Literal["sent", "acknowledged"]], Awaitable[None]]
