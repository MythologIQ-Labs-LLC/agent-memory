"""Preregistered comparison for the MemPalace full-500 repeat (#810, PREREGISTRATION.md in
reports/benchmarks/runs/810-mempalace-repeat/full500). Aggregate output only.

1. Native summaries of the repeat against the original run (8887bbe).
2. Per-question agreement on the scored questions: recall_all@{5,10,50} and ranked lists.
3. Re-pairing against frozen Agent Memory with the repeat's rows: exact McNemar on full-correct
   outcomes, paired bootstrap (10,000 resamples, seed 0) of the mean difference.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
from math import comb
from pathlib import Path

PLANES = ("session", "turn")
KS = ("recall_all@5", "recall_all@10", "recall_all@50")


def rows(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        r = json.loads(line)
        out[r["question_id"]] = r
    return out


def metric(row: dict, plane: str, name: str) -> float:
    m = row["metrics"]
    return m.get(plane, m)[name]


def mcnemar(w: int, l: int) -> float:
    n = w + l
    if not n:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)


def bootstrap(d: list[float], n: int = 10000, seed: int = 0) -> list[float]:
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return [round(means[int(0.025 * n)], 4), round(means[int(0.975 * n) - 1], 4)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=Path, required=True)
    ap.add_argument("--original", type=Path, required=True)
    ap.add_argument("--controls", type=Path, required=True, help="controls-500.json.gz (frozen Agent Memory)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    am = json.load(gzip.open(a.controls))
    report = {"backend": "mempalace_default_local", "planes": {}}
    for plane in PLANES:
        name = f"{plane}.mempalace_default_local"
        rep, org = rows(a.repeat / f"{name}.rows.jsonl"), rows(a.original / f"{name}.rows.jsonl")
        if set(rep) != set(org):
            raise SystemExit(f"{plane}: question sets differ")
        AM = {r["question_id"]: r for r in am["planes"][plane]["backends"]["agent_memory"]["rows"]}
        scored = sorted(q for q, r in rep.items() if r["status"] == "scored")
        if any(org[q]["status"] != "scored" or AM[q]["status"] != "scored" for q in scored):
            raise SystemExit(f"{plane}: scored sets differ")
        s_rep = json.loads((a.repeat / f"{name}.summary.json").read_text())
        s_org = json.loads((a.original / f"{name}.summary.json").read_text())
        agreement = {
            "questions": len(rep), "scored": len(scored),
            "status_differs": sum(rep[q]["status"] != org[q]["status"] for q in rep),
            "ranked_list_differs_all": sum(rep[q]["ranked_top"] != org[q]["ranked_top"] for q in rep),
            "ranked_list_differs_scored": sum(rep[q]["ranked_top"] != org[q]["ranked_top"] for q in scored),
            "metric_differs_scored": {k: sum(metric(rep[q], plane, k) != metric(org[q], plane, k) for q in scored) for k in KS},
            "all_metrics_identical_scored": sum(rep[q]["metrics"] == org[q]["metrics"] for q in scored),
        }
        pairing = {}
        for k in KS:
            d = [metric(rep[q], plane, k) - metric(AM[q], plane, k) for q in scored]
            w = sum(metric(rep[q], plane, k) == 1 and metric(AM[q], plane, k) < 1 for q in scored)
            l = sum(metric(rep[q], plane, k) < 1 and metric(AM[q], plane, k) == 1 for q in scored)
            pairing[k] = {
                "mempalace": round(sum(metric(rep[q], plane, k) for q in scored) / len(scored), 6),
                "agent_memory": round(sum(metric(AM[q], plane, k) for q in scored) / len(scored), 6),
                "mempalace_full_wins": w, "agent_memory_full_wins": l, "exact_mcnemar_p": float(f"{mcnemar(w, l):.3g}"),
                "delta_mean": round(sum(d) / len(d), 4), "delta_95ci_bootstrap": bootstrap(d),
            }
        report["planes"][plane] = {
            "native_summary": {
                "repeat_aggregate": s_rep["aggregate"],
                "identical_to_original": {key: s_rep[key] == s_org[key] for key in ("aggregate", "by_question_type", "currentness", "failures", "question_count_completed")},
            },
            "agreement": agreement, "paired_vs_agent_memory": pairing,
        }
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({p: {"agreement": v["agreement"], "pairing": {k: (x["mempalace_full_wins"], x["agent_memory_full_wins"], x["exact_mcnemar_p"], x["delta_mean"], x["delta_95ci_bootstrap"]) for k, x in v["paired_vs_agent_memory"].items()}} for p, v in report["planes"].items()}, indent=1))


if __name__ == "__main__":
    main()
