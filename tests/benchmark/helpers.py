from src.benchmark.apparatus import apparatus_contract_digest, load_apparatus_contract
from src.benchmark.enums import AgentActionKind, Condition
from src.benchmark.models import (
    BudgetLimits,
    SamplingConfig,
    TrialManifest,
    content_sha256,
)
from src.benchmark.scaffold import OBSERVATION_VERSION, SYSTEM_PROMPT


def make_manifest(
    trial_id: str = "trial-test-001",
    condition: Condition = Condition.CONTROL,
    pair_id: str = "pair-test-001",
) -> TrialManifest:
    return TrialManifest(
        trial_id=trial_id,
        model_namespace=trial_id,
        pair_id=pair_id,
        pair_order="AB",
        pair_position="A",
        task_id="synthetic_relay_lookup",
        task_version="1.0.0",
        condition=condition,
        condition_version="conditions-1.0.0",
        benchmark_origin="http://127.0.0.1:8443",
        seed=42,
        provider="mock",
        provider_profile="task_solver",
        model_id="mock/task-solver-v1",
        scaffold_version="http-dom-1.0.0",
        prompt_version="agent-loop-1.0.0",
        observation_version=OBSERVATION_VERSION,
        tool_schema_version="browser-actions-1.0.0",
        tool_set=list(AgentActionKind),
        sampling=SamplingConfig(seed=42),
        system_prompt_sha256=content_sha256(SYSTEM_PROMPT),
        task_prompt_sha256=content_sha256("test task"),
        config_sha256="a" * 64,
        fixture_sha256="c" * 64,
        apparatus_contract_version=load_apparatus_contract()[
            "apparatus_contract_version"
        ],
        apparatus_contract_sha256=apparatus_contract_digest(),
        git_commit="b" * 40,
        git_dirty=False,
        budgets=BudgetLimits(),
        price_snapshot_id="mock-zero-cost-v1",
        synthetic_secret_sha256=content_sha256("SYNTHETIC-KEY-TEST"),
    )
