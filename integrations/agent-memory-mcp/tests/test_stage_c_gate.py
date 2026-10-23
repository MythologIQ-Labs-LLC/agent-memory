"""Offline admission tests. Passing these does not qualify the MCP product."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("stage_c_gate", Path(__file__).resolve().parents[1] / "stage_c_gate.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def task(name: str, *, answerable: bool) -> dict:
    return {"id": name, "question": "Question " + name,
            "required": ["memory:fact"] if answerable else [], "forbidden": []}


def row(t: dict, *, status: str = "unverified", complete: bool = True) -> dict:
    answerable = bool(t["required"])
    return {
        "id": t["id"], "question": t["question"], "gold": t["required"],
        "forbidden": t["forbidden"],
        "mcp": {"required_total": 1 if answerable else 0,
                "required_complete": complete if answerable else None},
        "mcp_keys": ["memory:fact"], "mcp_full_text_keys": ["memory:fact"],
        "mcp_evidence_count": 1, "mcp_profile": "all_returned",
        "mcp_answer_generated": False, "mcp_answerability_verified": False,
        "mcp_selection_policy_version": None,
        "mcp_evidence_assessment": status,
        "mcp_evidence_assessment_reason": (
            "answer_entailment_not_checked" if status == "unverified"
            else "no_complete_attributed_evidence"),
    }


def cohort():
    a = task("A1", answerable=True)
    n = task("N1", answerable=False)
    manifest = {"records": [{"key": "memory:fact", "text": "A fact."}], "tasks": [a, n]}
    report = {"schema": module.PROBE_SCHEMA,
              "provider": "real stdio MCP / governed SQLite / memory_find experimental_selectivity=False (all_returned profile)",
              "selectivity": False, "dataset": {"records": 1, "tasks": 2},
              "rows": [row(a), row(n, status="insufficient_evidence")]}
    return report, manifest


class StageCGateTests(unittest.TestCase):
    def test_pass_requires_populated_store_both_controls_and_full_text(self):
        report, manifest = cohort()
        outcome = module.assess(report, manifest)
        self.assertEqual(outcome["status"], "PASS")
        self.assertEqual(outcome["counts"]["unanswerable_abstained"], 1)

    def test_current_unverified_on_no_answer_fails_closed(self):
        report, manifest = cohort()
        report["rows"][1]["mcp_evidence_assessment"] = "unverified"
        self.assertEqual(module.assess(report, manifest)["status"], "BLOCKED")

    def test_missing_assessment_and_retrieval_regression_fail(self):
        report, manifest = cohort()
        report["rows"][0]["mcp_full_text_keys"] = []
        report["rows"][1].pop("mcp_evidence_assessment")
        self.assertEqual(module.assess(report, manifest)["status"], "BLOCKED")

    def test_missing_runtime_field_fails_even_with_correct_labels(self):
        report, manifest = cohort()
        report["rows"][1].pop("mcp_answerability_verified")
        self.assertEqual(module.assess(report, manifest)["status"], "BLOCKED")

    def test_subset_only_successes_cannot_pass(self):
        report, manifest = cohort()
        report["rows"] = report["rows"][:1]
        with self.assertRaises(ValueError):
            module.assess(report, manifest)

    def test_duplicate_and_substituted_tasks_rejected(self):
        report, manifest = cohort()
        report["rows"][1]["id"] = "A1"
        with self.assertRaises(ValueError):
            module.assess(report, manifest)
        report, manifest = cohort()
        report["rows"][1]["id"] = "N2"
        with self.assertRaises(ValueError):
            module.assess(report, manifest)

    def test_gold_tampering_rejected_even_if_score_claims_success(self):
        report, manifest = cohort()
        report["rows"][0]["gold"] = []
        with self.assertRaises(ValueError):
            module.assess(report, manifest)

    def test_mcp_source_or_selectivity_cannot_be_substituted(self):
        report, manifest = cohort()
        report["selectivity"] = True
        with self.assertRaises(ValueError):
            module.assess(report, manifest)
        report, manifest = cohort()
        report["provider"] = "fixture stub"
        with self.assertRaises(ValueError):
            module.assess(report, manifest)

    def test_wrong_manifest_or_count_rejected(self):
        report, manifest = cohort()
        report["dataset"]["tasks"] = 1
        with self.assertRaises(ValueError):
            module.assess(report, manifest)
        report, manifest = cohort()
        manifest["records"] = []
        with self.assertRaises(ValueError):
            module.assess(report, manifest)

    def test_malformed_full_text_key_claim_refused(self):
        report, manifest = cohort()
        report["rows"][0]["mcp_full_text_keys"] = ["memory:not-returned"]
        with self.assertRaises(ValueError):
            module.assess(report, manifest)

    def test_positive_control_cannot_pass_with_loss_of_required_evidence(self):
        report, manifest = cohort()
        report["rows"][0]["mcp"]["required_complete"] = False
        self.assertEqual(module.assess(report, manifest)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
