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
        self.assertTrue(all(probe["detected"] for probe in report["profiles"]["swe_contextbench"]["probes"]))

    def test_baseline_is_clean_and_multi_gold_denominator_is_preserved(self) -> None:
        report = mutants.run_mutation_probes()["profiles"]["swe_contextbench"]
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
        report = mutants.run_mutation_probes()["profiles"]["swe_contextbench"]
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


class LongMemEvalIntegrityProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = mutants.run_mutation_probes()["profiles"]["longmemeval"]
        self.probes = {probe["name"]: probe for probe in self.profile["probes"]}

    def test_profile_uses_the_real_longmemeval_evaluator_and_clean_baseline(self) -> None:
        self.assertIn("run_longmemeval.score_record", self.profile["evaluator"])
        baseline = self.profile["baseline"]
        self.assertEqual(set(baseline["headline"].values()), {1.0})
        self.assertEqual(baseline["evaluated_question_count"], 3)
        self.assertEqual(baseline["latest_gold_ranked_first_rate"], 1.0)
        self.assertEqual(baseline["out_of_corpus_returned_count"], 0)

    def test_every_semantic_mutation_is_detected(self) -> None:
        expected = {
            "missing_gold",
            "irrelevant_ahead",
            "rank_below_cutoff",
            "stale_over_current",
            "suppressed_abstention",
            "identity_mapping_corruption",
            "cross_scope_injection",
        }
        detected = {name for name, probe in self.probes.items() if probe["expected_detection"] and probe["detected"]}
        self.assertEqual(detected, expected)
        self.assertTrue(self.profile["all_detected"])

    def test_currentness_damage_is_separate_from_recall(self) -> None:
        stale = self.probes["stale_over_current"]["metrics"]
        self.assertLess(stale["latest_gold_ranked_first_rate"], 1.0)
        self.assertEqual(stale["headline"]["recall_all@5"], 1.0)

    def test_upstream_rank_one_ndcg_insensitivity_is_recorded_not_hidden(self) -> None:
        probe = self.probes["irrelevant_at_rank_one"]
        self.assertFalse(probe["expected_detection"])
        self.assertFalse(probe["detected"])
        self.assertEqual(self.profile["known_insensitivities"], ["irrelevant_at_rank_one"])
        self.assertTrue(self.profile["known_insensitivities_confirmed"])



class AgentMemBenchIntegrityProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = mutants.run_mutation_probes()["profiles"]["agentmembench_memdialogue"]

    def test_clean_baseline(self) -> None:
        baseline = self.profile["baseline"]
        self.assertEqual(baseline["new_fact_rate"], 1.0)
        self.assertEqual(baseline["staleness_rate"], 0.0)
        self.assertEqual(baseline["cross_user_leak_rate"], 0.0)
        self.assertEqual(baseline["audited_deletion_rate"], 1.0)
        self.assertEqual(baseline["scale_recall_at_3"], 1.0)

    def test_every_backend_misbehavior_is_detected(self) -> None:
        names = {probe["name"] for probe in self.profile["probes"] if probe["detected"]}
        self.assertEqual(
            names,
            {"stale_over_current", "cross_user_leak", "deletion_ignored", "write_dropped", "identity_mapping_corruption"},
        )
        self.assertTrue(self.profile["all_detected"])
        self.assertIn("retrieval", self.profile["not_probed"])

    def test_every_profile_is_exercised(self) -> None:
        profiles = mutants.run_mutation_probes()["profiles"]
        self.assertEqual(set(profiles), {"swe_contextbench", "longmemeval", "agentmembench_memdialogue"})
        self.assertTrue(all(profile["all_detected"] for profile in profiles.values()))


if __name__ == "__main__":
    unittest.main()
