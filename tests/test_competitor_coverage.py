"""No provider dependencies: static competitive coverage audit regressions."""
import copy
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_competitor_coverage.py"
spec = importlib.util.spec_from_file_location("cohort_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SHA = "a" * 64
REV = "a" * 40


def source():
    return {
        "authority_effect": "none",
        "as_of": "2026-10-14",
        "published_reference": [{"system": "SomeVendor", "signals": {"accuracy": 0.99}}],
        "competitive_evidence": {
            "frozen_lanes": [{
                "lane_id": "longmemeval-parity-v1", "status": "accepted",
                "input_sha256": SHA, "harness_revision": REV,
                "accepted_on": "2026-10-14",
                "accepted_rows": [
                    {"provider": "agent_memory", "role": "control", "plane": "session",
                     "system_revision": REV, "evidence": "runs/am.json",
                     "native": {"recall_all@5": 0.80}},
                    {"provider": "mem0_explicit", "role": "comparator", "plane": "session",
                     "system_revision": REV, "evidence": "runs/mem0.json",
                     "native": {"recall_all@5": 0.81}},
                    {"provider": "bm25", "role": "baseline", "plane": "session",
                     "system_revision": REV, "evidence": "runs/bm25.json",
                     "native": {"recall_all@5": 0.95}},
                ],
            }],
        },
    }


class CohortAuditTests(unittest.TestCase):
    def report(self, source_doc=None):
        return audit.coverage_report(source_doc or source(), "f" * 40)

    def test_external_distinct_count_excludes_control_baseline_and_published(self):
        r = self.report()
        self.assertEqual(r["accepted_external_product_count"], 1)
        self.assertEqual(r["accepted_distinct_external_products"], ["mem0-explicit"])
        self.assertEqual(r["external_product_gap"], 5)
        self.assertEqual(r["comparable_native_metric_contexts"], 1)

    def test_deferred_row_is_not_measured(self):
        d = source()
        d["competitive_evidence"]["frozen_lanes"][0]["rows"] = {"hindsight": "deferred"}
        self.assertEqual(self.report(d)["accepted_external_product_count"], 1)

    def test_repeated_product_multiple_planes_does_not_count_twice(self):
        d = source()
        lane = copy.deepcopy(d["competitive_evidence"]["frozen_lanes"][0])
        for row in lane["accepted_rows"]:
            row["plane"] = "turn"
            if row["role"] == "comparator":
                row["provider"] = "mem0-explicit"
        d["competitive_evidence"]["frozen_lanes"].append(lane)
        r = self.report(d)
        self.assertEqual(r["accepted_external_product_count"], 1)
        self.assertEqual(r["accepted_profile_planes"], 2)

    def test_unaccepted_lane_is_never_counted(self):
        d = source()
        new_lane = copy.deepcopy(d["competitive_evidence"]["frozen_lanes"][0])
        new_lane["status"] = "draft"
        new_lane["accepted_rows"][1]["provider"] = "hindsight"
        d["competitive_evidence"]["frozen_lanes"].append(new_lane)
        self.assertEqual(self.report(d)["accepted_external_product_count"], 1)

    def test_missing_peer_metric_is_not_zero(self):
        d = source()
        d["competitive_evidence"]["frozen_lanes"][0]["accepted_rows"][1]["native"] = {}
        r = self.report(d)
        self.assertEqual(r["accepted_external_product_count"], 0)
        self.assertEqual(r["comparable_native_metric_contexts"], 0)

    def test_acceptance_identity_required(self):
        d = source()
        del d["competitive_evidence"]["frozen_lanes"][0]["input_sha256"]
        with self.assertRaisesRegex(ValueError, "frozen identity"):
            self.report(d)

    def test_reject_nan_and_negative_metric(self):
        for number in [float("nan"), -0.1, 1.1]:
            with self.subTest(value=number):
                d = source()
                d["competitive_evidence"]["frozen_lanes"][0]["accepted_rows"][1]["native"]["recall_all@5"] = number
                with self.assertRaisesRegex(ValueError, "outside"):
                    self.report(d)

    def test_zero_is_valid_measured_result(self):
        d = source()
        d["competitive_evidence"]["frozen_lanes"][0]["accepted_rows"][1]["native"]["recall_all@5"] = 0.0
        self.assertEqual(self.report(d)["comparable_native_metric_contexts"], 1)

    def test_boolean_does_not_count_as_score(self):
        d = source()
        d["competitive_evidence"]["frozen_lanes"][0]["accepted_rows"][1]["native"]["recall_all@5"] = True
        self.assertEqual(self.report(d)["comparable_native_metric_contexts"], 0)

    def test_dashboard_must_have_no_authority_effect(self):
        d = source()
        d["authority_effect"] = "mutation"
        with self.assertRaisesRegex(ValueError, "authority effect"):
            self.report(d)

    def test_git_blob_is_content_bound(self):
        self.assertEqual(
            audit.git_blob_sha(b"test content"),
            "08cf6101416f0ce0dda3c80e627f333854c4085c",
        )


if __name__ == "__main__":
    unittest.main()
