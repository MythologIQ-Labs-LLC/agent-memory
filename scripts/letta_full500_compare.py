"""Paired comparison for the Letta 0.16.8 archival LongMemEval-S full-500 run (#810), plus the
subset50 overlap check (bridge 0.1.0 runs vs the 0.1.1 full-500 run on the same questions).
Aggregate output only.

Paired statistics are on the questions scored by every system: exact McNemar on full-correct
outcomes, paired bootstrap of the mean difference (10,000 resamples, seed 0).
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
BACKEND = "letta_archival_local"


def rows(path: Path) -> dict:
    return {r["question_id"]: r for r in map(json.loads, path.read_text().splitlines())}


def metric(row: dict, plane: str, name: str) -> float:
    m = row["metrics"]
    return m.get(plane, m)[name]


def mcnemar(w: int, l: int) -> float:
    n = w + l
    return 1.0 if not n else min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)


def bootstrap(d: list[float], n: int = 10000, seed: int = 0) -> list[float]:
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return [round(means[int(0.025 * n)], 4), round(means[int(0.975 * n) - 1], 4)]


def paired(a: dict, b: dict, qs: list, plane: str, k: str) -> dict:
    d = [metric(a[q], plane, k) - metric(b[q], plane, k) for q in qs]
    w = sum(metric(a[q], plane, k) == 1 and metric(b[q], plane, k) < 1 for q in qs)
    l = sum(metric(a[q], plane, k) < 1 and metric(b[q], plane, k) == 1 for q in qs)
    return {"letta": round(sum(metric(a[q], plane, k) for q in qs) / len(qs), 6),
            "other": round(sum(metric(b[q], plane, k) for q in qs) / len(qs), 6),
            "letta_full_wins": w, "other_full_wins": l, "exact_mcnemar_p": float(f"{mcnemar(w, l):.3g}"),
            "delta_mean": round(sum(d) / len(d), 4), "delta_95ci_bootstrap": bootstrap(d)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--letta", type=Path, required=True, help="full-500 run directory")
    ap.add_argument("--subset", type=Path, nargs="+", required=True, help="subset50 run directories (bridge 0.1.0)")
    ap.add_argument("--controls", type=Path, required=True, help="controls-500.json.gz (frozen Agent Memory)")
    ap.add_argument("--hindsight", type=Path, required=True, help="Hindsight full-500 run directory")
    ap.add_argument("--mempalace", type=Path, required=True, help="MemPalace full-500 run directory")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    am = json.load(gzip.open(a.controls))
    report = {"backend": BACKEND, "planes": {}}
    for plane in PLANES:
        L = rows(a.letta / f"{plane}.{BACKEND}.rows.jsonl")
        peers = {"agent_memory": {r["question_id"]: r for r in am["planes"][plane]["backends"]["agent_memory"]["rows"]},
                 "hindsight_chunks_onnx": rows(a.hindsight / f"{plane}.hindsight_chunks_onnx.rows.jsonl"),
                 "mempalace_default_local": rows(a.mempalace / f"{plane}.mempalace_default_local.rows.jsonl")}
        if len(L) != 500 or any(set(p) != set(L) for p in peers.values()):
            raise SystemExit(f"{plane}: question sets differ")
        scored = sorted(q for q, r in L.items() if r["status"] == "scored")
        if any(p[q]["status"] != "scored" for p in peers.values() for q in scored):
            raise SystemExit(f"{plane}: scored sets differ")
        overlap = {}
        for sub in a.subset:
            S = rows(sub / f"{plane}.{BACKEND}.rows.jsonl")
            qs = sorted(S)
            sc = [q for q in qs if S[q]["status"] == "scored"]
            overlap[sub.name] = {"questions": len(qs), "scored": len(sc),
                                 "ranked_list_differs": sum(S[q]["ranked_top"] != L[q]["ranked_top"] for q in qs),
                                 "metric_differs_scored": {k: sum(metric(S[q], plane, k) != metric(L[q], plane, k) for q in sc) for k in KS},
                                 "same_returned_set_when_order_differs": sum(S[q]["ranked_top"] != L[q]["ranked_top"] and set(S[q]["ranked_top"]) == set(L[q]["ranked_top"]) for q in qs)}
        report["planes"][plane] = {
            "completed": len(L), "scored": len(scored),
            "failures": {"runtime_error": sum(bool(r.get("runtime_error")) for r in L.values()),
                         "ingestion_refusals": sum(r.get("ingestion_refusals", 0) for r in L.values()),
                         "unmapped_results": sum(r.get("unmapped_result_count", 0) for r in L.values())},
            "paired": {name: {k: paired(L, P, scored, plane, k) for k in KS} for name, P in peers.items()},
            "subset50_overlap": overlap}
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    for plane, v in report["planes"].items():
        print(plane, v["completed"], v["scored"], v["failures"])
        for name, ks in v["paired"].items():
            print("  vs", name, {k: (x["letta"], x["other"], x["letta_full_wins"], x["other_full_wins"], x["exact_mcnemar_p"], x["delta_95ci_bootstrap"]) for k, x in ks.items()})
        print("  overlap", v["subset50_overlap"])


if __name__ == "__main__":
    main()
