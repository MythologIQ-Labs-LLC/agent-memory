from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema

from tests.qualified_fixtures import corpus_for, registry_for, rule

from agentmem_ref import policy
from agentmem_ref.adapter import Clock, GovernedMemoryAdapter, RecallContext
from agentmem_ref.capabilities import ComponentDeclaration
from agentmem_ref.failure_memory import (
    CAPABILITY_ID,
    FailureMemory,
    FailureMemoryError,
    FailureRevision,
    FailureScope,
    StaleFailureRevision,
    derive_failure_ref,
)
from agentmem_ref.substrate import InMemoryTemporalGraph


ROOT = Path(__file__).resolve().parents[2]
PROFILE = (
    ROOT
    / "reference"
    / "fixtures"
    / "component-capabilities"
    / "failure-memory-reference-v3.json"
)
SCHEMA = ROOT / "schemas" / "component-capability-profile.schema.json"

TENANT = "tenant:failure-memory"
PROJECT = "project:failure-memory"
FAILURE_REF = "failure:deployment-timeout"


def _failure_corpus():
    return corpus_for(
        rule(
            rule_id="rule:failure-revision",
            target=FAILURE_REF,
            criterion="failure-revision",
            from_state="current",
            to_values=("revised", "disputed", "retracted"),
        ),
    )


def _failure_evidence():
    return _failure_corpus().evidence_for(
        target_reference=FAILURE_REF,
        criterion="failure-revision",
        pre_state="current",
        proposed_value="revised",
    )


def governed_scope() -> FailureScope:
    return FailureScope(
        scope=TENANT,
        isolation_domain_refs=(TENANT, PROJECT),
        required_isolation_domain_refs=(TENANT, PROJECT),
        project_ref=PROJECT,
    )


def context(project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:failure-test",
        project_ref=project_ref,
        purpose="failure_recurrence_prevention",
    )


def revision(
    revision_ref: str,
    *,
    failure_ref: str = FAILURE_REF,
    summary: str = "Deployment timed out while waiting for service readiness",
    category: str = "readiness_timeout",
    causal_status: str = "observed",
    source_component: str = "FailureReference",
    severity_label: str = "critical",
    impact_score: float | None = 0.95,
    similarity_score: float | None = None,
    source_evidence: tuple[str, ...] = ("evidence:deploy-log",),
    verification: tuple[str, ...] = ("evidence:timeout-confirmed",),
    recurrence: tuple[str, ...] = (),
    prior_revision_ref: str = "",
    revision_reason: str = "",
    memory_status: str = "active",
    scope: FailureScope | None = None,
    mitigation: str = "Check readiness dependency before deployment",
) -> FailureRevision:
    return FailureRevision(
        failure_ref=failure_ref,
        revision_ref=revision_ref,
        action_class="deploy_service",
        summary=summary,
        category=category,
        causal_status=causal_status,
        scope=scope or governed_scope(),
        source_component=source_component,
        observed_at="2026-01-01T00:00:00Z",
        expected_outcome="service becomes ready",
        actual_outcome="readiness deadline exceeded",
        severity_label=severity_label,
        impact_score=impact_score,
        root_cause_candidates=("dependency unavailable", "readiness probe mismatch"),
        mitigation=mitigation,
        verification_evidence_refs=verification,
        applicability_conditions=("same deployment path",),
        source_evidence_refs=source_evidence,
        recurrence_evidence_refs=recurrence,
        similarity_score=similarity_score,
        prior_revision_ref=prior_revision_ref,
        revision_reason=revision_reason,
        memory_status=memory_status,
        estimator_ref="estimator:failure-similarity",
        estimator_version="1.0.0",
    )


def runtime(*components: str) -> tuple[
    FailureMemory,
    GovernedMemoryAdapter,
    InMemoryTemporalGraph,
]:
    substrate = InMemoryTemporalGraph()
    corpus = _failure_corpus()
    adapter = GovernedMemoryAdapter(
        substrate,
        tenant=TENANT,
        clock=Clock(),
        verifier_registry=registry_for(corpus),
    )
    memory = FailureMemory(
        adapter=adapter,
        available_components=tuple(components),
    )
    return memory, adapter, substrate


