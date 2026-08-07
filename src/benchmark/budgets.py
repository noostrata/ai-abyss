"""Pre-action trial limits and atomic batch-level call reservations."""

from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from src.benchmark.enums import TerminationReason
from src.benchmark.models import BudgetLimits, ProviderUsage, ResourceLedger


class BudgetExceeded(RuntimeError):
    def __init__(self, reason: TerminationReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


class PriceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str = Field(min_length=1)
    prompt_usd_per_million: float = Field(ge=0)
    completion_usd_per_million: float = Field(ge=0)
    reasoning_usd_per_million: float = Field(ge=0)

    def worst_case_cost(self, prompt: int, completion: int, reasoning: int) -> float:
        return (
            prompt * self.prompt_usd_per_million
            + completion * self.completion_usd_per_million
            + reasoning * self.reasoning_usd_per_million
        ) / 1_000_000


@dataclass(frozen=True)
class CallBounds:
    request_overhead_tokens: int = 256
    max_output_tokens: int = 512
    max_reasoning_tokens: int = 512


@dataclass(frozen=True)
class CallReservation:
    reservation_id: str
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    total_tokens: int
    cost_usd: float


class BatchBudget:
    """One lock protects reservations shared by concurrently running trials."""

    def __init__(self, cost_limit_usd: float) -> None:
        if cost_limit_usd < 0:
            raise ValueError("batch cost limit cannot be negative")
        self.cost_limit_usd = cost_limit_usd
        self.actual_cost_usd = 0.0
        self.reserved_cost_usd = 0.0
        self._reservations: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def reserve(self, reservation_id: str, cost_usd: float) -> None:
        async with self._lock:
            if self.actual_cost_usd + self.reserved_cost_usd + cost_usd > self.cost_limit_usd:
                raise BudgetExceeded(TerminationReason.COST_EXHAUSTED)
            self._reservations[reservation_id] = cost_usd
            self.reserved_cost_usd += cost_usd

    async def reconcile(self, reservation_id: str, actual_cost_usd: float) -> None:
        async with self._lock:
            reserved = self._reservations.pop(reservation_id)
            if actual_cost_usd > reserved + 1e-12:
                raise RuntimeError("actual call cost exceeded its conservative reservation")
            self.reserved_cost_usd -= reserved
            self.actual_cost_usd += actual_cost_usd

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
        self._reserved_prompt = 0
        self._reserved_completion = 0
        self._reserved_total = 0
        self._reserved_cost = 0.0
        self._reservations: dict[str, CallReservation] = {}
        self._started = time.monotonic()
        self._cancelled = False
        self._visited_nodes: set[str] = set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def remaining_bytes(self) -> int:
        return self.limits.bytes_read - self.scaffold.bytes_read

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
        # UTF-8 bytes are a conservative tokenizer-independent upper bound: a
        # tokenizer cannot emit more non-empty tokens than input bytes.
        prompt_bound = len(prompt.encode()) + bounds.request_overhead_tokens
        completion_bound = bounds.max_output_tokens
        reasoning_bound = bounds.max_reasoning_tokens
        total_bound = prompt_bound + completion_bound + reasoning_bound
        cost = self.price.worst_case_cost(prompt_bound, completion_bound, reasoning_bound)
        self._check_call_dimensions(prompt_bound, completion_bound + reasoning_bound, total_bound, cost)
        reservation = CallReservation(
            reservation_id=f"res-{secrets.token_hex(10)}",
            prompt_tokens=prompt_bound,
            completion_tokens=completion_bound,
            reasoning_tokens=reasoning_bound,
            total_tokens=total_bound,
            cost_usd=cost,
        )
        await self.batch.reserve(reservation.reservation_id, cost)
        self._reservations[reservation.reservation_id] = reservation
        self._reserved_calls += 1
        self._reserved_prompt += prompt_bound
        self._reserved_completion += completion_bound + reasoning_bound
        self._reserved_total += total_bound
        self._reserved_cost += cost
        return reservation

    async def reconcile_call(self, reservation_id: str, usage: ProviderUsage) -> None:
        reservation = self._reservations.pop(reservation_id)
        actual_cost = usage.provider_reported_cost_usd
        if actual_cost is None:
            actual_cost = self.price.worst_case_cost(
                usage.prompt_tokens, usage.completion_tokens, usage.reasoning_tokens
            )
        actual_completion = usage.completion_tokens + usage.reasoning_tokens
        if (
            usage.prompt_tokens > reservation.prompt_tokens
            or actual_completion > reservation.completion_tokens + reservation.reasoning_tokens
            or usage.total_tokens > reservation.total_tokens
            or actual_cost > reservation.cost_usd + 1e-12
        ):
            await self.batch.release(reservation_id)
            self._drop_reservation(reservation)
            raise RuntimeError("provider usage exceeded the pre-call reservation")
        await self.batch.reconcile(reservation_id, actual_cost)
        self._drop_reservation(reservation)
        self.model.calls += 1
        self.model.prompt_tokens += usage.prompt_tokens
        self.model.completion_tokens += usage.completion_tokens
        self.model.reasoning_tokens += usage.reasoning_tokens
        self.model.cache_read_tokens += usage.cache_read_tokens
        self.model.cache_write_tokens += usage.cache_write_tokens
        self.model.total_tokens += usage.total_tokens
        self.model.estimated_cost_usd += actual_cost
        self.model.provider_reported_cost_usd = usage.provider_reported_cost_usd

    async def release_call(self, reservation_id: str) -> None:
        reservation = self._reservations.pop(reservation_id, None)
        if reservation is not None:
            await self.batch.release(reservation_id)
            self._drop_reservation(reservation)

    def consume_action(self) -> None:
        self.check_wall_clock()
        if self.scaffold.actions + 1 > self.limits.actions:
            raise BudgetExceeded(TerminationReason.ACTIONS_EXHAUSTED)
        self.scaffold.actions += 1

    def consume_request(self) -> None:
        self.check_wall_clock()
        if self.scaffold.requests + 1 > self.limits.requests:
            raise BudgetExceeded(TerminationReason.REQUESTS_EXHAUSTED)
        self.scaffold.requests += 1

    def consume_bytes(self, byte_count: int) -> None:
        self.check_wall_clock()
        if self.scaffold.bytes_read + byte_count > self.limits.bytes_read:
            raise BudgetExceeded(TerminationReason.BYTES_EXHAUSTED)
        self.scaffold.bytes_read += byte_count

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
            await self.release_call(reservation_id)

    def _ensure_active(self) -> None:
        if self._cancelled:
            raise BudgetExceeded(TerminationReason.CANCELLED)

    def _check_call_dimensions(
        self, prompt: int, completion: int, total: int, cost: float
    ) -> None:
        if self.model.calls + self._reserved_calls + 1 > self.limits.calls:
            raise BudgetExceeded(TerminationReason.MODEL_CALLS_EXHAUSTED)
        if self.model.prompt_tokens + self._reserved_prompt + prompt > self.limits.prompt_tokens:
            raise BudgetExceeded(TerminationReason.INPUT_TOKENS_EXHAUSTED)
        if self.model.completion_tokens + self._reserved_completion + completion > self.limits.completion_tokens:
            raise BudgetExceeded(TerminationReason.OUTPUT_TOKENS_EXHAUSTED)
        if self.model.total_tokens + self._reserved_total + total > self.limits.total_tokens:
            raise BudgetExceeded(TerminationReason.TOTAL_TOKENS_EXHAUSTED)
        if self.model.estimated_cost_usd + self._reserved_cost + cost > self.limits.cost_usd:
            raise BudgetExceeded(TerminationReason.COST_EXHAUSTED)

    def _drop_reservation(self, reservation: CallReservation) -> None:
        self._reserved_calls -= 1
        self._reserved_prompt -= reservation.prompt_tokens
        self._reserved_completion -= reservation.completion_tokens + reservation.reasoning_tokens
        self._reserved_total -= reservation.total_tokens
        self._reserved_cost -= reservation.cost_usd
