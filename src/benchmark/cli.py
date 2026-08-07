"""Local-only CLI commands. No command in this module opens the paid gate."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

from src.benchmark.drift import assert_no_drift
from src.benchmark.enums import Condition, MockProfile
from src.benchmark.export import replay_trial
from src.benchmark.protocol import generate_run_matrix, write_generated_matrix
from src.benchmark.providers.fake_openrouter import (
    create_fake_openrouter_app,
    serve_fake_openrouter,
)
from src.benchmark.qualification import run_unpaid_qualification
from src.benchmark.runner import (
    BenchmarkRunner,
    PairSpec,
    local_fake_provider_selection,
)
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


def calibration_specs() -> list[PairSpec]:
    return [
        PairSpec(
            pair_id=item["pair_id"],
            condition_a=Condition(item["condition_a"]),
            condition_b=Condition(item["condition_b"]),
            profile=MockProfile(item["qualification_profile"]),
            seed=item["seed"],
            order=item["order"],
        )
        for item in generate_run_matrix()
    ]


async def run_fake_provider_rehearsal(config_path: str | None) -> dict:
    """Run the committed calibration matrix over actual loopback TCP/HTTP."""

    config = load_config(config_path)
    artifact_root = Path(config.benchmark.artifact_dir) / "unpaid" / "fake-provider"
    config.benchmark.artifact_dir = str(artifact_root)
    app = create_benchmark_app(config_path)
    destinations: list[str] = []
    pair_summaries: list[dict] = []
    received_requests = 0
    reconciled_calls = 0
    replayed_trials = 0
    async with app.router.lifespan_context(app):
        for spec in calibration_specs():
            fake_app = create_fake_openrouter_app(spec.profile)
            async with serve_fake_openrouter(fake_app) as server:
                runner = BenchmarkRunner(
                    app,
                    config,
                    provider_selection=local_fake_provider_selection(
                        endpoint=server.endpoint,
                        request_audit=destinations,
                    ),
                )
                bundles = await runner.run_pair(spec)
            received_requests += len(fake_app.state.received_requests)
            reconciled_calls += sum(
                bundle.result.model_ledger.reconciled_calls
                for bundle in bundles.values()
            )
            for bundle in bundles.values():
                trial_dir = artifact_root / spec.pair_id / bundle.manifest.trial_id
                if replay_trial(trial_dir) != bundle:
                    raise RuntimeError("fake-provider trial replay differed")
                replayed_trials += 1
            pair_summaries.append(
                {
                    "pair_id": spec.pair_id,
                    "order": spec.order,
                    "conditions": {
                        position: bundle.manifest.condition.value
                        for position, bundle in bundles.items()
                    },
                    "terminations": {
                        position: bundle.result.termination_reason.value
                        for position, bundle in bundles.items()
                    },
                }
            )
    unique_destinations = sorted(set(destinations))
    external_destinations = [
        destination
        for destination in unique_destinations
        if urlsplit(destination).hostname not in {"127.0.0.1", "localhost"}
    ]
    if external_destinations:
        raise RuntimeError("fake-provider rehearsal attempted a non-loopback request")
    if received_requests != len(destinations) or received_requests != reconciled_calls:
        raise RuntimeError("fake-provider request, receipt, and reconciliation counts differ")
    output = {
        "execution_mode": "mock",
        "provider_boundary": "local_fake",
        "transport": "tcp_http_loopback",
        "pairs": pair_summaries,
        "trials": replayed_trials,
        "transport_requests": len(destinations),
        "server_received_requests": received_requests,
        "reconciled_calls": reconciled_calls,
        "attempted_destinations": unique_destinations,
        "external_destinations": external_destinations,
        "hosted_requests": 0,
        "credential_loaded": False,
    }
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
    fake_rehearsal = subparsers.add_parser("fake-provider-rehearsal")
    fake_rehearsal.add_argument("--config", default=None)
    replay = subparsers.add_parser("replay")
    replay.add_argument("trial_dir")
    subparsers.add_parser("protocol-matrix")
    drift = subparsers.add_parser("check-drift")
    drift.add_argument("--require-evidence", action="store_true")
    qualification = subparsers.add_parser("unpaid-qualification")
    qualification.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evidence/unpaid-qualification.json"),
    )
    arguments = parser.parse_args()
    if arguments.command == "mock-rehearsal":
        print(json.dumps(asyncio.run(run_rehearsal(arguments.config)), indent=2))
    elif arguments.command == "fake-provider-rehearsal":
        print(
            json.dumps(
                asyncio.run(run_fake_provider_rehearsal(arguments.config)),
                indent=2,
            )
        )
    elif arguments.command == "replay":
        print(replay_trial(Path(arguments.trial_dir)).model_dump_json(indent=2))
    elif arguments.command == "protocol-matrix":
        print(write_generated_matrix())
    elif arguments.command == "check-drift":
        assert_no_drift(require_evidence=arguments.require_evidence)
        print("repository contracts, documentation, matrix, and evidence are synchronized")
    elif arguments.command == "unpaid-qualification":
        print(
            json.dumps(
                run_unpaid_qualification(arguments.output),
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
