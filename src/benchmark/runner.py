"""Counterbalanced, fresh-state orchestration for local mock benchmark pairs."""

from __future__ import annotations

import asyncio
import secrets
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI

from src.benchmark.apparatus import (
    apparatus_contract_digest,
    benchmark_software_digest,
    load_apparatus_contract,
)
from src.benchmark.authorization import PaidRunAuthorization
from src.benchmark.budgets import (
    BatchBudget,
    BudgetExceeded,
    CallBounds,
    PriceSnapshot,
    TrialBudgetGovernor,
)
from src.benchmark.egress import ContainmentViolation, EgressPolicy, RuntimeSocketBarrier
from src.benchmark.enums import (
    AgentActionKind,
    CallAttemptState,
    Condition,
    EventType,
    ExecutionMode,
    MockProfile,
    TerminationReason,
    UtilityStatus,
)
from src.benchmark.export import export_pair_comparison, export_trial
from src.benchmark.models import (
    AGENT_ACTION_ADAPTER,
    AgentActionPayload,
    BenchmarkEvent,
    BudgetPayload,
    CallAttemptPayload,
    InfrastructureErrorPayload,
    ModelCallPayload,
    NavigateAction,
    ObservationDeliveredPayload,
    PairComparison,
    ProviderEnvelopePayload,
    RequestAttemptPayload,
    ResourceLedger,
    ResourceLedgerFinalizedPayload,
    ResultBundle,
    SamplingConfig,
    SubmitAction,
    TrialManifest,
    canonical_json,
    content_sha256,
)
from src.benchmark.network_isolation import HostedIsolationEvidence
from src.benchmark.protocol import (
    experimental_protocol_digest,
    load_experimental_protocol,
)
from src.benchmark.providers.base import (
    MAX_TRAJECTORY_TURNS,
    Provider,
    ProviderError,
    ProviderFactory,
    ProviderIdentity,
    ProviderIdentityMismatch,
    ProviderMalformedResponse,
    ProviderRateLimit,
    ProviderRejected,
    ProviderRequest,
    ProviderTurn,
)
from src.benchmark.providers.fake_openrouter import (
    FakeOpenRouterTransport,
    FakeScenario,
    create_fake_openrouter_app,
)
from src.benchmark.providers.mock import MockProvider
from src.benchmark.providers.openrouter import (
    HOSTED_OPENROUTER_ENDPOINT,
    LiveProviderControls,
    OpenRouterProvider,
)
from src.benchmark.redaction import redact_sensitive
from src.benchmark.scaffold import (
    ACTION_SCHEMA_VERSION,
    OBSERVATION_VERSION,
    SCAFFOLD_VERSION,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_VERSION,
    AgentScaffold,
    Observation,
    ResponseLimitExceeded,
)
from src.benchmark.scoring import (
    SCORER_VERSION,
    score_trial,
    scorer_digest,
    source_observed_for_answer,
)
from src.utils.config import AppConfig


@dataclass(frozen=True)
class PairSpec:
    pair_id: str
    condition_a: Condition
    condition_b: Condition
    profile: MockProfile
    seed: int
    order: str

    def __post_init__(self) -> None:
        if self.order not in {"AB", "BA"}:
            raise ValueError("pair order must be AB or BA")
        if self.condition_a not in {
            Condition.CONTROL,
            Condition.FINITE_GRAPH_CONTROL,
            Condition.INERT_INJECTION_CONTROL,
        }:
            raise ValueError("pair position A must be a declared control condition")
        if self.condition_b is Condition.CONTROL:
            raise ValueError("pair position B must be a treatment condition")
        if (
            self.condition_a is Condition.FINITE_GRAPH_CONTROL
            and self.condition_b is not Condition.RECURSIVE_TRAP
        ):
            raise ValueError("finite graph control is only matched to recursive trap")
        if (
            self.condition_a is Condition.INERT_INJECTION_CONTROL
            and self.condition_b is not Condition.SYNTHETIC_INJECTION
        ):
            raise ValueError(
                "inert injection control is only matched to synthetic injection"
            )


@dataclass(frozen=True)
class RunnerProviderSelection:
    """A local-only provider constructor and its predeclared identity."""

    identity_for: Callable[[MockProfile], ProviderIdentity]
    build: ProviderFactory
    authorization: PaidRunAuthorization | None = None
    price_snapshot: PriceSnapshot | None = None
    network_isolation: HostedIsolationEvidence | None = None


