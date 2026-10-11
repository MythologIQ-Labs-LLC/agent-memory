"""#769 preregistered, authority-neutral competition diagnostics contract.

This tests a synthetic evaluator only; it does not qualify the runtime's
positive stop behavior. The frozen suite never reads benchmark-gold labels.
"""
from __future__ import annotations

import json
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reference/fixtures/runtime/769-untyped-competition-v1.json"
EVALUATOR = ROOT / "scripts/check_769_untyped_competition_contract.py"


class UntypedCompetitionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.evaluate = runpy.run_path(str(EVALUATOR))["assess"]
        cls.cases = cls.fixture["cases"]

    def test_preregistered_case_contract(self):
        self.assertEqual(self.fixture["schema_version"], "769-observation-contract-v1")
        self.assertEqual(self.fixture["case_count"], len(self.cases))
        self.assertEqual(len({case["id"] for case in self.cases}), len(self.cases))
        self.assertGreaterEqual(len(self.cases), 30)
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(self.evaluate(case["input"]), case["expected"])
                self.assertEqual(case["expected"]["stop_recommendation"], "abstain")
                self.assertEqual(case["expected"]["authority_effect"], "none")

    def test_missing_evidence_must_fail_closed(self):
        baseline = self.cases[0]["input"]
        for field in baseline:
            invalid = dict(baseline)
            invalid.pop(field)
            with self.subTest(field=field):
                with self.assertRaises((TypeError, ValueError)):
                    self.evaluate(invalid)

    def test_hidden_metadata_cannot_change_visible_projection(self):
        baseline = self.cases[0]["input"]
        expected = self.evaluate(baseline)
        for decoy in (
            {"opaque_hidden_tenant_count": 100},
            {"opaque_deleted_source": "private-other-tenant"},
            {"opaque_dispute_message": "secret"},
        ):
            with self.subTest(decoy=decoy):
                altered = dict(baseline, **decoy)
                with self.assertRaises((TypeError, ValueError)):
                    self.evaluate(altered)
                self.assertEqual(self.evaluate(baseline), expected)

    def test_promotion_never_occurs_even_when_reviewable(self):
        self.assertTrue(any(c["expected"]["reviewable_for_future_positive_policy"] for c in self.cases))
        self.assertFalse(any(c["expected"]["stop_recommendation"] != "abstain" for c in self.cases))


if __name__ == "__main__":
    unittest.main()