class FailureMemoryTests(unittest.TestCase):
    def test_profile_is_honest_about_authority_and_process_local_restart(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        value = json.loads(PROFILE.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(value)
        component = ComponentDeclaration.from_dict(value)

        self.assertEqual("component-capability-v3", component.profile_version)
        capability = component.capabilities[0]
        self.assertEqual(CAPABILITY_ID, capability.capability_id)
        self.assertEqual("runtime_wired", capability.maturity)
        self.assertEqual("none", capability.authority_effect)
        self.assertEqual(
            "process_local_only",
            capability.operational_contract.restart_recovery,
        )

    def test_stable_failure_identity_is_deterministic_and_discriminating(self) -> None:
        kwargs = {
            "scope": TENANT,
            "action_class": "deploy_service",
            "category": "readiness_timeout",
            "identity_basis": "service-readiness-dependency",
        }
        first = derive_failure_ref(**kwargs)
        second = derive_failure_ref(**kwargs)
        different = derive_failure_ref(
            **{**kwargs, "identity_basis": "database-migration-lock"}
        )

        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertTrue(first.startswith("failure:sha256:"))

    def test_initial_failure_is_governed_and_recallable(self) -> None:
        memory, adapter, substrate = runtime("FailureReference")
        first = revision("failure-rev:001")

        result = memory.apply_revision(first, actor_id="agent:failure-test")

        self.assertTrue(result.commit.committed)
        self.assertEqual(policy.ALLOW_WITH_LEDGER, result.commit.decision.outcome)
        self.assertEqual("current", result.lineage_state)
        self.assertEqual(first, memory.current(FAILURE_REF))
        self.assertEqual(1, memory.occurrence_count(FAILURE_REF))
        self.assertEqual(result.fact_uuid, adapter.current_fact_uuid(FAILURE_REF))
        self.assertIn("Deployment timed out", substrate.get_fact(result.fact_uuid).fact_text)

        active = memory.recall_active("deployment readiness timeout", context=context())
        self.assertIn(FAILURE_REF, active.active_object_refs)

    def test_high_similarity_and_impact_cannot_bypass_correction_review(self) -> None:
        memory, adapter, _ = runtime("FailureReference")
        first = revision("failure-rev:001")
        committed = memory.apply_revision(first, actor_id="agent:failure-test")

        proposed = revision(
            "failure-rev:002",
            summary="Deployment failed again during the same readiness path",
            similarity_score=1.0,
            impact_score=1.0,
            prior_revision_ref=first.revision_ref,
            revision_reason="new recurrence observation",
            recurrence=("evidence:recurrence-2",),
        )
        refused = memory.apply_revision(proposed, actor_id="agent:failure-test")

        self.assertFalse(refused.commit.committed)
        self.assertEqual(policy.REQUIRE_REVIEW, refused.commit.decision.outcome)
        self.assertEqual(first, memory.current(FAILURE_REF))
        self.assertEqual(committed.fact_uuid, adapter.current_fact_uuid(FAILURE_REF))
        self.assertEqual(1, memory.occurrence_count(FAILURE_REF))

    def test_explicit_recurrence_deduplicates_under_same_logical_identity(self) -> None:
        memory, adapter, substrate = runtime("FailureReference")
        first = revision("failure-rev:001")
        first_result = memory.apply_revision(first, actor_id="agent:failure-test")

        second_result = memory.record_recurrence(
            FAILURE_REF,
            revision_ref="failure-rev:002",
            recurrence_evidence_ref="evidence:recurrence-2",
            observed_at="2026-01-02T00:00:00Z",
            actor_id="agent:failure-test",
            similarity_score=0.99,
            review_satisfied=True,
            approval_refs=("approval:failure-review",),
            evidence=_failure_evidence(),
        )

        self.assertTrue(second_result.commit.committed)
        self.assertEqual(FAILURE_REF, second_result.revision.failure_ref)
        self.assertEqual(2, memory.occurrence_count(FAILURE_REF))
        self.assertEqual(2, len(memory.history(FAILURE_REF)))
        self.assertEqual(
            "superseded",
            memory.revision_state(FAILURE_REF, first.revision_ref),
        )
        self.assertEqual(
            second_result.fact_uuid,
            adapter.current_fact_uuid(FAILURE_REF),
        )
        self.assertTrue(substrate.get_fact(first_result.fact_uuid).is_event_invalid)

    def test_recall_never_manufactures_recurrence_evidence(self) -> None:
        memory, _, _ = runtime("FailureReference")
        first = revision("failure-rev:001")
        memory.apply_revision(first, actor_id="agent:failure-test")
        before_history = memory.history(FAILURE_REF)
        before_count = memory.occurrence_count(FAILURE_REF)

        for _ in range(5):
            memory.recall_active("deployment readiness timeout", context=context())

        self.assertEqual(before_count, memory.occurrence_count(FAILURE_REF))
        self.assertEqual(before_history, memory.history(FAILURE_REF))

    def test_duplicate_recurrence_evidence_fails_before_mutation(self) -> None:
        memory, _, substrate = runtime("FailureReference")
        first = revision(
            "failure-rev:001",
            recurrence=("evidence:already-counted",),
        )
        memory.apply_revision(first, actor_id="agent:failure-test")
        before = tuple(substrate.write_log)

        with self.assertRaises(FailureMemoryError):
            memory.record_recurrence(
                FAILURE_REF,
                revision_ref="failure-rev:002",
                recurrence_evidence_ref="evidence:already-counted",
                observed_at="2026-01-02T00:00:00Z",
                actor_id="agent:failure-test",
            )

        self.assertEqual(before, tuple(substrate.write_log))
        self.assertEqual(2, memory.occurrence_count(FAILURE_REF))

    def test_match_evidence_is_never_action_authority(self) -> None:
        memory, _, _ = runtime("FailureReference")
        first = revision(
            "failure-rev:001",
            severity_label="critical",
            impact_score=1.0,
        )
        memory.apply_revision(first, actor_id="agent:failure-test")

        match = memory.match_evidence(FAILURE_REF, similarity_score=1.0)

        self.assertEqual("critical", match.severity_label)
        self.assertEqual(1.0, match.similarity_score)
        self.assertEqual("none", match.authority_effect)
        self.assertEqual(1, match.occurrence_count)

    def test_disputed_causal_memory_is_visible_but_not_active_guidance(self) -> None:
        memory, _, _ = runtime("FailureReference")
        first = revision("failure-rev:001")
        memory.apply_revision(first, actor_id="agent:failure-test")

        disputed = revision(
            "failure-rev:002",
            summary="The deployment timeout cause remains unresolved",
            causal_status="hypothesis",
            prior_revision_ref=first.revision_ref,
            revision_reason="conflicting root-cause evidence",
            memory_status="disputed",
        )
        result = memory.apply_revision(
            disputed,
            actor_id="agent:failure-test",
            review_satisfied=True,
            approval_refs=("approval:dispute-review",),
            evidence=_failure_evidence(),
        )

        self.assertTrue(result.commit.committed)
        self.assertEqual("disputed", result.lineage_state)
        active = memory.recall_active("deployment timeout cause", context=context())
        self.assertIn(result.fact_uuid, active.admitted_fact_uuids)
        self.assertNotIn(FAILURE_REF, active.active_object_refs)
        self.assertEqual("failure_disputed", active.refusals[result.fact_uuid])

    def test_retraction_tombstones_current_influence_but_preserves_history(self) -> None:
        memory, adapter, substrate = runtime("FailureReference")
        first = revision("failure-rev:001")
        first_result = memory.apply_revision(first, actor_id="agent:failure-test")

        retracted = revision(
            "failure-rev:002",
            summary="",
            impact_score=None,
            similarity_score=None,
            source_evidence=("evidence:withdrawal",),
            verification=(),
            prior_revision_ref=first.revision_ref,
            revision_reason="failure record was invalidated by source correction",
            memory_status="retracted",
            mitigation="",
        )
        result = memory.apply_revision(
            retracted,
            actor_id="agent:failure-test",
        )

        self.assertTrue(result.commit.committed)
        self.assertEqual("retracted", result.lineage_state)
        self.assertEqual(2, len(memory.history(FAILURE_REF)))
        self.assertIsNone(adapter.current_fact_uuid(FAILURE_REF))
        self.assertIsNotNone(substrate.get_fact(first_result.fact_uuid))
        self.assertIsNotNone(adapter.tombstone(first_result.fact_uuid))

        active = memory.recall_active("deployment readiness timeout", context=context())
        self.assertNotIn(FAILURE_REF, active.active_object_refs)
        self.assertEqual("tombstoned", active.refusals[first_result.fact_uuid])

    def test_stale_revision_and_scope_change_fail_before_substrate_mutation(self) -> None:
        memory, _, substrate = runtime("FailureReference")
        first = revision("failure-rev:001")
        memory.apply_revision(first, actor_id="agent:failure-test")
        before = tuple(substrate.write_log)

        stale = revision(
            "failure-rev:002",
            prior_revision_ref="failure-rev:000",
            revision_reason="stale writer",
        )
        with self.assertRaises(StaleFailureRevision):
            memory.apply_revision(stale, actor_id="agent:failure-test")
        self.assertEqual(before, tuple(substrate.write_log))

        foreign_scope = FailureScope(
            scope=TENANT,
            isolation_domain_refs=(TENANT, "project:other"),
            required_isolation_domain_refs=(TENANT, "project:other"),
            project_ref="project:other",
        )
        changed_scope = revision(
            "failure-rev:003",
            prior_revision_ref=first.revision_ref,
            revision_reason="attempted scope movement",
            scope=foreign_scope,
        )
        with self.assertRaises(FailureMemoryError):
            memory.apply_revision(changed_scope, actor_id="agent:failure-test")
        self.assertEqual(before, tuple(substrate.write_log))


if __name__ == "__main__":
    unittest.main()
