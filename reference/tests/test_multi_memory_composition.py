from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.qualified_fixtures import corpus_for, registry_for, rule

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.epistemic_memory import (
    EPISTEMIC_AUXILIARY_COMPONENT_ID,
    BeliefRevision,
    EpistemicScope,
    SemanticEpistemicCompositionRuntime,
)
from agentmem_ref.restart_runtime import (
    CapabilityBinding,
    RuntimeProfile,
    RuntimeRecoveryError,
)

TENANT = "tenant:multi-memory"
PROJECT = "project:multi-memory"
PURPOSE = "release-planning"
SEMANTIC_REF = "memory:release-branch"
BELIEF_REF = "belief:release-safety"
EXPERIENCE_REF = "experience:deploy-observation-001"
SOURCE_COMPONENT = "EpistemicReference"


def _binding() -> CapabilityBinding:
    return CapabilityBinding(
        component_id="reference-governed-memory",
        component_version="1.0.0",
        capability_id="governed-memory-core",
        capability_version="1.0.0",
        maturity="reference_qualified",
        evidence_ref="evidence:reference-runtime-core-v1",
    )


def _profile() -> RuntimeProfile:
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="reference-semantic-epistemic-memory",
        profile_version="1.0.0",
        bindings=(_binding(),),
    )


def _scope() -> EpistemicScope:
    return EpistemicScope(
        scope=TENANT,
        isolation_domain_refs=(TENANT, PROJECT),
        required_isolation_domain_refs=(PROJECT,),
        project_ref=PROJECT,
        purpose=PURPOSE,
    )


def _context(*, project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:multi-memory-test",
        project_ref=project_ref,
        purpose=PURPOSE,
    )


def _semantic_proposal(
    proposal_id: str = "proposal:semantic:001",
    *,
    experience_ref: str = EXPERIENCE_REF,
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:multi-memory-test",
        charter_version="rc1-multi-memory-v1",
        target_reference=SEMANTIC_REF,
        target_class=policy.M2,
        scope=TENANT,
        operation="promotion",
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=(experience_ref,),
        tenant_ref=TENANT,
        isolation_domain_refs=(TENANT, PROJECT),
        required_isolation_domain_refs=(PROJECT,),
        project_ref=PROJECT,
        purpose=PURPOSE,
    )


def _revision(
    revision_ref: str = "belief-rev:001",
    *,
    claim_text: str = "Release branch main is likely safe for staged deployment",
    confidence: float | None = 0.8,
    status: str = "active",
    prior_revision_ref: str = "",
    revision_reason: str = "",
    supporting: tuple[str, ...] = (EXPERIENCE_REF,),
    contradicting: tuple[str, ...] = (),
) -> BeliefRevision:
    return BeliefRevision(
        belief_ref=BELIEF_REF,
        revision_ref=revision_ref,
        epistemic_kind="belief",
        claim_text=claim_text,
        confidence=confidence,
        scope=_scope(),
        source_component=SOURCE_COMPONENT,
        observed_at="2026-09-23T06:00:00Z",
        supporting_evidence_refs=supporting,
        contradicting_evidence_refs=contradicting,
        revision_reason=revision_reason,
        prior_revision_ref=prior_revision_ref,
        epistemic_status=status,
        estimator_ref="estimator:release-safety",
        estimator_version="1.0.0",
    )


def _belief_corpus():
    return corpus_for(
        rule(
            rule_id="rule:multi-memory-belief-revision",
            target=BELIEF_REF,
            criterion="belief-revision",
            from_state="current",
            to_values=("revised", "disputed", "retracted"),
        )
    )


def _belief_evidence(*, proposed_value: str = "disputed"):
    return _belief_corpus().evidence_for(
        target_reference=BELIEF_REF,
        criterion="belief-revision",
        pre_state="current",
        proposed_value=proposed_value,
    )


class SemanticEpistemicCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile = _profile()
        self.registry = registry_for(_belief_corpus())

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _runtime(self) -> SemanticEpistemicCompositionRuntime:
        return SemanticEpistemicCompositionRuntime.create(
            self.root,
            tenant=TENANT,
            profile=self.profile,
            available_components=(SOURCE_COMPONENT,),
            verifier_registry=self.registry,
        )

    def _retain(self, runtime: SemanticEpistemicCompositionRuntime):
        return runtime.retain_experience(
            experience_ref=EXPERIENCE_REF,
            semantic_proposal=_semantic_proposal(),
            semantic_fact_text="Release branch main is active for staged deployment",
            epistemic_revision=_revision(),
            actor_id="agent:multi-memory-test",
        )

    def test_shared_experience_produces_distinct_memory_forms_and_survives_restart(self) -> None:
        runtime = self._runtime()
        retained = self._retain(runtime)

        self.assertTrue(retained.fully_retained)
        self.assertFalse(retained.partially_retained)
        self.assertNotEqual(
            retained.semantic_commit.fact_uuid,
            retained.epistemic_result.fact_uuid,
        )
        self.assertNotEqual(SEMANTIC_REF, BELIEF_REF)
        self.assertEqual(
            [EPISTEMIC_AUXILIARY_COMPONENT_ID],
            [item.component_id for item in runtime.runtime.auxiliary_evidence()],
        )

        semantic = runtime.recall_semantic("release branch main staged", _context())
        self.assertIn(retained.semantic_commit.fact_uuid, semantic.admitted)
        self.assertNotIn(retained.epistemic_result.fact_uuid, semantic.admitted)
        self.assertEqual(
            "memory_type_mismatch:semantic_fact_memory",
            semantic.refusals[retained.epistemic_result.fact_uuid],
        )

        epistemic = runtime.recall_epistemic("release branch main staged", _context())
        self.assertEqual([BELIEF_REF], epistemic.active_object_refs)
        self.assertEqual(
            "memory_type_mismatch:epistemic_belief_memory",
            epistemic.refusals[retained.semantic_commit.fact_uuid],
        )

        recovered = SemanticEpistemicCompositionRuntime.recover(
            self.root,
            profile=self.profile,
            available_components=(SOURCE_COMPONENT,),
            verifier_registry=self.registry,
        )
        self.assertEqual(_revision(), recovered.epistemic.current(BELIEF_REF))
        self.assertEqual(
            retained.epistemic_result.fact_uuid,
            recovered.epistemic.fact_uuid("belief-rev:001"),
        )
        semantic_after = recovered.recall_semantic("release branch main", _context())
        self.assertIn(retained.semantic_commit.fact_uuid, semantic_after.admitted)
        epistemic_after = recovered.recall_epistemic("release branch main", _context())
        self.assertEqual([BELIEF_REF], epistemic_after.active_object_refs)

    def test_disputed_epistemic_revision_survives_restart_but_not_active_cognition(self) -> None:
        runtime = self._runtime()
        self._retain(runtime)
        disputed = _revision(
            "belief-rev:002",
            claim_text="Release branch safety is unresolved after a production incident",
            confidence=1.0,
            status="disputed",
            prior_revision_ref="belief-rev:001",
            revision_reason="conflicting production evidence",
            supporting=(EXPERIENCE_REF, "evidence:incident"),
            contradicting=("evidence:canary-success",),
        )
        result = runtime.apply_epistemic_revision(
            disputed,
            actor_id="agent:multi-memory-test",
            review_satisfied=True,
            approval_refs=("approval:epistemic-review",),
            evidence=_belief_evidence(proposed_value="disputed"),
        )
        self.assertTrue(result.commit.committed)
        self.assertEqual("disputed", result.lineage_state)

        recovered = SemanticEpistemicCompositionRuntime.recover(
            self.root,
            profile=self.profile,
            available_components=(SOURCE_COMPONENT,),
            verifier_registry=self.registry,
        )
        self.assertEqual("disputed", recovered.epistemic.current(BELIEF_REF).epistemic_status)
        self.assertEqual(1.0, recovered.epistemic.current(BELIEF_REF).confidence)
        active = recovered.recall_epistemic("release branch safety unresolved", _context())
        self.assertNotIn(BELIEF_REF, active.active_object_refs)
        self.assertEqual("epistemic_disputed", active.refusals[result.fact_uuid])

    def test_retraction_survives_restart_without_resurrecting_current_claim(self) -> None:
        runtime = self._runtime()
        retained = self._retain(runtime)
        retracted = _revision(
            "belief-rev:002",
            claim_text="",
            confidence=None,
            status="retracted",
            prior_revision_ref="belief-rev:001",
            revision_reason="source withdrew the observation",
            supporting=(EXPERIENCE_REF, "evidence:withdrawal"),
        )
        result = runtime.apply_epistemic_revision(
            retracted,
            actor_id="agent:multi-memory-test",
        )
        self.assertTrue(result.commit.committed)
        self.assertIsNone(runtime.epistemic.current_claim(BELIEF_REF))

        recovered = SemanticEpistemicCompositionRuntime.recover(
            self.root,
            profile=self.profile,
            available_components=(SOURCE_COMPONENT,),
            verifier_registry=self.registry,
        )
        self.assertEqual("retracted", recovered.epistemic.current(BELIEF_REF).epistemic_status)
        self.assertIsNone(recovered.epistemic.current_claim(BELIEF_REF))
        self.assertIsNone(recovered.adapter.current_fact_uuid(BELIEF_REF))
        active = recovered.recall_epistemic("release branch safe staged", _context())
        self.assertEqual([], active.active_object_refs)
        self.assertNotIn(retained.epistemic_result.fact_uuid, active.admitted_fact_uuids)

    def test_confidence_one_does_not_create_revision_authority_or_rollback_semantic_memory(self) -> None:
        runtime = self._runtime()
        retained = self._retain(runtime)
        proposed = _revision(
            "belief-rev:002",
            claim_text="Release branch main is definitely unsafe",
            confidence=1.0,
            prior_revision_ref="belief-rev:001",
            revision_reason="estimator asserted certainty",
            supporting=(EXPERIENCE_REF, "evidence:estimator-only"),
        )
        refused = runtime.apply_epistemic_revision(
            proposed,
            actor_id="agent:multi-memory-test",
        )
        self.assertFalse(refused.commit.committed)
        self.assertEqual(policy.REQUIRE_REVIEW, refused.commit.decision.outcome)
        self.assertEqual("belief-rev:001", runtime.epistemic.current(BELIEF_REF).revision_ref)

        semantic = runtime.recall_semantic("release branch main", _context())
        self.assertIn(retained.semantic_commit.fact_uuid, semantic.admitted)

        recovered = SemanticEpistemicCompositionRuntime.recover(
            self.root,
            profile=self.profile,
            available_components=(SOURCE_COMPONENT,),
            verifier_registry=self.registry,
        )
        self.assertEqual("belief-rev:001", recovered.epistemic.current(BELIEF_REF).revision_ref)
        self.assertIn(
            retained.semantic_commit.fact_uuid,
            recovered.recall_semantic("release branch main", _context()).admitted,
        )

    def test_shared_experience_binding_and_scope_mismatch_fail_before_writes(self) -> None:
        runtime = self._runtime()
        missing = _semantic_proposal(experience_ref="experience:other")
        with self.assertRaisesRegex(ValueError, "semantic consequence"):
            runtime.retain_experience(
                experience_ref=EXPERIENCE_REF,
                semantic_proposal=missing,
                semantic_fact_text="Release branch main",
                epistemic_revision=_revision(),
                actor_id="agent:multi-memory-test",
            )
        self.assertEqual(0, runtime.adapter.state_version(SEMANTIC_REF))
        self.assertIsNone(runtime.epistemic.current(BELIEF_REF))

        wrong_scope = BeliefRevision(
            **{
                **_revision().__dict__,
                "scope": EpistemicScope(
                    scope=TENANT,
                    isolation_domain_refs=(TENANT, "project:other"),
                    required_isolation_domain_refs=("project:other",),
                    project_ref="project:other",
                    purpose=PURPOSE,
                ),
            }
        )
        with self.assertRaisesRegex(ValueError, "project_ref mismatch"):
            runtime.retain_experience(
                experience_ref=EXPERIENCE_REF,
                semantic_proposal=_semantic_proposal(),
                semantic_fact_text="Release branch main",
                epistemic_revision=wrong_scope,
                actor_id="agent:multi-memory-test",
            )
        self.assertEqual(0, runtime.adapter.state_version(SEMANTIC_REF))

    def test_auxiliary_component_drift_fails_closed(self) -> None:
        runtime = self._runtime()
        self._retain(runtime)

        with self.assertRaises(RuntimeRecoveryError):
            SemanticEpistemicCompositionRuntime.recover(
                self.root,
                profile=self.profile,
                available_components=("DifferentEpistemicProvider",),
                verifier_registry=self.registry,
            )

    def test_wrong_project_is_refused_for_both_memory_forms_after_restart(self) -> None:
        runtime = self._runtime()
        retained = self._retain(runtime)
        recovered = SemanticEpistemicCompositionRuntime.recover(
            self.root,
            profile=self.profile,
            available_components=(SOURCE_COMPONENT,),
            verifier_registry=self.registry,
        )

        semantic = recovered.recall_semantic("release branch main", _context(project_ref="project:other"))
        self.assertNotIn(retained.semantic_commit.fact_uuid, semantic.admitted)
        self.assertEqual(
            "project_scope_mismatch",
            semantic.refusals[retained.semantic_commit.fact_uuid],
        )

        epistemic = recovered.recall_epistemic(
            "release branch main safe",
            _context(project_ref="project:other"),
        )
        self.assertNotIn(BELIEF_REF, epistemic.active_object_refs)
        self.assertEqual(
            "project_scope_mismatch",
            epistemic.refusals[retained.epistemic_result.fact_uuid],
        )


if __name__ == "__main__":
    unittest.main()
