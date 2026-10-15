#!/usr/bin/env python3
"""Summarize LongMemEval-S retrieval reports for the #819 return-selection comparison.

Inputs are native ``reference/run_longmemeval.py`` reports for the same plane: the baseline,
the candidate default, and (optionally) the candidate with ``return_selection=ranked_prefix``.
Output: every aggregate metric side by side, per-question-type ``recall_all@10`` and
``recall_any@1``, mean returned counts, the abstention diagnostic, and whether the
ranked-prefix run reproduces the baseline question by question (``ranked_top`` and metrics).

    python scripts/summarize_longmemeval_return_selection.py session \
        --baseline A.json --candidate C.json --ranked-prefix Crp.json --output summary.json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def backend(path: Path, plane: str) -> tuple[dict, dict]:
    report = json.loads(path.read_text(encoding="utf-8"))
    return report, report["planes"][plane]["backends"]["agent_memory"]


def by_type(rows: list[dict], plane: str) -> dict[str, dict]:
    sums: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        metrics = (row.get("metrics") or {}).get(plane)
        if not metrics:
            continue
        bucket = sums[row["question_type"]]
        bucket["n"] += 1
        for key in ("recall_all@10", "recall_any@1", "recall_all@5"):
            bucket[key] += metrics[key]
    return {t: {"n": int(v["n"]), **{k: round(v[k] / v["n"], 6) for k in v if k != "n"}} for t, v in sorted(sums.items())}


def summarize(plane: str, baseline: Path, candidate: Path, ranked_prefix: Path | None) -> dict:
    runs = {"baseline": baseline, "candidate_default": candidate}
    if ranked_prefix is not None:
        runs["candidate_ranked_prefix"] = ranked_prefix
    out: dict = {"plane": plane, "runs": {}}
    rows = {}
    for name, path in runs.items():
        report, data = backend(path, plane)
        rows[name] = {row["question_id"]: row for row in data["rows"]}
        returned = [row["returned_count"] for row in data["rows"]]
        out["runs"][name] = {
            "report": path.name,
            "agent_memory_configuration": report["execution"]["agent_memory_configuration"],
            "agent_memory_revision": report["execution"].get("agent_memory_revision"),
            "agent_memory_worktree_dirty": report["execution"].get("agent_memory_worktree_dirty"),
            "metrics": data["aggregate"]["metrics"][plane],
            "evaluated_question_count": data["aggregate"]["evaluated_question_count"],
            "abstention_diagnostic": data["aggregate"].get("abstention_diagnostic"),
            "mean_returned_count": round(sum(returned) / len(returned), 3),
            "failures": data["failures"],
            "by_question_type": by_type(data["rows"], plane),
        }
    if ranked_prefix is not None:
        base, rp = rows["baseline"], rows["candidate_ranked_prefix"]
        differing = sorted(q for q in base if base[q]["ranked_top"] != rp[q]["ranked_top"]
                           or base[q].get("metrics") != rp[q].get("metrics"))
        out["ranked_prefix_reproduces_baseline"] = {"questions": len(base), "differing": differing,
                                                    "equal": not differing and set(base) == set(rp)}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("plane", choices=("session", "turn"))
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--ranked-prefix", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = summarize(args.plane, args.baseline, args.candidate, args.ranked_prefix)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({name: {k: run["metrics"][k] for k in ("recall_any@1", "recall_all@5", "recall_all@10", "ndcg_any@10")}
                      for name, run in summary["runs"].items()}, indent=1))
    if "ranked_prefix_reproduces_baseline" in summary:
        print("ranked_prefix equal:", summary["ranked_prefix_reproduces_baseline"]["equal"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
