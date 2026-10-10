"""#597: independent mixed-declaration/request boundary falsification.

Fresh generic utterances, not derived from the #594 accepted gold. A question or
imperative attached to an asserted memory is not part of its proposition value.
"""
import unittest

from agentmem_ref.runtime.proposition_semantics import interpret_write


class TrailingRequestBoundaryTests(unittest.TestCase):
    def assert_same_principal(self, base, compound):
        simple = interpret_write(base)["proposition"]
        mixed = interpret_write(compound)["proposition"]
        self.assertEqual(simple["status"], "known", simple)
        self.assertEqual(mixed, simple, (base, compound, mixed))

    def test_comma_attached_auxiliary_question_not_in_value(self):
        self.assert_same_principal(
            "I prefer green tea",
            "I prefer green tea, can you recommend a book?",
        )
        self.assert_same_principal(
            "I prefer green tea",
            "I prefer green tea, could you suggest a recipe?",
        )

    def test_conjoined_request_does_not_create_second_slot(self):
        self.assert_same_principal(
            "I prefer green tea",
            "I prefer green tea, and could you suggest a recipe?",
        )

    def test_unpunctuated_conjunction_opens_a_request(self):
        self.assert_same_principal(
            "I prefer green tea",
            "I prefer green tea and can you suggest an infusion?",
        )

    def test_quoted_question_is_not_a_request_boundary(self):
        self.assert_same_principal(
            'I enjoy the song "Hello, can you hear me?"',
            'I enjoy the song "Hello, can you hear me?"',
        )
        out = interpret_write('I enjoy the song "Hello, can you hear me?"')["proposition"]
        self.assertEqual(out["status"], "known", out)
        self.assertIn("can you hear me", out["value"])

    def test_single_quoted_question_stays_within_asserted_title(self):
        text = "I enjoy the song 'Hello, can you hear me?'"
        proposition = interpret_write(text)["proposition"]
        self.assertEqual(proposition["status"], "known", proposition)
        self.assertIn("can you hear me", proposition["value"])

    def test_curly_quoted_question_stays_within_asserted_title(self):
        text = "I enjoy the song ‘Hello, could you hear me?’"
        proposition = interpret_write(text)["proposition"]
        self.assertEqual(proposition["status"], "known", proposition)
        self.assertIn("could you hear me", proposition["value"])

    def test_parenthesized_question_verb_does_not_truncate_literal_value(self):
        base = "I enjoy the phrase (and can you imagine that)"
        self.assert_same_principal(
            base,
            base + ", can you recommend a book?",
        )

    def test_bracketed_question_verb_does_not_truncate_literal_value(self):
        base = "I enjoy the heading [and could you possibly help]"
        self.assert_same_principal(
            base,
            base + ", could you suggest a title?",
        )

    def test_braced_request_like_code_does_not_open_request(self):
        base = "I prefer the template {and can you improve this}"
        self.assert_same_principal(
            base,
            base + ", can you recommend another template?",
        )

    def test_conjoined_assertion_words_inside_literal_not_split(self):
        base = 'I enjoy the phrase "and I like that"'
        self.assert_same_principal(base, base + ", can you explain it?")

    def test_conjoined_assertion_words_inside_parentheses_not_split(self):
        base = "I enjoy the motto (and I mean it)"
        self.assert_same_principal(base, base + ", could you propose a variation?")

    def test_question_punctuation_inside_quoted_value_not_sentence_split(self):
        text = 'I enjoy the line "Can you stay? I can stay"'
        result = interpret_write(text)["proposition"]
        self.assertEqual(result["status"], "known", result)
        self.assertIn("i can stay", result["value"])

    def test_semicolon_inside_parenthesized_value_not_clause_split(self):
        text = "I enjoy the aside (I asked; can you reply?)"
        result = interpret_write(text)["proposition"]
        self.assertEqual(result["status"], "known", result)
        self.assertIn("can you reply", result["value"])

    def test_colon_inside_quoted_value_not_clause_split(self):
        text = 'I enjoy the label "Tag: can you help?"'
        result = interpret_write(text)["proposition"]
        self.assertEqual(result["status"], "known", result)
        self.assertIn("can you help", result["value"])

    def test_top_level_semicolon_still_separates_distinct_assertions(self):
        text = "I prefer green tea; I enjoy strong coffee"
        result = interpret_write(text)["proposition"]
        self.assertEqual(result["status"], "ambiguous", result)

    def test_contraction_before_genuine_request_boundary(self):
        self.assert_same_principal(
            "I'm fond of black tea",
            "I'm fond of black tea, can you suggest an alternative?",
        )

    def test_followup_request_in_separate_sentence(self):
        self.assert_same_principal(
            "I prefer green tea",
            "I prefer green tea. Can you suggest an infusion?",
        )

    def test_non_question_request_without_question_mark(self):
        self.assert_same_principal(
            "I prefer green tea",
            "I prefer green tea, please suggest a recipe",
        )

    def test_capitalized_first_person_conjunction_keeps_two_assertions(self):
        result = interpret_write("I prefer green tea and I enjoy strong coffee")["proposition"]
        self.assertEqual(result["status"], "ambiguous", result)

    def test_two_actual_assertions_not_silently_reduced_to_one(self):
        result = interpret_write("I prefer green tea, and I like strong coffee")["proposition"]
        self.assertEqual(result["status"], "ambiguous", result)

    def test_standalone_question_is_not_an_assertion(self):
        result = interpret_write("Could you recommend green tea?")["proposition"]
        self.assertNotEqual(result["status"], "known", result)

    def test_repeated_runs_are_identical(self):
        text = "My notebook is blue, can you list stationery stores?"
        first = interpret_write(text)
        self.assertEqual(first, interpret_write(text))
        self.assertEqual(first["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
