from datetime import datetime

import pytest
from asgi_lifespan import LifespanManager
from pydantic import ValidationError

from src.benchmark.enums import EventType, ExecutionMode, TerminationReason
from src.benchmark.models import (
    AGENT_ACTION_ADAPTER,
    BenchmarkEvent,
    LifecyclePayload,
    ResourceLedger,
    ResultBundle,
    TrajectoryScore,
    TrialResult,
    TrialStatus,
    UtilityScore,
    UtilityStatus,
    canonical_json,
    content_sha256,
)
from src.benchmark.scaffold import SYSTEM_PROMPT
from src.main import create_benchmark_app
from src.utils.config import AppConfig, BenchmarkConfig, load_config, resolve_config_path
from tests.benchmark.helpers import make_manifest


def test_checked_in_configuration_is_mock_local_and_unpaid():
    config = load_config("config.yaml")
    assert config.benchmark.execution_mode is ExecutionMode.MOCK
    assert config.benchmark.allow_paid is False
    assert config.benchmark.bind_host == "127.0.0.1"
    assert config.benchmark.admin_enabled is False
    assert config.benchmark.provider == "mock"


def test_live_configuration_refuses_without_every_gate():
    with pytest.raises(ValidationError, match="allow_paid is false"):
        BenchmarkConfig(execution_mode="live", provider="openrouter", model_id="vendor/model")
    with pytest.raises(ValidationError, match="authorization is absent"):
        BenchmarkConfig(
            execution_mode="live",
            allow_paid=True,
            provider="openrouter",
            model_id="vendor/model",
        )
    with pytest.raises(ValidationError, match="non-placeholder provider"):
        BenchmarkConfig(
            execution_mode="live",
            allow_paid=True,
            paid_gate_approved=True,
            paid_run_authorization_id="test-authorization",
            provider="your-provider",
            model_id="vendor/model",
        )


def test_missing_configuration_uses_safe_defaults(tmp_path):
    config = load_config(tmp_path / "does-not-exist.yaml")
    assert config.benchmark.execution_mode is ExecutionMode.MOCK
    assert config.benchmark.allow_paid is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("local_base_url", "https://example.com"),
        ("callback_base_url", "http://169.254.169.254"),
        ("local_base_url", "http://localhost.evil:8443"),
        ("local_base_url", "http://localhost/benchmark"),
        ("callback_base_url", "http://127.0.0.1"),
    ],
)
def test_benchmark_urls_reject_non_loopback(field, value):
    with pytest.raises(ValidationError):
        BenchmarkConfig(**{field: value})


def test_configuration_resolution_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert resolve_config_path() == tmp_path / "config.yaml" or resolve_config_path() == __import__("pathlib").Path("config.yaml")
    (tmp_path / "config.local.yaml").write_text("benchmark:\n  execution_mode: mock\n")
    assert resolve_config_path().name == "config.local.yaml"
    monkeypatch.setenv("AI_ABYSS_CONFIG", "chosen.yaml")
    assert resolve_config_path().name == "chosen.yaml"
    assert resolve_config_path("explicit.yaml").name == "explicit.yaml"


async def test_benchmark_app_uses_resolved_environment_config(tmp_path, monkeypatch):
    chosen = tmp_path / "chosen.yaml"
    chosen.write_text(
        "server:\n"
        "  port: 9444\n"
        "benchmark:\n"
        "  local_base_url: http://localhost:9444\n"
        "  callback_base_url: http://localhost:9444\n"
        "  db_path: ':memory:'\n"
        "  egress_allowlist: [localhost]\n"
    )
    monkeypatch.setenv("AI_ABYSS_CONFIG", str(chosen))
    app = create_benchmark_app()
    async with LifespanManager(app):
        assert app.state.benchmark_services.event_sink.base_url == "http://localhost:9444"


def test_benchmark_urls_must_match_the_bound_server_port():
    with pytest.raises(ValidationError, match="bound server port"):
        AppConfig(
            server={"port": 8443},
            benchmark={
                "local_base_url": "http://127.0.0.1:9444",
                "callback_base_url": "http://127.0.0.1:9444",
            },
        )


def test_manifest_event_and_result_round_trip():
    manifest = make_manifest()
    event = BenchmarkEvent(
        event_id="evt-test-001",
        trial_id=manifest.trial_id,
        sequence=0,
        event_type=EventType.TRIAL_CREATED,
        payload=LifecyclePayload(status=TrialStatus.CREATED),
    )
    assert BenchmarkEvent.model_validate_json(canonical_json(event)) == event
    result = TrialResult(
        trial_id=manifest.trial_id,
        termination_reason=TerminationReason.TASK_SUCCESS,
        utility=UtilityScore(
            status=UtilityStatus.CORRECT,
            exact_answer_match=True,
            accepted_source=True,
        ),
        trajectory=TrajectoryScore(
            payload_delivered=False,
            lure_selected=False,
            graph_entered=False,
            recursive_trap_entered=False,
            graph_propagated=False,
            trap_directed_actions=0,
            graph_revisits=0,
            repeated_edges=0,
            completed_cycles=0,
            max_depth=0,
            callback_visited=False,
            submission_attempted=False,
            exact_secret_submitted=False,
            graph_exited=False,
            task_resumed=False,
            task_completed=False,
            reentered=False,
        ),
        operator_ledger=ResourceLedger(),
        scaffold_ledger=ResourceLedger(),
        model_ledger=ResourceLedger(),
    )
    ended = manifest.model_copy(
        update={
            "status": TrialStatus.ENDED,
            "ended_at": event.occurred_at,
            "termination_reason": TerminationReason.TASK_SUCCESS,
        }
    )
    bundle = ResultBundle(
        manifest=ended,
        result=result,
        event_count=1,
        events_sha256=content_sha256(canonical_json(event) + "\n"),
    )
    assert ResultBundle.model_validate_json(canonical_json(bundle)) == bundle
    assert manifest.observation_version
    assert len(manifest.tool_set) == 4
    assert manifest.sampling.seed == 42


def test_contracts_reject_naive_timestamps_and_wrong_payload_type():
    with pytest.raises(ValidationError, match="timezone-aware"):
        BenchmarkEvent(
            event_id="evt-test-002",
            trial_id="trial-test-001",
            sequence=0,
            event_type=EventType.TRIAL_CREATED,
            occurred_at=datetime(2026, 1, 1, tzinfo=None),  # noqa: DTZ001 - invalid by design
            payload=LifecyclePayload(status=TrialStatus.CREATED),
        )
    with pytest.raises(TypeError, match="payload does not match"):
        BenchmarkEvent(
            event_id="evt-test-003",
            trial_id="trial-test-001",
            sequence=0,
            event_type=EventType.TRIAL_ENDED,
            payload=LifecyclePayload(status=TrialStatus.ENDED),
        )


def test_config_has_no_provider_secret_field():
    schema = AppConfig.model_json_schema()
    benchmark_fields = schema["$defs"]["BenchmarkConfig"]["properties"]
    assert "api_key" not in benchmark_fields
    assert "credential" not in benchmark_fields


def test_model_facing_action_schema_and_system_prompt_have_no_treatment_hints():
    model_facing = (canonical_json(AGENT_ACTION_ADAPTER.json_schema()) + SYSTEM_PROMPT).casefold()
    for forbidden in ("condition", "honeypot", "recognise_trap", "recognized_trap"):
        assert forbidden not in model_facing
