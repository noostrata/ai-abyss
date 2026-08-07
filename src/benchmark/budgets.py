"""Fail-closed trial and batch reservations for provider and scaffold work."""

from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.benchmark.enums import CallAttemptState, TerminationReason
from src.benchmark.models import BudgetLimits, ProviderUsage, ResourceLedger


class BudgetExceeded(RuntimeError):
    def __init__(self, reason: TerminationReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


class PriceSnapshot(BaseModel):
    """Immutable pricing inputs bound to a model and exact provider route."""

    model_config = ConfigDict(extra="forbid")
    snapshot_id: str = Field(min_length=1)
    source: str = "local-test-fixture"
    retrieved_at: datetime = Field(default_factory=lambda: datetime(1970, 1, 1, tzinfo=UTC))
    model_id: str = "mock"
    provider_route: str = "mock-local-no-network"
    prompt_usd_per_million: float = Field(ge=0)
    completion_usd_per_million: float = Field(ge=0)
    reasoning_usd_per_million: float = Field(ge=0)
    request_usd: float = Field(default=0.0, ge=0)

    @field_validator("retrieved_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("price snapshot retrieval time must be timezone-aware")
        return value

    def worst_case_cost(self, prompt: int, output: int, reasoning: int) -> float:
        """Conservatively price output when reasoning is an output-token subset."""

        del reasoning  # Any output token may fall in the more expensive category.
        output_rate = max(
            self.completion_usd_per_million,
            self.reasoning_usd_per_million,
        )
        return self.request_usd + (
            prompt * self.prompt_usd_per_million + output * output_rate
        ) / 1_000_000

    def estimated_actual_cost(self, usage: ProviderUsage) -> float:
        visible_output = usage.completion_tokens - usage.reasoning_tokens
        return self.request_usd + (
            usage.prompt_tokens * self.prompt_usd_per_million
            + visible_output * self.completion_usd_per_million
            + usage.reasoning_tokens * self.reasoning_usd_per_million
        ) / 1_000_000


@dataclass(frozen=True)
class CallBounds:
    request_overhead_tokens: int = 256
    max_output_tokens: int = 512
    max_reasoning_tokens: int = 512

    def __post_init__(self) -> None:
        if min(
            self.request_overhead_tokens,
            self.max_output_tokens,
            self.max_reasoning_tokens,
        ) < 0:
            raise ValueError("call bounds cannot be negative")
        if self.max_reasoning_tokens > self.max_output_tokens:
            raise ValueError("reasoning bound must be within the total output bound")


@dataclass(frozen=True)
class CallReservation:
    reservation_id: str
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    total_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class CallSettlement:
    estimated_cost_usd: float
    provider_reported_cost_usd: float | None
    maximum_possible_cost_usd: float


class BatchBudget:
    """One lock protects known, unknown, and reserved concurrent batch spend."""

    def __init__(self, cost_limit_usd: float) -> None:
        if cost_limit_usd < 0:
            raise ValueError("batch cost limit cannot be negative")
        self.cost_limit_usd = cost_limit_usd
        self.actual_cost_usd = 0.0
        self.billing_unknown_cost_usd = 0.0
        self.reserved_cost_usd = 0.0
        self._reservations: dict[str, float] = {}
        self._lock = asyncio.Lock()

    @property
    def maximum_possible_cost_usd(self) -> float:
        return (
            self.actual_cost_usd
            + self.billing_unknown_cost_usd
            + self.reserved_cost_usd
        )

    async def reserve(self, reservation_id: str, cost_usd: float) -> None:
        async with self._lock:
            if reservation_id in self._reservations:
                raise RuntimeError("duplicate batch reservation")
            if self.maximum_possible_cost_usd + cost_usd > self.cost_limit_usd + 1e-12:
                raise BudgetExceeded(TerminationReason.COST_EXHAUSTED)
            self._reservations[reservation_id] = cost_usd
            self.reserved_cost_usd += cost_usd

    async def reconcile(self, reservation_id: str, actual_cost_usd: float) -> None:
        async with self._lock:
            reserved = self._reservations.pop(reservation_id)
            if actual_cost_usd > reserved + 1e-12:
                self.billing_unknown_cost_usd += actual_cost_usd
                self.reserved_cost_usd -= reserved
                raise RuntimeError("actual call cost exceeded its conservative reservation")
            self.reserved_cost_usd -= reserved
            self.actual_cost_usd += actual_cost_usd

    async def retain_unknown(
        self, reservation_id: str, maximum_possible_cost_usd: float | None = None
    ) -> float:
        async with self._lock:
            reserved = self._reservations.pop(reservation_id)
            retained = max(reserved, maximum_possible_cost_usd or 0.0)
            self.reserved_cost_usd -= reserved
            self.billing_unknown_cost_usd += retained
            return retained

    async def release(self, reservation_id: str) -> None:
        async with self._lock:
            reserved = self._reservations.pop(reservation_id, 0.0)
            self.reserved_cost_usd -= reserved


class TrialBudgetGovernor:
    def __init__(self, limits: BudgetLimits, batch: BatchBudget, price: PriceSnapshot) -> None:
        self.limits = limits
        self.batch = batch
        self.price = price
        self.operator = ResourceLedger()
        self.scaffold = ResourceLedger()
        self.model = ResourceLedger()
        self._reserved_calls = 0
        self._reserved_actions = 0
        self._reserved_prompt = 0
        self._reserved_completion = 0
        self._reserved_total = 0
        self._reserved_cost = 0.0
        self._reservations: dict[str, CallReservation] = {}
        self._attempt_states: dict[str, CallAttemptState] = {}
        self._started = time.monotonic()
        self._cancelled = False
        self._visited_nodes: set[str] = set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def remaining_bytes(self) -> int:
        return self.limits.bytes_read - self.scaffold.bytes_delivered

    @property
    def remaining_wall_seconds(self) -> float:
        self._ensure_active()
        remaining = self.limits.wall_clock_seconds - (time.monotonic() - self._started)
        if remaining <= 0:
            raise BudgetExceeded(TerminationReason.WALL_TIME_EXHAUSTED)
        return remaining

    def check_wall_clock(self) -> None:
        elapsed = time.monotonic() - self._started
        self.operator.wall_clock_seconds = elapsed
        if elapsed >= self.limits.wall_clock_seconds:
            raise BudgetExceeded(TerminationReason.WALL_TIME_EXHAUSTED)
        self._ensure_active()

    async def reserve_call(self, prompt: str, bounds: CallBounds) -> CallReservation:
        self.check_wall_clock()
        # UTF-8 bytes are a tokenizer-independent conservative input-token bound.
        prompt_bound = len(prompt.encode()) + bounds.request_overhead_tokens
        output_bound = bounds.max_output_tokens
        total_bound = prompt_bound + output_bound
        cost = self.price.worst_case_cost(
            prompt_bound,
            output_bound,
            bounds.max_reasoning_tokens,
        )
        self._check_call_dimensions(prompt_bound, output_bound, total_bound, cost)
        reservation = CallReservation(
            reservation_id=f"res-{secrets.token_hex(10)}",
            prompt_tokens=prompt_bound,
            completion_tokens=output_bound,
            reasoning_tokens=bounds.max_reasoning_tokens,
            total_tokens=total_bound,
            cost_usd=cost,
        )
        await self.batch.reserve(reservation.reservation_id, cost)
        self._reservations[reservation.reservation_id] = reservation
        self._attempt_states[reservation.reservation_id] = CallAttemptState.RESERVED
        self._reserved_calls += 1
        self._reserved_actions += 1
        self._reserved_prompt += prompt_bound
        self._reserved_completion += output_bound
        self._reserved_total += total_bound
        self._reserved_cost += cost
        return reservation

    def start_call(self, reservation_id: str) -> None:
        self._transition(
            reservation_id,
            {CallAttemptState.RESERVED},
            CallAttemptState.LOCALLY_STARTED,
        )
        self.model.provider_attempts += 1

    def signal_call(self, reservation_id: str, signal: str) -> CallAttemptState:
        if signal == "sent":
            return self._transition(
                reservation_id,
                {CallAttemptState.LOCALLY_STARTED},
                CallAttemptState.SENT,
            )
        if signal == "acknowledged":
            state = self._transition(
                reservation_id,
                {CallAttemptState.SENT},
                CallAttemptState.ACKNOWLEDGED,
            )
            self.model.provider_acknowledged += 1
            return state
        raise ValueError(f"unknown call signal: {signal}")

    def attempt_state(self, reservation_id: str) -> CallAttemptState:
        return self._attempt_states[reservation_id]

    async def reconcile_call(
        self, reservation_id: str, usage: ProviderUsage
    ) -> CallSettlement:
        reservation = self._reservations[reservation_id]
        state = self._attempt_states[reservation_id]
        if state is not CallAttemptState.ACKNOWLEDGED:
            raise RuntimeError("only an acknowledged call can be reconciled")
        estimated_cost = self.price.estimated_actual_cost(usage)
        charged_cost = usage.provider_reported_cost_usd
        batch_cost = charged_cost if charged_cost is not None else estimated_cost
        if (
            usage.prompt_tokens > reservation.prompt_tokens
            or usage.completion_tokens > reservation.completion_tokens
            or usage.total_tokens > reservation.total_tokens
            or batch_cost > reservation.cost_usd + 1e-12
        ):
            await self.mark_billing_unknown(
                reservation_id,
                maximum_possible_cost_usd=max(batch_cost, reservation.cost_usd),
            )
            raise RuntimeError("provider usage exceeded the pre-call reservation")
        await self.batch.reconcile(reservation_id, batch_cost)
        self._reservations.pop(reservation_id)
        self._drop_reservation(reservation)
        self._attempt_states[reservation_id] = CallAttemptState.RECONCILED
        self.model.calls += 1
        self.model.reconciled_calls += 1
        self.model.prompt_tokens += usage.prompt_tokens
        self.model.completion_tokens += usage.completion_tokens
        self.model.reasoning_tokens += usage.reasoning_tokens
        self.model.cache_read_tokens += usage.cache_read_tokens
        self.model.cache_write_tokens += usage.cache_write_tokens
        self.model.total_tokens += usage.total_tokens
        self.model.estimated_cost_usd += estimated_cost
        if charged_cost is not None:
            self.model.known_cost_usd += charged_cost
            self.model.provider_reported_cost_usd = (
                (self.model.provider_reported_cost_usd or 0.0) + charged_cost
            )
        self.model.maximum_possible_cost_usd += batch_cost
        self.scaffold.actions += 1
        return CallSettlement(
            estimated_cost_usd=estimated_cost,
            provider_reported_cost_usd=charged_cost,
            maximum_possible_cost_usd=batch_cost,
        )

    async def reject_call(self, reservation_id: str) -> None:
        state = self._attempt_states[reservation_id]
        if state is not CallAttemptState.ACKNOWLEDGED:
            raise RuntimeError("only an acknowledged call can be rejected")
        reservation = self._reservations.pop(reservation_id)
        await self.batch.release(reservation_id)
        self._drop_reservation(reservation)
        self._attempt_states[reservation_id] = CallAttemptState.REJECTED_BEFORE_INFERENCE

    async def release_call(self, reservation_id: str) -> None:
        state = self._attempt_states.get(reservation_id)
        if state in {CallAttemptState.SENT, CallAttemptState.ACKNOWLEDGED}:
            raise RuntimeError("a sent call cannot be released as unbilled")
        reservation = self._reservations.pop(reservation_id, None)
        if reservation is not None:
            await self.batch.release(reservation_id)
            self._drop_reservation(reservation)
            self._attempt_states[reservation_id] = CallAttemptState.DEFINITELY_NOT_SENT

    async def mark_billing_unknown(
        self,
        reservation_id: str,
        maximum_possible_cost_usd: float | None = None,
    ) -> float:
        state = self._attempt_states[reservation_id]
        if state not in {CallAttemptState.SENT, CallAttemptState.ACKNOWLEDGED}:
            raise RuntimeError("billing can be unknown only after a send attempt")
        reservation = self._reservations.pop(reservation_id)
        retained = await self.batch.retain_unknown(
            reservation_id,
            maximum_possible_cost_usd,
        )
        self._drop_reservation(reservation)
        self._attempt_states[reservation_id] = CallAttemptState.BILLING_UNKNOWN
        self.model.billing_unknown_calls += 1
        self.model.maximum_possible_cost_usd += retained
        return retained

    def consume_action(self) -> None:
        """Reserve-free action accounting retained for isolated scaffold tests."""

        self.check_wall_clock()
        if self.scaffold.actions + self._reserved_actions + 1 > self.limits.actions:
            raise BudgetExceeded(TerminationReason.ACTIONS_EXHAUSTED)
        self.scaffold.actions += 1

    def consume_request(self) -> None:
        self.check_wall_clock()
        if self.scaffold.requests + 1 > self.limits.requests:
            raise BudgetExceeded(TerminationReason.REQUESTS_EXHAUSTED)
        self.scaffold.requests += 1

    def consume_bytes(self, byte_count: int) -> None:
        self.check_wall_clock()
        if self.scaffold.bytes_delivered + byte_count > self.limits.bytes_read:
            raise BudgetExceeded(TerminationReason.BYTES_EXHAUSTED)
        self.scaffold.bytes_delivered += byte_count
        self.scaffold.bytes_read = self.scaffold.bytes_delivered

    def visit_node(self, node_id: str, depth: int) -> None:
        self.check_node(node_id, depth)
        self._visited_nodes.add(node_id)
        self.scaffold.unique_nodes = len(self._visited_nodes)
        self.scaffold.max_depth = max(self.scaffold.max_depth, depth)

    def check_node(self, node_id: str, depth: int) -> None:
        self.check_wall_clock()
        unique_increment = 0 if node_id in self._visited_nodes else 1
        if self.scaffold.unique_nodes + unique_increment > self.limits.unique_nodes:
            raise BudgetExceeded(TerminationReason.NODES_EXHAUSTED)
        if depth > self.limits.max_depth:
            raise BudgetExceeded(TerminationReason.DEPTH_EXHAUSTED)

    async def cancel(self) -> None:
        if self._cancelled and not self._reservations:
            return
        self._cancelled = True
        for reservation_id in tuple(self._reservations):
            state = self._attempt_states[reservation_id]
            if state in {CallAttemptState.SENT, CallAttemptState.ACKNOWLEDGED}:
                await self.mark_billing_unknown(reservation_id)
            else:
                await self.release_call(reservation_id)

    def finalize(
        self,
        *,
        operator_bytes_generated: int,
        operator_bytes_sent: int,
        redirects: int,
    ) -> tuple[ResourceLedger, ResourceLedger, ResourceLedger]:
        self.operator.wall_clock_seconds = max(
            self.operator.wall_clock_seconds,
            time.monotonic() - self._started,
        )
        self.operator.bytes_generated = operator_bytes_generated
        self.operator.bytes_sent = operator_bytes_sent
        self.operator.bytes_served = operator_bytes_sent
        self.scaffold.redirects = redirects
        return (
            self.operator.model_copy(deep=True),
            self.scaffold.model_copy(deep=True),
            self.model.model_copy(deep=True),
        )

    def _ensure_active(self) -> None:
        if self._cancelled:
            raise BudgetExceeded(TerminationReason.CANCELLED)

    def _check_call_dimensions(
        self, prompt: int, completion: int, total: int, cost: float
    ) -> None:
        pending_not_started = sum(
            state is CallAttemptState.RESERVED
            for reservation_id, state in self._attempt_states.items()
            if reservation_id in self._reservations
        )
        if self.model.provider_attempts + pending_not_started + 1 > self.limits.calls:
            raise BudgetExceeded(TerminationReason.MODEL_CALLS_EXHAUSTED)
        if self.scaffold.actions + self._reserved_actions + 1 > self.limits.actions:
            raise BudgetExceeded(TerminationReason.ACTIONS_EXHAUSTED)
        if self.model.prompt_tokens + self._reserved_prompt + prompt > self.limits.prompt_tokens:
            raise BudgetExceeded(TerminationReason.INPUT_TOKENS_EXHAUSTED)
        if self.model.completion_tokens + self._reserved_completion + completion > self.limits.completion_tokens:
            raise BudgetExceeded(TerminationReason.OUTPUT_TOKENS_EXHAUSTED)
        if self.model.total_tokens + self._reserved_total + total > self.limits.total_tokens:
            raise BudgetExceeded(TerminationReason.TOTAL_TOKENS_EXHAUSTED)
        if self.model.maximum_possible_cost_usd + self._reserved_cost + cost > self.limits.cost_usd + 1e-12:
            raise BudgetExceeded(TerminationReason.COST_EXHAUSTED)

    def _drop_reservation(self, reservation: CallReservation) -> None:
        self._reserved_calls -= 1
        self._reserved_actions -= 1
        self._reserved_prompt -= reservation.prompt_tokens
        self._reserved_completion -= reservation.completion_tokens
        self._reserved_total -= reservation.total_tokens
        self._reserved_cost -= reservation.cost_usd

    def _transition(
        self,
        reservation_id: str,
        expected: set[CallAttemptState],
        target: CallAttemptState,
    ) -> CallAttemptState:
        if reservation_id not in self._reservations:
            raise KeyError(f"unknown call reservation: {reservation_id}")
        current = self._attempt_states[reservation_id]
        if current not in expected:
            raise RuntimeError(f"invalid call-attempt transition: {current} -> {target}")
        self._attempt_states[reservation_id] = target
        return target
