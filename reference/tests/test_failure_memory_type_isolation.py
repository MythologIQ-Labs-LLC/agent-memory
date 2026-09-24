from __future__ import annotations

import json
import unittest
from pathlib import Path

from agentmem_ref import policy
from tests.test_failure_memory import (
    FAILURE_REF,
    PROJECT,
    TENANT,
    context,
    revision,
    runtime,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT
    / "reference"
    / "fixtures"
    / "benchmarks"
    / "failure-memory-type-isolation-adversarial-v1.json"
)


class FailureMemoryTypeIsolationTests(unittest.TestCase):
    def test_unrelated_admitted_fact_fails_closed_at_failure_memory_surface(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        query = fixture["scenarios"][0]["query"]
        expected = fixture["scenarios"][0]["expected_failure_memory_outcome"]

        memory, adapter, _ = runtime("FailureReference")
        first = revision("failure-rev:001")
        failure_result = memory.apply_revision(
            first,
            actor_id="agent:failure-test",
        )
        self.assertTrue(failure_result.commit.committed)

        foreign_proposal = policy.Proposal(
            proposal_id="proposal:semantic-shared-readiness-note",
            actor_id="agent:failure-test",
            charter_version="failure-type-isolation-test-v1",
            target_reference="semantic:shared-readiness-note",
            target_class=policy.M2,
            scope=TENANT,
            operation="promotion",
            current_strength="observed",
            proposed_strength="promoted",
            downstream_authority=policy.A1,
            reversibility="reversible",
            risk_class="low",
            evidence_refs=("evidence:semantic-shared-readiness-note",),
            purpose="failure_recurrence_prevention",
            isolation_domain_refs=(TENANT, PROJECT),
            required_isolation_domain_refs=(TENANT, PROJECT),
            project_ref=PROJECT,
        )
        foreign = adapter.commit_proposal(
            foreign_proposal,
            "Deployment readiness timeout note from an unrelated semantic memory form",
        )
        self.assertTrue(foreign.committed)
        self.assertIsNotNone(foreign.fact_uuid)

        active = memory.recall_active(query, context=context())

        self.assertIn(failure_result.fact_uuid, active.admitted_fact_uuids)
        self.assertIn(foreign.fact_uuid, active.admitted_fact_uuids)
        self.assertIn(FAILURE_REF, active.active_object_refs)
        self.assertNotIn(foreign.fact_uuid, active.active_object_refs)
        self.assertNotIn("semantic:shared-readiness-note", active.active_object_refs)
        self.assertEqual(
            f"memory_type_mismatch:negative_failure_memory",
            active.refusals[foreign.fact_uuid],
        )
        self.assertEqual("memory_type_mismatch", expected)

    def test_current_failure_revision_remains_active_after_correction(self) -> None:
        memory, _, _ = runtime("FailureReference")
        first = revision("failure-rev:001")
        first_result = memory.apply_revision(first, actor_id="agent:failure-test")
        self.assertTrue(first_result.commit.committed)

        from tests.test_failure_memory import _failure_evidence

        second = memory.record_recurrence(
            FAILURE_REF,
            revision_ref="failure-rev:002",
            recurrence_evidence_ref="evidence:type-isolation-recurrence",
            observed_at="2026-01-02T00:00:00Z",
            actor_id="agent:failure-test",
            similarity_score=0.99,
            review_satisfied=True,
            approval_refs=("approval:type-isolation-review",),
            evidence=_failure_evidence(),
        )
        self.assertTrue(second.commit.committed)

        active = memory.recall_active(
            "deployment readiness timeout",
            context=context(),
        )

        self.assertIn(FAILURE_REF, active.active_object_refs)
        self.assertNotIn(first_result.fact_uuid, active.active_object_refs)
        self.assertEqual(
            "superseded",
            memory.revision_state(FAILURE_REF, first.revision_ref),
        )
        self.assertEqual(
            "current",
            memory.revision_state(FAILURE_REF, second.revision.revision_ref),
        )


if __name__ == "__main__":
    unittest.main()
