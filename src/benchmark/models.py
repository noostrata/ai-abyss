"""Typed, serializable benchmark contracts.

These models are intentionally independent from the web application so a run
can be planned, validated, hashed, and replayed without starting a server.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from src.benchmark.enums import (
    AgentActionKind,
    Condition,
    EventType,
    Recognition,
    TerminationReason,
    TrialStatus,
    UtilityStatus,
)

SCHEMA_VERSION = "1.0.0"
Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")]


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class BudgetLimits(ContractModel):
    calls: int = Field(default=20, ge=1)
    prompt_tokens: int = Field(default=30_000, ge=1)
    completion_tokens: int = Field(default=10_000, ge=1)
    total_tokens: int = Field(default=40_000, ge=1)
    actions: int = Field(default=30, ge=1)
    requests: int = Field(default=40, ge=1)
    bytes_read: int = Field(default=1_000_000, ge=1)
    unique_nodes: int = Field(default=40, ge=1)
    max_depth: int = Field(default=20, ge=1)
    wall_clock_seconds: float = Field(default=300.0, gt=0)
    cost_usd: float = Field(default=1.0, ge=0)

    @model_validator(mode="after")
    def total_covers_components(self) -> BudgetLimits:
        if self.total_tokens < self.prompt_tokens or self.total_tokens < self.completion_tokens:
            raise ValueError("total_tokens must cover each independent token limit")
        return self


class ProviderUsage(ContractModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    provider_reported_cost_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> ProviderUsage:
        if self.total_tokens < self.prompt_tokens + self.completion_tokens:
            raise ValueError("total_tokens cannot be below prompt plus completion tokens")
        return self


class SamplingConfig(ContractModel):
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)


class ResourceLedger(ContractModel):
    calls: int = Field(default=0, ge=0)
    requests: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    actions: int = Field(default=0, ge=0)
    bytes_read: int = Field(default=0, ge=0)
    bytes_served: int = Field(default=0, ge=0)
    unique_nodes: int = Field(default=0, ge=0)
    max_depth: int = Field(default=0, ge=0)
    wall_clock_seconds: float = Field(default=0.0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0)
    provider_reported_cost_usd: float | None = Field(default=None, ge=0)
    cpu_seconds: float | None = Field(default=None, ge=0)
    peak_memory_bytes: int | None = Field(default=None, ge=0)
    connections: int | None = Field(default=None, ge=0)
    file_descriptors_peak: int | None = Field(default=None, ge=0)


class NavigateAction(ContractModel):
    action: Literal[AgentActionKind.NAVIGATE] = AgentActionKind.NAVIGATE
    url: str = Field(min_length=1, max_length=2048)
    rationale: str | None = Field(default=None, max_length=512)


class SubmitAction(ContractModel):
    action: Literal[AgentActionKind.SUBMIT] = AgentActionKind.SUBMIT
    url: str = Field(min_length=1, max_length=2048)
    fields: dict[str, str] = Field(default_factory=dict)
    rationale: str | None = Field(default=None, max_length=512)

    @field_validator("fields")
    @classmethod
    def bounded_fields(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 8 or any(len(key) > 64 or len(item) > 512 for key, item in value.items()):
            raise ValueError("submission fields exceed the fixed action schema")
        return value


class AnswerAction(ContractModel):
    action: Literal[AgentActionKind.ANSWER] = AgentActionKind.ANSWER
    answer: str = Field(min_length=1, max_length=2048)
    source_url: str | None = Field(default=None, max_length=2048)
    rationale: str | None = Field(default=None, max_length=512)


class AbortAction(ContractModel):
    action: Literal[AgentActionKind.ABORT] = AgentActionKind.ABORT
    reason: str = Field(min_length=1, max_length=512)
    refused: bool = False
    rationale: str | None = Field(default=None, max_length=512)


AgentAction = Annotated[
    NavigateAction | SubmitAction | AnswerAction | AbortAction,
    Field(discriminator="action"),
]
AGENT_ACTION_ADAPTER = TypeAdapter(AgentAction)


class PageServedPayload(ContractModel):
    node_id: Identifier
    path: str = Field(min_length=1, max_length=2048)
    depth: int = Field(ge=0)
    byte_count: int = Field(ge=0)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    vector: str | None = Field(default=None, max_length=64)
    payload_id: Identifier | None = None


class RequestAttemptPayload(ContractModel):
    method: Literal["GET", "POST"]
    node_id: Identifier
    path: str = Field(min_length=1, max_length=2048)
    depth: int = Field(ge=0)


class ObservationDeliveredPayload(ContractModel):
    node_id: Identifier
    observation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    character_count: int = Field(ge=0)
    payload_id: Identifier | None = None
    payload_span: tuple[int, int] | None = None

    @model_validator(mode="after")
    def validate_span(self) -> ObservationDeliveredPayload:
        if self.payload_span is not None:
            start, end = self.payload_span
            if start < 0 or end <= start or end > self.character_count:
                raise ValueError("payload span must lie inside the delivered observation")
            if self.payload_id is None:
                raise ValueError("payload span requires a payload_id")
        return self


class AgentActionPayload(ContractModel):
    action: AgentAction


class ModelCallPayload(ContractModel):
    call_id: Identifier
    provider: Identifier
    model_id: str = Field(min_length=1, max_length=256)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    usage: ProviderUsage


class CallbackPayload(ContractModel):
    token_id: Identifier
    exposure_id: Identifier
    vector: str = Field(min_length=1, max_length=64)
    matched_expected_secret: bool | None = None


class BudgetPayload(ContractModel):
    reservation_id: Identifier
    reserved: ResourceLedger
    actual: ResourceLedger | None = None


class OutcomePayload(ContractModel):
    termination_reason: TerminationReason
    utility_status: UtilityStatus


class InfrastructureErrorPayload(ContractModel):
    component: str = Field(min_length=1, max_length=64)
    error_code: str = Field(min_length=1, max_length=64)


class LifecyclePayload(ContractModel):
    status: TrialStatus


class CallbackTokenIssuedPayload(ContractModel):
    token_id: Identifier
    exposure_id: Identifier
    vector: str = Field(min_length=1, max_length=64)
    expected_event_type: str = Field(min_length=1, max_length=64)
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


EventPayload = (
    RequestAttemptPayload
    | PageServedPayload
    | ObservationDeliveredPayload
    | AgentActionPayload
    | ModelCallPayload
    | CallbackPayload
    | BudgetPayload
    | OutcomePayload
    | InfrastructureErrorPayload
    | LifecyclePayload
    | CallbackTokenIssuedPayload
)


class BenchmarkEvent(ContractModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    event_id: Identifier
    trial_id: Identifier
    sequence: int = Field(default=0, ge=0)
    event_type: EventType
    occurred_at: datetime = Field(default_factory=utc_now)
    payload: EventPayload

    @field_validator("occurred_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def payload_matches_event_type(self) -> BenchmarkEvent:
        expected: dict[EventType, type[ContractModel]] = {
            EventType.TRIAL_CREATED: LifecyclePayload,
            EventType.TRIAL_STARTED: LifecyclePayload,
            EventType.REQUEST_ATTEMPT: RequestAttemptPayload,
            EventType.PAGE_SERVED: PageServedPayload,
            EventType.OBSERVATION_DELIVERED: ObservationDeliveredPayload,
            EventType.AGENT_ACTION: AgentActionPayload,
            EventType.MODEL_CALL: ModelCallPayload,
            EventType.CALLBACK_TOKEN_ISSUED: CallbackTokenIssuedPayload,
            EventType.CALLBACK_VISITED: CallbackPayload,
            EventType.SYNTHETIC_SECRET_SUBMITTED: CallbackPayload,
            EventType.SECONDARY_INSTRUCTION_FOLLOWED: CallbackPayload,
            EventType.BUDGET_RESERVED: BudgetPayload,
            EventType.BUDGET_RECONCILED: BudgetPayload,
            EventType.TRIAL_ENDED: OutcomePayload,
            EventType.INFRASTRUCTURE_ERROR: InfrastructureErrorPayload,
        }
        if not isinstance(self.payload, expected[self.event_type]):
            raise TypeError(f"payload does not match event type {self.event_type.value}")
        return self


class TrialManifest(ContractModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    trial_id: Identifier
    pair_id: Identifier
    pair_order: Literal["AB", "BA"]
    pair_position: Literal["A", "B"]
    task_id: Identifier
    task_version: Identifier
    condition: Condition
    condition_version: Identifier
    seed: int = Field(ge=0, le=2**63 - 1)
    provider: Identifier
    provider_profile: Identifier | None = None
    provider_route: str = Field(default="mock-local", min_length=1, max_length=256)
    model_id: str = Field(min_length=1, max_length=256)
    scaffold_version: Identifier
    prompt_version: Identifier
    observation_version: Identifier
    tool_schema_version: Identifier
    tool_set: list[AgentActionKind] = Field(min_length=4, max_length=4)
    sampling: SamplingConfig
    system_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_commit: str = Field(pattern=r"^[0-9a-f]{7,40}$")
    git_dirty: bool
    budgets: BudgetLimits
    price_snapshot_id: Identifier
    synthetic_secret_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cache_policy: Literal["fresh_no_cache"] = "fresh_no_cache"
    status: TrialStatus = TrialStatus.CREATED
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    termination_reason: TerminationReason | None = None

    @field_validator("created_at", "started_at", "ended_at")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def coherent_lifecycle(self) -> TrialManifest:
        if self.status is TrialStatus.ENDED and (self.ended_at is None or self.termination_reason is None):
            raise ValueError("ended trials require ended_at and termination_reason")
        return self


class UtilityScore(ContractModel):
    status: UtilityStatus
    exact_answer_match: bool
    accepted_source: bool


class TrapScore(ContractModel):
    exposed: bool
    attracted: bool
    entered: bool
    propagated: bool
    dwell_actions: int = Field(ge=0)
    revisits: int = Field(ge=0)
    repeated_states: int = Field(default=0, ge=0)
    repeated_edges: int = Field(ge=0)
    cycles: int = Field(ge=0)
    max_depth: int = Field(ge=0)
    callback_visited: bool
    synthetic_secret_submitted: bool
    secondary_instruction_followed: bool
    recognition: Recognition = Recognition.UNKNOWN
    escaped_to_task: bool
    recovery_started: bool
    reentered: bool
    actions_to_escape: int | None = Field(default=None, ge=0)
    seconds_to_escape: float | None = Field(default=None, ge=0)
    escape_censored: bool = True


class TrialResult(ContractModel):
    trial_id: Identifier
    termination_reason: TerminationReason
    utility: UtilityScore
    trap: TrapScore
    operator_ledger: ResourceLedger
    scaffold_ledger: ResourceLedger
    model_ledger: ResourceLedger


class ResultBundle(ContractModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    manifest: TrialManifest
    result: TrialResult
    event_count: int = Field(ge=0)
    events_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def same_trial(self) -> ResultBundle:
        if self.manifest.trial_id != self.result.trial_id:
            raise ValueError("manifest and result trial IDs differ")
        return self


class PairComparison(ContractModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    pair_id: Identifier
    pair_order: Literal["AB", "BA"]
    run_order: list[Literal["A", "B"]] = Field(min_length=2, max_length=2)
    condition_a: Condition
    condition_b: Condition
    treatment_minus_control: dict[str, float | int]
    economic_amplification: float | None = None
    economic_note: str


def canonical_json(value: BaseModel | dict | list) -> str:
    if isinstance(value, BaseModel):
        serializable = value.model_dump(mode="json")
    else:
        serializable = value
    return json.dumps(serializable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_sha256(value: str | bytes | BaseModel | dict | list) -> str:
    if isinstance(value, (BaseModel, dict, list)):
        data = canonical_json(value).encode()
    elif isinstance(value, str):
        data = value.encode()
    else:
        data = value
    return hashlib.sha256(data).hexdigest()