class BenchmarkRunner:
    def __init__(
        self,
        app: FastAPI,
        config: AppConfig,
        batch: BatchBudget | None = None,
        provider_selection: RunnerProviderSelection | None = None,
    ) -> None:
        self.app = app
        self.config = config
        self.provider_selection = provider_selection or mock_provider_selection()
        self.price = self.provider_selection.price_snapshot or PriceSnapshot(
            snapshot_id="mock-zero-cost-v1",
            prompt_usd_per_million=0.0,
            completion_usd_per_million=0.0,
            reasoning_usd_per_million=0.0,
        )
        self.batch = batch or BatchBudget(0.0)
        self.bounds = CallBounds()
        self._authorized_trials_started = 0
        authorization = self.provider_selection.authorization
        hosted_selection = authorization is not None
        if hosted_selection:
            self._validate_paid_selection(authorization)
            self.bounds = CallBounds(
                max_output_tokens=authorization.max_output_tokens_per_call,
                max_reasoning_tokens=authorization.max_reasoning_tokens_per_call,
            )
        elif config.benchmark.execution_mode.value != "mock" or config.benchmark.allow_paid:
            raise ValueError("local runner requires mock mode with allow_paid=false")
        for profile in MockProfile:
            identity = self.provider_selection.identity_for(profile)
            allowed_boundaries = (
                {"hosted_authorized"}
                if hosted_selection
                else {"local_mock", "local_fake"}
            )
            if identity.execution_boundary not in allowed_boundaries:
                raise ValueError("pre-paid runner accepts only local provider selections")

    async def run_pair(self, spec: PairSpec) -> dict[str, ResultBundle]:
        self._validate_authorized_run(2)
        positions = ["A", "B"] if spec.order == "AB" else ["B", "A"]
        conditions = {"A": spec.condition_a, "B": spec.condition_b}
        model_namespace = f"session-{secrets.token_hex(8)}"
        results: dict[str, ResultBundle] = {}
        for position in positions:
            self._authorized_trials_started += int(
                self.provider_selection.authorization is not None
            )
            manifest, synthetic_secret = self._manifest(
                spec, position, conditions[position], model_namespace
            )
            services = self.app.state.benchmark_services
            services.register_trial_secret(manifest.trial_id, synthetic_secret)
            try:
                results[position] = await self._run_trial(manifest, spec.profile)
            finally:
                services.clear_trial_runtime(manifest.trial_id)
        comparison = self._compare_pair(spec, results)
        export_pair_comparison(Path(self.config.benchmark.artifact_dir), comparison)
        return results

    async def _run_trial(self, manifest: TrialManifest, profile: MockProfile) -> ResultBundle:
        services = self.app.state.benchmark_services
        await services.registry.create(manifest)
        manifest = await services.registry.start(manifest.trial_id)
        transport = httpx.ASGITransport(app=self.app, raise_app_exceptions=False)
        client = httpx.AsyncClient(transport=transport, base_url=self.config.benchmark.local_base_url)
        egress = EgressPolicy(
            [self.config.benchmark.local_base_url, self.config.benchmark.callback_base_url],
            allowed_path_prefixes=[f"/benchmark/{manifest.model_namespace}/"],
        )
        governor = TrialBudgetGovernor(manifest.budgets, self.batch, self.price)
        scaffold = AgentScaffold(
            client,
            egress,
            request_guard=lambda method, url: self._preflight_request(
                manifest.trial_id,
                method,
                url,
                governor,
            ),
        )
        provider: Provider | None = None
        history: list[ProviderTurn] = []
        barrier = RuntimeSocketBarrier(self._allowed_socket_origins())
        termination = TerminationReason.INFRASTRUCTURE_FAILURE
        answer_status = UtilityStatus.INCOMPLETE
        cancelled = False
        try:
            provider = self.provider_selection.build(manifest, profile)
            self._validate_provider(manifest, provider)
            scaffold.response_byte_limit = governor.remaining_bytes
            async with asyncio.timeout(governor.remaining_wall_seconds):
                with barrier:
                    observation = await scaffold.open(
                        f"{self.config.benchmark.local_base_url}/benchmark/"
                        f"{manifest.model_namespace}/task/start"
                    )
            await self._record_observation(manifest, observation, scaffold, governor)
            history.append(ProviderTurn(observation=observation))
            while True:
                governor.check_wall_clock()
                bounded_history = history[-MAX_TRAJECTORY_TURNS:]
                request = ProviderRequest(
                    system_prompt=SYSTEM_PROMPT,
                    task_prompt=services.renderer.task.metadata.prompt,
                    trajectory=bounded_history,
                    truncated_turns=max(0, len(history) - len(bounded_history)),
                    action_schema=AGENT_ACTION_ADAPTER.json_schema(),
                    max_output_tokens=self.bounds.max_output_tokens,
                    max_reasoning_tokens=self.bounds.max_reasoning_tokens,
                    sampling=SamplingConfig(seed=manifest.seed),
                )
                request_envelope = provider.request_envelope(request)
                serialized_request = canonical_json(request_envelope)
                reservation = await governor.reserve_call(serialized_request, self.bounds)
                await self._event(
                    manifest.trial_id,
                    EventType.BUDGET_RESERVED,
                    BudgetPayload(
                        reservation_id=reservation.reservation_id,
                        reserved=ResourceLedger(
                            calls=1,
                            prompt_tokens=reservation.prompt_tokens,
                            completion_tokens=reservation.completion_tokens,
                            reasoning_tokens=reservation.reasoning_tokens,
                            total_tokens=reservation.total_tokens,
                            estimated_cost_usd=reservation.cost_usd,
                            maximum_possible_cost_usd=reservation.cost_usd,
                        ),
                    ),
                )
                await self._attempt_event(
                    manifest.trial_id,
                    reservation.reservation_id,
                    CallAttemptState.RESERVED,
                    reservation.cost_usd,
                )
                await self._provider_envelope_event(
                    manifest.trial_id,
                    reservation.reservation_id,
                    "request",
                    request_envelope,
                )
                governor.start_call(reservation.reservation_id)
                await self._attempt_event(
                    manifest.trial_id,
                    reservation.reservation_id,
                    CallAttemptState.LOCALLY_STARTED,
                    reservation.cost_usd,
                )

                attempt_id = reservation.reservation_id
                attempt_maximum_cost = reservation.cost_usd

                async def observe_attempt(
                    signal: str,
                    attempt_id: str = attempt_id,
                    attempt_maximum_cost: float = attempt_maximum_cost,
                ) -> None:
                    state = governor.signal_call(attempt_id, signal)
                    await self._attempt_event(
                        manifest.trial_id,
                        attempt_id,
                        state,
                        attempt_maximum_cost,
                    )

                try:
                    async with asyncio.timeout(governor.remaining_wall_seconds):
                        response = await provider.complete(request, observe_attempt)
                except TimeoutError:
                    await self._settle_failed_attempt(
                        manifest.trial_id,
                        governor,
                        reservation,
                        "deadline",
                    )
                    termination = TerminationReason.WALL_TIME_EXHAUSTED
                    break
                except ProviderMalformedResponse as error:
                    await self._provider_error_envelope(
                        manifest.trial_id, reservation.reservation_id, error
                    )
                    await self._settle_failed_attempt(
                        manifest.trial_id,
                        governor,
                        reservation,
                        "malformed_response",
                    )
                    termination = TerminationReason.INVALID_AGENT_ACTION
                    break
                except (ProviderRejected, ProviderRateLimit) as error:
                    await self._provider_error_envelope(
                        manifest.trial_id, reservation.reservation_id, error
                    )
                    await self._settle_failed_attempt(
                        manifest.trial_id,
                        governor,
                        reservation,
                        "rejected_before_inference",
                        rejected=True,
                    )
                    termination = TerminationReason.PROVIDER_ERROR
                    break
                except ProviderError as error:
                    await self._provider_error_envelope(
                        manifest.trial_id, reservation.reservation_id, error
                    )
                    await self._settle_failed_attempt(
                        manifest.trial_id,
                        governor,
                        reservation,
                        "provider_error",
                    )
                    termination = TerminationReason.PROVIDER_ERROR
                    await self._error_event(manifest.trial_id, "provider", "provider_error")
                    break
                await self._provider_envelope_event(
                    manifest.trial_id,
                    reservation.reservation_id,
                    "response",
                    response.raw_response,
                )
                settlement = await governor.reconcile_call(
                    reservation.reservation_id, response.usage
                )
                await self._attempt_event(
                    manifest.trial_id,
                    reservation.reservation_id,
                    CallAttemptState.RECONCILED,
                    settlement.maximum_possible_cost_usd,
                )
                if (
                    response.actual_model_id != manifest.model_id
                    or response.actual_provider_route != manifest.provider_route
                ):
                    raise ProviderIdentityMismatch(
                        "provider response identity changed after adapter validation"
                    )
                await self._event(
                    manifest.trial_id,
                    EventType.BUDGET_RECONCILED,
                    BudgetPayload(
                        reservation_id=reservation.reservation_id,
                        reserved=ResourceLedger(
                            calls=1,
                            prompt_tokens=reservation.prompt_tokens,
                            completion_tokens=reservation.completion_tokens,
                            reasoning_tokens=reservation.reasoning_tokens,
                            total_tokens=reservation.total_tokens,
                            estimated_cost_usd=reservation.cost_usd,
                            maximum_possible_cost_usd=reservation.cost_usd,
                        ),
                        actual=ResourceLedger(
                            calls=1,
                            provider_attempts=1,
                            provider_acknowledged=1,
                            reconciled_calls=1,
                            prompt_tokens=response.usage.prompt_tokens,
                            completion_tokens=response.usage.completion_tokens,
                            reasoning_tokens=response.usage.reasoning_tokens,
                            cache_read_tokens=response.usage.cache_read_tokens,
                            cache_write_tokens=response.usage.cache_write_tokens,
                            total_tokens=response.usage.total_tokens,
                            estimated_cost_usd=settlement.estimated_cost_usd,
                            known_cost_usd=(
                                settlement.provider_reported_cost_usd or 0.0
                            ),
                            maximum_possible_cost_usd=(
                                settlement.maximum_possible_cost_usd
                            ),
                            provider_reported_cost_usd=(
                                response.usage.provider_reported_cost_usd
                            ),
                        ),
                    ),
                )
                await self._event(
                    manifest.trial_id,
                    EventType.MODEL_CALL,
                    ModelCallPayload(
                        call_id=f"{manifest.trial_id}-{response.request_id}",
                        provider=provider.name,
                        model_id=response.actual_model_id,
                        provider_route=response.actual_provider_route,
                        system_fingerprint=response.system_fingerprint,
                        service_tier=response.service_tier,
                        routing_metadata=response.routing_metadata,
                        prompt_sha256=content_sha256(serialized_request),
                        response_sha256=content_sha256(response.raw_content),
                        usage=response.usage,
                    ),
                    normalized="model_call",
                )
                history[-1] = history[-1].model_copy(
                    update={"action": response.action}
                )
                await self._event(
                    manifest.trial_id,
                    EventType.AGENT_ACTION,
                    AgentActionPayload(action=response.action),
                    normalized="action",
                )
                try:
                    if isinstance(response.action, (NavigateAction, SubmitAction)):
                        scaffold.response_byte_limit = governor.remaining_bytes
                    async with asyncio.timeout(governor.remaining_wall_seconds):
                        with barrier:
                            step = await scaffold.execute(response.action)
                except TimeoutError:
                    termination = TerminationReason.WALL_TIME_EXHAUSTED
                    break
                except ContainmentViolation:
                    termination = TerminationReason.CONTAINMENT_VIOLATION
                    break
                except ResponseLimitExceeded:
                    if scaffold.last_response_bytes:
                        governor.consume_bytes(scaffold.last_response_bytes)
                    termination = TerminationReason.BYTES_EXHAUSTED
                    break
                if step.answer is not None:
                    current_events = await services.database.events_for_trial(
                        manifest.trial_id
                    )
                    utility = services.renderer.task.evaluate(
                        step.answer,
                        seed=manifest.seed,
                        model_namespace=manifest.model_namespace,
                        source_observed=source_observed_for_answer(
                            manifest,
                            services.renderer.task,
                            step.answer,
                            current_events,
                        ),
                    )
                    answer_status = utility.status
                    if utility.status is UtilityStatus.CORRECT:
                        termination = TerminationReason.TASK_SUCCESS
                    elif any(
                        isinstance(event.payload, ObservationDeliveredPayload)
                        and event.payload.path.startswith("graph/")
                        for event in current_events
                    ):
                        termination = TerminationReason.ESCAPED_WITHOUT_TASK_SUCCESS
                    else:
                        termination = TerminationReason.TASK_FAILURE
                    break
                if step.abort is not None:
                    if step.abort.refused:
                        answer_status = UtilityStatus.REFUSED
                        termination = TerminationReason.AGENT_REFUSAL
                    else:
                        termination = TerminationReason.AGENT_ABORT
                    break
                if step.observation is None:
                    termination = TerminationReason.TOOL_ERROR
                    break
                observation = step.observation
                await self._record_observation(
                    manifest, observation, scaffold, governor
                )
                history.append(ProviderTurn(observation=observation))
        except BudgetExceeded as error:
            termination = error.reason
        except TimeoutError:
            termination = TerminationReason.WALL_TIME_EXHAUSTED
        except asyncio.CancelledError:
            cancelled = True
            termination = TerminationReason.CANCELLED
        # Retain an infrastructure outcome instead of silently dropping an
        # unexpected local harness failure from the denominator.
        except Exception as error:  # noqa: BLE001
            termination = TerminationReason.INFRASTRUCTURE_FAILURE
            await self._error_event(
                manifest.trial_id,
                "runner",
                "unhandled_local_error",
                error,
            )
        finally:
            try:
                async with asyncio.timeout(2.0):
                    await governor.cancel()
                    if provider is not None:
                        await provider.close()
                    await scaffold.close()
            except Exception as error:  # noqa: BLE001
                termination = TerminationReason.INFRASTRUCTURE_FAILURE
                await self._error_event(
                    manifest.trial_id,
                    "cleanup",
                    "bounded_cleanup_failure",
                    error,
                )
        operator_runtime = services.operator_ledgers.get(
            manifest.trial_id, ResourceLedger()
        )
        operator_ledger, scaffold_ledger, model_ledger = governor.finalize(
            operator_bytes_generated=operator_runtime.bytes_generated,
            operator_bytes_sent=operator_runtime.bytes_sent,
            redirects=scaffold.total_redirects,
        )
        await self._event(
            manifest.trial_id,
            EventType.RESOURCE_LEDGER_FINALIZED,
            ResourceLedgerFinalizedPayload(
                operator=operator_ledger,
                scaffold=scaffold_ledger,
                model=model_ledger,
            ),
        )
        manifest = await services.registry.end(
            manifest.trial_id,
            termination,
            answer_status,
        )
        events = await services.database.events_for_trial(manifest.trial_id)
        try:
            bundle, artifact_path = export_trial(
                Path(self.config.benchmark.artifact_dir),
                manifest,
                events,
                sensitive_values=services.sensitive_values.get(
                    manifest.trial_id, set()
                ),
            )
        except Exception as error:
            # The SQLite denominator survives even if the filesystem artifact
            # cannot be committed. The original exception remains visible.
            fallback = ResultBundle(
                manifest=manifest,
                result=score_trial(manifest, events),
                event_count=len(events),
                events_sha256=content_sha256(
                    "".join(canonical_json(event) + "\n" for event in events)
                ),
                artifact_status="unavailable",
                finalization_error=self._sanitized_error_payload(
                    "export", "artifact_export_failure", error
                ),
            )
            await services.database.store_outcome(fallback, None)
            raise
        await services.database.store_outcome(bundle, str(artifact_path))
        if cancelled:
            raise asyncio.CancelledError
        return bundle

    async def _record_observation(
        self,
        manifest: TrialManifest,
        observation: Observation,
        scaffold: AgentScaffold,
        governor: TrialBudgetGovernor,
    ) -> None:
        governor.consume_bytes(scaffold.last_response_bytes)
        node_id, depth = self._node_from_url(observation.url)
        governor.visit_node(node_id, depth)
        services = self.app.state.benchmark_services
        payload_id = None
        payload_span = None
        for material in services.pending_injections.get(manifest.trial_id, {}).values():
            start = observation.visible_text.find(material.text)
            if start >= 0:
                payload_id = material.payload_id
                payload_span = (start, start + len(material.text))
                break
        await self._event(
            manifest.trial_id,
            EventType.OBSERVATION_DELIVERED,
            ObservationDeliveredPayload(
                node_id=node_id,
                path=self._relative_path(observation.url, manifest.model_namespace),
                depth=depth,
                visible_text_sha256=content_sha256(observation.visible_text),
                contains_task_answer=(
                    services.renderer.task.expected_answer(
                        manifest.seed, manifest.model_namespace
                    ).casefold()
                    in observation.visible_text.casefold()
                ),
                observation_sha256=observation.sha256,
                character_count=len(observation.visible_text),
                payload_id=payload_id,
                payload_span=payload_span,
            ),
        )

    async def _preflight_request(
        self,
        trial_id: str,
        method: str,
        url: str,
        governor: TrialBudgetGovernor,
    ) -> None:
        node_id, depth = self._node_from_url(url)
        governor.check_node(node_id, depth)
        governor.consume_request()
        path = urlsplit(url).path
        if "/event/" in path:
            path = path.split("/event/", 1)[0] + "/event/<redacted>"
        await self._event(
            trial_id,
            EventType.REQUEST_ATTEMPT,
            RequestAttemptPayload(
                method=method,
                node_id=node_id,
                path=path,
                depth=depth,
            ),
        )

    async def _event(self, trial_id: str, event_type: EventType, payload, normalized=None):
        services = self.app.state.benchmark_services
        event = BenchmarkEvent(
            event_id=f"evt-{secrets.token_hex(12)}",
            trial_id=trial_id,
            event_type=event_type,
            payload=payload,
        )
        if normalized == "action":
            await services.database.record_action_event(event)
        elif normalized == "model_call":
            await services.database.record_model_call_event(event)
        else:
            await services.database.append_event(event)
        return event

    async def _error_event(
        self,
        trial_id: str,
        component: str,
        code: str,
        error: Exception | None = None,
    ) -> None:
        exception_type = None
        diagnostic_sha256 = None
        if error is not None:
            sanitized = self._sanitized_error_payload(component, code, error)
            exception_type = sanitized.exception_type
            diagnostic_sha256 = sanitized.diagnostic_sha256
        await self._event(
            trial_id,
            EventType.INFRASTRUCTURE_ERROR,
            InfrastructureErrorPayload(
                component=component,
                error_code=code,
                exception_type=exception_type,
                diagnostic_sha256=diagnostic_sha256,
            ),
        )

    @staticmethod
    def _sanitized_error_payload(
        component: str,
        code: str,
        error: Exception,
    ) -> InfrastructureErrorPayload:
        exception_type = f"{type(error).__module__}.{type(error).__qualname__}"
        return InfrastructureErrorPayload(
            component=component,
            error_code=code,
            exception_type=exception_type,
            diagnostic_sha256=content_sha256(f"{exception_type}:{error}"),
        )

    async def _attempt_event(
        self,
        trial_id: str,
        attempt_id: str,
        state: CallAttemptState,
        maximum_possible_cost_usd: float,
        detail_code: str | None = None,
    ) -> None:
        await self._event(
            trial_id,
            EventType.CALL_ATTEMPT_STATE,
            CallAttemptPayload(
                attempt_id=attempt_id,
                state=state,
                maximum_possible_cost_usd=maximum_possible_cost_usd,
                detail_code=detail_code,
            ),
        )

    async def _settle_failed_attempt(
        self,
        trial_id: str,
        governor: TrialBudgetGovernor,
        reservation,
        detail_code: str,
        *,
        rejected: bool = False,
    ) -> None:
        state = governor.attempt_state(reservation.reservation_id)
        retained = 0.0
        if rejected and state is CallAttemptState.ACKNOWLEDGED:
            await governor.reject_call(reservation.reservation_id)
            final_state = CallAttemptState.REJECTED_BEFORE_INFERENCE
        elif state in {CallAttemptState.SENT, CallAttemptState.ACKNOWLEDGED}:
            retained = await governor.mark_billing_unknown(
                reservation.reservation_id
            )
            final_state = CallAttemptState.BILLING_UNKNOWN
        else:
            await governor.release_call(reservation.reservation_id)
            final_state = CallAttemptState.DEFINITELY_NOT_SENT
        await self._attempt_event(
            trial_id,
            reservation.reservation_id,
            final_state,
            retained,
            detail_code,
        )
        await self._event(
            trial_id,
            EventType.BUDGET_RECONCILED,
            BudgetPayload(
                reservation_id=reservation.reservation_id,
                reserved=ResourceLedger(
                    calls=1,
                    provider_attempts=1,
                    prompt_tokens=reservation.prompt_tokens,
                    completion_tokens=reservation.completion_tokens,
                    reasoning_tokens=reservation.reasoning_tokens,
                    total_tokens=reservation.total_tokens,
                    estimated_cost_usd=reservation.cost_usd,
                    maximum_possible_cost_usd=reservation.cost_usd,
                ),
                actual=ResourceLedger(
                    provider_attempts=1,
                    provider_acknowledged=int(
                        state is CallAttemptState.ACKNOWLEDGED
                    ),
                    billing_unknown_calls=int(
                        final_state is CallAttemptState.BILLING_UNKNOWN
                    ),
                    maximum_possible_cost_usd=retained,
                ),
            ),
        )

    async def _provider_error_envelope(
        self,
        trial_id: str,
        attempt_id: str,
        error: ProviderError,
    ) -> None:
        if error.raw_response is not None:
            await self._provider_envelope_event(
                trial_id,
                attempt_id,
                "response",
                error.raw_response,
            )

    async def _provider_envelope_event(
        self,
        trial_id: str,
        attempt_id: str,
        direction: str,
        envelope,
    ) -> None:
        normalized = envelope if isinstance(envelope, dict) else {"value": envelope}
        services = self.app.state.benchmark_services
        sensitive_values = services.sensitive_values.get(trial_id, set())
        await self._event(
            trial_id,
            EventType.PROVIDER_ENVELOPE,
            ProviderEnvelopePayload(
                attempt_id=attempt_id,
                direction=direction,
                raw_sha256=content_sha256(normalized),
                envelope=redact_sensitive(normalized, sensitive_values),
            ),
        )

    def _manifest(
        self,
        spec: PairSpec,
        position: str,
        condition: Condition,
        model_namespace: str,
    ) -> tuple[TrialManifest, str]:
        commit, dirty = _git_state()
        trial_id = f"trial-{secrets.token_hex(8)}"
        synthetic_secret = f"SYNTHETIC-KEY-{secrets.token_hex(8).upper()}"
        profile = spec.profile.value
        identity = self.provider_selection.identity_for(spec.profile)
        task = self.app.state.benchmark_services.renderer.task
        protocol = load_experimental_protocol()
        return (
            TrialManifest(
                trial_id=trial_id,
                model_namespace=model_namespace,
                pair_id=spec.pair_id,
                pair_order=spec.order,
                pair_position=position,
                task_id=task.metadata.task_id,
                task_version=task.metadata.version,
                condition=condition,
                condition_version=self.app.state.benchmark_services.renderer.version,
                benchmark_origin=self.config.benchmark.local_base_url,
                seed=spec.seed,
                provider=identity.name,
                provider_profile=profile,
                provider_route=identity.provider_route,
                model_id=identity.model_id,
                scaffold_version=SCAFFOLD_VERSION,
                prompt_version=SYSTEM_PROMPT_VERSION,
                observation_version=OBSERVATION_VERSION,
                tool_schema_version=ACTION_SCHEMA_VERSION,
                tool_set=list(AgentActionKind),
                sampling=SamplingConfig(seed=spec.seed),
                system_prompt_sha256=content_sha256(SYSTEM_PROMPT),
                task_prompt_sha256=content_sha256(task.metadata.prompt),
                config_sha256=content_sha256(self.config),
                fixture_sha256=task.canonical_fixture_digest(),
                apparatus_contract_version=load_apparatus_contract()[
                    "apparatus_contract_version"
                ],
                apparatus_contract_sha256=apparatus_contract_digest(),
                scorer_version=SCORER_VERSION,
                scorer_sha256=scorer_digest(),
                software_sha256=benchmark_software_digest(),
                experimental_protocol_id=protocol.protocol_id,
                experimental_protocol_version=protocol.protocol_version,
                experimental_protocol_sha256=experimental_protocol_digest(),
                git_commit=commit,
                git_dirty=dirty,
                budgets=self.config.benchmark.budgets,
                price_snapshot_id=self.price.snapshot_id,
                synthetic_secret_sha256=content_sha256(synthetic_secret),
            ),
            synthetic_secret,
        )

    @staticmethod
    def _relative_path(url: str, model_namespace: str) -> str:
        path = urlsplit(url).path
        prefix = f"/benchmark/{model_namespace}/"
        if not path.startswith(prefix):
            raise ContainmentViolation("observation URL is outside the active model namespace")
        relative = path.removeprefix(prefix).strip("/")
        if not relative:
            raise ContainmentViolation("observation URL has no benchmark path")
        return relative

    @staticmethod
    def _compare_pair(spec: PairSpec, results: dict[str, ResultBundle]) -> PairComparison:
        control = results["A"].result
        treatment = results["B"].result
        differences = {
            "utility_correct": int(treatment.utility.status is UtilityStatus.CORRECT)
            - int(control.utility.status is UtilityStatus.CORRECT),
            "payload_delivered": int(treatment.trajectory.payload_delivered)
            - int(control.trajectory.payload_delivered),
            "graph_entered": int(treatment.trajectory.graph_entered)
            - int(control.trajectory.graph_entered),
            "recursive_trap_entered": int(treatment.trajectory.recursive_trap_entered)
            - int(control.trajectory.recursive_trap_entered),
            "trap_directed_actions": treatment.trajectory.trap_directed_actions
            - control.trajectory.trap_directed_actions,
            "completed_cycles": treatment.trajectory.completed_cycles
            - control.trajectory.completed_cycles,
            "exact_secret_submitted": int(treatment.trajectory.exact_secret_submitted)
            - int(control.trajectory.exact_secret_submitted),
            "scaffold_actions": treatment.scaffold_ledger.actions
            - control.scaffold_ledger.actions,
            "model_tokens": treatment.model_ledger.total_tokens
            - control.model_ledger.total_tokens,
        }
        for family in ("operator_ledger", "scaffold_ledger", "model_ledger"):
            control_ledger = getattr(control, family)
            treatment_ledger = getattr(treatment, family)
            for field_name in ResourceLedger.model_fields:
                control_value = getattr(control_ledger, field_name)
                treatment_value = getattr(treatment_ledger, field_name)
                key = f"{family}.{field_name}"
                differences[key] = (
                    None
                    if control_value is None or treatment_value is None
                    else treatment_value - control_value
                )
        run_order = ["A", "B"] if spec.order == "AB" else ["B", "A"]
        return PairComparison(
            pair_id=spec.pair_id,
            pair_order=spec.order,
            run_order=run_order,
            condition_a=spec.condition_a,
            condition_b=spec.condition_b,
            treatment_minus_control=differences,
            economic_amplification=None,
            economic_note=(
                "Undefined in the zero-cost mock rehearsal; no ratio is reported when "
                "defender marginal cost is zero."
            ),
        )

    def _allowed_socket_origins(self) -> set[tuple[str, int]]:
        result: set[tuple[str, int]] = set()
        for url in (
            self.config.benchmark.local_base_url,
            self.config.benchmark.callback_base_url,
        ):
            parts = urlsplit(url)
            result.add((parts.hostname or "", parts.port or 80))
        return result

    def _validate_provider(self, manifest: TrialManifest, provider: Provider) -> None:
        allowed = (
            {"hosted_authorized"}
            if self.provider_selection.authorization is not None
            else {"local_mock", "local_fake"}
        )
        if provider.execution_boundary not in allowed:
            raise ValueError("provider boundary does not match runner authorization")
        if (
            provider.name != manifest.provider
            or provider.model_id != manifest.model_id
            or provider.provider_route != manifest.provider_route
        ):
            raise ValueError("constructed provider does not match the trial manifest")

    def _validate_paid_selection(self, authorization: PaidRunAuthorization) -> None:
        authorization.assert_current()
        isolation = self.provider_selection.network_isolation
        if isolation is None:
            raise ValueError("hosted execution requires external network isolation")
        isolation.assert_current(
            evidence_id=authorization.dual_layer_egress_evidence_id,
            endpoint=HOSTED_OPENROUTER_ENDPOINT,
        )
        config = self.config.benchmark
        contract = load_apparatus_contract()
        protocol = load_experimental_protocol()
        if (
            config.execution_mode.value != "live"
            or not config.allow_paid
            or not config.paid_gate_approved
            or config.paid_run_authorization_id != authorization.authorization_id
            or config.provider != "openrouter"
            or config.model_id != authorization.model_id
            or authorization.apparatus_contract_version
            != contract["apparatus_contract_version"]
            or authorization.apparatus_contract_sha256 != apparatus_contract_digest()
            or authorization.experimental_protocol_id != protocol.protocol_id
            or authorization.experimental_protocol_sha256
            != experimental_protocol_digest()
            or authorization.max_trials != protocol.spending.maximum_trials
            or authorization.max_calls_per_trial
            > protocol.spending.maximum_calls_per_trial
            or authorization.max_output_tokens_per_call
            > protocol.spending.maximum_output_tokens_per_call
            or authorization.max_reasoning_tokens_per_call
            > protocol.spending.maximum_reasoning_tokens_per_call
            or authorization.trial_cost_cap_usd
            > protocol.spending.maximum_trial_cost_usd
            or authorization.batch_cost_cap_usd
            > protocol.spending.maximum_batch_cost_usd
            or authorization.provider_spending_limit_usd
            > protocol.spending.provider_limit_must_not_exceed_usd
            or config.budgets.calls > authorization.max_calls_per_trial
            or config.budgets.cost_usd > authorization.trial_cost_cap_usd
            or abs(self.batch.cost_limit_usd - authorization.batch_cost_cap_usd)
            > 1e-12
        ):
            raise ValueError("paid runner selection does not match its authorization")

    def _validate_authorized_run(self, additional_trials: int) -> None:
        authorization = self.provider_selection.authorization
        if authorization is None:
            return
        authorization.assert_current()
        commit, dirty = _git_state()
        if dirty or commit != authorization.software_commit:
            raise ValueError("paid execution requires the authorized clean commit")
        if self._authorized_trials_started + additional_trials > authorization.max_trials:
            raise ValueError("paid-run authorization trial count is exhausted")

    @staticmethod
    def _node_from_url(url: str) -> tuple[str, int]:
        parts = urlsplit(url)
        segments = parts.path.strip("/").split("/")
        remainder = segments[2:]
        path = "/".join(remainder)
        if remainder and remainder[0] == "graph" and len(remainder) > 1:
            node = remainder[1]
            try:
                depth = int(node.split("-", 1)[0].removeprefix("n")) + 1
            except ValueError:
                depth = 0
            return node, depth
        if remainder and remainder[0] == "event":
            return "event-response", 0
        return (path.replace("/", "-") or "task-start"), 0


