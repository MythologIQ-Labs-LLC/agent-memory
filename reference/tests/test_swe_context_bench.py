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
            agent_memory_revision="frozen-test-revision",
            lexical_anchor_limit=3,
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

    def test_binary_gold_edge_recovery_uses_same_repo_distractors(self) -> None:
        report = self._report()
        self.assertEqual(report["score_protocol"], "binary_gold_edge_recovery")
        self.assertEqual(report["corpus"]["experience_count"], 2)
        self.assertEqual(report["corpus"]["repo_count"], 1)
        self.assertFalse(report["corpus"]["instance_ids_in_memory_text"])
        self.assertEqual(report["aggregate"]["query_count"], 1)
        self.assertEqual(report["aggregate"]["hit_count"], 1)
        self.assertEqual(report["aggregate"]["hit_rate"], 1.0)
        row = report["queries"][0]
        self.assertTrue(row["agent_memory"]["hit"])
        self.assertEqual(
            row["agent_memory"]["retrieved_experience_ids"][0],
            "acme__web-100",
        )
        self.assertEqual(row["gold_experience_instance_id"], "acme__web-100")

    def test_queries_do_not_mutate_candidate_corpus_or_gain_authority(self) -> None:
        report = self._report()
        self.assertEqual(report["governance"]["corpus_mutation_failures"], 0)
        self.assertEqual(report["governance"]["route_authority_effect_violations"], 0)
        self.assertTrue(report["queries"][0]["corpus_immutable"])

    def test_report_binds_exact_inputs_and_revision(self) -> None:
        report = self._report()
        self.assertEqual(report["agent_memory_revision"], "frozen-test-revision")
        self.assertTrue(report["inputs"]["manifest_sha256"].startswith("sha256:"))
        self.assertTrue(report["inputs"]["runtime_config_sha256"].startswith("sha256:"))
        self.assertEqual(
            set(report["inputs"]["file_sha256"]),
            {
                "experiences/cache.jsonl",
                "experiences/migration.jsonl",
                "queries/cache-related.json",
            },
        )
        self.assertEqual(
            report["claim_boundary"]["ranking"],
            "gold rank is diagnostic only; primary score is binary hit rate",
        )

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
                    "--agent-memory-revision",
                    "frozen-test-revision",
                    "--output",
                    str(output),
                ],
                cwd=ROOT / "reference",
                check=True,
            )
            emitted = json.loads(output.read_text(encoding="utf-8"))
        expected = self._report()
        self.assertEqual(
            emitted["aggregate"]["hit_rate"],
            expected["aggregate"]["hit_rate"],
        )
        self.assertEqual(emitted["governance"], expected["governance"])
        self.assertEqual(
            emitted["inputs"]["manifest_sha256"],
            expected["inputs"]["manifest_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
