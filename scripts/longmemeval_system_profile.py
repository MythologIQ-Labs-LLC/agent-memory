#!/usr/bin/env python3
"""Aggregate-only profile of LongMemEval systems on a common scored question set.

For each ``--system LABEL=PATH[:BACKEND]`` (same inputs as ``paired_longmemeval_systems.py``):

* recall_all@k, recall_any@k and ndcg_any@k for every k the evaluator reports (the context-budget
  curve), overall and per question type;
* selectivity: mean returned count relative to the corpus size;
* cost: median and p90 of per-question ingest and recall seconds, where the rows record them.

Timings are wall-clock on whatever host ran each system. Runs that shared a host are not timed
under equal load, so timings show orders of magnitude, not rankings. No gold label, answer or
corpus text is printed.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_longmemeval_rows import load_rows  # noqa: E402

KS = (1, 3, 5, 10, 30, 50)


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 4)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plane", required=True, choices=("session", "turn"))
    parser.add_argument("--system", action="append", required=True, metavar="LABEL=PATH[:BACKEND]")
    args = parser.parse_args(argv)

    systems: dict[str, dict[str, dict]] = {}
    for spec in args.system:
        label, _, rest = spec.partition("=")
        path, _, backend = rest.rpartition(":") if not Path(rest).exists() else (rest, "", "")
        systems[label] = {row["question_id"]: row for row in load_rows(Path(path), args.plane, backend)}
    common = set.intersection(*(set(rows) for rows in systems.values()))
    scored = sorted(q for q in common if all(systems[s][q]["status"] == "scored" for s in systems))
    first = next(iter(systems))
    types = defaultdict(list)
    for qid in scored:
        types[systems[first][qid]["question_type"]].append(qid)

    report: dict = {"plane": args.plane, "scored_common_questions": len(scored),
                    "type_counts": {t: len(v) for t, v in sorted(types.items())}, "systems": {}}
    for label, rows in systems.items():
        def mean(metric: str, qids: list[str]) -> float:
            return round(sum(rows[q]["metrics"][args.plane][metric] for q in qids) / len(qids), 4)

        curve = {f"{name}@{k}": mean(f"{name}@{k}", scored) for name in ("recall_all", "recall_any", "ndcg_any") for k in KS}
        by_type = {t: {f"recall_all@{k}": mean(f"recall_all@{k}", qs) for k in KS} for t, qs in sorted(types.items())}
        returned = [rows[q].get("returned_count") for q in scored if rows[q].get("returned_count") is not None]
        corpus = [rows[q].get("corpus_size") for q in scored if rows[q].get("corpus_size")]
        ratio = [rows[q]["returned_count"] / rows[q]["corpus_size"] for q in scored
                 if rows[q].get("returned_count") is not None and rows[q].get("corpus_size")]
        ingest = [rows[q]["ingest_seconds"] for q in scored if isinstance(rows[q].get("ingest_seconds"), (int, float))]
        recall = [rows[q]["recall_seconds"] for q in scored if isinstance(rows[q].get("recall_seconds"), (int, float))]
        report["systems"][label] = {
            "budget_curve": curve, "budget_curve_by_type": by_type,
            "selectivity": {"mean_returned": round(statistics.mean(returned), 2) if returned else None,
                            "mean_corpus": round(statistics.mean(corpus), 2) if corpus else None,
                            "mean_returned_over_corpus": round(statistics.mean(ratio), 4) if ratio else None},
            "cost_seconds": {"ingest_median": quantile(ingest, 0.5), "ingest_p90": quantile(ingest, 0.9),
                             "recall_median": quantile(recall, 0.5), "recall_p90": quantile(recall, 0.9),
                             "timed_questions": len(ingest)},
        }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
