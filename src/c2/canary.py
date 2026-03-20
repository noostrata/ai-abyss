"""Canary token generation and tracking for injection attribution."""

from __future__ import annotations

from src.utils.crypto import generate_canary_token, generate_random_token


def make_canary(page_path: str, vector: str, session_id: str) -> str:
    """Generate a deterministic canary token for a specific injection instance."""
    return generate_canary_token(page_path, vector, session_id)


def make_secondary_canary() -> str:
    """Generate a random secondary canary for C2 response tracking."""
    return f"PW-{generate_random_token(8)}"


def decode_canary(token: str) -> dict[str, str]:
    """Extract metadata from a canary token.

    Since canaries are HMAC-based, we can't decode them — we can only verify.
    The actual lookup happens in the telemetry DB by canary_token.
    This returns what we can infer from the token format.
    """
    return {
        "token": token,
        "length": str(len(token)),
        "is_secondary": token.startswith("PW-"),
    }
