"""Independent development challenges for Gate 2 selector and answer-scoring integrity.

These are NOT a sealed holdout. They were authored after reading selector
0.5.0 and task_eval.py at 9456708c. Expected RED at that revision.

The tests require a Python environment with agent-memory-reference and the
MCP SDK installed. No runtime, baseline or production files are modified.

Do not add these individual terms/answers to a heuristic stopword list.
Resolve the general inability of lexical absence to prove irrelevance, and
do not advertise substring matching as verified answer correctness.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from agentmem_ref.api import context_selection


HERE = Path(__file__).resolve().parents[1]
task_spec = importlib.util.spec_from_file_location(
    "am_independent_task_eval", HERE / "task_eval.py"
)
assert task_spec and task_spec.loader
task_eval = importlib.util.module_from_spec(task_spec)
task_spec.loader.exec_module(task_eval)

LEXICAL_ONLY = {
    "route_provenance": [{"route_id": "lexical"}],
    "admission_basis": {"currentness": "current_state"},
}


class SelectorParaphraseNonExclusion(unittest.TestCase):
    """A lack of shared English tokens is not evidence a multi-sentence fact is irrelevant."""

    def test_named_third_person_fact_has_implicit_landing_answer(self):
        # aircraft ~ plane; touch down ~ landed. The fact has the exact
        # landing location, even though none of the query's content terms
        # appears literally in either sentence.
        query = "Where did the aircraft touch down?"
        fact = "Captain Nia's plane landed at Orion Field. Her passengers cheered."
        verdict = context_selection.qualify(query, "ref-landing", LEXICAL_ONLY, fact, None)
        self.assertFalse(set(context_selection.content_terms(query)) &
                         set(context_selection.content_terms(fact)))
        self.assertEqual(
            verdict["outcome"], "delivered",
            f"Do not classify paraphrase absence as proved irrelevance: {verdict}"
        )
        self.assertEqual(verdict.get("certainty"), "uncertain")

    def test_named_third_person_fact_has_implicit_heating_answer(self):
        # A conservatory/glasshouse is greenhouse-like, and heating fuel
        # may be described without using the words fuel or heat.
        query = "What fuel warms the glasshouse?"
        fact = "Dr. Isa's conservatory runs on propane. The caretaker checked it yesterday."
        verdict = context_selection.qualify(query, "ref-fuel", LEXICAL_ONLY, fact, None)
        self.assertFalse(set(context_selection.content_terms(query)) &
                         set(context_selection.content_terms(fact)))
        self.assertEqual(
            verdict["outcome"], "delivered",
            f"A third-party possessive is not a semantic irrelevance certificate: {verdict}"
        )
        self.assertEqual(verdict.get("certainty"), "uncertain")

    def test_unavailable_is_not_a_negative_evidence_verdict(self):
        self.assertEqual(
            context_selection.assessment([
                {"outcome": "omitted", "reason": "no_query_term_evidence"},
                {"outcome": "unavailable", "state": "omitted_budget"},
            ]),
            "undetermined",
        )


class AnswerScoreValidity(unittest.TestCase):
    """'Gold substring appears' cannot be promoted to an actual correct answer."""

    def test_explicit_negation_cannot_be_scored_correct(self):
        verdict = task_eval.judge("The aircraft did not land in Oslo.", ["Oslo"])
        self.assertIsNot(
            verdict["correct"], True,
            "The gold phrase is explicitly negated, but a substring judge called it correct."
        )

    def test_gold_word_inside_another_word_cannot_be_scored_correct(self):
        verdict = task_eval.judge("The answer is blueberry.", ["blue"])
        self.assertIsNot(
            verdict["correct"], True,
            "Substring containment is not a word-level match, much less answer correctness."
        )

    def test_missing_answer_is_not_correct_on_answerable_task(self):
        verdict = task_eval.judge(None, ["Orion Field"])
        self.assertFalse(verdict["correct"])
        self.assertTrue(verdict["abstained"])


if __name__ == "__main__":
    unittest.main()
