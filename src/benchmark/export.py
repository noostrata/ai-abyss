"""Deterministic artifacts and offline trace replay."""

from __future__ import annotations

import json
from pathlib import Path

from src.benchmark.models import (
    AgentActionPayload,
    BenchmarkEvent,
    NavigateAction,
    PairComparison,
    ResultBundle,
    SubmitAction,
    TrialManifest,
    canonical_json,
    content_sha256,
)
from src.benchmark.scoring import score_trial


class ArtifactIntegrityError(ValueError):
    pass


def export_trial(
    artifact_root: Path,
    manifest: TrialManifest,
    events: list[BenchmarkEvent],
) -> tuple[ResultBundle, Path]:
    trial_dir = artifact_root / manifest.pair_id / manifest.trial_id
    trial_dir.mkdir(parents=True, exist_ok=True)
    artifact_events = [_artifact_event(event) for event in events]
    events_text = "".join(canonical_json(event) + "\n" for event in artifact_events)
    result = score_trial(manifest, events)
    bundle = ResultBundle(
        manifest=manifest,
        result=result,
        event_count=len(events),
        events_sha256=content_sha256(events_text),
    )
    files = {
        "manifest.json": canonical_json(manifest) + "\n",
        "events.jsonl": events_text,
        "result.json": canonical_json(bundle) + "\n",
    }
    for name, data in files.items():
        (trial_dir / name).write_text(data)
    hashes = {name: content_sha256(data) for name, data in files.items()}
    (trial_dir / "evidence_hashes.json").write_text(
        json.dumps(hashes, sort_keys=True, indent=2) + "\n"
    )
    return bundle, trial_dir


def _artifact_event(event: BenchmarkEvent) -> BenchmarkEvent:
    """Remove the raw synthetic secret while preserving replayable semantics."""
    payload = event.payload
    if isinstance(payload, AgentActionPayload):
        action = payload.action
        updates = {}
        target = getattr(action, "url", None)
        if target and "/event/" in target:
            prefix, token = target.split("/event/", 1)
            updates["url"] = f"{prefix}/event/sha256:{content_sha256(token)}"
        if isinstance(action, SubmitAction):
            fields = dict(action.fields)
            if "secret" in fields:
                fields["secret"] = f"sha256:{content_sha256(fields['secret'])}"
            updates["fields"] = fields
        if updates and isinstance(action, (NavigateAction, SubmitAction)):
            action = action.model_copy(update=updates)
            payload = payload.model_copy(update={"action": action})
            return event.model_copy(update={"payload": payload})
    return event


def replay_trial(trial_dir: Path) -> ResultBundle:
    hash_path = trial_dir / "evidence_hashes.json"
    if not hash_path.exists():
        raise ArtifactIntegrityError("artifact hash manifest is missing")
    try:
        expected_hashes = json.loads(hash_path.read_text())
    except json.JSONDecodeError as error:
        raise ArtifactIntegrityError("artifact hash manifest is malformed") from error
    required = {"manifest.json", "events.jsonl", "result.json"}
    if set(expected_hashes) != required:
        raise ArtifactIntegrityError("artifact hash manifest has an unexpected file set")
    for name, expected in expected_hashes.items():
        path = trial_dir / name
        if not path.is_file() or content_sha256(path.read_bytes()) != expected:
            raise ArtifactIntegrityError(f"artifact hash mismatch: {name}")
    manifest = TrialManifest.model_validate_json((trial_dir / "manifest.json").read_text())
    events_text = (trial_dir / "events.jsonl").read_text()
    events = [BenchmarkEvent.model_validate_json(line) for line in events_text.splitlines() if line]
    result = score_trial(manifest, events)
    return ResultBundle(
        manifest=manifest,
        result=result,
        event_count=len(events),
        events_sha256=content_sha256(events_text),
    )


def export_pair_comparison(
    artifact_root: Path,
    comparison: PairComparison,
) -> Path:
    pair_dir = artifact_root / comparison.pair_id
    pair_dir.mkdir(parents=True, exist_ok=True)
    path = pair_dir / "pair_summary.json"
    path.write_text(canonical_json(comparison) + "\n")
    return path
