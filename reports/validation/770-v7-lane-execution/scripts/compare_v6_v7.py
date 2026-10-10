#!/usr/bin/env python3
"""Question-by-question comparison of imported -v7 lane evidence with accepted -v6 evidence.

Reads committed evidence only (no execution). For every LongMemEval (backend, plane) row and
every AMB provider row, compares each question/case on its scored fields, the aggregates, the
cross-fact records, governance, and reports efficiency separately (never gated).
usage: compare_v6_v7.py <repo_root>
"""
import gzip, json, sys
from pathlib import Path

root = Path(sys.argv[1])
LME, AMB = root / "reports/benchmarks/longmemeval", root / "reports/benchmarks/amb"
out = {"longmemeval": {}, "amb": {}}


def one(base, pattern):
    found = sorted(p for p in base.glob(pattern) if p.is_dir())
    assert len(found) == 1, (base, pattern, found)
    return found[0]


for backend in ("agent_memory", "lexical_overlap", "mem0_explicit"):
    for plane in ("session", "turn"):
        dirs = {v: one(LME / f"longmemeval-s-retrieval-parity-{v}", f"{backend}-{plane}-*") for v in ("v6", "v7")}
        rep = {v: json.loads((d / "report.json").read_text()) for v, d in dirs.items()}
        rows = {}
        for v, d in dirs.items():
            with gzip.open(d / "report.rows.json.gz") as h:
                rows[v] = {r["question_id"]: r for r in json.loads(h.read())[plane][backend]}
        be = {v: rep[v]["planes"][plane]["backends"][backend] for v in rep}
        ids = sorted(set(rows["v6"]) | set(rows["v7"]))
        changed = {f: [q for q in ids if rows["v6"].get(q, {}).get(f) != rows["v7"].get(q, {}).get(f)]
                   for f in ("ranked_top", "metrics", "cross_fact", "admitted_count", "status", "error")}
        rank_moves = sum(1 for q in ids if rows["v6"].get(q, {}).get("ranked_top") != rows["v7"].get(q, {}).get("ranked_top"))
        agg_v6, agg_v7 = be["v6"].get("aggregate", {}), be["v7"].get("aggregate", {})
        ev = {v: json.loads((d / "evidence.json").read_text()) for v, d in dirs.items()}
        out["longmemeval"][f"{backend}/{plane}"] = {
            "questions": [len(rows["v6"]), len(rows["v7"])],
            "changed_questions_by_field": {f: len(qs) for f, qs in changed.items()},
            "changed_examples": {f: qs[:5] for f, qs in changed.items() if qs},
            "ranked_top_changes": rank_moves,
            "aggregate_equal": agg_v6 == agg_v7,
            "headline": agg_v7.get("headline"),
            "aggregate_metric_keys": sorted((agg_v7.get("metrics") or {}).keys())[:40],
            "governance_equal": be["v6"].get("governance") == be["v7"].get("governance"),
            "governance_v7": be["v7"].get("governance"),
            "cross_fact_summary_equal": be["v6"].get("cross_fact_summary") == be["v7"].get("cross_fact_summary"),
            "efficiency": {v: {k: be[v].get("timing", {}).get(k) for k in ("ingest_seconds_total", "recall_seconds_max", "wall_seconds", "recall_seconds_mean", "recall_seconds_p50", "recall_seconds_p95")}
                           | {"execution_wall_seconds": rep[v]["execution"].get("wall_seconds")} for v in rep},
            "v7_dir": str(dirs["v7"].relative_to(root)),
            "v7_runtime_baseline": ev["v7"].get("system", {}).get("runtime_baseline"),
            "v7_workflow_run_id": ev["v7"].get("execution", {}).get("workflow_run_id"),
            "v7_lane_digest": ev["v7"].get("execution", {}).get("lane_digest_sha256"),
        }

for provider in ("agent-memory", "bm25", "mem0-explicit"):
    dirs = {v: one(AMB / f"amb-precisionmembench-retrieval-{v}", f"{provider}-*") for v in ("v6", "v7")}
    st = {v: json.loads((d / "single-turn.json").read_text()) for v, d in dirs.items()}
    res = {v: {r["query_id"]: r for r in st[v]["results"]} for v in st}
    ids = sorted(set(res["v6"]) | set(res["v7"]))
    changed = {f: [q for q in ids if res["v6"].get(q, {}).get(f) != res["v7"].get(q, {}).get(f)] for f in ("correct", "context", "meta")}
    ev = {v: json.loads((d / "evidence.json").read_text()) for v, d in dirs.items()}
    ns = {v: ev[v].get("native_summary", {}) for v in ev}
    timing = ("ingestion_time_ms", "mean_retrieve_ms")
    side = {v: (d / "cross-fact.jsonl") for v, d in dirs.items()}
    out["amb"][provider] = {
        "queries": [len(res["v6"]), len(res["v7"])],
        "changed_queries_by_field": {f: len(qs) for f, qs in changed.items()},
        "native_summary_equal_excluding_timing": {k: v for k, v in ns["v6"].items() if k not in timing} == {k: v for k, v in ns["v7"].items() if k not in timing},
        "native_summary_v7": {k: v for k, v in ns["v7"].items() if k not in timing},
        "efficiency": {v: {k: ns[v].get(k) for k in timing} for v in ns},
        "cross_fact_sidecar_byte_identical": (side["v6"].read_bytes() == side["v7"].read_bytes()) if side["v6"].exists() else None,
        "v7_dir": str(dirs["v7"].relative_to(root)),
        "v7_runtime_baseline": ev["v7"].get("system", {}).get("runtime_baseline"),
        "v7_workflow_run_id": ev["v7"].get("execution", {}).get("workflow_run_id"),
        "v7_lane_digest": ev["v7"].get("execution", {}).get("lane_digest_sha256"),
    }
print(json.dumps(out, indent=1, ensure_ascii=False))
