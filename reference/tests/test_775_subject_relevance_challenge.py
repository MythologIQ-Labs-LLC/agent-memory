"""#775 anti-overfitting controls: overlap, identity and relationships can mislead."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from agentmem_ref.evaluation.subject_relevance_challenge import ChallengeInput, challenge


class SubjectRelevanceChallengeTests(unittest.TestCase):
    def test_wrong_subject_same_lexical_content(self):
        item = ChallengeInput("When is the rollout?", "The rollout begins Monday.",
            ("subject:alpha",), ("subject:beta",), identity_binding_checked=True)
        result = challenge(item)
        self.assertTrue(result.lexical_overlap)
        self.assertEqual(result.structured_signal, "different_subject_claim")
        self.assertTrue(result.disagrees_with_lexical_control)
        self.assertFalse(result.may_withhold_content)

    def test_valid_paraphrase_low_literal_overlap(self):
        item = ChallengeInput("Who maintains the repository?", "Mara owns the codebase.",
            ("subject:repo",), ("subject:repo",), identity_binding_checked=True)
        result = challenge(item)
        self.assertFalse(result.lexical_overlap)
        self.assertEqual(result.structured_signal, "direct_subject_claim")
        self.assertTrue(result.disagrees_with_lexical_control)

    def test_implicit_relation_can_preserve_needed_evidence(self):
        item = ChallengeInput("What happened to the engineer?", "A sibling moved abroad.",
            ("subject:engineer",), ("subject:sibling",), ("subject:engineer",),
            identity_binding_checked=True)
        result = challenge(item)
        self.assertFalse(result.lexical_overlap)
        self.assertEqual(result.structured_signal, "related_subject_claim")
        self.assertFalse(result.may_withhold_content)

    def test_unverified_identity_annotations_have_no_positive_status(self):
        item = ChallengeInput("X", "X", ("x",), ("x",), identity_binding_checked=False)
        self.assertEqual(challenge(item).structured_signal, "unverified_claims")

    def test_no_typed_data_is_unknown_not_irrelevant(self):
        self.assertEqual(challenge(ChallengeInput("renewal date", "contract end" ,
            identity_binding_checked=True)).structured_signal, "unknown")

    def test_subject_match_wrong_property_not_assumed_answer(self):
        item = ChallengeInput("deployment schedule", "deployment budget",
            ("subject:service",), ("subject:service",),
            query_property_refs=("property:date",),
            memory_property_refs=("property:cost",), identity_binding_checked=True)
        self.assertEqual(challenge(item).structured_signal, "property_mismatch_claim")

    def test_related_but_unrecorded_relation_cannot_be_automatic_negative(self):
        item = ChallengeInput("Why did Alex leave?", "Their manager changed the policy.",
            ("subject:alex",), ("subject:manager",), identity_binding_checked=True)
        result = challenge(item)
        self.assertEqual(result.structured_signal, "different_subject_claim")
        self.assertFalse(result.may_withhold_content)

    def test_typed_subject_claim_is_not_proof_of_answer_sufficiency(self):
        item = ChallengeInput("Is the service safe?", "Service X was once deemed safe.",
            ("x",), ("x",), identity_binding_checked=True)
        result = challenge(item)
        self.assertEqual(result.structured_signal, "direct_subject_claim")
        self.assertEqual(result.authority_effect, "none")
        self.assertFalse(result.may_withhold_content)

    def test_deterministic_and_immutable(self):
        item = ChallengeInput("Alice's role", "Her employment", ("a",), ("a",),
            identity_binding_checked=True)
        self.assertEqual(challenge(item), challenge(item))
        with self.assertRaises(FrozenInstanceError):
            challenge(item).may_withhold_content = True


if __name__ == "__main__":
    unittest.main()
