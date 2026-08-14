#!/usr/bin/env python3
"""Emit the first executable #275 CodeGenome/Graphify comparison report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentmem_ref.code_reality_comparator import run_code_reality_comparator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-commit", required=True)
    parser.add_argument("--fixture-dir", required=True)
    parser.add_argument("--codegenome-main-downstream", required=True)
    parser.add_argument("--codegenome-main-upstream", required=True)
    parser.add_argument("--codegenome-decoy-downstream", required=True)
    parser.add_argument("--graphify-graph", required=True)
    parser.add_argument("--output", default="code-reality-comparator.json")
    args = parser.parse_args()

    report = run_code_reality_comparator(
        agent_memory_commit=args.agent_memory_commit,
        fixture_dir=Path(args.fixture_dir),
        codegenome_main_downstream=Path(args.codegenome_main_downstream),
        codegenome_main_upstream=Path(args.codegenome_main_upstream),
        codegenome_decoy_downstream=Path(args.codegenome_decoy_downstream),
        graphify_graph=Path(args.graphify_graph),
    )
    Path(args.output).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
