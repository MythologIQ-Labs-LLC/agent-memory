from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

FIXTURE_ROOT = REFERENCE / "fixtures" / "benchmarks" / "swe-context-bench"
MANIFEST = FIXTURE_ROOT / "manifest.json"
EVIDENCE_PROFILE = (
    REFERENCE
    / "fixtures"
    / "benchmarks"
    / "swe-context-bench-rc-profile-v1.json"
)
RUNTIME_CONFIG = (
    REFERENCE
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)
RUNNER = REFERENCE / "run_swe_context_bench_harness.py"


def _runner_module():
    spec = importlib.util.spec_from_file_location("run_swe_context_bench_harness", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER_MODULE = _runner_module()


class SweContextBenchHarnessTests(unittest.TestCase):
    def _report(self) -> dict:
        return RUNNER_MODULE.run_harness(
            manifest_path=MANIFEST,
            benchmark_root=FIXTURE_ROOT,
            runtime_config_path=RUNTIME_CONFIG,
            evidence_profile_path=EVIDENCE_PROFILE,
            agent_memory_revision="frozen-test-revision",
            lexical_top_k=1,
            lexical_anchor_limit=3,
            consistency_repeat_count=2,
        )

    def test_default_fixture_compares_three_backends(self) -> None:
        report = self._report()
        self.assertEqual(
            set(report["backends"]),
            {"no_memory", "lexical_overlap", "agent_memory"},
        )
        self.assertEqual(
            report["backends"]["no_memory"]["quality"]["final_admitted_recall"],
            0.0,
        )
        self.assertEqual(
            report["backends"]["lexical_overlap"]["quality"]["final_admitted_recall"],
            1.0,
        )
        self.assertEqual(
            report["backends"]["lexical_overlap"]["quality"]["final_admitted_precision"],
            1.0,
        )
        self.assertEqual(
            report["backends"]["agent_memory"]["quality"]["final_admitted_recall"],
            1.0,
        )
        governance = report["backends"]["agent_memory"]["governance"]
        self.assertEqual(governance["corpus_mutation_failures"], 0)
        self.assertEqual(governance["route_authority_effect_violations"], 0)

    def test_synthetic_fixture_remains_explicitly_non_comparable(self) -> None:
        report = self._report()
        self.assertTrue(report["comparability"]["synthetic_fixture"])
        self.assertEqual(
            report["comparability"]["external_reference_status"],
            "not-comparable-synthetic-fixture",
        )
        self.assertEqual(report["comparison"]["aggregate_health_score"], "not_defined")
        self.assertFalse(report["claim_boundary"]["benchmark_score_is_authority"])

    def test_lexical_baseline_is_deterministic(self) -> None:
        manifest = RUNNER_MODULE._load_manifest(MANIFEST)
        documents, _hashes = RUNNER_MODULE._experience_documents(manifest, FIXTURE_ROOT)
        cases, _query_hashes = RUNNER_MODULE._query_cases(manifest, FIXTURE_ROOT, documents)
        first = RUNNER_MODULE._lexical_rank(cases[0], documents, top_k=2)
        second = RUNNER_MODULE._lexical_rank(cases[0], documents, top_k=2)
        self.assertEqual(first, second)
        self.assertEqual(first[0], "acme__web-100")

    def test_multi_gold_quality_is_edge_based(self) -> None:
        quality = RUNNER_MODULE._quality(
            [
                {
                    "gold_experience_instance_ids": ["gold-a", "gold-b"],
                    "candidate_experience_ids": ["gold-a", "noise"],
                    "retrieved_experience_ids": ["gold-a", "noise"],
                }
            ]
        )
        self.assertEqual(quality["gold_edge_count"], 2)
        self.assertEqual(quality["final_admitted_recall"], 0.5)
        self.assertEqual(quality["final_admitted_precision"], 0.5)
        self.assertEqual(quality["false_admission_count"], 1)
        self.assertEqual(quality["false_refusal_count"], 1)


if __name__ == "__main__":
    unittest.main()
