from __future__ import annotations

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
    RetrievalRequest,
    RetrievedItem,
    RetrieverBinding,
    RetrieverUnavailable,
    assess_checkpoint_transition,
    evaluate_assessment_requirement,
)

BASELINE = CheckpointBinding("checkpoint:baseline", "sha256:baseline")
CANDIDATE = CheckpointBinding("checkpoint:candidate", "sha256:candidate")
NOW = "2026-08-30T16:00:00Z"
DONE = "2026-08-30T16:00:10Z"


class FakeRetriever:
    def __init__(self, responses, *, states=None):
        self._responses = dict(responses)
        self._states = states or {
            BASELINE.checkpoint_ref: BASELINE.state_digest,
            CANDIDATE.checkpoint_ref: CANDIDATE.state_digest,
        }
        self.binding = RetrieverBinding(
            component_ref="memory:test-retriever",
            component_version="1.0.0",
            profile_ref="profile:test",
            profile_version="1.0.0",
            config_digest="sha256:config",
        )
        self.calls = 0

    def state_digest(self, checkpoint_ref):
        return self._states[checkpoint_ref]

    def retrieve(self, checkpoint_ref, request):
        self.calls += 1
        value = self._responses[(checkpoint_ref, request.request_ref)]
        if isinstance(value, Exception):
            raise value
        return value


def request(ref, context="context:shared"):
    return RetrievalRequest(ref, f"query for {ref}", context)


def suite(*, required_scope=True, trials=1):
    return ProbeSuite(
        suite_ref="suite:checkpoint-transition",
        suite_version="0.1.0",
        trials=trials,
        probes=(
            ProbeDefinition(
                probe_id="correction",
                kind=ProbeKind.CORRECTION_PRECEDENCE,
                candidate_request=request("correction"),
                corrected_ref="memory:new",
                superseded_ref="memory:old",
            ),
            ProbeDefinition(
                probe_id="anchor",
                kind=ProbeKind.ANCHOR_PRESERVATION,
                baseline_request=request("anchor-before"),
                candidate_request=request("anchor-after"),
                anchor_refs=("memory:anchor",),
                max_rank_drop=1,
            ),
            ProbeDefinition(
                probe_id="scope",
                kind=ProbeKind.SCOPE_ISOLATION,
                required=required_scope,
                candidate_request=request("scope"),
                forbidden_scope_refs=("tenant:other",),
            ),
            ProbeDefinition(
                probe_id="differentiate",
                kind=ProbeKind.STATE_CONDITIONED_DIFFERENTIATION,
                baseline_request=request("state-before", "context:before"),
                candidate_request=request("state-after", "context:after"),
                expected_baseline_refs=("memory:before",),
                expected_candidate_refs=("memory:after",),
            ),
        ),
    )


def passing_responses(scope_items=None):
    return {
        (CANDIDATE.checkpoint_ref, "correction"): (
            RetrievedItem("memory:new", 1, "v2", ("tenant:local",)),
            RetrievedItem("memory:old", 3, "v1", ("tenant:local",)),
        ),
        (BASELINE.checkpoint_ref, "anchor-before"): (
            RetrievedItem("memory:anchor", 1),
        ),
        (CANDIDATE.checkpoint_ref, "anchor-after"): (
            RetrievedItem("memory:anchor", 2),
        ),
        (CANDIDATE.checkpoint_ref, "scope"): scope_items
        if scope_items is not None
        else (RetrievedItem("memory:safe", 1, scope_refs=("tenant:local",)),),
        (BASELINE.checkpoint_ref, "state-before"): (
            RetrievedItem("memory:before", 1),
        ),
        (CANDIDATE.checkpoint_ref, "state-after"): (
            RetrievedItem("memory:after", 1),
        ),
    }


def assess(retriever, probe_suite=None):
    return assess_checkpoint_transition(
        baseline=BASELINE,
        candidate=CANDIDATE,
        suite=probe_suite or suite(),
        retriever=retriever,
        started_at=NOW,
        completed_at=DONE,
    )


