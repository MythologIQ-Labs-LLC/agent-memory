import sys, tempfile, json
from agentmem_ref import AgentMemory
from agentmem_ref.recall_control import ControlledRecallPlanner, DeterministicRecallController
from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
from agentmem_ref.runtime import typed_proposition as t
def op(root): return AgentMemory.open(root, tenant="tenant:adv644", actor_id="agent:adv644", scope="project:adv644", purpose="adv644")
d = tempfile.mkdtemp(); m = op(d)
P = lambda v: {"subject":"Hydra service","attribute":"owner","value":v,"assertion":"state","cardinality":"single"}
m.remember("memory:o1","Hydra service owner is Linda",proposition=P("Linda"))
m.remember("memory:o2","Hydra service owner is Simon",proposition=P("Simon"))
rt = m.runtime
pl = ControlledRecallPlanner(rt.adapter, controller=DeterministicRecallController())
ctx = m._handle_recall_context()
res = rt.durable_runtime.run_governed_read(lambda: pl.recall("Hydra service owner", ctx))
sub = rt.adapter.checkpoint_substrate()
d0 = sub.state_digest(); ev0 = len(rt.adapter.events)
need = (CoverageNeed(t.typed_slot("Hydra service","owner")),)
r1 = pl.observe_persisted_typed_coverage(res, ctx, needs=need).to_dict(); w1 = [w.to_dict() for w in pl.observe_governed_transition_witnesses(res, ctx)]
print("digest unchanged by observer:", sub.state_digest()==d0, "events unchanged:", len(rt.adapter.events)==ev0)
m.close()
m2 = op(d); print("reopen OK")
pl2 = ControlledRecallPlanner(m2.runtime.adapter, controller=DeterministicRecallController())
ctx2 = m2._handle_recall_context()
res2 = m2.runtime.durable_runtime.run_governed_read(lambda: pl2.recall("Hydra service owner", ctx2))
r2 = pl2.observe_persisted_typed_coverage(res2, ctx2, needs=need).to_dict()
print("report identical after restart:", r1==r2, r2["diagnosis"], r2["value_coherence"])
m2.close()
