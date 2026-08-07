"""Local benchmark routes backed only by explicit server-side trial state."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.benchmark.conditions import ConditionRenderer, InjectionMaterial
from src.benchmark.enums import Condition, EventType
from src.benchmark.event_sink import InvalidEventToken, TrialEventSink
from src.benchmark.models import BenchmarkEvent, PageServedPayload
from src.benchmark.registry import (
    EndedTrial,
    InactiveTrial,
    InvalidTrialID,
    TrialRegistry,
    UnknownTrial,
)
from src.benchmark.storage import BenchmarkDB

MAX_EVENT_BODY_BYTES = 2_048


@dataclass
class BenchmarkServices:
    database: BenchmarkDB
    registry: TrialRegistry
    renderer: ConditionRenderer
    event_sink: TrialEventSink
    trial_secrets: dict[str, str] = field(default_factory=dict)
    pending_injections: dict[str, dict[str, InjectionMaterial]] = field(default_factory=dict)

    def register_trial_secret(self, trial_id: str, secret: str) -> None:
        self.trial_secrets[trial_id] = secret

    def add_injection(self, trial_id: str, injection: InjectionMaterial) -> None:
        self.pending_injections.setdefault(trial_id, {})[injection.payload_id] = injection

    def clear_trial_runtime(self, trial_id: str) -> None:
        self.trial_secrets.pop(trial_id, None)
        self.pending_injections.pop(trial_id, None)


class SyntheticSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    secret: str = Field(min_length=1, max_length=128)


router = APIRouter()


def services_from(request: Request) -> BenchmarkServices:
    services = getattr(request.app.state, "benchmark_services", None)
    if services is None:
        raise RuntimeError("benchmark services are unavailable")
    return services


async def validate_benchmark_request(request: Request, trial_id: str) -> JSONResponse | None:
    services = services_from(request)
    try:
        await services.registry.get(trial_id, active_only=True)
    except InvalidTrialID:
        return JSONResponse({"error": "malformed_trial_id"}, status_code=400)
    except UnknownTrial:
        return JSONResponse({"error": "unknown_trial"}, status_code=404)
    except EndedTrial:
        return JSONResponse({"error": "ended_trial"}, status_code=410)
    except InactiveTrial:
        return JSONResponse({"error": "inactive_trial"}, status_code=409)
    return None


@router.post("/benchmark/{trial_id}/event/{token}")
async def synthetic_event_sink(trial_id: str, token: str, request: Request):
    validation_error = await validate_benchmark_request(request, trial_id)
    if validation_error is not None:
        return validation_error
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError:
            return JSONResponse({"error": "malformed_content_length"}, status_code=400)
        if declared_length < 0:
            return JSONResponse({"error": "malformed_content_length"}, status_code=400)
        if declared_length > MAX_EVENT_BODY_BYTES:
            return JSONResponse({"error": "body_too_large"}, status_code=413)
    raw = await request.body()
    if len(raw) > MAX_EVENT_BODY_BYTES:
        return JSONResponse({"error": "body_too_large"}, status_code=413)
    try:
        submission = SyntheticSubmission.model_validate_json(raw)
    except ValidationError:
        return JSONResponse({"error": "invalid_submission"}, status_code=422)
    services = services_from(request)
    try:
        consumed = await services.event_sink.consume(token, trial_id, submission.secret)
    except InvalidEventToken:
        return JSONResponse({"error": "invalid_event_token"}, status_code=403)
    events = await services.event_sink.events_for_consumption(consumed)
    await services.database.record_callback_events(events)
    return JSONResponse({"accepted": True, "synthetic": True})


@router.get("/benchmark/{trial_id}/{page_path:path}")
async def benchmark_page(trial_id: str, page_path: str, request: Request):
    validation_error = await validate_benchmark_request(request, trial_id)
    if validation_error is not None:
        return validation_error
    services = services_from(request)
    manifest = await services.registry.get(trial_id, active_only=True)
    injection: InjectionMaterial | None = None
    if manifest.condition is Condition.SYNTHETIC_INJECTION and page_path.strip("/") == "docs/catalog":
        synthetic_secret = services.trial_secrets.get(trial_id)
        if synthetic_secret is None:
            return JSONResponse({"error": "trial_runtime_unavailable"}, status_code=409)
        injection, _token_event = await services.event_sink.issue_injection(
            trial_id,
            manifest.condition,
            synthetic_secret,
        )
        services.add_injection(trial_id, injection)
    try:
        page = services.renderer.render(
            condition=manifest.condition,
            trial_id=trial_id,
            seed=manifest.seed,
            path=page_path,
            injection=injection,
        )
    except KeyError:
        return JSONResponse({"error": "unknown_page"}, status_code=404)
    event = BenchmarkEvent(
        event_id=f"evt-{secrets.token_hex(12)}",
        trial_id=trial_id,
        event_type=EventType.PAGE_SERVED,
        payload=PageServedPayload(
            node_id=page.node_id,
            path=page.path,
            depth=page.depth,
            byte_count=len(page.html.encode()),
            content_sha256=page.content_sha256,
            vector=page.vector,
            payload_id=page.payload_id,
        ),
    )
    await services.database.record_page_event(event)
    return HTMLResponse(page.html)
