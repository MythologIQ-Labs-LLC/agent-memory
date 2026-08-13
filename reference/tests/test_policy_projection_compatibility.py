"""Tests for the #256 projection compatibility contract."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from agentmem_ref.policy_projection_compatibility import evaluate_policy_projection_compatibility

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reference" / "testdata" / "policy-projection-compatibility-adversarial.json"


def _merge(base, overrides):
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class PolicyProjectionCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def _evaluate_case(self, case):
        currentness = copy.deepcopy(self.fixture["source_currentness"])
        if case.get("source_currentness_status") is not None:
            currentness["status"] = case["source_currentness_status"]
        target = _merge(self.fixture["base_target"], case.get("overrides", {}))
        return evaluate_policy_projection_compatibility(
            self.fixture["projection"],
            source_currentness=currentness,
            target=target,
            evaluated_at="2026-08-13T20:00:00Z",
        )

    def test_all_declared_cases_match_expected_status_and_reason(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                result = self._evaluate_case(case)
                self.assertEqual(result["compatibility"]["status"], case["expected_status"])
                expected_reason = case.get("expected_reason")
                if expected_reason is None:
                    self.assertEqual(result["compatibility"]["reason_codes"], [])
                else:
                    self.assertIn(expected_reason, result["compatibility"]["reason_codes"])
                self.assertEqual(
                    result["compatibility"]["consequential_use_current"],
                    case["expected_status"] == "current",
                )

    def test_evaluation_does_not_mutate_projection(self):
        projection = copy.deepcopy(self.fixture["projection"])
        before = copy.deepcopy(projection)
        result = evaluate_policy_projection_compatibility(
            projection,
            source_currentness=self.fixture["source_currentness"],
            target=self.fixture["base_target"],
            evaluated_at="2026-08-13T20:00:01Z",
        )
        self.assertEqual(projection, before)
        self.assertFalse(result["interpretation"]["historical_projection_mutated"])
        self.assertEqual(result["interpretation"]["authority_effect"], "none")
        self.assertEqual(result["interpretation"]["consumer_trace_role"], "derived_noncanonical")

    def test_new_target_contract_creates_new_evaluation_identity(self):
        first = evaluate_policy_projection_compatibility(
            self.fixture["projection"],
            source_currentness=self.fixture["source_currentness"],
            target=self.fixture["base_target"],
            evaluated_at="2026-08-13T20:00:02Z",
        )
        changed_target = copy.deepcopy(self.fixture["base_target"])
        changed_target["action_schema_digest"] = "sha256:3333333333333333333333333333333333333333333333333333333333333333"
        changed_target["semantic_mapping_status"] = "migration_required"
        second = evaluate_policy_projection_compatibility(
            self.fixture["projection"],
            source_currentness=self.fixture["source_currentness"],
            target=changed_target,
            evaluated_at="2026-08-13T20:00:03Z",
        )
        self.assertNotEqual(first["evaluation_id"], second["evaluation_id"])
        self.assertEqual(first["compatibility"]["status"], "current")
        self.assertEqual(second["compatibility"]["status"], "migration_required")

    def test_external_result_boundaries_are_fixed(self):
        result = self._evaluate_case(self.fixture["cases"][0])
        self.assertEqual(result["interpretation"]["external_policy_effect"], "may_only_tighten_existing_boundary")
        self.assertEqual(result["interpretation"]["execution_evidence"], "not_established")
        self.assertEqual(result["interpretation"]["human_adjudication"], "not_established")
        self.assertEqual(result["interpretation"]["memory_admission"], "not_established")

    def test_invalid_digest_is_rejected(self):
        projection = copy.deepcopy(self.fixture["projection"])
        projection["projection_digest"] = "not-a-digest"
        with self.assertRaisesRegex(ValueError, "projection.projection_digest"):
            evaluate_policy_projection_compatibility(
                projection,
                source_currentness=self.fixture["source_currentness"],
                target=self.fixture["base_target"],
                evaluated_at="2026-08-13T20:00:04Z",
            )


if __name__ == "__main__":
    unittest.main()
