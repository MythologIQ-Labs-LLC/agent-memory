from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref.evaluation import (
    BenchmarkContractError,
    ComparisonCompatibilityError,
    compare_runs,
    dimension_report,
    load_run,
    metric_observation,
    validate_run,
    write_run,
)


SHA_A = "a" * 64
CONFIG_A = "b" * 64


def _empty_dimensions(status: str = "not_measured"):
    return {
        "retrieval": dimension_report(status, notes=["not measured in this fixture"]),
        "currentness": dimension_report(status, notes=["not measured in this fixture"]),
        "reasoning": dimension_report(status, notes=["not measured in this fixture"]),
        "governance": dimension_report(status, notes=["not measured in this fixture"]),
        "efficiency": dimension_report(status, notes=["not measured in this fixture"]),
        "evaluator_integrity": dimension_report(status, notes=["not measured in this fixture"]),
        "reproducibility": dimension_report(status, notes=["not measured in this fixture"]),
    }


def _run(
    system_id: str,
    recall: float = 0.5,
    *,
    input_sha: str | None = SHA_A,
    denominator: int = 10,
    status: str = "complete",
):
    dimensions = _empty_dimensions()
    dimensions["retrieval"] = dimension_report(
        "measured",
        [
            metric_observation(
                "recall@10",
                value=recall,
                direction="higher_better",
                denominator=denominator,
                unit="ratio",
                population="retrieval_questions",
            ),
            metric_observation(
                "false_admissions",
                value=0,
                direction="zero_target",
                denominator=denominator,
                unit="count",
                population="retrieval_questions",
            ),
        ],
    )
    dimensions["evaluator_integrity"] = dimension_report(
        "measured",
        [
            metric_observation(
                "controlled_mutations_detected",
                value=5,
                direction="higher_better",
                denominator=5,
                unit="count",
                population="mutation_probes",
            )
        ],
        notes=["evaluator evidence only; not memory efficacy"],
    )
    return {
        "schema_version": "1.0.0",
        "run_id": f"run:{system_id}",
        "status": status,
        "benchmark": {
            "id": "example-memory-benchmark",
            "source_url": "https://example.test/benchmark",
            "source_revision": "benchmark-rev-1",
            "dataset_id": "example-cleaned",
            "dataset_revision": "dataset-rev-1",
            "input_sha256": input_sha,
            "task_profile": "retrieval-v1",
        },
        "system": {
            "id": system_id,
            "kind": "agent_memory" if system_id == "agent-memory" else "lexical",
            "revision": "system-rev-1",
            "configuration_digest": CONFIG_A,
        },
        "execution": {
            "selection_id": "frozen-10",
            "selection_method": "first-10-after-id-sort",
            "sample_count": 10,
            "environment": {"python": "3.11"},
            "seed": 7,
        },
        "dimensions": dimensions,
        "native_results": {
            "benchmark_specific_metric": {"value": 17, "meaning": "opaque to common contract"}
        },
        "limitations": ["fixture is synthetic"],
        "artifacts": [],
        "authority_effect": "none",
    }


def _unexecuted(status: str):
    run = _run("agent-memory", input_sha=None, status=status)
    run["execution"]["sample_count"] = 0
    run["dimensions"] = _empty_dimensions("blocked" if status == "blocked" else "not_measured")
    run["native_results"] = {}
    run["limitations"] = ["exact frozen benchmark input has not been materialized"]
    return run


