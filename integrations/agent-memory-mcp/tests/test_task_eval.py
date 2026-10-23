"""Checks for the Phase 5 task-level *measurement* (judge/aggregate/reader plumbing), not the product."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("am_mcp_task_eval", HERE / "task_eval.py")
assert spec and spec.loader
task_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(task_eval)


class TaskEvalJudge(unittest.TestCase):
    def test_abstention_on_answerable_is_not_correct_and_not_a_false_answer(self):
        v = task_eval.judge(None, ["propane"])
        self.assertEqual((v["answerable"], v["abstained"], v["correct"], v["false_answer"]), (True, True, False, False))

    def test_gold_phrase_match_is_whole_token_case_insensitive_and_negation_guarded(self):
        self.assertTrue(task_eval.judge("It is heated by a Propane burner.", ["propane"])["correct"])
        self.assertTrue(task_eval.judge("Frostline FL-80", ["fl-80"])["correct"])
        self.assertFalse(task_eval.judge("It is heated by paraffin.", ["propane"])["correct"])
        # a word inside another word and a negated mention are not credited (review 5628673295)
        self.assertFalse(task_eval.judge("The answer is blueberry.", ["blue"])["correct"])
        negated = task_eval.judge("The aircraft did not land in Oslo.", ["Oslo"])
        self.assertEqual((negated["correct"], negated["gold_phrase_present"], negated["negated"]), (False, True, True))
        self.assertFalse(task_eval.judge("It isn't propane.", ["propane"])["correct"])

    def test_no_answer_question_rewards_abstention_and_flags_a_false_answer(self):
        self.assertTrue(task_eval.judge(None, None)["correct"])
        v = task_eval.judge("Saturday", None)
        self.assertFalse(v["correct"])
        self.assertTrue(v["false_answer"])

    def test_extractive_reader_abstains_without_shared_terms_and_never_sees_gold(self):
        answer, _ = task_eval.extractive_answerer("How is the greenhouse heated?",
                                                  ["Tamsin's greenhouse is heated by a propane burner. The thermostat is set to twelve degrees.",
                                                   "The harvest fair opens Saturday."])
        self.assertEqual(answer, "Tamsin's greenhouse is heated by a propane burner.")
        self.assertEqual(task_eval.extractive_answerer("What is the garage code?", ["The fern sits by the window."]), (None, None))
        self.assertEqual(task_eval.extractive_answerer("anything", []), (None, None))

    def test_task_cases_require_gold_for_answerable_and_null_for_no_answer(self):
        base = {"records": [{"key": "memory:a", "text": "Alpha is blue."}],
                "tasks": [{"id": "t", "question": "What colour is alpha?", "required": ["memory:a"], "forbidden": [], "gold": ["blue"]}]}
        task_eval.validate_task_cases(base)
        with self.assertRaises(ValueError):
            task_eval.validate_task_cases({**base, "tasks": [{**base["tasks"][0], "gold": None}]})
        with self.assertRaises(ValueError):
            task_eval.validate_task_cases({**base, "tasks": [{**base["tasks"][0], "required": [], "gold": ["blue"]}]})

    def test_aggregate_separates_answerable_from_unanswerable(self):
        ev = task_eval.quality.score(["memory:a"], ["memory:a"], [])
        rows = [
            {"mcp": {"verdict": task_eval.judge("blue", ["blue"]), "elapsed_ms": 1.0, "delivered_chars": 10, "evidence": ev}},
            {"mcp": {"verdict": task_eval.judge(None, None), "elapsed_ms": 2.0, "delivered_chars": 0,
                     "evidence": task_eval.quality.score([], [], [])}},
            {"mcp": {"verdict": task_eval.judge("red", None), "elapsed_ms": 3.0, "delivered_chars": 5,
                     "evidence": task_eval.quality.score(["memory:a"], [], [])}},
        ]
        s = task_eval.aggregate(rows, "mcp")
        self.assertEqual((s["answerable_total"], s["answerable_gold_phrase_match"]), (1, 1))
        self.assertEqual((s["unanswerable_total"], s["unanswerable_abstained"], s["unanswerable_false_answer"]), (2, 1, 1))
        self.assertEqual(s["unexpected_evidence_items"], 1)


if __name__ == "__main__":
    unittest.main()
