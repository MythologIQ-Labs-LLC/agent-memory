#!/usr/bin/env python3
"""Per-question parity of a LongMemEval_S v7 raw report against the accepted v6 evidence.

usage: compare_lme.py <v6-evidence-dir> <v7-raw-report.json> <plane> <backend> <out.json>

Pairs by question_id. Reports: complete recall@50 (recall_all@50 == 1) over the scored
questions, required-evidence counts (gold items present in the top-50 ranking), exact
ranked_top + metrics parity, cross-fact record parity, headline aggregates, timing.
"""
import gzip
import json
import sys
from pathlib import Path

v6_dir, v7_raw, plane, backend, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], Path(sys.argv[5])
v6_report = json.loads((v6_dir / "report.json").read_text(encoding="utf-8"))
v6_rows = json.loads(gzip.open(v6_dir / "report.rows.json.gz").read())[plane][backend]
v7_report = json.loads(v7_raw.read_text(encoding="utf-8"))
v7_rows = v7_report["planes"][plane]["backends"][backend]["rows"]
b6 = v6_report["planes"][plane]["backends"][backend]
b7 = {k: v for k, v in v7_report["planes"][plane]["backends"][backend].items() if k != "rows"}

old = {r["question_id"]: r for r in v6_rows}
new = {r["question_id"]: r for r in v7_rows}
assert sorted(old) == sorted(new) and len(v6_rows) == len(v7_rows) == 500, (len(v6_rows), len(v7_rows))


def scored(row):
    return row.get("status") == "scored"


def complete(row):
    return (row.get("metrics") or {}).get(plane, {}).get("recall_all@50") == 1.0


def required_hits(row):
    gold = set(row.get("gold") or [])
    top = row.get("ranked_top") or []
    if plane == "turn":
        return len(gold & set(top[:50])), len(gold)
    return len(gold & set(top[:50])), len(gold)


result = {"plane": plane, "backend": backend, "v6_dir": str(v6_dir), "v7_raw": str(v7_raw),
          "questions": len(v7_rows), "statuses_v7": {}, "statuses_v6": {}, "scored_v6": 0, "scored_v7": 0,
          "complete50_v6": 0, "complete50_v7": 0, "required_v6": [0, 0], "required_v7": [0, 0],
          "ranked_top_equal": 0, "metrics_equal": 0, "cross_fact_equal": 0, "runtime_errors_v6": 0, "runtime_errors_v7": 0,
          "lost_complete": [], "gained_complete": [], "lost_required_evidence": [], "gained_required_evidence": [],
          "differing_questions": [], "headline_v6": {}, "headline_v7": {}, "timing_v6": b6.get("timing"), "timing_v7": b7.get("timing")}
for qid, r7 in new.items():
    r6 = old[qid]
    result["statuses_v7"][r7.get("status")] = result["statuses_v7"].get(r7.get("status"), 0) + 1
    result["statuses_v6"][r6.get("status")] = result["statuses_v6"].get(r6.get("status"), 0) + 1
    result["runtime_errors_v6"] += r6.get("runtime_error") is not None
    result["runtime_errors_v7"] += r7.get("runtime_error") is not None
    if r7["ranked_top"] == r6["ranked_top"]:
        result["ranked_top_equal"] += 1
    if r7["metrics"] == r6["metrics"]:
        result["metrics_equal"] += 1
    if r7.get("cross_fact") == r6.get("cross_fact"):
        result["cross_fact_equal"] += 1
    if r7["ranked_top"] != r6["ranked_top"] or r7["metrics"] != r6["metrics"]:
        result["differing_questions"].append({"question_id": qid, "type": r7.get("question_type"),
                                              "v6_top10": r6["ranked_top"][:10], "v7_top10": r7["ranked_top"][:10],
                                              "v6_metrics": r6["metrics"], "v7_metrics": r7["metrics"],
                                              "v7_cross_fact": r7.get("cross_fact"), "v6_cross_fact": r6.get("cross_fact")})
    s6, s7 = scored(r6), scored(r7)
    result["scored_v6"] += bool(s6)
    result["scored_v7"] += bool(s7)
    if s6:
        c6 = complete(r6); result["complete50_v6"] += c6
        h, t = required_hits(r6); result["required_v6"][0] += h; result["required_v6"][1] += t
    if s7:
        c7 = complete(r7); result["complete50_v7"] += c7
        h7, t7 = required_hits(r7); result["required_v7"][0] += h7; result["required_v7"][1] += t7
    if s6 and s7:
        if complete(r6) and not complete(r7):
            result["lost_complete"].append(qid)
        if complete(r7) and not complete(r6):
            result["gained_complete"].append(qid)
        if required_hits(r7)[0] < required_hits(r6)[0]:
            result["lost_required_evidence"].append({"question_id": qid, "v6": required_hits(r6), "v7": required_hits(r7)})
        if required_hits(r7)[0] > required_hits(r6)[0]:
            result["gained_required_evidence"].append({"question_id": qid, "v6": required_hits(r6), "v7": required_hits(r7)})
agg6, agg7 = b6.get("aggregate") or {}, b7.get("aggregate") or {}
result["headline_v6"] = agg6
result["headline_v7"] = agg7
result["aggregate_equal"] = agg6 == agg7
result["by_question_type_equal"] = b6.get("by_question_type") == b7.get("by_question_type")
result["currentness_equal"] = b6.get("currentness") == b7.get("currentness")
result["cross_fact_summary_equal"] = b6.get("cross_fact_summary") == b7.get("cross_fact_summary")
result["governance_equal"] = b6.get("governance") == b7.get("governance")
result["differing_count"] = len(result["differing_questions"])
out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
summary = {k: v for k, v in result.items() if k not in ("differing_questions", "headline_v6", "headline_v7", "timing_v6", "timing_v7")}
print(json.dumps(summary, indent=1, sort_keys=True))
