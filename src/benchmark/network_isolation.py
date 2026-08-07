"""Evidence contract for external hosted-run egress enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, field_validator

from src.benchmark.models import ContractModel, Identifier


class HostedIsolationEvidence(ContractModel):
    """Attestation to an active OS firewall or independently enforced proxy policy."""

    evidence_id: Identifier
    enforcement_kind: Literal["os_firewall", "dedicated_proxy"]
    independent_enforcement: Literal[True] = True
    authorized_endpoint: str = Field(min_length=1, max_length=512)
    activated_at: datetime
    expires_at: datetime
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    allowed_probe_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    blocked_probe_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("activated_at", "expires_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("isolation evidence timestamps must be timezone-aware")
        return value

    def assert_current(
        self,
        *,
        evidence_id: str,
        endpoint: str,
        now: datetime | None = None,
    ) -> None:
        current = now or datetime.now(UTC)
        if (
            self.evidence_id != evidence_id
            or self.authorized_endpoint != endpoint
            or current < self.activated_at
            or current >= self.expires_at
        ):
            raise ValueError("hosted network isolation evidence is invalid or expired")
