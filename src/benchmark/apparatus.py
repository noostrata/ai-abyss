"""Versioned machine-readable authority for benchmark apparatus semantics."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.benchmark.enums import AgentActionKind, Condition, EventType, TerminationReason
from src.benchmark.models import SCHEMA_VERSION, content_sha256

APPARATUS_CONTRACT_PATH = Path(__file__).parents[2] / "protocol" / "apparatus-v1.json"


@lru_cache(maxsize=1)
def load_apparatus_contract() -> dict:
    contract = json.loads(APPARATUS_CONTRACT_PATH.read_text())
    required_top_level = {
        "action_kinds",
        "apparatus_contract_version",
        "conditions",
        "deprecated_events_pending_removal",
        "event_evidence",
        "event_types",
        "evidence_levels",
        "lifecycle",
        "primary_outcomes",
        "required_events_pending_implementation",
        "resource_ledger",
        "schema_version",
        "termination_reasons",
    }
    if set(contract) != required_top_level:
        raise ValueError("apparatus contract has an unexpected top-level field set")
    return contract


def apparatus_contract_digest() -> str:
    return content_sha256(APPARATUS_CONTRACT_PATH.read_bytes())


def benchmark_software_digest() -> str:
    """Digest the benchmark implementation and its configuration contract."""

    root = Path(__file__).parents[2]
    paths = sorted((root / "src" / "benchmark").rglob("*.py"))
    paths.append(root / "src" / "utils" / "config.py")
    material = bytearray()
    for path in paths:
        material.extend(str(path.relative_to(root)).encode())
        material.extend(b"\0")
        material.extend(path.read_bytes())
        material.extend(b"\0")
    return content_sha256(bytes(material))


def apparatus_contract_errors() -> list[str]:
    contract = load_apparatus_contract()
    errors: list[str] = []
    if contract["schema_version"] != SCHEMA_VERSION:
        errors.append("apparatus schema_version differs from code schema version")
    if set(contract["action_kinds"]) != {item.value for item in AgentActionKind}:
        errors.append("apparatus action vocabulary differs from code")
    if set(contract["conditions"]) != {item.value for item in Condition}:
        errors.append("apparatus condition vocabulary differs from code")
    if set(contract["termination_reasons"]) != {item.value for item in TerminationReason}:
        errors.append("apparatus termination vocabulary differs from code")
    required_events = set(contract["event_types"])
    pending_events = set(contract["required_events_pending_implementation"])
    deprecated_events = set(contract["deprecated_events_pending_removal"])
    implemented_events = {item.value for item in EventType}
    if pending_events - required_events:
        errors.append("pending event types must be required by the apparatus")
    if required_events - pending_events - implemented_events:
        errors.append("apparatus requires event types not implemented in code")
    if implemented_events - required_events - deprecated_events:
        errors.append("code implements undeclared event types")
    if set(contract["event_evidence"]) != required_events:
        errors.append("every required event needs exactly one evidence definition")
    return errors