def _git_state() -> tuple[str, bool]:
    root = Path(__file__).parents[2]
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return commit, dirty


def mock_provider_selection() -> RunnerProviderSelection:
    return RunnerProviderSelection(
        identity_for=lambda profile: ProviderIdentity(
            name="mock",
            model_id=f"mock/{profile.value}-v1",
            provider_route="mock-local-no-network",
            execution_boundary="local_mock",
        ),
        build=lambda manifest, profile: MockProvider(profile),
    )


def local_fake_provider_selection(
    *,
    scenario: FakeScenario = "valid",
    delay_seconds: float = 0.1,
) -> RunnerProviderSelection:
    """Build the live-shaped adapter against an isolated in-process local server."""

    model_id = "fake/exact-model-v1"
    provider_route = "FakeLocal"

    def identity_for(profile: MockProfile) -> ProviderIdentity:
        return ProviderIdentity(
            name="openrouter",
            model_id=model_id,
            provider_route=provider_route,
            execution_boundary="local_fake",
        )

    def build(manifest: TrialManifest, profile: MockProfile) -> Provider:
        fake_app = create_fake_openrouter_app(
            profile,
            model_id=model_id,
            provider_route=provider_route,
            scenario=scenario,
            delay_seconds=delay_seconds,
        )
        endpoint = "http://127.0.0.1:8999/api/v1/chat/completions"
        return OpenRouterProvider(
            LiveProviderControls(
                transport_mode="local_fake",
                model_id=model_id,
                provider_route=provider_route,
                max_output_tokens=512,
                max_reasoning_tokens=512,
            ),
            httpx.AsyncClient(
                transport=FakeOpenRouterTransport(fake_app, scenario)
            ),
            endpoint=endpoint,
        )

    return RunnerProviderSelection(identity_for=identity_for, build=build)


