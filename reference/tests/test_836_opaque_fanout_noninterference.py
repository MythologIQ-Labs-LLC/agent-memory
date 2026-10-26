"""#836 independent review follow-up (PR #836 comment 6318816265): opaque neighbour budget noninterference.

Preregistered before any runtime change, on the amended head ``07cd8692``
(``runtime/recall_control.py`` blob ``c16452ef``). Question under test: the canonical typed-graph
traversal reports a withheld (``opaque``) neighbour as a candidate for the #777 refusal audit, but it
counts that neighbour against the finite discovery budget (``accepted_fanout``) and lets it occupy a
``candidate_limit`` slot. Can a node the reader cannot see therefore displace an accessible sibling,
so that the public result differs based solely on the hidden node's presence?

Contract (docs/44 #777 clause, docs/41, #809 public noninterference): a deleted or withheld generation
confers no reachability and must not change what the reader can discover. The accepted bounded-work
trade-off (#835 probe ceiling) applies to INELIGIBLE neighbours, which never spend fan-out; nothing
in the accepted contract lets a withheld neighbour spend the budget an accessible sibling needs.
The #777 audit pin is kept: the withheld neighbour may still surface as a canonical candidate that
admission refuses, with the refusal recorded.

Each differential pairs the SAME reader, query, budget and visible data with and without the hidden
node. A RED on the unmodified head is the finding reproduced; the controls stay GREEN throughout.
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from agentmem_ref.recall_control import (
    ControlledRecallPlanner,
    GraphTraversalSpec,
    NativeTypedGraphCandidateRetriever,
    RecallControlPlan,
    RecallRouteBudget,
    TYPED_GRAPH_ROUTE,
)
from agentmem_ref.runtime_composition import EXACT_IDENTITY_ROUTE, LEXICAL_ROUTE, SHARED_EVIDENCE_ROUTE
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.test_776_adversarial_review import KILN, _Store
from tests.test_runtime_composition import TENANT, _context, _proposal
from tests.test_typed_graph_retrieval import TENANT as GRAPH_TENANT, _FixedController, _fact, _relation

HIDDEN, VISIBLE = "hidden", "visible"


def _graph_plan(graph_limit: int = 8, exact: int = 1) -> RecallControlPlan:
    return RecallControlPlan(controller_ref="t836f", controller_version="1", route_budgets=(
        RecallRouteBudget(LEXICAL_ROUTE, 0), RecallRouteBudget(EXACT_IDENTITY_ROUTE, exact),
        RecallRouteBudget(TYPED_GRAPH_ROUTE, graph_limit), RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0)))


def _retriever(max_fanout: int = 8) -> NativeTypedGraphCandidateRetriever:
    return NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_fanout=max_fanout))


def _planner(store: _Store, *, graph_limit: int = 8, max_fanout: int = 8) -> ControlledRecallPlanner:
    return ControlledRecallPlanner(store.adapter, controller=_FixedController(_graph_plan(graph_limit)),
                                   graph_retriever=_retriever(max_fanout))


class RetrieverLevel(unittest.TestCase):
    """``NativeTypedGraphCandidateRetriever.search`` with ``opaque`` naming the hidden neighbour."""

    def _graph(self, *, with_hidden: bool = True, hidden_group: str = GRAPH_TENANT) -> InMemoryTemporalGraph:
        graph = InMemoryTemporalGraph()
        graph.write_fact(_fact("seed"))
        graph.write_fact(_fact(VISIBLE))
        graph.write_fact(_fact(HIDDEN, group=hidden_group))
        if with_hidden:
            # the hidden neighbour outranks the visible one, so it is visited first
            graph.write_relation(_relation("r-hidden", "seed", HIDDEN, weight=1.0))
        graph.write_relation(_relation("r-visible", "seed", VISIBLE, weight=0.8))
        return graph

    @staticmethod
    def _refs(hits):
        return [hit.candidate_ref for hit in hits]

    def test_control_without_the_hidden_node_the_visible_neighbour_is_found(self):
        for max_fanout, limit in ((1, 8), (8, 1)):
            hits = _retriever(max_fanout).search(self._graph(with_hidden=False), ("seed",), group_id=GRAPH_TENANT,
                                                 candidate_limit=limit, opaque=lambda ref: ref == HIDDEN)
            self.assertEqual(self._refs(hits), [VISIBLE], (max_fanout, limit))

    def test_control_a_live_higher_ranked_neighbour_legitimately_takes_the_single_slot(self):
        # accepted bounded-work baseline: with nothing hidden, max_fanout=1 (or candidate_limit=1)
        # keeps only the best-ranked neighbour
        for max_fanout, limit in ((1, 8), (8, 1)):
            hits = _retriever(max_fanout).search(self._graph(), ("seed",), group_id=GRAPH_TENANT, candidate_limit=limit)
            self.assertEqual(self._refs(hits), [HIDDEN], (max_fanout, limit))

    def test_control_an_other_project_neighbour_never_spends_the_budget(self):
        # #835: an ineligible neighbour is neither reported nor charged against fan-out
        graph = self._graph(hidden_group="other-project")
        for max_fanout, limit in ((1, 8), (8, 1)):
            hits = _retriever(max_fanout).search(
                graph, ("seed",), group_id=GRAPH_TENANT, candidate_limit=limit,
                eligible=lambda fact: fact.group_id == GRAPH_TENANT,
                eligible_identity=lambda uuid, group_id: uuid != HIDDEN)
            self.assertEqual(self._refs(hits), [VISIBLE], (max_fanout, limit))

    def test_opaque_neighbour_must_not_spend_the_fanout_an_accessible_sibling_needs(self):
        hits = _retriever(max_fanout=1).search(self._graph(), ("seed",), group_id=GRAPH_TENANT, candidate_limit=8,
                                               opaque=lambda ref: ref == HIDDEN)
        self.assertIn(VISIBLE, self._refs(hits),
                      "a withheld neighbour confers no reachability and must not starve the visible sibling (max_fanout=1)")
        self.assertIn(HIDDEN, self._refs(hits), "the withheld neighbour is still reported for the #777 refusal audit")

    def test_opaque_hit_must_not_displace_an_accessible_hit_at_the_candidate_limit(self):
        hits = _retriever(max_fanout=8).search(self._graph(), ("seed",), group_id=GRAPH_TENANT, candidate_limit=1,
                                               opaque=lambda ref: ref == HIDDEN)
        self.assertIn(VISIBLE, self._refs(hits),
                      "a withheld canonical hit must not occupy the only candidate_limit slot (candidate_limit=1)")

    def test_opaque_hits_stay_bounded(self):
        # accessible hits fill the route budget first; withheld neighbours are reported for the
        # audit only in the budget that remains, so a route never returns more than its budget
        graph = InMemoryTemporalGraph()
        graph.write_fact(_fact("seed"))
        for i in range(20):
            graph.write_fact(_fact(f"hidden-{i:02d}"))
            graph.write_relation(_relation(f"r-{i:02d}", "seed", f"hidden-{i:02d}", weight=1.0))
        graph.write_fact(_fact(VISIBLE))
        graph.write_relation(_relation("r-visible", "seed", VISIBLE, weight=0.5))
        hits = _retriever(max_fanout=4).search(graph, ("seed",), group_id=GRAPH_TENANT, candidate_limit=3,
                                               opaque=lambda ref: ref.startswith("hidden-"))
        self.assertIn(VISIBLE, self._refs(hits))
        self.assertEqual(len(hits), 3, "a route never returns more than its budget")
        self.assertEqual(sum(ref.startswith("hidden-") for ref in self._refs(hits)), 2, "audited hits fill the remainder")


class GovernedLevel(unittest.TestCase):
    """``ControlledRecallPlanner.recall`` (the governed route) and the public facade under one reader."""

    def _store(self, *, with_hidden: bool = True):
        h = _Store(self)
        old, _ = h.chain("kiln", KILN)                                   # old generation: withheld after prune
        seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
        tail = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
        sub = h.adapter.checkpoint_substrate()
        if with_hidden:
            sub.write_relation(replace(_relation("r-hidden", seed, old, weight=1.0), group_id=TENANT))
        sub.write_relation(replace(_relation("r-visible", seed, tail, weight=0.8), group_id=TENANT))
        return h, old, seed, tail

    def _recall(self, h, **kw):
        return _planner(h, **kw).recall("", _context(), logical_memory_refs=("memory:776r:studio",))

    def test_control_before_the_prune_the_live_neighbour_legitimately_takes_the_slot(self):
        h, old, seed, tail = self._store()
        self.assertFalse(h.adapter.public_identifier_withheld(old, _context()))
        for kw in ({"max_fanout": 1}, {"graph_limit": 1}):
            result = self._recall(h, **kw)
            # the superseded-but-visible generation is a legitimate canonical candidate (admission
            # then rules on its currentness); it takes the only slot and the lower-ranked tail is not reached
            self.assertIn(old, result.candidates, kw)
            self.assertNotIn(tail, result.candidates, kw)

    def test_control_without_the_hidden_node_the_live_neighbour_is_admitted(self):
        h, old, seed, tail = self._store(with_hidden=False)
        h.prune("kiln")
        for kw in ({"max_fanout": 1}, {"graph_limit": 1}):
            result = self._recall(h, **kw)
            self.assertIn(tail, result.admitted, kw)
            self.assertEqual(result.graph_candidate_hits[tail].path_refs, (seed, tail))

    def test_control_an_other_project_neighbour_does_not_displace_the_live_neighbour(self):
        h = _Store(self)
        seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
        tail = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
        foreign = h.runtime.retain(replace(_proposal("proposal:776f:foreign", operation="promotion", project_ref="project-b"),
                                           target_reference="memory:776f:foreign",
                                           isolation_domain_refs=(TENANT, "project-b"),
                                           required_isolation_domain_refs=("project-b",)),
                                   "Private studio note.")
        self.assertTrue(foreign.committed, foreign)
        sub = h.adapter.checkpoint_substrate()
        sub.write_relation(replace(_relation("r-foreign", seed, foreign.fact_uuid, weight=1.0), group_id=TENANT))
        sub.write_relation(replace(_relation("r-visible", seed, tail, weight=0.8), group_id=TENANT))
        for kw in ({"max_fanout": 1}, {"graph_limit": 1}):
            result = self._recall(h, **kw)
            self.assertIn(tail, result.admitted, kw)
            self.assertNotIn(foreign.fact_uuid, result.candidates, kw)

    def test_withheld_neighbour_must_not_starve_the_live_neighbour_under_fanout_pressure(self):
        h, old, seed, tail = self._store()
        h.prune("kiln")
        self.assertTrue(h.adapter.public_identifier_withheld(old, _context()), "precondition: the neighbour is withheld")
        result = self._recall(h, max_fanout=1)
        self.assertIn(tail, result.admitted,
                      "public result must not lose the accessible neighbour because a withheld one outranks it (max_fanout=1)")
        self.assertEqual(result.graph_candidate_hits[tail].path_refs, (seed, tail))
        self.assertNotIn(old, result.admitted)
        self.assertEqual(result.recall.refusals.get(old), "logical_memory_deleted", "the #777 audit still records the refusal")

    def test_withheld_canonical_hit_must_not_displace_the_live_neighbour_under_truncation_pressure(self):
        h, old, seed, tail = self._store()
        h.prune("kiln")
        result = self._recall(h, graph_limit=1)
        self.assertIn(tail, result.admitted,
                      "public result must not lose the accessible neighbour to a withheld canonical hit (candidate_limit=1)")
        self.assertNotIn(old, result.admitted)

    def test_public_facade_sees_the_same_noninterference(self):
        # the public facade with the governed planner installed, same reader, same budget
        h, old, seed, tail = self._store()
        h.prune("kiln")
        for kw in ({"max_fanout": 1}, {"graph_limit": 1}):
            h.runtime.recall_planner = _planner(h, **kw)
            result = h.recall("", mode="current", logical_memory_refs=("memory:776r:studio",))
            self.assertIn(tail, result.admitted, kw)
            self.assertNotIn(old, result.admitted, kw)


if __name__ == "__main__":
    unittest.main()
