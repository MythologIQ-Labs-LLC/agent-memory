from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

RUNNER = REFERENCE / "run_swe_context_bench_real_100.py"
FIXTURE_ROOT = REFERENCE / "fixtures" / "benchmarks" / "swe-context-bench"
RUNTIME_CONFIG = (
    REFERENCE
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)
EVIDENCE_PROFILE = (
    REFERENCE
    / "fixtures"
    / "benchmarks"
    / "swe-context-bench-rc-profile-v1.json"
)


def _runner_module():
    spec = importlib.util.spec_from_file_location("run_swe_context_bench_real_100", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER_MODULE = _runner_module()


class SweContextBenchReal100Tests(unittest.TestCase):
    def _public_shape_manifest(self) -> dict:
        experiences = [
            {
                "instance_id": f"exp-{index:03d}",
                "repo": "acme/repo",
                "path": f"experiences/exp-{index:03d}.jsonl",
            }
            for index in range(300)
        ]
        queries = []
        gold_cursor = 0
        for index in range(99):
            gold_count = 2 if index == 0 else 1
            golds = [f"exp-{cursor:03d}" for cursor in range(gold_cursor, gold_cursor + gold_count)]
            gold_cursor += gold_count
            queries.append(
                {
                    "related_instance_id": f"query-{index:03d}",
                    "repo": "acme/repo",
                    "path": f"queries/query-{index:03d}.json",
                    "batch_id": "batch-main",
                    "gold_experience_instance_ids": golds,
                }
            )
        self.assertEqual(gold_cursor, 100)
        return {
            "schema_version": "2.0.0",
            "corpus_class": "external_public_lite",
            "selection_protocol": "gold_plus_up_to_2_same_repo_non_gold",
            "experiences": experiences,
            "batches": [
                {
                    "batch_id": "batch-main",
                    "experience_instance_ids": [row["instance_id"] for row in experiences],
                }
            ],
            "queries": queries,
            "consistency_related_instance_ids": [f"query-{index:03d}" for index in range(10)],
        }

    def test_public_manifest_requires_99_queries_and_100_gold_edges(self) -> None:
        manifest = self._public_shape_manifest()
        validated = RUNNER_MODULE._validate_real_manifest(manifest)
        self.assertEqual(len(validated["queries"]), 99)
        self.assertEqual(
            sum(len(row["gold_experience_instance_ids"]) for row in validated["queries"]),
            100,
        )
        self.assertEqual(
            sum(len(row["gold_experience_instance_ids"]) == 2 for row in validated["queries"]),
            1,
        )

    def test_public_manifest_rejects_collapsed_99_edge_denominator(self) -> None:
        manifest = self._public_shape_manifest()
        manifest["queries"][0]["gold_experience_instance_ids"] = ["exp-000"]
        with self.assertRaisesRegex(ValueError, "exactly 100 gold edges"):
            RUNNER_MODULE._validate_real_manifest(manifest)

    def test_multi_gold_metrics_are_edge_level_and_ndcg_uses_multi_relevance(self) -> None:
        metrics = RUNNER_MODULE._quality_metrics(
            [
                {
                    "gold_experience_instance_ids": ["gold-a", "gold-b"],
                    "candidate_experience_ids": ["gold-a", "noise-a", "gold-b"],
                    "retrieved_experience_ids": ["gold-a", "noise-a", "gold-b"],
                },
                {
                    "gold_experience_instance_ids": ["gold-c"],
                    "candidate_experience_ids": ["noise-b"],
                    "retrieved_experience_ids": ["noise-b"],
                },
            ]
        )
        self.assertEqual(metrics["query_count"], 2)
        self.assertEqual(metrics["gold_edge_count"], 3)
        self.assertEqual(metrics["candidate_gold_hit_count"], 2)
        self.assertEqual(metrics["candidate_recall"], 0.666667)
        self.assertEqual(metrics["candidate_noise_count"], 2)
        self.assertEqual(metrics["final_gold_hit_count"], 2)
        self.assertEqual(metrics["final_admitted_recall"], 0.666667)
        self.assertEqual(metrics["final_admitted_precision"], 0.5)
        self.assertEqual(metrics["final_admitted_f1"], 0.571429)
        self.assertEqual(metrics["false_admission_count"], 2)
        self.assertEqual(metrics["false_refusal_count"], 1)
        self.assertEqual(metrics["ndcg_at_1"], 0.5)
        self.assertEqual(metrics["ndcg_at_3"], 0.45986)

    def test_batch_must_contain_every_gold_experience(self) -> None:
        manifest = self._public_shape_manifest()
        manifest["batches"][0]["experience_instance_ids"].remove("exp-001")
        with self.assertRaisesRegex(ValueError, "absent from batch"):
            RUNNER_MODULE._validate_real_manifest(manifest)

    def test_synthetic_execution_supports_two_gold_edges_on_one_query(self) -> None:
        manifest = {
            "schema_version": "2.0.0",
            "upstream_repository": "jiayuanz3/SWEContextBench",
            "upstream_revision": "synthetic-fixture",
            "corpus_class": "synthetic",
            "selection_protocol": "gold_plus_up_to_2_same_repo_non_gold",
            "fixture_provenance_status": "synthetic",
            "selection_provenance_status": "synthetic",
            "experiences": [
                {
                    "instance_id": "acme__web-100",
                    "repo": "acme/web",
                    "path": "experiences/cache.jsonl",
                },
                {
                    "instance_id": "acme__web-200",
                    "repo": "acme/web",
                    "path": "experiences/migration.jsonl",
                },
            ],
            "batches": [
                {
                    "batch_id": "synthetic-batch",
                    "experience_instance_ids": ["acme__web-100", "acme__web-200"],
                }
            ],
            "queries": [
                {
                    "related_instance_id": "acme__web-300",
                    "repo": "acme/web",
                    "path": "queries/cache-related.json",
                    "batch_id": "synthetic-batch",
                    "gold_experience_instance_ids": ["acme__web-100", "acme__web-200"],
                }
            ],
            "consistency_related_instance_ids": ["acme__web-300"],
        }
        with tempfile.TemporaryDirectory() as temp:
            manifest_path = Path(temp) / "manifest-v2.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = RUNNER_MODULE.run_real_100_edge_benchmark(
                manifest_path=manifest_path,
                benchmark_root=FIXTURE_ROOT,
                runtime_config_path=RUNTIME_CONFIG,
                evidence_profile_path=EVIDENCE_PROFILE,
                agent_memory_revision="frozen-real-100-test-revision",
                consistency_repeat_count=5,
            )

        self.assertEqual(report["schema_version"], "1.0.0")
        self.assertEqual(report["quality"]["query_count"], 1)
        self.assertEqual(report["quality"]["gold_edge_count"], 2)
        self.assertEqual(len(report["queries"]), 1)
        self.assertEqual(
            report["queries"][0]["gold_experience_instance_ids"],
            ["acme__web-100", "acme__web-200"],
        )
        self.assertEqual(report["governance"]["authority_effect"], "none")
        self.assertEqual(report["consistency"]["repeat_count"], 5)
        self.assertFalse(report["comparability"]["public_99_query_100_edge_shape_valid"])
        self.assertEqual(
            report["comparability"]["external_reference_status"],
            "not-yet-comparable-input-provenance",
        )
        self.assertEqual(report["claim_boundary"]["aggregate_health_score"], "not_defined")
        self.assertTrue(report["claim_boundary"]["no_new_retrieval_engine"])


if __name__ == "__main__":
    unittest.main()
