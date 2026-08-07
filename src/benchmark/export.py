"""Atomic benchmark artifacts and strict offline trace replay."""

from __future__ import annotations

import json
import os
import secrets
from itertools import pairwise
from pathlib import Path

from src.benchmark.apparatus import (
    apparatus_contract_digest,
    benchmark_software_digest,
    load_apparatus_contract,
)
from src.benchmark.enums import EventType, TrialStatus
from src.benchmark.models import (
    BenchmarkEvent,
    OutcomePayload,
    PairComparison,
    ResourceLedgerFinalizedPayload,
    ResultBundle,
    TrialManifest,
    canonical_json,
    content_sha256,
)
from src.benchmark.protocol import (
    experimental_protocol_digest,
    load_experimental_protocol,
)
from src.benchmark.redaction import redact_sensitive
from src.benchmark.scoring import SCORER_VERSION, score_trial, scorer_digest


class ArtifactIntegrityError(ValueError):
    pass


def export_trial(
    artifact_root: Path,
    manifest: TrialManifest,
    events: list[BenchmarkEvent],
    sensitive_values: set[str] | None = None,
) -> tuple[ResultBundle, Path]:
    trial_dir = artifact_root / manifest.pair_id / manifest.trial_id
    trial_dir.mkdir(parents=True, exist_ok=True)
    artifact_events = [
        _artifact_event(event, sensitive_values or set()) for event in events
    ]
    events_text = "".join(canonical_json(event) + "\n" for event in artifact_events)
    result = score_trial(manifest, artifact_events)
    bundle = ResultBundle(
        manifest=manifest,
        result=result,
        event_count=len(artifact_events),
        events_sha256=content_sha256(events_text),
    )
    files = {
        "manifest.json": canonical_json(manifest) + "\n",
        "events.jsonl": events_text,
        "result.json": canonical_json(bundle) + "\n",
    }
    for name, data in files.items():
        _atomic_write(trial_dir / name, data)
    hashes = {name: content_sha256(data) for name, data in files.items()}
    hashes_text = json.dumps(hashes, sort_keys=True, indent=2) + "\n"
    _atomic_write(trial_dir / "evidence_hashes.json", hashes_text)
    _update_pair_evidence_summary(
        artifact_root,
        manifest,
        content_sha256(hashes_text),
    )
    return bundle, trial_dir


def _artifact_event(
    event: BenchmarkEvent, sensitive_values: set[str]
) -> BenchmarkEvent:
    """Recursively redact registered values while preserving typed semantics."""

    return BenchmarkEvent.model_validate(redact_sensitive(event, sensitive_values))


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
    try:
        manifest = TrialManifest.model_validate_json(
            (trial_dir / "manifest.json").read_text()
        )
        events_text = (trial_dir / "events.jsonl").read_text()
        events = [
            BenchmarkEvent.model_validate_json(line)
            for line in events_text.splitlines()
            if line
        ]
        stored = ResultBundle.model_validate_json(
            (trial_dir / "result.json").read_text()
        )
    except (ValueError, TypeError) as error:
        raise ArtifactIntegrityError("typed artifact validation failed") from error
    _validate_manifest_contract(manifest)
    _validate_event_stream(manifest, events)
    recomputed = ResultBundle(
        manifest=manifest,
        result=score_trial(manifest, events),
        event_count=len(events),
        events_sha256=content_sha256(events_text),
    )
    if stored != recomputed:
        raise ArtifactIntegrityError("stored result does not match replayed result")
    return recomputed


def _validate_manifest_contract(manifest: TrialManifest) -> None:
    contract = load_apparatus_contract()
    protocol = load_experimental_protocol()
    if (
        manifest.apparatus_contract_version != contract["apparatus_contract_version"]
        or manifest.apparatus_contract_sha256 != apparatus_contract_digest()
        or manifest.scorer_version != SCORER_VERSION
        or manifest.scorer_sha256 != scorer_digest()
        or manifest.software_sha256 != benchmark_software_digest()
        or manifest.experimental_protocol_id != protocol.protocol_id
        or manifest.experimental_protocol_version != protocol.protocol_version
        or manifest.experimental_protocol_sha256 != experimental_protocol_digest()
    ):
        raise ArtifactIntegrityError("artifact apparatus contract is not current")


