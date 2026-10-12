#!/usr/bin/env python3
"""#771: verify label provenance before scoring a real governed recall run.

This is a POST-RUN step. It cannot influence ranking or admission because it
receives a completed run manifest, not a runtime instance or controller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_served_memory_scenarios import validate_inputs  # noqa: E402
from score_served_memory_quality import score  # noqa: E402


def qualify(inputs: dict, gold: dict, run: dict) -> dict:
    """Reject unannotated sources, changed questions, or undeclared exclusions."""
    validate_inputs(inputs)
    if type(gold) is not dict or set(gold) != {"schema", "cases"}:
        raise ValueError("invalid gold structure")
    if type(run) is not dict or set(run) != {
        "schema", "runtime_revision", "lane_id", "rows",
    }:
        raise ValueError("invalid run structure")
    scenarios = inputs["queries"]
    cases = gold["cases"]
    if type(cases) is not list or len(cases) != len(scenarios):
        raise ValueError("gold must cover all and only the execution scenarios")
    expected_source_ids = {w["id"] for w in inputs["writes"]}
    excluded_source_ids = {
        w["id"] for w in inputs["writes"]
        if w["project"] != inputs["project"]
    }
    by_query = {q["id"]: q for q in scenarios}
    if len(by_query) != len(scenarios):
        raise ValueError("duplicate scenario queries")
    if set(by_query) != {c["id"] for c in cases}:
        raise ValueError("gold and execution query identities differ")
    for case in cases:
        query = by_query[case["id"]]
        if (case["scenario"] != query["query"]
                or case["budget"] != query["budget"]
                or case["intent"] != query["intent"]):
            raise ValueError("gold/execution question, intent or budget drift")
        if set(case["relevance"]) != expected_source_ids:
            raise ValueError("every persisted source must carry an explicit grade")
        if not excluded_source_ids.issubset(case["prohibited"]):
            raise ValueError("out-of-scope project sources must be prohibited")
    return score(gold, run)


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing to overwrite prior qualification output")
    raw = {
        "execution_inputs": args.inputs.read_bytes(),
        "gold": args.gold.read_bytes(),
        "runs": args.runs.read_bytes(),
    }
    report = qualify(
        json.loads(raw["execution_inputs"]),
        json.loads(raw["gold"]),
        json.loads(raw["runs"]),
    )
    report["input_digests"] = {
        name + "_sha256": _hash(body) for name, body in raw.items()
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
