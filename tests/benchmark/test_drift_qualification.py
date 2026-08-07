import json

import pytest

from src.benchmark import drift, qualification


def test_repository_contract_and_documentation_drift_check_passes():
    assert drift.drift_errors() == []


def test_data_dictionary_coverage_detects_an_omitted_contract_term(
    monkeypatch, tmp_path
):
    incomplete = tmp_path / "data-dictionary.md"
    incomplete.write_text("# Incomplete\n")
    monkeypatch.setattr(drift, "DATA_DICTIONARY_PATH", incomplete)
    errors = drift._data_dictionary_errors()
    assert "data dictionary omits `trial_created`" in errors
    assert "data dictionary omits `provider_attempts`" in errors


def test_qualification_refuses_dirty_worktree_before_running_commands(monkeypatch):
    monkeypatch.setattr(
        qualification,
        "_git_state",
        lambda root: ("a" * 40, True),
    )
    with pytest.raises(ValueError, match="clean worktree"):
        qualification.run_unpaid_qualification()


def test_evidence_validator_rejects_hosted_or_credential_activity(
    monkeypatch, tmp_path
):
    current = {
        "evidence_schema_version": "1.0.0",
        "status": "passed",
        "tested_commit": "a" * 40,
        "tested_worktree_clean": True,
        "generated_at": "2026-08-08T00:00:00+00:00",
        "python_version": "3.12.0",
        "dependency_lock_sha256": drift.content_sha256(
            (drift.REPOSITORY_ROOT / "uv.lock").read_bytes()
        ),
        "schema_version": drift.SCHEMA_VERSION,
        "apparatus_contract_version": drift.load_apparatus_contract()[
            "apparatus_contract_version"
        ],
        "apparatus_contract_sha256": drift.apparatus_contract_digest(),
        "experimental_protocol_id": drift.load_experimental_protocol().protocol_id,
        "experimental_protocol_version": drift.load_experimental_protocol().protocol_version,
        "experimental_protocol_sha256": drift.experimental_protocol_digest(),
        "scorer_version": "placeholder",
        "scorer_sha256": "placeholder",
        "benchmark_software_sha256": drift.benchmark_software_digest(),
        "commands": [],
        "checks": {name: {} for name in {*drift.PRIMARY_CHECK_NAMES, "clean_checkout"}},
        "network_audit": {"external_destinations": ["https://example.invalid"]},
        "hosted_requests": 1,
        "credential_loaded": True,
        "limitations": [],
    }
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(current))
    monkeypatch.setattr(drift, "EVIDENCE_PATH", evidence_path)
    errors = drift._evidence_errors(required=True)
    assert "unpaid qualification reports a hosted request" in errors
    assert "unpaid qualification reports a credential load" in errors
    assert "unpaid qualification network audit is not loopback-only" in errors
