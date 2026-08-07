import json
import shutil
from pathlib import Path

import pytest

from src.benchmark.enums import Condition, EventType, MockProfile
from src.benchmark.export import ArtifactIntegrityError, replay_trial
from src.benchmark.models import content_sha256
from src.benchmark.runner import BenchmarkRunner, PairSpec
from src.utils.config import load_config


async def _export_one_trial(benchmark_app, tmp_path: Path) -> Path:
    config = load_config("tests/config_test.yaml")
    config.benchmark.artifact_dir = str(tmp_path / "source")
    bundles = await BenchmarkRunner(benchmark_app, config).run_pair(
        PairSpec(
            pair_id="integrity-source",
            condition_a=Condition.CONTROL,
            condition_b=Condition.SYNTHETIC_INJECTION,
            profile=MockProfile.INJECTION_FOLLOWER,
            seed=1212,
            order="AB",
        )
    )
    treatment = bundles["B"]
    return (
        Path(config.benchmark.artifact_dir)
        / treatment.manifest.pair_id
        / treatment.manifest.trial_id
    )


def _copy_trial(source: Path, tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copytree(source, target)
    return target


def _rehash(trial_dir: Path) -> None:
    hashes = {
        name: content_sha256((trial_dir / name).read_bytes())
        for name in ("manifest.json", "events.jsonl", "result.json")
    }
    (trial_dir / "evidence_hashes.json").write_text(
        json.dumps(hashes, sort_keys=True, indent=2) + "\n"
    )


async def test_export_preserves_redacted_exact_provider_envelopes(
    benchmark_app, tmp_path
):
    trial_dir = await _export_one_trial(benchmark_app, tmp_path)
    events_text = (trial_dir / "events.jsonl").read_text()
    assert "SYNTHETIC-KEY" not in events_text
    assert "[REDACTED:sha256:" in events_text
    events = [json.loads(line) for line in events_text.splitlines()]
    envelopes = [
        event
        for event in events
        if event["event_type"] == EventType.PROVIDER_ENVELOPE.value
    ]
    assert {event["payload"]["direction"] for event in envelopes} == {
        "request",
        "response",
    }
    assert all(len(event["payload"]["raw_sha256"]) == 64 for event in envelopes)
    assert replay_trial(trial_dir)
    assert not list(trial_dir.glob("*.tmp"))
    evidence_summary = trial_dir.parent / "evidence_summary.json"
    assert evidence_summary.is_file()
    assert json.loads(evidence_summary.read_text())["trials"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("reorder", "sequences"),
        ("duplicate_id", "unique"),
        ("cross_trial", "cross-trial"),
        ("backwards_time", "timestamps"),
        ("missing_ledger", "lifecycle"),
        ("stored_result", "stored result"),
        ("wrong_contract", "apparatus contract"),
    ],
)
async def test_replay_rejects_semantic_corruption_even_after_attacker_rehashes(
    benchmark_app, tmp_path, mutation, message
):
    source = await _export_one_trial(benchmark_app, tmp_path / mutation)
    trial_dir = _copy_trial(source, tmp_path, f"copy-{mutation}")
    events_path = trial_dir / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    if mutation == "reorder":
        events[0], events[1] = events[1], events[0]
    elif mutation == "duplicate_id":
        events[1]["event_id"] = events[0]["event_id"]
    elif mutation == "cross_trial":
        events[2]["trial_id"] = "trial-other"
    elif mutation == "backwards_time":
        events[2]["occurred_at"] = "2000-01-01T00:00:00Z"
    elif mutation == "missing_ledger":
        events = [
            event
            for event in events
            if event["event_type"] != EventType.RESOURCE_LEDGER_FINALIZED.value
        ]
        for sequence, event in enumerate(events):
            event["sequence"] = sequence
    elif mutation == "stored_result":
        result_path = trial_dir / "result.json"
        stored = json.loads(result_path.read_text())
        stored["event_count"] += 1
        result_path.write_text(json.dumps(stored, sort_keys=True, separators=(",", ":")) + "\n")
    elif mutation == "wrong_contract":
        manifest_path = trial_dir / "manifest.json"
        result_path = trial_dir / "result.json"
        manifest = json.loads(manifest_path.read_text())
        stored = json.loads(result_path.read_text())
        manifest["apparatus_contract_version"] = "wrong-1"
        stored["manifest"]["apparatus_contract_version"] = "wrong-1"
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
        )
        result_path.write_text(
            json.dumps(stored, sort_keys=True, separators=(",", ":")) + "\n"
        )
    if mutation not in {"stored_result", "wrong_contract"}:
        events_path.write_text(
            "".join(
                json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
                for event in events
            )
        )
    _rehash(trial_dir)
    with pytest.raises(ArtifactIntegrityError, match=message):
        replay_trial(trial_dir)
