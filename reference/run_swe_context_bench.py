#!/usr/bin/env python
"""Run the Agent Memory SWE Context Bench Lite retrieval adapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentmem_ref.harness.swe_context_bench import run_benchmark


REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_RUNTIME_CONFIG = (
    REFERENCE_ROOT
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--benchmark-root", required=True)
    parser.add_argument("--runtime-config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--lexical-anchor-limit", type=int, default=3)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_benchmark(
        manifest_path=Path(args.manifest).resolve(),
        benchmark_root=Path(args.benchmark_root).resolve(),
        runtime_config_path=Path(args.runtime_config).resolve(),
        agent_memory_revision=args.agent_memory_revision,
        lexical_anchor_limit=args.lexical_anchor_limit,
    )

    governance = report["governance"]
    if governance["corpus_mutation_failures"] != 0:
        raise SystemExit("SWE Context benchmark detected candidate-corpus mutation during query evaluation")
    if governance["route_authority_effect_violations"] != 0:
        raise SystemExit("SWE Context benchmark detected retrieval authority leakage")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
