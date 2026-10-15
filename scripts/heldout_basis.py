"""Diagnostic (post-freeze): selection basis of every extra returned ref, per category. Args: reference_dir cohort [category]"""
import json, sys, tempfile, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm
T, A = "tenant:memory-quality", "agent:memory-quality"
def ev(scope):
    s = pm.SkillArtifact(skill_id="skill:memory-quality-lifecycle", version=1, purpose="p", scope=scope, isolation_domain_refs=(T, scope),
        required_isolation_domain_refs=(T, scope), procedure_markdown="# v\nok", provenance_refs=("evidence:d",))
    return pm.evidence_for(s)
want = sys.argv[3] if len(sys.argv) > 3 else None
bases = collections.Counter(); shapes = collections.Counter(); examples = []
for sc in json.load(open(sys.argv[2]))["scenarios"]:
    if want and sc.get("category") != want: continue
    with tempfile.TemporaryDirectory() as d:
        by = {}
        for op in sc["operations"]:
            with AgentMemory.open(Path(d), tenant=T, actor_id=A, scope=op["scope"], purpose="memory quality scenario") as m:
                kw = {"observed_at": op["observed_at"]} if op.get("observed_at") else {}
                if op["op"] == "remember": o = m.remember(op["ref"], op["text"], **kw)
                elif op["op"] == "correct": o = m.correct(op["ref"], op["text"], evidence=ev(op["scope"]))
                else: o = m.forget(op["ref"], evidence=ev(op["scope"]))
            if o.get("fact_uuid"): by[o["fact_uuid"]] = op["ref"]
        for q in sc["queries"]:
            with AgentMemory.open(Path(d), tenant=T, actor_id=A, scope=q["scope"], purpose="memory quality scenario") as m:
                r = m.recall(q["query"], budget=10)
            ok = set(q["expect"].get("must_include") or []) | set(q["expect"].get("may_include") or [])
            info = r["return_policy"].get("information_requirement", {})
            for u in r["returned"]:
                if by.get(u) not in ok:
                    b = r["admissions"][u]["return_selection"]["basis"]; bases[b] += 1; shapes[info.get("shape")] += 1
                    if len(examples) < 6: examples.append((q["query"], b, info.get("shape"), info.get("cues")))
print("extra-return bases:", dict(bases)); print("query shapes of extras:", dict(shapes))
for e in examples: print("  ", e)
