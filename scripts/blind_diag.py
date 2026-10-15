"""Diagnostic only: per query, must_include refs not admitted (discovery), admitted but withheld
(selection), and extra returned refs. Usage: blind_diag.py <reference_dir> <cohort>"""
import json, sys, tempfile, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm
T, A = "tenant:memory-quality", "agent:memory-quality"
def ev(scope):
    s = pm.SkillArtifact(skill_id="skill:d", version=1, purpose="p", scope=scope, isolation_domain_refs=(T, scope),
        required_isolation_domain_refs=(T, scope), procedure_markdown="# v\nok", provenance_refs=("evidence:d",))
    return pm.evidence_for(s)
agg = collections.defaultdict(collections.Counter)
for sc in json.load(open(sys.argv[2]))["scenarios"]:
    with tempfile.TemporaryDirectory() as d:
        by = {}
        for op in sc["operations"]:
            with AgentMemory.open(Path(d), tenant=T, actor_id=A, scope=op["scope"], purpose="p") as m:
                if op["op"] == "remember": o = m.remember(op["ref"], op["text"])
                elif op["op"] == "correct": o = m.correct(op["ref"], op["text"], evidence=ev(op["scope"]))
                else: o = m.forget(op["ref"], evidence=ev(op["scope"]))
            if o.get("fact_uuid"): by[o["fact_uuid"]] = op["ref"]
        for q in sc["queries"]:
            with AgentMemory.open(Path(d), tenant=T, actor_id=A, scope=q["scope"], purpose="p") as m:
                r = m.recall(q["query"], budget=10)
            adm = {by.get(u) for u in r["admitted"]}; ret = {by.get(u) for u in r["returned"]}
            must = set(q["expect"].get("must_include") or []); ok = must | set(q["expect"].get("may_include") or [])
            c = agg[sc["category"]]
            c["must"] += len(must); c["not_admitted"] += len(must - adm); c["withheld"] += len((must & adm) - ret)
            c["extra_returned"] += len(ret - ok); c["queries"] += 1
for k, v in sorted(agg.items()): print(k, dict(v))
