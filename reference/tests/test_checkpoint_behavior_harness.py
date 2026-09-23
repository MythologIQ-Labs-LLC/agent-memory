from __future__ import annotations

import unittest

from agentmem_ref.harness.checkpoint_behavior_harness import (
    AssessmentRequirement,
    BehavioralResult,
    CheckpointBehaviorContract,
    CheckpointRef,
    CheckpointStateChanged,
    ObservationUnavailable,
    RecallStage,
    RetrievedItem,
    assess_checkpoint_behavior,
    evaluate_requirement,
)

BASE = CheckpointRef("checkpoint:base", "sha256:base")
CAND = CheckpointRef("checkpoint:candidate", "sha256:candidate")


def contract(*, stage: RecallStage = RecallStage.ADMITTED, tie: str = "rank:stable-v1"):
    return CheckpointBehaviorContract(
        baseline=BASE,
        candidate=CAND,
        recall_stage=stage,
        observer_ref="observer:test",
        observer_version="1.0.0",
        observer_config_digest="sha256:config",
        tie_policy_ref=tie,
        corrected_ref="memory:new",
        superseded_ref="memory:old",
        anchor_refs=("memory:anchor",),
        max_anchor_rank_drop=1,
        forbidden_refs=("memory:forbidden",),
        forbidden_scope_refs=("tenant:other",),
        expected_baseline_refs=("memory:before",),
        expected_candidate_refs=("memory:after",),
    )


def observations():
    return {
        (CAND.checkpoint_ref, "correction_precedence"): (
            RetrievedItem("memory:new", 1),
            RetrievedItem("memory:old", 2),
        ),
        (BASE.checkpoint_ref, "anchor_preservation"): (
            RetrievedItem("memory:anchor", 1),
        ),
        (CAND.checkpoint_ref, "anchor_preservation"): (
            RetrievedItem("memory:anchor", 2),
        ),
        (CAND.checkpoint_ref, "scope_isolation"): (
            RetrievedItem("memory:safe", 1, ("tenant:local",)),
        ),
        (BASE.checkpoint_ref, "state_conditioned_differentiation"): (
            RetrievedItem("memory:before", 1),
        ),
        (CAND.checkpoint_ref, "state_conditioned_differentiation"): (
            RetrievedItem("memory:after", 1),
        ),
    }


class Observer:
    def __init__(self, values=None, *, states=None):
        self.values = values or observations()
        self.states = states or {
            BASE.checkpoint_ref: BASE.state_digest,
            CAND.checkpoint_ref: CAND.state_digest,
        }
        self.calls = 0

    def state_digest(self, checkpoint_ref: str) -> str:
        return self.states[checkpoint_ref]

    def observe(self, checkpoint_ref: str, observation_ref: str, stage: RecallStage):
        self.calls += 1
        value = self.values[(checkpoint_ref, observation_ref)]
        if isinstance(value, Exception):
            raise value
        return value


