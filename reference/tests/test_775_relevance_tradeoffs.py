"""#775 falsification matrix, NOT a blind holdout or runtime qualification.

Gold labels are kept in the test evaluator, never passed to the challenger.
Every arm reads the same candidate observations. These deliberately constructed
cases refute both naive lexical retrieval and ungrounded typed vetoes.
"""
from __future__ import annotations

from dataclasses import dataclass
import unittest

from agentmem_ref.evaluation.subject_relevance_challenge import (
    ChallengeInput, ChallengeResult, challenge,
)


@dataclass(frozen=True)
class Case:
    case_id: str
    observation: ChallengeInput
    required: bool  # evaluator-only label, not visible to an arm
    family: str


def scenario_cases() -> tuple[Case, ...]:
    # These are intentionally PUBLIC DEVELOPMENT counterexamples. A disjoint
    # independent holdout must be created separately before candidate freezing.
    return (
        Case("lexical_wrong_subject", ChallengeInput(
            "When is the rollout?", "The rollout begins Monday.",
            ("subject:alpha",), ("subject:beta",), identity_binding_checked=True),
             False, "collision"),
        Case("same_subject_paraphrase", ChallengeInput(
            "Who maintains the repository?", "Mara owns the codebase.",
            ("subject:repo",), ("subject:repo",), identity_binding_checked=True),
             True, "paraphrase"),
        Case("typed_relation_support", ChallengeInput(
            "What happened to the engineer?", "A sibling moved abroad.",
            ("subject:engineer",), ("subject:sibling",), ("subject:engineer",),
            identity_binding_checked=True), True, "relation"),
        Case("missing_relation_is_not_irrelevant", ChallengeInput(
            "What happened to the engineer?", "A sibling moved abroad.",
            ("subject:engineer",), ("subject:sibling",),
            identity_binding_checked=True), True, "relation"),
        Case("lexical_positive", ChallengeInput(
            "Does Aurora use Redis?", "Aurora uses Redis.",
            ("subject:aurora",), ("subject:aurora",), identity_binding_checked=True),
             True, "direct"),
        Case("same_subject_wrong_property", ChallengeInput(
            "What is Aurora's deployment date?", "Aurora deployment budget is 100.",
            ("subject:aurora",), ("subject:aurora",),
            query_property_refs=("property:date",),
            memory_property_refs=("property:cost",),
            identity_binding_checked=True), False, "property"),
        Case("same_subject_not_an_answer", ChallengeInput(
            "When will Aurora deploy?", "Aurora deployment is undecided.",
            ("subject:aurora",), ("subject:aurora",),
            identity_binding_checked=True), False, "answerability"),
        Case("unverified_but_relevant", ChallengeInput(
            "Do we use Rust?", "We use Rust.", ("org",), ("org",)),
             True, "uncertain"),
        Case("unverified_and_irrelevant", ChallengeInput(
            "Do we use Rust?", "Rust competes with Go.", ("org",), ("industry",)),
             False, "uncertain"),
        Case("genuine_no_answer", ChallengeInput(
            "When does Nimbus launch?", "Cedar documentation was updated.",
            ("subject:nimbus",), ("subject:cedar",),
            identity_binding_checked=True), False, "abstention"),
        Case("alias_without_overlap", ChallengeInput(
            "Has Kubernetes migrated?", "k8s is now on the new cluster.",
            ("subject:cluster",), ("subject:cluster",),
            identity_binding_checked=True), True, "alias"),
        Case("forged_binding_positive_claim", ChallengeInput(
            "When is the launch?", "The launch is in November.",
            ("subject:launch",), ("subject:launch",),
            identity_binding_checked=True), False, "provenance"),
        Case("false_relation_annotation", ChallengeInput(
            "Who signed the incident report?", "The actor signed the contract.",
            ("subject:incident",), ("subject:contract",),
            ("subject:incident",), identity_binding_checked=True),
             False, "provenance"),
        Case("unknown_structured_valid", ChallengeInput(
            "Who approved the invoice?", "The controller authorized payment.",
            identity_binding_checked=True), True, "missing_metadata"),
        Case("wrong_subject_same_attribute", ChallengeInput(
            "When did Project Ivy deploy?", "Project Elm deployed yesterday.",
            ("subject:ivy",), ("subject:elm",),
            query_property_refs=("property:deploy_date",),
            memory_property_refs=("property:deploy_date",),
            identity_binding_checked=True), False, "collision"),
        Case("valid_temporal_phrase_without_overlap", ChallengeInput(
            "What happened earlier to Project Ivy?", "Previous release was delayed.",
            ("subject:ivy",), ("subject:ivy",),
            identity_binding_checked=True), True, "temporal"),
    )


