"""#774/#776 integration contract: same memory ID does not mean same lineage.

Tests are preregistered BEFORE a combined runtime implementation. They are
expected to expose the legacy #774 memory-id-wide deletion guard and the
lack of the #776 logical-lineage reader protection on this test-only branch.

No benchmark-specific query heuristics or production merges.
"""
from __future__ import annotations

import unittest

from tests.test_774_governed_predecessor import _History, KILN, S
from tests.test_runtime_composition import _context


class RecreatedMemoryLineageIntegration(unittest.TestCase):
    def test_new_generation_visible_after_prior_lineage_pruned(self):
        h = _History(self, {"kiln": KILN})
        old_refs = tuple(h.ids["kiln"])
        h.delete("kiln")

        newest = h.runtime.retain(
            h._proposal("kiln", 42),
            "The replacement kiln firing schedule uses cone 4 glaze.",
        )
        self.assertTrue(newest.committed, newest)
        self.assertIsNotNone(newest.fact_uuid)
        visible = h.recall("replacement kiln firing schedule", "current")
        self.assertIn(newest.fact_uuid, visible.admitted)

        # #776: deleted OLD lineage stays denied even after an ID is reused.
        history = h.recall("kiln firing schedule", "historical")
        self.assertFalse(set(old_refs).intersection(history.admitted))
        self.assertFalse(h.runtime.adapter.memory_deleted(newest.fact_uuid))
        self.assertEqual(
            h.runtime.adapter.lineage_head(newest.fact_uuid, _context()),
            newest.fact_uuid,
        )

    def test_new_generation_cannot_inherit_predecessor_of_deleted_generation(self):
        h = _History(self, {"kiln": KILN})
        old_refs = tuple(h.ids["kiln"])
        h.delete("kiln")
        new = h.runtime.retain(
            h._proposal("kiln", 43),
            "Replacement kiln inspection uses a digital checklist.",
        )
        self.assertTrue(new.committed, new)
        selected = h.select(
            "What preceded this replacement kiln inspection checklist?",
            successor_ref=new.fact_uuid, budget=5,
        )
        self.assertIsNone(selected.predecessor_ref)
        self.assertFalse(set(old_refs).intersection(selected.served_refs))
        self.assertEqual(selected.authority_effect, "none")
        self.assertFalse(selected.complete_evidence_attested)

    def test_deleting_superseded_version_preserves_current_predecessor_target(self):
        h = _History(self, {"kiln": KILN})
        predecessor, current = h.ids["kiln"]
        # Independent #776 reviewers demonstrated a superseded-version
        # tombstone must not suppress the still-live current lineage.
        proposal = h._proposal("kiln", 44, op="pruning")
        from dataclasses import replace
        from agentmem_ref import policy
        proposal = replace(
            proposal, target_class=policy.M1, proposed_strength="tentative",
            review_satisfied=True, approval_refs=("approval:774-776",),
        )
        deleted = h.runtime.adapter.governed_delete(proposal, predecessor)
        self.assertTrue(deleted.committed, deleted)
        result = h.recall("kiln firing schedule", "current")
        self.assertIn(current, result.admitted)
        self.assertFalse(h.runtime.adapter.memory_deleted(current))
        self.assertEqual(
            h.runtime.adapter.lineage_head(current, _context()), current
        )

    def test_other_memory_history_unaffected_by_reused_deleted_identity(self):
        h = _History(self, {"kiln": KILN, "tram": [
            ("Route 9 maintenance inspections use paper forms.", None),
            ("Route 9 maintenance inspections use tablet forms.", S),
        ]})
        h.delete("kiln")
        new = h.runtime.retain(
            h._proposal("kiln", 45),
            "The replacement kiln now uses a tablet inspection log.",
        )
        self.assertTrue(new.committed, new)
        tram_prior, tram_current = h.ids["tram"]
        selected = h.select("What did Route 9 use before tablet forms?",
                            successor_ref=tram_current, budget=5)
        self.assertEqual(selected.predecessor_ref, tram_prior)
        self.assertEqual(selected.served_refs[0], tram_prior)


if __name__ == "__main__":
    unittest.main()
