"""Explicit server-side trial registry; request metadata cannot select treatment."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

from src.benchmark.enums import EventType, TerminationReason, TrialStatus, UtilityStatus
from src.benchmark.models import (
    BenchmarkEvent,
    LifecyclePayload,
    OutcomePayload,
    TrialManifest,
)
from src.benchmark.storage import BenchmarkDB

TRIAL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")


class InvalidTrialID(ValueError):
    pass


class UnknownTrial(KeyError):
    pass


class EndedTrial(RuntimeError):
    pass


class InactiveTrial(RuntimeError):
    pass


class TrialRegistry:
    def __init__(self, database: BenchmarkDB) -> None:
        self.database = database

    @staticmethod
    def validate_trial_id(trial_id: str) -> None:
        if not TRIAL_ID_PATTERN.fullmatch(trial_id):
            raise InvalidTrialID("malformed trial ID")

    async def create(self, manifest: TrialManifest) -> TrialManifest:
        self.validate_trial_id(manifest.trial_id)
        event = BenchmarkEvent(
            event_id=f"evt-{secrets.token_hex(12)}",
            trial_id=manifest.trial_id,
            event_type=EventType.TRIAL_CREATED,
            payload=LifecyclePayload(status=TrialStatus.CREATED),
        )
        await self.database.create_trial(manifest, event)
        return manifest

    async def get(self, trial_id: str, active_only: bool = False) -> TrialManifest:
        self.validate_trial_id(trial_id)
        manifest = await self.database.get_trial(trial_id)
        if manifest is None:
            raise UnknownTrial(trial_id)
        if active_only:
            if manifest.status is TrialStatus.ENDED:
                raise EndedTrial(trial_id)
            if manifest.status is not TrialStatus.RUNNING:
                raise InactiveTrial(trial_id)
        return manifest

    async def resolve_model_namespace(
        self, model_namespace: str, active_only: bool = False
    ) -> TrialManifest:
        self.validate_trial_id(model_namespace)
        manifests = await self.database.trials_for_model_namespace(model_namespace)
        if not manifests:
            raise UnknownTrial(model_namespace)
        if active_only:
            active = [item for item in manifests if item.status is TrialStatus.RUNNING]
            if len(active) > 1:
                raise RuntimeError("multiple active trials share one model namespace")
            if active:
                return active[0]
            if any(item.status is TrialStatus.CREATED for item in manifests):
                raise InactiveTrial(model_namespace)
            raise EndedTrial(model_namespace)
        return manifests[0]

    async def start(self, trial_id: str) -> TrialManifest:
        manifest = await self.get(trial_id)
        if manifest.status is TrialStatus.ENDED:
            raise EndedTrial(trial_id)
        if manifest.status is TrialStatus.CREATED:
            manifest = manifest.model_copy(
                update={"status": TrialStatus.RUNNING, "started_at": datetime.now(UTC)}
            )
            event = BenchmarkEvent(
                event_id=f"evt-{secrets.token_hex(12)}",
                trial_id=trial_id,
                event_type=EventType.TRIAL_STARTED,
                payload=LifecyclePayload(status=TrialStatus.RUNNING),
            )
            await self.database.update_trial(manifest, event)
        return manifest

    async def end(
        self,
        trial_id: str,
        reason: TerminationReason,
        utility_status: UtilityStatus = UtilityStatus.INCOMPLETE,
    ) -> TrialManifest:
        manifest = await self.get(trial_id)
        if manifest.status is TrialStatus.ENDED:
            return manifest
        payload = manifest.model_dump()
        payload.update(
            status=TrialStatus.ENDED,
            ended_at=datetime.now(UTC),
            termination_reason=reason,
        )
        manifest = TrialManifest.model_validate(payload)
        event = BenchmarkEvent(
            event_id=f"evt-{secrets.token_hex(12)}",
            trial_id=trial_id,
            event_type=EventType.TRIAL_ENDED,
            payload=OutcomePayload(
                termination_reason=reason,
                utility_status=utility_status,
            ),
        )
        await self.database.update_trial(manifest, event)
        return manifest
