"""Independent review findings on the #774 as-of target (P1), pinned as invariants.

1. A version corrected as false never held, but the other versions of the memory still
   resolve: an as-of instant at a later version must resolve that version, exactly as the
   same successor declared by reference does.
2. A deleted version is a barrier for as-of resolution as it is for the predecessor walk: an
   instant at which the deleted version was in effect resolves nothing, never an older
   version that had already been superseded.
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from agentmem_ref import policy
from agentmem_ref.runtime.runtime_composition import AsOfTarget
from tests.test_774_governed_predecessor import E, S, TRAM, _History
from tests.test_runtime_composition import _context

MEM = "memory:774:tram"
Q = "How often did Route 4 trams run?"


def _at(h, uuid):
    return h.runtime.adapter._substrate.get_fact(uuid).created_at


class AsOfTargetReview(unittest.TestCase):
    def test_error_corrected_version_does_not_block_as_of_resolution(self):
        h = _History(self, {"tram": [("Route 4 trams run every 20 minutes.", None),
                                     ("Route 4 trams run every 15 minutes.", E),
                                     ("Route 4 trams run every 10 minutes.", S)]})
        v1, v2, v3 = h.ids["tram"]
        ad, ctx = h.runtime.adapter, _context()
        self.assertEqual(ad.version_in_effect(MEM, _at(h, v3), ctx), v3)
        self.assertEqual(ad.version_in_effect(MEM, _at(h, v2), ctx), v2)
        self.assertIsNone(ad.version_in_effect(MEM, _at(h, v1), ctx))  # v1 never held
        as_of = h.select(Q, as_of_target=AsOfTarget(MEM, _at(h, v3)))
        declared = h.select(Q, successor_ref=v3)
        self.assertEqual((as_of.target_resolution, as_of.successor_ref, as_of.predecessor_ref),
                         ("resolved", v3, v2))
        self.assertEqual((declared.successor_ref, declared.predecessor_ref), (v3, v2))
        self.assertEqual(as_of.served_refs, declared.served_refs)

    def test_deleted_superseded_version_is_a_barrier_for_as_of(self):
        h = _History(self, {"tram": TRAM})
        v1, v2, v3 = h.ids["tram"]
        out = h.runtime.durable_runtime.governed_delete(
            replace(h._proposal("tram", 97, op="pruning", review_satisfied=True, approval_refs=("approval:774",)),
                    target_class=policy.M1, proposed_strength="tentative"), v2, derived_refs=())
        self.assertTrue(out.committed, out)
        ad, ctx = h.runtime.adapter, _context()
        self.assertEqual(ad.version_in_effect(MEM, _at(h, v1), ctx), v1)
        self.assertIsNone(ad.version_in_effect(MEM, _at(h, v2), ctx))  # v2 was in effect and is deleted
        self.assertEqual(ad.version_in_effect(MEM, _at(h, v3), ctx), v3)
        sel = h.select(Q, as_of_target=AsOfTarget(MEM, _at(h, v2)))
        self.assertEqual(sel.target_resolution, "unresolved")
        self.assertNotIn(v2, sel.served_refs)
        # consistent with the predecessor walk, which refuses to cross the deleted version
        self.assertIsNone(ad.governed_state_change_predecessor(v3, ctx))
        later = h.select(Q, as_of_target=AsOfTarget(MEM, _at(h, v3)))
        self.assertEqual((later.target_resolution, later.successor_ref, later.predecessor_ref), ("resolved", v3, None))

    def test_as_of_inside_a_deleted_generation_resolves_nothing_after_recreation(self):
        h = _History(self, {"tram": TRAM})
        v1, v2, v3 = h.ids["tram"]
        h.delete("tram")
        n1 = h.runtime.retain(h._proposal("tram", 60), "Route 4 trams run every 8 minutes.").fact_uuid
        ad, ctx = h.runtime.adapter, _context()
        for old in (v1, v2, v3):
            self.assertIsNone(ad.version_in_effect(MEM, _at(h, old), ctx))
        self.assertEqual(ad.version_in_effect(MEM, _at(h, n1), ctx), n1)
        sel = h.select(Q, as_of_target=AsOfTarget(MEM, _at(h, v2)))
        self.assertEqual(sel.target_resolution, "unresolved")
        self.assertFalse({v1, v2, v3} & set(sel.served_refs))

    def test_other_project_reader_resolves_nothing(self):
        h = _History(self, {"tram": TRAM})
        v1, v2, v3 = h.ids["tram"]
        self.assertIsNone(h.runtime.adapter.version_in_effect(MEM, _at(h, v3), _context("project:other")))
        sel = h.select(Q, as_of_target=AsOfTarget(MEM, _at(h, v3)), project="project:other")
        self.assertEqual((sel.target_resolution, sel.served_refs), ("unresolved", ()))


if __name__ == "__main__":
    unittest.main()
