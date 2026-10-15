"""Trace PrecisionMemBench cases through the public AgentMemory.recall, ingesting exactly as the AMB bridge does.

Usage: python scripts/trace_pmb_recall.py reference <dir with beliefs.seed.json and retrieval.cases.json> <out.json> [case_id ...]
Gold is read ONLY for reporting next to the trace; it is never passed to the runtime.
"""
import hashlib, json, shutil, sys, tempfile
from pathlib import Path

ref, fixtures, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
only = set(sys.argv[4:])
sys.path.insert(0, str(ref))
from agentmem_ref import AgentMemory  # noqa: E402

beliefs = json.loads((fixtures / "beliefs.seed.json").read_text())
cases = json.loads((fixtures / "retrieval.cases.json").read_text())
T, A, P = "tenant:amb-competitive", "agent:amb-competitive", "Independent Agent Memory Benchmark competitive evaluation"

def scope(u): return "amb:scope:" + hashlib.sha256((u or "global").encode()).hexdigest()[:32]
def lid(d, u): return "memory:amb:" + hashlib.sha256(f"{u or 'global'}\x00{d}".encode()).hexdigest()
def text(b): return " ".join(p for p in [b.get("canonical_name"), *(b.get("aliases") or []), b.get("content"), b.get("why_it_matters")] if p)

root = Path(tempfile.mkdtemp()) / "rt"
by_fact = {}
users = {}
for b in beliefs:
    users.setdefault(b["user_id"], []).append(b)
for u, bs in users.items():
    with AgentMemory.open(root, tenant=T, actor_id=A, scope=scope(u), purpose=P) as m:
        for b in bs:
            o = m.remember(lid(b["_id"], u), text(b), observed_at=b.get("created_at"))
            by_fact[o["fact_uuid"]] = b["_id"]
records = []
for c in cases:
    if only and c["caseId"] not in only:
        continue
    q = c["query"]
    if not q.strip():
        continue
    k = {"maxBeliefs": 20, **(c.get("budget") or {})}["maxBeliefs"]
    if k < 1:
        continue
    u = c.get("userId") or "test-user"
    with AgentMemory.open(root, tenant=T, actor_id=A, scope=scope(u), purpose=P) as m:
        o = m.recall(q, budget=k)
    adm = o.get("admissions") or {}
    rows = []
    for f in o.get("admitted") or []:
        d = adm.get(f, {})
        ev = d.get("ranking_evidence") or {}
        rows.append({"belief": by_fact.get(f), "rank": d.get("rank_position"),
                     "bm25": ev.get("lexical_relevance_score"), "routes": ev.get("routes"),
                     "lex_raw": (ev.get("route_scores") or {}).get("lexical"),
                     "tier": ev.get("temporal_applicability"), "selection": d.get("return_selection")})
    records.append({"case": c["caseId"], "category": c["category"], "query": q, "scope": c["scope"], "k": k,
                    "intent": (o.get("query_temporal_intent") or {}),
                    "candidates": len(o.get("candidates") or []), "refused": len(o.get("candidates") or []) - len(o.get("admitted") or []),
                    "returned": [by_fact.get(f) for f in o.get("returned") or []],
                    "return_policy": o.get("return_policy"),
                    "ranked": rows,
                    "expect": c["expect"]})
out.write_text(json.dumps(records, indent=1))
shutil.rmtree(root.parent, ignore_errors=True)
print(len(records), "traced")
