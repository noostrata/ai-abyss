# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Request classification engine — fuses all signal sources into a decision

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from starlette.requests import Request

from src.classifier.behaviour import BehaviourTracker
from src.classifier.fingerprint import FingerprintAnalyzer
from src.classifier.ip_reputation import IPReputationChecker
from src.classifier.signals import Classification, ClassificationResult, Signal, fuse_signals
from src.utils.config import ClassificationConfig
from src.utils.crypto import hash_fingerprint


class ClassificationEngine:

    def __init__(
        self,
        config: ClassificationConfig,
        data_dir: str | Path = "data",
    ) -> None:
        self.config = config
        self._data_dir = Path(data_dir)

        self._fingerprint = FingerprintAnalyzer(self._data_dir / "ja3_signatures.json")
        self._ip_checker = IPReputationChecker(self._data_dir / "ai_crawler_ips.json")
        self._behaviour = BehaviourTracker()

        self._ua_patterns: list[dict[str, str]] = []
        self._load_ua_patterns()

        self._cache: dict[str, tuple[ClassificationResult, float]] = {}

    def _load_ua_patterns(self) -> None:
        ua_path = self._data_dir / "user_agents.json"
        if ua_path.exists():
            with open(ua_path) as f:
                data = json.load(f)
            self._ua_patterns = data.get("known_ai_crawlers", [])

    async def classify(self, request: Request) -> ClassificationResult:
        ip = self._get_client_ip(request)
        ua = request.headers.get("user-agent", "")
        ja3 = request.headers.get("x-ja3-hash", "")
        path = request.url.path
        fingerprint = hash_fingerprint(ip, ua, ja3)

        if path == "/robots.txt":
            self._behaviour.record_robots_fetch(fingerprint)

        # Skip cache during early session phase where new evidence could change the result
        session_data = self._behaviour.get_session(fingerprint)
        session_is_mature = session_data.total_requests >= 5
        cached = self._get_cached(fingerprint)
        if cached is not None and session_is_mature:
            self._behaviour.record_request(fingerprint, path)
            return cached

        session = self._behaviour.record_request(fingerprint, path)

        header_dict: dict[str, str] | None = None
        try:
            header_dict = {k.lower(): v for k, v in request.headers.items()}
        except Exception:
            pass

        signals = self._gather_signals(ip, ua, ja3, path, fingerprint, headers=header_dict)

        # Named AI crawler UA (GPTBot, ClaudeBot, CCBot, etc.) is conclusive evidence
        ua_signal = next((s for s in signals if s.name == "user_agent"), None)
        known_crawler = ua_signal is not None and ua_signal.score >= 0.85

        # Bot fetched robots.txt (which says Disallow: /) and is now crawling other pages
        robots_violated = (
            self.config.robots_txt_override
            and session.robots_fetched
            and session.total_requests >= 2
            and path != "/robots.txt"
        )

        # Bot hasn't even bothered to fetch robots.txt
        robots_ignored = (
            self.config.robots_txt_override
            and session.total_requests >= 3
            and not session.robots_fetched
        )

        robots_override = robots_violated or robots_ignored

        result = fuse_signals(
            signals=signals,
            human_max=self.config.thresholds.human_max,
            compliant_max=self.config.thresholds.compliant_max,
            robots_override=robots_override,
            robots_override_floor=self.config.robots_override_floor,
            known_crawler_floor=0.85 if known_crawler else None,
        )

        self._set_cached(fingerprint, result)
        return result

    @property
    def behaviour_tracker(self) -> BehaviourTracker:
        return self._behaviour

    def get_fingerprint(self, request: Request) -> str:
        ip = self._get_client_ip(request)
        ua = request.headers.get("user-agent", "")
        ja3 = request.headers.get("x-ja3-hash", "")
        return hash_fingerprint(ip, ua, ja3)

    def _gather_signals(
        self,
        ip: str,
        ua: str,
        ja3: str,
        path: str,
        fingerprint: str,
        headers: dict[str, str] | None = None,
    ) -> list[Signal]:
        signals: list[Signal] = []
        weights = self.config.weights

        ua_score, ua_detail = self._score_user_agent(ua)
        signals.append(Signal(
            name="user_agent", score=ua_score, weight=weights.user_agent, detail=ua_detail
        ))

        ip_score, ip_rep = self._ip_checker.score(ip)
        signals.append(Signal(
            name="ip_asn",
            score=ip_score,
            weight=weights.ip_asn,
            detail=f"{ip_rep.org or 'unknown'} ({ip_rep.source})",
        ))

        if ja3:
            tls_score = self._fingerprint.score(ja3)
            signals.append(Signal(
                name="tls_fingerprint",
                score=tls_score,
                weight=weights.tls_fingerprint,
                detail=self._fingerprint.analyze(ja3).description,
            ))

        # Scale behaviour weight by session maturity to avoid diluting strong UA/IP signals early on
        session = self._behaviour.get_session(fingerprint)
        behav_score = self._behaviour.score(fingerprint)
        maturity = min(session.total_requests / 5.0, 1.0)
        behav_weight = weights.behaviour * maturity
        signals.append(Signal(
            name="behaviour",
            score=behav_score,
            weight=behav_weight,
            detail=f"reqs={session.total_requests} maturity={maturity:.1f}",
        ))

        if headers:
            header_score = self.score_headers(headers)
            header_detail = "full header analysis"
        else:
            header_score = self._score_header_heuristics(ua)
            header_detail = "ua-based heuristics"
        signals.append(Signal(
            name="header_anomalies",
            score=header_score,
            weight=weights.header_anomalies,
            detail=header_detail,
        ))

        return signals

    def _score_user_agent(self, ua: str) -> tuple[float, str]:
        if not ua:
            return 0.7, "empty user-agent"

        ua_lower = ua.lower()

        for entry in self._ua_patterns:
            if re.search(entry["name"], ua, re.IGNORECASE):
                return 0.9, f"matched: {entry['name']} ({entry['org']})"

        bot_keywords = ["bot", "crawl", "spider", "scrape", "fetch", "http"]
        for kw in bot_keywords:
            if kw in ua_lower:
                return 0.6, f"contains bot keyword: {kw}"

        if len(ua) < 20:
            return 0.4, "suspiciously short UA"

        return 0.0, "appears legitimate"

    def _score_header_heuristics(self, ua: str) -> float:
        if not ua:
            return 0.6

        browser_indicators = ["Mozilla/", "Chrome/", "Firefox/", "Safari/", "Edge/"]
        has_browser = any(ind in ua for ind in browser_indicators)

        if not has_browser:
            return 0.5

        return 0.0

    def score_headers(self, headers: dict[str, str]) -> float:
        score = 0.0
        checks = 0

        if "accept-language" not in headers:
            score += 0.3
        checks += 1

        sec_fetch_headers = ["sec-fetch-mode", "sec-fetch-site", "sec-fetch-dest"]
        missing_sec = sum(1 for h in sec_fetch_headers if h not in headers)
        if missing_sec == len(sec_fetch_headers):
            score += 0.3
        checks += 1

        accept = headers.get("accept", "")
        if not accept or accept == "*/*":
            score += 0.2
        checks += 1

        if "referer" not in headers:
            score += 0.1
        checks += 1

        return min(1.0, score) if checks > 0 else 0.0

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "0.0.0.0"

    def _get_cached(self, fingerprint: str) -> ClassificationResult | None:
        if fingerprint in self._cache:
            result, ts = self._cache[fingerprint]
            if time.time() - ts < self.config.cache_ttl_seconds:
                return result
            del self._cache[fingerprint]
        return None

    def _set_cached(self, fingerprint: str, result: ClassificationResult) -> None:
        if len(self._cache) > 10000:
            cutoff = time.time() - self.config.cache_ttl_seconds
            self._cache = {
                k: (v, ts) for k, (v, ts) in self._cache.items() if ts > cutoff
            }
        self._cache[fingerprint] = (result, time.time())
