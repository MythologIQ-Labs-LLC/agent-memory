"""Diagnostic only: run the dev cohort through the real facade (no MCP) and dump
per-item route provenance / ranking evidence so the padding source is visible."""
import json, sys, tempfile
from pathlib import Path
from agentmem_ref.host_activation import open_qualified_memory
cases = json.load(open(sys.argv[1]))
out = {}
with tempfile.TemporaryDirectory() as d:
    def op():
        return open_qualified_memory(Path(d)/"store", tenant=cases["tenant"], actor_id="agent:diag",
                                     scope=cases["scope"], purpose="gate2 diagnostic")
    refs = {}
    with op() as m:
        for r in cases["records"]:
            o = m.remember(r["key"], r["text"], source_ref="mcp:agent-observation")
            refs[o["fact_uuid"]] = r["key"]
    with op() as m:
        for t in cases["tasks"]:
            res = m.recall(t["question"], budget=5)
            rows = []
            for ref in res["admitted"]:
                adm = res["admissions"].get(ref, {})
                rows.append({"key": refs.get(ref, ref), "returned": ref in res["returned"],
                             "routes": [(h.get("route_id"), h.get("raw_score")) for h in adm.get("route_provenance") or []],
                             "rank": adm.get("ranking_evidence")})
            out[t["id"]] = {"q": t["question"], "candidates": len(res["candidates"]), "admitted": len(res["admitted"]),
                            "candidate_policy": res.get("candidate_policy"), "return_policy": res.get("return_policy"), "rows": rows}
json.dump(out, open(sys.argv[2], "w"), indent=1, default=str)
for tid, v in out.items():
    print(tid, v["q"], "| candidates", v["candidates"], "admitted", v["admitted"])
    for r in v["rows"]:
        print("   ", "*" if r["returned"] else " ", r["key"], r["routes"], (r["rank"] or {}).get("route_scores"), (r["rank"] or {}).get("route_corroboration_count"))
print(json.dumps(out["A5"]["candidate_policy"], indent=1)[:1500]); print(json.dumps(out["A5"]["return_policy"], indent=1)[:800])
