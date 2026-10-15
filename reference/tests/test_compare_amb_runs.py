"""scripts/compare_amb_runs.py: equality of AMB result files without blind spots."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "compare_amb_runs.py"


def _load():
    spec = importlib.util.spec_from_file_location("compare_amb_runs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _result() -> dict:
    return {
        "dataset": "precisionmembench",
        "category": None,
        "run_name": "left",
        "ingestion_time_ms": 1.0,
        "results": [
            {"query_id": "a", "correct": True, "score": None, "retrieve_time_ms": 1.0, "meta": {"k": 1}},
            {"query_id": "b", "correct": False, "score": None, "retrieve_time_ms": 2.0, "meta": {"k": 2}},
        ],
    }


class CompareAmbRunsTests(unittest.TestCase):
    def setUp(self):
        self.module = _load()

    def test_timing_and_run_name_are_the_only_ignored_differences(self):
        right = _result()
        right["run_name"], right["ingestion_time_ms"] = "right", 9.0
        right["results"][0]["retrieve_time_ms"] = 99.0
        self.assertEqual(self.module.compare(_result(), right, ignore_raw=False), [])

    def test_missing_key_is_not_equal_to_none(self):
        right = _result()
        del right["category"]
        del right["results"][1]["score"]
        differences = self.module.compare(_result(), right, ignore_raw=False)
        self.assertIn("summary.category: missing on right", differences)
        self.assertIn("case b.score: missing on right", differences)

    def test_duplicate_query_ids_are_reported(self):
        right = _result()
        right["results"].append(copy.deepcopy(right["results"][1]))
        right["results"][2]["correct"] = True
        differences = self.module.compare(_result(), right, ignore_raw=False)
        self.assertIn("case b: duplicate query_id on right", differences)

    def test_value_and_order_differences_are_reported(self):
        right = _result()
        right["results"][0]["meta"] = {"k": 5}
        right["results"].reverse()
        differences = self.module.compare(_result(), right, ignore_raw=False)
        self.assertIn("case order or membership differs", differences)
        self.assertTrue(any(line.startswith("case a.meta") for line in differences))


if __name__ == "__main__":
    unittest.main()
