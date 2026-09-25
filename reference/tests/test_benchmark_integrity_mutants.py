from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

import run_benchmark_integrity_mutants as mutants


class BenchmarkIntegrityMutantTests(unittest.TestCase):
    def test_all_controlled_mutations_are_detected(self) -> None:
        report = mutants.run_mutation_probes()
        self.assertTrue(report["all_detected"])
        self.assertTrue(all(probe["detected"] for probe in report["probes"]))

    def test_baseline_is_clean_and_multi_gold_denominator_is_preserved(self) -> None:
        report = mutants.run_mutation_probes()
        baseline = report["baseline"]
        self.assertEqual(baseline["gold_edge_count"], 3)
        self.assertEqual(baseline["final_admitted_recall"], 1.0)
        self.assertEqual(baseline["final_admitted_precision"], 1.0)
        self.assertEqual(baseline["false_admission_count"], 0)
        self.assertEqual(baseline["false_refusal_count"], 0)

        missing_gold = next(
            probe for probe in report["probes"] if probe["name"] == "missing_gold"
        )
        self.assertEqual(missing_gold["metrics"]["gold_edge_count"], 3)
        self.assertEqual(missing_gold["metrics"]["false_refusal_count"], 1)

    def test_candidate_and_final_admission_metrics_do_not_collapse(self) -> None:
        report = mutants.run_mutation_probes()
        refusal = next(
            probe for probe in report["probes"] if probe["name"] == "admission_refusal"
        )
        self.assertEqual(
            refusal["metrics"]["candidate_recall"],
            report["baseline"]["candidate_recall"],
        )
        self.assertLess(
            refusal["metrics"]["final_admitted_recall"],
            report["baseline"]["final_admitted_recall"],
        )

    def test_mutation_probe_is_not_a_benchmark_claim(self) -> None:
        report = mutants.run_mutation_probes()
        boundary = report["claim_boundary"]
        self.assertFalse(boundary["benchmark_result"])
        self.assertFalse(boundary["external_comparability"])
        self.assertEqual(boundary["memory_authority_effect"], "none")
        self.assertFalse(boundary["mutant_detection_proves_real_world_quality"])


if __name__ == "__main__":
    unittest.main()
