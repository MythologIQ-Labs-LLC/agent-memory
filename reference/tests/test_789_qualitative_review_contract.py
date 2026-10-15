"""Negative and positive controls for blinded qualitative evidence acceptance."""
import unittest

from scripts.check_789_qualitative_review import review_coverage, validate_review, DIMENSIONS

DOSSIER = {"review_selection": {"target_case_ids": ["case-1"]}, "entries": [{"case_id": "case-1"}]}


def record(reviewer="person-a", arm="A", kind="human"):
    return {
        "schema_version": "competitive-qualitative-review/1", "case_id": "case-1",
        "blind_arm": arm, "reviewer_id": reviewer, "reviewer_kind": kind,
        "locked": True, "benchmark_outcome_visible": False, "source_trace": "source:query-id:case-1",
        "dimensions": {d: {"rating": 2, "rationale": "Example anchored reason", "evidence_refs": ["original-output:1"]} for d in DIMENSIONS},
        "safety_flags": {"unauthorized_exposure": False, "deleted_data_exposure": False},
    }


class QualitativeGuardTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_review(record(), {"case-1"}), ("case-1", "A", "person-a"))

    def test_no_review_is_not_publishable(self):
        self.assertEqual(review_coverage(DOSSIER, [])["status"], "incomplete_not_publishable")

    def test_one_human_per_arm_not_publishable(self):
        self.assertEqual(review_coverage(DOSSIER, [record(), record(arm="B")])["status"], "incomplete_not_publishable")

    def test_two_distinct_humans_for_both_arms(self):
        rs = [record("p1", "A"), record("p2", "A"), record("p1", "B"), record("p2", "B")]
        self.assertEqual(review_coverage(DOSSIER, rs)["status"], "ready_for_independent_adjudication")

    def test_machine_only_not_publishable(self):
        rs = [record("model1", "A", "machine"), record("model2", "A", "machine"),
              record("model1", "B", "machine"), record("model2", "B", "machine")]
        self.assertEqual(review_coverage(DOSSIER, rs)["status"], "incomplete_not_publishable")

    def test_duplicate_review_rejected(self):
        with self.assertRaises(ValueError):
            review_coverage(DOSSIER, [record(), record()])

    def test_invalid_case(self):
        x = record()
        x["case_id"] = "hidden"
        with self.assertRaises(ValueError):
            validate_review(x, {"case-1"})

    def test_outcome_visible_refused(self):
        x = record()
        x["benchmark_outcome_visible"] = True
        with self.assertRaises(ValueError):
            validate_review(x, {"case-1"})

    def test_bool_rating_refused(self):
        x = record()
        x["dimensions"]["task_utility"]["rating"] = True
        with self.assertRaises(ValueError):
            validate_review(x, {"case-1"})

    def test_missing_evidence_ref_refused(self):
        x = record()
        x["dimensions"]["task_utility"]["evidence_refs"] = []
        with self.assertRaises(ValueError):
            validate_review(x, {"case-1"})

    def test_not_applicable_requires_reason(self):
        x = record()
        x["dimensions"]["task_utility"] = {"rating": "not_applicable", "rationale": "", "evidence_refs": []}
        with self.assertRaises(ValueError):
            validate_review(x, {"case-1"})

    def test_unreviewed_dimension_refused(self):
        x = record()
        x["dimensions"].pop("task_utility")
        with self.assertRaises(ValueError):
            validate_review(x, {"case-1"})

    def test_all_dimensions_not_applicable_rejected(self):
        x = record()
        for d in DIMENSIONS:
            x["dimensions"][d] = {"rating": "not_applicable", "rationale": "Not measurable", "evidence_refs": []}
        with self.assertRaises(ValueError):
            validate_review(x, {"case-1"})

    def test_disagreement_and_P0_flag_stay_visible(self):
        a = record("p1", "A")
        b = record("p2", "A")
        b["dimensions"]["task_utility"]["rating"] = 1
        b["safety_flags"]["deleted_data_exposure"] = True
        out = review_coverage(DOSSIER, [a, b, record("p1", "B"), record("p2", "B")])
        self.assertEqual(out["unresolved_dimension_disagreements"]["task_utility"], 1)
        self.assertEqual(out["cases_with_reported_P0_flags"], ["case-1"])


if __name__ == "__main__":
    unittest.main()
