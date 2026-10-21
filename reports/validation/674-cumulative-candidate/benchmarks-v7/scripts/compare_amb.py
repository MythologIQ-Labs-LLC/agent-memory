#!/usr/bin/env python3
"""Per-case parity of an AMB PrecisionMemBench v7 EvalSummary against the accepted v6 evidence.

usage: compare_amb.py <v6-evidence-dir> <v7-single-turn.json> [v7-cross-fact.jsonl] <out.json>

Pairs by query_id. Compares the frozen L1 fields (correct, context, the nine meta fields),
the per-case retrieved context documents, timing, and the summary; reports category results
and the strict/precision/recall aggregates of both runs.
"""
import json
import sys
from pathlib import Path

args = sys.argv[1:]
v6_dir, v7_summary = Path(args[0]), Path(args[1])
v7_sidecar = Path(args[2]) if len(args) == 4 else None
out = Path(args[-1])
old = json.loads((v6_dir / "single-turn.json").read_text(encoding="utf-8"))
new = json.loads(v7_summary.read_text(encoding="utf-8"))
META = ("relevant_beliefs", "pinned_beliefs", "retrieved_questions", "retrieval_precision", "retrieval_recall",
        "category", "subcategory", "case_type", "assertions")
o = {r["query_id"]: r for r in old["results"]}
n = {r["query_id"]: r for r in new["results"]}
assert sorted(o) == sorted(n) and len(o) == len(n) == 77, (len(o), len(n))
meta_keys = sorted(set(k for r in old["results"] for k in (r.get("meta") or {})))
result = {"cases": 77, "equal_correct": 0, "equal_context": 0, "equal_meta": 0, "equal_all_L1": 0,
          "correct_v6": 0, "correct_v7": 0, "flips": [], "differing": [], "meta_keys": meta_keys,
          "by_category_v6": {}, "by_category_v7": {}, "summary_v6": {}, "summary_v7": {}, "retrieve_time_ms": {}}
t6, t7 = [], []
for qid, r7 in n.items():
    r6 = o[qid]
    eq_c = r7.get("correct") == r6.get("correct")
    eq_x = r7.get("context") == r6.get("context")
    m6, m7 = r6.get("meta") or {}, r7.get("meta") or {}
    eq_m = all(m6.get(k) == m7.get(k) for k in meta_keys)
    result["equal_correct"] += eq_c
    result["equal_context"] += eq_x
    result["equal_meta"] += eq_m
    result["equal_all_L1"] += eq_c and eq_x and eq_m
    result["correct_v6"] += bool(r6.get("correct"))
    result["correct_v7"] += bool(r7.get("correct"))
    cat = (m7.get("category") or (r7.get("category_axes") or {}).get("category") or "unknown")
    for key, row, acc in (("by_category_v6", r6, "correct_v6"), ("by_category_v7", r7, "correct_v7")):
        c = (row.get("meta") or {}).get("category") or (row.get("category_axes") or {}).get("category") or "unknown"
        d = result[key].setdefault(c, {"cases": 0, "correct": 0})
        d["cases"] += 1
        d["correct"] += bool(row.get("correct"))
    if not eq_c:
        result["flips"].append({"query_id": qid, "v6": r6.get("correct"), "v7": r7.get("correct")})
    if not (eq_c and eq_x and eq_m):
        result["differing"].append({"query_id": qid, "correct": [r6.get("correct"), r7.get("correct")],
                                    "context_equal": eq_x, "meta_diff": {k: [m6.get(k), m7.get(k)] for k in meta_keys if m6.get(k) != m7.get(k)}})
    t6.append(r6.get("retrieve_time_ms") or 0)
    t7.append(r7.get("retrieve_time_ms") or 0)
for key, summ, store in (("summary_v6", old, "summary_v6"), ("summary_v7", new, "summary_v7")):
    result[store] = {k: summ.get(k) for k in ("total_queries", "correct", "accuracy", "mean_precision", "mean_recall", "active_passes", "active_total", "avg_retrieve_time_ms", "avg_context_tokens", "ingested_docs", "ingestion_time_ms")}
result["retrieve_time_ms"] = {"v6_mean": round(sum(t6) / len(t6), 2), "v7_mean": round(sum(t7) / len(t7), 2),
                              "v6_p50": sorted(t6)[len(t6) // 2], "v7_p50": sorted(t7)[len(t7) // 2],
                              "v6_p95": sorted(t6)[int(len(t6) * 0.95)], "v7_p95": sorted(t7)[int(len(t7) * 0.95)]}
if v7_sidecar is not None and v7_sidecar.is_file():
    lines = [json.loads(line) for line in v7_sidecar.read_text(encoding="utf-8").splitlines() if line.strip()]
    v6_side = v6_dir / "cross-fact.jsonl"
    old_lines = [json.loads(line) for line in v6_side.read_text(encoding="utf-8").splitlines() if line.strip()] if v6_side.is_file() else []
    result["cross_fact"] = {"v7_lines": len(lines), "v6_lines": len(old_lines),
                            "v7_limited": sum(1 for x in lines if (x.get("limited_count") or 0) > 0),
                            "v6_limited": sum(1 for x in old_lines if (x.get("limited_count") or 0) > 0),
                            "keys": sorted(lines[0].keys()) if lines else []}
out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "differing"}, indent=1, sort_keys=True))
