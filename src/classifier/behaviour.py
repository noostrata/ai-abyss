# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Session-level behavioural analysis for bot detection

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class SessionBehaviour:

    fingerprint: str
    first_seen: float = field(default_factory=time.time)
    request_times: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    paths_visited: list[str] = field(default_factory=list)
    js_beacon_received: bool = False
    css_loaded: bool = False
    images_loaded: bool = False
    cookies_accepted: bool = False
    robots_fetched: bool = False
    robots_respected: bool = True
    total_requests: int = 0

    def record_request(self, path: str, timestamp: float | None = None) -> None:
        ts = timestamp or time.time()
        self.request_times.append(ts)
        self.paths_visited.append(path)
        self.total_requests += 1

    @property
    def request_cadence_variance(self) -> float:
        if len(self.request_times) < 3:
            return 1.0
        intervals = []
        times = list(self.request_times)
        for i in range(1, len(times)):
            intervals.append(times[i] - times[i - 1])
        if not intervals:
            return 1.0
        mean = sum(intervals) / len(intervals)
        if mean == 0:
            return 0.0
        variance = sum((x - mean) ** 2 for x in intervals) / len(intervals)
        # Normalize: humans have variance > 1s typically, bots < 0.1s
        return max(0.0, 1.0 - min(variance, 5.0) / 5.0)

    @property
    def requests_per_second(self) -> float:
        if len(self.request_times) < 2:
            return 0.0
        duration = self.request_times[-1] - self.request_times[0]
        if duration == 0:
            return float(len(self.request_times))
        return len(self.request_times) / duration

    @property
    def path_depth_ratio(self) -> float:
        if not self.paths_visited:
            return 0.0
        deep_paths = [p for p in self.paths_visited if p.count("/") > 3]
        return len(deep_paths) / len(self.paths_visited)


class BehaviourTracker:

    def __init__(self, session_ttl: float = 3600.0) -> None:
        self._sessions: dict[str, SessionBehaviour] = {}
        self._session_ttl = session_ttl

    def get_session(self, fingerprint: str) -> SessionBehaviour:
        self._evict_expired()
        if fingerprint not in self._sessions:
            self._sessions[fingerprint] = SessionBehaviour(fingerprint=fingerprint)
        return self._sessions[fingerprint]

    def record_request(self, fingerprint: str, path: str) -> SessionBehaviour:
        session = self.get_session(fingerprint)
        session.record_request(path)
        return session

    def record_js_beacon(self, fingerprint: str) -> None:
        session = self.get_session(fingerprint)
        session.js_beacon_received = True

    def record_resource_load(self, fingerprint: str, resource_type: str) -> None:
        session = self.get_session(fingerprint)
        if resource_type == "css":
            session.css_loaded = True
        elif resource_type == "image":
            session.images_loaded = True

    def record_robots_fetch(self, fingerprint: str) -> None:
        session = self.get_session(fingerprint)
        session.robots_fetched = True

    def mark_robots_violated(self, fingerprint: str) -> None:
        session = self.get_session(fingerprint)
        session.robots_respected = False

    def score(self, fingerprint: str) -> float:
        session = self.get_session(fingerprint)

        if session.total_requests < 2:
            return 0.0

        score = 0.0

        if not session.js_beacon_received and session.total_requests >= 3:
            score += 0.35

        if not session.css_loaded and not session.images_loaded and session.total_requests >= 5:
            score += 0.15

        score += session.request_cadence_variance * 0.20

        rps = session.requests_per_second
        if rps > 2.0:
            score += min(0.15, (rps - 2.0) / 10.0 * 0.15)

        if session.total_requests >= 10:
            score += session.path_depth_ratio * 0.15

        return min(1.0, score)

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [
            fp
            for fp, s in self._sessions.items()
            if now - s.first_seen > self._session_ttl
        ]
        for fp in expired:
            del self._sessions[fp]
