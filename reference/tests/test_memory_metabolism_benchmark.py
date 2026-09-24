from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reference" / "fixtures" / "benchmarks" / "rc-memory-metabolism-v1.json"
RUNNER = ROOT / "reference" / "run_memory_metabolism_benchmark.py"


def _runner_module():
    spec = importlib.util.spec_from_file_location("memory_metabolism_benchmark_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RUNNER_MODULE = _runner_module()


class MemoryMetabolismBenchmarkTests(unittest.TestCase):
    def _report(self) -> dict:
        return RUNNER_MODULE.run_benchmark(
            fixture_path=FIXTURE,
            agent_memory_revision="test-revision",
        )

    def test_report_is_revision_bound_and_separates_evidence_groups(self) -> None:
        report = self._report()
        self.assertEqual(report["schema_version"], "1.0.0")
        self.assertEqual(report["benchmark_id"], "agent-memory-native-metabolism")
        self.assertEqual(report["benchmark_version"], "1.0.0")
        self.assertEqual(report["agent_memory_revision"], "test-revision")
        self.assertTrue(report["fixture"]["sha256"].startswith("sha256:"))
        self.assertEqual(report["fixture"]["case_count"], 6)
        self.assertEqual(report["fixture"]["consolidation_case_count"], 3)
        self.assertIn("metabolism_quality", report)
        self.assertIn("operational_behavior", report)
        self.assertIn("governance_failures", report)
        self.assertNotIn("health_score", report)
        self.assertNotIn("memory_health_score", report)

    def test_quality_evidence_covers_required_traps_without_aggregate_score(self) -> None:
        quality = self._report()["metabolism_quality"]
        self.assertEqual(quality["fixture_expectation_failures"], 0)
        self.assertEqual(quality["valuable_retention_behavior"]["failures"], 0)
        self.assertEqual(quality["ephemeral_prune_candidacy_behavior"]["failures"], 0)
        self.assertEqual(quality["false_permanence_pressure"]["failures"], 0)
        self.assertEqual(quality["stale_disputed_demotion_pressure"]["failures"], 0)
        self.assertEqual(quality["consolidation_source_exception_preservation"]["failures"], 0)
        self.assertEqual(quality["access_spam_trap_failures"], 0)

        cases = {row["case_id"]: row for row in quality["cases"]}
        spam = cases["access-spam-junk"]
        self.assertEqual(spam["result"]["disposition"], "prune_candidate")
        self.assertFalse(spam["result"]["crystallization_candidate"])
        disputed = cases["confidently-wrong-disputed"]
        reinforcement = disputed["result"]["reinforcement"]
        self.assertLess(
            reinforcement["effective_saturation"],
            reinforcement["saturation_after_reinforcement"],
        )
        self.assertEqual(disputed["result"]["authority_effect"], "none")

    def test_operational_evidence_proves_stateless_replay_and_proposal_counts(self) -> None:
        operational = self._report()["operational_behavior"]
        self.assertEqual(operational["memory_snapshots_evaluated"], 6)
        self.assertEqual(operational["reinforcement_observation_groups_evaluated"], 6)
        self.assertEqual(operational["reinforcement_events_declared"], 100015)
        self.assertEqual(operational["consolidation_cases_evaluated"], 3)
        self.assertEqual(operational["consolidation_sources_evaluated"], 6)
        self.assertEqual(
            operational["proposal_counts_by_disposition"],
            {
                "keep_active": 1,
                "mandatory_deletion_review": 1,
                "prune_candidate": 2,
                "retention_hold": 2,
            },
        )
        self.assertEqual(
            operational["consolidation_proposal_counts"],
            {"eligible": 1, "ineligible": 2},
        )
        self.assertEqual(operational["persisted_state_growth_bytes"], 0)
        self.assertTrue(operational["stateless_estimator"])
        self.assertTrue(operational["same_instance_replay_consistent"])
        self.assertTrue(operational["fresh_instance_restart_consistent"])
        self.assertTrue(operational["batch_evidence_ref"].startswith("metabolism-batch:sha256:"))
        self.assertEqual(operational["latency"]["measurement"], "not_measured")

    def test_governance_failure_group_is_zero(self) -> None:
        self.assertEqual(
            self._report()["governance_failures"],
            {
                "observed_unauthorized_mutation_attempts": 0,
                "authority_effect_violations": 0,
                "prune_delete_authority_effect_violations": 0,
                "held_memory_prune_violations": 0,
                "mandatory_deletion_routing_failures": 0,
                "scope_currentness_laundering_failures": 0,
                "consolidation_certification_violations": 0,
                "consolidation_authority_effect_violations": 0,
                "score_to_authority_violations": 0,
            },
        )

    def test_deterministic_evidence_is_stable_when_latency_is_not_measured(self) -> None:
        first = self._report()
        second = self._report()
        self.assertEqual(first, second)

    def test_latency_can_be_measured_without_changing_metabolism_evidence(self) -> None:
        ticks = iter((1_000_000, 3_000_000, 5_000_000, 8_000_000))
        timed = RUNNER_MODULE.run_benchmark(
            fixture_path=FIXTURE,
            agent_memory_revision="timed-test-revision",
            measure_latency=True,
            clock_ns=lambda: next(ticks),
        )
        latency = timed["operational_behavior"]["latency"]
        self.assertEqual(latency["measurement"], "wall_clock")
        self.assertEqual(latency["memory_evaluation_ms"], 2.0)
        self.assertEqual(latency["consolidation_evaluation_ms"], 3.0)
        self.assertEqual(latency["total_evaluation_ms"], 5.0)
        self.assertTrue(timed["operational_behavior"]["fresh_instance_restart_consistent"])

    def test_runner_emits_governance_clean_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "memory-metabolism.json"
            subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--agent-memory-revision",
                    "runner-test-revision",
                    "--fixture",
                    str(FIXTURE),
                    "--output",
                    str(output),
                ],
                cwd=ROOT / "reference",
                check=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["agent_memory_revision"], "runner-test-revision")
        self.assertEqual(report["metabolism_quality"]["fixture_expectation_failures"], 0)
        self.assertTrue(report["operational_behavior"]["same_instance_replay_consistent"])
        self.assertTrue(report["operational_behavior"]["fresh_instance_restart_consistent"])
        self.assertFalse(RUNNER_MODULE._governance_failed(report))


if __name__ == "__main__":
    unittest.main()
