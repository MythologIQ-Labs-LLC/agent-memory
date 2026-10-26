"""Direct lower-level reproduction at the retriever, no planner/adapter involved."""
import sys; sys.path.insert(0, ".")
from agentmem_ref.recall_control import NativeTypedGraphCandidateRetriever, GraphTraversalSpec
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.test_typed_graph_retrieval import TENANT, _fact, _relation

def build(with_hidden):
    g = InMemoryTemporalGraph()
    for r in ("seed", "hidden", "visible", "tail"):
        g.write_fact(_fact(r))
    g.write_relation(_relation("r-visible", "seed", "visible", weight=0.8))
    if with_hidden:
        g.write_relation(_relation("r-hidden", "seed", "hidden", weight=1.0))
    return g

opaque = lambda ref: ref == "hidden"
for label, fan, lim in (("fanout-starvation", 1, 8), ("limit-truncation", 8, 1), ("both-roomy", 8, 8)):
    for hidden in (False, True):
        g = build(hidden)
        r = NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_depth=1, max_fanout=fan))
        canon = [h.candidate_ref for h in r.search(g, ("seed",), group_id=TENANT, candidate_limit=lim, opaque=opaque)]
        rep = [h.candidate_ref for h in r.search(g, ("seed",), group_id=TENANT, candidate_limit=lim, exclude=opaque)]
        print(f"{label:18} fanout={fan} limit={lim} hidden_present={hidden!s:5} canonical(opaque)={canon}  reported(exclude)={rep}")
