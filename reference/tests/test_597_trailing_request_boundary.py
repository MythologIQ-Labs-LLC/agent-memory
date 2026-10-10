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

    def test_non_question_request_without_question_mark(self):
        self.assert_same_principal(
            "I prefer green tea",
            "I prefer green tea, please suggest a recipe",
        )

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
