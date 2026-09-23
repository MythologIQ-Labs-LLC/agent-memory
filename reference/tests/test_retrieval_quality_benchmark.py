from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agentmem_ref.harness.retrieval_quality_benchmark import run_benchmark


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reference" / "fixtures" / "benchmarks" / "rc-retrieval-quality-v1.json"
RUNTIME_CONFIG = (
    ROOT
    / "reference"
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)
RUNNER = ROOT / "reference" / "run_retrieval_quality_benchmark.py"


class RetrievalQualityBenchmarkTests(unittest.TestCase):
    def _report(self) -> dict:
        return run_benchmark(
            fixture_path=FIXTURE,
            runtime_config_path=RUNTIME_CONFIG,
            agent_memory_revision="test-revision",
        )

    def test_composed_retrieval_improves_recall_without_precision_loss(self) -> None:
        report = self._report()
        lexical = report["systems"]["lexical_only"]["aggregate"]
        multi = report["systems"]["multi_route"]["aggregate"]

        self.assertEqual(lexical["relevant_total"], 7)
        self.assertEqual(lexical["candidate_total"], 3)
        self.assertEqual(lexical["admitted_total"], 3)
        self.assertEqual(lexical["candidate_recall"], 0.428571)
        self.assertEqual(lexical["admitted_recall"], 0.428571)
        self.assertEqual(lexical["admitted_precision"], 1.0)
        self.assertEqual(lexical["mean_reciprocal_rank"], 0.6)

        self.assertEqual(multi["relevant_total"], 7)
        self.assertEqual(multi["candidate_total"], 11)
        self.assertEqual(multi["admitted_total"], 7)
        self.assertEqual(multi["candidate_recall"], 1.0)
        self.assertEqual(multi["admitted_recall"], 1.0)
        self.assertEqual(multi["admitted_precision"], 1.0)
        self.assertEqual(multi["mean_reciprocal_rank"], 1.0)
        self.assertEqual(multi["candidate_noise"], 4)

        comparison = report["comparison"]
        self.assertEqual(comparison["candidate_recall_delta"], 0.571429)
        self.assertEqual(comparison["admitted_recall_delta"], 0.571429)
        self.assertEqual(comparison["admitted_precision_delta"], 0.0)
        self.assertEqual(comparison["mean_reciprocal_rank_delta"], 0.4)
        self.assertEqual(comparison["candidate_amplification"], 8)

    def test_route_contributions_show_exact_and_relational_unique_gains(self) -> None:
        report = self._report()
        multi = report["systems"]["multi_route"]

        self.assertEqual(
            multi["route_contribution_counts"],
            {
                "exact_logical_identity": 3,
                "lexical": 3,
                "shared_evidence_neighbor": 6,
            },
        )
        self.assertEqual(
            multi["unique_recall_gain_by_route"],
            {
                "exact_logical_identity": 2,
                "shared_evidence_neighbor": 2,
            },
        )

    def test_governance_failures_remain_zero_despite_candidate_amplification(self) -> None:
        report = self._report()
        self.assertEqual(
            report["governance"],
            {
                "lexical_forbidden_admission_failures": 0,
                "multi_route_forbidden_admission_failures": 0,
                "multi_route_forbidden_ranked_failures": 0,
                "route_authority_effect_violations": 0,
            },
        )

        rows = {
            row["case_id"]: row
            for row in report["systems"]["multi_route"]["cases"]
        }
        relational = rows["shared-evidence-neighbor-rescue"]
        self.assertEqual(
            relational["result"]["admitted"],
            ["memory:deploy-window", "memory:deploy-belief"],
        )
        self.assertEqual(
            relational["result"]["refusals"],
            {
                "memory:foreign-related": "required_isolation_domain_missing",
                "memory:stale-related": "superseded_not_current",
            },
        )
        self.assertNotIn(
            "memory:foreign-related",
            relational["result"]["ranked_admitted"],
        )
        self.assertNotIn(
            "memory:stale-related",
            relational["result"]["ranked_admitted"],
        )

    def test_report_is_deterministic_and_binds_inputs(self) -> None:
        first = self._report()
        second = self._report()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "1.0.0")
        self.assertEqual(first["benchmark_id"], "agent-memory-rc-retrieval-quality")
        self.assertEqual(first["benchmark_version"], "1.0.0")
        self.assertEqual(first["agent_memory_revision"], "test-revision")
        self.assertTrue(first["fixture"]["sha256"].startswith("sha256:"))
        self.assertTrue(first["runtime_configuration"]["sha256"].startswith("sha256:"))
        self.assertEqual(first["fixture"]["memory_count"], 6)
        self.assertEqual(first["fixture"]["case_count"], 5)

    def test_runner_emits_same_report_and_enforces_governance_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "retrieval-quality.json"
            subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--agent-memory-revision",
                    "test-revision",
                    "--fixture",
                    str(FIXTURE),
                    "--runtime-config",
                    str(RUNTIME_CONFIG),
                    "--output",
                    str(output),
                ],
                cwd=ROOT / "reference",
                check=True,
            )
            emitted = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(emitted, self._report())


if __name__ == "__main__":
    unittest.main()
