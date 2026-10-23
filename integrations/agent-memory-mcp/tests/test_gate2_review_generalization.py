"""Generalization checks for the three defects of review 5628673295 (PR #843).

The review's seven controls (``test_gate2_independent_adversarial.py``) pin its own examples. These
check that the repairs are general: fresh vocabulary that appears in no review test, cohort or
fixture, and the same three properties.

1. Lexical absence is not evidence of irrelevance, for a **single statement** as much as for a
   multi-statement fact: a one-sentence paraphrase shares no content term and still answers. A
   conflict of named subjects stays a grounded exclusion (it is an observation, not an absence).
2. The answer verdict reports a defensible strict measure (SQuAD 1.1 normalised exact match and
   token F1) next to the gold-phrase proxy, and the proxy is never the only "correct".
3. Full-evidence credit has exactly one contract: the scorer cannot be called without saying which
   keys were fully delivered, and both harnesses derive them with the same function.
"""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import unittest

from agentmem_ref.api import context_selection


HERE = Path(__file__).resolve().parents[1]


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


task_eval = _load("am_generalization_task_eval", "task_eval.py")
quality = _load("am_generalization_quality_probe", "quality_probe.py")

LEXICAL_ONLY = {
    "route_provenance": [{"route_id": "lexical"}],
    "admission_basis": {"currentness": "current_state"},
}


def _verdict(query: str, text: str) -> dict:
    return context_selection.qualify(query, "ref", LEXICAL_ONLY, text, None)


KNOWN_RED = (
    "Known defect at selector 0.5.1, kept RED on purpose: a single statement sharing no content "
    "term with the query is still declined as grounded (absence_grounding single_statement). "
    "Withdrawing that rule here would break the owner's control "
    "test_819_served_context_quality_contract::test_no_safe_answer_does_not_serve_distractors_as_"
    "an_answer, which must not be weakened; both hold only if function-word-only candidates are "
    "not admitted. That is the bounded admission candidate, not this PR."
)


class SingleStatementParaphrase(unittest.TestCase):
    """A one-sentence fact sharing no content term with the query may still be the answer.

    Expected failures on the PR branch (``KNOWN_RED``); repaired here by selector 0.5.2, which this
    experiment pairs with content-term admission so the owner's no-safe-answer control still holds."""

    CASES = [
        # third person, named subject on the fact side only
        ("Who repaired the bicycle?", "Mechanic Oren fixed Tamsin's bike."),
        # first person
        ("Where is my automobile parked?", "I left the car in bay nine."),
        # no names on either side
        ("What time does the ferry depart?", "Boats to the island leave at noon."),
    ]

    def test_no_shared_term_single_statement_is_delivered_uncertain(self):
        for query, text in self.CASES:
            with self.subTest(query=query):
                self.assertFalse(set(context_selection.content_terms(query)) &
                                 set(context_selection.content_terms(text)))
                verdict = _verdict(query, text)
                self.assertEqual(verdict["outcome"], "delivered", verdict)
                self.assertEqual(verdict.get("certainty"), "uncertain", verdict)

    def test_no_returned_fact_is_declined_on_lexical_absence_alone(self):
        for query, text in self.CASES:
            with self.subTest(query=query):
                self.assertNotEqual(_verdict(query, text).get("reason"), "no_query_term_evidence")


class GroundedExclusionsStay(unittest.TestCase):
    """The repair must not deliver what is excluded on an observation rather than an absence."""

    def test_conflicting_named_subject_with_a_shared_term_is_still_declined(self):
        verdict = _verdict("What colour is Odile's umbrella?", "Bastien's umbrella is yellow.")
        self.assertEqual((verdict["outcome"], verdict.get("reason")), ("omitted", "subject_mismatch"))

    def test_conflicting_named_subject_without_a_shared_term_is_still_declined(self):
        verdict = _verdict("Where did Odile's aircraft touch down?",
                           "Captain Bastien's plane landed at Vesper Strip. The crew rested.")
        self.assertEqual((verdict["outcome"], verdict.get("reason")), ("omitted", "subject_mismatch"))

    def test_query_with_only_function_words_matched_still_has_no_negative_certificate(self):
        self.assertEqual(
            context_selection.assessment([{"outcome": "delivered", "certainty": "uncertain"}]),
            "undetermined",
        )


