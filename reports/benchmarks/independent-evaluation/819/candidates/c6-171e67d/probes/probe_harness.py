"""Run the independent probe set through the public facade of whichever tree this venv imports.

usage: probe_harness.py probes.json SEMANTIC(off|required) REPRESENTATION_DIR out.json
"""
import json, sys, tempfile, time
from pathlib import Path
import agentmem_ref
from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm

TENANT, ACTOR = "tenant:probe", "agent:probe"


def ev(tenant, scope):
    skill = pm.SkillArtifact(skill_id="skill:probe", version=1, purpose="apply a lifecycle change", scope=scope,
                             isolation_domain_refs=(tenant, scope), required_isolation_domain_refs=(tenant, scope),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:probe",))
    return pm.evidence_for(skill)


def main():
    data = json.load(open(sys.argv[1]))
    sem, rep, out_path = sys.argv[2], sys.argv[3], sys.argv[4]
    kw = {} if sem == "off" else {"semantic_retrieval": sem, "representation_dir": rep}
    rows, op_failures = [], []
    for s in data["scenarios"]:
        with tempfile.TemporaryDirectory() as tmp:
            root, names, texts, uuid_of = Path(tmp), {}, {}, {}
            for op in s["operations"]:
                t, sc = op.get("tenant", TENANT), op["scope"]
                label = op.get("as") or (op["ref"] if sc == "user:probe" or op.get("tenant") else f"{sc}#{op['ref']}")
                with AgentMemory.open(root, tenant=t, actor_id=ACTOR, scope=sc, purpose="probe", **kw) as m:
                    if op["op"] == "remember":
                        o = m.remember(op["ref"], op["text"], **({"observed_at": op["observed_at"]} if op.get("observed_at") else {}))
                    elif op["op"] == "correct":
                        ck = {k: op[k] for k in ("replacement_kind", "valid_from") if op.get(k)}
                        o = m.correct(op["ref"], op["text"], evidence=ev(t, sc), **ck)
                    elif op["op"] == "forget":
                        o = m.forget(op["ref"], evidence=ev(t, sc))
                    elif op["op"] == "dispute":
                        o = m.dispute(op["ref"], evidence=ev(t, sc))
                if not o.get("committed"):
                    op_failures.append({"scenario": s["id"], "op": op["op"], "ref": op["ref"], "refusal": str(o.get("refusal"))[:300]})
                if op["op"] in ("remember", "correct") and o.get("fact_uuid"):
                    u = str(o["fact_uuid"])
                    names[(sc, u)] = label
                    uuid_of[(sc, label)] = u
                    texts[(sc, label)] = op["text"]
            for qq in s["queries"]:
                sc = qq["scope"]

                def name(u):
                    for (ss, uu), lab in names.items():
                        if uu == str(u):
                            return lab if ss == sc else (lab if "#" in lab else f"{ss}#{lab}")
                    return "unmapped:" + str(u)[:8]
                rk = {"budget": data.get("budget", 5)}
                if qq.get("temporal_intent"):
                    rk["temporal_intent"] = qq["temporal_intent"]
                with AgentMemory.open(root, tenant=qq.get("tenant", TENANT), actor_id=ACTOR, scope=sc, purpose="probe", **kw) as m:
                    t0 = time.perf_counter()
                    r = m.recall(qq["query"], **rk)
                    ms = (time.perf_counter() - t0) * 1000
                returned = [name(u) for u in r.get("returned") or []]
                routes, semp = {}, []
                for u, d in (r.get("admissions") or {}).items():
                    prov = d.get("route_provenance") or []
                    routes[name(u)] = sorted({str(h.get("route_id")) for h in prov})
                    for h in prov:
                        if "semantic" in str(h.get("route_id")) or "vector" in str(h.get("route_id")):
                            semp.append([name(u), round(float(h.get("raw_score") or 0), 4), d.get("refusal")])
                must, may, excl = set(qq["must"]), set(qq["may"]), set(qq["exclude"])
                blob = json.dumps(r, default=str)
                leaked_text = sorted(lab for (ss, lab), t in texts.items() if lab in excl and t in blob)
                rp = r.get("return_policy") or {}
                rows.append({
                    "scenario": s["id"], "category": s["category"], "id": qq["id"], "query": qq["query"],
                    "returned": returned, "routes": {x: routes.get(x) for x in returned},
                    "semantic_proposals": sorted(semp, key=lambda x: -x[1]),
                    "must": sorted(must), "needed": len(must), "needed_returned": len(must & set(returned)),
                    "extra": len([x for x in returned if x not in must | may]),
                    "excluded_returned": sorted(excl & set(returned)), "excluded_text_in_result": leaked_text,
                    "strict": must <= set(returned) and not (excl & set(returned)) and set(returned) <= (must | may),
                    "no_answer": not must, "abstained": not returned, "ms": round(ms, 2),
                    "shape": (rp.get("information_requirement") or {}).get("shape"),
                    "control": qq.get("control", False), "false_positive_probe": qq.get("false_positive", False),
                })
    n = len(rows)
    summary = {
        "runtime": agentmem_ref.__file__, "semantic": sem, "queries": n,
        "strict": sum(r["strict"] for r in rows),
        "needed_recall": round(sum(r["needed_returned"] for r in rows) / max(1, sum(r["needed"] for r in rows)), 4),
        "extras": sum(r["extra"] for r in rows),
        "no_answer_returning": sum(1 for r in rows if r["no_answer"] and r["returned"] and not r["category"] in ("historical", "cross_scope", "lifecycle")),
        "safety_ref_leaks": sum(len(r["excluded_returned"]) for r in rows),
        "safety_text_leaks": sum(len(r["excluded_text_in_result"]) for r in rows),
        "op_failures": op_failures,
        "p50_ms": sorted(r["ms"] for r in rows)[n // 2],
    }
    json.dump({"summary": summary, "rows": rows}, open(out_path, "w"), indent=1)
    print(json.dumps(summary))


main()
