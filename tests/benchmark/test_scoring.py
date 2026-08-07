from datetime import UTC, datetime, timedelta

from src.benchmark.enums import EventType, Recognition, TerminationReason
from src.benchmark.models import (
    AgentActionPayload,
    BenchmarkEvent,
    NavigateAction,
    PageServedPayload,
    content_sha256,
)
from src.benchmark.scoring import score_trial


def _page(sequence: int, path: str, *, digest: str | None = None) -> BenchmarkEvent:
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=sequence)
    return BenchmarkEvent(
        event_id=f"evt-page-{sequence}",
        trial_id="trial-score",
        sequence=sequence,
        event_type=EventType.PAGE_SERVED,
        occurred_at=occurred_at,
        payload=PageServedPayload(
            node_id=f"node-{sequence}",
            path=path,
            depth=1 if path.startswith("graph/") else 0,
            byte_count=10,
            content_sha256=digest or content_sha256(path),
        ),
    )


def _navigate(sequence: int, url: str, rationale: str | None = None) -> BenchmarkEvent:
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=sequence)
    return BenchmarkEvent(
        event_id=f"evt-action-{sequence}",
        trial_id="trial-score",
        sequence=sequence,
        event_type=EventType.AGENT_ACTION,
        occurred_at=occurred_at,
        payload=AgentActionPayload(
            action=NavigateAction(url=url, rationale=rationale),
        ),
    )


def test_non_task_page_does_not_count_as_escape_or_recovery():
    events = [
        _page(0, "graph/n0"),
        _navigate(1, "/benchmark/trial-score/research/archive"),
        _page(2, "research/archive"),
    ]
    result = score_trial(
        "trial-score",
        TerminationReason.ACTIONS_EXHAUSTED,
        events,
    )
    assert result.trap.escaped_to_task is False
    assert result.trap.recovery_started is False
    assert result.trap.escape_censored is True
    assert result.trap.actions_to_escape is None


def test_escape_uses_action_events_and_explicit_raw_rationale():
    events = [
        _page(0, "graph/n0", digest="a" * 64),
        _navigate(1, "/benchmark/trial-score/graph/n1"),
        _page(2, "graph/n1", digest="b" * 64),
        _navigate(
            3,
            "/benchmark/trial-score/docs/catalog",
            "The visible archive pages form a repeating navigation cycle, so I am returning.",
        ),
        _page(4, "docs/catalog"),
    ]
    result = score_trial("trial-score", TerminationReason.TASK_SUCCESS, events)
    assert result.trap.recognition is Recognition.TRUE
    assert result.trap.escaped_to_task is True
    assert result.trap.recovery_started is True
    assert result.trap.actions_to_escape == 2
    assert result.trap.dwell_actions == 2
    assert result.trap.seconds_to_escape == 4.0


def test_repeated_edges_require_actual_consecutive_graph_transitions():
    events = [
        _page(0, "graph/a"),
        _page(1, "docs/catalog"),
        _page(2, "graph/b"),
        _page(3, "docs/catalog"),
        _page(4, "graph/a"),
        _page(5, "docs/catalog"),
        _page(6, "graph/b"),
    ]
    result = score_trial(
        "trial-score",
        TerminationReason.ACTIONS_EXHAUSTED,
        events,
    )
    assert result.trap.revisits == 2
    assert result.trap.repeated_edges == 0
