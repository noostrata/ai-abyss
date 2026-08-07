import asyncio

import aiosqlite
import pytest

from src.benchmark.enums import Condition, EventType, TerminationReason, TrialStatus
from src.benchmark.event_sink import InvalidEventToken, TrialEventSink
from src.benchmark.models import (
    BenchmarkEvent,
    CallbackPayload,
    LifecyclePayload,
    ModelCallPayload,
    ProviderUsage,
)
from src.benchmark.registry import TrialRegistry
from src.benchmark.storage import BenchmarkDB
from tests.benchmark.helpers import make_manifest


@pytest.fixture
async def memory_db():
    database = BenchmarkDB(":memory:")
    await database.connect()
    yield database
    await database.close()


async def test_storage_foreign_keys_idempotence_and_round_trip(memory_db):
    event = BenchmarkEvent(
        event_id="evt-storage-001",
        trial_id="trial-storage-001",
        sequence=0,
        event_type=EventType.TRIAL_CREATED,
        payload=LifecyclePayload(status=TrialStatus.CREATED),
    )
    with pytest.raises(aiosqlite.IntegrityError):
        await memory_db.append_event(event)
    await memory_db.create_trial(make_manifest(trial_id="trial-storage-001"))
    assert await memory_db.append_event(event) is True
    assert await memory_db.append_event(event) is False
    stored = await memory_db.events_for_trial("trial-storage-001")
    assert stored == [event]


async def test_normalized_child_failure_rolls_back_parent_event(memory_db):
    trial_id = "trial-atomic-event"
    await memory_db.create_trial(make_manifest(trial_id=trial_id))
    callback = BenchmarkEvent(
        event_id="evt-atomic-callback",
        trial_id=trial_id,
        sequence=0,
        event_type=EventType.CALLBACK_VISITED,
        payload=CallbackPayload(
            token_id="unknown-token",
            exposure_id="unknown-exposure",
            vector="visible_text",
        ),
    )
    with pytest.raises(aiosqlite.IntegrityError):
        await memory_db.record_callback_event(callback, "callback_visited")
    assert await memory_db.events_for_trial(trial_id) == []

    first = BenchmarkEvent(
        event_id="evt-model-first",
        trial_id=trial_id,
        sequence=0,
        event_type=EventType.MODEL_CALL,
        payload=ModelCallPayload(
            call_id="call-duplicate",
            provider="mock",
            model_id="mock/test",
            provider_route="mock-local-no-network",
            prompt_sha256="a" * 64,
            response_sha256="b" * 64,
            usage=ProviderUsage(),
        ),
    )
    second = first.model_copy(update={"event_id": "evt-model-second", "sequence": 1})
    assert await memory_db.record_model_call_event(first) is True
    with pytest.raises(aiosqlite.IntegrityError):
        await memory_db.record_model_call_event(second)
    assert len(await memory_db.events_for_trial(trial_id)) == 1


async def test_concurrent_trials_remain_isolated(memory_db):
    registry = TrialRegistry(memory_db)
    manifests = [
        make_manifest(trial_id=f"trial-concurrent-{index}", pair_id=f"pair-{index}")
        for index in range(12)
    ]
    await asyncio.gather(*(registry.create(manifest) for manifest in manifests))
    loaded = await asyncio.gather(*(registry.get(manifest.trial_id) for manifest in manifests))
    assert {item.trial_id for item in loaded} == {item.trial_id for item in manifests}


async def test_trial_lifecycle_transitions_include_atomic_events(memory_db):
    registry = TrialRegistry(memory_db)
    manifest = make_manifest(trial_id="trial-lifecycle")
    await registry.create(manifest)
    running = await registry.start(manifest.trial_id)
    assert running.status is TrialStatus.RUNNING
    ended = await registry.end(manifest.trial_id, TerminationReason.CANCELLED)
    assert ended.status is TrialStatus.ENDED
    events = await memory_db.events_for_trial(manifest.trial_id)
    assert [event.sequence for event in events] == [0, 1, 2]
    assert [event.event_type for event in events] == [
        EventType.TRIAL_CREATED,
        EventType.TRIAL_STARTED,
        EventType.TRIAL_ENDED,
    ]


