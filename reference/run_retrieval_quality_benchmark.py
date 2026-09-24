#!/usr/bin/env python
"""Emit the deterministic RC retrieval-quality benchmark artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentmem_ref.harness.retrieval_quality_benchmark import run_benchmark


REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURE = REFERENCE_ROOT / "fixtures" / "benchmarks" / "rc-retrieval-quality-v1.json"
DEFAULT_RUNTIME_CONFIG = (
    REFERENCE_ROOT
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--runtime-config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_benchmark(
        fixture_path=Path(args.fixture).resolve(),
        runtime_config_path=Path(args.runtime_config).resolve(),
        agent_memory_revision=args.agent_memory_revision,
    )

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

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
