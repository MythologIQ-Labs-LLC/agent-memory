from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.harness.retrieval_quality_benchmark import run_benchmark
from retrieval_regression import (
    compare_reports,
    enrich_admitted_f1,
    load_json,
    run_continuous_regression,
    run_sqlite_persisted_restart_probe,
)

FIXTURE = ROOT / "reference" / "fixtures" / "benchmarks" / "rc-retrieval-quality-v1.json"
RUNTIME_CONFIG = (
    ROOT
    / "reference"
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)
TARGETS = ROOT / "reference" / "fixtures" / "benchmarks" / "retrieval-regression-targets-v1.json"
HISTORICAL = ROOT / "reference" / "fixtures" / "benchmarks" / "historical-jin-100-gold-edges-v1.json"
RUNNER = ROOT / "reference" / "run_retrieval_quality_benchmark.py"


class ContinuousRetrievalRegressionTests(unittest.TestCase):
    def _base_report(self, revision: str = "baseline-revision") -> dict:
        return run_benchmark(
            fixture_path=FIXTURE,
            runtime_config_path=RUNTIME_CONFIG,
            agent_memory_revision=revision,
        )

    def test_enrichment_keeps_candidate_and_final_metrics_distinct(self) -> None:
        report = enrich_admitted_f1(self._base_report())
        lexical = report["systems"]["lexical_only"]["aggregate"]
        multi = report["systems"]["multi_route"]["aggregate"]
        self.assertEqual(multi["candidate_recall"], 1.0)
        self.assertEqual(multi["admitted_recall"], 1.0)
        self.assertEqual(multi["admitted_precision"], 1.0)
        self.assertEqual(multi["admitted_f1"], 1.0)
        self.assertEqual(multi["false_admission_count"], 0)
        self.assertEqual(multi["false_refusal_count"], 0)
        self.assertEqual(lexical["false_admission_count"], 0)
        self.assertEqual(lexical["false_refusal_count"], 4)
        self.assertIn("candidate_recall", report["metric_contract"]["candidate_generation"])
        self.assertIn("admitted_f1", report["metric_contract"]["final_governed_admission"])
        self.assertIn("false_admission_count", report["metric_contract"]["final_governed_admission"])
        self.assertIn("false_refusal_count", report["metric_contract"]["final_governed_admission"])
        self.assertEqual(report["metric_contract"]["aggregate_health_score"], "not_defined")

        refusal_counts = report["governance_evidence"]["multi_route"]["refusal_reason_counts"]
        # Contract 1.3.0 (#548): domain-ineligible matches never become candidates, so no
        # isolation refusal is recorded. In-domain lifecycle refusals stay visible as evidence.
        self.assertEqual(refusal_counts.get("required_isolation_domain_missing", 0), 0)
        self.assertGreater(refusal_counts.get("superseded_not_current", 0), 0)
        self.assertEqual(report["governance_evidence"]["multi_route"]["authority_effect"], "none")

    def test_correct_refusals_are_evidence_not_governance_failures(self) -> None:
        report = enrich_admitted_f1(self._base_report())
        refusal_counts = report["governance_evidence"]["multi_route"]["refusal_reason_counts"]
        self.assertGreater(sum(refusal_counts.values()), 0)
        self.assertTrue(all(value == 0 for value in report["governance"].values()))

    def test_compatible_revision_comparison_classifies_each_metric(self) -> None:
        baseline = enrich_admitted_f1(self._base_report("older-revision"))
        current = enrich_admitted_f1(self._base_report("newer-revision"))
        comparison = compare_reports(current, baseline)
        self.assertEqual(comparison["status"], "comparable")
        self.assertEqual(comparison["baseline_revision"], "older-revision")
        self.assertEqual(comparison["current_revision"], "newer-revision")
        self.assertTrue(
            all(
                row["classification"] == "unchanged"
                for row in comparison["metrics"].values()
            )
        )

    def test_changed_fixture_digest_is_not_comparable(self) -> None:
        baseline = enrich_admitted_f1(self._base_report())
        current = enrich_admitted_f1(self._base_report("newer-revision"))
        baseline["fixture"]["sha256"] = "sha256:different-fixture"
        comparison = compare_reports(current, baseline)
        self.assertEqual(comparison["status"], "not-comparable")
        self.assertEqual(comparison["reason"], "benchmark_contract_mismatch")
        self.assertIn("fixture_sha256", comparison["mismatched_fields"])

    def test_sqlite_persisted_restart_preserves_bounded_recall_results(self) -> None:
        probe = run_sqlite_persisted_restart_probe(
            fixture_path=FIXTURE,
            runtime_config_path=RUNTIME_CONFIG,
        )
        self.assertEqual(probe["profile"], "sqlite_lexical_exact_shared_evidence_v1")
        self.assertEqual(
            probe["route_scope"],
            ["lexical", "exact_logical_identity", "shared_evidence_neighbor"],
        )
        self.assertTrue(probe["persisted_restart_exercised"])
        self.assertTrue(probe["canonical_state_digest_consistent"])
        self.assertTrue(probe["recall_result_consistent"])
        self.assertEqual(probe["case_count"], 5)
        self.assertFalse(probe["vector_persistence_claimed"])
        self.assertFalse(probe["typed_graph_persistence_claimed"])
        self.assertEqual(probe["authority_effect"], "none")

    def test_continuous_regression_proves_replay_and_preserves_historical_baseline(self) -> None:
        report = run_continuous_regression(
            fixture_path=FIXTURE,
            runtime_config_path=RUNTIME_CONFIG,
            agent_memory_revision="regression-test-revision",
            targets=load_json(TARGETS) or {},
            historical_baseline=load_json(HISTORICAL),
        )
        regression = report["continuous_regression"]
        self.assertTrue(regression["same_process_repeat_consistent"])
        self.assertTrue(regression["fresh_runtime_reconstruction_consistent"])
        self.assertTrue(regression["persisted_restart_exercised_by_this_runner"])
        self.assertTrue(regression["persisted_restart"]["canonical_state_digest_consistent"])
        self.assertTrue(regression["persisted_restart"]["recall_result_consistent"])
        self.assertFalse(regression["persisted_restart"]["vector_persistence_claimed"])
        self.assertFalse(regression["persisted_restart"]["typed_graph_persistence_claimed"])
        self.assertEqual(
            regression["reconstruction_posture"],
            "fresh_fixture_rebuild_from_canonical_inputs",
        )
        self.assertTrue(regression["targets"]["all_expectations_met"])
        self.assertEqual(regression["baseline_comparison"]["status"], "not-requested")
        historical = regression["historical_baselines"][0]
        self.assertEqual(historical["dataset"]["gold_edge_count"], 100)
        self.assertEqual(historical["reported_metrics"]["recall"], 1.0)
        self.assertEqual(historical["reported_metrics"]["precision"], 0.06)
        self.assertEqual(historical["reported_metrics"]["f1"], 0.1)
        self.assertEqual(historical["reported_metrics"]["metric_layer"], "not_bound_in_source_context")

    def test_runner_continuous_mode_emits_regression_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "retrieval-regression.json"
            subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--agent-memory-revision",
                    "runner-regression-revision",
                    "--continuous-regression",
                    "--fixture",
                    str(FIXTURE),
                    "--runtime-config",
                    str(RUNTIME_CONFIG),
                    "--targets",
                    str(TARGETS),
                    "--historical-baseline",
                    str(HISTORICAL),
                    "--output",
                    str(output),
                ],
                cwd=ROOT / "reference",
                check=True,
            )
            emitted = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(emitted["agent_memory_revision"], "runner-regression-revision")
        self.assertEqual(emitted["systems"]["multi_route"]["aggregate"]["admitted_f1"], 1.0)
        self.assertEqual(emitted["systems"]["multi_route"]["aggregate"]["false_admission_count"], 0)
        self.assertEqual(emitted["systems"]["multi_route"]["aggregate"]["false_refusal_count"], 0)
        self.assertTrue(emitted["continuous_regression"]["targets"]["all_expectations_met"])
        self.assertTrue(
            emitted["continuous_regression"]["persisted_restart_exercised_by_this_runner"]
        )
        self.assertNotIn("health_score", emitted)
        self.assertNotIn("memory_health_score", emitted)


if __name__ == "__main__":
    unittest.main()
