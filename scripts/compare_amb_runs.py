#!/usr/bin/env python3
"""Compare two AMB result files case by case, ignoring only wall-clock timing fields.

Used to show that a change around the harness (the retrieval no-LLM guard, a different
host, a newer Agent Memory revision) leaves AMB's scored output unchanged. Every result
field and every summary field is compared except the timing fields named below. Exits 1
on any difference and prints each one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TIMING_RESULT_FIELDS = {"retrieve_time_ms"}
TIMING_SUMMARY_FIELDS = {"ingestion_time_ms", "avg_retrieve_time_ms"}
# run_name defaults to the output directory name, which differs between runs by design.
LABEL_SUMMARY_FIELDS = {"run_name"}


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("results"), list):
        raise SystemExit(f"{path}: not an AMB result file")
    return payload


def _strip_provider_raw(result: dict, ignore_raw: bool) -> dict:
    result = {key: value for key, value in result.items() if key not in TIMING_RESULT_FIELDS}
    if ignore_raw:
        result.pop("raw_response", None)
    return result


def compare(left: dict, right: dict, *, ignore_raw: bool) -> list[str]:
    differences: list[str] = []
    skip = TIMING_SUMMARY_FIELDS | LABEL_SUMMARY_FIELDS | {"results"}
    for key in sorted(set(left) | set(right)):
        if key in skip:
            continue
        if left.get(key) != right.get(key):
            differences.append(f"summary.{key}: {left.get(key)!r} != {right.get(key)!r}")
    left_cases = {item["query_id"]: item for item in left["results"]}
    right_cases = {item["query_id"]: item for item in right["results"]}
    if [item["query_id"] for item in left["results"]] != [item["query_id"] for item in right["results"]]:
        differences.append("case order or membership differs")
    for query_id in sorted(set(left_cases) | set(right_cases)):
        if query_id not in left_cases or query_id not in right_cases:
            differences.append(f"case {query_id}: present on one side only")
            continue
        a = _strip_provider_raw(left_cases[query_id], ignore_raw)
        b = _strip_provider_raw(right_cases[query_id], ignore_raw)
        for key in sorted(set(a) | set(b)):
            if a.get(key) != b.get(key):
                differences.append(f"case {query_id}.{key}: {a.get(key)!r} != {b.get(key)!r}")
    return differences


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument(
        "--ignore-raw-response",
        action="store_true",
        help="skip raw_response (it carries revision ids; published AMB files strip it)",
    )
    args = parser.parse_args(argv)
    left, right = _load(args.left), _load(args.right)
    differences = compare(left, right, ignore_raw=args.ignore_raw_response)
    verdict = {
        "left": str(args.left),
        "right": str(args.right),
        "cases_compared": len(left["results"]),
        "ignored_fields": sorted(TIMING_RESULT_FIELDS | TIMING_SUMMARY_FIELDS | LABEL_SUMMARY_FIELDS)
        + (["raw_response"] if args.ignore_raw_response else []),
        "differences": len(differences),
        "equal": not differences,
    }
    for line in differences:
        print(line, file=sys.stderr)
    print(json.dumps(verdict, indent=2))
    return 0 if not differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
