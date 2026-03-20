"""Signal definitions and weighted fusion for request classification."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Classification(str, enum.Enum):
    HUMAN = "HUMAN"
    COMPLIANT_BOT = "COMPLIANT_BOT"
    HOSTILE_BOT = "HOSTILE_BOT"


@dataclass
class Signal:
    """A single classification signal with its score and metadata."""

    name: str
    score: float  # 0.0 = definitely human, 1.0 = definitely hostile bot
    weight: float
    detail: str = ""

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ClassificationResult:
    """Aggregated classification decision from all signals."""

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
    """Combine weighted signals into a classification decision.

    The score is a weighted average normalized by total weight, so adding more signals
    doesn't inflate the score beyond 1.0.

    If robots_override is True (bot didn't respect robots.txt), the final score
    is floored at robots_override_floor regardless of other signals.

    If known_crawler_floor is set, the UA matched a named AI crawler — floor the score
    at that value since the identity alone is conclusive.
    """
    if not signals:
        return ClassificationResult(classification=Classification.HUMAN)

    total_weight = sum(s.weight for s in signals)
    if total_weight == 0:
        return ClassificationResult(signals=signals, classification=Classification.HUMAN)

    raw_score = sum(s.weighted_score for s in signals) / total_weight
    final_score = raw_score

    override_applied = False

    # Known AI crawler floor — a named crawler (GPTBot, ClaudeBot, etc.) is
    # conclusive regardless of IP/behaviour signals being absent.
    if known_crawler_floor is not None and final_score < known_crawler_floor:
        final_score = known_crawler_floor
        override_applied = True

    if robots_override and final_score < robots_override_floor:
        final_score = robots_override_floor
        override_applied = True

    # Clamp
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
