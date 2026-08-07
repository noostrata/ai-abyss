import json
from pathlib import Path

import pytest

from src.benchmark.enums import Condition, EventType, MockProfile
from src.benchmark.models import AgentActionPayload, BenchmarkEvent, NavigateAction
from src.benchmark.protocol import (
    GENERATED_MATRIX_PATH,
    experimental_protocol_digest,
    generate_run_matrix,
    load_experimental_protocol,
)
from src.benchmark.recognition import blinded_recognition_items
from src.benchmark.runner import PairSpec


def test_calibration_protocol_and_generated_matrix_are_exactly_synchronized():
    protocol = load_experimental_protocol()
    matrix = generate_run_matrix(protocol)
    generated = json.loads(GENERATED_MATRIX_PATH.read_text())
    assert generated == {
        "protocol_id": protocol.protocol_id,
        "protocol_sha256": experimental_protocol_digest(),
        "pairs": matrix,
    }
    assert len(matrix) * 2 == protocol.spending.maximum_trials
    assert {item["order"] for item in matrix} == {"AB", "BA"}
    assert {item["contrast_id"] for item in matrix} == {"recursion", "injection"}
    assert len({item["seed"] for item in matrix}) == len(matrix)
    assert "population" in protocol.inferential_scope.casefold()


def test_protocol_uses_only_matched_primary_contrasts():
    protocol = load_experimental_protocol()
    assert {
        (pair.condition_a, pair.condition_b) for pair in protocol.pairs
    } == {
        (Condition.FINITE_GRAPH_CONTROL, Condition.RECURSIVE_TRAP),
        (Condition.INERT_INJECTION_CONTROL, Condition.SYNTHETIC_INJECTION),
    }
    with pytest.raises(ValueError, match="only matched"):
        PairSpec(
            pair_id="invalid-inert-pair",
            condition_a=Condition.INERT_INJECTION_CONTROL,
            condition_b=Condition.RECURSIVE_TRAP,
            profile=MockProfile.TASK_SOLVER,
            seed=1,
            order="AB",
        )


def test_recognition_review_items_are_blinded_and_missing_rationale_is_absent():
    events = [
        BenchmarkEvent(
            event_id="evt-rationale",
            trial_id="trial-sensitive-condition",
            sequence=0,
            event_type=EventType.AGENT_ACTION,
            payload=AgentActionPayload(
                action=NavigateAction(
                    url="http://127.0.0.1:8443/benchmark/session/docs/catalog",
                    rationale="These pages form a repeating cycle, so I am returning.",
                )
            ),
        ),
        BenchmarkEvent(
            event_id="evt-no-rationale",
            trial_id="trial-sensitive-condition",
            sequence=1,
            event_type=EventType.AGENT_ACTION,
            payload=AgentActionPayload(
                action=NavigateAction(
                    url="http://127.0.0.1:8443/benchmark/session/docs/catalog"
                )
            ),
        ),
    ]
    items = blinded_recognition_items(events)
    assert len(items) == 1
    serialized = items[0].model_dump_json()
    assert "trial-sensitive" not in serialized
    assert "condition" not in serialized
    rubric = json.loads(Path("protocol/recognition-rubric-v1.json").read_text())
    assert rubric["missing_rationale"] == "unknown"
    assert rubric["reviewers"] == 2
