import sys, time, statistics; sys.path.insert(0, ".")
from agentmem_ref.recall_control import NativeTypedGraphCandidateRetriever, GraphTraversalSpec
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.test_typed_graph_retrieval import TENANT, _fact, _relation
def build(n, opaque_every):
    g = InMemoryTemporalGraph(); g.write_fact(_fact("seed")); hidden=set()
    for i in range(n):
        ref=f"n{i:04d}"; g.write_fact(_fact(ref))
        g.write_relation(_relation(f"r{i:04d}", "seed", ref, weight=1.0 - i/(2*n)))
        if opaque_every and i % opaque_every == 0: hidden.add(ref)
    return g, hidden
for n, every in ((400, 0), (400, 4), (400, 2)):
    g, hidden = build(n, every)
    r = NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_depth=1, max_fanout=8))
    op = (lambda ref: ref in hidden) if every else None
    times=[]
    for _ in range(7):
        t=time.perf_counter()
        for _ in range(100): hits = r.search(g, ("seed",), group_id=TENANT, candidate_limit=8, eligible=lambda f: True, opaque=op)
        times.append((time.perf_counter()-t)/100*1000)
    vis = sum(1 for h in hits if h.candidate_ref not in hidden)
    print(f"hub={n} opaque_every={every or '-'}: p50 {statistics.median(times):.3f} ms/search  returned={len(hits)} visible={vis} opaque={len(hits)-vis}")
