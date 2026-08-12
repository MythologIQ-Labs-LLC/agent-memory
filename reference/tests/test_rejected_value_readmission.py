"""Characterization evidence for #147: fresh-identity rejected-value re-admission.

This first-stage test intentionally proves the *current* reference behavior before
we change it. It is not a conformance assertion and must be inverted by the
implementation commit that closes the reproduced gap.

The test isolates re-admission from #142's correction implementation work by
explicitly invalidating the original substrate fact, thereby granting the
stronger assumption that supersession already happened correctly. It then asks
whether the same rejected value can enter as a fresh fact and become admissible.

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


class RejectedValueReadmissionCharacterization(unittest.TestCase):
    """Prove the pre-fix failure without relying on Agent Memory Atlas claims."""

    def test_fresh_identity_can_reintroduce_a_superseded_value(self):
        substrate = InMemoryTemporalGraph()
        adapter = GovernedMemoryAdapter(substrate, TENANT, Clock())

        original = adapter.commit_proposal(proposal("prop-original"), VALUE_A)
        self.assertTrue(original.committed)
        self.assertIsNotNone(original.fact_uuid)

        # Isolate the #147 question from #142. Assume correction-as-supersession
        # has already worked and the old fact is no longer current.
        substrate.invalidate_fact(
            original.fact_uuid,
            invalid_at="2026-01-01T00:10:00Z",
            expired_at="2026-01-01T00:10:00Z",
        )
        adapter.record_correction(MEMORY)

        replacement = adapter.commit_proposal(
            proposal("prop-correction", operation="correction", evidence_refs=("ev:correction",), approved=True),
            VALUE_B,
        )
        self.assertTrue(replacement.committed)

        # A later extraction uses a fresh proposal/fact identity and repeats the
        # value that was just superseded. The current adapter has no write-path
        # rejection history to consult.
        reintroduced = adapter.commit_proposal(
            proposal("prop-reintroduced", evidence_refs=("ev:later-extraction",)),
            VALUE_A,
        )
        self.assertTrue(
            reintroduced.committed,
            "characterization failed: the current adapter unexpectedly blocked re-admission",
        )

        recall = adapter.governed_recall("deploy window Thursday")

        # Supersession protects the old row on the read path...
        self.assertIn(original.fact_uuid, recall.candidates)
        self.assertEqual(recall.refusals.get(original.fact_uuid), "superseded_not_current")

        # ...but a fresh row carrying the same rejected value is admitted.
        self.assertIn(reintroduced.fact_uuid, recall.candidates)
        self.assertIn(
            reintroduced.fact_uuid,
            recall.admitted,
            "characterization failed: fresh rejected value did not become current/admissible",
        )


if __name__ == "__main__":
    unittest.main()