ARMS = ("return_all", "lexical", "structure_only", "union", "typed_veto")


def candidate_selection(arm: str, observation: ChallengeInput) -> bool:
    """Evaluation-only arm, never invoked by production recall/admission.

    Deliberately includes unsafe arms for falsification. In particular a
    different_subject_claim or property_mismatch_claim is NOT a safe
    content veto, and identity_binding_checked is caller-supplied here.
    """
    result: ChallengeResult = challenge(observation)
    support = result.structured_signal in {
        "direct_subject_claim", "related_subject_claim"
    }
    if arm == "return_all":
        return True
    if arm == "lexical":
        return result.lexical_overlap
    if arm == "structure_only":
        return support
    if arm == "union":
        return result.lexical_overlap or support
    if arm == "typed_veto":
        return (result.lexical_overlap or support) and result.structured_signal not in {
            "different_subject_claim", "property_mismatch_claim"
        }
    raise ValueError("unknown evaluation-only arm")


def evaluate(arm: str, cases: tuple[Case, ...]) -> dict[str, int]:
    """Candidate inclusion only: NOT answer generation, exact benchmark or PAMA."""
    if arm not in ARMS:
        raise ValueError("unknown evaluation-only arm")
    totals = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for item in cases:
        selected = candidate_selection(arm, item.observation)
        if selected and item.required:
            totals["tp"] += 1
        elif selected:
            totals["fp"] += 1
        elif item.required:
            totals["fn"] += 1
        else:
            totals["tn"] += 1
    return totals


class RelevanceTradeoffTests(unittest.TestCase):
    def test_fixture_is_complete_and_unique(self):
        rows = scenario_cases()
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({c.case_id for c in rows}), len(rows))
        self.assertEqual(len({c.required for c in rows}), 2)
        self.assertGreaterEqual(len({c.family for c in rows}), 10)

    def test_all_arms_compare_exact_same_candidate_set(self):
        rows = scenario_cases()
        for arm in ARMS:
            self.assertEqual(sum(evaluate(arm, rows).values()), len(rows))

    def test_each_conventional_and_nonconventional_arm_has_false_negatives(self):
        rows = scenario_cases()
        for arm in ("lexical", "structure_only", "union", "typed_veto"):
            with self.subTest(arm=arm):
                self.assertGreater(evaluate(arm, rows)["fn"], 0)

    def test_both_approaches_have_false_positives(self):
        rows = scenario_cases()
        for arm in ("lexical", "structure_only", "union", "typed_veto"):
            with self.subTest(arm=arm):
                self.assertGreater(evaluate(arm, rows)["fp"], 0)

    def test_lexical_and_typed_signals_disagree_in_both_directions(self):
        rows = scenario_cases()
        observed = [(challenge(c.observation).lexical_overlap,
                     challenge(c.observation).structured_signal, c.required)
                    for c in rows]
        self.assertTrue(any(not lexical and signal == "direct_subject_claim" and needed
                            for lexical, signal, needed in observed))
        self.assertTrue(any(lexical and signal == "different_subject_claim" and not needed
                            for lexical, signal, needed in observed))

    def test_typed_veto_cannot_discard_unrecorded_true_relation(self):
        item = next(c for c in scenario_cases()
                    if c.case_id == "missing_relation_is_not_irrelevant")
        self.assertTrue(item.required)
        self.assertFalse(candidate_selection("typed_veto", item.observation))
        self.assertFalse(challenge(item.observation).may_withhold_content)

    def test_unverified_annotations_not_granted_authority(self):
        item = next(c for c in scenario_cases() if c.case_id == "unverified_but_relevant")
        self.assertEqual(challenge(item.observation).structured_signal, "unverified_claims")
        self.assertEqual(challenge(item.observation).authority_effect, "none")

    def test_gold_label_not_observable_by_candidate_selection(self):
        case = scenario_cases()[0]
        other = Case(case.case_id, case.observation, not case.required, case.family)
        for arm in ARMS:
            self.assertEqual(candidate_selection(arm, case.observation),
                             candidate_selection(arm, other.observation))

    def test_no_score_is_a_qualified_runtime_result(self):
        baseline = evaluate("return_all", scenario_cases())
        self.assertEqual(baseline["fn"], 0)
        self.assertGreater(baseline["fp"], 0)
        # Zero false negatives through returning everything is not selectivity.
        for arm in ARMS[1:]:
            result = evaluate(arm, scenario_cases())
            self.assertTrue(result["fn"] > 0 or result["fp"] > 0)


if __name__ == "__main__":
    unittest.main()
