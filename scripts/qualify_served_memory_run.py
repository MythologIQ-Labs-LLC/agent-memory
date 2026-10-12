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

from run_served_memory_scenarios import canonical_input_digest, validate_inputs  # noqa: E402
from score_served_memory_quality import score  # noqa: E402
import run_served_memory_lifecycle_scenarios as lifecycle  # noqa: E402


def qualify(inputs: dict, gold: dict, run: dict) -> dict:
    """Reject unannotated sources, changed questions, or undeclared exclusions."""
    if type(inputs) is dict and inputs.get("schema") == lifecycle.SCHEMA:
        return _qualify_lifecycle(inputs, gold, run)
    validate_inputs(inputs)
    if type(gold) is not dict or set(gold) != {"schema", "cases"}:
        raise ValueError("invalid gold structure")
    if type(run) is not dict or set(run) != {
        "schema", "runtime_revision", "lane_id", "rows",
        "input_sha256", "execution_backend",
    }:
        raise ValueError("real-run provenance requires exact input binding and backend")
    if run["input_sha256"] != canonical_input_digest(inputs):
        raise ValueError("run executed with a different input corpus")
    if run["execution_backend"] not in ("composed-multiroute", "governed-lexical"):
        raise ValueError("invalid executed retrieval backend")
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


def _qualify_lifecycle(inputs: dict, gold: dict, run: dict) -> dict:
    """validation(771) v2: gold must agree with the executed lifecycle.

    Deleted and out-of-scope (other project or tenant) facts must be
    prohibited for every question; values superseded by a governed
    correction must be stale (or prohibited) for current-intent questions.
    """
    facts = lifecycle.lifecycle_facts(inputs)
    if type(gold) is not dict or set(gold) != {"schema", "cases"}:
        raise ValueError("invalid gold structure")
    if type(run) is not dict or set(run) != {
        "schema", "runtime_revision", "lane_id", "rows",
        "input_sha256", "execution_backend",
    }:
        raise ValueError("real-run provenance requires exact input binding and backend")
    if run["input_sha256"] != lifecycle.canonical_input_digest(inputs):
        raise ValueError("run executed with a different input corpus")
    if run["execution_backend"] not in ("composed-multiroute", "governed-lexical"):
        raise ValueError("invalid executed retrieval backend")
    by_query = {q["id"]: q for q in inputs["queries"]}
    cases = gold["cases"]
    if type(cases) is not list or set(by_query) != {c.get("id") for c in cases} \
            or len(cases) != len(by_query):
        raise ValueError("gold must cover all and only the execution scenarios")
    must_prohibit = set(facts["deleted"]) | set(facts["out_of_scope"])
    for case in cases:
        query = by_query[case["id"]]
        if (case["scenario"] != query["query"] or case["budget"] != query["budget"]
                or case["intent"] != query["intent"]):
            raise ValueError("gold/execution question, intent or budget drift")
        if set(case["relevance"]) != set(facts["fact_ids"]):
            raise ValueError("every persisted source must carry an explicit grade")
        if not must_prohibit.issubset(case["prohibited"]):
            raise ValueError("deleted and out-of-scope sources must be prohibited")
        # validation(771) R-A1: an error-corrected value was never true, so no
        # intent may credit it as answer-level evidence (grade >= 2 eligible).
        unsafe = set(case["stale"]) | set(case["prohibited"])
        if any(case["relevance"][ref] >= 2 and ref not in unsafe
               for ref in facts["error_corrected"]):
            raise ValueError("error-corrected values cannot be credited as evidence")
        if case["intent"] == "current" and not set(facts["superseded"]).issubset(
                set(case["stale"]) | set(case["prohibited"])):
            raise ValueError("superseded values must be stale for current-intent questions")
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
