#!/usr/bin/env python3
"""Paired, per-case comparison of AMB PrecisionMemBench results of different systems.

Each ``--system LABEL=PATH`` is an AMB result file (``single-turn.json``). The script checks
that all files cover the same case ids. For each system it reports:

* correct cases, overall and per category;
* how many failures name an unexpected belief (AMB ``judge_reason``), which is a selectivity
  failure, and how many name a missing belief. AMB keeps only the first 4 reasons per case, so
  both are lower bounds;
* the mean number of memories returned per case (AMB ``answer`` "N memories retrieved");
* wins, losses and ties against ``--reference`` (default: the first system), with an exact
  McNemar p-value.

AMB's own summary metrics (precision, recall, pass classes) are copied verbatim from each file.
Nothing is rescored.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

RETRIEVED = re.compile(r"^(\d+) memories retrieved")


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--system", action="append", required=True, metavar="LABEL=PATH")
    parser.add_argument("--reference")
    args = parser.parse_args(argv)
    systems: dict[str, dict] = {}
    for spec in args.system:
        label, _, path = spec.partition("=")
        systems[label] = json.loads(Path(path).read_text(encoding="utf-8"))
    reference = args.reference or next(iter(systems))
    case_sets = {label: {r["query_id"] for r in data["results"]} for label, data in systems.items()}
    if len({frozenset(s) for s in case_sets.values()}) != 1:
        print(json.dumps({"error": "systems cover different case ids",
                          "counts": {k: len(v) for k, v in case_sets.items()}}))
        return 2
    by_case = {label: {r["query_id"]: r for r in data["results"]} for label, data in systems.items()}
    cases = sorted(case_sets[reference])
    category = {q: by_case[reference][q]["meta"]["category"] for q in cases}
    report: dict = {"cases": len(cases), "reference": reference, "systems": {}}
    for label, data in systems.items():
        rows = by_case[label]
        failed = [q for q in cases if not rows[q]["correct"]]
        returned = [int(m.group(1)) for q in cases if (m := RETRIEVED.match(str(rows[q].get("answer") or "")))]
        per_cat = defaultdict(lambda: [0, 0])
        for q in cases:
            per_cat[category[q]][1] += 1
            per_cat[category[q]][0] += bool(rows[q]["correct"])
        entry = {
            "amb_summary": {k: data.get(k) for k in ("correct", "total_queries", "accuracy", "mean_precision",
                                                     "mean_recall", "active_passes", "active_total")},
            "correct": sum(bool(rows[q]["correct"]) for q in cases),
            # AMB's judge_reason lists at most the first 4 failure reasons per case, so these
            # counts are lower bounds (a case can fail on a reason not shown).
            "failures_with_unexpected_belief_in_first4_reasons": sum("unexpected belief" in str(rows[q].get("judge_reason")) for q in failed),
            "failures_with_missing_belief_in_first4_reasons": sum("missing" in str(rows[q].get("judge_reason")).lower() for q in failed),
            "mean_memories_returned": round(sum(returned) / len(returned), 2) if returned else None,
            "per_category": {c: f"{v[0]}/{v[1]}" for c, v in sorted(per_cat.items())},
        }
        if label != reference:
            wins = sum(bool(rows[q]["correct"]) and not by_case[reference][q]["correct"] for q in cases)
            losses = sum(by_case[reference][q]["correct"] and not rows[q]["correct"] for q in cases)
            entry[f"paired_vs_{reference}"] = {"wins": wins, "losses": losses, "ties": len(cases) - wins - losses,
                                               "mcnemar_exact_p": float(f"{mcnemar_exact(wins, losses):.3g}")}
        report["systems"][label] = entry
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
