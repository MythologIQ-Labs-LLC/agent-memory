from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agentmem_ref.locomo_evidence_benchmark import normalize_evidence_ids, run_benchmark


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reference" / "fixtures" / "benchmarks" / "locomo-schema-synthetic-v1.json"
RUNTIME_CONFIG = (
    ROOT
    / "reference"
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)
RUNNER = ROOT / "reference" / "run_locomo_evidence_benchmark.py"


class LoCoMoEvidenceBenchmarkTests(unittest.TestCase):
    def _report(self) -> dict:
        return run_benchmark(
            dataset_path=FIXTURE,
            runtime_config_path=RUNTIME_CONFIG,
            agent_memory_revision="test-revision",
            sample_indexes=(0,),
            categories=(1, 3),
            lexical_anchor_limit=1,
            k_values=(1, 3, 5),
        )

    def test_evidence_normalization_splits_compound_dialog_ids(self) -> None:
        self.assertEqual(
            normalize_evidence_ids(["D2:1; D2:3", "D2:3", "noise D4:8 text"]),
            ("D2:1", "D2:3", "D4:8"),
        )

    def test_query_driven_relation_recovers_synthetic_evidence_lexical_misses(self) -> None:
        report = self._report()
        lexical_rows = {
            row["question"]: row for row in report["lexical_only"]["questions"]
        }
        multi_rows = {
            row["question"]: row
            for row in report["query_driven_multi_route"]["questions"]
        }
        question = "What object came out of the pottery class?"

        self.assertEqual(lexical_rows[question]["normalized_evidence"], ["D1:3"])
        self.assertEqual(lexical_rows[question]["metrics"]["at_k"]["5"]["recall"], 0.0)
        self.assertEqual(multi_rows[question]["metrics"]["at_k"]["5"]["recall"], 1.0)
        self.assertIn("D1:3", multi_rows[question]["ranked_dialog_ids"][:5])

    def test_aggregate_evidence_recall_improves_without_authority_leakage(self) -> None:
        report = self._report()
        lexical = report["lexical_only"]["aggregate"]
        multi = report["query_driven_multi_route"]["aggregate"]

        self.assertEqual(lexical["question_count"], 3)
        self.assertEqual(lexical["evidence_count"], 4)
        self.assertEqual(multi["question_count"], 3)
        self.assertEqual(report["excluded_empty_evidence_questions"], 1)
        self.assertGreater(
            multi["at_k"]["5"]["micro_recall"],
            lexical["at_k"]["5"]["micro_recall"],
        )
        self.assertEqual(multi["at_k"]["5"]["micro_recall"], 1.0)
        # Ranking policy 2.0.0 (#538/#531) breaks exact relevance ties newer-first instead of
        # by ascending insertion id. On "What two things did the friends plan for the
        # weekend?" gold D2:1 and non-gold D2:2 tie on every relevance stage (two routes,
        # identical lexical and shared-evidence scores: each shares one stopword with the
        # query), so D2:2 (newer) now ranks first and that question's reciprocal rank falls
        # from 1.0 to 0.5. The earlier positive MRR delta depended on that arbitrary tie
        # order. It is recorded as a known regression on this fixture, not hidden; the
        # coarse lexical scoring that creates the tie is owned by #538.
        self.assertAlmostEqual(report["comparison"]["mean_reciprocal_rank_delta"], -0.083333)
        weekend = next(
            row
            for row in report["query_driven_multi_route"]["questions"]
            if row["question"] == "What two things did the friends plan for the weekend?"
        )
        self.assertEqual(weekend["ranked_dialog_ids"][:2], ["D2:2", "D2:1"])
        self.assertEqual(report["governance"]["query_driven_refusal_count"], 0)
        self.assertEqual(report["governance"]["route_authority_effect_violations"], 0)

    def test_report_binds_external_dataset_and_non_claims(self) -> None:
        report = self._report()
        self.assertEqual(report["schema_version"], "1.0.0")
        self.assertEqual(report["benchmark_id"], "agent-memory-locomo-evidence-retrieval")
        self.assertEqual(
            report["evaluation_kind"],
            "retrieval_evidence_diagnostic_not_official_qa_score",
        )
        self.assertEqual(report["agent_memory_revision"], "test-revision")
        self.assertEqual(
            report["dataset"]["upstream_commit"],
            "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376",
        )
        self.assertEqual(report["dataset"]["upstream_license"], "CC-BY-NC-4.0")
        self.assertFalse(report["dataset"]["redistributed_by_agent_memory"])
        self.assertTrue(report["dataset"]["sha256"].startswith("sha256:"))
        self.assertTrue(report["runtime_configuration"]["sha256"].startswith("sha256:"))
        self.assertTrue(
            report["timing_diagnostic_seconds"]["not_comparable_to_jev_mem_paper_timing"]
        )
        self.assertTrue(
            any("not the official LoCoMo QA score" in item for item in report["limitations"])
        )

    def test_runner_emits_report_from_external_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "locomo-evidence.json"
            subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--dataset",
                    str(FIXTURE),
                    "--runtime-config",
                    str(RUNTIME_CONFIG),
                    "--agent-memory-revision",
                    "test-revision",
                    "--sample",
                    "0",
                    "--categories",
                    "1,3",
                    "--lexical-anchor-limit",
                    "1",
                    "--k-values",
                    "1,3,5",
                    "--output",
                    str(output),
                ],
                cwd=ROOT / "reference",
                check=True,
            )
            emitted = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(emitted["benchmark_id"], "agent-memory-locomo-evidence-retrieval")
        self.assertEqual(emitted["lexical_only"]["aggregate"]["question_count"], 3)
        self.assertEqual(
            emitted["query_driven_multi_route"]["aggregate"]["at_k"]["5"]["micro_recall"],
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
