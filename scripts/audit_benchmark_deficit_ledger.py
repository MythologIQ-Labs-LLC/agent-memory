#!/usr/bin/env python3
"""Read-only, policy-neutral benchmark deficit evidence audit (#722, stage zero).

This tool does NOT compare metric values, set remediation priority, change posture,
write a ledger, accept a benchmark, or diagnose a root cause. Published reference
values must never be substituted for same-harness comparators. It audits
accountability and evidence integrity independent of any benchmark's terminology.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

SCHEMA = "agent-memory.deficit-audit/v1"
DEFAULT_LEDGER = Path("reports/benchmarks/deficits/current.json")
CLOSED_STATES = frozenset({"frontier", "closed", "resolved"})
OPEN_STATES = frozenset({"open", "blocked", "deferred"})
ALLOWED_STATES = OPEN_STATES | CLOSED_STATES
ALLOWED_FINDINGS = frozenset({"error", "review"})
# No evaluator metrics, language cues, or benchmark family names are encoded here.


def _string(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _references(value: object) -> bool:
    return type(value) is list and all(_string(item) for item in value)


def _owner(value: object) -> bool:
    return type(value) is int and value > 0


def audit(ledger: object) -> dict[str, Any]:
    """Pure, deterministic audit; never normalizes numerical benchmark evidence.

    A review finding is NOT a policy violation, architectural defect, or
    automatically approved remediation. This phase intentionally cannot gate CI
    for review findings; those decisions require #719/ADR-043 acceptance.
    """
    errors: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    seen: set[str] = set()
    stats = Counter()

    def note(level: str, code: str, deficit: str, detail: str) -> None:
        if level not in ALLOWED_FINDINGS:
            raise ValueError("unknown audit severity")
        finding = {"severity": level, "code": code, "deficit_id": deficit,
                   "message": detail}
        (errors if level == "error" else review).append(finding)

    if type(ledger) is not dict or set(ledger) != {"schema_version", "generated_from", "deficits"}:
        note("error", "invalid_envelope", "(ledger)", "Unexpected or missing top-level keys.")
        return _result(stats, errors, review)
    if ledger.get("schema_version") != "1.0.0":
        note("error", "unknown_ledger_schema", "(ledger)", "Unsupported deficit ledger schema.")
    if not _references(ledger.get("generated_from")) or not ledger["generated_from"]:
        note("error", "missing_source_provenance", "(ledger)",
             "Ledger must identify at least one source evidence reference.")
    rows = ledger.get("deficits")
    if type(rows) is not list:
        note("error", "invalid_deficit_collection", "(ledger)", "deficits must be an array.")
        return _result(stats, errors, review)
    stats["records"] = len(rows)
    for index, item in enumerate(rows):
        location = f"(row:{index})"
        if type(item) is not dict:
            note("error", "invalid_deficit", location, "Each deficit must be an object.")
            continue
        name = item.get("deficit_id")
        if not _string(name):
            note("error", "missing_deficit_id", location, "Every deficit requires an opaque ID.")
            continue
        if name in seen:
            note("error", "duplicate_deficit_id", name, "IDs must be unique.")
        seen.add(name)
        state = item.get("state")
        if not _string(state) or state not in ALLOWED_STATES:
            note("error", "unknown_state", name, "Deficit state is not understood by this audit.")
        else:
            stats[f"state:{state}"] += 1
        if not _string(item.get("benchmark_profile")) or not _string(item.get("metric")):
            note("error", "missing_profile_or_metric", name,
                 "Comparable benchmark profile and metric identity are required.")
        if not _references(item.get("evidence_refs")) or not item["evidence_refs"]:
            note("error", "missing_evidence", name, "Every deficit must cite source evidence.")
        if not _owner(item.get("owning_issue")):
            note("error", "missing_owner", name,
                 "Every recorded deficit must point to a real owning issue number.")
        if state in CLOSED_STATES:
            stats["closed_records"] += 1
            if not _references(item.get("closure_evidence")) or not item["closure_evidence"]:
                note("error", "unsupported_closure", name,
                     "Closed/frontier records need explicit closure evidence.")
        elif state in OPEN_STATES:
            stats["unresolved_records"] += 1
            if not _string(item.get("primary_stage")) or item.get("primary_stage") == "unclassified":
                note("review", "stage_unclassified", name,
                     "Root-cause stage is unknown; preserve this uncertainty during remediation.")
            if item.get("negative_control_refs") is not None and not _references(item["negative_control_refs"]):
                note("error", "invalid_negative_controls", name,
                     "Negative-control evidence references must be an array of nonempty strings.")
            elif not item.get("negative_control_refs"):
                note("review", "negative_controls_missing", name,
                     "Propose independent, generalizable negative controls before a runtime fix.")
        same_harness = item.get("same_harness_frontier")
        published = item.get("published_frontier")
        if same_harness is not None:
            if type(same_harness) is not dict or not _string(same_harness.get("system")) or "value" not in same_harness:
                note("error", "invalid_same_harness_frontier", name,
                     "A same-harness comparator requires system and native metric value.")
        if published is not None:
            if type(published) is not dict or not _string(published.get("system")) or "value" not in published:
                note("error", "invalid_published_reference", name,
                     "Published references require provenance; they are never same-harness results.")
        if item.get("posture") == "competitive_deficit" and same_harness is None:
            note("review", "frontier_not_measured", name,
                 "Do not infer a comparable competitive deficit from a published reference.")
        if item.get("posture") == "frontier_but_inadequate":
            stats["frontier_but_inadequate"] += 1
        if item.get("posture") == "architecture_gap":
            stats["architecture_gaps"] += 1
    return _result(stats, errors, review)


def _result(stats: Counter, errors: list[dict[str, str]],
            review: list[dict[str, str]]) -> dict[str, Any]:
    key = lambda item: (item["deficit_id"], item["code"], item["message"])
    return {
        "schema": SCHEMA,
        "posture": "READ_ONLY_REVIEW" if not errors else "STRUCTURAL_FAILURE",
        "counts": {k: stats[k] for k in sorted(stats)},
        "structural_errors": sorted(errors, key=key),
        "review_candidates": sorted(review, key=key),
        "automation_authority": "none",
        "benchmark_remediation_authority": "none",
        "record_mutations": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit deficit evidence, without remediation authority")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path,
                        help="Optional report path; input ledger is never modified")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.ledger.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print("Deficit audit: cannot read valid JSON ledger: " + str(error), file=sys.stderr)
        return 2
    report = audit(document)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.resolve() == args.ledger.resolve():
            print("Deficit audit refuses to overwrite the input ledger.", file=sys.stderr)
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 1 if report["structural_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