async def test_concurrent_lifecycle_transitions_commit_exactly_once(memory_db):
    registry = TrialRegistry(memory_db)
    manifest = make_manifest(trial_id="trial-lifecycle-cas")
    await registry.create(manifest)
    starts = await asyncio.gather(
        registry.start(manifest.trial_id),
        registry.start(manifest.trial_id),
        return_exceptions=True,
    )
    assert sum(not isinstance(item, Exception) for item in starts) >= 1
    events = await memory_db.events_for_trial(manifest.trial_id)
    assert sum(event.event_type is EventType.TRIAL_STARTED for event in events) == 1

    endings = await asyncio.gather(
        registry.end(manifest.trial_id, TerminationReason.CANCELLED),
        registry.end(manifest.trial_id, TerminationReason.CANCELLED),
        return_exceptions=True,
    )
    assert sum(not isinstance(item, Exception) for item in endings) >= 1
    events = await memory_db.events_for_trial(manifest.trial_id)
    assert sum(event.event_type is EventType.TRIAL_ENDED for event in events) == 1


async def test_concurrent_same_trial_events_receive_unique_sequences(memory_db):
    trial_id = "trial-concurrent-events"
    await memory_db.create_trial(make_manifest(trial_id=trial_id))
    events = [
        BenchmarkEvent(
            event_id=f"evt-concurrent-{index}",
            trial_id=trial_id,
            event_type=EventType.TRIAL_CREATED,
            payload=LifecyclePayload(status=TrialStatus.CREATED),
        )
        for index in range(20)
    ]
    assert all(await asyncio.gather(*(memory_db.append_event(event) for event in events)))
    stored = await memory_db.events_for_trial(trial_id)
    assert [event.sequence for event in stored] == list(range(20))


async def test_distinct_event_id_collision_is_not_silently_ignored(memory_db):
    trial_id = "trial-event-id-collision"
    await memory_db.create_trial(make_manifest(trial_id=trial_id))
    first = BenchmarkEvent(
        event_id="evt-collision",
        trial_id=trial_id,
        event_type=EventType.TRIAL_CREATED,
        payload=LifecyclePayload(status=TrialStatus.CREATED),
    )
    await memory_db.append_event(first)
    conflicting = first.model_copy(
        update={"payload": LifecyclePayload(status=TrialStatus.RUNNING)}
    )
    with pytest.raises(ValueError, match="event ID collision"):
        await memory_db.append_event(conflicting)


async def test_explicit_routes_ignore_classifier_and_condition_tampering(
    benchmark_app, benchmark_client
):
    services = benchmark_app.state.benchmark_services
    manifest = make_manifest(trial_id="trial-route-control")
    await services.registry.create(manifest)
    await services.registry.start(manifest.trial_id)
    response = await benchmark_client.get(
        f"/benchmark/{manifest.trial_id}/task/start?condition=recursive_trap",
        headers={"user-agent": "sqlmap/hostile", "x-forwarded-for": "169.254.169.254"},
    )
    assert response.status_code == 200
    assert "Meridian Field Manual" in response.text
    archive = await benchmark_client.get(
        f"/benchmark/{manifest.trial_id}/research/archive?condition=recursive_trap"
    )
    assert "finite archive" in archive.text
    assert "/graph/" not in archive.text
    assert (await services.registry.get(manifest.trial_id)).condition is Condition.CONTROL


async def test_unknown_malformed_and_ended_trial_errors(benchmark_app, benchmark_client):
    assert (await benchmark_client.get("/benchmark/unknown-trial/task/start")).status_code == 404
    assert (await benchmark_client.get("/benchmark/bad!id/task/start")).status_code == 400
    services = benchmark_app.state.benchmark_services
    manifest = make_manifest(trial_id="trial-ended-route")
    await services.registry.create(manifest)
    await services.registry.start(manifest.trial_id)
    await services.registry.end(manifest.trial_id, TerminationReason.CANCELLED)
    assert (
        await benchmark_client.get(f"/benchmark/{manifest.trial_id}/task/start")
    ).status_code == 410


async def test_created_trial_and_legacy_paths_are_not_served(benchmark_app, benchmark_client):
    services = benchmark_app.state.benchmark_services
    manifest = make_manifest(trial_id="trial-not-started")
    await services.registry.create(manifest)
    inactive = await benchmark_client.get(f"/benchmark/{manifest.trial_id}/task/start")
    assert inactive.status_code == 409
    assert inactive.json() == {"error": "inactive_trial"}
    for path in ("/", "/admin/", "/callback?token=x", "/robots.txt"):
        response = await benchmark_client.get(path)
        assert response.status_code == 404
        assert response.json() == {"error": "benchmark_path_only"}


