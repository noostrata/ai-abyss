"""Machine-readable calibration protocol and deterministic run-matrix generation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from src.benchmark.enums import Condition, MockProfile
from src.benchmark.models import ContractModel, Identifier, content_sha256
from src.benchmark.providers.base import TRAJECTORY_POLICY_VERSION

PROTOCOL_PATH = Path(__file__).parents[2] / "protocol" / "calibration-v1.json"
GENERATED_MATRIX_PATH = (
    Path(__file__).parents[2]
    / "protocol"
    / "generated"
    / "calibration-v1-matrix.json"
)


class ProtocolPair(ContractModel):
    contrast_id: Identifier
    condition_a: Condition
    condition_b: Condition
    qualification_profile: MockProfile
    primary_outcomes: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def matched_contrast(self) -> ProtocolPair:
        allowed = {
            (Condition.FINITE_GRAPH_CONTROL, Condition.RECURSIVE_TRAP),
            (Condition.INERT_INJECTION_CONTROL, Condition.SYNTHETIC_INJECTION),
        }
        if (self.condition_a, self.condition_b) not in allowed:
            raise ValueError("calibration contrast is not a declared matched pair")
        return self


class SpendingProtocol(ContractModel):
    maximum_trials: int = Field(ge=1)
    maximum_calls_per_trial: int = Field(ge=1)
    maximum_output_tokens_per_call: int = Field(ge=1)
    maximum_reasoning_tokens_per_call: int = Field(ge=0)
    maximum_trial_cost_usd: float = Field(gt=0)
    maximum_batch_cost_usd: float = Field(gt=0)
    provider_limit_must_not_exceed_usd: float = Field(gt=0)


class CalibrationProtocol(ContractModel):
    protocol_schema_version: Literal["1.0.0"]
    protocol_id: Identifier
    protocol_version: Identifier
    status: Literal["preauthorized_design"]
    purpose: str
    task_id: Identifier
    task_version: Identifier
    task_fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    apparatus_contract_version: Identifier
    apparatus_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    trajectory_policy_version: Literal[TRAJECTORY_POLICY_VERSION]
    scaffold_version: Identifier
    system_prompt_version: Identifier
    observation_version: Identifier
    action_schema_version: Identifier
    model_binding: Literal["exact_paid_authorization_required"]
    cache_policy: Literal["fresh_no_cache"]
    pairs: list[ProtocolPair] = Field(min_length=2, max_length=2)
    orders: list[Literal["AB", "BA"]] = Field(min_length=2, max_length=2)
    seeds: list[int] = Field(min_length=2)
    repetitions_per_order: int = Field(ge=1, le=3)
    randomization_policy: str
    primary_outcome_families: dict[str, list[str]]
    secondary_outcomes: list[str]
    censoring_policy: dict[str, str]
    infrastructure_failure_policy: str
    missing_data_policy: str
    exclusion_policy: str
    stopping_rules: list[str] = Field(min_length=1)
    spending: SpendingProtocol
    analysis_version: Identifier
    inferential_scope: str
    recognition_policy: str

    @model_validator(mode="after")
    def coherent_matrix(self) -> CalibrationProtocol:
        expected = len(self.pairs) * len(self.orders) * self.repetitions_per_order * 2
        if expected != self.spending.maximum_trials:
            raise ValueError("protocol trial ceiling must equal the generated matrix")
        if len(self.seeds) < len(self.pairs) * len(self.orders):
            raise ValueError("protocol does not provide one seed per order block")
        return self


@lru_cache(maxsize=1)
def load_experimental_protocol() -> CalibrationProtocol:
    protocol = CalibrationProtocol.model_validate_json(PROTOCOL_PATH.read_text())
    from src.benchmark.apparatus import (
        apparatus_contract_digest,
        load_apparatus_contract,
    )
    from src.benchmark.scaffold import (
        ACTION_SCHEMA_VERSION,
        OBSERVATION_VERSION,
        SCAFFOLD_VERSION,
        SYSTEM_PROMPT_VERSION,
    )
    from src.benchmark.tasks import SyntheticTask

    apparatus = load_apparatus_contract()
    task = SyntheticTask()
    if (
        protocol.apparatus_contract_version
        != apparatus["apparatus_contract_version"]
        or protocol.apparatus_contract_sha256 != apparatus_contract_digest()
        or protocol.task_id != task.metadata.task_id
        or protocol.task_version != task.metadata.version
        or protocol.task_fixture_sha256 != task.canonical_fixture_digest()
        or protocol.scaffold_version != SCAFFOLD_VERSION
        or protocol.system_prompt_version != SYSTEM_PROMPT_VERSION
        or protocol.observation_version != OBSERVATION_VERSION
        or protocol.action_schema_version != ACTION_SCHEMA_VERSION
    ):
        raise ValueError("experimental protocol dependencies have drifted")
    return protocol


def experimental_protocol_digest() -> str:
    return content_sha256(PROTOCOL_PATH.read_bytes())


def generate_run_matrix(protocol: CalibrationProtocol | None = None) -> list[dict]:
    protocol = protocol or load_experimental_protocol()
    matrix: list[dict] = []
    seed_index = 0
    for pair in protocol.pairs:
        for order in protocol.orders:
            for repetition in range(protocol.repetitions_per_order):
                seed = protocol.seeds[seed_index]
                seed_index += 1
                matrix.append(
                    {
                        "pair_id": (
                            f"cal-{pair.contrast_id}-{order.lower()}-r{repetition + 1}"
                        ),
                        "contrast_id": pair.contrast_id,
                        "condition_a": pair.condition_a.value,
                        "condition_b": pair.condition_b.value,
                        "order": order,
                        "repetition": repetition + 1,
                        "seed": seed,
                        "qualification_profile": pair.qualification_profile.value,
                    }
                )
    return matrix


def write_generated_matrix(path: Path = GENERATED_MATRIX_PATH) -> Path:
    matrix = {
        "protocol_id": load_experimental_protocol().protocol_id,
        "protocol_sha256": experimental_protocol_digest(),
        "pairs": generate_run_matrix(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matrix, sort_keys=True, indent=2) + "\n")
    return path
