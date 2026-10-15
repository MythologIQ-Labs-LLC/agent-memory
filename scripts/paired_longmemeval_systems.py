#!/usr/bin/env python3
"""Paired, per-question-type comparison of LongMemEval executions of different systems.

Each ``--system LABEL=PATH[:BACKEND]`` is a one-shot ``run_longmemeval.py`` output (``.json`` /
``.json.gz``; BACKEND required) or a resumable ``<plane>.<backend>.rows.jsonl``. Only questions
scored by every system are compared, so every mean is over the same question set. Paired counts
are against ``--reference`` (the first system by default): a "win" is a question the system
retrieves fully (``recall_all@k == 1``) where the reference does not, a "loss" the reverse.

Output is aggregate only: means, per-type means, paired counts, and question ids. It prints no
gold label, answer, or corpus text. Exits 2 if any system has a runtime error or a question
scored on one side and excluded on another.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_longmemeval_rows import load_rows  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plane", required=True, choices=("session", "turn"))
    parser.add_argument("--system", action="append", required=True, metavar="LABEL=PATH[:BACKEND]")
    parser.add_argument("--reference", help="label of the reference system (default: the first)")
    parser.add_argument("--k", type=int, action="append", help="cutoffs (default 5, 10)")
    args = parser.parse_args(argv)
    ks = args.k or [5, 10]

    systems: dict[str, dict[str, dict]] = {}
    problems: list[str] = []
    for spec in args.system:
        label, _, rest = spec.partition("=")
        path, _, backend = rest.rpartition(":") if not Path(rest).exists() else (rest, "", "")
        rows = load_rows(Path(path), args.plane, backend)
        systems[label] = {row["question_id"]: row for row in rows}
        problems += [f"{label}:{row['question_id']} runtime_error" for row in rows if row.get("runtime_error")]
    reference = args.reference or next(iter(systems))
    common = set.intersection(*(set(rows) for rows in systems.values()))
    scored = sorted(q for q in common if all(systems[s][q]["status"] == "scored" for s in systems))
    problems += [f"{q}: scored on some systems only" for q in common
                 if len({systems[s][q]["status"] == "scored" for s in systems}) > 1]

    def value(label: str, qid: str, metric: str) -> float:
        return systems[label][qid]["metrics"][args.plane][metric]

    types = defaultdict(list)
    for qid in scored:
        types[systems[reference][qid]["question_type"]].append(qid)
    report = {"plane": args.plane, "reference": reference, "scored_common_questions": len(scored),
              "question_counts": {label: len(rows) for label, rows in systems.items()},
              "type_counts": {t: len(q) for t, q in sorted(types.items())}, "systems": {}}
    for label in systems:
        entry: dict = {}
        for k in ks:
            metric = f"recall_all@{k}"
            entry[metric] = round(sum(value(label, q, metric) for q in scored) / len(scored), 6)
            entry[f"ndcg_any@{k}"] = round(sum(value(label, q, f"ndcg_any@{k}") for q in scored) / len(scored), 6)
            entry[f"{metric}_by_type"] = {t: round(sum(value(label, q, metric) for q in qs) / len(qs), 3)
                                          for t, qs in sorted(types.items())}
            if label != reference:
                wins = [q for q in scored if value(label, q, metric) == 1 > value(reference, q, metric)]
                losses = [q for q in scored if value(reference, q, metric) == 1 > value(label, q, metric)]
                entry[f"{metric}_paired_vs_{reference}"] = {"wins": len(wins), "losses": len(losses)}
        report["systems"][label] = entry
    k = ks[0]
    metric = f"recall_all@{k}"
    others = [s for s in systems if s != reference]
    missed = [q for q in scored if value(reference, q, metric) < 1]
    rescued = [q for q in missed if any(value(s, q, metric) == 1 for s in others)]
    report[f"reference_misses_at_{k}"] = {
        "total": len(missed), "some_peer_full_recall": len(rescued),
        "by_type": {t: sum(1 for q in rescued if q in set(qs)) for t, qs in sorted(types.items())},
        "question_ids": rescued}
    report["problems"] = problems
    print(json.dumps(report, indent=2))
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
