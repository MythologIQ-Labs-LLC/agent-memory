"""#774 strict predecessor identification: no inference of an older target.

These tests capture the owner decision after independent blind Q19. Existing
unqualified #774 implicit routing is intentionally expected to fail the
negative cases. Do not tune based on theatre/ticket literals.
"""
from __future__ import annotations

import unittest

from tests.test_774_governed_predecessor import _History, S
from tests.test_runtime_composition import _context
from agentmem_ref.runtime_composition import predecessor_routing

PRICES = [
    ("Arbor museum membership used monthly dues of 12 credits.", None),
    ("Arbor museum membership changed to 18 credits.", S),
    ("Arbor museum membership changed to 25 credits.", S),
    ("Arbor museum membership changed to 32 credits.", S),
]


class StrictHistoricalSuccessorTargets(unittest.TestCase):
    def test_declared_older_successor_yields_its_own_predecessor(self):
        h = _History(self, {"membership": PRICES})
        v1, v2, v3, v4 = h.ids["membership"]
        result = h.select(
            "What were the membership dues before the 25 credit schedule?",
            successor_ref=v3,
        )
        self.assertEqual(result.predecessor_ref, v2)
        self.assertEqual(result.successor_ref, v3)
        self.assertEqual(result.served_refs[0], v2)
        self.assertNotEqual(result.predecessor_ref, v3)

    def test_missing_successor_identity_must_not_assume_current_head(self):
        h = _History(self, {"membership": PRICES})
        v1, v2, v3, v4 = h.ids["membership"]
        query = "Which membership dues preceded a previously recorded change?"
        plain = h.recall(query, "historical")
        result = h.select(query)
        # Unresolved target is not proof of any predecessor. It may leave
        # ordinary historical evidence available in existing rank order.
        self.assertIsNone(result.predecessor_ref)
        self.assertIsNone(result.successor_ref)
        self.assertEqual(tuple(result.served_refs), tuple(plain.ranked_admitted[:3]))

    def test_no_auto_predecessor_promotion_for_ambiguous_historical_target(self):
        h = _History(self, {"membership": PRICES})
        query = "What were the membership dues before an earlier increase?"
        # This is a true positive lexical route cue, but it has no governed
        # identity for *which* later price version the user meant.
        self.assertTrue(predecessor_routing(query).routed)
        selected = h.runtime.routed_historical_context(
            query, _context(), budget=3, temporal_intent={"mode": "historical"},
        )
        plain = h.recall(query, "historical")
        self.assertIsNone(selected.predecessor_ref)
        self.assertFalse(selected.routed)
        self.assertEqual(selected.served_refs, tuple(plain.ranked_admitted[:3]))

    def test_explicit_current_successor_preserves_latest_predecessor_behavior(self):
        h = _History(self, {"membership": PRICES})
        v1, v2, v3, v4 = h.ids["membership"]
        result = h.select(
            "What membership dues preceded the latest schedule?",
            successor_ref=v4,
        )
        self.assertEqual(result.predecessor_ref, v3)
        self.assertEqual(result.served_refs[0], v3)


if __name__ == "__main__":
    unittest.main()