def requirement(assessment, **changes):
    values = {
        "requirement_ref": "requirement:checkpoint-transition",
        "baseline": assessment.baseline,
        "candidate": assessment.candidate,
        "probe_suite_digest": assessment.probe_suite_digest,
        "retriever_profile_digest": assessment.retriever_profile_digest,
        "not_before": NOW,
        "not_after": "2026-08-30T17:00:00Z",
    }
    values.update(changes)
    return AssessmentRequirement(**values)


class CheckpointBehaviorTests(unittest.TestCase):
    def test_four_invariants_verify_without_granting_authority(self) -> None:
        assessment = assess(FakeRetriever(passing_responses()), suite(trials=2))
        self.assertIs(BehavioralResult.VERIFIED, assessment.result)
        self.assertIs(EvidencePosture.EXERCISED, assessment.posture)
        self.assertEqual("none", assessment.authority_effect)
        self.assertEqual(set(ProbeKind), {item.kind for item in assessment.probe_results})
        self.assertTrue(
            all(item.result is BehavioralResult.VERIFIED for item in assessment.probe_results)
        )

    def test_correction_missing_or_outranked_is_contradicted(self) -> None:
        responses = passing_responses()
        responses[(CANDIDATE.checkpoint_ref, "correction")] = (
            RetrievedItem("memory:old", 1),
        )
        missing = assess(FakeRetriever(responses))
        self.assertIs(BehavioralResult.CONTRADICTED, missing.result)
        self.assertEqual(
            ("corrected_memory_missing",),
            missing.probe_results[0].reason_codes,
        )

        responses = passing_responses()
        responses[(CANDIDATE.checkpoint_ref, "correction")] = (
            RetrievedItem("memory:old", 1),
            RetrievedItem("memory:new", 2),
        )
        outranked = assess(FakeRetriever(responses))
        self.assertIs(BehavioralResult.CONTRADICTED, outranked.result)
        self.assertEqual(
            ("superseded_memory_outranks_correction",),
            outranked.probe_results[0].reason_codes,
        )

    def test_anchor_loss_rank_regression_and_missing_baseline_are_distinct(self) -> None:
        responses = passing_responses()
        responses[(CANDIDATE.checkpoint_ref, "anchor-after")] = ()
        missing = assess(FakeRetriever(responses))
        self.assertIs(BehavioralResult.CONTRADICTED, missing.result)
        self.assertIn("anchor_missing_after_transition", missing.probe_results[1].reason_codes)

        responses = passing_responses()
        responses[(CANDIDATE.checkpoint_ref, "anchor-after")] = (
            RetrievedItem("memory:anchor", 3),
        )
        regressed = assess(FakeRetriever(responses))
        self.assertIs(BehavioralResult.CONTRADICTED, regressed.result)
        self.assertIn("anchor_rank_regressed", regressed.probe_results[1].reason_codes)

        responses = passing_responses()
        responses[(BASELINE.checkpoint_ref, "anchor-before")] = ()
        inconclusive = assess(FakeRetriever(responses))
        self.assertIs(BehavioralResult.INCONCLUSIVE, inconclusive.result)
        self.assertEqual(
            ("baseline_anchor_missing",),
            inconclusive.probe_results[1].reason_codes,
        )

    def test_scope_isolation_detects_forbidden_scope(self) -> None:
        responses = passing_responses(
            (RetrievedItem("memory:foreign", 1, scope_refs=("tenant:other",)),)
        )
        assessment = assess(FakeRetriever(responses))
        self.assertIs(BehavioralResult.CONTRADICTED, assessment.result)
        self.assertEqual(
            ("forbidden_scope_retrieved",),
            assessment.probe_results[2].reason_codes,
        )

    def test_empty_scope_result_proves_only_negative_isolation_property(self) -> None:
        assessment = assess(FakeRetriever(passing_responses(scope_items=())))
        scope = assessment.probe_results[2]
        self.assertIs(BehavioralResult.VERIFIED, scope.result)
        self.assertEqual(("no_forbidden_retrieval_observed",), scope.reason_codes)
        self.assertIs(BehavioralResult.VERIFIED, assessment.result)

    def test_state_conditioned_retrieval_collapse_is_contradicted(self) -> None:
        responses = passing_responses()
        same = (
            RetrievedItem("memory:before", 1),
            RetrievedItem("memory:after", 2),
        )
        responses[(BASELINE.checkpoint_ref, "state-before")] = same
        responses[(CANDIDATE.checkpoint_ref, "state-after")] = same
        assessment = assess(FakeRetriever(responses))
        self.assertIs(BehavioralResult.CONTRADICTED, assessment.result)
        self.assertEqual(
            ("retrieval_state_collapsed",),
            assessment.probe_results[3].reason_codes,
        )

    def test_invalid_differentiation_probe_rejects_same_context(self) -> None:
        with self.assertRaisesRegex(ValueError, "distinct contexts"):
            ProbeDefinition(
                probe_id="bad",
                kind=ProbeKind.STATE_CONDITIONED_DIFFERENTIATION,
                baseline_request=request("before", "context:same"),
                candidate_request=request("after", "context:same"),
                expected_baseline_refs=("memory:before",),
                expected_candidate_refs=("memory:after",),
            )

    def test_duplicate_probe_ids_and_retrieved_items_are_rejected(self) -> None:
        probe = ProbeDefinition(
            probe_id="same",
            kind=ProbeKind.SCOPE_ISOLATION,
            candidate_request=request("scope"),
            forbidden_refs=("memory:foreign",),
        )
        with self.assertRaisesRegex(ValueError, "probe IDs must be unique"):
            ProbeSuite("suite:x", "1", (probe, probe))

        responses = passing_responses()
        responses[(CANDIDATE.checkpoint_ref, "scope")] = (
            RetrievedItem("memory:dup", 1),
            RetrievedItem("memory:dup", 2),
        )
        with self.assertRaisesRegex(ValueError, "duplicate retrieved logical_ref"):
            assess(FakeRetriever(responses))

    def test_checkpoint_state_change_aborts_artifact_construction(self) -> None:
        class ChangingRetriever(FakeRetriever):
            def state_digest(self, checkpoint_ref):
                if checkpoint_ref == CANDIDATE.checkpoint_ref and self.calls:
                    return "sha256:changed"
                return super().state_digest(checkpoint_ref)

        with self.assertRaisesRegex(AssessmentStateChanged, "changed during assessment"):
            assess(ChangingRetriever(passing_responses()))

    def test_bound_precondition_mismatch_aborts_before_probes(self) -> None:
        retriever = FakeRetriever(
            passing_responses(),
            states={
                BASELINE.checkpoint_ref: BASELINE.state_digest,
                CANDIDATE.checkpoint_ref: "sha256:not-candidate",
            },
        )
        with self.assertRaisesRegex(AssessmentStateChanged, "bound precondition"):
            assess(retriever)
        self.assertEqual(0, retriever.calls)

    def test_unavailable_required_probe_is_inconclusive(self) -> None:
        responses = passing_responses()
        responses[(CANDIDATE.checkpoint_ref, "scope")] = RetrieverUnavailable("down")
        assessment = assess(FakeRetriever(responses))
        self.assertIs(BehavioralResult.INCONCLUSIVE, assessment.result)
        self.assertIs(EvidencePosture.UNAVAILABLE, assessment.posture)
        self.assertIs(BehavioralResult.INCONCLUSIVE, assessment.probe_results[2].result)
        self.assertIs(EvidencePosture.UNAVAILABLE, assessment.probe_results[2].posture)

    def test_non_required_failure_stays_visible_without_changing_aggregate(self) -> None:
        responses = passing_responses(
            (RetrievedItem("memory:foreign", 1, scope_refs=("tenant:other",)),)
        )
        assessment = assess(FakeRetriever(responses), suite(required_scope=False))
        self.assertIs(BehavioralResult.VERIFIED, assessment.result)
        self.assertIs(BehavioralResult.CONTRADICTED, assessment.probe_results[2].result)

    def test_exact_verified_assessment_satisfies_requirement_only(self) -> None:
        assessment = assess(FakeRetriever(passing_responses()))
        result = evaluate_assessment_requirement(
            requirement(assessment),
            (assessment,),
            evaluated_at="2026-08-30T16:30:00Z",
        )
        self.assertEqual("satisfied", result.status)
        self.assertEqual(("applicable_behavior_verified",), result.reason_codes)
        self.assertEqual("none", result.authority_effect)

    def test_wrong_binding_or_time_never_satisfies_requirement(self) -> None:
        assessment = assess(FakeRetriever(passing_responses()))
        cases = (
            requirement(
                assessment,
                candidate=CheckpointBinding("checkpoint:other", "sha256:other"),
            ),
            requirement(assessment, probe_suite_digest="sha256:wrong-suite"),
            requirement(assessment, retriever_profile_digest="sha256:wrong-profile"),
            requirement(assessment, not_before="2026-08-30T16:30:00Z"),
            requirement(assessment, not_after="2026-08-30T16:00:05Z"),
        )
        for case in cases:
            result = evaluate_assessment_requirement(
                case,
                (assessment,),
                evaluated_at="2026-08-30T16:30:00Z",
            )
            self.assertEqual("not_satisfied", result.status)
            self.assertEqual(("no_applicable_assessment",), result.reason_codes)

    def test_applicable_contradiction_dominates_verified_result(self) -> None:
        verified = assess(FakeRetriever(passing_responses()))
        responses = passing_responses()
        responses[(CANDIDATE.checkpoint_ref, "correction")] = (
            RetrievedItem("memory:old", 1),
        )
        contradicted = assess(FakeRetriever(responses))
        result = evaluate_assessment_requirement(
            requirement(verified),
            (verified, contradicted),
            evaluated_at="2026-08-30T16:30:00Z",
        )
        self.assertEqual("not_satisfied", result.status)
        self.assertEqual(("applicable_contradiction",), result.reason_codes)
        self.assertEqual(2, len(result.applicable_assessment_ids))

    def test_remediation_can_be_current_without_erasing_historical_failure(self) -> None:
        bad_responses = passing_responses()
        bad_responses[(CANDIDATE.checkpoint_ref, "correction")] = (
            RetrievedItem("memory:old", 1),
        )
        historical_failure = assess(FakeRetriever(bad_responses))

        remediated_candidate = CheckpointBinding(
            "checkpoint:remediated",
            "sha256:remediated",
        )
        responses = {
            (
                key
                if key[0] != CANDIDATE.checkpoint_ref
                else (remediated_candidate.checkpoint_ref, key[1])
            ): value
            for key, value in passing_responses().items()
        }
        retriever = FakeRetriever(
            responses,
            states={
                BASELINE.checkpoint_ref: BASELINE.state_digest,
                remediated_candidate.checkpoint_ref: remediated_candidate.state_digest,
            },
        )
        remediation = assess_checkpoint_transition(
            baseline=BASELINE,
            candidate=remediated_candidate,
            suite=suite(),
            retriever=retriever,
            started_at=NOW,
            completed_at=DONE,
        )
        current_requirement = AssessmentRequirement(
            requirement_ref="requirement:remediated",
            baseline=BASELINE,
            candidate=remediated_candidate,
            probe_suite_digest=remediation.probe_suite_digest,
            retriever_profile_digest=remediation.retriever_profile_digest,
        )
        result = evaluate_assessment_requirement(
            current_requirement,
            (historical_failure, remediation),
            evaluated_at="2026-08-30T16:30:00Z",
        )
        self.assertIs(BehavioralResult.CONTRADICTED, historical_failure.result)
        self.assertIs(BehavioralResult.VERIFIED, remediation.result)
        self.assertEqual("satisfied", result.status)
        self.assertEqual((remediation.assessment_id,), result.applicable_assessment_ids)


if __name__ == "__main__":
    unittest.main()