async def test_signed_sink_binds_trial_exposure_secret_and_single_use(memory_db):
    registry = TrialRegistry(memory_db)
    first = make_manifest(trial_id="trial-sink-first", condition=Condition.SYNTHETIC_INJECTION)
    second = make_manifest(
        trial_id="trial-sink-second",
        pair_id="pair-sink-second",
        condition=Condition.SYNTHETIC_INJECTION,
    )
    await registry.create(first)
    await registry.create(second)
    sink = TrialEventSink(memory_db, "http://127.0.0.1:8443", b"x" * 32)
    material, issued = await sink.issue_injection(
        first.trial_id,
        first.model_namespace,
        first.condition,
        "SYNTHETIC-KEY-TEST",
    )
    assert issued.sequence == 1
    token = material.text.split(f"/benchmark/{first.trial_id}/event/", 1)[1].split(". This", 1)[0]
    with pytest.raises(InvalidEventToken, match="cross-trial"):
        await sink.consume(token, second.trial_id, "SYNTHETIC-KEY-TEST")
    forged = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(InvalidEventToken):
        await sink.consume(forged, first.trial_id, "SYNTHETIC-KEY-TEST")
    consumed = await sink.consume(token, first.trial_id, "SYNTHETIC-KEY-TEST")
    assert consumed.matched_expected_secret is True
    with pytest.raises(InvalidEventToken, match="already used"):
        await sink.consume(token, first.trial_id, "SYNTHETIC-KEY-TEST")


async def test_callback_consumption_and_events_roll_back_together(memory_db, monkeypatch):
    manifest = make_manifest(
        trial_id="trial-atomic-callback", condition=Condition.SYNTHETIC_INJECTION
    )
    await memory_db.create_trial(manifest)
    sink = TrialEventSink(memory_db, "http://127.0.0.1:8443", b"z" * 32)
    material, _ = await sink.issue_injection(
        manifest.trial_id,
        manifest.model_namespace,
        manifest.condition,
        "SYNTHETIC-KEY-TEST",
    )
    token = material.text.split(
        f"/benchmark/{manifest.model_namespace}/event/", 1
    )[1].split(". This", 1)[0]
    original = memory_db._insert_event_locked

    async def fail_on_submission(connection, event):
        if event.event_type is EventType.SUBMISSION_ATTEMPTED:
            raise RuntimeError("synthetic child-write failure")
        return await original(connection, event)

    monkeypatch.setattr(memory_db, "_insert_event_locked", fail_on_submission)
    with pytest.raises(RuntimeError, match="child-write failure"):
        await sink.consume(token, manifest.trial_id, "SYNTHETIC-KEY-TEST")
    monkeypatch.setattr(memory_db, "_insert_event_locked", original)

    consumed = await sink.consume(token, manifest.trial_id, "SYNTHETIC-KEY-TEST")
    assert consumed.matched_expected_secret is True
    event_types = [item.event_type for item in await memory_db.events_for_trial(manifest.trial_id)]
    assert event_types == [
        EventType.CALLBACK_TOKEN_ISSUED,
        EventType.CALLBACK_VISITED,
        EventType.SUBMISSION_ATTEMPTED,
        EventType.SYNTHETIC_SECRET_SUBMITTED,
    ]


async def test_sink_rejects_expired_token(memory_db):
    manifest = make_manifest(
        trial_id="trial-expired-sink", condition=Condition.SYNTHETIC_INJECTION
    )
    await memory_db.create_trial(manifest)
    sink = TrialEventSink(memory_db, "http://localhost:8443", b"y" * 32)
    material, _ = await sink.issue_injection(
        manifest.trial_id,
        manifest.model_namespace,
        manifest.condition,
        "SYNTHETIC-KEY-TEST",
        ttl_seconds=-1,
    )
    token = material.text.split(f"/benchmark/{manifest.trial_id}/event/", 1)[1].split(". This", 1)[0]
    with pytest.raises(InvalidEventToken, match="expired"):
        await sink.consume(token, manifest.trial_id, "SYNTHETIC-KEY-TEST")


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost.evil.invalid:8443",
        "http://127.0.0.1:8443@evil.invalid:8443",
        "https://127.0.0.1:8443",
        "http://127.0.0.1",
        "http://127.0.0.1:8443/path",
    ],
)
def test_sink_constructor_parses_loopback_origin_strictly(memory_db, base_url):
    with pytest.raises(ValueError, match="trusted loopback"):
        TrialEventSink(memory_db, base_url, b"z" * 32)


