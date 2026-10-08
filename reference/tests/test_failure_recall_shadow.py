"""#690: real governed failure-memory recall in read-only shadow mode.

This tests product safety invariants, NOT a benchmark-specific phrase grammar,
ranking improvement, facade integration, or accepted Runtime Baseline successor.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest import TestCase
from unittest.mock import patch

from agentmem_ref.evaluation.failure_recall_shadow import inspect_failure_recall
from agentmem_ref.memory.cognitive_mesh import ActiveCognition
from tests.test_failure_memory import (
    FAILURE_REF, PROJECT, _failure_evidence, context, revision, runtime,
)


class FailureRecallShadowTests(TestCase):
    def setUp(self):
        self.memory, self.adapter, self.substrate = runtime("FailureReference")
        self.initial = revision("failure-rev:001")
        self.write = self.memory.apply_revision(
            self.initial, actor_id="agent:failure-test"
        )
        self.assertTrue(self.write.commit.committed)

    def inspect(self, query="deployment readiness timeout", *, project_ref=PROJECT):
        return inspect_failure_recall(
            self.memory, query, context=context(project_ref=project_ref)
        )

    def test_real_admission_yields_non_authoritative_failure_evidence(self):
        evidence = self.inspect()
        self.assertIn(self.write.fact_uuid, evidence.generic_admitted_fact_uuids)
        self.assertEqual(len(evidence.usable_failures), 1)
        item = evidence.usable_failures[0]
        self.assertEqual(item.failure_ref, FAILURE_REF)
        self.assertEqual(item.fact_uuid, self.write.fact_uuid)
        self.assertEqual(item.revision_ref, self.initial.revision_ref)
        self.assertEqual(item.memory_status, "active")
        self.assertEqual(item.occurrence_count, 1)
        self.assertEqual(item.authority_effect, "none")
        self.assertEqual(evidence.authority_effect, "none")
        self.assertFalse(evidence.mutates_memory)
        self.assertEqual(evidence.integration_state, "evaluation_only")

    def test_shadow_recall_is_read_only_and_cannot_invent_recurrence(self):
        old_writes = tuple(self.substrate.write_log)
        old_events = tuple(self.adapter.events)
        old_history = self.memory.history(FAILURE_REF)
        for _ in range(3):
            self.inspect()
        self.assertEqual(old_writes, tuple(self.substrate.write_log))
        self.assertEqual(old_events, tuple(self.adapter.events))
        self.assertEqual(old_history, self.memory.history(FAILURE_REF))
        self.assertEqual(1, self.memory.occurrence_count(FAILURE_REF))

    def test_scope_mismatch_does_not_expose_usable_failure(self):
        evidence = self.inspect(project_ref="project:unrelated")
        self.assertEqual(evidence.usable_failures, ())
        self.assertEqual(evidence.authority_effect, "none")

    def test_disputed_memory_does_not_become_usable_guidance(self):
        proposal = revision(
            "failure-rev:002",
            summary="Deployment failure cause is disputed",
            causal_status="hypothesis",
            prior_revision_ref="failure-rev:001",
            revision_reason="contradictory evidence",
            memory_status="disputed",
        )
        result = self.memory.apply_revision(
            proposal,
            actor_id="agent:failure-test",
            review_satisfied=True,
            approval_refs=("approval:failure-review",),
            evidence=_failure_evidence(),
        )
        self.assertTrue(result.commit.committed)
        evidence = self.inspect("deployment failure cause")
        self.assertEqual(evidence.usable_failures, ())
        self.assertIn("failure_disputed", dict(evidence.rejected_fact_reasons).values())

    def test_retracted_failure_stays_unusable(self):
        proposed = revision(
            "failure-rev:002",
            summary="",
            impact_score=None,
            similarity_score=None,
            source_evidence=("evidence:withdrawal",),
            verification=(),
            prior_revision_ref="failure-rev:001",
            revision_reason="source withdrawn",
            memory_status="retracted",
            mitigation="",
        )
        outcome = self.memory.apply_revision(
            proposed, actor_id="agent:failure-test"
        )
        self.assertTrue(outcome.commit.committed)
        self.assertEqual(self.inspect().usable_failures, ())

    def test_generic_admission_cannot_promote_unknown_memory_kind(self):
        unknown_fact = "fact:outside-specialized-failure-owner"
        active = ActiveCognition(
            candidate_fact_uuids=[self.write.fact_uuid, unknown_fact],
            admitted_fact_uuids=[self.write.fact_uuid, unknown_fact],
            active_object_refs=[FAILURE_REF],
            refusals={unknown_fact: "memory_type_mismatch:negative_failure_memory"},
            contextual_decisions={},
        )
        with patch.object(self.memory, "recall_active", return_value=active):
            result = self.inspect()
        self.assertIn(unknown_fact, result.generic_admitted_fact_uuids)
        self.assertEqual(tuple(x.failure_ref for x in result.usable_failures), (FAILURE_REF,))
        self.assertEqual(
            dict(result.rejected_fact_reasons)[unknown_fact],
            "memory_type_mismatch:negative_failure_memory",
        )

    def test_current_owner_fact_must_be_generically_admitted(self):
        active = ActiveCognition(
            candidate_fact_uuids=[self.write.fact_uuid],
            admitted_fact_uuids=[],
            active_object_refs=[FAILURE_REF],
            refusals={self.write.fact_uuid: "scope_mismatch"},
            contextual_decisions={},
        )
        with patch.object(self.memory, "recall_active", return_value=active):
            result = self.inspect()
        self.assertEqual(result.usable_failures, ())
        self.assertEqual(result.generic_admitted_fact_uuids, ())

    def test_severity_and_recurrence_never_create_action_authority(self):
        for _ in range(2):
            item = self.inspect().usable_failures[0]
            self.assertEqual(item.severity_label, "critical")
            self.assertEqual(item.authority_effect, "none")
        with self.assertRaises(FrozenInstanceError):
            item.authority_effect = "block"

    def test_rejects_invalid_query_and_context_before_recall(self):
        with self.assertRaises(ValueError):
            inspect_failure_recall(self.memory, "", context=context())
        with self.assertRaises(TypeError):
            inspect_failure_recall(self.memory, "failure", context={})
        with self.assertRaises(TypeError):
            inspect_failure_recall(object(), "failure", context=context())

    def test_result_does_not_downgrade_missing_evidence_to_a_block(self):
        with patch.object(
            self.memory,
            "recall_active",
            return_value=ActiveCognition(
                candidate_fact_uuids=[], admitted_fact_uuids=[],
                active_object_refs=[], refusals={}, contextual_decisions={},
            ),
        ):
            evidence = self.inspect("previously unseen action")
        self.assertEqual(evidence.usable_failures, ())
        self.assertEqual(evidence.authority_effect, "none")


if __name__ == "__main__":
    import unittest
    unittest.main()
