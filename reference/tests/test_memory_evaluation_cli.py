from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref.console import main
from agentmem_ref.evaluation import dimension_report, metric_observation, write_run


INPUT_SHA = "a" * 64
CONFIG_SHA = "b" * 64


def _dimensions(recall: float):
    result = {
        name: dimension_report("not_measured", notes=["not measured in CLI fixture"])
        for name in (
            "retrieval",
            "currentness",
            "reasoning",
            "governance",
            "efficiency",
            "evaluator_integrity",
            "reproducibility",
        )
    }
    result["retrieval"] = dimension_report(
        "measured",
        [
            metric_observation(
                "recall@10",
                value=recall,
                direction="higher_better",
                denominator=10,
                unit="ratio",
                population="retrieval_questions",
            )
        ],
    )
    return result


def _report(system_id: str, recall: float, *, input_sha: str = INPUT_SHA):
    return {
        "schema_version": "1.0.0",
        "run_id": f"run:{system_id}",
        "status": "complete",
        "benchmark": {
            "id": "cli-memory-benchmark",
            "source_revision": "benchmark-rev-1",
            "dataset_id": "dataset",
            "dataset_revision": "dataset-rev-1",
            "input_sha256": input_sha,
            "task_profile": "retrieval-v1",
        },
        "system": {
            "id": system_id,
            "kind": "agent_memory" if system_id == "agent-memory" else "lexical",
            "revision": "system-rev-1",
            "configuration_digest": CONFIG_SHA,
        },
        "execution": {
            "selection_id": "frozen-10",
            "selection_method": "stable-id-first-10",
            "sample_count": 10,
        },
        "dimensions": _dimensions(recall),
        "native_results": {},
        "limitations": ["synthetic CLI fixture"],
        "artifacts": [],
        "authority_effect": "none",
    }


class MemoryEvaluationCliTests(unittest.TestCase):
    def test_benchmark_list_json_is_machine_readable_and_truthful(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["benchmark", "list", "--json"])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["command"], "benchmark_list")
        self.assertEqual(report["authority_effect"], "none")
        profile_ids = {profile["profile_id"] for profile in report["profiles"]}
        self.assertIn("swe-context-bench-lite-external-retrieval-v1", profile_ids)
        self.assertIn("agent-memory-longmemeval-retrieval-currentness-v1", profile_ids)
        swe = next(
            profile
            for profile in report["profiles"]
            if profile["profile_id"] == "swe-context-bench-lite-external-retrieval-v1"
        )
        self.assertIn("blocked", swe["external_evidence_status"])

    def test_registry_evidence_is_truthful_and_bound_to_committed_reports(self):
        from agentmem_ref.evaluation.registry import list_profiles

        root = Path(__file__).resolve().parents[2]
        profiles = {profile["profile_id"]: profile for profile in list_profiles()}
        self.assertIn("agent-memory-agentmembench-memdialogue-operational-v1", profiles)
        statuses = {
            (profile_id, item["variant"]): item["status"]
            for profile_id, profile in profiles.items()
            for item in profile["external_evidence"]
        }
        self.assertEqual(
            statuses[("swe-context-bench-lite-external-retrieval-v1", "lite_protocol_comparable_99_query_100_edge")],
            "blocked",
        )
        longmemeval = "agent-memory-longmemeval-retrieval-currentness-v1"
        self.assertEqual(statuses[(longmemeval, "longmemeval_s_cleaned")], "complete")
        self.assertEqual(statuses[(longmemeval, "longmemeval_m_cleaned")], "not_run")
        self.assertEqual(statuses[(longmemeval, "upstream_model_judged_qa")], "not_run")
        for profile in profiles.values():
            for item in profile["external_evidence"]:
                self.assertIn(item["status"], {"complete", "partial", "blocked", "not_run"})
                if item["status"] != "complete":
                    self.assertNotIn("report", item)
                    continue
                report = json.loads((root / item["report"]).read_text(encoding="utf-8"))
                self.assertEqual(report["input"]["sha256"], item["input_sha256"])
                self.assertEqual(report["execution"]["agent_memory_revision"], item["agent_memory_revision"])
                self.assertEqual(report["input"]["corpus_class"], "external_frozen")

    def test_console_routes_runtime_commands_and_runtime_never_imports_evaluation(self):
        import ast

        root = Path(__file__).resolve().parents[2]
        source = (root / "reference" / "agentmem_ref" / "runtime" / "cli.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn("evaluation", node.module or "")
        error = io.StringIO()
        with contextlib.redirect_stderr(error), self.assertRaises(SystemExit) as raised:
            main(["no-such-command"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("agent-memory", error.getvalue())

    def test_benchmark_list_human_output_names_profiles(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["benchmark", "list"])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("swe-context-bench-lite-external-retrieval-v1", text)
        self.assertIn("agent-memory-longmemeval-retrieval-currentness-v1", text)
        self.assertIn("Authority effect: none", text)

    def test_benchmark_validate_reports_digest_and_measured_dimensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run.json"
            write_run(path, _report("agent-memory", 0.7))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["benchmark", "validate", str(path), "--json"])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report["valid"])
        self.assertEqual(report["run_id"], "run:agent-memory")
        self.assertEqual(report["measured_dimensions"], ["retrieval"])
        self.assertEqual(len(report["run_digest_sha256"]), 64)
        self.assertEqual(report["authority_effect"], "none")

    def test_benchmark_compare_reports_metric_delta_without_overall_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline.json"
            candidate = root / "candidate.json"
            write_run(baseline, _report("lexical", 0.4))
            write_run(candidate, _report("agent-memory", 0.7))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    ["benchmark", "compare", str(baseline), str(candidate), "--json"]
                )
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        recall = report["dimensions"]["retrieval"][0]
        self.assertEqual(recall["metric_id"], "recall@10")
        self.assertAlmostEqual(recall["delta"], 0.3)
        self.assertEqual(recall["outcome"], "improved")
        self.assertNotIn("overall_score", report)
        self.assertEqual(report["authority_effect"], "none")

    def test_benchmark_compare_incompatible_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline.json"
            candidate = root / "candidate.json"
            write_run(baseline, _report("lexical", 0.4))
            write_run(candidate, _report("agent-memory", 0.7, input_sha="c" * 64))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    ["benchmark", "compare", str(baseline), str(candidate), "--json"]
                )
        self.assertEqual(code, 2)
        report = json.loads(output.getvalue())
        self.assertFalse(report["valid"])
        self.assertEqual(report["status"], "refused")
        self.assertIn("not comparable", report["error"])
        self.assertEqual(report["authority_effect"], "none")

    def test_benchmark_validate_malformed_report_returns_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text("{}", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["benchmark", "validate", str(path), "--json"])
        self.assertEqual(code, 2)
        report = json.loads(output.getvalue())
        self.assertFalse(report["valid"])
        self.assertEqual(report["status"], "refused")


if __name__ == "__main__":
    unittest.main()
