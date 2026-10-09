import sys, tempfile
mode = sys.argv[1]
from agentmem_ref import AgentMemory
def op(root): return AgentMemory.open(root, tenant="tenant:adv644", actor_id="agent:adv644", scope="project:adv644", purpose="adv644")
d = tempfile.mkdtemp()
m = op(d)
P = lambda v: {"subject":"Hydra service","attribute":"owner","value":v,"assertion":"state","cardinality":"single"}
m.remember("memory:o1","Hydra service owner is Linda",proposition=P("Linda"))
m.remember("memory:o2","Hydra service owner is Simon",proposition=P("Simon"))
if mode in ("planner","observer"):
    from agentmem_ref.recall_control import ControlledRecallPlanner, DeterministicRecallController
    pl = ControlledRecallPlanner(m.runtime.adapter, controller=DeterministicRecallController())
    res = pl.recall("Hydra service owner", m._handle_recall_context())
    if mode == "observer":
        from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
        from agentmem_ref.runtime import typed_proposition as t
        pl.observe_persisted_typed_coverage(res, m._handle_recall_context(), needs=(CoverageNeed(t.typed_slot("Hydra service","owner")),))
if mode == "facade_recall":
    m.recall("Hydra service owner")
m.close()
try:
    m2 = op(d); print(mode, "reopen OK"); m2.close()
except Exception as e:
    print(mode, "reopen FAILED:", type(e).__name__, e)
