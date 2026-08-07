"""Generate a sanitized, commit-bound unpaid qualification report."""

from __future__ import annotations

import json
import os
import platform
import shlex
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from src.benchmark.apparatus import (
    apparatus_contract_digest,
    benchmark_software_digest,
    load_apparatus_contract,
)
from src.benchmark.drift import assert_no_drift
from src.benchmark.models import SCHEMA_VERSION, content_sha256
from src.benchmark.protocol import (
    experimental_protocol_digest,
    load_experimental_protocol,
)
from src.benchmark.scoring import SCORER_VERSION, scorer_digest

REPOSITORY_ROOT = Path(__file__).parents[2]
DEFAULT_EVIDENCE_PATH = (
    REPOSITORY_ROOT / "docs" / "evidence" / "unpaid-qualification.json"
)

PRIMARY_COMMANDS = {
    "lock": ["uv", "lock", "--locked"],
    "sync": ["uv", "sync", "--locked", "--extra", "dev"],
    "drift": ["uv", "run", "ai-abyss-benchmark", "check-drift"],
    "ruff": ["uv", "run", "ruff", "check", "src", "tests"],
    "full_suite": ["uv", "run", "pytest", "-q"],
    "budget_and_containment": [
        "uv",
        "run",
        "pytest",
        "-q",
        "tests/benchmark/test_scaffold_egress_budget.py",
    ],
    "provider_faults_and_concurrency": [
        "uv",
        "run",
        "pytest",
        "-q",
        "tests/benchmark/test_providers_runner.py",
        "-k",
        (
            "boundary or timeout or disconnect or malformed or identity or "
            "billing or cancel or concurrent"
        ),
    ],
    "artifact_corruption": [
        "uv",
        "run",
        "pytest",
        "-q",
        "tests/benchmark/test_artifact_integrity.py",
    ],
    "mock_rehearsal": [
        "uv",
        "run",
        "ai-abyss-benchmark",
        "mock-rehearsal",
    ],
    "fake_provider_rehearsal": [
        "uv",
        "run",
        "ai-abyss-benchmark",
        "fake-provider-rehearsal",
    ],
}

CLEAN_CHECKOUT_COMMANDS = {
    name: PRIMARY_COMMANDS[name]
    for name in ("sync", "drift", "ruff", "full_suite", "mock_rehearsal", "fake_provider_rehearsal")
}


def run_unpaid_qualification(
    output_path: Path = DEFAULT_EVIDENCE_PATH,
) -> dict:
    commit, dirty = _git_state(REPOSITORY_ROOT)
    if dirty:
        raise ValueError("unpaid qualification requires a clean worktree")
    if output_path.exists():
        raise ValueError("remove or archive the prior qualification report first")

    checks = {
        name: _run_checked(command, REPOSITORY_ROOT)
        for name, command in PRIMARY_COMMANDS.items()
    }
    mock_output = json.loads(checks["mock_rehearsal"].pop("stdout"))
    fake_output = json.loads(checks["fake_provider_rehearsal"].pop("stdout"))
    if (
        mock_output["hosted_requests"] != 0
        or fake_output["hosted_requests"] != 0
        or fake_output["credential_loaded"] is not False
        or fake_output["external_destinations"]
        or fake_output["transport_requests"]
        != fake_output["server_received_requests"]
        or fake_output["transport_requests"] != fake_output["reconciled_calls"]
        or fake_output["trials"] != 8
    ):
        raise RuntimeError("unpaid rehearsal evidence did not satisfy the safety gate")
    checks["mock_rehearsal"]["pairs"] = len(mock_output["pairs"])
    checks["fake_provider_rehearsal"]["pairs"] = len(fake_output["pairs"])
    checks["fake_provider_rehearsal"]["trials"] = fake_output["trials"]

    checks["clean_checkout"] = _verify_clean_checkout(commit)
    final_commit, final_dirty = _git_state(REPOSITORY_ROOT)
    if final_commit != commit or final_dirty:
        raise RuntimeError("worktree changed during unpaid qualification")

    contract = load_apparatus_contract()
    protocol = load_experimental_protocol()
    evidence = {
        "evidence_schema_version": "1.0.0",
        "status": "passed",
        "tested_commit": commit,
        "tested_worktree_clean": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "dependency_lock_sha256": content_sha256(
            (REPOSITORY_ROOT / "uv.lock").read_bytes()
        ),
        "schema_version": SCHEMA_VERSION,
        "apparatus_contract_version": contract["apparatus_contract_version"],
        "apparatus_contract_sha256": apparatus_contract_digest(),
        "experimental_protocol_id": protocol.protocol_id,
        "experimental_protocol_version": protocol.protocol_version,
        "experimental_protocol_sha256": experimental_protocol_digest(),
        "scorer_version": SCORER_VERSION,
        "scorer_sha256": scorer_digest(),
        "benchmark_software_sha256": benchmark_software_digest(),
        "commands": [
            shlex.join(command) for command in PRIMARY_COMMANDS.values()
        ],
        "checks": checks,
        "network_audit": {
            "provider_transport": fake_output["transport"],
            "attempted_destination_classes": ["loopback"],
            "external_destinations": [],
            "transport_requests": fake_output["transport_requests"],
            "server_received_requests": fake_output["server_received_requests"],
            "reconciled_calls": fake_output["reconciled_calls"],
        },
        "hosted_requests": 0,
        "credential_loaded": False,
        "limitations": [
            "No hosted model or real credential was used.",
            "The exact paid model, provider route, and current price snapshot remain unselected.",
            "The matrix calibrates one dynamic task and one scaffold; it does not estimate population susceptibility or rank models.",
            "CPU, memory, connection, and file-descriptor attribution remain uninstrumented and null.",
            "Recognition has a blinded rubric but no real-model human-validation evidence.",
            "Local artifact hashes are not an independent public signature or transparency-log commitment.",
            "The inherited public honeypot remains outside this qualification and is not production-ready.",
        ],
    }
    _atomic_write_json(output_path, evidence)
    assert_no_drift(require_evidence=True)
    return evidence


def _run_checked(command: list[str], cwd: Path) -> dict:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    combined = completed.stdout + completed.stderr
    if completed.returncode != 0:
        raise RuntimeError(
            f"qualification command failed: {shlex.join(command)}\n{combined[-4000:]}"
        )
    return {
        "status": "passed",
        "command": shlex.join(command),
        "output_sha256": content_sha256(combined),
        "stdout": completed.stdout,
    }


def _verify_clean_checkout(commit: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="ai-abyss-qualification-") as temporary:
        checkout = Path(temporary) / "repository"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-hardlinks",
                str(REPOSITORY_ROOT),
                str(checkout),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        actual = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=checkout,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if actual != commit:
            raise RuntimeError("clean-checkout verification used the wrong commit")
        results = {
            name: _run_checked(command, checkout)
            for name, command in CLEAN_CHECKOUT_COMMANDS.items()
        }
        for result in results.values():
            result.pop("stdout")
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=checkout,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if dirty:
            raise RuntimeError("documented commands dirtied a clean checkout")
        return {
            "status": "passed",
            "tested_commit": commit,
            "commands": results,
            "worktree_clean_after_commands": True,
        }


def _git_state(root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return commit, dirty


def _atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    data = json.dumps(value, sort_keys=True, indent=2) + "\n"
    try:
        with temporary.open("x") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
