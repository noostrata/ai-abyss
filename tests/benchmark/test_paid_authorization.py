from datetime import UTC, datetime, timedelta

import httpx
import pytest

from src.benchmark.apparatus import apparatus_contract_digest, load_apparatus_contract
from src.benchmark.authorization import PaidRunAuthorization
from src.benchmark.budgets import BatchBudget, PriceSnapshot
from src.benchmark.enums import Condition, ExecutionMode, MockProfile
from src.benchmark.runner import (
    BenchmarkRunner,
    PairSpec,
    authorized_openrouter_selection,
)
from src.utils.config import BenchmarkConfig, load_config


def _authorization(**updates) -> PaidRunAuthorization:
    now = datetime.now(UTC)
    contract = load_apparatus_contract()
    values = {
        "authorization_id": "auth-test-only",
        "issued_at": now - timedelta(minutes=1),
        "expires_at": now + timedelta(minutes=10),
        "operator_approval_evidence": "synthetic-test-approval",
        "credential_reference": "gitignored-test-reference",
        "software_commit": "0" * 40,
        "apparatus_contract_version": contract["apparatus_contract_version"],
        "apparatus_contract_sha256": apparatus_contract_digest(),
        "experimental_protocol_id": "protocol-test-only",
        "experimental_protocol_sha256": "1" * 64,
        "model_id": "vendor/exact-model",
        "provider_route": "VendorExact",
        "price_snapshot": PriceSnapshot(
            snapshot_id="price-test-only",
            source="synthetic-test-fixture",
            retrieved_at=now,
            model_id="vendor/exact-model",
            provider_route="VendorExact",
            prompt_usd_per_million=1,
            completion_usd_per_million=2,
            reasoning_usd_per_million=2,
        ),
        "max_trials": 2,
        "max_calls_per_trial": 20,
        "max_output_tokens_per_call": 512,
        "max_reasoning_tokens_per_call": 512,
        "trial_cost_cap_usd": 1,
        "batch_cost_cap_usd": 2,
        "provider_spending_limit_usd": 2,
        "dual_layer_egress_evidence_id": "egress-test",
        "kill_switch_id": "kill-test",
        "artifact_policy_id": "artifact-test",
    }
    values.update(updates)
    return PaidRunAuthorization(**values)


def _live_config() -> object:
    config = load_config("tests/config_test.yaml")
    config.benchmark = BenchmarkConfig(
        execution_mode=ExecutionMode.LIVE,
        allow_paid=True,
        paid_gate_approved=True,
        paid_run_authorization_id="auth-test-only",
        local_base_url="http://127.0.0.1:8443",
        callback_base_url="http://127.0.0.1:8443",
        artifact_dir=config.benchmark.artifact_dir,
        db_path=":memory:",
        provider="openrouter",
        model_id="vendor/exact-model",
        budgets=config.benchmark.budgets,
        egress_allowlist=["127.0.0.1", "localhost"],
        bind_host="127.0.0.1",
        admin_enabled=False,
    )
    return config


async def test_authorized_factory_is_inert_until_exact_clean_commit(benchmark_app):
    credential_loaded = False

    def credential_loader() -> str:
        nonlocal credential_loaded
        credential_loaded = True
        return "must-not-load"

    authorization = _authorization()
    runner = BenchmarkRunner(
        benchmark_app,
        _live_config(),
        batch=BatchBudget(authorization.batch_cost_cap_usd),
        provider_selection=authorized_openrouter_selection(
            authorization,
            credential_loader=credential_loader,
            client_factory=lambda: httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request: pytest.fail("hosted transport must remain unused")
                )
            ),
        ),
    )
    with pytest.raises(ValueError, match="authorized clean commit"):
        await runner.run_pair(
            PairSpec(
                pair_id="must-not-run",
                condition_a=Condition.CONTROL,
                condition_b=Condition.RECURSIVE_TRAP,
                profile=MockProfile.TASK_SOLVER,
                seed=1,
                order="AB",
            )
        )
    assert credential_loaded is False


def test_authorized_factory_rejects_budget_or_identity_drift(benchmark_app):
    authorization = _authorization()
    config = _live_config()
    config.benchmark.budgets.cost_usd = 1.01
    with pytest.raises(ValueError, match="does not match"):
        BenchmarkRunner(
            benchmark_app,
            config,
            batch=BatchBudget(authorization.batch_cost_cap_usd),
            provider_selection=authorized_openrouter_selection(
                authorization,
                credential_loader=lambda: "unused",
            ),
        )


def test_authorization_rejects_expiry_route_and_cap_incoherence():
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="expire"):
        _authorization(issued_at=now, expires_at=now)
    with pytest.raises(ValueError, match="price snapshot identity"):
        _authorization(
            price_snapshot=_authorization().price_snapshot.model_copy(
                update={"provider_route": "OtherRoute"}
            )
        )
    with pytest.raises(ValueError, match="batch cap"):
        _authorization(trial_cost_cap_usd=3)
