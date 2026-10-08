"""Contract tests for #722 read-only evidence audit, not a benchmark evaluator."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_benchmark_deficit_ledger import audit, main


def base():
    return {
        "schema_version": "1.0.0",
        "generated_from": ["frozen-evidence.json"],
        "deficits": [{
            "deficit_id": "capability-gap-1",
            "benchmark_profile": "Independent profile",
            "metric": "native_measure",
            "posture": "implementation_defect",
            "state": "open",
            "owning_issue": 100,
            "primary_stage": "unclassified",
            "evidence_refs": ["rows/frozen-evidence.json"],
            "same_harness_frontier": None,
            "published_frontier": {"system": "Literature only", "value": 0.9},
            "closure_evidence": [],
            "negative_control_refs": [],
        }],
    }


class AuditTests(unittest.TestCase):
    def test_live_repository_ledger_is_structurally_readable(self):
        path = ROOT / "reports/benchmarks/deficits/current.json"
        before = path.read_bytes()
        result = audit(json.loads(before))
        self.assertFalse(result["structural_errors"], result["structural_errors"])
        self.assertEqual(result["counts"]["records"], len(json.loads(before)["deficits"]))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(result["record_mutations"], 0)

    def test_published_reference_never_becomes_same_harness(self):
        data = base()
        result = audit(data)
        self.assertFalse(any(f["code"] == "frontier_not_measured" for f in
                             result["review_candidates"]))
        data["deficits"][0]["posture"] = "competitive_deficit"
        result = audit(data)
        self.assertIn("frontier_not_measured",
                      {f["code"] for f in result["review_candidates"]})
        self.assertEqual(data["deficits"][0]["same_harness_frontier"], None)
        self.assertEqual(data["deficits"][0]["published_frontier"]["value"], 0.9)

    def test_unknown_attribution_never_invented(self):
        result = audit(base())
        self.assertIn("stage_unclassified", {f["code"] for f in result["review_candidates"]})
        self.assertNotIn("remediation_hypothesis", result)

    def test_closed_record_without_evidence_fails(self):
        data = base()
        data["deficits"][0]["state"] = "frontier"
        data["deficits"][0]["posture"] = "frontier"
        result = audit(data)
        self.assertIn("unsupported_closure", {e["code"] for e in result["structural_errors"]})
        data["deficits"][0]["closure_evidence"] = ["accepted/replay-1.json"]
        self.assertFalse(audit(data)["structural_errors"])

    def test_duplicate_id_and_missing_owner_fails(self):
        data = base()
        clone = deepcopy(data["deficits"][0])
        clone["owning_issue"] = None
        data["deficits"].append(clone)
        codes = {x["code"] for x in audit(data)["structural_errors"]}
        self.assertIn("duplicate_deficit_id", codes)
        self.assertIn("missing_owner", codes)

    def test_unknown_scope_key_and_schema_fail_closed(self):
        data = base()
        data["enforcement_override"] = True
        self.assertIn("invalid_envelope", {e["code"] for e in audit(data)["structural_errors"]})
        data = base()
        data["schema_version"] = "999.0"
        self.assertIn("unknown_ledger_schema", {e["code"] for e in audit(data)["structural_errors"]})

    def test_blocked_state_is_never_coerced_to_zero(self):
        data = base()
        row = data["deficits"][0]
        row["state"] = "blocked"
        row["agent_memory"] = None
        row["published_frontier"] = None
        report = audit(data)
        self.assertFalse(report["structural_errors"])
        self.assertEqual(report["counts"]["state:blocked"], 1)
        self.assertNotIn("metric_value", report)
        self.assertIsNone(row["agent_memory"])

    def test_metric_value_is_not_tuned_or_interpreted(self):
        data = base()
        for value in (0, 1, -400, "unmeasured", {"precision": 0.01},
                      {"custom": ["external", "structured", "metric"]}):
            data["deficits"][0]["agent_memory"] = value
            report = audit(data)
            self.assertFalse(report["structural_errors"])
            self.assertEqual(report["counts"]["records"], 1)

    def test_negative_controls_are_review_not_a_ledger_mutation(self):
        data = base()
        report = audit(data)
        self.assertIn("negative_controls_missing", {f["code"] for f in report["review_candidates"]})
        self.assertEqual(report["automation_authority"], "none")
        self.assertEqual(report["benchmark_remediation_authority"], "none")
        self.assertEqual(report["record_mutations"], 0)
        self.assertEqual(data, base())

    def test_results_deterministic_across_ledger_row_order(self):
        data = base()
        other = deepcopy(data["deficits"][0])
        other["deficit_id"] = "another-capability"
        data["deficits"].append(other)
        baseline = audit(data)
        data["deficits"].reverse()
        self.assertEqual(audit(data), baseline)

    def test_cli_refuses_overwriting_ledger_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ledger.json"
            p.write_text(json.dumps(base()), encoding="utf-8")
            original = p.read_bytes()
            self.assertEqual(main(["--ledger", str(p), "--output", str(p)]), 2)
            self.assertEqual(p.read_bytes(), original)
            report_path = Path(tmp) / "audit.json"
            self.assertEqual(main(["--ledger", str(p), "--output", str(report_path)]), 0)
            result = json.loads(report_path.read_text())
            self.assertEqual(result["schema"], "agent-memory.deficit-audit/v1")
            self.assertEqual(p.read_bytes(), original)

    def test_empty_or_unreadable_ledger_is_explicit_failure(self):
        data = base()
        data["generated_from"] = []
        self.assertIn("missing_source_provenance",
                      {e["code"] for e in audit(data)["structural_errors"]})
        data = base()
        data["deficits"] = "not an array"
        self.assertIn("invalid_deficit_collection",
                      {e["code"] for e in audit(data)["structural_errors"]})


if __name__ == "__main__":
    unittest.main()
