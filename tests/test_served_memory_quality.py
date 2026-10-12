"""#771 quality-first scorecard tests over wholly synthetic, preregistered cases.

These validate the EVALUATOR, not Agent Memory production quality. Never
reuse these synthetic labels in a runtime ranking/admission policy.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from score_served_memory_quality import score  # noqa: E402

DIR = ROOT / "reference/fixtures/evaluation"


def fixture(name):
    return json.loads((DIR / ("served-memory-quality-v1-" + name + ".json")).read_text())


class ServedMemoryQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.good, cls.bad = fixture("cases"), fixture("good"), fixture("bad")

    def test_safe_control_has_zero_prohibited_and_stale_exposure(self):
        report = score(self.cases, self.good)
        self.assertEqual(report["quality_case_count"], 6)
        self.assertEqual(report["P0_safety"]["cases_with_prohibited_exposure"], 0)
        self.assertEqual(report["P0_safety"]["cases_with_stale_exposure"], 0)
        self.assertEqual(report["P1_served_correctness"]["no_safe_answer_empty_context_count"], 2)
        self.assertIsNone(report["P1_served_correctness"]["answer_abstention_verified"])
        self.assertEqual(report["P1_served_correctness"]["all_critical_groups_covered_rate"], 1.0)
        self.assertTrue(report["not_a_composite_score"])
        self.assertNotIn("overall_score", report)
        self.assertNotIn("weighted_score", report)

    def test_unsafe_control_exposes_prohibited_stale_and_missing_critical_groups(self):
        report = score(self.cases, self.bad)
        self.assertEqual(report["P0_safety"]["cases_with_prohibited_exposure"], 2)
        self.assertEqual(report["P0_safety"]["cases_with_stale_exposure"], 1)
        by_id = {row["id"]: row for row in report["per_case"]}
        self.assertEqual(by_id["Q04"]["critical_groups_met"], 1)
        self.assertEqual(by_id["Q04"]["critical_groups_total"], 2)
        self.assertFalse(by_id["Q05"]["top1_relevant"])
        self.assertFalse(by_id["Q02"]["top1_relevant"])
        self.assertFalse(by_id["Q06"]["empty_delivery"])
        self.assertFalse(by_id["Q06"]["safely_answerable"])

    def test_historical_memory_is_not_incorrectly_marked_stale(self):
        report = score(self.cases, self.good)
        row = next(row for row in report["per_case"] if row["id"] == "Q02")
        self.assertEqual(row["intent"], "historical")
        self.assertEqual(row["stale_served"], 0)
        # The historical target ranks first, but leaving a lower-grade
        # supporting source unreturned can still reduce nDCG@budget.
        self.assertGreater(row["ndcg_at_budget"], 0.9)
        self.assertLessEqual(row["ndcg_at_budget"], 1.0)
        self.assertTrue(row["top1_relevant"])

    def test_top1_and_critical_recall_denominators_are_answerable_cases_only(self):
        report = score(self.cases, self.good)
        # Four of six cases are answerable. The other two have empty context,
        # which alone is NOT evidence of an answer-layer refusal.
        # and must not dilute top-1 ranking/critical-coverage scores.
        self.assertEqual(report["P1_served_correctness"]["top1_relevant_rate"], 1.0)
        self.assertEqual(report["P1_served_correctness"]["all_critical_groups_covered_rate"], 1.0)
        self.assertEqual(report["P1_served_correctness"]["answerable_case_count"], 4)

    def test_unknown_returned_ref_must_not_be_scored_irrelevant_by_default(self):
        altered = copy.deepcopy(self.good)
        altered["rows"][0]["returned"] = ["unknown-source-id"]
        with self.assertRaises(ValueError):
            score(self.cases, altered)

    def test_missing_extra_duplicate_query_rows_are_rejected(self):
        for mutation in ("missing", "extra", "duplicate"):
            altered = copy.deepcopy(self.good)
            if mutation == "missing":
                altered["rows"].pop()
            elif mutation == "extra":
                altered["rows"].append({"id": "extra", "returned": []})
            else:
                altered["rows"].append(copy.deepcopy(altered["rows"][0]))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                score(self.cases, altered)

    def test_return_budget_and_duplicate_references_are_rejected(self):
        too_many = copy.deepcopy(self.good)
        too_many["rows"][0]["returned"] = [
            "endpoint-current", "endpoint-prior", "service-context", "service-misc"
        ]
        with self.assertRaises(ValueError):
            score(self.cases, too_many)
        repeated = copy.deepcopy(self.good)
        repeated["rows"][0]["returned"] = ["endpoint-current", "endpoint-current"]
        with self.assertRaises(ValueError):
            score(self.cases, repeated)

    def test_declared_answerability_must_have_legitimate_critical_evidence(self):
        altered = copy.deepcopy(self.cases)
        altered["cases"][2]["safe_answer_exists"] = True
        with self.assertRaises(ValueError):
            score(altered, self.good)

    def test_forged_grades_and_output_fields_are_rejected(self):
        altered = copy.deepcopy(self.cases)
        altered["cases"][0]["relevance"]["endpoint-current"] = True
        with self.assertRaises(ValueError):
            score(altered, self.good)
        altered = copy.deepcopy(self.good)
        altered["rows"][0]["time_ms"] = 0.001
        with self.assertRaises(ValueError):
            score(self.cases, altered)

    def test_context_delivery_is_not_proof_of_answer_abstention(self):
        # Q03/Q06 have no permissible complete answer. Serving neutral context
        # does not establish that an answer was attempted or refused.
        altered = copy.deepcopy(self.good)
        altered["rows"][2]["returned"] = ["owner-guess"]
        report = score(self.cases, altered)
        row = next(item for item in report["per_case"] if item["id"] == "Q03")
        self.assertFalse(row["empty_delivery"])
        self.assertFalse(row["safely_answerable"])
        self.assertIsNone(row["answer_abstention_verified"])
        self.assertNotIn("abstention_correct", row)
        self.assertNotIn("correct_abstention_rate", report["P1_served_correctness"])
        self.assertEqual(report["P1_served_correctness"]["answer_abstention_status"],
                         "not_measured_without_answering_layer")
        self.assertEqual(report["P1_served_correctness"]["no_safe_answer_with_context_count"], 1)

    def test_empty_delivery_does_not_verify_correct_answer_abstention(self):
        report = score(self.cases, self.good)
        self.assertIsNone(report["P1_served_correctness"]["answer_abstention_verified"])
        self.assertEqual(report["P1_served_correctness"]["no_safe_answer_empty_context_count"], 2)
        self.assertEqual(report["P1_served_correctness"]["empty_delivery_on_answerable_count"], 0)

    def test_resource_metrics_remain_explicitly_unmeasured(self):
        report = score(self.cases, self.bad)
        self.assertEqual(report["P3_efficiency"]["status"], "not_measured_in_quality_scorer")
        self.assertNotIn("latency", report["P1_served_correctness"])


if __name__ == "__main__":
    unittest.main()
