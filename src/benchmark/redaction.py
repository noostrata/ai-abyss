"""Deterministic recursive redaction for benchmark evidence."""

from __future__ import annotations

from pydantic import BaseModel

from src.benchmark.models import content_sha256

REDACTION_VERSION = "recursive-redaction-v1"


def redact_sensitive(value, sensitive_values: set[str]):
    """Replace every registered secret substring at any JSON-compatible depth."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        return {
            str(key): redact_sensitive(item, sensitive_values)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item, sensitive_values) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive(item, sensitive_values) for item in value]
    if isinstance(value, str):
        result = value
        for secret in sorted((item for item in sensitive_values if item), key=len, reverse=True):
            result = result.replace(
                secret,
                f"[REDACTED:sha256:{content_sha256(secret)}]",
            )
        return result
    return value
