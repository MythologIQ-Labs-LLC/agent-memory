"""Stage C successor: subject applicability and answerability are separate, then combined.

The offline tests pin the decision logic with a fake classifier. The real-model tests run only
when the host names the pinned answerability model in AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR. Their
questions are the holdout-1 failures (P1, P3, U1, U8, U12) used here for failure analysis and as
regression tests; they are not evidence of generalization.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import answer_support


class NamedSubjectTests(unittest.TestCase):
    def test_capitalised_names_after_the_first_word_are_subjects(self):
        self.assertEqual(answer_support.named_subjects("Where does Imogen keep her kayak?"), {"imogen"})
        self.assertEqual(answer_support.named_subjects("Where is Noor's kayak stored?"), {"noor"})
        self.assertEqual(answer_support.named_subjects("What is the WiFi password for Harbour Library?"),
                         {"wifi", "harbour", "library"})

    def test_question_words_lowercase_nouns_and_the_first_word_name_nothing(self):
        self.assertEqual(answer_support.named_subjects("What day is the dental cleaning?"), frozenset())
        self.assertEqual(answer_support.named_subjects("Which food can I not eat?"), frozenset())
        self.assertEqual(answer_support.named_subjects("Ravi drives which car?"), frozenset())

    def test_grounding_uses_the_runtime_fold_on_both_sides(self):
        self.assertTrue(answer_support.grounded({"noor"}, "Noor keeps her kayak at the boathouse."))
        self.assertTrue(answer_support.grounded({"tuesday"}, "Elena swims on Tuesdays."))
        self.assertTrue(answer_support.grounded(frozenset(), "Anything at all."))
        self.assertFalse(answer_support.grounded({"noor"}, "Tobias stores his kayak in his garage."))
        self.assertFalse(answer_support.grounded({"imogen"}, "Morgan keeps a kayak by the lake."))


class DecisionTests(unittest.TestCase):
    def decide(self, question, texts, answering, joint_answering=False):
        return answer_support.decide(question, texts, answering, joint_answering)

    def test_support_needs_an_applicable_and_answering_item(self):
        texts = ["Noor keeps her kayak at the boathouse.", "Tobias stores his kayak in his garage."]
        out = self.decide("Where is Noor's kayak stored?", texts, [True, True], True)
        self.assertEqual(out["per_item"], [True, False])
        self.assertEqual(out["applicable"], [True, False])
        self.assertEqual(out["answering"], [True, True])
        self.assertTrue(out["joint"])

    def test_an_answering_item_about_another_subject_is_not_support(self):
        texts = ["Noor keeps her kayak at the boathouse.", "Tobias stores his kayak in his garage."]
        out = self.decide("Where does Imogen keep her kayak?", texts, [True, True], True)
        self.assertEqual(out["per_item"], [False, False])
        self.assertFalse(out["joint"])
        self.assertFalse(out["joint_applicable"])

    def test_an_applicable_item_that_does_not_answer_is_not_support(self):
        out = self.decide("What climbing grade can Tobias lead?",
                          ["Tobias goes rock climbing at the Summit Wall gym on Wednesdays."], [False])
        self.assertEqual(out["per_item"], [False])
        self.assertEqual(out["applicable"], [True])

    def test_no_extractable_span_is_needed(self):
        # The decision has no span input at all: an inferential answer counts when the
        # classifier says the text answers the question.
        out = self.decide("Which food can Noor not eat?",
                          ["Noor is allergic to peanuts and carries an epinephrine pen."], [True])
        self.assertEqual(out["per_item"], [True])

    def test_joint_support_needs_every_subject_somewhere_in_the_joint_text(self):
        texts = ["Elena is planning a trip with her sister Marisol.", "Marisol has been vegetarian for years."]
        out = self.decide("Will Elena's companion eat meat?", texts, [False, False], True)
        self.assertEqual(out["per_item"], [False, False])
        self.assertTrue(out["joint_applicable"])
        self.assertTrue(out["joint"])


class PerMemoryDecisionTests(unittest.TestCase):
    """answerability-subject-grounded/1.1.0: support is per memory; joined text never grants it."""

    def decide(self, question, texts, answering, joint_answering=False):
        return answer_support.decide_per_memory(question, texts, answering, joint_answering)

    def test_concatenated_memories_never_grant_support(self):
        texts = ["Marisol is going to Lisbon in May.", "Elena's car is a red Fiat.", "Rent is due on the fifth."]
        out = self.decide("What car does Marisol drive?", texts, [False, True, False], joint_answering=True)
        self.assertEqual(out["per_item"], [False, False, False])
        self.assertFalse(out["joint"])
        self.assertEqual(out["cross_memory_candidates"], [])
        self.assertEqual(out["diagnostics"], {"joint_answering_unadmitted": True})

    def test_subject_in_one_memory_cannot_authorise_an_answer_in_an_unlinked_one(self):
        texts = ["Marisol works at the harbour office.", "The red Fiat is parked on Birch Lane."]
        out = self.decide("What car does Marisol drive?", texts, [False, True])
        self.assertEqual(out["per_item"], [False, False])
        self.assertEqual(out["cross_memory_candidates"], [])

    def test_linked_pair_is_an_unresolved_candidate_with_its_facts_and_link_not_support(self):
        texts = ["Elena is planning a trip to Kyoto with her sister Marisol.",
                 "The rent is due on the fifth.",
                 "Marisol has been vegetarian for ten years."]
        out = self.decide("Will Elena's travel companion eat meat?", texts, [False, False, False])
        self.assertEqual(out["per_item"], [False, False, False])
        self.assertFalse(out["joint"])
        self.assertEqual(out["cross_memory_candidates"],
                         [{"facts": [0, 2], "link_terms": ["marisol"], "relationship": "shared_name_unresolved"}])

    def test_the_question_subject_itself_is_not_a_link(self):
        texts = ["Elena teaches chemistry.", "Elena swims on Tuesdays."]
        out = self.decide("Which car does Elena drive?", texts, [False, False])
        self.assertEqual(out["cross_memory_candidates"], [])

    def test_a_capitalised_sentence_start_is_not_a_name(self):
        texts = ["Rent for the studio is due on the fifth.", "Rent increases are announced in May."]
        self.assertEqual(answer_support.memory_names(texts[0]), frozenset())
        out = self.decide("When is the rent due for Ivo?", ["Ivo rents the studio.", *texts], [False, False, False])
        self.assertEqual(out["cross_memory_candidates"], [])

    def test_no_bridge_starts_without_a_memory_naming_the_subject(self):
        texts = ["Kesh lives with Marisol.", "Marisol has been vegetarian for ten years."]
        out = self.decide("Does Elena's companion eat meat?", texts, [False, False])
        self.assertEqual(out["cross_memory_candidates"], [])

    def test_a_question_that_names_no_one_has_no_subject_to_bridge_from(self):
        texts = ["The shed was repainted by Kesh in May.", "Kesh keeps spare tools in the garage."]
        out = self.decide("Where is the shed key kept?", texts, [False, False])
        self.assertEqual(out["subjects"], [])
        self.assertEqual(out["cross_memory_candidates"], [])

    def test_single_memory_support_still_wins_and_no_candidate_is_formed(self):
        texts = ["Noor is allergic to peanuts.", "Noor's neighbour Kesh waters the plants."]
        out = self.decide("Which food can Noor not eat?", texts, [True, False])
        self.assertEqual(out["per_item"], [True, False])
        self.assertTrue(out["joint"])
        self.assertEqual(out["cross_memory_candidates"], [])

    def test_names_come_from_mid_sentence_capitals_folded(self):
        from agentmem_ref.api.context_selection import content_terms
        self.assertEqual(answer_support.memory_names("Elena is planning a trip to Kyoto with her sister Marisol."),
                         {"kyoto", "marisol"})
        self.assertEqual(answer_support.memory_names("It rained. Then Ines's flight left for Lisbon."),
                         content_terms("Ines Lisbon"))


class MethodSelectionTests(unittest.TestCase):
    def test_answerability_layout_offers_both_versions_and_defaults_to_the_correction(self):
        self.assertEqual(answer_support.methods_for(answer_support.ANSWERABILITY),
                         ("answerability-subject-grounded/1.1.0", "answerability-subject-grounded/1.0.0"))
        self.assertEqual(answer_support.methods_for(answer_support.EXTRACTIVE),
                         ("extractive-qa-null-comparison/1.0.0",))


class FromEnvironmentTests(unittest.TestCase):
    def test_each_pinned_layout_selects_its_own_method(self):
        self.assertEqual({spec.method for spec in answer_support.SPECS},
                         {answer_support.EXTRACTIVE.method, answer_support.ANSWERABILITY.method})
        self.assertNotEqual(set(answer_support.EXTRACTIVE.files), set(answer_support.ANSWERABILITY.files))


def _successor_model() -> bool:
    raw = os.environ.get(answer_support.ENV_DIR, "")
    return bool(raw) and (Path(raw) / "onnx" / "model.onnx").is_file()


@unittest.skipUnless(_successor_model(), "pinned answerability model not provided by the host")
class RealAnswerabilityModelTests(unittest.TestCase):
    checker: answer_support.Answerability

    @classmethod
    def setUpClass(cls):
        cls.checker = answer_support.from_environment()

    def test_method_is_the_corrected_successor_by_default(self):
        if os.environ.get(answer_support.METHOD_ENV):
            self.skipTest("host selected a method explicitly")
        self.assertEqual(self.checker.METHOD, "answerability-subject-grounded/1.1.0")

    def test_cross_memory_answer_is_an_attributed_candidate_not_support(self):
        if self.checker.METHOD != "answerability-subject-grounded/1.1.0":
            self.skipTest("cycle-3 behaviour")
        out = self.checker.check("Will Elena's travel companion eat meat on the Kyoto trip?",
                                 ["Elena is planning a trip to Kyoto in April with her sister Marisol.",
                                  "Marisol has been vegetarian for ten years."])
        self.assertEqual(out["per_item"], [False, False])
        self.assertFalse(out["joint"])
        self.assertEqual([c["facts"] for c in out["cross_memory_candidates"]], [[0, 1]])
        self.assertEqual(out["cross_memory_candidates"][0]["link_terms"], ["marisol"])

    def test_u1_and_p1_hold_under_per_memory_support(self):
        texts = ["Noor keeps her kayak at the Pinecrest boathouse. It is painted yellow.",
                 "Tobias stores his kayak in his garage on Elm Street."]
        self.assertEqual(self.checker.check("Where does Imogen keep her kayak?", texts)["per_item"], [False, False])
        self.assertEqual(self.checker.check("Where is Noor's kayak stored?", texts)["per_item"], [True, False])

    def test_p3_inferential_answer_is_supported(self):
        out = self.checker.check("Which food can Noor not eat?",
                                 ["Noor is allergic to peanuts and carries an epinephrine pen.",
                                  "While Noor is away, her neighbour Kesh waters the balcony plants."])
        self.assertEqual(out["per_item"], [True, False])

    def test_u12_related_fact_of_the_wrong_kind_is_not_support(self):
        out = self.checker.check("What climbing grade can Tobias lead?",
                                 ["Tobias goes rock climbing at the Summit Wall gym on Wednesdays.",
                                  "Tobias is employed as a structural engineer at Calder Bridgeworks."])
        self.assertEqual(out["per_item"], [False, False])
        self.assertFalse(out["joint"])

    def test_u1_absent_subject_is_not_supported_by_other_peoples_memories(self):
        out = self.checker.check("Where does Imogen keep her kayak?",
                                 ["Noor keeps her kayak at the Pinecrest boathouse. It is painted yellow.",
                                  "Tobias stores his kayak in his garage on Elm Street."])
        self.assertEqual(out["answering"], [True, True])
        self.assertEqual(out["per_item"], [False, False])
        self.assertFalse(out["joint"])

    def test_p1_support_is_attributed_only_to_the_named_subjects_memory(self):
        out = self.checker.check("Where is Noor's kayak stored?",
                                 ["Noor keeps her kayak at the Pinecrest boathouse. It is painted yellow.",
                                  "Tobias stores his kayak in his garage on Elm Street."])
        self.assertEqual(out["per_item"], [True, False])

    @unittest.expectedFailure
    def test_u8_known_failure_a_date_is_accepted_for_a_time_question(self):
        # Answer type is not checked separately: the classifier judges that a sentence giving the
        # flight's date answers a question about its departure time. Kept red on purpose.
        out = self.checker.check("What time does Ines's flight to Lisbon depart?",
                                 ["Ines flies to Lisbon on the 14th for the architecture conference."])
        self.assertEqual(out["per_item"], [False])


if __name__ == "__main__":
    unittest.main()
