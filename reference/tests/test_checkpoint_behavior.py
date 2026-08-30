from __future__ import annotations

import json
import unittest

from agentmem_ref.checkpoint_behavior import (
    AssessmentRequirement,
    AssessmentStateChanged,
    BehavioralResult,
    CheckpointBinding,
    EvidencePosture,
    ProbeDefinition,
    ProbeKind,
    ProbeSuite,
    RecallStage,
    RetrievalRequest,
    RetrievedItem,
    RetrieverBinding,
    RetrieverUnavailable,
    assess_checkpoint_transition,
    evaluate_assessment_requirement,
)

BASE = CheckpointBinding("checkpoint:base", "sha256:base")
CAND = CheckpointBinding("checkpoint:candidate", "sha256:candidate")
START = "2026-08-30T16:00:00Z"
DONE = "2026-08-30T16:00:10Z"


def req(ref: str, context: str = "context:shared") -> RetrievalRequest:
    return RetrievalRequest(ref, f"query:{ref}", context)


def probes(*, trials: int = 1) -> ProbeSuite:
    return ProbeSuite(
        "suite:checkpoint-behavior",
        "0.1.0",
        (
            ProbeDefinition(
                "correction",
                ProbeKind.CORRECTION_PRECEDENCE,
                candidate_request=req("correction"),
                corrected_ref="memory:new",
                superseded_ref="memory:old",
            ),
            ProbeDefinition(
                "anchor",
                ProbeKind.ANCHOR_PRESERVATION,
                baseline_request=req("anchor-before"),
                candidate_request=req("anchor-after"),
                anchor_refs=("memory:anchor",),
                max_rank_drop=1,
            ),
            ProbeDefinition(
                "scope",
                ProbeKind.SCOPE_ISOLATION,
                candidate_request=req("scope"),
                forbidden_scope_refs=("tenant:other",),
            ),
            ProbeDefinition(
                "state",
                ProbeKind.STATE_CONDITIONED_DIFFERENTIATION,
                baseline_request=req("state-before", "context:before"),
                candidate_request=req("state-after", "context:after"),
                expected_baseline_refs=("memory:before",),
                expected_candidate_refs=("memory:after",),
            ),
        ),
        trials=trials,
    )


def good() -> dict[tuple[str, str], tuple[RetrievedItem, ...]]:
    return {
        (CAND.checkpoint_ref, "correction"): (
            RetrievedItem("memory:new", 1, "v2", ("tenant:local",)),
            RetrievedItem("memory:old", 3, "v1", ("tenant:local",)),
        ),
        (BASE.checkpoint_ref, "anchor-before"): (
            RetrievedItem("memory:anchor", 1),
        ),
        (CAND.checkpoint_ref, "anchor-after"): (
            RetrievedItem("memory:anchor", 2),
        ),
        (CAND.checkpoint_ref, "scope"): (
            RetrievedItem("memory:safe", 1, scope_refs=("tenant:local",)),
        ),
        (BASE.checkpoint_ref, "state-before"): (
            RetrievedItem("memory:before", 1),
        ),
        (CAND.checkpoint_ref, "state-after"): (
            RetrievedItem("memory:after", 1),
        ),
    }


class Retriever:
    def __init__(
        self,
        responses=None,
        *,
        stage=RecallStage.ADMITTED,
        tie="rank:stable-explicit-v1",
        states=None,
    ):
        self.responses = responses or good()
        self.states = states or {
            BASE.checkpoint_ref: BASE.state_digest,
            CAND.checkpoint_ref: CAND.state_digest,
        }
        self.calls = 0
        self.binding = RetrieverBinding(
            "retriever:test",
            "1.0.0",
            "profile:test",
            "1.0.0",
            "sha256:config",
            stage,
            tie,
        )

    def state_digest(self, checkpoint_ref: str) -> str:
        return self.states[checkpoint_ref]

    def retrieve(self, checkpoint_ref: str, request: RetrievalRequest):
        self.calls += 1
        value = self.responses[(checkpoint_ref, request.request_ref)]
        if isinstance(value, Exception):
            raise value
        return value


def assess(retriever: Retriever, suite=None):
    return assess_checkpoint_transition(
        baseline=BASE,
        candidate=CAND,
        suite=suite or probes(),
        retriever=retriever,
        started_at=START,
        completed_at=DONE,
    )


def requirement(assessment, **changes) -> AssessmentRequirement:
    values = dict(
        requirement_ref="requirement:checkpoint",
        baseline=assessment.baseline,
        candidate=assessment.candidate,
        probe_suite_digest=assessment.probe_suite_digest,
        retriever_profile_digest=assessment.retriever_profile_digest,
        not_before=START,
        not_after="2026-08-30T17:00:00Z",
    )
    values.update(changes)
    return AssessmentRequirement(**values)