def _validate_event_stream(
    manifest: TrialManifest, events: list[BenchmarkEvent]
) -> None:
    if not events:
        raise ArtifactIntegrityError("event stream is empty")
    if len({event.event_id for event in events}) != len(events):
        raise ArtifactIntegrityError("event IDs are not unique")
    if [event.sequence for event in events] != list(range(len(events))):
        raise ArtifactIntegrityError("event sequences are not contiguous and ordered")
    if any(event.trial_id != manifest.trial_id for event in events):
        raise ArtifactIntegrityError("event stream contains a cross-trial event")
    if any(
        first.occurred_at > second.occurred_at
        for first, second in pairwise(events)
    ):
        raise ArtifactIntegrityError("event timestamps move backwards")
    event_types = [event.event_type for event in events]
    if (
        event_types[0] is not EventType.TRIAL_CREATED
        or len(event_types) < 3
        or event_types[1] is not EventType.TRIAL_STARTED
        or event_types[-1] is not EventType.TRIAL_ENDED
        or event_types.count(EventType.TRIAL_CREATED) != 1
        or event_types.count(EventType.TRIAL_STARTED) != 1
        or event_types.count(EventType.TRIAL_ENDED) != 1
        or event_types.count(EventType.RESOURCE_LEDGER_FINALIZED) != 1
    ):
        raise ArtifactIntegrityError("trial lifecycle ordering is invalid")
    finalized_index = event_types.index(EventType.RESOURCE_LEDGER_FINALIZED)
    if finalized_index >= len(events) - 1:
        raise ArtifactIntegrityError("resource ledger was not frozen before trial end")
    finalized = events[finalized_index].payload
    if not isinstance(finalized, ResourceLedgerFinalizedPayload):
        raise ArtifactIntegrityError("resource ledger payload is invalid")
    outcome = events[-1].payload
    if not isinstance(outcome, OutcomePayload):
        raise ArtifactIntegrityError("trial end payload is invalid")
    if (
        manifest.status is not TrialStatus.ENDED
        or outcome.termination_reason is not manifest.termination_reason
    ):
        raise ArtifactIntegrityError("manifest and lifecycle outcome disagree")


def export_pair_comparison(
    artifact_root: Path,
    comparison: PairComparison,
) -> Path:
    pair_dir = artifact_root / comparison.pair_id
    pair_dir.mkdir(parents=True, exist_ok=True)
    path = pair_dir / "pair_summary.json"
    _atomic_write(path, canonical_json(comparison) + "\n")
    return path


def _update_pair_evidence_summary(
    artifact_root: Path,
    manifest: TrialManifest,
    artifact_digest: str,
) -> None:
    path = artifact_root / manifest.pair_id / "evidence_summary.json"
    summary = {"pair_id": manifest.pair_id, "trials": []}
    if path.exists():
        try:
            loaded = json.loads(path.read_text())
            if isinstance(loaded, dict) and loaded.get("pair_id") == manifest.pair_id:
                summary = loaded
        except json.JSONDecodeError:
            pass
    trials = [
        item
        for item in summary.get("trials", [])
        if item.get("trial_id") != manifest.trial_id
    ]
    trials.append(
        {
            "trial_id": manifest.trial_id,
            "pair_position": manifest.pair_position,
            "git_commit": manifest.git_commit,
            "git_dirty": manifest.git_dirty,
            "schema_version": manifest.schema_version,
            "apparatus_contract_version": manifest.apparatus_contract_version,
            "artifact_digest": artifact_digest,
        }
    )
    summary["trials"] = sorted(trials, key=lambda item: item["pair_position"])
    _atomic_write(path, json.dumps(summary, sort_keys=True, indent=2) + "\n")


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("x") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
