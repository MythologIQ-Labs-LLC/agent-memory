from __future__ import annotations

import unittest

from run_keyed_rebinding_benchmark import UOR_R4_REVISION, _fixture, _digest, run_benchmark


class KeyedRebindingBenchmarkTests(unittest.TestCase):
    def test_small_fixture_preserves_currentness_and_controls(self) -> None:
        report = run_benchmark("0" * 40, key_count=2, rounds=2)

        self.assertTrue(report["passed"])
        self.assertEqual(report["source_pressure"]["revision"], UOR_R4_REVISION)
        self.assertFalse(report["source_pressure"]["code_or_schema_reused"])
        self.assertFalse(report["source_pressure"]["geometric_model_adopted"])
        self.assertFalse(report["source_pressure"]["runtime_dependency_required"])

        quality = report["quality"]
        self.assertEqual(quality["correction_commit_rate"], 1.0)
        self.assertEqual(quality["current_fact_retrieval_rate"], 1.0)
        self.assertEqual(quality["stale_fact_candidate_rate"], 0.0)
        self.assertEqual(quality["stale_fact_admission_rate"], 0.0)
        self.assertEqual(quality["matched_control_stability_rate"], 1.0)
        self.assertEqual(quality["history_preservation_rate"], 1.0)

        governance = report["governance"]
        self.assertFalse(governance["unqualified_correction_committed"])
        self.assertEqual(governance["wrong_scope_admission_count"], 0)
        self.assertEqual(governance["stale_currentness_violation_count"], 0)
        self.assertEqual(governance["retrieval_evidence_authority_effect"], "none")

        recovery = report["runtime_recovery"]
        self.assertEqual(recovery["restart_count"], 2)
        self.assertEqual(recovery["restart_current_fact_mismatch_count"], 0)
        self.assertTrue(recovery["configuration_digest_stable"])

        self.assertFalse(report["performance"]["timing_is_conformance_gate"])
        self.assertNotIn("score", report)
        self.assertNotIn("health_score", report)

    def test_fixture_digest_is_deterministic(self) -> None:
        first = _fixture(3, 3)
        second = _fixture(3, 3)
        self.assertEqual(first, second)
        self.assertEqual(_digest(first), _digest(second))

    def test_rejects_unbounded_or_ambiguous_inputs(self) -> None:
        with self.assertRaises(ValueError):
            run_benchmark("not-a-revision", key_count=2, rounds=2)
        with self.assertRaises(ValueError):
            run_benchmark("0" * 40, key_count=0, rounds=2)
        with self.assertRaises(ValueError):
            run_benchmark("0" * 40, key_count=2, rounds=1)


if __name__ == "__main__":
    unittest.main()
