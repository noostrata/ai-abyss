# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Signal definitions and weighted fusion for request classification

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Classification(str, enum.Enum):
    HUMAN = "HUMAN"
    COMPLIANT_BOT = "COMPLIANT_BOT"
    HOSTILE_BOT = "HOSTILE_BOT"


@dataclass
class Signal:

    name: str
    score: float
    weight: float
    detail: str = ""

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ClassificationResult:

    signals: list[Signal] = field(default_factory=list)
    raw_score: float = 0.0
    final_score: float = 0.0
    classification: Classification = Classification.HUMAN
    robots_override: bool = False

    @property
    def signal_details(self) -> dict[str, float]:
        return {s.name: round(s.score, 3) for s in self.signals}


def fuse_signals(
    signals: list[Signal],
    human_max: float = 0.3,
    compliant_max: float = 0.6,
    robots_override: bool = False,
    robots_override_floor: float = 0.7,
    known_crawler_floor: float | None = None,
) -> ClassificationResult:
    if not signals:
        return ClassificationResult(classification=Classification.HUMAN)

    total_weight = sum(s.weight for s in signals)
    if total_weight == 0:
        return ClassificationResult(signals=signals, classification=Classification.HUMAN)

    raw_score = sum(s.weighted_score for s in signals) / total_weight
    final_score = raw_score

    override_applied = False

    # Named AI crawler floor — conclusive regardless of other signals
    if known_crawler_floor is not None and final_score < known_crawler_floor:
        final_score = known_crawler_floor
        override_applied = True

    if robots_override and final_score < robots_override_floor:
        final_score = robots_override_floor
        override_applied = True

    final_score = max(0.0, min(1.0, final_score))

    if final_score <= human_max:
        classification = Classification.HUMAN
    elif final_score <= compliant_max:
        classification = Classification.COMPLIANT_BOT
    else:
        classification = Classification.HOSTILE_BOT

    return ClassificationResult(
        signals=signals,
        raw_score=round(raw_score, 4),
        final_score=round(final_score, 4),
        classification=classification,
        robots_override=override_applied,
    )