class CheckpointBehaviorHarnessTests(unittest.TestCase):
    def test_four_required_probes_verify_without_authority(self):
        assessment = assess_checkpoint_behavior(contract(), Observer())
        self.assertIs(assessment.result, BehavioralResult.VERIFIED)
        self.assertEqual("none", assessment.authority_effect)
        self.assertEqual(
            {
                "correction_precedence",
                "anchor_preservation",
                "scope_isolation",
                "state_conditioned_differentiation",
            },
            {item.probe for item in assessment.probe_results},
        )
        self.assertTrue(all(item.authority_effect == "none" for item in assessment.probe_results))

    def test_correction_precedence_detects_missing_or_outranked_correction(self):
        values = observations()
        values[(CAND.checkpoint_ref, "correction_precedence")] = (
            RetrievedItem("memory:old", 1),
        )
        result = assess_checkpoint_behavior(contract(), Observer(values)).probe_results[0]
        self.assertIs(result.result, BehavioralResult.CONTRADICTED)
        self.assertEqual(("corrected_memory_missing",), result.reason_codes)

        values = observations()
        values[(CAND.checkpoint_ref, "correction_precedence")] = (
            RetrievedItem("memory:old", 1),
            RetrievedItem("memory:new", 2),
        )
        result = assess_checkpoint_behavior(contract(), Observer(values)).probe_results[0]
        self.assertEqual(("superseded_memory_outranks_correction",), result.reason_codes)

    def test_anchor_preservation_distinguishes_loss_regression_and_missing_baseline(self):
        values = observations()
        values[(CAND.checkpoint_ref, "anchor_preservation")] = ()
        result = assess_checkpoint_behavior(contract(), Observer(values)).probe_results[1]
        self.assertEqual(("anchor_missing_after_transition",), result.reason_codes)

        values = observations()
        values[(CAND.checkpoint_ref, "anchor_preservation")] = (
            RetrievedItem("memory:anchor", 3),
        )
        result = assess_checkpoint_behavior(contract(), Observer(values)).probe_results[1]
        self.assertEqual(("anchor_rank_regressed",), result.reason_codes)

        values = observations()
        values[(BASE.checkpoint_ref, "anchor_preservation")] = ()
        result = assess_checkpoint_behavior(contract(), Observer(values)).probe_results[1]
        self.assertIs(result.result, BehavioralResult.INCONCLUSIVE)
        self.assertEqual(("baseline_anchor_missing",), result.reason_codes)

    def test_scope_isolation_is_bound_to_declared_recall_stage(self):
        values = observations()
        values[(CAND.checkpoint_ref, "scope_isolation")] = (
            RetrievedItem("memory:foreign", 1, ("tenant:other",)),
        )
        admitted = assess_checkpoint_behavior(contract(stage=RecallStage.ADMITTED), Observer(values))
        self.assertEqual(
            ("forbidden_scope_retrieved",),
            admitted.probe_results[2].reason_codes,
        )
        self.assertNotEqual(
            contract(stage=RecallStage.CANDIDATE).observer_binding_digest,
            contract(stage=RecallStage.ADMITTED).observer_binding_digest,
        )

    def test_state_conditioned_differentiation_detects_state_collapse_and_leakage(self):
        values = observations()
        same = (
            RetrievedItem("memory:before", 1),
            RetrievedItem("memory:after", 2),
        )
        values[(BASE.checkpoint_ref, "state_conditioned_differentiation")] = same
        values[(CAND.checkpoint_ref, "state_conditioned_differentiation")] = same
        result = assess_checkpoint_behavior(contract(), Observer(values)).probe_results[3]
        self.assertIn("retrieval_state_collapsed", result.reason_codes)

        values = observations()
        values[(BASE.checkpoint_ref, "state_conditioned_differentiation")] = (
            RetrievedItem("memory:before", 1),
            RetrievedItem("memory:after", 2),
        )
        result = assess_checkpoint_behavior(contract(), Observer(values)).probe_results[3]
        self.assertIn("candidate_only_memory_leaked_into_baseline_state", result.reason_codes)

    def test_precondition_and_toctou_state_change_fail_closed(self):
        observer = Observer(states={BASE.checkpoint_ref: BASE.state_digest, CAND.checkpoint_ref: "sha256:wrong"})
        with self.assertRaisesRegex(CheckpointStateChanged, "bound precondition"):
            assess_checkpoint_behavior(contract(), observer)
        self.assertEqual(0, observer.calls)

        class Changing(Observer):
            def state_digest(self, checkpoint_ref: str) -> str:
                if self.calls and checkpoint_ref == CAND.checkpoint_ref:
                    return "sha256:changed"
                return super().state_digest(checkpoint_ref)

        with self.assertRaisesRegex(CheckpointStateChanged, "changed during assessment"):
            assess_checkpoint_behavior(contract(), Changing())

    def test_unavailable_observation_is_inconclusive_not_contradicted(self):
        values = observations()
        values[(CAND.checkpoint_ref, "scope_isolation")] = ObservationUnavailable("down")
        assessment = assess_checkpoint_behavior(contract(), Observer(values))
        self.assertIs(assessment.result, BehavioralResult.INCONCLUSIVE)
        self.assertIs(assessment.probe_results[2].result, BehavioralResult.INCONCLUSIVE)
        self.assertEqual(("observation_unavailable",), assessment.probe_results[2].reason_codes)

    def test_tie_policy_changes_applicability_binding(self):
        self.assertNotEqual(
            contract(tie="tie:v1").observer_binding_digest,
            contract(tie="tie:v2").observer_binding_digest,
        )

    def test_requirement_accepts_only_exact_verified_evidence(self):
        c = contract()
        verified = assess_checkpoint_behavior(c, Observer())
        requirement = AssessmentRequirement(
            baseline=c.baseline,
            candidate=c.candidate,
            contract_digest=c.contract_digest,
            observer_binding_digest=c.observer_binding_digest,
        )
        evaluation = evaluate_requirement(requirement, (verified,))
        self.assertEqual("satisfied", evaluation.status)
        self.assertEqual("none", evaluation.authority_effect)

        wrong = AssessmentRequirement(
            baseline=c.baseline,
            candidate=c.candidate,
            contract_digest=c.contract_digest,
            observer_binding_digest="sha256:wrong",
        )
        self.assertEqual(
            ("no_applicable_assessment",),
            evaluate_requirement(wrong, (verified,)).reason_codes,
        )

    def test_applicable_contradiction_dominates_verified_evidence(self):
        c = contract()
        verified = assess_checkpoint_behavior(c, Observer())
        values = observations()
        values[(CAND.checkpoint_ref, "correction_precedence")] = (
            RetrievedItem("memory:old", 1),
        )
        contradicted = assess_checkpoint_behavior(c, Observer(values))
        requirement = AssessmentRequirement(
            baseline=c.baseline,
            candidate=c.candidate,
            contract_digest=c.contract_digest,
            observer_binding_digest=c.observer_binding_digest,
        )
        evaluation = evaluate_requirement(requirement, (verified, contradicted))
        self.assertEqual("not_satisfied", evaluation.status)
        self.assertEqual(("applicable_contradiction",), evaluation.reason_codes)

    def test_evidence_is_content_minimized(self):
        assessment = assess_checkpoint_behavior(contract(), Observer())
        encoded = str(assessment.to_dict())
        self.assertIn("observer_binding_digest", encoded)
        self.assertNotIn("query text", encoded)
        self.assertNotIn("memory:safe", encoded)


if __name__ == "__main__":
    unittest.main()
