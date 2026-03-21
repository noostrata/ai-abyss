# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Canary token generation and tracking for injection attribution.
from __future__ import annotations

from src.utils.crypto import generate_canary_token, generate_random_token


def make_canary(page_path: str, vector: str, session_id: str) -> str:
    return generate_canary_token(page_path, vector, session_id)


def make_secondary_canary() -> str:
    return f"PW-{generate_random_token(8)}"
