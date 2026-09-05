"""Regression evidence for #147: governed exact-value re-admission.

Commit 0e1eca3 first preserved the pre-fix characterization: after a value was
superseded, the same value could return under a fresh fact identity and become
admissible. The Validate Doctrine Evidence workflow executed that test through
full unittest discovery before the implementation change.

These tests invert that characterization. They cover only deterministic exact
identity after case/whitespace normalization. They do not claim semantic
paraphrase equivalence or architecture-independent conformance.

Run: python -m unittest reference.tests.test_rejected_value_readmission
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import policy  # noqa: E402
from agentmem_ref.adapter import Clock, GovernedMemoryAdapter  # noqa: E402
from agentmem_ref.substrate import InMemoryTemporalGraph  # noqa: E402

TENANT = "tenant-a"
MEMORY = "mem:deploy-window"
VALUE_A = "deploy window is Thursday"
VALUE_B = "deploy window is Friday"


def proposal(
    proposal_id: str,
    *,
    operation: str = "promotion",
    evidence_refs: tuple[str, ...] = ("ev:source-a",),
    approved: bool = False,
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:planner",
        charter_version="charter-1",
        target_reference=MEMORY,
        target_class=policy.M2,
        scope=TENANT,
        operation=operation,
        current_strength="reinforced",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=evidence_refs,
        tenant_ref=TENANT,
        approval_refs=("approval:owner",) if approved else (),
        review_satisfied=approved,
    )


class RejectedValueReadmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.substrate = InMemoryTemporalGraph()
        self.adapter = GovernedMemoryAdapter(self.substrate, TENANT, Clock())

        self.original = self.adapter.commit_proposal(proposal("prop-original"), VALUE_A)
        self.assertTrue(self.original.committed)

        self.replacement = self.adapter.commit_proposal(
            proposal("prop-correction", operation="correction", evidence_refs=("ev:correction",), approved=True),
            VALUE_B,
        )
        self.assertTrue(self.replacement.committed)

    def test_correction_supersedes_old_row_and_records_rejection_history(self):
        recall = self.adapter.governed_recall("deploy window Thursday")

        self.assertIn(self.original.fact_uuid, recall.candidates)
        self.assertEqual(recall.refusals.get(self.original.fact_uuid), "superseded_not_current")

        history = self.adapter.rejected_value_history(MEMORY, VALUE_A)
        self.assertEqual(len(history), 1)
        self.assertTrue(history[0]["active"])
        self.assertEqual(history[0]["superseded_fact_uuid"], self.original.fact_uuid)
        self.assertEqual(history[0]["correction_proposal_id"], "prop-correction")
        self.assertNotIn("fact_text", history[0], "rejection history must not duplicate raw memory content")

    def test_fresh_identity_cannot_silently_reintroduce_rejected_value(self):
        reintroduced = self.adapter.commit_proposal(
            proposal("prop-reintroduced", evidence_refs=("ev:later-extraction",)),
            VALUE_A,
        )

        self.assertFalse(reintroduced.committed)
        self.assertIsNone(reintroduced.fact_uuid)
        self.assertEqual(reintroduced.refusal, "rejected_value_requires_reconciliation")
        self.assertEqual(reintroduced.receipt["selected_action"], "defer")
        self.assertTrue(any(event["event_type"] == "memory.readmission_blocked" for event in reintroduced.events))

        recall = self.adapter.governed_recall("deploy window Thursday")
        self.assertEqual(recall.refusals.get(self.original.fact_uuid), "superseded_not_current")
        self.assertNotIn(None, recall.admitted)

    def test_deterministic_normalization_does_not_bypass_rejection(self):
        variant = "  Deploy   Window is THURSDAY  "
        result = self.adapter.commit_proposal(
            proposal("prop-normalized-variant", evidence_refs=("ev:later-extraction",)),
            variant,
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "rejected_value_requires_reconciliation")

    def test_explicit_approved_correction_can_reverse_prior_rejection(self):
        reversal = self.adapter.commit_proposal(
            proposal(
                "prop-approved-reversal",
                operation="correction",
                evidence_refs=("ev:new-independent-evidence",),
                approved=True,
            ),
            VALUE_A,
        )

        self.assertTrue(reversal.committed)
        self.assertEqual(self.adapter.current_fact_uuid(MEMORY), reversal.fact_uuid)

        old_history = self.adapter.rejected_value_history(MEMORY, VALUE_A)
        self.assertEqual(len(old_history), 1)
        self.assertFalse(old_history[0]["active"])
        self.assertEqual(old_history[0]["readmission_proposal_id"], "prop-approved-reversal")
        self.assertIsNotNone(old_history[0]["readmitted_at"])

        replaced_history = self.adapter.rejected_value_history(MEMORY, VALUE_B)
        self.assertEqual(len(replaced_history), 1)
        self.assertTrue(replaced_history[0]["active"])
        self.assertEqual(replaced_history[0]["superseded_fact_uuid"], self.replacement.fact_uuid)

        recall = self.adapter.governed_recall("deploy window Thursday")
        self.assertIn(reversal.fact_uuid, recall.admitted)
        self.assertEqual(recall.refusals.get(self.original.fact_uuid), "superseded_not_current")
        self.assertEqual(recall.refusals.get(self.replacement.fact_uuid), "superseded_not_current")


if __name__ == "__main__":
    unittest.main()
