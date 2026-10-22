"""#836 independent review, findings A and B: the typed-graph traversal's deletion boundary.

Preregistered before any runtime change (PR #836 review comment 6317441131). Each test states the
behaviour the contract requires; a RED on the unmodified candidate ``2d83db0e`` is the finding
reproduced, a GREEN after the smallest repair is the closure.

A. ``exclude`` (#777) must cover the starting node: a withheld seed is neither traversed nor
   reported, at the retriever and through the governed planner.
B. A deleted generation confers no reachability (docs/44 #777 clause; docs/41: no hop through an
   ineligible node) in the CANONICAL traversal too: with a sole two-hop bridge
   ``seed -> deleted -> live tail`` the tail is not a graph candidate for the reader, while the
   deleted node itself may still surface as a canonical candidate that admission refuses
   (the #777 audit pin, ``test_777_public_projection_review.GraphProjection``, is unchanged).
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from agentmem_ref.recall_control import (
    ControlledRecallPlanner,
    NativeTypedGraphCandidateRetriever,
    RecallControlPlan,
    RecallRouteBudget,
    TYPED_GRAPH_ROUTE,
)
from agentmem_ref.runtime_composition import EXACT_IDENTITY_ROUTE, LEXICAL_ROUTE, SHARED_EVIDENCE_ROUTE
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.test_776_adversarial_review import KILN, _Store
from tests.test_runtime_composition import TENANT, _context
from tests.test_typed_graph_retrieval import TENANT as GRAPH_TENANT, _FixedController, _fact, _relation


def _graph_plan(graph_limit: int = 8, exact: int = 1) -> RecallControlPlan:
    return RecallControlPlan(controller_ref="t836", controller_version="1", route_budgets=(
        RecallRouteBudget(LEXICAL_ROUTE, 0), RecallRouteBudget(EXACT_IDENTITY_ROUTE, exact),
        RecallRouteBudget(TYPED_GRAPH_ROUTE, graph_limit), RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0)))


def _planner(store: _Store, plan: RecallControlPlan | None = None) -> ControlledRecallPlanner:
    return ControlledRecallPlanner(store.adapter, controller=_FixedController(plan or _graph_plan()),
                                   graph_retriever=NativeTypedGraphCandidateRetriever())


class FindingA_ExcludedSeed(unittest.TestCase):
    def test_retriever_never_traverses_or_reports_from_an_excluded_seed(self):
        graph = InMemoryTemporalGraph()
        for ref in ("seed", "tail"):
            graph.write_fact(_fact(ref))
        graph.write_relation(_relation("r-seed-tail", "seed", "tail"))
        retriever = NativeTypedGraphCandidateRetriever()
        # control: without the exclusion the live target is reported
        self.assertEqual([h.candidate_ref for h in retriever.search(graph, ("seed",), group_id=GRAPH_TENANT, candidate_limit=8)],
                         ["tail"])
        hits = retriever.search(graph, ("seed",), group_id=GRAPH_TENANT, candidate_limit=8,
                                exclude=lambda ref: ref == "seed")
        self.assertEqual(hits, [], "an excluded seed must neither be traversed nor reported")

    def test_governed_route_does_not_expand_a_withheld_seed(self):
        # The seed is a live head whose canonical derivation binds a deleted source (#776/#809), so
        # the reader's public view withholds it. It must confer no reachability to its neighbour.
        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        seed = h.chain("digest", [("Digest: the kiln used cone 6 glaze.", None)], evidence_refs=(old,))[0]
        tail = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
        sub = h.adapter.checkpoint_substrate()
        sub.write_relation(replace(_relation("r-digest-shelf", seed, tail), group_id=TENANT))
        h.prune("kiln")
        self.assertTrue(h.adapter.public_identifier_withheld(seed, _context()), "precondition: the seed is withheld")
        result = _planner(h).recall("", _context(), logical_memory_refs=("memory:776r:digest",))
        self.assertNotIn(tail, result.candidates, "no reachability through a withheld seed")
        self.assertNotIn(tail, result.graph_candidate_hits)
        self.assertEqual(result.route_candidate_counts.get(TYPED_GRAPH_ROUTE, 0), 0)
        self.assertNotIn(seed, result.admitted, "the withheld seed itself stays refused at admission")


class FindingB_SoleDeletedBridge(unittest.TestCase):
    def _bridge(self):
        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
        tail = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
        sub = h.adapter.checkpoint_substrate()
        sub.write_relation(replace(_relation("r1", seed, old), group_id=TENANT))
        sub.write_relation(replace(_relation("r2", old, tail), group_id=TENANT))
        return h, old, seed, tail

    def test_live_tail_is_reachable_before_the_bridge_is_deleted(self):
        h, old, seed, tail = self._bridge()
        result = _planner(h).recall("", _context(), logical_memory_refs=("memory:776r:studio",))
        self.assertIn(tail, result.admitted)
        self.assertEqual(result.graph_candidate_hits[tail].path_refs, (seed, old, tail))

    def test_deleted_bridge_confers_no_canonical_reachability(self):
        h, old, seed, tail = self._bridge()
        h.prune("kiln")
        result = _planner(h).recall("", _context(), logical_memory_refs=("memory:776r:studio",))
        # the deleted node may surface as a canonical candidate that admission refuses (#777 audit pin)
        self.assertEqual(result.recall.refusals.get(old), "logical_memory_deleted")
        # ... but it confers no reachability: the tail has no path for this reader
        self.assertNotIn(tail, result.candidates, "a deleted generation confers no reachability")
        self.assertNotIn(tail, result.recall.route_hits)
        self.assertNotIn(tail, result.graph_candidate_hits)
        for ref, hit in result.graph_candidate_hits.items():
            self.assertNotIn(old, hit.path_refs, ref)
        self.assertEqual(result.route_candidate_counts.get(TYPED_GRAPH_ROUTE, 0), 1, "only the refused direct neighbour")

    def test_foreign_deleted_bridge_is_a_control(self):
        # An other-project intermediate is already ineligible (#835); deleting it changes nothing
        # the reader can see, before or after.
        from tests.test_runtime_composition import _proposal
        h = _Store(self)
        seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
        tail = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
        foreign = h.runtime.retain(replace(_proposal("proposal:776r:foreign", operation="promotion", project_ref="project-b"),
                                           target_reference="memory:776r:foreign",
                                           isolation_domain_refs=(TENANT, "project-b"),
                                           required_isolation_domain_refs=("project-b",)),
                                   "Private studio note.")
        self.assertTrue(foreign.committed, foreign)
        sub = h.adapter.checkpoint_substrate()
        sub.write_relation(replace(_relation("r1", seed, foreign.fact_uuid), group_id=TENANT))
        sub.write_relation(replace(_relation("r2", foreign.fact_uuid, tail), group_id=TENANT))
        before = _planner(h).recall("", _context(), logical_memory_refs=("memory:776r:studio",))
        self.assertNotIn(tail, before.candidates)
        self.assertNotIn(foreign.fact_uuid, before.candidates)
        self.assertEqual(before.route_candidate_counts.get(TYPED_GRAPH_ROUTE, 0), 0)


if __name__ == "__main__":
    unittest.main()