class StrictAnswerMeasure(unittest.TestCase):
    """The verdict carries a standard strict measure; the phrase proxy is reported separately."""

    def test_hedged_answer_is_not_an_exact_match(self):
        verdict = task_eval.judge("Vesper Strip or Halden Field", ["Vesper Strip"])
        self.assertFalse(verdict["exact_match"])
        self.assertLess(verdict["token_f1"], 1.0)

    def test_wrong_location_mentioning_the_gold_is_not_an_exact_match(self):
        verdict = task_eval.judge("Halden Field, after leaving Vesper Strip", ["Vesper Strip"])
        self.assertFalse(verdict["exact_match"])

    def test_article_and_punctuation_normalisation_follow_squad(self):
        verdict = task_eval.judge("The Vesper Strip.", ["vesper strip"])
        self.assertTrue(verdict["exact_match"])
        self.assertEqual(verdict["token_f1"], 1.0)

    def test_partial_span_gets_partial_f1(self):
        verdict = task_eval.judge("by a kerosene stove", ["kerosene"])
        self.assertFalse(verdict["exact_match"])
        self.assertGreater(verdict["token_f1"], 0.0)
        self.assertLess(verdict["token_f1"], 1.0)

    def test_aggregate_reports_strict_and_proxy_side_by_side(self):
        rows = [{"mcp": {"verdict": task_eval.judge("kerosene", ["kerosene"]), "elapsed_ms": 1.0,
                         "delivered_chars": 1, "evidence": quality.score(["a"], ["a"], [], fully_delivered_keys=["a"])}},
                {"mcp": {"verdict": task_eval.judge("by a kerosene stove", ["kerosene"]), "elapsed_ms": 1.0,
                         "delivered_chars": 1, "evidence": quality.score(["a"], ["a"], [], fully_delivered_keys=["a"])}}]
        summary = task_eval.aggregate(rows, "mcp")
        self.assertEqual(summary["answerable_exact_match"], 1)
        self.assertEqual(summary["answerable_gold_phrase_match"], 2)
        self.assertIn("answerable_mean_token_f1", summary)


class OneFullDeliveryContract(unittest.TestCase):
    def test_scorer_requires_the_fully_delivered_keys(self):
        with self.assertRaises(TypeError):
            quality.score(["memory:a"], ["memory:a"], [])

    def test_both_harnesses_use_the_same_full_delivery_function(self):
        # Each harness loads quality_probe by path, so compare what the run loops call, not objects.
        for module, call in ((task_eval, "quality.fully_delivered_keys(evidence, by_key)"),
                             (quality, "fully_delivered_keys(evidence, by_key)")):
            with self.subTest(module=module.__name__):
                source = inspect.getsource(module.run)
                self.assertIn(call, source)
                self.assertNotIn('"resolved"', source, "a second, private copy of the contract")

    def test_full_delivery_requires_resolved_state_exact_text_and_attribution(self):
        seeded = {"memory:a": "Kerosene heats the shed.", "memory:b": "The shed is red."}
        evidence = [
            {"memory_ref": "memory:a", "state": "resolved", "content": "Kerosene heats the shed."},
            {"memory_ref": "memory:b", "state": "resolved", "content": "The shed is"},     # abridged
            {"memory_ref": "memory:b", "state": "truncated", "content": "The shed is red."},  # flagged
            {"memory_ref": None, "state": "resolved", "content": "The shed is red."},     # unattributed
        ]
        self.assertEqual(quality.fully_delivered_keys(evidence, seeded), ["memory:a"])


if __name__ == "__main__":
    unittest.main()
