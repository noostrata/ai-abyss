"""Tests for the machine-readable apparatus authority and unpaid execution gate."""

from pathlib import Path

import pytest

from src.benchmark.apparatus import (
    APPARATUS_CONTRACT_PATH,
    apparatus_contract_digest,
    apparatus_contract_errors,
    load_apparatus_contract,
)
from src.benchmark.runner import BenchmarkRunner
from src.main import create_benchmark_app
from src.utils.config import load_config


def test_apparatus_contract_is_complete_and_matches_closed_vocabularies() -> None:
    assert APPARATUS_CONTRACT_PATH.is_file()
    assert apparatus_contract_errors() == []
    assert len(apparatus_contract_digest()) == 64
    contract = load_apparatus_contract()
    assert contract["lifecycle"] == {
        "created": ["running"],
        "ended": [],
        "running": ["ended"],
    }
    assert contract["deprecated_events_pending_removal"] == []
    assert contract["required_events_pending_implementation"] == []


def test_checked_in_runner_cannot_select_hosted_provider(tmp_path: Path) -> None:
    raw = Path("config.yaml").read_text()
    config_path = tmp_path / "live.yaml"
    config_path.write_text(
        raw.replace('execution_mode: "mock"', 'execution_mode: "live"')
        .replace("allow_paid: false", "allow_paid: true")
        .replace("paid_gate_approved: false", "paid_gate_approved: true")
        .replace('provider: "mock"', 'provider: "openrouter"')
        .replace('model_id: "mock/task-solver-v1"', 'model_id: "example/model"')
        .replace(
            'paid_gate_approved: true',
            'paid_gate_approved: true\n  paid_run_authorization_id: "test-only"',
        )
    )
    config = load_config(config_path)
    app = create_benchmark_app(config_path)
    with pytest.raises(ValueError, match="local runner requires mock mode"):
        BenchmarkRunner(app, config)
