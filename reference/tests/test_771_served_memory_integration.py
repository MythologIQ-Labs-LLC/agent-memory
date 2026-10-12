"""#771: real composed-runtime scoring bridge, with execution inputs separate from gold.

Do not require benchmark "wins" from a reference lexical implementation.
Failure is measured by the separate quality scorer after real governed recall.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from run_served_memory_scenarios import run_scenarios  # noqa: E402
from score_served_memory_quality import score  # noqa: E402

DIR = ROOT / "reference/fixtures/evaluation"


class GovernedServedMemoryQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = json.loads((DIR / "served-memory-integration-v1-input.json").read_text())
        cls.gold = json.loads((DIR / "served-memory-integration-v1-gold.json").read_text())

    def test_real_governed_multiroute_evidence_can_be_scored_after_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = run_scenarios(copy.deepcopy(self.inputs), Path(tmp),
                                     revision="test-sha-quality-771",
                                     lane_id="reference-governed-recall-v1")
        self.assertEqual(manifest["schema"], "served-memory-run-v1")
        self.assertEqual(manifest["runtime_revision"], "test-sha-quality-771")
        self.assertEqual([x["id"] for x in manifest["rows"]],
                         [x["id"] for x in self.inputs["queries"]])
        for row in manifest["rows"]:
            self.assertEqual(len(row["returned"]), len(set(row["returned"])))
            query = next(q for q in self.inputs["queries"] if q["id"] == row["id"])
            self.assertLessEqual(len(row["returned"]), query["budget"])
            self.assertNotIn("hidden-endpoint", row["returned"])
        measured = score(copy.deepcopy(self.gold), manifest)
        self.assertEqual(measured["quality_case_count"], len(self.inputs["queries"]))
        self.assertEqual(measured["P0_safety"]["cases_with_prohibited_exposure"], 0)
        self.assertTrue(measured["not_a_composite_score"])
        self.assertNotIn("latency", measured["P1_served_correctness"])
        # We deliberately make no pass assertion about recall/top1/currentness
        # before the actual reference runtime is executed and examined.

    def test_labels_do_not_enter_the_runtime_execution_path(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            original = run_scenarios(copy.deepcopy(self.inputs), Path(a),
                                     revision="same-source",
                                     lane_id="reference-governed-recall-v1")
            altered_gold = copy.deepcopy(self.gold)
            altered_gold["cases"][0]["relevance"]["endpoint"] = 0
            replay = run_scenarios(copy.deepcopy(self.inputs), Path(b),
                                   revision="same-source",
                                   lane_id="reference-governed-recall-v1")
        self.assertEqual(original, replay)
        self.assertNotEqual(self.gold, altered_gold)

    def test_budget_not_leaked_as_fake_stop_or_completeness(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = run_scenarios(copy.deepcopy(self.inputs), Path(tmp),
                                revision="test-sha", lane_id="quality-v1")
        for row in run["rows"]:
            self.assertEqual(set(row), {"id", "returned"})
        self.assertEqual(run["schema"], "served-memory-run-v1")
        self.assertNotIn("authority_effect", run)
        self.assertNotIn("stop_recommendation", run)

    def test_bad_inputs_fail_before_any_governed_write(self):
        for mode in ("duplicate_id", "empty_query", "budget_zero", "extra_gold"):
            data = copy.deepcopy(self.inputs)
            if mode == "duplicate_id":
                data["writes"][1]["id"] = data["writes"][0]["id"]
            elif mode == "empty_query":
                data["queries"][0]["query"] = ""
            elif mode == "budget_zero":
                data["queries"][0]["budget"] = 0
            else:
                data["queries"][0]["gold"] = {"endpoint": 3}
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises((ValueError, TypeError)):
                    run_scenarios(data, Path(tmp), revision="test", lane_id="quality-v1")


if __name__ == "__main__":
    unittest.main()
