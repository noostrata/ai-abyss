import socket

import httpx
import pytest
from pydantic import ValidationError

from src.benchmark.budgets import (
    BatchBudget,
    BudgetExceeded,
    CallBounds,
    PriceSnapshot,
    TrialBudgetGovernor,
)
from src.benchmark.egress import ContainmentViolation, EgressPolicy, RuntimeSocketBarrier
from src.benchmark.enums import TerminationReason
from src.benchmark.models import AGENT_ACTION_ADAPTER, BudgetLimits, ProviderUsage
from src.benchmark.scaffold import AgentScaffold, ResponseLimitExceeded, extract_observation


@pytest.mark.parametrize(
    "target",
    [
        "https://127.0.0.1:8443/escape",
        "file:///etc/passwd",
        "//example.com/escape",
        "http://user:pass@127.0.0.1:8443/escape",
        "http://%31%32%37.0.0.1:8443/escape",
        "http://127.0.0.1:22/escape",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/private",
    ],
)
def test_application_egress_policy_rejects_escape_forms(target):
    policy = EgressPolicy(["http://127.0.0.1:8443"])
    with pytest.raises(ContainmentViolation):
        policy.validate(target, "http://127.0.0.1:8443/start")


def test_application_egress_normalizes_relative_local_urls():
    policy = EgressPolicy(["http://127.0.0.1:8443"])
    assert policy.validate("../docs/page#fragment", "http://127.0.0.1:8443/a/b") == (
        "http://127.0.0.1:8443/docs/page"
    )


@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1:8443/admin/",
        "http://127.0.0.1:8443/callback/token",
        "http://127.0.0.1:8443/benchmark/trial-b/task/start",
        "http://127.0.0.1:8443/benchmark/trial-a/%2e%2e/admin",
    ],
)
def test_trial_scoped_egress_rejects_legacy_cross_trial_and_encoded_paths(target):
    policy = EgressPolicy(
        ["http://127.0.0.1:8443"],
        allowed_path_prefixes=["/benchmark/trial-a/"],
    )
    with pytest.raises(ContainmentViolation):
        policy.validate(target)


async def test_socket_barriers_keep_concurrent_task_policies_separate():
    async def exercise(port: int, denied_port: int):
        with RuntimeSocketBarrier({("127.0.0.1", port)}):
            socket.getaddrinfo("127.0.0.1", port)
            await __import__("asyncio").sleep(0)
            with pytest.raises(ContainmentViolation):
                socket.getaddrinfo("127.0.0.1", denied_port)

    await __import__("asyncio").gather(exercise(8443, 9444), exercise(9444, 8443))


async def test_redirect_is_validated_before_following():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scaffold = AgentScaffold(client, EgressPolicy(["http://127.0.0.1:8443"]))
    with pytest.raises(ContainmentViolation):
        await scaffold.open("http://127.0.0.1:8443/start")
    assert requests == ["http://127.0.0.1:8443/start"]
    await scaffold.close()


async def test_request_guard_runs_before_initial_and_redirect_requests():
    guarded: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/finish"})
        return httpx.Response(200, content=b"done", request=request)

    async def guard(method: str, url: str) -> None:
        guarded.append((method, url))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scaffold = AgentScaffold(
        client,
        EgressPolicy(["http://127.0.0.1:8443"]),
        request_guard=guard,
    )
    await scaffold.open("http://127.0.0.1:8443/start")
    assert guarded == [
        ("GET", "http://127.0.0.1:8443/start"),
        ("GET", "http://127.0.0.1:8443/finish"),
    ]
    await scaffold.close()


async def test_response_body_is_stopped_at_declared_remaining_budget():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"12345", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scaffold = AgentScaffold(client, EgressPolicy(["http://127.0.0.1:8443"]))
    scaffold.response_byte_limit = 4
    with pytest.raises(ResponseLimitExceeded):
        await scaffold.open("http://127.0.0.1:8443/page")
    assert scaffold.last_response_bytes == 0
    await scaffold.close()


