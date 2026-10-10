"""Compare b854d5e LongMemEval-S rows with the accepted v6 evidence and the local v6 rerun."""
import hashlib, json, sys
repo, v6local, cand = sys.argv[1], sys.argv[2], sys.argv[3]  # cand/v6local are prefixes: <prefix>-{session,turn}.json
for g in ("session", "turn"):
    acc = json.load(open(f"{repo}/reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v6/agent_memory-{g}-24048d55e26d/evidence.json"))["native_summary"]
    def load(p):
        be = json.load(open(p))["planes"][g]["backends"]["agent_memory"]
        rows = be["rows"]
        dig = hashlib.sha256(json.dumps([[q["question_id"], q["ranked_top"], q["metrics"], q["admitted_count"], q["status"]] for q in rows], sort_keys=True).encode()).hexdigest()
        return be["aggregate"]["headline"], be["aggregate"]["metrics"], be["governance"], dig, len(rows)
    a = load(f"{cand}-{g}.json"); b = load(f"{v6local}-{g}.json")
    print(g, "headline", json.dumps(a[0], sort_keys=True), "| equals accepted v6:", a[0] == acc["headline"],
          "| all metrics == local v6:", a[1] == b[1], "| per-question digest == local v6:", a[3] == b[3], a[3][:16],
          "| governance == accepted:", a[2] == acc["governance"], "| rows", a[4])
