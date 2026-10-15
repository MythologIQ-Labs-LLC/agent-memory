"""Reviewer harness: run self-authored scenarios through the public facade of one tree.

usage: python harness.py <tree> <scenarios.json> <semantic: off|required> <out.json> [--selection ranked_prefix]
The tree's reference/ is put first on sys.path. Records, per query, returned refs, the routes
that surfaced each returned ref, the semantic proposals (admitted or refused) and timing.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402

TENANT = "tenant:review"
ACTOR = "agent:review"


def evidence(scope):
    skill = pm.SkillArtifact(skill_id="skill:review", version=1, purpose="apply a lifecycle change", scope=scope,
                             isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:review",))
    return pm.evidence_for(skill)


def run(scenarios, semantic, selection=None, tenant=TENANT):
    out = []
    for sc in scenarios:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            by_uuid = {}
            kw = {} if semantic == "off" else {"semantic_retrieval": semantic}
            for op in sc["operations"]:
                t = op.get("tenant", tenant)
                with AgentMemory.open(root, tenant=t, actor_id=ACTOR, scope=op["scope"], purpose="review", **kw) as m:
                    if op["op"] == "remember":
                        o = m.remember(op["ref"], op["text"], **({"observed_at": op["observed_at"]} if op.get("observed_at") else {}))
                    elif op["op"] == "correct":
                        ckw = {k: op[k] for k in ("replacement_kind", "valid_from") if op.get(k)}
                        o = m.correct(op["ref"], op["text"], evidence=evidence(op["scope"]), **ckw)
                    elif op["op"] == "forget":
                        o = m.forget(op["ref"], evidence=evidence(op["scope"]))
                if o.get("committed") and o.get("fact_uuid"):
                    by_uuid[str(o["fact_uuid"])] = (op["scope"], op.get("as", op["ref"]))
                elif not o.get("committed"):
                    print("OP FAILED", sc["id"], op["ref"], o.get("refusal"), file=sys.stderr)
            for q in sc["queries"]:
                rkw = {"budget": 10}
                if selection:
                    rkw["return_selection"] = selection
                if q.get("temporal_intent"):
                    rkw["temporal_intent"] = q["temporal_intent"]
                with AgentMemory.open(root, tenant=q.get("tenant", tenant), actor_id=ACTOR, scope=q["scope"], purpose="review", **kw) as m:
                    t0 = time.perf_counter()
                    r = m.recall(q["query"], **rkw)
                    ms = (time.perf_counter() - t0) * 1000

                def name(u):
                    s, ref = by_uuid.get(str(u), ("?", "unmapped:" + str(u)[:8]))
                    return ref if s == q["scope"] else f"{s}#{ref}"

                routes = {}
                sem = []
                for u, d in (r.get("admissions") or {}).items():
                    rs = sorted({h.get("route_id") for h in d.get("route_provenance") or []})
                    routes[name(u)] = rs
                    for h in d.get("route_provenance") or []:
                        if "semantic" in str(h.get("route_id")) or "vector" in str(h.get("route_id")):
                            sem.append((name(u), round(float(h.get("raw_score", 0)), 3), d.get("refusal")))
                returned = [name(u) for u in r.get("returned") or []]
                e = q["expect"]
                must = e.get("must_include") or []
                allowed = set(must) | set(e.get("may_include") or [])
                excl = {x["ref"] if isinstance(x, dict) else x for x in e.get("must_exclude") or []}
                out.append({
                    "scenario": sc["id"], "id": q["id"], "kind": q.get("kind"), "query": q["query"],
                    "returned": returned,
                    "returned_routes": {x: routes.get(x) for x in returned},
                    "semantic_proposals": sorted(sem, key=lambda x: -x[1]),
                    "admitted": len(r.get("admitted") or []),
                    "pass": all(x in returned for x in must) and not (set(returned) & excl) and set(returned) <= allowed,
                    "needed": len(must), "needed_returned": len(set(must) & set(returned)),
                    "extra": len([x for x in returned if x not in allowed]),
                    "excluded_returned": sorted(set(returned) & excl),
                    "no_answer": not must, "ms": round(ms, 2),
                })
    return out


if __name__ == "__main__":
    scen = json.loads(Path(sys.argv[2]).read_text())
    scen = scen["scenarios"] if isinstance(scen, dict) else scen
    sel = sys.argv[sys.argv.index("--selection") + 1] if "--selection" in sys.argv else None
    rows = run(scen, sys.argv[3], sel)
    Path(sys.argv[4]).write_text(json.dumps(rows, indent=1))
    n = len(rows)
    print(json.dumps({"tree": tree.name, "semantic": sys.argv[3], "selection": sel, "queries": n,
                      "strict": sum(r["pass"] for r in rows),
                      "needed_recall": round(sum(r["needed_returned"] for r in rows) / max(1, sum(r["needed"] for r in rows)), 3),
                      "extras": sum(r["extra"] for r in rows),
                      "no_answer_returning": sum(1 for r in rows if r["no_answer"] and r["returned"]),
                      "safety": sum(len(r["excluded_returned"]) for r in rows)}))
