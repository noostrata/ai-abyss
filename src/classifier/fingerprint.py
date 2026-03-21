# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# JA3/JA4 TLS fingerprint analysis against known bot and browser signatures

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FingerprintMatch:

    matched: bool
    is_bot: bool
    description: str
    confidence: float


class FingerprintAnalyzer:

    def __init__(self, signatures_path: str | Path = "data/ja3_signatures.json") -> None:
        self._bot_sigs: dict[str, dict] = {}
        self._browser_sigs: dict[str, dict] = {}
        self._load_signatures(Path(signatures_path))

    def _load_signatures(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as f:
            data = json.load(f)
        for entry in data.get("known_bots", []):
            self._bot_sigs[entry["ja3"]] = entry
        for entry in data.get("known_browsers", []):
            self._browser_sigs[entry["ja3"]] = entry

    def analyze(self, ja3_hash: str | None) -> FingerprintMatch:
        if not ja3_hash:
            return FingerprintMatch(
                matched=False, is_bot=False, description="no JA3 hash available", confidence=0.0
            )

        if ja3_hash in self._bot_sigs:
            entry = self._bot_sigs[ja3_hash]
            return FingerprintMatch(
                matched=True,
                is_bot=True,
                description=entry["description"],
                confidence=entry.get("confidence", 0.8),
            )

        if ja3_hash in self._browser_sigs:
            entry = self._browser_sigs[ja3_hash]
            return FingerprintMatch(
                matched=True,
                is_bot=False,
                description=entry["description"],
                confidence=entry.get("confidence", 0.9),
            )

        # Unknown fingerprint — mildly suspicious since legitimate browsers have well-known JA3s
        return FingerprintMatch(
            matched=False,
            is_bot=False,
            description=f"unknown JA3: {ja3_hash[:16]}...",
            confidence=0.0,
        )

    def score(self, ja3_hash: str | None) -> float:
        result = self.analyze(ja3_hash)
        if not result.matched and not ja3_hash:
            return 0.0
        if result.is_bot:
            return min(1.0, 0.6 + result.confidence * 0.4)
        if result.matched:
            return 0.0
        return 0.3
