"""#732 oracle-ceiling diagnostic tooling, on synthetic fixtures only.

The frozen corpus is never read here. These tests pin that the oracle is derived from metadata
only, that each mode labels as documented, and that the unchanged runner's stages respond to the
oracle evidence (and that the harness is restored afterwards).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

import run_currentness_generalization as runner  # noqa: E402
import run_currentness_oracle_ceiling as oracle  # noqa: E402

OLD = "The billing service runs on Django 4.2."
NEW = "Billing service: Django 5.1 now."


def _write(handle, scope, ref, text, source=None):
    return {"handle": handle, "scope": scope, "target_reference": ref, "text": text, "source_ref": source}


def _case(family="P1", expected="engage", old=OLD, new=NEW, **extra):
    return {
        "case_id": "syn-1", "family": family, "expected": expected,
        "writes": [_write("A", "S1", "memory:billing:1", old), _write("A", "S1", "memory:billing:2", new)],
        "older_write": 0, "newer_write": 1, "actions": [],
        "recall_as": {"handle": "A", "scope": "S1"},
        "query": "Which Django version is the billing service on?", "rationale": "Synthetic fixture.", **extra,
    }


class LabelTests(unittest.TestCase):
    def test_labels_do_not_depend_on_text(self):
        a = oracle.labels_for(_case(family="N3", expected="refrain"), "N3", "gold")
        b = oracle.labels_for(_case(family="N3", expected="refrain", old="x one", new="y two"), "N3", "gold")
        self.assertEqual([v["proposition"] for v in a.values()], [v["proposition"] for v in b.values()])

    def test_gold_sets_family_flag_and_flag_blind_does_not(self):
        gold = oracle.newer_label(_case(family="N3"), "N3", "gold")
        blind = oracle.newer_label(_case(family="N3"), "N3", "flag_blind")
        self.assertTrue(gold["flags"]["joke_or_sarcasm"])
        self.assertFalse(any(blind["flags"].values()))

    def test_must_change_variant_uses_variant_flag(self):
        label = oracle.newer_label({"kind": "must_change", "variant_type": "coexistent"}, "P1", "gold")
        self.assertTrue(label["flags"]["coexistent"])
        self.assertEqual(label["cardinality"], "multi")

    def test_structural_variant_gets_clean_change(self):
        label = oracle.newer_label({"kind": "must_change", "variant_type": "change_actor"}, "P1", "gold")
        self.assertEqual((label["assertion"], any(label["flags"].values())), ("change", False))

    def test_slot_drift_changes_wording_only(self):
        gold = oracle.newer_label(_case(), "P1", "gold")
        drift = oracle.newer_label(_case(), "P1", "slot_drift")
        self.assertNotEqual((gold["subject"], gold["attribute"]), (drift["subject"], drift["attribute"]))
        self.assertEqual({k: v for k, v in gold.items() if k not in ("subject", "attribute")},
                         {k: v for k, v in drift.items() if k not in ("subject", "attribute")})

    def test_duplicate_texts_are_invalid(self):
        self.assertIsNone(oracle.labels_for(_case(new=OLD), "P1", "gold"))


class StageTests(unittest.TestCase):
    def test_gold_engages_where_extractor_off_does_not(self):
        self.assertNotEqual(runner.run_record(_case())["stage"], "S7")
        result = oracle.run_with_oracle(_case(), "P1", "gold")
        self.assertEqual(result["stage"], "S7")
        self.assertTrue(result["observations"]["oracle_older_in_candidates"])

    def test_gold_flag_refuses(self):
        self.assertNotEqual(oracle.run_with_oracle(_case(family="N3", expected="refrain"), "N3", "gold")["stage"], "S7")

    def test_gold_different_actor_refuses_at_g8(self):
        case = _case(family="N9", expected="refrain")
        case["writes"][1]["handle"] = "B"
        result = oracle.run_with_oracle(case, "N9", "gold")
        self.assertEqual((result["stage"], result["reason"]), ("S5", "guard_refusal:G8"))

    def test_slot_drift_is_measured_not_assumed(self):
        self.assertIn(oracle.run_with_oracle(_case(), "P1", "slot_drift")["stage"], {"S3", "S4"})

    def test_harness_open_is_restored(self):
        before = runner._open
        oracle.run_with_oracle(_case(), "P1", "gold")
        self.assertIs(runner._open, before)


if __name__ == "__main__":
    unittest.main()