async def test_sink_route_has_bounded_schema_and_ignores_spoofed_host(
    benchmark_app, benchmark_client
):
    services = benchmark_app.state.benchmark_services
    manifest = make_manifest(
        trial_id="trial-sink-route", condition=Condition.SYNTHETIC_INJECTION
    )
    await services.registry.create(manifest)
    await services.registry.start(manifest.trial_id)
    synthetic_secret = "SYNTHETIC-KEY-ROUTE-TEST"
    material, issued = await services.event_sink.issue_injection(
        manifest.trial_id,
        manifest.model_namespace,
        manifest.condition,
        synthetic_secret,
    )
    assert issued.sequence == 2
    assert "evil.example" not in material.text
    callback_url = material.text.split(" to ", 1)[1].split(". This", 1)[0]
    oversized = await benchmark_client.post(callback_url, content=b"x" * 3_000)
    assert oversized.status_code == 413
    malformed_length = await benchmark_client.post(
        callback_url,
        content=b"{}",
        headers={"content-length": "not-a-number"},
    )
    assert malformed_length.status_code == 400
    invalid = await benchmark_client.post(
        callback_url, json={"secret": "x", "extra": "context"}
    )
    assert invalid.status_code == 422
    accepted = await benchmark_client.post(
        callback_url,
        json={"secret": synthetic_secret},
        headers={"host": "evil.example"},
    )
    assert accepted.json() == {"accepted": True, "synthetic": True}
    replay = await benchmark_client.post(
        callback_url,
        json={"secret": synthetic_secret},
    )
    assert replay.status_code == 403
    counts = await services.database.counts_for_trial(manifest.trial_id)
    assert counts["callbacks"] == 3


async def test_wrong_secret_records_attempt_without_exact_submission(
    benchmark_app, benchmark_client
):
    services = benchmark_app.state.benchmark_services
    manifest = make_manifest(
        trial_id="trial-wrong-secret", condition=Condition.SYNTHETIC_INJECTION
    )
    await services.registry.create(manifest)
    await services.registry.start(manifest.trial_id)
    material, _ = await services.event_sink.issue_injection(
        manifest.trial_id,
        manifest.model_namespace,
        manifest.condition,
        "SYNTHETIC-KEY-CORRECT",
    )
    callback_url = material.text.split(" to ", 1)[1].split(". This", 1)[0]
    response = await benchmark_client.post(callback_url, json={"secret": "wrong"})
    assert response.status_code == 200
    event_types = [
        item.event_type
        for item in await services.database.events_for_trial(manifest.trial_id)
    ]
    assert EventType.CALLBACK_VISITED in event_types
    assert EventType.SUBMISSION_ATTEMPTED in event_types
    assert EventType.SYNTHETIC_SECRET_SUBMITTED not in event_types


async def test_injection_material_is_stable_across_page_revisits(
    benchmark_app, benchmark_client
):
    services = benchmark_app.state.benchmark_services
    manifest = make_manifest(
        trial_id="trial-stable-injection", condition=Condition.SYNTHETIC_INJECTION
    )
    await services.registry.create(manifest)
    await services.registry.start(manifest.trial_id)
    services.register_trial_secret(manifest.trial_id, "SYNTHETIC-KEY-STABLE")
    path = f"/benchmark/{manifest.model_namespace}/docs/catalog"
    first = await benchmark_client.get(path)
    second = await benchmark_client.get(path)
    assert first.text == second.text
    events = await services.database.events_for_trial(manifest.trial_id)
    assert sum(item.event_type is EventType.CALLBACK_TOKEN_ISSUED for item in events) == 1
    page_hashes = [
        item.payload.content_sha256
        for item in events
        if item.event_type is EventType.PAGE_SERVED
    ]
    assert len(page_hashes) == 2
    assert len(set(page_hashes)) == 1
