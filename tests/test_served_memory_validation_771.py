"""#771 independent cloud qualification: evaluator regressions and adversarial controls.

Authored by the independent reviewer, not the candidate author. The
``EvaluatorDefects`` cases were committed failing against candidate
23321e4bc1d8039ea64f8d135aac080fc98806fa before any repair.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from score_served_memory_quality import score  # noqa: E402


def _case(cid, relevance, groups, *, budget=3, intent="current", prohibited=(), stale=()):
    eligible = [r for r, g in relevance.items() if g >= 2 and r not in prohibited and r not in stale]
    return {
        "id": cid, "scenario": "synthetic " + cid, "intent": intent, "budget": budget,
        "relevance": dict(relevance), "critical_groups": [list(g) for g in groups],
        "prohibited": list(prohibited), "stale": list(stale),
        "safe_answer_exists": bool(groups and eligible),
    }


def _doc(*cases):
    return {"schema": "served-memory-quality-v1", "cases": list(cases)}


def _run(**rows):
    return {"schema": "served-memory-run-v1", "runtime_revision": "synthetic",
            "lane_id": "validation-771", "rows": [{"id": k, "returned": v} for k, v in rows.items()]}


class EvaluatorDefects(unittest.TestCase):
    """Each failed on the unrepaired candidate."""

    def test_provenance_suite_does_not_shadow_testcase_run(self):
        # E1: `cls.run = {...}` replaced unittest.TestCase.run, so all 11
        # provenance tests crashed the runner and never executed.
        spec = importlib.util.spec_from_file_location(
            "prov_771", ROOT / "tests" / "test_served_memory_provenance.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = module.ServedQualityProvenanceTests
        cls.setUpClass()
        self.assertIs(cls.run, unittest.TestCase.run)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(cls)
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(result.testsRun, 11)
        self.assertEqual((result.errors, result.failures), ([], []))

    def test_empty_delivery_on_answerable_case_cannot_raise_macro_precision(self):
        # E2: precision was None for an empty list and silently dropped from
        # the macro mean, so serving NOTHING on an answerable case scored
        # better than serving the right memory plus one distractor.
        cases = _doc(_case("A", {"a": 3, "x": 0, "b": 3, "y": 0}, [["a"]]),
                     _case("B", {"a": 0, "x": 0, "b": 3, "y": 0}, [["b"]]))
        full = score(cases, _run(A=["a", "x"], B=["b", "y"]))
        starved = score(cases, _run(A=["a"], B=[]))
        self.assertLessEqual(starved["P2_context_utility"]["macro_relevant_precision"],
                             full["P2_context_utility"]["macro_relevant_precision"])

    def test_no_safe_answer_context_is_not_mixed_into_answerable_utility(self):
        # E3: precision 0.0 / nDCG from no-safe-answer cases was averaged into
        # the same macro as answerable cases, so adding an unanswerable query
        # changed answerable context-utility numbers.
        answerable = _case("A", {"a": 3, "x": 1, "z": 0}, [["a"]])
        unanswerable = _case("N", {"a": 0, "x": 1, "z": 0}, [])
        alone = score(_doc(answerable), _run(A=["a", "x"]))
        mixed = score(_doc(answerable, unanswerable), _run(A=["a", "x"], N=["x", "z"]))
        for key in ("macro_relevant_precision", "macro_ndcg_at_budget"):
            self.assertEqual(alone["P2_context_utility"][key], mixed["P2_context_utility"][key], key)
        self.assertEqual(mixed["P1_served_correctness"]["no_safe_answer_served_total"], 2)

    def test_recall_is_reported_at_the_actual_served_budget(self):
        # E4: recall divided by ALL safe relevant memories, so a perfect
        # budget-2 context over 4 relevant memories could never exceed 0.5.
        case = _case("A", {"a": 3, "b": 3, "c": 2, "d": 2, "z": 0}, [["a"], ["b"]], budget=2)
        report = score(_doc(case), _run(A=["a", "b"]))
        self.assertEqual(report["per_case"][0]["relevant_recall"], 0.5)
        self.assertEqual(report["per_case"][0]["relevant_recall_at_budget"], 1.0)
        self.assertEqual(report["P2_context_utility"]["macro_relevant_recall_at_budget"], 1.0)


class AdversarialControls(unittest.TestCase):
    """Held on the candidate; pinned so later repairs cannot regress them."""

    def test_supporting_context_at_rank_one_is_not_an_answer(self):
        case = _case("A", {"answer": 3, "context": 1, "z": 0}, [["answer"]])
        report = score(_doc(case), _run(A=["context", "answer"]))
        row = report["per_case"][0]
        self.assertFalse(row["top1_relevant"])
        self.assertEqual(row["critical_groups_met"], 1)

    def test_forbidden_relevant_memory_earns_no_relevance_credit(self):
        case = _case("A", {"ok": 3, "secret": 3, "z": 0}, [["ok"]], prohibited=("secret",))
        report = score(_doc(case), _run(A=["secret", "ok"]))
        row = report["per_case"][0]
        self.assertFalse(row["top1_relevant"])
        self.assertEqual(row["prohibited_served"], 1)
        self.assertEqual(row["relevant_precision"], 0.5)
        self.assertLess(row["ndcg_at_budget"], 1.0)
        self.assertEqual(report["P0_safety"]["cases_with_prohibited_exposure"], 1)

    def test_only_one_of_two_required_memories_is_partial_coverage(self):
        case = _case("A", {"a": 3, "b": 3, "z": 0}, [["a"], ["b"]])
        report = score(_doc(case), _run(A=["a", "z"]))
        self.assertEqual(report["per_case"][0]["critical_coverage"], 0.5)
        self.assertEqual(report["P1_served_correctness"]["all_critical_groups_covered_rate"], 0.0)

    def test_old_value_is_credit_for_historical_but_stale_for_current(self):
        historical = _case("H", {"old": 3, "new": 1, "z": 0}, [["old"]], intent="historical")
        current = _case("C", {"old": 3, "new": 3, "z": 0}, [["new"]], stale=("old",))
        report = score(_doc(historical, current), _run(H=["old"], C=["old", "new"]))
        h, c = report["per_case"]
        self.assertTrue(h["top1_relevant"])
        self.assertEqual(h["stale_served"], 0)
        self.assertFalse(c["top1_relevant"])
        self.assertEqual(c["stale_served"], 1)
        self.assertEqual(report["P0_safety"]["cases_with_stale_exposure"], 1)

    def test_empty_retrieval_is_never_reported_as_answer_abstention(self):
        answerable = _case("A", {"a": 3, "z": 0}, [["a"]])
        unanswerable = _case("N", {"a": 0, "z": 0}, [])
        report = score(_doc(answerable, unanswerable), _run(A=[], N=[]))
        p1 = report["P1_served_correctness"]
        self.assertIsNone(p1["answer_abstention_verified"])
        self.assertEqual(p1["answer_abstention_status"], "not_measured_without_answering_layer")
        self.assertEqual(p1["empty_delivery_on_answerable_count"], 1)
        self.assertEqual(p1["no_safe_answer_empty_context_count"], 1)
        for row in report["per_case"]:
            self.assertIsNone(row["answer_abstention_verified"])
            self.assertNotIn("abstention_correct", row)
        self.assertNotIn("correct_abstention_rate", p1)

    def test_unlabeled_returned_memory_is_refused_not_scored_irrelevant(self):
        case = _case("A", {"a": 3, "z": 0}, [["a"]])
        with self.assertRaises(ValueError):
            score(_doc(case), _run(A=["a", "never-labelled"]))

    def test_over_budget_and_duplicate_outputs_are_refused(self):
        case = _case("A", {"a": 3, "b": 1, "z": 0}, [["a"]], budget=2)
        for returned in (["a", "b", "z"], ["a", "a"]):
            with self.subTest(returned=returned), self.assertRaises(ValueError):
                score(_doc(case), _run(A=returned))

    def test_gold_cannot_mark_a_stale_or_forbidden_memory_critical(self):
        for kw in ({"stale": ("a",)}, {"prohibited": ("a",)}):
            case = _case("A", {"a": 3, "b": 3}, [["a"]], **kw)
            case["safe_answer_exists"] = True
            with self.subTest(**{k: v for k, v in kw.items()}), self.assertRaises(ValueError):
                score(_doc(case), _run(A=["b"]))

    def test_no_composite_score_is_emitted(self):
        case = _case("A", {"a": 3, "z": 0}, [["a"]])
        report = score(_doc(case), _run(A=["a"]))
        def keys(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield key
                    yield from keys(value)
            elif isinstance(node, list):
                for value in node:
                    yield from keys(value)
        for key in keys(report):
            if key != "not_a_composite_score":
                self.assertFalse(any(b in key for b in ("overall", "weighted", "composite", "health")), key)
        self.assertTrue(report["not_a_composite_score"])


if __name__ == "__main__":
    unittest.main()
