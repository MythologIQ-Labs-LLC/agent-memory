"""#771: independent audit of the execution->gold->score handoff.

These tests do not assume the real runtime achieves any target metric.
They reject protocol drift and source-scope masking before judging results.
"""
from __future__ import annotations

import copy
import hashlib
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
            "input_sha256": hashlib.sha256(json.dumps(
                cls.inputs, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")).hexdigest(),
            "execution_backend": "composed-multiroute",
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
        self.assertEqual(report["P1_served_correctness"]["empty_delivery_on_answerable_count"], 4)
        self.assertIsNone(report["P1_served_correctness"]["answer_abstention_verified"])
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

    def test_runtime_run_requires_exact_input_digest_binding(self):
        for mutation in ("missing", "wrong", "legacy"):
            run = copy.deepcopy(self.run)
            if mutation == "missing":
                run.pop("input_sha256")
            elif mutation == "wrong":
                run["input_sha256"] = "0" * 64
            else:
                run.pop("execution_backend")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                qualify(copy.deepcopy(self.inputs), copy.deepcopy(self.gold), run)

    def test_changed_write_text_with_identical_opaque_ids_is_rejected(self):
        # Equal IDs do not mean equal underlying memory. The run must be
        # bound to the exact source content, not merely matching row labels.
        altered = copy.deepcopy(self.inputs)
        altered["writes"][0]["text"] += " secretly changed"
        with self.assertRaises(ValueError):
            qualify(altered, copy.deepcopy(self.gold), copy.deepcopy(self.run))

    def test_backend_provenance_is_closed_not_assumed_from_lane_label(self):
        run = copy.deepcopy(self.run)
        run["execution_backend"] = "invented-memory-provider"
        with self.assertRaises(ValueError):
            qualify(copy.deepcopy(self.inputs), copy.deepcopy(self.gold), run)

    def test_gold_only_change_cannot_modify_runtime_input_fingerprint(self):
        report = qualify(copy.deepcopy(self.inputs), copy.deepcopy(self.gold),
                         copy.deepcopy(self.run))
        self.assertEqual(report["execution_backend"], "composed-multiroute")
        self.assertEqual(report["input_sha256"], self.run["input_sha256"])

    def test_unscored_case_ids_cannot_be_dropped_from_run(self):
        run = copy.deepcopy(self.run)
        run["rows"].pop()
        with self.assertRaises(ValueError):
            qualify(copy.deepcopy(self.inputs), copy.deepcopy(self.gold), run)


if __name__ == "__main__":
    unittest.main()
