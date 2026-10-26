"""Planner-level differential with controls. Run from reference/ with sys.path='.'"""
import sys, unittest; sys.path.insert(0, ".")
from dataclasses import replace
from agentmem_ref.recall_control import (ControlledRecallPlanner, GraphTraversalSpec,
    NativeTypedGraphCandidateRetriever, TYPED_GRAPH_ROUTE)
from tests.test_836_graph_exclusion_boundaries import _graph_plan
from tests.test_776_adversarial_review import KILN, _Store
from tests.test_runtime_composition import TENANT, _context, _proposal
from tests.test_typed_graph_retrieval import _FixedController, _relation

class _Case(unittest.TestCase):
    def runTest(self): pass
case = _Case(); case.setUp()

def planner(h, fanout, limit):
    return ControlledRecallPlanner(h.adapter, controller=_FixedController(_graph_plan(limit, 1)),
        graph_retriever=NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_depth=1, max_fanout=fanout)))

def show(label, r, names):
    inv = {v: k for k, v in names.items()}
    nm = lambda x: inv.get(x, x)
    print(f"  [{label}] candidates={[nm(c) for c in r.candidates]} admitted={[nm(a) for a in r.admitted]}")
    print(f"     refusals={{{', '.join(f'{nm(k)}:{v}' for k,v in r.recall.refusals.items())}}} route_counts={r.route_candidate_counts}")
    print(f"     graph_candidate_hits={[nm(k) for k in r.graph_candidate_hits]} paths={[tuple(nm(p) for p in h.path_refs) for h in r.graph_candidate_hits.values()]}")

def scenario(title, build, fanout, limit):
    print(f"\n== {title}  fanout={fanout} limit={limit}")
    for arm in ("control", "probe"):
        h = _Store(case); names = build(h, arm == "probe")
        r = planner(h, fanout, limit).recall("", _context(), logical_memory_refs=("memory:776r:studio",))
        show(arm, r, names)

def base(h):
    seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
    vis = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
    sub = h.adapter.checkpoint_substrate()
    sub.write_relation(replace(_relation("r-visible", seed, vis, weight=0.80), group_id=TENANT))
    return seed, vis, sub

def deleted_neighbor(h, probe):
    old, _ = h.chain("kiln", KILN); seed, vis, sub = base(h)
    if probe: sub.write_relation(replace(_relation("r-deleted", seed, old, weight=1.0), group_id=TENANT))
    h.prune("kiln")
    return {"seed": seed, "visible": vis, "deleted_old": old}

def accessible_sibling(h, probe):
    seed, vis, sub = base(h)
    sib = h.chain("wheel", [("The wheel room has three kick wheels.", None)])[0]
    if probe: sub.write_relation(replace(_relation("r-sib", seed, sib, weight=1.0), group_id=TENANT))
    return {"seed": seed, "visible": vis, "sibling": sib}

def foreign_neighbor(h, probe):
    seed, vis, sub = base(h)
    f = h.runtime.retain(replace(_proposal("proposal:776r:foreign", operation="promotion", project_ref="project-b"),
        target_reference="memory:776r:foreign", isolation_domain_refs=(TENANT, "project-b"),
        required_isolation_domain_refs=("project-b",)), "Private studio note.")
    assert f.committed
    if probe: sub.write_relation(replace(_relation("r-foreign", seed, f.fact_uuid, weight=1.0), group_id=TENANT))
    return {"seed": seed, "visible": vis, "foreign": f.fact_uuid}

def superseded_neighbor(h, probe):
    old, new = h.chain("kiln", KILN); seed, vis, sub = base(h)   # kiln NOT pruned: old is a stale live-lineage version
    if probe: sub.write_relation(replace(_relation("r-stale", seed, old, weight=1.0), group_id=TENANT))
    return {"seed": seed, "visible": vis, "stale_old": old, "kiln_head": new}

def deleted_with_direct_alt(h, probe):
    # visible has a direct path AND is also reached via deleted node (two-hop). Depth 1 though -> direct only.
    old, _ = h.chain("kiln", KILN); seed, vis, sub = base(h)
    if probe:
        sub.write_relation(replace(_relation("r-deleted", seed, old, weight=1.0), group_id=TENANT))
        sub.write_relation(replace(_relation("r-old-vis", old, vis, weight=1.0), group_id=TENANT))
    h.prune("kiln")
    return {"seed": seed, "visible": vis, "deleted_old": old}

for fan, lim in ((1, 2), (2, 1), (8, 8)):
    scenario("DELETED higher-ranked neighbor", deleted_neighbor, fan, lim)
for fan, lim in ((1, 2), (2, 1)):
    scenario("CONTROL accessible higher-ranked sibling (legit displacement)", accessible_sibling, fan, lim)
    scenario("CONTROL cross-project higher-ranked neighbor", foreign_neighbor, fan, lim)
    scenario("CONTROL superseded (stale, not deleted) higher-ranked neighbor", superseded_neighbor, fan, lim)
scenario("DELETED neighbor + alt two-hop to visible, depth1", deleted_with_direct_alt, 1, 8)