class MemoryEvaluationContractTests(unittest.TestCase):
    def test_zero_is_measured_and_not_missing(self):
        run = validate_run(_run("agent-memory", recall=0.0))
        recall = run["dimensions"]["retrieval"]["metrics"][0]
        self.assertEqual(recall["state"], "measured")
        self.assertEqual(recall["value"], 0.0)

        missing = metric_observation(
            "answer_accuracy",
            state="not_measured",
            direction="higher_better",
            note="reader evaluation not run",
        )
        self.assertNotIn("value", missing)

    def test_metric_builder_rejects_invalid_state_value_combinations(self):
        with self.assertRaises(BenchmarkContractError):
            metric_observation("recall", state="measured", value=None)
        with self.assertRaises(BenchmarkContractError):
            metric_observation("recall", state="blocked", value=0.0)

    def test_schema_rejects_non_none_authority_effect(self):
        run = _run("agent-memory")
        run["authority_effect"] = "advisory"
        with self.assertRaises(BenchmarkContractError):
            validate_run(run)

    def test_semantics_reject_duplicate_metric_ids(self):
        run = _run("agent-memory")
        duplicate = dict(run["dimensions"]["retrieval"]["metrics"][0])
        run["dimensions"]["retrieval"]["metrics"].append(duplicate)
        with self.assertRaises(BenchmarkContractError):
            validate_run(run)

    def test_semantics_reject_measured_metric_inside_not_measured_dimension(self):
        run = _run("agent-memory")
        run["dimensions"]["reasoning"] = dimension_report(
            "not_measured",
            [metric_observation("qa", value=1.0, direction="higher_better")],
        )
        with self.assertRaises(BenchmarkContractError):
            validate_run(run)

    def test_blocked_manifest_can_record_unavailable_input_without_fake_digest(self):
        run = validate_run(_unexecuted("blocked"))
        self.assertEqual(run["status"], "blocked")
        self.assertIsNone(run["benchmark"]["input_sha256"])
        self.assertEqual(run["dimensions"]["retrieval"]["status"], "blocked")

    def test_not_run_manifest_can_record_unavailable_input_without_fake_digest(self):
        run = validate_run(_unexecuted("not_run"))
        self.assertEqual(run["status"], "not_run")
        self.assertIsNone(run["benchmark"]["input_sha256"])

    def test_complete_and_partial_runs_require_exact_input_digest(self):
        for status in ("complete", "partial"):
            with self.subTest(status=status):
                run = _run("agent-memory", input_sha=None, status=status)
                with self.assertRaises(BenchmarkContractError):
                    validate_run(run)

    def test_compare_compatible_runs_emits_dimension_specific_delta(self):
        baseline = _run("lexical", recall=0.4)
        candidate = _run("agent-memory", recall=0.7)
        comparison = compare_runs(baseline, candidate)

        retrieval = {row["metric_id"]: row for row in comparison["dimensions"]["retrieval"]}
        self.assertEqual(retrieval["recall@10"]["comparison_state"], "comparable")
        self.assertAlmostEqual(retrieval["recall@10"]["delta"], 0.3)
        self.assertEqual(retrieval["recall@10"]["outcome"], "improved")
        self.assertEqual(retrieval["false_admissions"]["outcome"], "unchanged")
        self.assertNotIn("overall_score", comparison)
        self.assertEqual(comparison["authority_effect"], "none")

    def test_compare_rejects_different_frozen_input(self):
        baseline = _run("lexical")
        candidate = _run("agent-memory", input_sha="c" * 64)
        with self.assertRaises(ComparisonCompatibilityError):
            compare_runs(baseline, candidate)

    def test_compare_rejects_unavailable_input_even_when_both_are_null(self):
        baseline = _unexecuted("blocked")
        candidate = _unexecuted("blocked")
        candidate["run_id"] = "run:agent-memory-candidate"
        with self.assertRaises(ComparisonCompatibilityError):
            compare_runs(baseline, candidate)

    def test_metric_denominator_mismatch_does_not_fake_delta(self):
        baseline = _run("lexical", recall=0.4, denominator=10)
        candidate = _run("agent-memory", recall=0.8, denominator=9)
        comparison = compare_runs(baseline, candidate)
        recall = {
            row["metric_id"]: row for row in comparison["dimensions"]["retrieval"]
        }["recall@10"]
        self.assertEqual(recall["comparison_state"], "denominator_mismatch")
        self.assertNotIn("delta", recall)

    def test_evaluator_integrity_stays_separate_from_retrieval(self):
        comparison = compare_runs(_run("lexical"), _run("agent-memory"))
        retrieval_ids = {
            row["metric_id"] for row in comparison["dimensions"]["retrieval"]
        }
        integrity_ids = {
            row["metric_id"] for row in comparison["dimensions"]["evaluator_integrity"]
        }
        self.assertNotIn("controlled_mutations_detected", retrieval_ids)
        self.assertIn("controlled_mutations_detected", integrity_ids)

    def test_native_results_round_trip_without_common_semantic_mapping(self):
        run = _run("agent-memory")
        validated = validate_run(run)
        self.assertEqual(validated["native_results"], run["native_results"])

    def test_write_and_load_are_validated_and_stable(self):
        run = _run("agent-memory")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            digest = write_run(path, run)
            loaded = load_run(path)
            self.assertEqual(loaded, validate_run(run))
            self.assertEqual(len(digest), 64)
            parsed = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["run_id"], "run:agent-memory")


if __name__ == "__main__":
    unittest.main()
