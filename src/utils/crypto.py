# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Token generation, hashing, and cryptographic utilities

from __future__ import annotations

import hashlib
import hmac
import secrets
import time


# Stable secret for deterministic canary generation per deployment
_DEPLOYMENT_SECRET: str | None = None


def set_deployment_secret(secret: str) -> None:
    global _DEPLOYMENT_SECRET
    _DEPLOYMENT_SECRET = secret


def _get_secret() -> str:
    if _DEPLOYMENT_SECRET is None:
        raise RuntimeError("Deployment secret not initialized. Call set_deployment_secret() first.")
    return _DEPLOYMENT_SECRET


def generate_canary_token(page_path: str, vector: str, session_id: str) -> str:
    secret = _get_secret()
    msg = f"{page_path}:{vector}:{session_id}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()[:24]


def generate_session_id() -> str:
    return secrets.token_hex(16)


def generate_random_token(length: int = 16) -> str:
    return secrets.token_hex(length)


def deterministic_seed(path: str) -> int:
    return int(hashlib.sha256(path.encode()).hexdigest(), 16)


def hash_fingerprint(ip: str, user_agent: str, ja3: str = "") -> str:
    raw = f"{ip}|{user_agent}|{ja3}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def timestamp_ms() -> int:
    return int(time.time() * 1000)
