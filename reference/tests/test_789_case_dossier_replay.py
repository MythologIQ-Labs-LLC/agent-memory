"""Source replay negative controls. No benchmark or inference execution."""
import unittest

from scripts.check_789_case_dossier import diagnostics, validate_dossier


def fixture():
    arms = ("agent_memory", "mem0_oss", "bm25_control")
    rows = {}
    for arm in arms:
        correct = arm != "mem0_oss"
        rows[arm] = {"query_id": "case-a", "query": "Which decision?", "gold_answers": ["id-a"],
                     "correct": correct, "context_tokens": 8, "retrieve_time_ms": 1.5,
                     "meta": {"category": "Example", "failures": [] if correct else ["missing expected belief: id-a"], "retrieval_precision": 0.5, "retrieval_recall": 1.0}}
    reports = {arm: {"dataset": "precisionmembench", "split": "single-turn", "mode": "retrieval",
                     "run_name": arm, "total_queries": 1, "correct": int(rows[arm]["correct"]),
                     "accuracy": float(rows[arm]["correct"]), "mean_precision": 0.5, "mean_recall": 1.0,
                     "results": [rows[arm]]} for arm in arms}
    dossier = {
        "schema_version": "competitive-case-dossier/1", "accepted_score_update": False,
        "qualitative_review_status": "not_started",
        "source_reports": [{"arm": arm, "run_name": arm, "total_queries": 1} for arm in arms],
        "entries": [{"case_id": "case-a", "source_row_key": "case-a", "benchmark_category": "Example",
                     "outcome": "agent_only", "arms": {arm: {"passed_native_scorer": row["correct"],
                               "context_tokens": 8, "retrieval_ms": 1.5, "diagnostic_flags": diagnostics(row)} for arm, row in rows.items()}}],
        "review_selection": {"target_case_ids": ["case-a"]},
        "summary": {"count": 1, "correct": {arm: reports[arm]["correct"] for arm in arms},
                    "native_accuracy": {arm: reports[arm]["accuracy"] for arm in arms},
                    "native_mean_precision": {arm: 0.5 for arm in arms},
                    "native_mean_recall": {arm: 1.0 for arm in arms},
                    "metric_denominators": {"native_mean_precision": {arm: 1 for arm in arms}, "native_mean_recall": {arm: 1 for arm in arms}},
                    "pair_outcomes": {"agent_only": 1},
                    "category_breakdown": [{"category": "Example", "case_count": 1, "agent_pass": 1, "mem0_pass": 0, "bm25_pass": 1}],
                    "mcnemar_exact_two_sided_agent_vs_mem0": 1.0},
    }
    return dossier, reports


class ReplayTests(unittest.TestCase):
    def test_valid_frozen_like_evidence(self):
        d, reports = fixture()
        self.assertEqual(validate_dossier(d, reports, expected_count=1, review_count=1)["status"], "source_replay_pass")

    def test_mutated_query_breaks_pairing(self):
        d, r = fixture()
        r["mem0_oss"]["results"][0]["query"] = "different question"
        with self.assertRaisesRegex(ValueError, "query/gold"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_mutated_gold_breaks_pairing(self):
        d, r = fixture()
        r["bm25_control"]["results"][0]["gold_answers"] = ["wrong"]
        with self.assertRaisesRegex(ValueError, "query/gold"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_dossier_misstates_case_verdict(self):
        d, r = fixture()
        d["entries"][0]["arms"]["mem0_oss"]["passed_native_scorer"] = True
        with self.assertRaisesRegex(ValueError, "verdict"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_missing_failure_flags_block_evidence(self):
        d, r = fixture()
        d["entries"][0]["arms"]["mem0_oss"]["diagnostic_flags"]["missing_expected_belief"] = False
        with self.assertRaisesRegex(ValueError, "complete failures"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_native_totals_must_match_rows(self):
        d, r = fixture()
        r["agent_memory"]["correct"] = 0
        with self.assertRaisesRegex(ValueError, "native pass total"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_mutated_summary_rejected(self):
        d, r = fixture()
        d["summary"]["correct"]["agent_memory"] = 0
        with self.assertRaisesRegex(ValueError, "summary pass"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_metric_denominator_must_match_native_rows(self):
        d, r = fixture()
        d["summary"]["metric_denominators"]["native_mean_recall"]["agent_memory"] = 77
        with self.assertRaisesRegex(ValueError, "metric denominator"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_metric_aggregation_must_match_native_rows(self):
        d, r = fixture()
        r["agent_memory"]["results"][0]["meta"]["retrieval_precision"] = 0.75
        with self.assertRaisesRegex(ValueError, "native metric aggregation"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_substituted_sample_rejected(self):
        d, r = fixture()
        d["review_selection"]["target_case_ids"] = ["made-up"]
        with self.assertRaisesRegex(ValueError, "frozen sample"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_promotion_rejected(self):
        d, r = fixture()
        d["accepted_score_update"] = True
        with self.assertRaisesRegex(ValueError, "unauthorized promotion"):
            validate_dossier(d, r, expected_count=1, review_count=1)

    def test_complete_failure_list_not_abbreviated_display_reason(self):
        row = {"correct": False, "judge_reason": "unexpected belief: x",
               "meta": {"failures": ["unexpected belief: x", "missing expected belief: y"]}}
        self.assertEqual(diagnostics(row), {"unexpected_belief": True, "missing_expected_belief": True, "pass": False})


if __name__ == "__main__":
    unittest.main()
