"""Compare LongMemEval rows: local v6 vs local candidate vs accepted v6 evidence (native_summary)."""
import json, sys, hashlib
W, gran = sys.argv[1], sys.argv[2]
acc = json.load(open(f"{W}/rem/reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v6/agent_memory-{gran}-24048d55e26d/evidence.json"))["native_summary"]
out = {}
for tag in ("v6", "46d84ad"):
    r = json.load(open(f"{W}/lme/{tag}-{gran}.json"))
    be = r["planes"][gran]["backends"]["agent_memory"]
    agg = be["aggregate"]
    rows = be.get("rows") or be.get("questions") or []
    ranking_digest = hashlib.sha256(json.dumps([[q.get("question_id"), q.get("ranked_top"), q.get("metrics"), q.get("admitted_count"), q.get("status")] for q in rows], sort_keys=True).encode()).hexdigest() if rows else None
    out[tag] = {"evaluated": agg["evaluated_question_count"], "headline": agg["headline"], "metrics": agg["metrics"],
                "governance": be.get("governance") or agg.get("governance"), "failures": be.get("failures") or agg.get("failures"),
                "rows": len(rows), "ranking_digest": ranking_digest, "input": r["input"].get("sha256") if isinstance(r.get("input"), dict) else None}
print(f"== {gran}")
for tag, o in out.items():
    print(tag, "evaluated", o["evaluated"], "headline", json.dumps(o["headline"]), "rows", o["rows"], "rankdigest", (o["ranking_digest"] or "")[:16], "input", (o["input"] or "")[:12])
print("accepted v6 evidence headline", json.dumps(acc["headline"]), "evaluated", acc["evaluated_question_count"])
print("local v6 == candidate (all metrics):", out["v6"]["metrics"] == out["46d84ad"]["metrics"], "| rankings identical:", out["v6"]["ranking_digest"] == out["46d84ad"]["ranking_digest"])
print("local v6 headline == accepted:", out["v6"]["headline"] == acc["headline"], "| candidate headline == accepted:", out["46d84ad"]["headline"] == acc["headline"])
print("governance v6", json.dumps(out["v6"]["governance"])[:300]); print("governance cand", json.dumps(out["46d84ad"]["governance"])[:300])
print("accepted governance", json.dumps(acc.get("governance")), "failures", json.dumps(acc.get("failures")))
