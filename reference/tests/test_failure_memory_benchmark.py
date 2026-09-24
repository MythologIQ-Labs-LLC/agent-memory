from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from run_failure_memory_benchmark import (
    BENCHMARK_ID,
    DEFAULT_FIXTURE,
    run_benchmark,
)


REVISION = "a" * 40


class FailureMemoryBenchmarkTests(unittest.TestCase):
    def test_default_fixture_reports_quality_performance_and_governance_separately(self) -> None:
        report = run_benchmark(
            fixture_path=DEFAULT_FIXTURE,
            agent_memory_revision=REVISION,
        )

        self.assertEqual(BENCHMARK_ID, report["benchmark_id"])
        self.assertEqual(REVISION, report["agent_memory_revision"])
        self.assertEqual(0, report["quality"]["identity_equivalence_failures"])
        self.assertEqual(0, report["quality"]["identity_separation_failures"])
        self.assertEqual(0, report["quality"]["false_recurrence_match_count"])
        self.assertEqual(1.0, report["quality"]["repeated_failure_retrieval"]["recall"])
        self.assertEqual(0, report["quality"]["initial_commit_failures"])
        self.assertEqual(0, report["quality"]["recurrence_identification_failures"])
        self.assertEqual(0, report["quality"]["correction_currentness_failures"])
        self.assertEqual(0, report["quality"]["retraction_currentness_failures"])

        self.assertGreater(report["performance"]["owner_checkpoint_bytes"], 0)
        self.assertEqual("not_measured", report["performance"]["latency_measurement"])

        violations = report["governance"]
        self.assertEqual(0, violations["wrong_scope_admission_violations"])
        self.assertEqual(0, violations["recall_mutated_recurrence_violations"])
        self.assertEqual(0, violations["similarity_authority_effect_violations"])
        self.assertEqual(0, violations["similarity_correction_bypass_violations"])
        self.assertEqual(0, violations["retracted_resurfacing_violations"])
        self.assertEqual("none", violations["failure_memory_authority_effect"])
        self.assertFalse(violations["action_authority_claimed"])

        self.assertTrue(report["claim_boundary"]["no_aggregate_health_score"])
        self.assertNotIn("health_score", report)
        self.assertEqual(
            "not_measured",
            report["quality"]["avoided_repeated_failure"]["status"],
        )

    def test_revision_binding_requires_exact_commit(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact 40-hex"):
            run_benchmark(
                fixture_path=DEFAULT_FIXTURE,
                agent_memory_revision="main",
            )

    def test_fixture_sha_changes_when_fixture_changes(self) -> None:
        original = json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as root:
            first = Path(root) / "a.json"
            second = Path(root) / "b.json"
            first.write_text(json.dumps(original), encoding="utf-8")
            changed = dict(original)
            changed["repeat_recall_count"] = original["repeat_recall_count"] + 1
            second.write_text(json.dumps(changed), encoding="utf-8")

            first_report = run_benchmark(
                fixture_path=first,
                agent_memory_revision=REVISION,
            )
            second_report = run_benchmark(
                fixture_path=second,
                agent_memory_revision=REVISION,
            )

        self.assertNotEqual(
            first_report["fixture"]["sha256"],
            second_report["fixture"]["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
