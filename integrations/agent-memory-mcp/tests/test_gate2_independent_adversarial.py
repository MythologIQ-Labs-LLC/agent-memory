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
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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


class AnswerLevelEvidenceCompleteness(unittest.IsolatedAsyncioTestCase):
    async def test_truncated_returned_key_does_not_count_as_complete_evidence(self):
        # Drive task_eval.run through a substituted protocol client, while
        # leaving the same quality.score() and indexed FTS5 comparator intact.
        # The only source delivered by MCP is truncated. Merely returning its
        # logical key must not count as full evidence coverage.
        cases = {
            "tenant": "tenant:adversarial-test",
            "scope": "project:adversarial-test",
            "records": [{"key": "memory:heat",
                         "text": "The greenhouse is heated by a propane burner."}],
            "tasks": [{"id": "A", "question": "How is the greenhouse heated?",
                       "required": ["memory:heat"], "forbidden": [],
                       "gold": ["propane"]}],
        }

        class FakeClient:
            async def call_tool(self, name, arguments):
                if name == "memory_remember":
                    return SimpleNamespace(is_error=False,
                                           structured_content={"committed": True})
                if name == "memory_find":
                    return SimpleNamespace(is_error=False, structured_content={
                        "answer_generated": False,
                        "evidence": [{
                            "state": "truncated",
                            "memory_ref": "memory:heat",
                            "content": "The greenhouse is heated by...",
                        }],
                        "selection_assessment": "undetermined",
                        "profile": "all_returned",
                    })
                raise AssertionError(name)

        @asynccontextmanager
        async def client_session(*args, **kwargs):
            yield FakeClient()

        with patch.object(task_eval, "Client", client_session):
            report = await task_eval.run(
                cases, lambda question, texts: (None, None),
                k=1, selectivity=False, answerer_name="adversarial-test",
            )
        mcp = report["rows"][0]["mcp"]["evidence"]
        fts = report["rows"][0]["fts5"]["evidence"]
        self.assertEqual(mcp["required_key_hits"], 1)
        self.assertFalse(
            mcp["required_complete"],
            "task_eval credited truncated MCP content because the required source key appeared",
        )
        self.assertTrue(fts["required_complete"])


if __name__ == "__main__":
    unittest.main()
