"""Does any supported public path execute the typed-graph route? Unmodified runtime."""
import sys, inspect, unittest; sys.path.insert(0, ".")
from dataclasses import replace
from agentmem_ref.api.surface import AgentMemory
from agentmem_ref.runtime.runtime_composition import ConfiguredCompositionRuntime, DeterministicMultiRouteRecallPlanner
from tests.test_776_adversarial_review import KILN, _Store
from tests.test_runtime_composition import TENANT, _context
from tests.test_typed_graph_retrieval import _relation
class _C(unittest.TestCase):
    def runTest(self): pass
c=_C(); c.setUp()
print("AgentMemory.open params:", [p for p in inspect.signature(AgentMemory.open).parameters])
print("AgentMemory.recall params:", [p for p in inspect.signature(AgentMemory.recall).parameters])
print("ConfiguredCompositionRuntime.create params:", [p for p in inspect.signature(ConfiguredCompositionRuntime.create).parameters])
print("ConfiguredCompositionRuntime.__init__ params:", [p for p in inspect.signature(ConfiguredCompositionRuntime.__init__).parameters])
src = inspect.getsource(DeterministicMultiRouteRecallPlanner)
print("default planner mentions typed_graph/graph_retriever:", ("typed_graph" in src, "graph_retriever" in src))
h=_Store(c)
old,_=h.chain("kiln", KILN); seed=h.chain("studio",[("The pottery studio fires glazes on Fridays.",None)])[0]
vis=h.chain("shelf",[("The glaze shelf holds test tiles.",None)])[0]
sub=h.adapter.checkpoint_substrate()
sub.write_relation(replace(_relation("r-visible", seed, vis, weight=0.8), group_id=TENANT))
sub.write_relation(replace(_relation("r-deleted", seed, old, weight=1.0), group_id=TENANT))
h.prune("kiln")
print("default planner type:", type(h.runtime.recall_planner).__name__)
r=h.runtime.multi_route_recall("pottery studio glazes", _context(), logical_memory_refs=("memory:776r:studio",))
print("default multi_route routes_executed:", r.routes_executed)
print("route ids in provenance:", sorted({hit.route_id for cand in r.candidates for hit in r.provenance_for(cand)}))
print("visible shelf admitted via default planner (lexical/exact only):", vis in r.admitted, "| deleted old in candidates:", old in r.candidates)
