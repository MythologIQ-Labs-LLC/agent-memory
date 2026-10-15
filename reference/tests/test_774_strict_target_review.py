"""#774 strict caller-targeted predecessor contract: independent adversarial tests.

Authored before the implementation. A predecessor is asserted only for a successor the
caller identifies (an authorized fact reference, or an unambiguous governed as-of target
on a named logical memory). Unresolved targeting never claims "no predecessor existed"
and never changes ordinary historical ranking.
"""
from __future__ import annotations

import unittest

from tests.test_774_governed_predecessor import E, S, _History
from tests.test_runtime_composition import _context

THREE = [("The seminar room booking limit is 2 hours.", None),
         ("The seminar room booking limit is 3 hours.", S),
         ("The seminar room booking limit is 4 hours.", S)]
CORRECTED = [("The seminar fee is 10 credits.", None),
             ("The seminar fee is 15 credits.", S),
             ("The seminar fee is 14 credits.", E)]
Q = "What was the seminar room booking limit before?"


class StrictTargetResolution(unittest.TestCase):
    def test_unresolved_target_reports_unresolved_not_absence(self):
        h = _History(self, {"room": THREE})
        out = h.select(Q)
        self.assertIsNone(out.predecessor_ref)
        self.assertEqual(out.target_resolution, "unresolved")
        self.assertEqual(out.selection_policy_version, "0.2.0")
        self.assertEqual(tuple(out.served_refs), tuple(h.recall(Q, "historical").ranked_admitted[:3]))

    def test_first_version_resolves_with_no_governed_predecessor(self):
        h = _History(self, {"room": THREE})
        out = h.select(Q, successor_ref=h.ids["room"][0])
        self.assertIsNone(out.predecessor_ref)
        self.assertEqual(out.target_resolution, "resolved")

    def test_every_declared_successor_in_a_chain(self):
        h = _History(self, {"room": THREE})
        v1, v2, v3 = h.ids["room"]
        self.assertEqual(h.select(Q, successor_ref=v2).predecessor_ref, v1)
        self.assertEqual(h.select(Q, successor_ref=v3).predecessor_ref, v2)

    def test_error_corrected_successor_never_held_and_is_unresolved(self):
        h = _History(self, {"fee": CORRECTED})
        v1, v2, v3 = h.ids["fee"]
        with self.assertRaises(ValueError):  # a value corrected as false is not a visible successor
            h.select("What was the seminar fee before?", successor_ref=v2)
        out = h.select("What was the seminar fee before?", successor_ref=v3)
        self.assertEqual(out.predecessor_ref, v1)  # v2 never held

    def test_duplicate_text_in_two_memories_resolves_by_identity(self):
        h = _History(self, {"room": THREE, "room-b": THREE})
        a1, a2, _ = h.ids["room"]
        b1, b2, _ = h.ids["room-b"]
        self.assertEqual(h.select(Q, successor_ref=b2).predecessor_ref, b1)
        self.assertEqual(h.select(Q, successor_ref=a2).predecessor_ref, a1)

    def test_out_of_budget_predecessor_is_promoted_for_a_declared_target(self):
        h = _History(self, {"room": THREE})
        for i in range(6):
            h.runtime.retain(h._proposal(f"noise{i}", 0), f"The seminar room booking limit note {i}.")
        v1, v2, v3 = h.ids["room"]
        out = h.select(Q, successor_ref=v2, budget=1)
        self.assertEqual(out.served_refs, (v1,))


class AsOfTargets(unittest.TestCase):
    def _times(self, h, refs):
        return [h.runtime.adapter._substrate.get_fact(r).created_at for r in refs]

    def test_as_of_on_a_named_memory_resolves_the_version_then_in_effect(self):
        from agentmem_ref.runtime_composition import AsOfTarget
        h = _History(self, {"room": THREE})
        v1, v2, v3 = h.ids["room"]
        t1, t2, t3 = self._times(h, (v1, v2, v3))
        out = h.select(Q, as_of_target=AsOfTarget(memory_ref="memory:774:room", instant=t2))
        self.assertEqual((out.successor_ref, out.predecessor_ref, out.target_resolution), (v2, v1, "resolved"))

    def test_as_of_before_the_memory_existed_or_unknown_memory_is_unresolved(self):
        from agentmem_ref.runtime_composition import AsOfTarget
        h = _History(self, {"room": THREE})
        for target in (AsOfTarget(memory_ref="memory:774:room", instant="2000-01-01T00:00:00Z"),
                       AsOfTarget(memory_ref="memory:774:none", instant="2026-01-01T00:00:10Z")):
            with self.subTest(target=target):
                out = h.select(Q, as_of_target=target)
                self.assertIsNone(out.predecessor_ref)
                self.assertEqual(out.target_resolution, "unresolved")

    def test_as_of_on_other_project_or_deleted_memory_is_unresolved_without_leak(self):
        from agentmem_ref.runtime_composition import AsOfTarget
        h = _History(self, {"room": THREE})
        h.write_chain("secret", THREE, project="project-beta")
        t = self._times(h, h.ids["secret"])[1]
        foreign = h.select(Q, as_of_target=AsOfTarget(memory_ref="memory:774:secret", instant=t))
        unknown = h.select(Q, as_of_target=AsOfTarget(memory_ref="memory:774:none", instant=t))
        self.assertEqual((foreign.predecessor_ref, foreign.target_resolution), (None, "unresolved"))
        self.assertEqual(foreign.served_refs, unknown.served_refs)
        self.assertFalse(set(h.ids["secret"]) & set(foreign.served_refs))
        t_room = self._times(h, h.ids["room"])[1]
        h.delete("room")
        out = h.select(Q, as_of_target=AsOfTarget(memory_ref="memory:774:room", instant=t_room))
        self.assertEqual(out.target_resolution, "unresolved")
        self.assertFalse(set(h.ids["room"]) & set(out.served_refs))

    def test_both_targets_or_malformed_target_are_rejected(self):
        from agentmem_ref.runtime_composition import AsOfTarget
        h = _History(self, {"room": THREE})
        with self.assertRaises(ValueError):
            h.select(Q, successor_ref=h.ids["room"][1],
                     as_of_target=AsOfTarget(memory_ref="memory:774:room", instant="2026-01-01T00:00:10Z"))
        with self.assertRaises(ValueError):
            AsOfTarget(memory_ref="", instant="2026-01-01T00:00:10Z")
        with self.assertRaises(ValueError):
            AsOfTarget(memory_ref="memory:774:room", instant="yesterday")


class RoutingNeverPromotesWithoutTarget(unittest.TestCase):
    def test_routed_context_promotes_only_with_a_resolved_target(self):
        h = _History(self, {"room": THREE})
        v1, v2, v3 = h.ids["room"]
        hist = {"mode": "historical"}
        plain = tuple(h.recall(Q, "historical").ranked_admitted[:3])
        untargeted = h.runtime.routed_historical_context(Q, _context(), budget=3, temporal_intent=hist)
        self.assertFalse(untargeted.routed)
        self.assertEqual(untargeted.served_refs, plain)
        targeted = h.runtime.routed_historical_context(Q, _context(), budget=3, temporal_intent=hist,
                                                       successor_ref=v3)
        self.assertTrue(targeted.routed)
        self.assertEqual(targeted.predecessor_ref, v2)


if __name__ == "__main__":
    unittest.main()
