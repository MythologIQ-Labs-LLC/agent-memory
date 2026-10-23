"""Checks for the Gate 2 *measurement*, not the memory product itself.

The MCP/SQLite comparison is a development diagnostic. Tests here prevent
accidental scoring reversals (e.g. empty no-answer -> 'correct answer').
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("am_mcp_quality_probe", HERE / "quality_probe.py")
assert spec and spec.loader
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


class QualityProbeScorer(unittest.TestCase):
    def test_answerable_missing_is_not_success(self):
        x = quality.score([], ["memory:target"], [])
        self.assertFalse(x["required_complete"])
        self.assertEqual(x["required_hits"], 0)
        self.assertEqual(x["evidence_precision"], 0.0)
        self.assertIsNone(x["empty_context_on_no_answer"])

    def test_no_answer_with_distractors_is_not_abstention(self):
        x = quality.score(["memory:distractor"], [], ["memory:distractor"])
        self.assertFalse(x["empty_context_on_no_answer"])
        self.assertEqual(x["forbidden_keys_present"], ["memory:distractor"])
        self.assertEqual(x["unexpected_evidence_items"], 1)

    def test_empty_context_on_no_answer_is_only_context_proxy(self):
        x = quality.score([], [], [])
        self.assertTrue(x["empty_context_on_no_answer"])
        self.assertIsNone(x["required_complete"])
        self.assertIsNone(x["evidence_precision"])

    def test_required_evidence_and_extra_item_are_counted_separately(self):
        x = quality.score(["memory:required", "memory:other"], ["memory:required"],
                          ["memory:other"])
        self.assertTrue(x["required_complete"])
        self.assertEqual(x["required_hits"], 1)
        self.assertEqual(x["unexpected_evidence_items"], 1)
        self.assertAlmostEqual(x["evidence_precision"], 0.5)

    def test_comparator_fts5_is_indexed_and_uses_same_texts(self):
        records = [
            {"key": "memory:one", "text": "The home office printer uses TN830 toner."},
            {"key": "memory:two", "text": "The kitchen has a new mixing bowl."},
        ]
        try:
            db = quality.build_fts(records)
        except sqlite3.OperationalError as exc:
            self.skipTest(f"local SQLite built without FTS5: {exc}")
        try:
            self.assertEqual(quality.fts_find(db, "Which toner for the printer?", 2),
                             ["memory:one"])
            self.assertEqual(quality.fts_find(db, "quantum vacuum propulsion", 2), [])
        finally:
            db.close()

    def test_fixture_keys_must_be_unique_and_labels_valid(self):
        data = {
            "records": [{"key": "memory:a", "text": "Alpha."}],
            "tasks": [{"id": "one", "question": "Where alpha?",
                       "required": ["memory:a"], "forbidden": []}],
        }
        quality.validate_cases(data)
        duplicate = dict(data, records=data["records"] * 2)
        with self.assertRaises(ValueError):
            quality.validate_cases(duplicate)
        impossible = dict(data, tasks=[{
            "id": "one", "question": "Where alpha?",
            "required": ["memory:unknown"], "forbidden": [],
        }])
        with self.assertRaises(ValueError):
            quality.validate_cases(impossible)

    def test_aggregate_does_not_mix_unanswered_and_answerable_denominators(self):
        rows = [
            {"mcp": quality.score(["a"], ["a"], []), "mcp_elapsed_ms": 1.0},
            {"mcp": quality.score(["b"], [], []), "mcp_elapsed_ms": 2.0},
        ]
        summary = quality.aggregate(rows, "mcp")
        self.assertEqual(summary["answerable_complete"], 1)
        self.assertEqual(summary["answerable_total"], 1)
        self.assertEqual(summary["no_answer_empty_context"], 0)
        self.assertEqual(summary["no_answer_total"], 1)
        self.assertEqual(summary["unexpected_evidence_items"], 1)
        self.assertEqual(summary["mean_evidence_precision_on_answerable"], 1.0)


if __name__ == "__main__":
    unittest.main()
