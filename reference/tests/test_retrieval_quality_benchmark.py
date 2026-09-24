from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agentmem_ref.harness.retrieval_quality_benchmark import run_benchmark
from agentmem_ref.vector_retrieval import (
    DETERMINISTIC_REBUILD_POSTURE,
    SEMANTIC_VECTOR_ROUTE,
    NativeVectorCandidateRetriever,
    VectorRepresentationSpec,
)


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


class _BenchmarkVectorRepresentation:
    """Deterministic fixture representation used only for benchmark conformance."""

    spec = VectorRepresentationSpec(
        representation_ref="agent-memory:benchmark-vector-fixture",
        representation_version="1.0.0",
        config_digest="sha256:benchmark-vector-fixture-v1",
        dimensions=3,
        deterministic_rebuild=True,
    )

    _vectors = {
        "weather forecast": (1.0, 0.0, 0.0),
        "database backups run nightly": (1.0, 0.0, 0.0),
        "staged rollout remains preferred": (0.9, 0.1, 0.0),
        "deploy window": (0.0, 1.0, 0.0),
        "deploy window is Thursday": (0.0, 1.0, 0.0),
        "foreign deployment evidence belongs to beta": (0.0, 0.95, 0.05),
        "deprecated rollout procedure used canary zero": (0.0, 0.9, 0.1),
        "team lunch": (0.0, 0.0, 1.0),
        "team lunch is Tuesday": (0.0, 0.0, 1.0),
    }

    def embed(self, text: str) -> tuple[float, ...]:
        return self._vectors.get(text, (0.0, 0.0, 0.0))


class RetrievalQualityBenchmarkTests(unittest.TestCase):
    def _report(self) -> dict:
        return run_benchmark(
            fixture_path=FIXTURE,
            runtime_config_path=RUNTIME_CONFIG,
            agent_memory_revision="test-revision",
        )

    def _vector_report(self) -> dict:
        return run_benchmark(
            fixture_path=FIXTURE,
            runtime_config_path=RUNTIME_CONFIG,
            agent_memory_revision="vector-test-revision",
            vector_retriever=NativeVectorCandidateRetriever(
                _BenchmarkVectorRepresentation(),
            ),
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
        self.assertIsNone(first["vector_route"])

    def test_vector_profile_and_route_contribution_are_revision_bound(self) -> None:
        first = self._vector_report()
        second = self._vector_report()
        self.assertEqual(first, second)
        self.assertEqual(first["agent_memory_revision"], "vector-test-revision")

        profile = first["vector_route"]
        self.assertEqual(profile["route_id"], SEMANTIC_VECTOR_ROUTE)
        self.assertEqual(
            profile["representation_ref"],
            _BenchmarkVectorRepresentation.spec.representation_ref,
        )
        self.assertEqual(profile["representation_version"], "1.0.0")
        self.assertEqual(
            profile["representation_config_digest"],
            "sha256:benchmark-vector-fixture-v1",
        )
        self.assertEqual(profile["vector_dimension"], 3)
        self.assertEqual(profile["similarity_metric"], "cosine")
        self.assertEqual(profile["candidate_limit"], 16)
        self.assertEqual(profile["rebuild_posture"], DETERMINISTIC_REBUILD_POSTURE)
        self.assertTrue(profile["deterministic_rebuild"])
        self.assertEqual(profile["authority_effect"], "none")

        contributions = first["systems"]["multi_route"]["route_contribution_counts"]
        self.assertGreater(contributions.get(SEMANTIC_VECTOR_ROUTE, 0), 0)
        self.assertEqual(first["governance"]["route_authority_effect_violations"], 0)
        self.assertEqual(first["governance"]["multi_route_forbidden_admission_failures"], 0)
        self.assertEqual(first["governance"]["multi_route_forbidden_ranked_failures"], 0)

        vector_hits = [
            hit
            for row in first["systems"]["multi_route"]["cases"]
            for hits in row["route_provenance"].values()
            for hit in hits
            if hit["route_id"] == SEMANTIC_VECTOR_ROUTE
        ]
        self.assertTrue(vector_hits)
        self.assertTrue(
            all(
                hit["representation_config_digest"]
                == "sha256:benchmark-vector-fixture-v1"
                for hit in vector_hits
            )
        )

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
