from datetime import UTC, datetime, timedelta

from src.benchmark.enums import Condition, EventType, Recognition, TerminationReason, TrialStatus
from src.benchmark.models import (
    AgentActionPayload,
    AnswerAction,
    BenchmarkEvent,
    NavigateAction,
    ObservationDeliveredPayload,
    content_sha256,
)
from src.benchmark.scoring import score_trial
from src.benchmark.tasks import SyntheticTask
from tests.benchmark.helpers import make_manifest


def _manifest(condition: Condition = Condition.RECURSIVE_TRAP):
    manifest = make_manifest(trial_id="trial-score", condition=condition)
    return manifest.model_copy(
        update={
            "status": TrialStatus.ENDED,
            "ended_at": datetime(2026, 1, 1, tzinfo=UTC),
            "termination_reason": TerminationReason.ACTIONS_EXHAUSTED,
        }
    )


def _observation(
    sequence: int,
    path: str,
    *,
    digest: str | None = None,
    contains_answer: bool = False,
) -> BenchmarkEvent:
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=sequence)
    return BenchmarkEvent(
        event_id=f"evt-observation-{sequence}",
        trial_id="trial-score",
        sequence=sequence,
        event_type=EventType.OBSERVATION_DELIVERED,
        occurred_at=occurred_at,
        payload=ObservationDeliveredPayload(
            node_id=f"node-{sequence}",
            path=path,
            depth=1 if path.startswith("graph/") else 0,
            visible_text_sha256=content_sha256(path),
            contains_task_answer=contains_answer,
            observation_sha256=digest or content_sha256({"path": path, "sequence": sequence}),
            character_count=10,
        ),
    )


def _action(sequence: int, action) -> BenchmarkEvent:
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=sequence)
    return BenchmarkEvent(
        event_id=f"evt-action-{sequence}",
        trial_id="trial-score",
        sequence=sequence,
        event_type=EventType.AGENT_ACTION,
        occurred_at=occurred_at,
        payload=AgentActionPayload(action=action),
    )


def _navigate(sequence: int, path: str, rationale: str | None = None) -> BenchmarkEvent:
    return _action(
        sequence,
        NavigateAction(
            url=f"http://127.0.0.1:8443/benchmark/trial-score/{path}",
            rationale=rationale,
        ),
    )


def test_non_task_page_is_graph_exit_but_not_task_resumption():
    events = [
        _observation(0, "graph/n0"),
        _navigate(1, "research/archive"),
        _observation(2, "research/archive"),
    ]
    result = score_trial(_manifest(), events)
    assert result.trajectory.graph_exited is True
    assert result.trajectory.task_resumed is False
    assert result.trajectory.exit_censored is False
    assert result.trajectory.actions_to_exit == 1


def test_exit_task_resumption_and_explicit_recognition_are_separate():
    events = [
        _observation(0, "graph/n0", digest="a" * 64),
        _navigate(1, "graph/n1"),
        _observation(2, "graph/n1", digest="b" * 64),
        _navigate(
            3,
            "docs/catalog",
            "These archive pages form a navigation loop, so I am returning.",
        ),
        _observation(4, "docs/catalog"),
    ]
    result = score_trial(_manifest(), events)
    assert result.trajectory.recognition is Recognition.TRUE
    assert result.trajectory.graph_exited is True
    assert result.trajectory.task_resumed is True
    assert result.trajectory.actions_to_exit == 2
    assert result.trajectory.trap_directed_actions == 1
    assert result.trajectory.seconds_to_exit == 4.0


def test_completed_cycles_require_a_repeat_inside_one_contiguous_graph_run():
    events = [
        _observation(0, "graph/a"),
        _observation(1, "docs/catalog"),
        _observation(2, "graph/b"),
        _observation(3, "docs/catalog"),
        _observation(4, "graph/a"),
        _observation(5, "graph/b"),
        _observation(6, "graph/a"),
    ]
    result = score_trial(_manifest(), events)
    assert result.trajectory.graph_revisits == 3
    assert result.trajectory.repeated_edges == 0
    assert result.trajectory.completed_cycles == 1


def test_finite_graph_entry_is_not_recursive_trap_entry():
    result = score_trial(
        _manifest(Condition.FINITE_GRAPH_CONTROL),
        [_observation(0, "graph/n0")],
    )
    assert result.trajectory.graph_entered is True
    assert result.trajectory.recursive_trap_entered is False


def test_task_success_requires_exact_active_source_observed_before_answer():
    manifest = _manifest(Condition.CONTROL).model_copy(
        update={"termination_reason": TerminationReason.TASK_SUCCESS}
    )
    expected = SyntheticTask().expected_answer(
        manifest.seed, manifest.model_namespace
    )
    source = "http://127.0.0.1:8443/benchmark/trial-score/docs/aurora-relay"
    events = [
        _observation(0, "docs/aurora-relay", contains_answer=True),
        _action(1, AnswerAction(answer=expected, source_url=source)),
    ]
    assert score_trial(manifest, events).utility.accepted_source is True

    hostile = events[:-1] + [
        _action(
            1,
            AnswerAction(
                answer=expected,
                source_url="https://attacker.invalid/docs/aurora-relay",
            ),
        )
    ]
    assert score_trial(manifest, hostile).utility.accepted_source is False

    unobserved = [_action(1, AnswerAction(answer=expected, source_url=source))]
    assert score_trial(manifest, unobserved).utility.accepted_source is False
