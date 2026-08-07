"""Offline contract, documentation, matrix, and evidence drift checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from src.benchmark.apparatus import (
    apparatus_contract_digest,
    apparatus_contract_errors,
    benchmark_software_digest,
    load_apparatus_contract,
)
from src.benchmark.enums import CallAttemptState, EventType, TerminationReason
from src.benchmark.models import (
    SCHEMA_VERSION,
    ResourceLedger,
    TrajectoryScore,
    UtilityScore,
    content_sha256,
)
from src.benchmark.protocol import (
    GENERATED_MATRIX_PATH,
    experimental_protocol_digest,
    generated_matrix_text,
    load_experimental_protocol,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
DATA_DICTIONARY_PATH = REPOSITORY_ROOT / "docs" / "data-dictionary.md"
EVIDENCE_PATH = (
    REPOSITORY_ROOT / "docs" / "evidence" / "unpaid-qualification.json"
)
GENERAL_DOCUMENTS = (
    REPOSITORY_ROOT / "README.md",
    REPOSITORY_ROOT / "agent.md",
    REPOSITORY_ROOT / "AGENTS.md",
    REPOSITORY_ROOT / "issues.md",
    REPOSITORY_ROOT / "next_steps.md",
    REPOSITORY_ROOT / "plan.md",
    REPOSITORY_ROOT / "existing benchmark review.md",
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HARDCODED_PASS_COUNT = re.compile(r"\b\d+\s+(?:tests?\s+)?passed\b", re.IGNORECASE)


def drift_errors(*, require_evidence: bool = False) -> list[str]:
    errors = apparatus_contract_errors()
    try:
        protocol = load_experimental_protocol()
    except ValueError as error:
        errors.append(f"experimental protocol drift: {error}")
        protocol = None

    if GENERATED_MATRIX_PATH.read_text() != generated_matrix_text(protocol):
        errors.append("generated calibration matrix differs from the protocol")

    errors.extend(_documentation_link_errors())
    errors.extend(_data_dictionary_errors())
    errors.extend(_general_documentation_errors())
    errors.extend(_evidence_errors(required=require_evidence))
    return errors


def assert_no_drift(*, require_evidence: bool = False) -> None:
    errors = drift_errors(require_evidence=require_evidence)
    if errors:
        raise ValueError("repository drift detected:\n- " + "\n- ".join(errors))


def _documentation_link_errors() -> list[str]:
    errors: list[str] = []
    documents = sorted(REPOSITORY_ROOT.rglob("*.md"))
    for document in documents:
        if ".git" in document.parts:
            continue
        for raw_target in MARKDOWN_LINK.findall(document.read_text()):
            stripped = raw_target.strip()
            if stripped.startswith("<") and ">" in stripped:
                target = stripped[1 : stripped.index(">")]
            else:
                target = stripped.split(maxsplit=1)[0]
            if not target or target.startswith("#"):
                continue
            parts = urlsplit(target)
            if parts.scheme or parts.netloc:
                continue
            relative = unquote(parts.path)
            if not relative:
                continue
            resolved = (document.parent / relative).resolve()
            try:
                resolved.relative_to(REPOSITORY_ROOT.resolve())
            except ValueError:
                errors.append(
                    f"{document.relative_to(REPOSITORY_ROOT)} links outside the repository: {target}"
                )
                continue
            if not resolved.exists():
                errors.append(
                    f"{document.relative_to(REPOSITORY_ROOT)} has a missing link target: {target}"
                )
    return errors


def _data_dictionary_errors() -> list[str]:
    if not DATA_DICTIONARY_PATH.exists():
        return ["data dictionary is missing"]
    text = DATA_DICTIONARY_PATH.read_text()
    required_terms = {
        *(item.value for item in EventType),
        *(item.value for item in TerminationReason),
        *(item.value for item in CallAttemptState),
        *ResourceLedger.model_fields,
        *TrajectoryScore.model_fields,
        *UtilityScore.model_fields,
        *load_experimental_protocol().censoring_policy,
    }
    missing = sorted(term for term in required_terms if f"`{term}`" not in text)
    return [f"data dictionary omits `{term}`" for term in missing]


def _general_documentation_errors() -> list[str]:
    errors: list[str] = []
    for path in GENERAL_DOCUMENTS:
        if not path.exists():
            errors.append(f"required general document is missing: {path.name}")
            continue
        if HARDCODED_PASS_COUNT.search(path.read_text()):
            errors.append(f"{path.name} contains a brittle hard-coded passing-test count")
    agents_text = (REPOSITORY_ROOT / "AGENTS.md").read_text()
    if "agent.md" not in agents_text:
        errors.append("AGENTS.md does not point agents to agent.md")
    return errors


def _evidence_errors(*, required: bool) -> list[str]:
    if not required:
        return []
    if not EVIDENCE_PATH.exists():
        return ["unpaid qualification evidence is missing"]
    try:
        evidence = json.loads(EVIDENCE_PATH.read_text())
    except json.JSONDecodeError:
        return ["unpaid qualification evidence is not valid JSON"]
    expected = {
        "evidence_schema_version",
        "status",
        "tested_commit",
        "tested_worktree_clean",
        "generated_at",
        "python_version",
        "dependency_lock_sha256",
        "schema_version",
        "apparatus_contract_version",
        "apparatus_contract_sha256",
        "experimental_protocol_id",
        "experimental_protocol_version",
        "experimental_protocol_sha256",
        "scorer_version",
        "scorer_sha256",
        "benchmark_software_sha256",
        "commands",
        "checks",
        "network_audit",
        "hosted_requests",
        "credential_loaded",
        "limitations",
    }
    if set(evidence) != expected:
        return ["unpaid qualification evidence has an unexpected field set"]
    from src.benchmark.scoring import SCORER_VERSION, scorer_digest

    contract = load_apparatus_contract()
    protocol = load_experimental_protocol()
    current_values = {
        "schema_version": SCHEMA_VERSION,
        "apparatus_contract_version": contract["apparatus_contract_version"],
        "apparatus_contract_sha256": apparatus_contract_digest(),
        "experimental_protocol_id": protocol.protocol_id,
        "experimental_protocol_version": protocol.protocol_version,
        "experimental_protocol_sha256": experimental_protocol_digest(),
        "scorer_version": SCORER_VERSION,
        "scorer_sha256": scorer_digest(),
        "benchmark_software_sha256": benchmark_software_digest(),
        "dependency_lock_sha256": content_sha256(
            (REPOSITORY_ROOT / "uv.lock").read_bytes()
        ),
    }
    errors = [
        f"unpaid qualification evidence has drifted field: {field}"
        for field, current in current_values.items()
        if evidence.get(field) != current
    ]
    if required and evidence.get("status") != "passed":
        errors.append("unpaid qualification evidence is not passed")
    if evidence.get("tested_worktree_clean") is not True:
        errors.append("unpaid qualification did not test a clean worktree")
    if not re.fullmatch(r"[0-9a-f]{40}", str(evidence.get("tested_commit", ""))):
        errors.append("unpaid qualification tested_commit is not an exact commit")
    if evidence.get("hosted_requests") != 0:
        errors.append("unpaid qualification reports a hosted request")
    if evidence.get("credential_loaded") is not False:
        errors.append("unpaid qualification reports a credential load")
    network = evidence.get("network_audit")
    if not isinstance(network, dict) or network.get("external_destinations") != []:
        errors.append("unpaid qualification network audit is not loopback-only")
    required_checks = {
        *PRIMARY_CHECK_NAMES,
        "clean_checkout",
    }
    checks = evidence.get("checks")
    if not isinstance(checks, dict) or not required_checks.issubset(checks):
        errors.append("unpaid qualification omits required checks")
    return errors


PRIMARY_CHECK_NAMES = {
    "lock",
    "sync",
    "drift",
    "ruff",
    "full_suite",
    "budget_and_containment",
    "provider_faults_and_concurrency",
    "artifact_corruption",
    "mock_rehearsal",
    "fake_provider_rehearsal",
}
