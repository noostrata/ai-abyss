# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# SQLite schema management and query helpers for telemetry

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    ip TEXT NOT NULL,
    asn TEXT,
    user_agent TEXT,
    ja3_hash TEXT,
    path TEXT NOT NULL,
    classification TEXT NOT NULL,
    hostility_score REAL NOT NULL,
    kill_chain TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL UNIQUE,
    first_seen DATETIME NOT NULL,
    last_seen DATETIME NOT NULL,
    pages_fetched INTEGER NOT NULL DEFAULT 0,
    tarpit_depth INTEGER NOT NULL DEFAULT 0,
    robots_checked BOOLEAN NOT NULL DEFAULT 0,
    robots_respected BOOLEAN NOT NULL DEFAULT 0,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS injections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_token TEXT NOT NULL UNIQUE,
    session_id INTEGER REFERENCES sessions(id),
    vector TEXT NOT NULL,
    payload_type TEXT NOT NULL,
    page_path TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS callbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_token TEXT NOT NULL,
    injection_id INTEGER REFERENCES injections(id),
    timestamp DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    headers TEXT,
    ip TEXT,
    asn TEXT,
    secondary_canary_served TEXT,
    chain_confirmed BOOLEAN NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_requests_ip ON requests(ip);
CREATE INDEX IF NOT EXISTS idx_requests_classification ON requests(classification);
CREATE INDEX IF NOT EXISTS idx_sessions_fingerprint ON sessions(fingerprint);
CREATE INDEX IF NOT EXISTS idx_injections_canary ON injections(canary_token);
CREATE INDEX IF NOT EXISTS idx_callbacks_canary ON callbacks(canary_token);
"""


class TelemetryDB:

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    async def log_request(
        self,
        ip: str,
        path: str,
        classification: str,
        hostility_score: float,
        user_agent: str | None = None,
        asn: str | None = None,
        ja3_hash: str | None = None,
        kill_chain: str | None = None,
    ) -> int:
        cursor = await self.db.execute(
            """INSERT INTO requests (ip, asn, user_agent, ja3_hash, path, classification, hostility_score, kill_chain)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ip, asn, user_agent, ja3_hash, path, classification, hostility_score, kill_chain),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def upsert_session(
        self,
        fingerprint: str,
        robots_checked: bool = False,
        robots_respected: bool = False,
        user_agent: str | None = None,
    ) -> int:
        now = datetime.now(UTC).isoformat()
        cursor = await self.db.execute(
            """UPDATE sessions
               SET last_seen = ?, pages_fetched = pages_fetched + 1,
                   robots_checked = robots_checked OR ?, robots_respected = robots_respected OR ?,
                   user_agent = COALESCE(?, user_agent)
               WHERE fingerprint = ?""",
            (now, robots_checked, robots_respected, user_agent, fingerprint),
        )
        if cursor.rowcount == 0:
            cursor = await self.db.execute(
                """INSERT INTO sessions (fingerprint, first_seen, last_seen, pages_fetched, robots_checked, robots_respected, user_agent)
                   VALUES (?, ?, ?, 1, ?, ?, ?)""",
                (fingerprint, now, now, robots_checked, robots_respected, user_agent),
            )
        await self.db.commit()
        row = await self.db.execute_fetchall(
            "SELECT id FROM sessions WHERE fingerprint = ?", (fingerprint,)
        )
        return row[0][0]

    async def update_tarpit_depth(self, fingerprint: str, depth: int) -> None:
        await self.db.execute(
            "UPDATE sessions SET tarpit_depth = MAX(tarpit_depth, ?) WHERE fingerprint = ?",
            (depth, fingerprint),
        )
        await self.db.commit()

    async def mark_robots_checked(self, fingerprint: str, respected: bool) -> None:
        await self.db.execute(
            "UPDATE sessions SET robots_checked = 1, robots_respected = ? WHERE fingerprint = ?",
            (respected, fingerprint),
        )
        await self.db.commit()

    async def log_injection(
        self,
        canary_token: str,
        session_id: int,
        vector: str,
        payload_type: str,
        page_path: str,
    ) -> int:
        cursor = await self.db.execute(
            """INSERT OR IGNORE INTO injections (canary_token, session_id, vector, payload_type, page_path)
               VALUES (?, ?, ?, ?, ?)""",
            (canary_token, session_id, vector, payload_type, page_path),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def log_callback(
        self,
        canary_token: str,
        ip: str,
        headers: dict | None = None,
        asn: str | None = None,
        secondary_canary: str | None = None,
    ) -> int:
        rows = await self.db.execute_fetchall(
            "SELECT id FROM injections WHERE canary_token = ?", (canary_token,)
        )
        injection_id = rows[0][0] if rows else None

        cursor = await self.db.execute(
            """INSERT INTO callbacks (canary_token, injection_id, ip, asn, headers, secondary_canary_served)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                canary_token,
                injection_id,
                ip,
                asn,
                json.dumps(headers) if headers else None,
                secondary_canary,
            ),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def get_stats(self) -> dict:
        total = await self.db.execute_fetchall("SELECT COUNT(*) FROM requests")
        by_class = await self.db.execute_fetchall(
            "SELECT classification, COUNT(*) FROM requests GROUP BY classification"
        )
        injection_count = await self.db.execute_fetchall("SELECT COUNT(*) FROM injections")
        callback_count = await self.db.execute_fetchall("SELECT COUNT(*) FROM callbacks")
        active_sessions = await self.db.execute_fetchall(
            """SELECT COUNT(*) FROM sessions
               WHERE last_seen > datetime('now', '-1 hour')"""
        )
        return {
            "total_requests": total[0][0],
            "by_classification": {row[0]: row[1] for row in by_class},
            "total_injections": injection_count[0][0],
            "total_callbacks": callback_count[0][0],
            "active_sessions_1h": active_sessions[0][0],
        }

    async def get_sessions(self, limit: int = 50) -> list[dict]:
        rows = await self.db.execute_fetchall(
            """SELECT id, fingerprint, first_seen, last_seen, pages_fetched,
                      tarpit_depth, robots_checked, robots_respected, user_agent
               FROM sessions ORDER BY last_seen DESC LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in rows]

    async def get_injections(self, limit: int = 100) -> list[dict]:
        rows = await self.db.execute_fetchall(
            """SELECT i.*, COUNT(c.id) as callback_count
               FROM injections i LEFT JOIN callbacks c ON c.canary_token = i.canary_token
               GROUP BY i.id ORDER BY i.created_at DESC LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in rows]

    async def get_callbacks(self, limit: int = 100) -> list[dict]:
        rows = await self.db.execute_fetchall(
            "SELECT * FROM callbacks ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in rows]

    async def get_top_user_agents(self, limit: int = 10) -> list[dict]:
        rows = await self.db.execute_fetchall(
            """SELECT user_agent, COUNT(*) as request_count,
                      SUM(CASE WHEN classification = 'HOSTILE_BOT' THEN 1 ELSE 0 END) as hostile_count,
                      SUM(CASE WHEN classification = 'HUMAN' THEN 1 ELSE 0 END) as human_count,
                      ROUND(AVG(hostility_score), 2) as avg_score
               FROM requests
               WHERE user_agent IS NOT NULL AND user_agent != ''
               GROUP BY user_agent
               ORDER BY request_count DESC LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in rows]

    async def get_injection_success_rate(self) -> list[dict]:
        rows = await self.db.execute_fetchall(
            """SELECT i.vector, i.payload_type,
                      COUNT(DISTINCT i.id) as total_injections,
                      COUNT(DISTINCT c.id) as callbacks_received,
                      ROUND(CAST(COUNT(DISTINCT c.id) AS REAL) / MAX(COUNT(DISTINCT i.id), 1) * 100, 2) as success_rate
               FROM injections i LEFT JOIN callbacks c ON c.canary_token = i.canary_token
               GROUP BY i.vector, i.payload_type"""
        )
        return [dict(row) for row in rows]
