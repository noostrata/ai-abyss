"""Append-only SQLite storage isolated from legacy honeypot telemetry."""

from __future__ import annotations

import asyncio
import hmac
import secrets
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.benchmark.models import BenchmarkEvent, ResultBundle, TrialManifest, canonical_json

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS benchmark_trials (
    trial_id TEXT PRIMARY KEY,
    model_namespace TEXT NOT NULL,
    condition TEXT NOT NULL,
    task_id TEXT NOT NULL,
    seed INTEGER NOT NULL,
    status TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benchmark_events (
    event_id TEXT PRIMARY KEY,
    trial_id TEXT NOT NULL REFERENCES benchmark_trials(trial_id),
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(trial_id, sequence)
);
CREATE TABLE IF NOT EXISTS benchmark_page_exposures (
    event_id TEXT PRIMARY KEY REFERENCES benchmark_events(event_id),
    trial_id TEXT NOT NULL REFERENCES benchmark_trials(trial_id),
    node_id TEXT NOT NULL,
    path TEXT NOT NULL,
    depth INTEGER NOT NULL,
    vector TEXT,
    payload_id TEXT,
    content_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benchmark_agent_actions (
    event_id TEXT PRIMARY KEY REFERENCES benchmark_events(event_id),
    trial_id TEXT NOT NULL REFERENCES benchmark_trials(trial_id),
    action_type TEXT NOT NULL,
    action_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benchmark_model_calls (
    event_id TEXT PRIMARY KEY REFERENCES benchmark_events(event_id),
    trial_id TEXT NOT NULL REFERENCES benchmark_trials(trial_id),
    call_id TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    usage_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benchmark_callback_tokens (
    token_id TEXT PRIMARY KEY,
    trial_id TEXT NOT NULL REFERENCES benchmark_trials(trial_id),
    condition TEXT NOT NULL,
    exposure_id TEXT NOT NULL,
    vector TEXT NOT NULL,
    expected_event_type TEXT NOT NULL,
    expected_secret_digest TEXT NOT NULL,
    token_digest TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT
);
CREATE TABLE IF NOT EXISTS benchmark_callback_events (
    event_id TEXT PRIMARY KEY REFERENCES benchmark_events(event_id),
    trial_id TEXT NOT NULL REFERENCES benchmark_trials(trial_id),
    token_id TEXT NOT NULL REFERENCES benchmark_callback_tokens(token_id),
    event_kind TEXT NOT NULL,
    matched_expected_secret INTEGER
);
CREATE TABLE IF NOT EXISTS benchmark_outcomes (
    trial_id TEXT PRIMARY KEY REFERENCES benchmark_trials(trial_id),
    result_json TEXT NOT NULL,
    artifact_path TEXT,
    created_at TEXT NOT NULL
);
"""


class BenchmarkDB:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.executescript(SCHEMA)
        columns_cursor = await self.connection.execute("PRAGMA table_info(benchmark_trials)")
        columns = {row["name"] for row in await columns_cursor.fetchall()}
        if "model_namespace" not in columns:
            await self.connection.execute(
                "ALTER TABLE benchmark_trials ADD COLUMN model_namespace TEXT"
            )
            await self.connection.execute(
                "UPDATE benchmark_trials SET model_namespace = trial_id "
                "WHERE model_namespace IS NULL"
            )
        await self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_benchmark_trials_namespace "
            "ON benchmark_trials(model_namespace)"
        )
        await self.connection.commit()

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            self.connection = None

    def _connection(self) -> aiosqlite.Connection:
        if self.connection is None:
            raise RuntimeError("benchmark database is not connected")
        return self.connection

    async def create_trial(
        self, manifest: TrialManifest, lifecycle_event: BenchmarkEvent | None = None
    ) -> None:
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                await connection.execute(
                    """INSERT INTO benchmark_trials
                    (trial_id, model_namespace, condition, task_id, seed, status,
                     manifest_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        manifest.trial_id,
                        manifest.model_namespace,
                        manifest.condition.value,
                        manifest.task_id,
                        manifest.seed,
                        manifest.status.value,
                        canonical_json(manifest),
                        manifest.created_at.isoformat(),
                    ),
                )
                if lifecycle_event is not None:
                    await self._insert_event_locked(connection, lifecycle_event)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    async def get_trial(self, trial_id: str) -> TrialManifest | None:
        cursor = await self._connection().execute(
            "SELECT manifest_json FROM benchmark_trials WHERE trial_id = ?", (trial_id,)
        )
        row = await cursor.fetchone()
        return TrialManifest.model_validate_json(row["manifest_json"]) if row else None

    async def trials_for_model_namespace(self, model_namespace: str) -> list[TrialManifest]:
        cursor = await self._connection().execute(
            "SELECT manifest_json FROM benchmark_trials WHERE model_namespace = ? "
            "ORDER BY created_at DESC",
            (model_namespace,),
        )
        rows = await cursor.fetchall()
        manifests = [
            TrialManifest.model_validate_json(row["manifest_json"])
            for row in rows
        ]
        return manifests

    async def update_trial(
        self,
        manifest: TrialManifest,
        lifecycle_event: BenchmarkEvent | None = None,
        *,
        expected_status: str,
    ) -> None:
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                cursor = await connection.execute(
                    """UPDATE benchmark_trials SET status = ?, model_namespace = ?, manifest_json = ?
                    WHERE trial_id = ? AND status = ?""",
                    (
                        manifest.status.value,
                        manifest.model_namespace,
                        canonical_json(manifest),
                        manifest.trial_id,
                        expected_status,
                    ),
                )
                if cursor.rowcount != 1:
                    exists = await connection.execute(
                        "SELECT 1 FROM benchmark_trials WHERE trial_id = ?",
                        (manifest.trial_id,),
                    )
                    if await exists.fetchone() is None:
                        raise KeyError(f"unknown trial: {manifest.trial_id}")
                    raise RuntimeError(
                        f"trial lifecycle compare-and-swap failed: {expected_status}"
                    )
                if lifecycle_event is not None:
                    await self._insert_event_locked(connection, lifecycle_event)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    async def append_event(self, event: BenchmarkEvent) -> bool:
        """Append once; retrying the same event ID is an idempotent no-op."""
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                inserted = await self._insert_event_locked(connection, event)
                await connection.commit()
                return inserted
            except Exception:
                await connection.rollback()
                raise

    async def record_page_event(self, event: BenchmarkEvent) -> bool:
        from src.benchmark.models import PageServedPayload

        if not isinstance(event.payload, PageServedPayload):
            raise TypeError("page event requires PageServedPayload")
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                if not await self._insert_event_locked(connection, event):
                    await connection.rollback()
                    return False
                payload = event.payload
                await connection.execute(
                    """INSERT INTO benchmark_page_exposures
                    (event_id, trial_id, node_id, path, depth, vector, payload_id, content_sha256)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.event_id,
                        event.trial_id,
                        payload.node_id,
                        payload.path,
                        payload.depth,
                        payload.vector,
                        payload.payload_id,
                        payload.content_sha256,
                    ),
                )
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def record_action_event(self, event: BenchmarkEvent) -> bool:
        from src.benchmark.models import AgentActionPayload

        if not isinstance(event.payload, AgentActionPayload):
            raise TypeError("action event requires AgentActionPayload")
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                if not await self._insert_event_locked(connection, event):
                    await connection.rollback()
                    return False
                action = event.payload.action
                await connection.execute(
                    """INSERT INTO benchmark_agent_actions
                    (event_id, trial_id, action_type, action_json) VALUES (?, ?, ?, ?)""",
                    (event.event_id, event.trial_id, action.action.value, canonical_json(action)),
                )
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def record_model_call_event(self, event: BenchmarkEvent) -> bool:
        from src.benchmark.models import ModelCallPayload

        if not isinstance(event.payload, ModelCallPayload):
            raise TypeError("model-call event requires ModelCallPayload")
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                if not await self._insert_event_locked(connection, event):
                    await connection.rollback()
                    return False
                payload = event.payload
                await connection.execute(
                    """INSERT INTO benchmark_model_calls
                    (event_id, trial_id, call_id, provider, model_id, usage_json)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        event.event_id,
                        event.trial_id,
                        payload.call_id,
                        payload.provider,
                        payload.model_id,
                        canonical_json(payload.usage),
                    ),
                )
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def store_callback_token(
        self,
        *,
        token_id: str,
        trial_id: str,
        condition: str,
        exposure_id: str,
        vector: str,
        expected_event_type: str,
        expected_secret_digest: str,
        token_digest: str,
        expires_at: datetime,
        issued_event: BenchmarkEvent,
    ) -> None:
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                await connection.execute(
                    """INSERT INTO benchmark_callback_tokens
                    (token_id, trial_id, condition, exposure_id, vector, expected_event_type,
                     expected_secret_digest, token_digest, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        token_id,
                        trial_id,
                        condition,
                        exposure_id,
                        vector,
                        expected_event_type,
                        expected_secret_digest,
                        token_digest,
                        expires_at.isoformat(),
                    ),
                )
                await self._insert_event_locked(connection, issued_event)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    async def consume_callback_token_with_events(
        self,
        *,
        token_id: str,
        token_digest: str,
        now: datetime,
        submitted_secret_digest: str,
        claims: dict,
    ) -> dict:
        from src.benchmark.enums import EventType
        from src.benchmark.models import CallbackPayload

        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                cursor = await connection.execute(
                    "SELECT * FROM benchmark_callback_tokens WHERE token_id = ?", (token_id,)
                )
                row = await cursor.fetchone()
                if row is None:
                    raise KeyError("unknown token")
                if row["token_digest"] != token_digest:
                    raise ValueError("token digest mismatch")
                if row["used_at"] is not None:
                    raise ValueError("token already used")
                if datetime.fromisoformat(row["expires_at"]) <= now:
                    raise ValueError("token expired")
                bound_fields = ("trial_id", "condition", "exposure_id", "vector")
                if any(str(claims.get(field)) != str(row[field]) for field in bound_fields):
                    raise ValueError("stored token binding mismatch")
                if claims.get("event") != row["expected_event_type"]:
                    raise ValueError("stored event-type binding mismatch")
                matched = hmac.compare_digest(
                    row["expected_secret_digest"], submitted_secret_digest
                )
                event_types = [EventType.CALLBACK_VISITED, EventType.SUBMISSION_ATTEMPTED]
                if matched:
                    event_types.append(EventType.SYNTHETIC_SECRET_SUBMITTED)
                for event_type in event_types:
                    event = BenchmarkEvent(
                        event_id=f"evt-{secrets.token_hex(12)}",
                        trial_id=row["trial_id"],
                        event_type=event_type,
                        payload=CallbackPayload(
                            token_id=row["token_id"],
                            exposure_id=row["exposure_id"],
                            vector=row["vector"],
                            matched_expected_secret=(
                                matched if event_type is EventType.SUBMISSION_ATTEMPTED else None
                            ),
                        ),
                    )
                    await self._insert_event_locked(connection, event)
                    await connection.execute(
                        """INSERT INTO benchmark_callback_events
                        (event_id, trial_id, token_id, event_kind, matched_expected_secret)
                        VALUES (?, ?, ?, ?, ?)""",
                        (
                            event.event_id,
                            event.trial_id,
                            row["token_id"],
                            event.event_type.value,
                            event.payload.matched_expected_secret,
                        ),
                    )
                await connection.execute(
                    "UPDATE benchmark_callback_tokens SET used_at = ? WHERE token_id = ?",
                    (now.isoformat(), token_id),
                )
                await connection.commit()
                result = dict(row)
                result["matched_expected_secret"] = matched
                return result
            except Exception:
                await connection.rollback()
                raise

    async def record_callback_event(self, event: BenchmarkEvent, event_kind: str) -> bool:
        from src.benchmark.models import CallbackPayload

        if not isinstance(event.payload, CallbackPayload):
            raise TypeError("callback event requires CallbackPayload")
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                if not await self._insert_event_locked(connection, event):
                    await connection.rollback()
                    return False
                payload = event.payload
                await connection.execute(
                    """INSERT INTO benchmark_callback_events
                    (event_id, trial_id, token_id, event_kind, matched_expected_secret)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        event.event_id,
                        event.trial_id,
                        payload.token_id,
                        event_kind,
                        payload.matched_expected_secret,
                    ),
                )
                await connection.commit()
                return True
            except Exception:
                await connection.rollback()
                raise

    async def events_for_trial(self, trial_id: str) -> list[BenchmarkEvent]:
        cursor = await self._connection().execute(
            "SELECT * FROM benchmark_events WHERE trial_id = ? ORDER BY sequence", (trial_id,)
        )
        rows = await cursor.fetchall()
        return [
            BenchmarkEvent.model_validate(
                {
                    "event_id": row["event_id"],
                    "trial_id": row["trial_id"],
                    "sequence": row["sequence"],
                    "event_type": row["event_type"],
                    "occurred_at": row["occurred_at"],
                    "payload": __import__("json").loads(row["payload_json"]),
                }
            )
            for row in rows
        ]

    async def store_outcome(self, bundle: ResultBundle, artifact_path: str | None = None) -> None:
        connection = self._connection()
        async with self._write_lock:
            try:
                await connection.execute("BEGIN IMMEDIATE")
                await connection.execute(
                    """INSERT OR REPLACE INTO benchmark_outcomes
                    (trial_id, result_json, artifact_path, created_at) VALUES (?, ?, ?, ?)""",
                    (
                        bundle.manifest.trial_id,
                        canonical_json(bundle),
                        artifact_path,
                        datetime.now().astimezone().isoformat(),
                    ),
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise

    async def outcome_for_trial(self, trial_id: str) -> ResultBundle | None:
        cursor = await self._connection().execute(
            "SELECT result_json FROM benchmark_outcomes WHERE trial_id = ?",
            (trial_id,),
        )
        row = await cursor.fetchone()
        return ResultBundle.model_validate_json(row["result_json"]) if row else None

    async def _insert_event_locked(
        self, connection: aiosqlite.Connection, event: BenchmarkEvent
    ) -> bool:
        existing_cursor = await connection.execute(
            "SELECT * FROM benchmark_events WHERE event_id = ?", (event.event_id,)
        )
        existing = await existing_cursor.fetchone()
        if existing is not None:
            same_event = (
                existing["trial_id"] == event.trial_id
                and existing["event_type"] == event.event_type.value
                and existing["occurred_at"] == event.occurred_at.isoformat()
                and existing["payload_json"] == canonical_json(event.payload)
            )
            if not same_event:
                raise ValueError(f"event ID collision: {event.event_id}")
            event.sequence = int(existing["sequence"])
            return False
        sequence_cursor = await connection.execute(
            "SELECT COALESCE(MAX(sequence), -1) + 1 AS value FROM benchmark_events WHERE trial_id = ?",
            (event.trial_id,),
        )
        sequence_row = await sequence_cursor.fetchone()
        event.sequence = int(sequence_row["value"])
        await connection.execute(
            """INSERT INTO benchmark_events
            (event_id, trial_id, sequence, event_type, occurred_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.trial_id,
                event.sequence,
                event.event_type.value,
                event.occurred_at.isoformat(),
                canonical_json(event.payload),
            ),
        )
        return True

    async def counts_for_trial(self, trial_id: str) -> dict[str, int]:
        connection = self._connection()
        result: dict[str, int] = {}
        for name, table in {
            "events": "benchmark_events",
            "pages": "benchmark_page_exposures",
            "actions": "benchmark_agent_actions",
            "model_calls": "benchmark_model_calls",
            "callbacks": "benchmark_callback_events",
        }.items():
            cursor = await connection.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE trial_id = ?", (trial_id,)
            )
            row = await cursor.fetchone()
            result[name] = int(row["count"])
        return result
