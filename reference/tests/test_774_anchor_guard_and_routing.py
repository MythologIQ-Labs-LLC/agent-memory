"""#774 follow-on: wrong-subject anchor guard and automatic predecessor routing.

Preregistered before implementation (generic histories; no Halcyon, Cedarline
or Brightwater wording). The explicit, caller-declared selector behaviour of
ce1fdfc must be preserved; routing must never send every historical question
to an older value.
"""
from __future__ import annotations

import unittest

from tests.test_774_governed_predecessor import KILN, S, TRAM, _History

CRANE = [("The dock crane inspection uses checklist form C.", None)]
TRAM_INSPECTION = [("Route 4 tram inspection happens every 20 days.", None),
                   ("Route 4 tram inspection happens every 15 days.", S)]


class WrongSubjectAnchorGuard(unittest.TestCase):
    def test_unrelated_lineage_outside_the_served_budget_is_never_promoted(self):
        # The asked-about memory has no history; an unrelated chain ranks below
        # the budget. Promoting its predecessor would displace the answer.
        h = _History(self, {"crane": CRANE, "tram": TRAM_INSPECTION})
        query = "Which checklist form did the dock crane inspection use before?"
        base = list(h.recall(query, "historical").ranked_admitted)
        self.assertEqual(base[0], h.ids["crane"][0])
        self.assertIn(h.ids["tram"][1], base)  # the unrelated chain is admitted, just lower
        out = h.select(query, budget=1)
        self.assertIsNone(out.predecessor_ref)
        self.assertEqual(out.served_refs, (h.ids["crane"][0],))

    def test_lineage_inside_the_served_budget_below_rank_one_still_anchors(self):
        h = _History(self, {"kiln": KILN})
        h.runtime.retain(h._proposal("why", 0),
                         "The kiln firing schedule glaze changed because cone 6 glaze crazed on the stoneware.")
        query = "What glaze did the kiln firing schedule use before the glaze changed?"
        base = list(h.recall(query, "historical").ranked_admitted)
        old, new = h.ids["kiln"]
        self.assertIn(new, base[:3])
        out = h.select(query, budget=3)
        self.assertEqual((out.predecessor_ref, out.served_refs[0]), (old, old))

    def test_declared_successor_is_not_gated(self):
        h = _History(self, {"crane": CRANE, "tram": TRAM_INSPECTION})
        out = h.select("Which checklist form did the dock crane inspection use before?", budget=1,
                       successor_ref=h.ids["tram"][1])
        self.assertEqual(out.predecessor_ref, h.ids["tram"][0])


class PredecessorRouting(unittest.TestCase):
    def decide(self, query):
        from agentmem_ref.runtime_composition import predecessor_routing
        return predecessor_routing(query)

    def test_predecessor_relation_cues_route(self):
        for query in ("What was the glaze before the current one?",
                      "Which engine did the catalogue previously run on?",
                      "How often did the trams used to run?",
                      "Which host formerly ran the builds?",
                      "What was the fee prior to the change?",
                      "Which form did we use earlier?"):
            with self.subTest(query=query):
                decision = self.decide(query)
                self.assertTrue(decision.routed, decision)
                self.assertTrue(decision.evidence)
                self.assertEqual(decision.authority_effect, "none")

    def test_other_historical_questions_do_not_route(self):
        for query in ("What did the catalogue originally run on?",
                      "Which form did the inspection initially use?",
                      "What was the schedule at first?",
                      "Why did the billing frequency change?",
                      "What happened with the billing migration?",
                      "What did the team decide in the past about retention?",
                      "How often do Route 4 trams run?",
                      "Which version will we deploy before next week's freeze?",
                      "What does the word 'before' mean in the runbook?"):
            with self.subTest(query=query):
                self.assertFalse(self.decide(query).routed)

    def test_routing_is_query_only_and_deterministic(self):
        a = self.decide("What was the glaze before the current one?")
        b = self.decide("What was the glaze before the current one?")
        self.assertEqual(a, b)
        with self.assertRaises(TypeError):
            self.decide(None)


class RoutedRecall(unittest.TestCase):
    def test_routed_question_serves_the_predecessor_first(self):
        h = _History(self, {"kiln": KILN})
        out = h.runtime.routed_historical_context(
            "What glaze did the kiln firing schedule use before cone 10?", _ctx(), budget=3, temporal_intent=HIST)
        self.assertTrue(out.routed)
        self.assertEqual(out.served_refs[0], h.ids["kiln"][0])
        self.assertEqual(out.predecessor_ref, h.ids["kiln"][0])

    def test_unrouted_question_is_identical_to_unchanged_recall(self):
        h = _History(self, {"tram": TRAM})
        for query, intent in (("What did Route 4 trams originally run?", {"mode": "historical"}),
                              ("How often do Route 4 trams run?", {"mode": "current"}),
                              ("How often do Route 4 trams run?", None)):
            with self.subTest(query=query, intent=intent):
                out = h.runtime.routed_historical_context(query, _ctx(), budget=3, temporal_intent=intent)
                base = h.runtime.multi_route_recall(query, _ctx(), temporal_intent=intent)
                self.assertFalse(out.routed)
                self.assertIsNone(out.predecessor_ref)
                self.assertEqual(out.served_refs, tuple(base.ranked_admitted[:3]))

    def test_only_caller_historical_questions_are_routed(self):
        # v0.1.0 finding (Halcyon H08): "How long before ... times out?" is a CURRENT
        # question; routing it served a superseded value first (P0 stale). Automatic
        # routing must never act on current or timeless questions, or when no
        # historical intent was given.
        h = _History(self, {"tram": TRAM})
        query = "How long before the Route 4 tram leaves does boarding close?"
        self.assertTrue(PredecessorRoutingHelpers.decide(query).routed)  # the cue is present ...
        for intent in ({"mode": "current"}, {"mode": "atemporal_or_unspecified"}, None):
            with self.subTest(intent=intent):
                out = h.runtime.routed_historical_context(query, _ctx(), budget=3, temporal_intent=intent)
                base = h.runtime.multi_route_recall(query, _ctx(), temporal_intent=intent)
                self.assertFalse(out.routed)  # ... but only a historical question may be routed
                self.assertEqual(out.served_refs, tuple(base.ranked_admitted[:3]))
                self.assertNotIn(h.ids["tram"][0], out.served_refs[:1])

    def test_routed_question_without_lineage_keeps_historical_ranking(self):
        h = _History(self, {"crane": CRANE})
        query = "Which checklist form did the dock crane inspection use before?"
        out = h.runtime.routed_historical_context(query, _ctx(), budget=3, temporal_intent=HIST)
        self.assertTrue(out.routed)
        self.assertIsNone(out.predecessor_ref)
        self.assertEqual(out.served_refs, tuple(h.recall(query, "historical").ranked_admitted[:3]))

    def test_routed_deleted_memory_serves_nothing_of_it(self):
        h = _History(self, {"kiln": KILN})
        h.delete("kiln")
        out = h.runtime.routed_historical_context(
            "What glaze did the kiln firing schedule use before cone 10?", _ctx(), budget=3, temporal_intent=HIST)
        self.assertFalse(set(h.ids["kiln"]) & set(out.served_refs))


HIST = {"mode": "historical"}


class PredecessorRoutingHelpers:
    @staticmethod
    def decide(query):
        from agentmem_ref.runtime_composition import predecessor_routing
        return predecessor_routing(query)


def _ctx():
    from tests.test_runtime_composition import _context
    return _context()


if __name__ == "__main__":
    unittest.main()
