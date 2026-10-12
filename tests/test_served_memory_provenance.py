"""#771: independent audit of the execution->gold->score handoff.

These tests do not assume the real runtime achieves any target metric.
They reject protocol drift and source-scope masking before judging results.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from qualify_served_memory_run import qualify  # noqa: E402

DIR = ROOT / "reference/fixtures/evaluation"


class ServedQualityProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = json.loads((DIR / "served-memory-integration-v1-input.json").read_text())
        cls.gold = json.loads((DIR / "served-memory-integration-v1-gold.json").read_text())
        cls.run = {
            "schema": "served-memory-run-v1",
            "runtime_revision": "synthetic-not-executed",
            "lane_id": "reference-governed-recall-v1",
            "rows": [{"id": q["id"], "returned": []} for q in cls.inputs["queries"]],
        }

    def test_alignment_separates_truth_from_actual_returned_ids(self):
        report = qualify(copy.deepcopy(self.inputs), copy.deepcopy(self.gold),
                         copy.deepcopy(self.run))
        self.assertEqual(report["quality_case_count"], 5)
        self.assertEqual(report["P1_served_correctness"]["answerable_case_count"], 4)
        self.assertEqual(report["P1_served_correctness"]["unsafe_empty_on_answerable_count"], 4)
        self.assertEqual(report["P0_safety"]["cases_with_prohibited_exposure"], 0)

    def test_scenario_content_cannot_drift_from_gold(self):
        src = copy.deepcopy(self.inputs)
        src["queries"][0]["query"] += " changed question"
        with self.assertRaises(ValueError):
            qualify(src, copy.deepcopy(self.gold), copy.deepcopy(self.run))

    def test_query_intent_and_return_budget_are_invariant(self):
        for key, value in (("intent", "historical"), ("budget", 100)):
            src = copy.deepcopy(self.inputs)
            src["queries"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                qualify(src, copy.deepcopy(self.gold), copy.deepcopy(self.run))

    def test_all_written_source_ids_must_be_annotated_for_every_case(self):
        gold = copy.deepcopy(self.gold)
        del gold["cases"][0]["relevance"]["mugs"]
        with self.assertRaises(ValueError):
            qualify(copy.deepcopy(self.inputs), gold, copy.deepcopy(self.run))

    def test_scope_exclusions_must_be_explicit_in_gold(self):
        gold = copy.deepcopy(self.gold)
        gold["cases"][0]["prohibited"].remove("hidden-endpoint")
        with self.assertRaises(ValueError):
            qualify(copy.deepcopy(self.inputs), gold, copy.deepcopy(self.run))

    def test_forged_gold_in_execution_inputs_is_rejected(self):
        src = copy.deepcopy(self.inputs)
        src["relevance"] = {"endpoint": 3}
        with self.assertRaises(ValueError):
            qualify(src, copy.deepcopy(self.gold), copy.deepcopy(self.run))

    def test_unscored_case_ids_cannot_be_dropped_from_run(self):
        run = copy.deepcopy(self.run)
        run["rows"].pop()
        with self.assertRaises(ValueError):
            qualify(copy.deepcopy(self.inputs), copy.deepcopy(self.gold), run)


if __name__ == "__main__":
    unittest.main()
