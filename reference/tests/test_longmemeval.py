from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
RUNNER = REFERENCE / "run_longmemeval.py"
FIXTURE = REFERENCE / "fixtures" / "benchmarks" / "longmemeval" / "synthetic.json"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))


def _module():
    spec = importlib.util.spec_from_file_location("run_longmemeval", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = _module()


class LongMemEvalProfileTests(unittest.TestCase):
    def test_synthetic_baselines_preserve_upstream_retrieval_denominators(self) -> None:
        report = M.run(FIXTURE, corpus_class="synthetic", include_agent_memory=False)
        session = report["planes"]["session"]["backends"]
        turn = report["planes"]["turn"]["backends"]

        self.assertEqual(report["input"]["question_count"], 3)
        self.assertEqual(session["no_memory"]["metrics"]["evaluated_question_count"], 2)
        self.assertEqual(session["no_memory"]["metrics"]["abstention_question_count"], 1)
        self.assertEqual(session["no_memory"]["metrics"]["recall_all@5"], 0.0)
        self.assertEqual(session["lexical_overlap"]["metrics"]["recall_all@5"], 1.0)
        self.assertEqual(turn["lexical_overlap"]["metrics"]["recall_all@5"], 1.0)
        self.assertEqual(report["comparability"]["status"], "synthetic-smoke-only")
        self.assertEqual(report["comparability"]["official_longmemeval_qa_score"], "not_computed")
        self.assertFalse(report["claim_boundary"]["answer_generation_quality_measured"])
        self.assertEqual(report["claim_boundary"]["aggregate_memory_health_score"], "not_defined")

    def test_question_type_metrics_keep_knowledge_update_separate(self) -> None:
        report = M.run(FIXTURE, corpus_class="synthetic", include_agent_memory=False)
        by_type = report["planes"]["session"]["backends"]["lexical_overlap"]["by_question_type"]
        self.assertIn("knowledge-update", by_type)
        self.assertEqual(report["currentness_slice"]["knowledge_update_question_count"], 1)

    def test_agent_memory_backend_uses_governed_admission(self) -> None:
        report = M.run(
            FIXTURE,
            corpus_class="synthetic",
            max_questions=1,
            include_agent_memory=True,
        )
        backend = report["planes"]["session"]["backends"]["agent_memory"]
        self.assertEqual(backend["authority_effect"], "none")
        self.assertIn("governed admission", backend["boundary"])
        self.assertEqual(backend["metrics"]["evaluated_question_count"], 1)
        row = backend["rows"][0]
        self.assertGreaterEqual(row["candidate_count"], len(row["ranked"]))

    def test_invalid_haystack_lengths_fail_closed(self) -> None:
        import json
        import tempfile

        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value[0]["haystack_dates"] = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "haystack arrays"):
                M.run(path, corpus_class="synthetic", include_agent_memory=False)


if __name__ == "__main__":
    unittest.main()
