"""Blinded review material for the secondary recognition outcome."""

from __future__ import annotations

from pydantic import Field

from src.benchmark.models import (
    AgentActionPayload,
    BenchmarkEvent,
    ContractModel,
    Identifier,
    content_sha256,
)

RECOGNITION_RUBRIC_VERSION = "recognition-rubric-1.0.0"


class BlindedRecognitionItem(ContractModel):
    item_id: Identifier
    rubric_version: Identifier = RECOGNITION_RUBRIC_VERSION
    action_sequence: int = Field(ge=0)
    rationale: str = Field(min_length=1, max_length=512)


def blinded_recognition_items(events: list[BenchmarkEvent]) -> list[BlindedRecognitionItem]:
    """Remove trial and condition identity while retaining observable rationales."""

    items: list[BlindedRecognitionItem] = []
    for event in sorted(events, key=lambda item: item.sequence):
        if not isinstance(event.payload, AgentActionPayload):
            continue
        rationale = getattr(event.payload.action, "rationale", None)
        if not rationale:
            continue
        digest = content_sha256(
            {"sequence": event.sequence, "rationale": rationale}
        )[:20]
        items.append(
            BlindedRecognitionItem(
                item_id=f"recognition-{digest}",
                action_sequence=event.sequence,
                rationale=rationale,
            )
        )
    return items
