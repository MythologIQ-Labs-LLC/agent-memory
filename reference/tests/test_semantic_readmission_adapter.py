"""End-to-end governed semantic re-admission profile tests for #147."""

from __future__ import annotations

import unittest

from tests.qualified_fixtures import attestation_for, corpus_for, registry_for, rule

from agentmem_ref import policy
from agentmem_ref.adapter import Clock
from agentmem_ref.readmission import SemanticSimilaritySignal
from agentmem_ref.semantic_readmission_adapter import SemanticReadmissionAdapter
from agentmem_ref.substrate import InMemoryTemporalGraph

TENANT = "tenant-a"
MEMORY_ID = "mem:deploy-window"
VALUE_A = "deploy window is Thursday"
VALUE_B = "deploy window is Friday"
PARAPHRASE_A = "Thursday is the deployment window"


def _proposal(
    proposal_id: str,
    *,
    operation: str = "promotion",
    state_snapshot: str = "",
    actor_authority_resolved: bool = True,
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:planner",
        charter_version="charter:semantic-readmission",
        target_reference=MEMORY_ID,
        target_class=policy.M2,
        scope=TENANT,
        operation=operation,
        current_strength="reinforced" if operation != "correction" else "promoted",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=(f"evidence:{proposal_id}",),
        actor_authority_resolved=actor_authority_resolved,
        state_snapshot=state_snapshot,
        tenant_ref=TENANT,
        purpose="semantic-readmission-test",
    )


def _semantic_signal(adapter: SemanticReadmissionAdapter, *, candidate_match: bool = True) -> SemanticSimilaritySignal:
    active = adapter.active_rejection_records(MEMORY_ID)
    if not active:
        raise AssertionError("semantic test requires an active rejection record")
    return SemanticSimilaritySignal(
        memory_id=MEMORY_ID,
        rejection_ref=active[0]["rejection_id"],
        estimator_id="semantic-paraphrase-test",
        estimator_version="1.0.0",
        candidate_match=candidate_match,
        confidence=0.93 if candidate_match else 0.08,
        evidence_refs=("evidence:semantic-comparison",),
    )


def _correction_corpus():
    """The evaluator's adjudication: from VALUE_A this memory may become VALUE_B."""
    return corpus_for(
        rule(rule_id="rule:semantic-correction", target=MEMORY_ID,
             criterion="value-correction", from_state=VALUE_A, to_values=(VALUE_B,)),
        # An adjudicated reversal, authored ahead of the proposal that will cite
        # it. The evaluator decided in advance that a paraphrase of the original
        # is a permitted reversal target; the caller cannot add this.
        rule(rule_id="rule:semantic-reversal", target=MEMORY_ID,
             criterion="value-reversal", from_state=VALUE_B,
             to_values=(PARAPHRASE_A,)),
        rule(rule_id="rule:semantic-deletion", target=MEMORY_ID,
             criterion="lifecycle-deletion", from_state=VALUE_B,
             to_values=("deleted",)),
    )