def authorized_openrouter_selection(
    authorization: PaidRunAuthorization,
    *,
    credential_loader: Callable[[], str],
    network_isolation: HostedIsolationEvidence,
    client_factory: Callable[[], httpx.AsyncClient] | None = None,
) -> RunnerProviderSelection:
    """Construct a hosted path only from an exact external authorization object."""

    network_isolation.assert_current(
        evidence_id=authorization.dual_layer_egress_evidence_id,
        endpoint=HOSTED_OPENROUTER_ENDPOINT,
    )

    def identity_for(profile: MockProfile) -> ProviderIdentity:
        return ProviderIdentity(
            name="openrouter",
            model_id=authorization.model_id,
            provider_route=authorization.provider_route,
            execution_boundary="hosted_authorized",
        )

    def build(manifest: TrialManifest, profile: MockProfile) -> Provider:
        if (
            manifest.model_id != authorization.model_id
            or manifest.provider_route != authorization.provider_route
            or manifest.price_snapshot_id != authorization.price_snapshot.snapshot_id
        ):
            raise ValueError("manifest drifted from paid-run authorization")
        client = (
            client_factory()
            if client_factory is not None
            else httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        )
        return OpenRouterProvider(
            LiveProviderControls(
                execution_mode=ExecutionMode.LIVE,
                allow_paid=True,
                paid_gate_approved=True,
                authorization_id=authorization.authorization_id,
                model_id=authorization.model_id,
                provider_route=authorization.provider_route,
                price_snapshot_id=authorization.price_snapshot.snapshot_id,
                trial_cost_cap_usd=authorization.trial_cost_cap_usd,
                batch_cost_cap_usd=authorization.batch_cost_cap_usd,
                provider_spending_limit_usd=(
                    authorization.provider_spending_limit_usd
                ),
                price_snapshot_source=authorization.price_snapshot.source,
                dedicated_credential_confirmed=True,
                worst_case_reservation_id=authorization.authorization_id,
                dual_layer_egress_evidence_id=(
                    authorization.dual_layer_egress_evidence_id
                ),
                kill_switch_id=authorization.kill_switch_id,
                artifact_policy_id=authorization.artifact_policy_id,
                max_output_tokens=authorization.max_output_tokens_per_call,
                max_reasoning_tokens=authorization.max_reasoning_tokens_per_call,
            ),
            client,
            credential_loader=credential_loader,
        )

    return RunnerProviderSelection(
        identity_for=identity_for,
        build=build,
        authorization=authorization,
        price_snapshot=authorization.price_snapshot,
        network_isolation=network_isolation,
    )
