"""Offline gate-contract tests; the real MCP acceptance probe remains separate."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("stage_c_gate", Path(__file__).resolve().parents[1] / "stage_c_gate.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(name: str, *, answerable: bool, status: str, complete: bool = True) -> dict:
    return {
        "id": name,
        "mcp": {"required_total": 1 if answerable else 0,
                "required_complete": complete if answerable else None},
        "mcp_keys": ["memory:fact"], "mcp_evidence_count": 1,
        "mcp_profile": "all_returned", "mcp_answer_generated": False,
        "mcp_answerability_verified": False, "mcp_selection_policy_version": None,
        "mcp_evidence_assessment": status,
        "mcp_evidence_assessment_reason": (
            "answer_entailment_not_checked" if status == "unverified"
            else "no_complete_attributed_evidence"),
    }


class StageCGateTests(unittest.TestCase):
    def test_pass_requires_both_populated_no_answer_abstention_and_answerable_preservation(self):
        outcome = module.assess({"rows": [
            row("A1", answerable=True, status="unverified"),
            row("N1", answerable=False, status="insufficient_evidence"),
        ]})
        self.assertEqual(outcome["status"], "PASS")
        self.assertEqual(outcome["counts"]["unanswerable_abstained"], 1)

    def test_current_unverified_on_no_answer_fails_closed(self):
        outcome = module.assess({"rows": [
            row("A1", answerable=True, status="unverified"),
            row("N1", answerable=False, status="unverified"),
        ]})
        self.assertEqual(outcome["status"], "BLOCKED")
        self.assertEqual([c["task_id"] for c in outcome["checks"] if not c["passed"]], ["N1"])

    def test_missing_assessment_and_retrieval_regression_fail(self):
        a = row("A1", answerable=True, status="unverified", complete=False)
        n = row("N1", answerable=False, status="insufficient_evidence")
        n.pop("mcp_evidence_assessment")
        self.assertEqual(module.assess({"rows": [a, n]})["status"], "BLOCKED")

    def test_missing_runtime_field_fails_even_with_correct_labels(self):
        a = row("A1", answerable=True, status="unverified")
        n = row("N1", answerable=False, status="insufficient_evidence")
        n.pop("mcp_answerability_verified")
        self.assertEqual(module.assess({"rows": [a, n]})["status"], "BLOCKED")

    def test_missing_cohort_or_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            module.assess({"rows": []})
        with self.assertRaises(ValueError):
            module.assess({"rows": [row("A1", answerable=True, status="unverified")]})
        with self.assertRaises(ValueError):
            module.assess({"rows": [row("A1", answerable=True, status="unverified"),
                                    row("A1", answerable=False, status="insufficient_evidence")]})


if __name__ == "__main__":
    unittest.main()
