from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tests.qualified_fixtures import corpus_for, registry_for, rule

from agentmem_ref.failure_memory import FailureRevision, FailureScope
from agentmem_ref.memory.failure_checkpoint import (
    CheckpointedFailureMemory,
    FailureCheckpointError,
)
from agentmem_ref.adapter import RecallContext
from agentmem_ref.auxiliary_checkpoint import ComposedRestartSafeRuntime
from agentmem_ref.restart_runtime import CapabilityBinding, RuntimeProfile


TENANT = "tenant:failure-restart"
PROJECT = "project:failure-restart"
FAILURE_REF = "failure:restart-readiness-timeout"
COMPONENT = "FailureReference"
AUXILIARY_ID = "negative_failure_memory"


def profile() -> RuntimeProfile:
    binding = CapabilityBinding(
        component_id="reference-governed-memory",
        component_version="1.0.0",
        capability_id="governed-memory-core",
        capability_version="1.0.0",
        maturity="reference_qualified",
        evidence_ref="evidence:reference-runtime-core-v1",
    )
    return RuntimeProfile(
        runtime_version="0.1.0-failure-memory",
        profile_id="failure-memory-restart-reference",
        profile_version="1.0.0",
        bindings=(binding,),
    )


def failure_corpus():
    return corpus_for(
        rule(
            rule_id="rule:failure-restart-revision",
            target=FAILURE_REF,
            criterion="failure-revision",
            from_state="current",
            to_values=("revised", "disputed", "retracted"),
        ),
    )


def failure_evidence(corpus):
    return corpus.evidence_for(
        target_reference=FAILURE_REF,
        criterion="failure-revision",
        pre_state="current",
        proposed_value="revised",
    )


def scope() -> FailureScope:
    return FailureScope(
        scope=TENANT,
        isolation_domain_refs=(TENANT, PROJECT),
        required_isolation_domain_refs=(TENANT, PROJECT),
        project_ref=PROJECT,
    )


def context() -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, PROJECT),
        principal_ref="agent:failure-restart-test",
        project_ref=PROJECT,
        purpose="failure_recurrence_prevention",
    )


def initial_revision() -> FailureRevision:
    return FailureRevision(
        failure_ref=FAILURE_REF,
        revision_ref="failure-restart-rev:001",
        action_class="deploy_service",
        summary="Deployment timed out while waiting for service readiness",
        category="readiness_timeout",
        causal_status="observed",
        scope=scope(),
        source_component=COMPONENT,
        observed_at="2026-01-01T00:00:00Z",
        expected_outcome="service becomes ready",
        actual_outcome="readiness deadline exceeded",
        severity_label="critical",
        impact_score=0.95,
        root_cause_candidates=("dependency unavailable",),
        mitigation="Check readiness dependency before deployment",
        verification_evidence_refs=("evidence:timeout-confirmed",),
        applicability_conditions=("same deployment path",),
        source_evidence_refs=("evidence:deploy-log",),
        estimator_ref="estimator:failure-similarity",
        estimator_version="1.0.0",
    )


def retracted_revision(prior: FailureRevision) -> FailureRevision:
    return FailureRevision(
        failure_ref=FAILURE_REF,
        revision_ref="failure-restart-rev:003",
        action_class=prior.action_class,
        summary="",
        category=prior.category,
        causal_status=prior.causal_status,
        scope=prior.scope,
        source_component=prior.source_component,
        observed_at="2026-01-03T00:00:00Z",
        severity_label=prior.severity_label,
        source_evidence_refs=("evidence:source-correction",),
        prior_revision_ref=prior.revision_ref,
        revision_reason="source correction invalidated the failure record",
        memory_status="retracted",
        estimator_ref=prior.estimator_ref,
        estimator_version=prior.estimator_version,
    )


class FailureMemoryRestartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile = profile()
        self.corpus = failure_corpus()
        self.registry = registry_for(self.corpus)
        self.factories = {
            AUXILIARY_ID: lambda adapter: CheckpointedFailureMemory(
                adapter=adapter,
                available_components=(COMPONENT,),
            )
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create(self) -> ComposedRestartSafeRuntime:
        return ComposedRestartSafeRuntime.create(
            self.root,
            tenant=TENANT,
            profile=self.profile,
            auxiliary_factories=self.factories,
            verifier_registry=self.registry,
        )

    def recover(self) -> ComposedRestartSafeRuntime:
        return ComposedRestartSafeRuntime.recover(
            self.root,
            profile=self.profile,
            auxiliary_factories=self.factories,
            verifier_registry=self.registry,
        )

    def test_recurrence_lineage_and_current_recall_survive_restart(self) -> None:
        runtime = self.create()
        memory = runtime.auxiliary(AUXILIARY_ID)
        first = initial_revision()
        first_result = memory.apply_revision(
            first,
            actor_id="agent:failure-restart-test",
        )
        self.assertTrue(first_result.commit.committed)

        second_result = memory.record_recurrence(
            FAILURE_REF,
            revision_ref="failure-restart-rev:002",
            recurrence_evidence_ref="evidence:recurrence-after-redeploy",
            observed_at="2026-01-02T00:00:00Z",
            actor_id="agent:failure-restart-test",
            similarity_score=0.98,
            review_satisfied=True,
            approval_refs=("approval:failure-recurrence-review",),
            evidence=failure_evidence(self.corpus),
        )
        self.assertTrue(second_result.commit.committed)
        self.assertEqual(2, memory.occurrence_count(FAILURE_REF))

        checkpoint = runtime.checkpoint()
        recovered = self.recover()
        restored = recovered.auxiliary(AUXILIARY_ID)

        self.assertEqual(checkpoint.generation, recovered.recovery_evidence.generation)
        self.assertEqual(2, len(restored.history(FAILURE_REF)))
        self.assertEqual(2, restored.occurrence_count(FAILURE_REF))
        self.assertEqual(
            "failure-restart-rev:002",
            restored.current(FAILURE_REF).revision_ref,
        )
        self.assertEqual(
            second_result.fact_uuid,
            restored.fact_uuid("failure-restart-rev:002"),
        )
        active = restored.recall_active(
            "deployment readiness timeout",
            context=context(),
        )
        self.assertIn(FAILURE_REF, active.active_object_refs)

    def test_retracted_failure_cannot_resurrect_after_restart(self) -> None:
        runtime = self.create()
        memory = runtime.auxiliary(AUXILIARY_ID)
        first = initial_revision()
        first_result = memory.apply_revision(
            first,
            actor_id="agent:failure-restart-test",
        )
        self.assertTrue(first_result.commit.committed)

        retracted = retracted_revision(first)
        delete_result = memory.apply_revision(
            retracted,
            actor_id="agent:failure-restart-test",
        )
        self.assertTrue(delete_result.commit.committed)
        self.assertEqual("retracted", memory.revision_state(FAILURE_REF, retracted.revision_ref))
        self.assertIsNone(runtime.adapter.current_fact_uuid(FAILURE_REF))

        runtime.checkpoint()
        recovered = self.recover()
        restored = recovered.auxiliary(AUXILIARY_ID)

        self.assertEqual(2, len(restored.history(FAILURE_REF)))
        self.assertEqual("retracted", restored.current(FAILURE_REF).memory_status)
        self.assertIsNone(recovered.adapter.current_fact_uuid(FAILURE_REF))
        self.assertIsNotNone(recovered.adapter.tombstone(first_result.fact_uuid))
        active = restored.recall_active(
            "deployment readiness timeout",
            context=context(),
        )
        self.assertNotIn(FAILURE_REF, active.active_object_refs)
        self.assertNotIn(first_result.fact_uuid, active.admitted_fact_uuids)

    def test_owner_restore_fails_closed_on_missing_durable_fact(self) -> None:
        runtime = self.create()
        memory = runtime.auxiliary(AUXILIARY_ID)
        first = initial_revision()
        result = memory.apply_revision(
            first,
            actor_id="agent:failure-restart-test",
        )
        self.assertTrue(result.commit.committed)

        snapshot = memory.export_checkpoint_state()
        corrupted = copy.deepcopy(snapshot)
        corrupted["fact_by_revision"][first.revision_ref] = "missing-fact"
        corrupted["object_by_fact"] = {"missing-fact": FAILURE_REF}

        fresh = CheckpointedFailureMemory(
            adapter=runtime.adapter,
            available_components=(COMPONENT,),
        )
        with self.assertRaisesRegex(
            FailureCheckpointError,
            "absent from durable substrate",
        ):
            fresh.restore_checkpoint_state(corrupted)


if __name__ == "__main__":
    unittest.main()
