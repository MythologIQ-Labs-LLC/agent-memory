"""Same-scenario noninterference probe. argv: <out.json> <observe:0|1>"""
import sys, json, re, tempfile, hashlib, dataclasses
from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.recall_control import ControlledRecallPlanner, DeterministicRecallController
out_path, observe = sys.argv[1], sys.argv[2] == "1"
TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?")
EL = re.compile(r'"elapsed_ms": [0-9.]+')
def norm(x): return json.loads(EL.sub('"elapsed_ms": 0', TS.sub("<ts>", json.dumps(x, sort_keys=True, default=str))))
def ev():
    s = pm.SkillArtifact(skill_id="skill:ni", version=1, purpose="ni", scope="project:ni",
        isolation_domain_refs=("tenant:ni","project:ni"), required_isolation_domain_refs=("tenant:ni","project:ni"),
        procedure_markdown="# v\nok", provenance_refs=("evidence:ni",))
    return pm.evidence_for(s)
P = lambda s,a,v,**k: {"subject":s,"attribute":a,"value":v,"assertion":k.pop("assertion","state"),"cardinality":k.pop("cardinality","single"),"flags":k}
log = []
def rec(name, val): log.append([name, norm(val)])
d = tempfile.mkdtemp()
m = AgentMemory.open(d, tenant="tenant:ni", actor_id="agent:ni", scope="project:ni", purpose="ni", recall_control="shadow")
HAS_OBSERVER = hasattr(ControlledRecallPlanner, "observe_persisted_typed_coverage")
def maybe_observe(q, slots):
    pl = ControlledRecallPlanner(m.runtime.adapter, controller=DeterministicRecallController())
    ctx = m._handle_recall_context()
    res = m.runtime.durable_runtime.run_governed_read(lambda: pl.recall(q, ctx))
    before = (list(res.recall.admitted), list(res.recall.ranked_admitted), dict(res.recall.refusals))
    rec("planner_read:"+q, before)
    if not (observe and HAS_OBSERVER): return
    from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
    from agentmem_ref.runtime import typed_proposition as t
    pl.observe_persisted_typed_coverage(res, ctx, needs=tuple(CoverageNeed(t.typed_slot(*s)) for s in slots))
    res.observe_evidence_sufficiency()
    pl.observe_governed_transition_witnesses(res, ctx)
    assert before == (list(res.recall.admitted), list(res.recall.ranked_admitted), dict(res.recall.refusals))
    # discard: observer-mode run re-does the same read in both modes below
rec("r1", m.remember("memory:a","Hydra service owner is Linda",proposition=P("Hydra service","owner","Linda")))
maybe_observe("Hydra service owner", [("Hydra service","owner")])
rec("r2", m.remember("memory:b","Hydra service owner is Simon",proposition=P("Hydra service","owner","Simon")))
rec("r3", m.remember("memory:c","Nimbus app tag is blue",proposition=P("Nimbus app","tag","blue",cardinality="multi")))
rec("r4", m.remember("memory:d","Beacon region changed to west",proposition=P("Beacon","region","west",assertion="change")))
rec("r5", m.remember("memory:e","Deploy window is Thursday"))
maybe_observe("Hydra service owner Nimbus tag", [("Hydra service","owner"),("Nimbus app","tag")])
for q in ("Hydra service owner","Nimbus app tag","Beacon region","Deploy window"):
    rec("recall:"+q, m.recall(q))
rec("correct", m.correct("memory:e","Deploy window is Friday",evidence=ev(),risk_class="low",replacement_kind="state_change"))
maybe_observe("Deploy window", [("Deploy","window")])
rec("dispute", m.dispute("memory:a", evidence=ev(), risk_class="low", evidence_refs=("evidence:d",)))
rec("forget", m.forget("memory:c"))
for q in ("Hydra service owner","Nimbus app tag","Deploy window","Kevin"):
    rec("recall2:"+q, m.recall(q))
    rec("recall2b:"+q, m.recall(q, budget=1))
rec("hist", [m.history(t) for t in ("memory:a","memory:b","memory:c","memory:e")])
rec("proposals", m.semantic_proposals())
rec("semantics", [m.write_semantics(f) for f in ("ref-0004","ref-0011")])
rec("posture", m.posture())
pl = ControlledRecallPlanner(m.runtime.adapter, controller=DeterministicRecallController())
ctx = m._handle_recall_context()
res = m.runtime.durable_runtime.run_governed_read(lambda: pl.recall("Hydra service owner", ctx))
rec("planner", {"cand": res.candidates, "adm": res.admitted, "rank": res.ranked_admitted, "ref": res.recall.refusals,
                "counts": res.route_candidate_counts, "stop": res.stop_reason, "plan": dataclasses.asdict(res.plan),
                "rank_ev": res.recall.ranking_evidence})
sub = m.runtime.adapter.checkpoint_substrate()
rec("facts", [dataclasses.asdict(f) for f in sub.all_facts()])
rec("events", m.runtime.adapter.events)
m.close()
m = AgentMemory.open(d, tenant="tenant:ni", actor_id="agent:ni", scope="project:ni", purpose="ni")
rec("after_restart", m.recall("Hydra service owner"))
m.close()
json.dump(log, open(out_path,"w"), indent=1, sort_keys=True)
print("sections", len(log), "events", len(log[-2][1]))