async def test_partial_stream_bytes_are_retained_when_limit_interrupts_read():
    class Chunks(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"12"
            yield b"345"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=Chunks(), request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scaffold = AgentScaffold(client, EgressPolicy(["http://127.0.0.1:8443"]))
    scaffold.response_byte_limit = 4
    with pytest.raises(ResponseLimitExceeded):
        await scaffold.open("http://127.0.0.1:8443/page")
    assert scaffold.last_response_bytes == 2
    await scaffold.close()


async def test_active_http_work_is_cancellable_and_transport_closes():
    release = __import__("asyncio").Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        await release.wait()
        return httpx.Response(200, content=b"done", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scaffold = AgentScaffold(client, EgressPolicy(["http://127.0.0.1:8443"]))
    task = __import__("asyncio").create_task(
        scaffold.open("http://127.0.0.1:8443/page")
    )
    await __import__("asyncio").sleep(0)
    task.cancel()
    with pytest.raises(__import__("asyncio").CancelledError):
        await task
    await scaffold.close()
    assert scaffold.closed is True


def test_independent_runtime_barrier_denies_dns_and_raw_socket_escape():
    barrier = RuntimeSocketBarrier({("127.0.0.1", 8443)})
    with barrier:
        with pytest.raises(ContainmentViolation):
            socket.getaddrinfo("example.com", 443)
        raw_socket = socket.socket()
        try:
            with pytest.raises(ContainmentViolation):
                raw_socket.connect(("8.8.8.8", 53))
        finally:
            raw_socket.close()


def test_dom_extractor_excludes_hidden_payload_and_includes_visible_payload():
    response = httpx.Response(
        200,
        request=httpx.Request("GET", "http://127.0.0.1:8443/page"),
        headers={"content-type": "text/html"},
        text=(
            "<html><head><title>Page</title></head><body>"
            "<div hidden>HIDDEN-PAYLOAD</div><p>VISIBLE-PAYLOAD</p>"
            '<a href="/next">Next</a>'
            '<form method="post" action="/submit"><input name="secret"></form>'
            "</body></html>"
        ),
    )
    observation = extract_observation(response)
    assert "HIDDEN-PAYLOAD" not in observation.visible_text
    assert "VISIBLE-PAYLOAD" in observation.visible_text
    assert observation.links[0].url == "http://127.0.0.1:8443/next"
    assert observation.forms[0].fields == ["secret"]


def test_malformed_html_has_deterministic_bounded_observation():
    response = httpx.Response(
        200,
        request=httpx.Request("GET", "http://127.0.0.1:8443/page"),
        headers={"content-type": "text/html"},
        text="<html><body><p>Unclosed <a href='/next'>link",
    )
    first = extract_observation(response)
    second = extract_observation(response)
    assert first == second
    assert first.visible_text == "Unclosed link"


@pytest.mark.parametrize(
    "action",
    [
        {"action": "shell", "command": "id"},
        {"action": "navigate", "url": "http://localhost", "undeclared": True},
        {"action": "submit", "url": "/", "fields": {"x" * 65: "value"}},
    ],
)
def test_action_schema_rejects_malformed_or_undeclared_fields(action):
    with pytest.raises(ValidationError):
        AGENT_ACTION_ADAPTER.validate_python(action)


def _governor(limits: BudgetLimits) -> TrialBudgetGovernor:
    return TrialBudgetGovernor(
        limits,
        BatchBudget(limits.cost_usd),
        PriceSnapshot(
            snapshot_id="test-price",
            prompt_usd_per_million=0,
            completion_usd_per_million=0,
            reasoning_usd_per_million=0,
        ),
    )


def test_action_request_byte_node_and_depth_limits_enforce_before_increment():
    limits = BudgetLimits(actions=2, requests=1, bytes_read=4, unique_nodes=1, max_depth=1)
    governor = _governor(limits)
    governor.consume_action()
    governor.consume_action()
    with pytest.raises(BudgetExceeded) as action_error:
        governor.consume_action()
    assert action_error.value.reason is TerminationReason.ACTIONS_EXHAUSTED
    governor.consume_request()
    with pytest.raises(BudgetExceeded) as request_error:
        governor.consume_request()
    assert request_error.value.reason is TerminationReason.REQUESTS_EXHAUSTED
    governor.consume_bytes(4)
    with pytest.raises(BudgetExceeded) as byte_error:
        governor.consume_bytes(1)
    assert byte_error.value.reason is TerminationReason.BYTES_EXHAUSTED
    governor.visit_node("one", 1)
    governor.visit_node("one", 1)
    with pytest.raises(BudgetExceeded) as node_error:
        governor.visit_node("two", 1)
    assert node_error.value.reason is TerminationReason.NODES_EXHAUSTED
    with pytest.raises(BudgetExceeded) as depth_error:
        governor.visit_node("one", 2)
    assert depth_error.value.reason is TerminationReason.DEPTH_EXHAUSTED


async def test_wall_clock_boundary_and_idempotent_cancellation(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("src.benchmark.budgets.time.monotonic", lambda: clock[0])
    governor = _governor(BudgetLimits(wall_clock_seconds=1.0))
    clock[0] = 100.999
    governor.check_wall_clock()
    clock[0] = 101.0
    with pytest.raises(BudgetExceeded) as error:
        governor.check_wall_clock()
    assert error.value.reason is TerminationReason.WALL_TIME_EXHAUSTED
    await governor.cancel()
    await governor.cancel()
    assert governor.cancelled is True


async def test_cancellation_releases_outstanding_batch_reservations():
    price = PriceSnapshot(
        snapshot_id="one-dollar-token",
        prompt_usd_per_million=1_000_000,
        completion_usd_per_million=0,
        reasoning_usd_per_million=0,
    )
    batch = BatchBudget(2.0)
    governor = TrialBudgetGovernor(BudgetLimits(cost_usd=2.0), batch, price)
    await governor.reserve_call("x", CallBounds(0, 0, 0))
    assert batch.reserved_cost_usd == 1.0
    await governor.cancel()
    assert batch.reserved_cost_usd == 0.0
    assert governor._reservations == {}


@pytest.mark.parametrize(
    ("limits", "prompt", "bounds", "reason"),
    [
        (BudgetLimits(calls=1), "x", CallBounds(0, 1, 0), TerminationReason.MODEL_CALLS_EXHAUSTED),
        (
            BudgetLimits(prompt_tokens=1),
            "xx",
            CallBounds(0, 1, 0),
            TerminationReason.INPUT_TOKENS_EXHAUSTED,
        ),
        (
            BudgetLimits(completion_tokens=1),
            "x",
            CallBounds(0, 2, 0),
            TerminationReason.OUTPUT_TOKENS_EXHAUSTED,
        ),
        (
            BudgetLimits(total_tokens=2, prompt_tokens=2, completion_tokens=2),
            "xx",
            CallBounds(0, 1, 0),
            TerminationReason.TOTAL_TOKENS_EXHAUSTED,
        ),
    ],
)
async def test_model_call_dimension_boundaries(limits, prompt, bounds, reason):
    governor = _governor(limits)
    if reason is TerminationReason.MODEL_CALLS_EXHAUSTED:
        first = await governor.reserve_call(prompt, bounds)
        with pytest.raises(BudgetExceeded) as error:
            await governor.reserve_call(prompt, bounds)
        await governor.release_call(first.reservation_id)
    else:
        with pytest.raises(BudgetExceeded) as error:
            await governor.reserve_call(prompt, bounds)
    assert error.value.reason is reason


async def test_reconciliation_releases_unused_reservation():
    governor = _governor(BudgetLimits())
    reservation = await governor.reserve_call("prompt", CallBounds(10, 10, 10))
    governor.start_call(reservation.reservation_id)
    governor.signal_call(reservation.reservation_id, "sent")
    governor.signal_call(reservation.reservation_id, "acknowledged")
    await governor.reconcile_call(
        reservation.reservation_id,
        ProviderUsage(prompt_tokens=2, completion_tokens=1, total_tokens=3, provider_reported_cost_usd=0),
    )
    assert governor.model.calls == 1
    assert governor.batch.reserved_cost_usd == 0


async def test_trial_cost_boundary_and_usage_over_reservation():
    price = PriceSnapshot(
        snapshot_id="one-dollar-token",
        prompt_usd_per_million=1_000_000,
        completion_usd_per_million=0,
        reasoning_usd_per_million=0,
    )
    exact = TrialBudgetGovernor(BudgetLimits(cost_usd=1), BatchBudget(1), price)
    reservation = await exact.reserve_call("x", CallBounds(0, 0, 0))
    await exact.release_call(reservation.reservation_id)
    below = TrialBudgetGovernor(BudgetLimits(cost_usd=0.99), BatchBudget(0.99), price)
    with pytest.raises(BudgetExceeded) as error:
        await below.reserve_call("x", CallBounds(0, 0, 0))
    assert error.value.reason is TerminationReason.COST_EXHAUSTED

    bounded = _governor(BudgetLimits())
    reservation = await bounded.reserve_call("x", CallBounds(0, 0, 0))
    bounded.start_call(reservation.reservation_id)
    bounded.signal_call(reservation.reservation_id, "sent")
    bounded.signal_call(reservation.reservation_id, "acknowledged")
    with pytest.raises(RuntimeError, match="exceeded"):
        await bounded.reconcile_call(
            reservation.reservation_id,
            ProviderUsage(prompt_tokens=2, total_tokens=2, provider_reported_cost_usd=0),
        )
    assert bounded.batch.reserved_cost_usd == 0


async def test_atomic_batch_reservation_prevents_concurrent_overspend():
    price = PriceSnapshot(
        snapshot_id="one-dollar-token",
        prompt_usd_per_million=1_000_000,
        completion_usd_per_million=0,
        reasoning_usd_per_million=0,
    )
    batch = BatchBudget(1.0)
    limits = BudgetLimits(cost_usd=2.0)
    first = TrialBudgetGovernor(limits, batch, price)
    second = TrialBudgetGovernor(limits, batch, price)
    results = await __import__("asyncio").gather(
        first.reserve_call("x", CallBounds(0, 0, 0)),
        second.reserve_call("x", CallBounds(0, 0, 0)),
        return_exceptions=True,
    )
    assert sum(isinstance(result, BudgetExceeded) for result in results) == 1
    reservation = next(result for result in results if not isinstance(result, Exception))
    owner = first if reservation.reservation_id in first._reservations else second
    await owner.release_call(reservation.reservation_id)


async def test_action_capacity_is_reserved_before_provider_start():
    governor = _governor(BudgetLimits(actions=1))
    reservation = await governor.reserve_call("x", CallBounds(0, 1, 1))
    with pytest.raises(BudgetExceeded) as error:
        await governor.reserve_call("x", CallBounds(0, 1, 1))
    assert error.value.reason is TerminationReason.ACTIONS_EXHAUSTED
    assert governor.model.provider_attempts == 0
    await governor.release_call(reservation.reservation_id)


async def test_sent_unknown_billing_retains_worst_case_batch_capacity():
    price = PriceSnapshot(
        snapshot_id="one-dollar-token",
        prompt_usd_per_million=1_000_000,
        completion_usd_per_million=0,
        reasoning_usd_per_million=0,
    )
    batch = BatchBudget(1.0)
    governor = TrialBudgetGovernor(BudgetLimits(cost_usd=1), batch, price)
    reservation = await governor.reserve_call("x", CallBounds(0, 0, 0))
    governor.start_call(reservation.reservation_id)
    governor.signal_call(reservation.reservation_id, "sent")
    retained = await governor.mark_billing_unknown(reservation.reservation_id)
    assert retained == 1.0
    assert batch.reserved_cost_usd == 0.0
    assert batch.billing_unknown_cost_usd == 1.0
    assert batch.maximum_possible_cost_usd == 1.0
    assert governor.model.billing_unknown_calls == 1
    with pytest.raises(BudgetExceeded):
        await TrialBudgetGovernor(BudgetLimits(cost_usd=1), batch, price).reserve_call(
            "x", CallBounds(0, 0, 0)
        )


async def test_reasoning_is_an_output_subset_and_missing_cost_is_not_zeroed():
    price = PriceSnapshot(
        snapshot_id="reasoning-subset",
        prompt_usd_per_million=1_000_000,
        completion_usd_per_million=2_000_000,
        reasoning_usd_per_million=3_000_000,
    )
    governor = TrialBudgetGovernor(BudgetLimits(cost_usd=100), BatchBudget(100), price)
    reservation = await governor.reserve_call("x", CallBounds(0, 5, 2))
    assert reservation.total_tokens == reservation.prompt_tokens + 5
    governor.start_call(reservation.reservation_id)
    governor.signal_call(reservation.reservation_id, "sent")
    governor.signal_call(reservation.reservation_id, "acknowledged")
    settlement = await governor.reconcile_call(
        reservation.reservation_id,
        ProviderUsage(
            prompt_tokens=1,
            completion_tokens=5,
            reasoning_tokens=2,
            total_tokens=6,
        ),
    )
    assert settlement.provider_reported_cost_usd is None
    assert settlement.estimated_cost_usd == 13.0
    assert governor.model.completion_tokens == 5
    assert governor.model.reasoning_tokens == 2
    assert governor.model.total_tokens == 6
    assert governor.model.provider_reported_cost_usd is None
    assert governor.model.maximum_possible_cost_usd == 13.0


async def test_cancellation_after_send_retains_unknown_billing_reservation():
    price = PriceSnapshot(
        snapshot_id="one-dollar-token",
        prompt_usd_per_million=1_000_000,
        completion_usd_per_million=0,
        reasoning_usd_per_million=0,
    )
    batch = BatchBudget(1.0)
    governor = TrialBudgetGovernor(BudgetLimits(cost_usd=1), batch, price)
    reservation = await governor.reserve_call("x", CallBounds(0, 0, 0))
    governor.start_call(reservation.reservation_id)
    governor.signal_call(reservation.reservation_id, "sent")
    await governor.cancel()
    assert batch.billing_unknown_cost_usd == 1.0
    assert governor.model.billing_unknown_calls == 1
