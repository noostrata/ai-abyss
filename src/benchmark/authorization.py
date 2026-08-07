"""Explicit, expiring authority required to construct a hosted provider path."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from src.benchmark.budgets import PriceSnapshot
from src.benchmark.models import ContractModel, Identifier


class PaidRunAuthorization(ContractModel):
    authorization_id: Identifier
    issued_at: datetime
    expires_at: datetime
    one_run_scope: Literal[True] = True
    operator_approval_evidence: str = Field(min_length=1, max_length=256)
    credential_reference: str = Field(min_length=1, max_length=256)
    software_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    apparatus_contract_version: Identifier
    apparatus_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    experimental_protocol_id: Identifier
    experimental_protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_id: str = Field(min_length=1, max_length=256)
    provider_route: str = Field(min_length=1, max_length=256)
    price_snapshot: PriceSnapshot
    max_trials: int = Field(ge=1)
    max_calls_per_trial: int = Field(ge=1)
    max_output_tokens_per_call: int = Field(ge=1)
    max_reasoning_tokens_per_call: int = Field(ge=0)
    trial_cost_cap_usd: float = Field(gt=0)
    batch_cost_cap_usd: float = Field(gt=0)
    provider_spending_limit_usd: float = Field(gt=0)
    dual_layer_egress_evidence_id: Identifier
    kill_switch_id: Identifier
    artifact_policy_id: Identifier

    @field_validator("issued_at", "expires_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def coherent_authority(self) -> PaidRunAuthorization:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization must expire after it is issued")
        if self.max_reasoning_tokens_per_call > self.max_output_tokens_per_call:
            raise ValueError("reasoning tokens must fit within the output-token cap")
        if self.trial_cost_cap_usd > self.batch_cost_cap_usd:
            raise ValueError("trial cost cap cannot exceed the batch cap")
        if self.batch_cost_cap_usd > self.provider_spending_limit_usd:
            raise ValueError("batch cap cannot exceed the provider-side limit")
        if (
            self.price_snapshot.model_id != self.model_id
            or self.price_snapshot.provider_route != self.provider_route
        ):
            raise ValueError("price snapshot identity must match the authorized route")
        return self

    def assert_current(self, now: datetime | None = None) -> None:
        current = now or datetime.now(UTC)
        if current < self.issued_at or current >= self.expires_at:
            raise ValueError("paid-run authorization is not currently valid")
