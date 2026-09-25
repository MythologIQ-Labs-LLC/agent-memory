from __future__ import annotations

import unittest

import run_rc_cognitive_memory_scenario as scenario


REVISION = "a" * 40


class RCCognitiveMemoryScenario(unittest.TestCase):
    def test_end_to_end_scenario_passes_with_separate_evidence_dimensions(self):
        report = scenario.run_scenario(REVISION)
        self.assertTrue(report["passed"])
        self.assertEqual(report["scenario_id"], "agent-memory-rc1-cognitive-lifecycle")
        self.assertEqual(report["scenario_version"], "1.0.0")
        self.assertEqual(report["contract_version"], "1.2.0")
        self.assertEqual(set(report) & {"quality", "governance", "runtime_recovery"}, {"quality", "governance", "runtime_recovery"})
        self.assertNotIn("health_score", report)
        self.assertNotIn("score", report)
        self.assertIn("no_universal_health_score", report["non_claims"])

    def test_scenario_is_deterministic_for_same_revision(self):
        first = scenario.run_scenario(REVISION)
        second = scenario.run_scenario(REVISION)
        self.assertEqual(first, second)
        self.assertEqual(first["evidence_digest"], second["evidence_digest"])

    def test_revision_binding_is_exact(self):
        for invalid in ("", "abc", "A" * 40, "g" * 40, "a" * 39, "a" * 41):
            with self.subTest(revision=invalid):
                with self.assertRaises(ValueError):
                    scenario.run_scenario(invalid)

    def test_negative_and_lifecycle_checks_are_load_bearing(self):
        report = scenario.run_scenario(REVISION)
        checks = report["checks"]
        for name in (
            "correction_without_qualified_evidence_requires_review",
            "superseded_value_not_admitted_as_current",
            "forgotten_memory_tombstoned_with_history",
            "forgotten_memory_not_admitted",
            "wrong_scope_candidate_never_admitted",
            "confidence_does_not_widen_authority",
            "configuration_digest_stable_across_restarts",
            "sqlite_profile_recovered",
        ):
            self.assertTrue(checks[name], name)


if __name__ == "__main__":
    unittest.main()
