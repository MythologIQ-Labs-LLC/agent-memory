#!/usr/bin/env python
"""Run Agent Memory's retrieval-only LoCoMo evidence diagnostic.

The LoCoMo dataset is external CC BY-NC 4.0 material and is not bundled with
Agent Memory. Supply a local dataset path obtained under appropriate terms.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentmem_ref.harness.locomo_evidence_benchmark import (
    DEFAULT_K_VALUES,
    UPSTREAM_COMMIT,
    run_benchmark,
)


REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_RUNTIME_CONFIG = (
    REFERENCE_ROOT
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)


def _csv_ints(value: str) -> tuple[int, ...]:
    rows = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not rows:
        raise argparse.ArgumentTypeError("expected one or more comma-separated integers")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--runtime-config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--upstream-commit", default=UPSTREAM_COMMIT)
    parser.add_argument("--sample", type=int, action="append", default=None)
    parser.add_argument("--categories", type=_csv_ints, default=(1, 2, 3, 4))
    parser.add_argument("--max-questions-per-sample", type=int, default=None)
    parser.add_argument("--lexical-anchor-limit", type=int, default=3)
    parser.add_argument("--k-values", type=_csv_ints, default=DEFAULT_K_VALUES)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_benchmark(
        dataset_path=Path(args.dataset).resolve(),
        runtime_config_path=Path(args.runtime_config).resolve(),
        agent_memory_revision=args.agent_memory_revision,
        upstream_commit=args.upstream_commit,
        sample_indexes=args.sample,
        categories=args.categories,
        max_questions_per_sample=args.max_questions_per_sample,
        lexical_anchor_limit=args.lexical_anchor_limit,
        k_values=args.k_values,
    )

    governance = report["governance"]
    if governance["route_authority_effect_violations"] != 0:
        raise SystemExit("LoCoMo retrieval diagnostic detected retrieval authority leakage")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