class CheckpointBehaviorTests(unittest.TestCase):
    def test_four_required_invariants_verify_without_authority(self):
        assessment = assess(Retriever(), probes(trials=2))
        self.assertIs(assessment.result, BehavioralResult.VERIFIED)
        self.assertIs(assessment.posture, EvidencePosture.EXERCISED)
        self.assertEqual("none", assessment.authority_effect)
        self.assertEqual(
            set(ProbeKind),
            {result.kind for result in assessment.probe_results},
        )

    def test_correction_missing_and_outranked_are_contradictions(self):
        responses = good()
        responses[(CAND.checkpoint_ref, "correction")] = (
            RetrievedItem("memory:old", 1),
        )
        self.assertEqual(
            ("corrected_memory_missing",),
            assess(Retriever(responses)).probe_results[0].reason_codes,
        )
        responses = good()
        responses[(CAND.checkpoint_ref, "correction")] = (
            RetrievedItem("memory:old", 1),
            RetrievedItem("memory:new", 2),
        )
        self.assertEqual(
            ("superseded_memory_outranks_correction",),
            assess(Retriever(responses)).probe_results[0].reason_codes,
        )

    def test_anchor_loss_demote_and_missing_baseline_stay_distinct(self):
        responses = good()
        responses[(CAND.checkpoint_ref, "anchor-after")] = ()
        self.assertEqual(
            ("anchor_missing_after_transition",),
            assess(Retriever(responses)).probe_results[1].reason_codes,
        )
        responses = good()
        responses[(CAND.checkpoint_ref, "anchor-after")] = (
            RetrievedItem("memory:anchor", 3),
        )
        self.assertEqual(
            ("anchor_rank_regressed",),
            assess(Retriever(responses)).probe_results[1].reason_codes,
        )
        responses = good()
        responses[(BASE.checkpoint_ref, "anchor-before")] = ()
        result = assess(Retriever(responses)).probe_results[1]
        self.assertIs(result.result, BehavioralResult.INCONCLUSIVE)
        self.assertEqual(("baseline_anchor_missing",), result.reason_codes)

    def test_scope_isolation_is_bound_to_declared_recall_stage(self):
        responses = good()
        responses[(CAND.checkpoint_ref, "scope")] = (
            RetrievedItem("memory:foreign", 1, scope_refs=("tenant:other",)),
        )
        admitted = assess(Retriever(responses, stage=RecallStage.ADMITTED))
        self.assertEqual(
            ("forbidden_scope_retrieved",),
            admitted.probe_results[2].reason_codes,
        )
        candidate_digest = Retriever(
            responses,
            stage=RecallStage.CANDIDATE,
        ).binding.digest
        admitted_digest = Retriever(
            responses,
            stage=RecallStage.ADMITTED,
        ).binding.digest
        self.assertNotEqual(candidate_digest, admitted_digest)

    def test_empty_scope_result_is_only_negative_property_evidence(self):
        responses = good()
        responses[(CAND.checkpoint_ref, "scope")] = ()
        result = assess(Retriever(responses)).probe_results[2]
        self.assertIs(result.result, BehavioralResult.VERIFIED)
        self.assertEqual(
            ("no_forbidden_retrieval_observed",),
            result.reason_codes,
        )

    def test_state_collapse_and_cross_state_leak_are_contradictions(self):
        same = (
            RetrievedItem("memory:before", 1),
            RetrievedItem("memory:after", 2),
        )
        responses = good()
        responses[(BASE.checkpoint_ref, "state-before")] = same
        responses[(CAND.checkpoint_ref, "state-after")] = same
        self.assertEqual(
            ("retrieval_state_collapsed",),
            assess(Retriever(responses)).probe_results[3].reason_codes,
        )

        responses = good()
        responses[(BASE.checkpoint_ref, "state-before")] = (
            RetrievedItem("memory:before", 1),
            RetrievedItem("memory:after", 2),
        )
        self.assertEqual(
            ("candidate_only_memory_leaked_into_baseline_state",),
            assess(Retriever(responses)).probe_results[3].reason_codes,
        )

    def test_bad_probe_shapes_and_duplicates_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct contexts"):
            ProbeDefinition(
                "bad",
                ProbeKind.STATE_CONDITIONED_DIFFERENTIATION,
                baseline_request=req("a", "same"),
                candidate_request=req("b", "same"),
                expected_baseline_refs=("a",),
                expected_candidate_refs=("b",),
            )
        probe = ProbeDefinition(
            "scope",
            ProbeKind.SCOPE_ISOLATION,
            candidate_request=req("scope"),
            forbidden_refs=("x",),
        )
        with self.assertRaisesRegex(ValueError, "probe IDs must be unique"):
            ProbeSuite("suite:x", "1", (probe, probe))

        responses = good()
        responses[(CAND.checkpoint_ref, "scope")] = (
            RetrievedItem("dup", 1),
            RetrievedItem("dup", 2),
        )
        with self.assertRaisesRegex(
            ValueError,
            "duplicate retrieved logical_ref",
        ):
            assess(Retriever(responses))

    def test_core_suite_cannot_make_one_invariant_optional(self):
        definitions = list(probes().probes)
        definitions[2] = ProbeDefinition(
            "scope",
            ProbeKind.SCOPE_ISOLATION,
            required=False,
            candidate_request=req("scope"),
            forbidden_scope_refs=("tenant:other",),
        )
        with self.assertRaisesRegex(
            ValueError,
            "required checkpoint probes missing",
        ):
            ProbeSuite("suite:x", "1", tuple(definitions))

    def test_tie_policy_is_part_of_retriever_applicability(self):
        self.assertNotEqual(
            Retriever(tie="tie:v1").binding.digest,
            Retriever(tie="tie:v2").binding.digest,
        )

    def test_state_change_aborts_instead_of_misbinding_evidence(self):
        class Changing(Retriever):
            def state_digest(self, checkpoint_ref):
                if checkpoint_ref == CAND.checkpoint_ref and self.calls:
                    return "sha256:changed"
                return super().state_digest(checkpoint_ref)

        with self.assertRaisesRegex(
            AssessmentStateChanged,
            "changed during assessment",
        ):
            assess(Changing())

    def test_precondition_mismatch_aborts_before_retrieval(self):
        retriever = Retriever(
            states={
                BASE.checkpoint_ref: BASE.state_digest,
                CAND.checkpoint_ref: "sha256:wrong",
            }
        )
        with self.assertRaisesRegex(
            AssessmentStateChanged,
            "bound precondition",
        ):
            assess(retriever)
        self.assertEqual(0, retriever.calls)

    def test_unavailable_probe_is_inconclusive_not_contradicted(self):
        responses = good()
        responses[(CAND.checkpoint_ref, "scope")] = RetrieverUnavailable("down")
        assessment = assess(Retriever(responses))
        self.assertIs(assessment.result, BehavioralResult.INCONCLUSIVE)
        self.assertIs(assessment.posture, EvidencePosture.UNAVAILABLE)

    def test_evidence_is_machine_readable_and_content_minimized(self):
        assessment = assess(Retriever())
        encoded = json.dumps(assessment.to_dict())
        self.assertIn("retriever_profile_digest", encoded)
        self.assertNotIn("query:correction", encoded)
        json.dumps(
            evaluate_assessment_requirement(
                requirement(assessment),
                (assessment,),
                evaluated_at="2026-08-30T16:30:00Z",
            ).to_dict()
        )

    def test_only_exact_verified_applicable_evidence_satisfies_requirement(self):
        assessment = assess(Retriever())
        evaluation = evaluate_assessment_requirement(
            requirement(assessment),
            (assessment,),
            evaluated_at="2026-08-30T16:30:00Z",
        )
        self.assertEqual("satisfied", evaluation.status)
        self.assertEqual("none", evaluation.authority_effect)

        wrong = requirement(
            assessment,
            retriever_profile_digest="sha256:wrong",
        )
        self.assertEqual(
            ("no_applicable_assessment",),
            evaluate_assessment_requirement(
                wrong,
                (assessment,),
                evaluated_at="2026-08-30T16:30:00Z",
            ).reason_codes,
        )

    def test_applicable_contradiction_dominates_verified_evidence(self):
        verified = assess(Retriever())
        responses = good()
        responses[(CAND.checkpoint_ref, "correction")] = (
            RetrievedItem("memory:old", 1),
        )
        contradicted = assess(Retriever(responses))
        evaluation = evaluate_assessment_requirement(
            requirement(verified),
            (verified, contradicted),
            evaluated_at="2026-08-30T16:30:00Z",
        )
        self.assertEqual("not_satisfied", evaluation.status)
        self.assertEqual(
            ("applicable_contradiction",),
            evaluation.reason_codes,
        )

    def test_remediation_preserves_historical_failure_without_reapplying_it(self):
        responses = good()
        responses[(CAND.checkpoint_ref, "correction")] = (
            RetrievedItem("memory:old", 1),
        )
        old_failure = assess(Retriever(responses))

        remediated = CheckpointBinding(
            "checkpoint:remediated",
            "sha256:remediated",
        )
        moved = {
            (
                remediated.checkpoint_ref
                if checkpoint == CAND.checkpoint_ref
                else checkpoint,
                request_ref,
            ): value
            for (checkpoint, request_ref), value in good().items()
        }
        retriever = Retriever(
            moved,
            states={
                BASE.checkpoint_ref: BASE.state_digest,
                remediated.checkpoint_ref: remediated.state_digest,
            },
        )
        repaired = assess_checkpoint_transition(
            baseline=BASE,
            candidate=remediated,
            suite=probes(),
            retriever=retriever,
            started_at=START,
            completed_at=DONE,
        )
        current = AssessmentRequirement(
            "requirement:repaired",
            BASE,
            remediated,
            repaired.probe_suite_digest,
            repaired.retriever_profile_digest,
        )
        evaluation = evaluate_assessment_requirement(
            current,
            (old_failure, repaired),
            evaluated_at="2026-08-30T16:30:00Z",
        )
        self.assertIs(old_failure.result, BehavioralResult.CONTRADICTED)
        self.assertEqual("satisfied", evaluation.status)
        self.assertEqual(
            (repaired.assessment_id,),
            evaluation.applicable_assessment_ids,
        )


if __name__ == "__main__":
    unittest.main()
