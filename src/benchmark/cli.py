"""Local-only CLI commands. No command in this module opens the paid gate."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from src.benchmark.enums import Condition, MockProfile
from src.benchmark.export import replay_trial
from src.benchmark.protocol import write_generated_matrix
from src.benchmark.runner import BenchmarkRunner, PairSpec
from src.main import create_benchmark_app
from src.utils.config import load_config


def rehearsal_specs() -> list[PairSpec]:
    templates = [
        ("task-finite", Condition.CONTROL, Condition.FINITE_GRAPH_CONTROL, MockProfile.TASK_SOLVER),
        ("task-recursive", Condition.CONTROL, Condition.RECURSIVE_TRAP, MockProfile.TASK_SOLVER),
        ("follow-recursive", Condition.CONTROL, Condition.RECURSIVE_TRAP, MockProfile.RECURSIVE_FOLLOWER),
        (
            "follow-finite-recursive",
            Condition.FINITE_GRAPH_CONTROL,
            Condition.RECURSIVE_TRAP,
            MockProfile.RECURSIVE_FOLLOWER,
        ),
        ("follow-injection", Condition.CONTROL, Condition.SYNTHETIC_INJECTION, MockProfile.INJECTION_FOLLOWER),
        ("recover-recursive", Condition.CONTROL, Condition.RECURSIVE_TRAP, MockProfile.RECOGNISE_AND_RECOVER),
        ("egress", Condition.CONTROL, Condition.RECURSIVE_TRAP, MockProfile.EGRESS_ATTACKER),
        ("invalid", Condition.CONTROL, Condition.SYNTHETIC_INJECTION, MockProfile.INVALID_ACTION),
        ("refusal", Condition.CONTROL, Condition.RECURSIVE_TRAP, MockProfile.REFUSAL),
    ]
    specs: list[PairSpec] = []
    for index, (name, condition_a, condition_b, profile) in enumerate(templates):
        for order in ("AB", "BA"):
            specs.append(
                PairSpec(
                    pair_id=f"mock-{name}-{order.lower()}",
                    condition_a=condition_a,
                    condition_b=condition_b,
                    profile=profile,
                    seed=10_000 + index,
                    order=order,
                )
            )
    return specs


async def run_rehearsal(config_path: str | None) -> dict:
    config = load_config(config_path)
    app = create_benchmark_app(config_path)
    summaries: list[dict] = []
    hosted_requests = 0
    async with app.router.lifespan_context(app):
        runner = BenchmarkRunner(app, config)
        for spec in rehearsal_specs():
            bundles = await runner.run_pair(spec)
            hosted_requests += sum(
                bundle.result.model_ledger.calls
                for bundle in bundles.values()
                if bundle.manifest.provider != "mock"
            )
            summaries.append(
                {
                    "pair_id": spec.pair_id,
                    "order": spec.order,
                    "results": {
                        position: {
                            "condition": bundle.manifest.condition.value,
                            "termination": bundle.result.termination_reason.value,
                            "utility": bundle.result.utility.status.value,
                            "graph_entered": bundle.result.trajectory.graph_entered,
                            "completed_cycles": bundle.result.trajectory.completed_cycles,
                            "exact_secret_submitted": (
                                bundle.result.trajectory.exact_secret_submitted
                            ),
                        }
                        for position, bundle in bundles.items()
                    },
                }
            )
    output = {
        "execution_mode": "mock",
        "hosted_requests": hosted_requests,
        "pairs": summaries,
    }
    artifact_root = Path(config.benchmark.artifact_dir)
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "rehearsal_summary.json").write_text(
        json.dumps(output, sort_keys=True, indent=2) + "\n"
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Abyss local benchmark tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    rehearsal = subparsers.add_parser("mock-rehearsal")
    rehearsal.add_argument("--config", default=None)
    replay = subparsers.add_parser("replay")
    replay.add_argument("trial_dir")
    subparsers.add_parser("protocol-matrix")
    arguments = parser.parse_args()
    if arguments.command == "mock-rehearsal":
        print(json.dumps(asyncio.run(run_rehearsal(arguments.config)), indent=2))
    elif arguments.command == "replay":
        print(replay_trial(Path(arguments.trial_dir)).model_dump_json(indent=2))
    elif arguments.command == "protocol-matrix":
        print(write_generated_matrix())


if __name__ == "__main__":
    main()
