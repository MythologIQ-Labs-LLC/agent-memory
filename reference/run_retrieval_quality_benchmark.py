#!/usr/bin/env python
"""Emit deterministic RC retrieval-quality and optional continuous-regression evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentmem_ref.harness.retrieval_quality_benchmark import run_benchmark
from retrieval_regression import load_json, run_continuous_regression


REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURE = REFERENCE_ROOT / "fixtures" / "benchmarks" / "rc-retrieval-quality-v1.json"
DEFAULT_RUNTIME_CONFIG = (
    REFERENCE_ROOT
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)
DEFAULT_TARGETS = (
    REFERENCE_ROOT
    / "fixtures"
    / "benchmarks"
    / "retrieval-regression-targets-v1.json"
)
DEFAULT_HISTORICAL_BASELINE = (
    REFERENCE_ROOT
    / "fixtures"
    / "benchmarks"
    / "historical-jin-100-gold-edges-v1.json"
)


def _governance_gate(report: dict) -> None:
    governance = report["governance"]
    required_zero_keys = [
        "lexical_forbidden_admission_failures",
        "multi_route_forbidden_admission_failures",
        "multi_route_forbidden_ranked_failures",
        "route_authority_effect_violations",
    ]
    required_zero_keys.extend(
        key
        for key in (
            "controlled_typed_graph_forbidden_admission_failures",
            "controlled_typed_graph_forbidden_ranked_failures",
            "controlled_typed_graph_authority_effect_violations",
        )
        if key in governance
    )
    if any(governance[key] != 0 for key in required_zero_keys):
        raise SystemExit("retrieval benchmark detected a governance failure")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--runtime-config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--continuous-regression",
        action="store_true",
        help="enrich the canonical benchmark with F1, replay, targets, and comparison evidence",
    )
    parser.add_argument("--targets", default=str(DEFAULT_TARGETS))
    parser.add_argument(
        "--historical-baseline",
        default=str(DEFAULT_HISTORICAL_BASELINE),
    )
    parser.add_argument("--baseline-report")
    args = parser.parse_args()

    fixture_path = Path(args.fixture).resolve()
    runtime_config_path = Path(args.runtime_config).resolve()
    if args.continuous_regression:
        report = run_continuous_regression(
            fixture_path=fixture_path,
            runtime_config_path=runtime_config_path,
            agent_memory_revision=args.agent_memory_revision,
            targets=load_json(Path(args.targets).resolve()) or {},
            historical_baseline=load_json(Path(args.historical_baseline).resolve()),
            baseline_report=(
                load_json(Path(args.baseline_report).resolve())
                if args.baseline_report
                else None
            ),
        )
        regression = report["continuous_regression"]
        if not regression["same_process_repeat_consistent"]:
            raise SystemExit("retrieval regression same-process replay diverged")
        if not regression["fresh_runtime_reconstruction_consistent"]:
            raise SystemExit("retrieval regression fresh reconstruction diverged")
        persisted = regression["persisted_restart"]
        if not regression["persisted_restart_exercised_by_this_runner"]:
            raise SystemExit("retrieval regression did not exercise persisted restart")
        if not persisted["canonical_state_digest_consistent"]:
            raise SystemExit("retrieval regression SQLite state digest changed across restart")
        if not persisted["recall_result_consistent"]:
            raise SystemExit("retrieval regression recall changed across persisted restart")
        if not regression["targets"]["all_expectations_met"]:
            raise SystemExit("retrieval regression target profile failed")
    else:
        report = run_benchmark(
            fixture_path=fixture_path,
            runtime_config_path=runtime_config_path,
            agent_memory_revision=args.agent_memory_revision,
        )

    _governance_gate(report)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