class SemanticReadmissionAdapterTests(unittest.TestCase):
    def _corrected_adapter(self) -> tuple[SemanticReadmissionAdapter, str]:
        # The correction uses evaluator-held evidence only. Legacy caller-set
        # approval fields are deliberately absent; the scenario under test is
        # semantic readmission, not the pre-ADR-037 assertion path.
        corpus = _correction_corpus()
        adapter = SemanticReadmissionAdapter(
            InMemoryTemporalGraph(), tenant=TENANT, clock=Clock(),
            verifier_registry=registry_for(corpus),
        )
        first = adapter.commit_proposal(_proposal("original"), VALUE_A)
        self.assertTrue(first.committed)

        correction = adapter.commit_proposal(
            _proposal(
                "correction",
                operation="correction",
                state_snapshot="v1",
            ),
            VALUE_B,
            evidence=corpus.evidence_for(
                target_reference=MEMORY_ID, criterion="value-correction",
                pre_state=VALUE_A, proposed_value=VALUE_B,
            ),
        )
        self.assertTrue(correction.committed)
        return adapter, correction.fact_uuid

    def _reversal(self, proposal_id: str = "approved-semantic-reversal") -> policy.Proposal:
        return _proposal(
            proposal_id,
            operation="correction",
            state_snapshot="v2",
        )

    def _reversal_evidence(self):
        return _correction_corpus().evidence_for(
            target_reference=MEMORY_ID, criterion="value-reversal",
            pre_state=VALUE_B, proposed_value=PARAPHRASE_A,
        )

    def test_exact_reentry_remains_deterministically_blocked(self):
        adapter, _ = self._corrected_adapter()

        result = adapter.commit_with_semantic_signal(
            _proposal("exact-reentry", state_snapshot="v2"),
            VALUE_A,
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "rejected_value_requires_reconciliation")
        self.assertIsNotNone(result.downstream)

    def test_semantic_paraphrase_match_routes_to_reconciliation_before_pama_commit(self):
        adapter, _ = self._corrected_adapter()
        signal = _semantic_signal(adapter, candidate_match=True)
        before_state = adapter.state_version(MEMORY_ID)

        result = adapter.commit_with_semantic_signal(
            _proposal("semantic-reentry", state_snapshot="v2"),
            PARAPHRASE_A,
            semantic_signal=signal,
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "semantic_reconciliation_required")
        self.assertIsNone(result.downstream)
        self.assertTrue(result.routing.review_required)
        self.assertEqual(adapter.state_version(MEMORY_ID), before_state)
        self.assertEqual(result.events[-1]["event_type"], "memory.semantic_readmission_review_required")
        self.assertEqual(
            result.events[0]["signal"]["signal_semantics"],
            "candidate_match_for_reconciliation_not_authority",
        )
        self.assertFalse(result.events[-1]["payload"]["reversal_attestation_present"])

    def test_semantic_nonmatch_does_not_authorize_pama_blocked_mutation(self):
        adapter, _ = self._corrected_adapter()
        signal = _semantic_signal(adapter, candidate_match=False)

        result = adapter.commit_with_semantic_signal(
            _proposal(
                "blocked-nonmatch",
                state_snapshot="v2",
                actor_authority_resolved=False,
            ),
            "unrelated candidate",
            semantic_signal=signal,
        )

        self.assertFalse(result.committed)
        self.assertIsNotNone(result.downstream)
        self.assertEqual(result.downstream.decision.outcome, policy.BLOCK)
        self.assertFalse(result.routing.review_required)

    def test_invalid_semantic_rejection_reference_fails_closed_without_pama_mutation(self):
        adapter, _ = self._corrected_adapter()
        signal = SemanticSimilaritySignal(
            memory_id=MEMORY_ID,
            rejection_ref="rejection:sha256:not-active",
            estimator_id="semantic-paraphrase-test",
            estimator_version="1.0.0",
            candidate_match=False,
        )
        before_state = adapter.state_version(MEMORY_ID)

        result = adapter.commit_with_semantic_signal(
            _proposal("invalid-signal", state_snapshot="v2"),
            "unrelated candidate",
            semantic_signal=signal,
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "semantic_reconciliation_signal_invalid")
        self.assertIsNone(result.downstream)
        self.assertEqual(adapter.state_version(MEMORY_ID), before_state)

    def test_qualified_evidence_without_reversal_attestation_stays_in_reconciliation(self):
        adapter, _ = self._corrected_adapter()
        signal = _semantic_signal(adapter, candidate_match=True)
        reversal_proposal = self._reversal("evidence-only-semantic-reversal")

        result = adapter.commit_with_semantic_signal(
            reversal_proposal,
            PARAPHRASE_A,
            semantic_signal=signal,
            evidence=self._reversal_evidence(),
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "semantic_reconciliation_required")
        self.assertIsNone(result.downstream)
        self.assertEqual(adapter.state_version(MEMORY_ID), 2)

    def test_wrong_proposal_attestation_does_not_bypass_semantic_reconciliation(self):
        adapter, _ = self._corrected_adapter()
        signal = _semantic_signal(adapter, candidate_match=True)
        reversal_proposal = self._reversal("wrong-binding-semantic-reversal")
        wrong_attestation = attestation_for(self._reversal("other-semantic-reversal"))

        result = adapter.commit_with_semantic_signal(
            reversal_proposal,
            PARAPHRASE_A,
            semantic_signal=signal,
            evidence=self._reversal_evidence(),
            attestation=wrong_attestation,
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "semantic_reconciliation_required")
        self.assertEqual(
            result.events[-1]["payload"]["reversal_attestation_refusal"],
            "attestation_not_bound_to_proposal",
        )

    def test_externally_approved_semantic_reversal_still_passes_through_pama(self):
        adapter, _ = self._corrected_adapter()
        signal = _semantic_signal(adapter, candidate_match=True)
        reversal_proposal = self._reversal()
        self.assertFalse(reversal_proposal.review_satisfied)
        self.assertEqual(reversal_proposal.approval_refs, ())
        attestation = attestation_for(reversal_proposal)

        result = adapter.commit_with_semantic_signal(
            reversal_proposal,
            PARAPHRASE_A,
            semantic_signal=signal,
            evidence=self._reversal_evidence(),
            attestation=attestation,
        )

        self.assertTrue(result.committed)
        self.assertIsNotNone(result.downstream)
        self.assertTrue(result.downstream.committed)
        self.assertEqual(result.downstream.decision.outcome, policy.ALLOW_WITH_LEDGER)
        self.assertTrue(result.routing.review_required)
        self.assertEqual(adapter.state_version(MEMORY_ID), 3)
        self.assertTrue(result.events[0]["payload"]["reversal_attestation_valid"])

    def test_correction_rejection_record_does_not_infer_legacy_authority(self):
        adapter, _ = self._corrected_adapter()
        records = adapter.active_rejection_records(MEMORY_ID)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["authority_refs"], [])
        self.assertEqual(records[0]["scope"], TENANT)
        self.assertEqual(records[0]["lifecycle_state"], "rejected")
        self.assertNotIn("value", records[0])

    def test_permanent_deletion_purges_rejection_fingerprints_after_commit(self):
        adapter, current_fact_uuid = self._corrected_adapter()
        self.assertEqual(len(adapter.active_rejection_records(MEMORY_ID)), 1)

        deletion = adapter.governed_delete(
            _proposal(
                "permanent-delete",
                operation="permanent_deletion",
                state_snapshot="v2",
            ),
            current_fact_uuid,
            evidence=_correction_corpus().evidence_for(
                target_reference=MEMORY_ID, criterion="lifecycle-deletion",
                pre_state=VALUE_B, proposed_value="deleted",
            ),
        )

        self.assertTrue(deletion.committed)
        self.assertEqual(adapter.active_rejection_records(MEMORY_ID), ())
        self.assertEqual(deletion.events[-1]["event_type"], "memory.rejection_history_purged")
        self.assertEqual(deletion.events[-1]["payload"]["purged_rejection_records"], 1)


if __name__ == "__main__":
    unittest.main()
