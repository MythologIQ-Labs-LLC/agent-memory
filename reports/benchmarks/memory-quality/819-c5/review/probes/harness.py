"""Probe harness: python3 harness.py <worktree> <scenarios.json> <off|required> -> JSON on stdout.

Each scenario: {"name", "facts": {ref: text}, "queries": [str], optional "forget": [ref],
"correct": {ref: new_text}, "other_scope": {ref: text}}.
"""
import json, sys, tempfile, time, os
from pathlib import Path

worktree, spec_path, mode = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, str(Path(worktree) / "reference"))
os.environ.setdefault("AGENT_MEMORY_REPRESENTATION_DIR",
                      "/tmp/claude-0/-home-user-agent-memory/d36426e4-2c3f-5d02-b5a0-991ea8f96c90/scratchpad/representation")
from agentmem_ref import AgentMemory  # noqa
from agentmem_ref.memory import procedural_memory as pm  # noqa

TENANT, SCOPE = "tenant:probe", "user:probe"

def evidence(scope=SCOPE):
    skill = pm.SkillArtifact(skill_id="skill:probe", version=1, purpose="apply a lifecycle change", scope=scope,
        isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:probe",))
    return pm.evidence_for(skill)

def open_(root, scope=SCOPE):
    kw = {} if mode == "off" else {"semantic_retrieval": mode}
    return AgentMemory.open(root, tenant=TENANT, actor_id="agent:probe", scope=scope, purpose="probe", **kw)

out = []
for sc in json.loads(Path(spec_path).read_text()):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        refs = {}
        if sc.get("other_scope"):
            o = open_(root, "user:other")
            for ref, text in sc["other_scope"].items():
                r = o.remember(ref, text); refs[r["fact_uuid"]] = "OTHER:" + ref
            o.close()
        m = open_(root)
        for ref, text in sc["facts"].items():
            r = m.remember(ref, text); assert r["committed"], r
            refs[r["fact_uuid"]] = ref
        for ref in sc.get("forget", []):
            assert m.forget(ref, evidence=evidence())["committed"]
        for ref, text in sc.get("correct", {}).items():
            r = m.correct(ref, text, evidence=evidence()); assert r["committed"], r
            refs[r.get("fact_uuid", "")] = ref + "(corrected)"
        # resolve uuids for any facts created by correct
        for q in sc["queries"]:
            t0 = time.perf_counter()
            res = m.recall(q, budget=sc.get("budget", 10), return_selection=sc.get("return_selection", "relevance_sufficient"))
            dt = (time.perf_counter() - t0) * 1000
            name = lambda u: refs.get(u, u)
            recs = {name(u): {k: d.get("return_selection", {}).get(k) for k in ("basis", "semantic_similarity")}
                    for u, d in res["admissions"].items() if "return_selection" in d}
            routes = {name(u): sorted({h["route_id"] for h in d.get("route_provenance", [])}) for u, d in res["admissions"].items()}
            rp = res.get("return_policy", {})
            out.append({"scenario": sc["name"], "query": q, "returned": [name(u) for u in res["returned"]],
                        "admitted": [name(u) for u in res["admitted"]], "records": recs, "routes": routes,
                        "abstained": rp.get("abstained"), "semantic_channel": rp.get("semantic_channel"),
                        "ms": round(dt, 1), "raw": json.dumps(res) if sc.get("dump") else None})
        m.close()
print(json.dumps(out, indent=1))
