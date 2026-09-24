from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "reference" / "fixtures" / "benchmarks" / "swe-context-bench"
MANIFEST = FIXTURE_ROOT / "manifest.json"
EVIDENCE_PROFILE = (
    ROOT
    / "reference"
    / "fixtures"
    / "benchmarks"
    / "swe-context-bench-rc-profile-v1.json"
)
RUNTIME_CONFIG = (
    ROOT
    / "reference"
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)
RUNNER = ROOT / "reference" / "run_swe_context_bench.py"


def _runner_module():
    spec = importlib.util.spec_from_file_location("run_swe_context_bench", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER_MODULE = _runner_module()


class SweContextBenchTests(unittest.TestCase):
    def _report(self) -> dict:
        return RUNNER_MODULE.run_benchmark(
            manifest_path=MANIFEST,
            benchmark_root=FIXTURE_ROOT,
            runtime_config_path=RUNTIME_CONFIG,
            evidence_profile_path=EVIDENCE_PROFILE,
            agent_memory_revision="frozen-test-revision",
            lexical_anchor_limit=3,
            consistency_repeat_count=5,
            consistency_query_limit=10,
        )

    def test_experience_projection_drops_benchmark_identity_and_raw_tool_state(self) -> None:
        projection = RUNNER_MODULE.parse_experience(
            FIXTURE_ROOT / "experiences" / "cache.jsonl"
        )
        self.assertEqual(projection.instance_id, "acme__web-100")
        self.assertEqual(projection.repo, "acme/web")
        retained_text = "\n".join(text for _kind, text in projection.fragments)
        self.assertNotIn("acme__web-100", retained_text)
        self.assertNotIn("instance_id", retained_text)
        self.assertNotIn("abc123", retained_text)
        self.assertNotIn("file-history-snapshot", retained_text)
        self.assertIn("Template renderer returns stale content", retained_text)
        self.assertIn("Template loader cache invalidation", retained_text)
        self.assertIn("timestamp-aware cache invalidation", retained_text)

    def test_gold_edge_recovery_uses_same_repo_distractors(self) -> None:
        report = self._report()
        self.assertEqual(
            report["score_protocol"],
            "swe_context_bench_lite_gold_edge_retrieval_v1",
        )
        self.assertEqual(report["corpus"]["experience_count"], 2)
        self.assertEqual(report["corpus"]["repo_count"], 1)
        self.assertFalse(report["corpus"]["instance_ids_in_memory_text"])
        self.assertEqual(report["aggregate"]["query_count"], 1)
        self.assertEqual(report["aggregate"]["hit_count"], 1)
        self.assertEqual(report["aggregate"]["hit_rate"], 1.0)
        row = report["queries"][0]
        self.assertTrue(row["agent_memory"]["candidate_hit"])
        self.assertTrue(row["agent_memory"]["hit"])
        self.assertEqual(
            row["agent_memory"]["retrieved_experience_ids"][0],
            "acme__web-100",
        )
        self.assertEqual(row["gold_experience_instance_id"], "acme__web-100")

    def test_metric_contract_separates_candidate_and_final_admission(self) -> None:
        rows = [
            {
                "gold_experience_instance_id": "gold-a",
                "agent_memory": {
                    "candidate_experience_ids": ["gold-a", "noise"],
                    "retrieved_experience_ids": ["noise", "gold-a"],
                    "gold_rank_diagnostic": 2,
                },
            },
            {
                "gold_experience_instance_id": "gold-b",
                "agent_memory": {
                    "candidate_experience_ids": ["noise"],
                    "retrieved_experience_ids": ["noise"],
                    "gold_rank_diagnostic": None,
                },
            },
        ]
        metrics = RUNNER_MODULE._retrieval_metrics(rows)
        self.assertEqual(metrics["candidate_recall"], 0.5)
        self.assertEqual(metrics["candidate_experience_total"], 3)
        self.assertEqual(metrics["candidate_noise_count"], 2)
        self.assertEqual(metrics["final_admitted_recall"], 0.5)
        self.assertEqual(metrics["final_admitted_precision"], 0.333333)
        self.assertEqual(metrics["final_admitted_f1"], 0.4)
        self.assertEqual(metrics["false_admission_count"], 2)
        self.assertEqual(metrics["false_refusal_count"], 1)
        self.assertEqual(metrics["ndcg_at_1"], 0.0)
        self.assertEqual(metrics["ndcg_at_3"], 0.315465)

    def test_pairwise_jaccard_is_explicit_and_deterministic(self) -> None:
        score = RUNNER_MODULE._mean_pairwise_jaccard(
            [["a", "b"], ["a", "b"], ["a"]]
        )
        self.assertEqual(score, 0.666667)
        self.assertEqual(RUNNER_MODULE._mean_pairwise_jaccard([["a"]]), None)

    def test_queries_do_not_mutate_candidate_corpus_or_gain_authority(self) -> None:
        report = self._report()
        self.assertEqual(report["governance"]["corpus_mutation_failures"], 0)
        self.assertEqual(report["governance"]["route_authority_effect_violations"], 0)
        self.assertEqual(report["governance"]["authority_effect"], "none")
        self.assertTrue(report["queries"][0]["corpus_immutable"])
        self.assertEqual(
            report["governance"]["ir_false_admission_count"],
            report["quality"]["false_admission_count"],
        )
        self.assertEqual(
            report["governance"]["ir_false_refusal_count"],
            report["quality"]["false_refusal_count"],
        )

    def test_repeated_run_consistency_is_reported_without_restart_claim(self) -> None:
        report = self._report()
        self.assertEqual(report["consistency"]["query_count"], 1)
        self.assertEqual(report["consistency"]["repeat_count"], 5)
        self.assertEqual(report["consistency"]["mean_pairwise_jaccard"], 1.0)
        self.assertFalse(report["consistency"]["persisted_restart_claimed"])
        row = report["queries"][0]["consistency"]
        self.assertTrue(row["included"])
        self.assertEqual(row["repeat_count"], 5)
        self.assertEqual(len(row["admitted_experience_id_sets"]), 5)
        self.assertEqual(row["mean_pairwise_jaccard"], 1.0)

    def test_report_binds_exact_inputs_profile_and_revision(self) -> None:
        report = self._report()
        self.assertEqual(report["schema_version"], "1.1.0")
        self.assertEqual(report["agent_memory_revision"], "frozen-test-revision")
        self.assertTrue(report["inputs"]["manifest_sha256"].startswith("sha256:"))
        self.assertTrue(report["inputs"]["runtime_config_sha256"].startswith("sha256:"))
        self.assertTrue(report["inputs"]["evidence_profile_sha256"].startswith("sha256:"))
        self.assertEqual(
            set(report["inputs"]["file_sha256"]),
            {
                "experiences/cache.jsonl",
                "experiences/migration.jsonl",
                "queries/cache-related.json",
            },
        )
        self.assertEqual(
            report["benchmark_profile"]["profile_id"],
            "swe-context-bench-lite-bicameral-retrieval-v1",
        )
        self.assertEqual(
            report["benchmark_profile"]["historical_agent_memory"]["provenance_status"],
            "historical_metadata_only",
        )
        self.assertFalse(
            report["benchmark_profile"]["historical_agent_memory"]["directly_comparable"]
        )
        self.assertEqual(report["metric_contract"]["aggregate_health_score"], "not_defined")
        self.assertNotIn("health_score", report)
        self.assertTrue(report["corpus"]["synthetic_fixture"])
        self.assertEqual(
            report["comparability"]["external_reference_status"],
            "not-comparable-synthetic-fixture",
        )
        self.assertTrue(
            report["claim_boundary"]["synthetic_fixture_cannot_substitute_for_public_corpus"]
        )
        self.assertIn("nDCG", report["claim_boundary"]["ranking"])

    def test_performance_semantics_do_not_invent_unavailable_call_counts(self) -> None:
        report = self._report()
        performance = report["performance"]
        self.assertEqual(performance["successful_scored_query_count"], 1)
        self.assertGreaterEqual(performance["corpus_build_seconds_total"], 0.0)
        self.assertGreaterEqual(performance["median_successful_scored_query_ms"], 0.0)
        self.assertEqual(
            performance["token_or_model_call_counts"],
            "not_exposed_by_this_runner",
        )
        self.assertIn("first scored Agent Memory query pass", performance["timing_semantics"])

    def test_runner_emits_the_same_semantic_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "swe-context.json"
            subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--manifest",
                    str(MANIFEST),
                    "--benchmark-root",
                    str(FIXTURE_ROOT),
                    "--runtime-config",
                    str(RUNTIME_CONFIG),
                    "--evidence-profile",
                    str(EVIDENCE_PROFILE),
                    "--agent-memory-revision",
                    "frozen-test-revision",
                    "--consistency-repeat-count",
                    "5",
                    "--output",
                    str(output),
                ],
                cwd=ROOT / "reference",
                check=True,
            )
            emitted = json.loads(output.read_text(encoding="utf-8"))
        expected = self._report()
        self.assertEqual(emitted["quality"], expected["quality"])
        self.assertEqual(emitted["governance"], expected["governance"])
        self.assertEqual(emitted["consistency"], expected["consistency"])
        self.assertEqual(
            emitted["inputs"]["manifest_sha256"],
            expected["inputs"]["manifest_sha256"],
        )
        self.assertEqual(
            emitted["comparability"]["signature"],
            expected["comparability"]["signature"],
        )


if __name__ == "__main__":
    unittest.main()
