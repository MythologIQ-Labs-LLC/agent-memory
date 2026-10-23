"""Offline controls for the four-arm semantic rescue research probe, no model needed."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("semantic_rescue_probe", HERE / "semantic_rescue_probe.py")
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class SemanticRescueProbeControls(unittest.TestCase):
    def test_dataset_is_real_committed_disjoint_fixture(self):
        import json
        cases = json.loads(probe.DEFAULT_CASES.read_text(encoding="utf-8"))
        probe.validate_cases(cases)
        self.assertEqual(len(cases["records"]), 24)
        self.assertEqual(len(cases["tasks"]), 26)
        self.assertEqual({task["id"] for task in cases["tasks"] if task["id"] in ("D14", "D15")},
                         {"D14", "D15"})

    def test_flag_context_restores_environment_after_error(self):
        original = os.environ.get(probe.FLAG)
        try:
            with self.assertRaises(RuntimeError):
                with probe.admission_mode("content_term"):
                    self.assertEqual(os.environ.get(probe.FLAG), "content_term")
                    raise RuntimeError("stop")
            self.assertEqual(os.environ.get(probe.FLAG), original)
        finally:
            if original is None:
                os.environ.pop(probe.FLAG, None)
            else:
                os.environ[probe.FLAG] = original

    def test_missing_required_evidence_does_not_count_as_success(self):
        result = probe.assess(["memory:distractor"], ["memory:needed"])
        self.assertFalse(result["required_complete"])
        self.assertEqual(result["required_hits"], 0)
        self.assertEqual(result["unexpected_items"], 1)

    def test_unanswerable_with_any_returned_context_is_not_abstention(self):
        answer = probe.assess(["memory:distractor"], [])
        self.assertIsNone(answer["required_complete"])
        self.assertFalse(answer["empty_no_answer_context"])

    def test_summary_keeps_positive_and_negative_denominators_separate(self):
        rows = [
            {"id": "A", "required": ["memory:1"], "score": probe.assess(["memory:1"], ["memory:1"]),
             "elapsed_ms": 11.0},
            {"id": "N", "required": [], "score": probe.assess([], []), "elapsed_ms": 13.0},
        ]
        out = probe.summarize(rows)
        self.assertEqual(out["answerable_complete"], 1)
        self.assertEqual(out["no_answer_empty_context"], 1)
        self.assertEqual(out["p50_ms"], 12.0)

    def test_missing_expected_key_is_rejected_before_any_model_start(self):
        cases = {
            "records": [{"key": "memory:a", "text": "A"}],
            "tasks": [{"id": "q", "question": "What?", "required": ["memory:b"]}],
        }
        with self.assertRaises(ValueError):
            probe.validate_cases(cases)


if __name__ == "__main__":
    unittest.main()
