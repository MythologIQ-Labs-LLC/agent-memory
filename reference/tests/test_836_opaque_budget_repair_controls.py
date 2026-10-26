"""#836 C: controls around the opaque-neighbour budget repair in the typed-graph traversal.

Independent qualification receipts for the budget question raised in PR #836 comment 6318816265.
Written and first run against the unmodified cumulative candidate ``07cd8692`` (``recall_control.py``
blob ``c16452ef``) beside an independently written repair; then run unchanged against the owner's
repair at ``2ad4cf23`` (blob ``9fa861c3``), which they pass. The two repairs are behaviourally the
same (no fan-out spent on an opaque neighbour; visible candidates fill ``candidate_limit`` first).
These tests pin what the repair must preserve and what it must change, at the retriever and through
the governed planner:

* an opaque neighbour (withheld for the reader, #836 B) spends no eligible fan-out and takes no
  candidate slot a visible neighbour needs, yet is still reported as a canonical candidate when a
  slot is free, so admission records its refusal (the #777 audit pin);
* the eligibility-probe ceiling (``max_fanout * MAX_GRAPH_ELIGIBILITY_PROBE_FACTOR``) still bounds
  the work, so many opaque neighbours cannot force an unbounded scan: the bounded-work trade-off
  (an eligible neighbour ranked behind more opaque ones than the ceiling allows is not reached) is
  recorded here, not hidden;
* an opaque hop is still never continued through; a raw traversal without the predicate is unchanged;
* through the planner, the canonical visible candidate set and the reported graph hits agree under
  tight budgets, and the cross-project control is unaffected.

* no supported public path executes the typed-graph route: the default runtime planner has no such
  route and the facade exposes no parameter that installs the controlled planner, so the finding is a
  library-level (``ControlledRecallPlanner`` / benchmark harness) retrieval-correctness defect, not a
  default public API exposure.

Negative control (run on the unmodified runtime): the tests marked ``RED-before`` fail there for the
predicted reason; the ``control`` tests pass on both trees.
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from agentmem_ref.recall_control import (
    MAX_GRAPH_ELIGIBILITY_PROBE_FACTOR,
    ControlledRecallPlanner,
    GraphTraversalSpec,
    NativeTypedGraphCandidateRetriever,
    TYPED_GRAPH_ROUTE,
)
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.test_836_graph_exclusion_boundaries import _graph_plan
from tests.test_776_adversarial_review import KILN, _Store
from tests.test_runtime_composition import TENANT, _context, _proposal
from tests.test_typed_graph_retrieval import TENANT as GRAPH_TENANT, _FixedController, _fact, _relation


def _graph(*, hidden_count: int = 1, hidden_weight: float = 1.0, visible_weight: float = 0.8,
           tail: bool = False) -> tuple[InMemoryTemporalGraph, tuple[str, ...]]:
    graph = InMemoryTemporalGraph()
    for ref in ("seed", "visible", "tail"):
        graph.write_fact(_fact(ref))
    hidden = tuple(f"hidden-{i:03d}" for i in range(hidden_count))
    for ref in hidden:
        graph.write_fact(_fact(ref))
        graph.write_relation(_relation(f"r-{ref}", "seed", ref, weight=hidden_weight))
    graph.write_relation(_relation("r-visible", "seed", "visible", weight=visible_weight))
    if tail:
        graph.write_relation(_relation("r-hidden-tail", hidden[0], "tail", weight=1.0))
    return graph, hidden


def _refs(hits) -> list[str]:
    return [hit.candidate_ref for hit in hits]


class RetrieverBudget(unittest.TestCase):
    def _search(self, graph, hidden, *, fanout: int, limit: int, depth: int = 1, opaque=True):
        retriever = NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_depth=depth, max_fanout=fanout))
        predicate = (lambda ref: ref in hidden) if opaque else None
        return retriever.search(graph, ("seed",), group_id=GRAPH_TENANT, candidate_limit=limit, opaque=predicate)

    def test_opaque_neighbour_spends_no_fanout_and_is_still_reported_when_a_slot_is_free(self):
        # RED-before: the unmodified traversal returned ['hidden-000'] only.
        graph, hidden = _graph()
        self.assertEqual(_refs(self._search(graph, hidden, fanout=1, limit=8)), ["hidden-000", "visible"])

    def test_visible_candidates_fill_the_limit_before_opaque_ones(self):
        # RED-before: ordered[:1] was ['hidden-000'] (higher path score).
        graph, hidden = _graph()
        self.assertEqual(_refs(self._search(graph, hidden, fanout=8, limit=1)), ["visible"])
        # with room for both the deterministic ranking is kept: higher score first
        self.assertEqual(_refs(self._search(graph, hidden, fanout=8, limit=2)), ["hidden-000", "visible"])

    def test_opaque_neighbours_below_the_probe_ceiling_do_not_hide_the_visible_one(self):
        # RED-before: ten opaque neighbours exhausted max_fanout=1 before the visible one was probed.
        graph, hidden = _graph(hidden_count=10)
        hits = _refs(self._search(graph, hidden, fanout=1, limit=16))
        self.assertIn("visible", hits)
        self.assertEqual(len(hits), 11)

    def test_probe_ceiling_still_bounds_the_work_and_records_the_trade_off(self):
        # RED-before on the probe count (the unmodified traversal stopped after the first opaque
        # neighbour filled max_fanout=1). The eligibility-probe ceiling itself is unchanged: more
        # opaque neighbours than max_fanout * MAX_GRAPH_ELIGIBILITY_PROBE_FACTOR ranked ahead of
        # the visible one mean the visible one is NOT reached. Bounded work wins over
        # completeness, by design; this test records that trade-off rather than hiding it.
        ceiling = 1 * MAX_GRAPH_ELIGIBILITY_PROBE_FACTOR
        graph, hidden = _graph(hidden_count=ceiling + 4)
        probes: list[str] = []
        retriever = NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_depth=1, max_fanout=1))
        hits = retriever.search(
            graph, ("seed",), group_id=GRAPH_TENANT, candidate_limit=64,
            eligible=lambda fact: probes.append(fact.uuid) or True,
            opaque=lambda ref: ref in hidden,
        )
        # the seed's own eligibility check is not a neighbour probe
        self.assertEqual([ref for ref in probes if ref != "seed"], [ref for ref in probes if ref != "seed"][:ceiling])
        self.assertEqual(len([ref for ref in probes if ref != "seed"]), ceiling, "exactly the probe ceiling is spent")
        self.assertNotIn("visible", _refs(hits), "documented trade-off: beyond the ceiling the visible node is unreached")
        self.assertEqual(len(hits), ceiling)

    def test_opaque_hop_is_still_never_continued_through(self):
        # control (both trees): #836 B unchanged by the budget repair.
        graph, hidden = _graph(tail=True)
        hits = _refs(self._search(graph, hidden, fanout=8, limit=8, depth=2))
        self.assertIn("hidden-000", hits)
        self.assertNotIn("tail", hits, "no reachability through an opaque node")

    def test_raw_traversal_without_an_opaque_predicate_is_unchanged(self):
        # control (both trees): no predicate, no special casing; the raw ranking spends the budget.
        graph, hidden = _graph()
        self.assertEqual(_refs(self._search(graph, hidden, fanout=1, limit=8, opaque=False)), ["hidden-000"])
        self.assertEqual(_refs(self._search(graph, hidden, fanout=8, limit=1, opaque=False)), ["hidden-000"])

    def test_result_is_deterministic(self):
        # control (both trees)
        graph, hidden = _graph(hidden_count=3)
        first = self._search(graph, hidden, fanout=2, limit=3)
        for _ in range(3):
            self.assertEqual(self._search(graph, hidden, fanout=2, limit=3), first)


class PublicPathBoundary(unittest.TestCase):
    """control (both trees): the typed-graph route is not reachable through a supported public path."""

    def test_default_runtime_planner_never_executes_the_typed_graph_route(self):
        import inspect
        from agentmem_ref.api.surface import AgentMemory
        from agentmem_ref.runtime.runtime_composition import ConfiguredCompositionRuntime, DeterministicMultiRouteRecallPlanner

        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
        visible = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
        sub = h.adapter.checkpoint_substrate()
        sub.write_relation(replace(_relation("r-visible", seed, visible, weight=0.80), group_id=TENANT))
        sub.write_relation(replace(_relation("r-deleted", seed, old, weight=1.0), group_id=TENANT))
        h.prune("kiln")
        self.assertIsInstance(h.runtime.recall_planner, DeterministicMultiRouteRecallPlanner)
        result = h.runtime.multi_route_recall("pottery studio glazes", _context(), logical_memory_refs=("memory:776r:studio",))
        self.assertNotIn(TYPED_GRAPH_ROUTE, result.routes_executed)
        self.assertNotIn(old, result.candidates)
        # neither constructor of the composed runtime nor the facade accepts a graph retriever or planner
        for signature in (inspect.signature(ConfiguredCompositionRuntime.create),
                          inspect.signature(ConfiguredCompositionRuntime.__init__),
                          inspect.signature(AgentMemory.open)):
            self.assertFalse({"graph_retriever", "recall_planner", "planner"} & set(signature.parameters), signature)


class PlannerBudget(unittest.TestCase):
    def _store(self, *, neighbour: str):
        h = _Store(self)
        seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
        visible = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
        sub = h.adapter.checkpoint_substrate()
        sub.write_relation(replace(_relation("r-visible", seed, visible, weight=0.80), group_id=TENANT))
        if neighbour == "deleted":
            old, _ = h.chain("kiln", KILN)
            sub.write_relation(replace(_relation("r-other", seed, old, weight=1.0), group_id=TENANT))
            h.prune("kiln")
            other = old
        elif neighbour == "foreign":
            out = h.runtime.retain(replace(_proposal("proposal:776r:foreign", operation="promotion", project_ref="project-b"),
                                           target_reference="memory:776r:foreign",
                                           isolation_domain_refs=(TENANT, "project-b"),
                                           required_isolation_domain_refs=("project-b",)),
                                   "Private studio note.")
            self.assertTrue(out.committed, out)
            other = out.fact_uuid
            sub.write_relation(replace(_relation("r-other", seed, other, weight=1.0), group_id=TENANT))
        else:
            raise AssertionError(neighbour)
        return h, seed, visible, other

    def _recall(self, h, *, fanout: int, limit: int):
        planner = ControlledRecallPlanner(
            h.adapter, controller=_FixedController(_graph_plan(limit, 1)),
            graph_retriever=NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_depth=1, max_fanout=fanout)))
        return planner.recall("", _context(), logical_memory_refs=("memory:776r:studio",))

    def test_canonical_visible_candidates_agree_with_reported_graph_hits(self):
        # RED-before: the reported traversal listed the visible sibling while the canonical one
        # had spent its budget on the withheld neighbour, so candidates and diagnostics disagreed.
        for fanout, limit in ((1, 2), (2, 1), (1, 1)):
            with self.subTest(fanout=fanout, limit=limit):
                h, seed, visible, old = self._store(neighbour="deleted")
                result = self._recall(h, fanout=fanout, limit=limit)
                context = _context()
                visible_graph_candidates = {
                    ref for ref in result.candidates
                    if ref != seed and not h.adapter.public_identifier_withheld(ref, context)}
                self.assertEqual(visible_graph_candidates, set(result.graph_candidate_hits))
                self.assertIn(visible, result.admitted)
                self.assertNotIn(old, result.admitted)
                self.assertNotIn(old, result.graph_candidate_hits)
                self.assertLessEqual(result.route_candidate_counts[TYPED_GRAPH_ROUTE], limit)

    def test_refusal_audit_is_retained_whenever_a_slot_is_free(self):
        # RED-before on the admitted assertion; the refusal assertion held on both trees.
        h, seed, visible, old = self._store(neighbour="deleted")
        result = self._recall(h, fanout=1, limit=2)
        self.assertIn(visible, result.admitted)
        self.assertEqual(result.recall.refusals.get(old), "logical_memory_deleted",
                         "the #777 canonical refusal audit is kept when the budget has room")
        self.assertEqual(result.route_candidate_counts[TYPED_GRAPH_ROUTE], 2)

    def test_refusal_audit_yields_only_to_a_visible_candidate_under_a_one_slot_budget(self):
        # RED-before: the single canonical slot went to the withheld neighbour.
        h, seed, visible, old = self._store(neighbour="deleted")
        result = self._recall(h, fanout=2, limit=1)
        self.assertEqual([ref for ref in result.candidates if ref != seed], [visible])
        self.assertNotIn(old, result.recall.refusals, "no candidate, so nothing to refuse: the budget bound is one slot")

    def test_cross_project_neighbour_is_a_control(self):
        # control (both trees): #835 eligibility already keeps a foreign neighbour out of the budget.
        for fanout, limit in ((1, 2), (2, 1)):
            with self.subTest(fanout=fanout, limit=limit):
                h, seed, visible, foreign = self._store(neighbour="foreign")
                result = self._recall(h, fanout=fanout, limit=limit)
                self.assertIn(visible, result.admitted)
                self.assertNotIn(foreign, result.candidates)
                self.assertNotIn(foreign, result.recall.refusals)
                self.assertEqual(result.route_candidate_counts[TYPED_GRAPH_ROUTE], 1)


if __name__ == "__main__":
    unittest.main()
