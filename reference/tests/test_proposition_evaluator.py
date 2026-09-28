"""#594: the proposition evaluator detects each failure class (evaluator-only fixtures).

These synthetic fixtures prove the evaluator works. They are not Agent Memory
performance evidence and never touch the runtime interpreter.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

import proposition_semantics_evaluator as E  # noqa: E402

FIXTURES = REFERENCE / "fixtures" / "benchmarks" / "proposition-semantics"


def _gold(item_id, status, props=(), principal=None, cardinality="unknown", aspect="none_unknown", coexistence="no"):
    return {
        "item_id": item_id, "status": status,
        "propositions": [dict(zip(("entity", "property", "value", "polarity"), p)) for p in props],
        "principal": principal, "cardinality": cardinality, "temporal_aspect": aspect,
        "coexistence_marker": coexistence,
    }


GOLD = [
    _gold("g1", "known", [("user", "residence", "Lisbon", "affirmed")], 0, "hierarchical", "present"),
    _gold("g2", "known", [("user", "likes", "gardening", "affirmed")], 0, "multi_valued", "present", coexistence="yes"),
    _gold("g3", "unknown"),
    _gold("g4", "ambiguous", [("user", "owns", "a bike", "affirmed"), ("user", "owns", "a car", "affirmed")]),
    _gold("g5", "known", [("user", "planned trip", "Denver", "affirmed")], 0, "multi_valued", "prospective"),
]
PERFECT = {
    "g1": {"status": "known", "entity": "I", "property": "residence", "value": "Lisbon", "cardinality": "hierarchical", "aspect": "present"},
    "g2": {"status": "known", "entity": "user", "property": "likes", "value": "gardening", "cardinality": "multi_valued", "aspect": "present"},
    "g3": {"status": "unknown"},
    "g4": {"status": "ambiguous"},
    "g5": {"status": "known", "entity": "user", "property": "planned trip", "value": "a trip to Denver", "cardinality": "multi_valued", "aspect": "prospective"},
}
STAMPS = ("2023-05-20T02:21:00Z", "2023/05/20 (Sat) 02:21")


def _run(predictions):
    return E.evaluate(GOLD, predictions, source_timestamps=STAMPS)


def _mutate(item_id, **changes):
    predictions = copy.deepcopy(PERFECT)
    predictions[item_id].update(changes)
    return predictions


class EvaluatorContractTests(unittest.TestCase):
    def test_perfect_predictions_have_no_failures_and_no_aggregate_score(self) -> None:
        report = _run(PERFECT)
        self.assertEqual(report["failure_counts"], {"slot_and_value_correct": 3})
        self.assertEqual(report["aggregate_score"], "not_defined")
        self.assertEqual(report["items_evaluated"], 5)

    def assertOnly(self, predictions, expected_class, item_id):
        report = _run(predictions)
        self.assertEqual([(f["item_id"], f["class"]) for f in report["findings"]], [(item_id, expected_class)])

    def test_detects_wrong_proposition_slot(self) -> None:
        self.assertOnly(_mutate("g1", property="employer"), "wrong_slot", "g1")
        self.assertOnly(_mutate("g1", entity="my sister"), "wrong_slot", "g1")

    def test_detects_wrong_value(self) -> None:
        self.assertOnly(_mutate("g1", value="Porto"), "wrong_value", "g1")

    def test_detects_over_eager_single_valued(self) -> None:
        self.assertOnly(_mutate("g5", cardinality="single_valued"), "over_eager_single_valued", "g5")

    def test_detects_coexistence_misclassified_as_replacement(self) -> None:
        self.assertOnly(_mutate("g2", replacement=True), "coexistence_as_replacement", "g2")
        self.assertOnly(_mutate("g2", change=True), "coexistence_as_replacement", "g2")

    def test_detects_temporal_aspect_over_classification(self) -> None:
        self.assertOnly(_mutate("g3", aspect="present"), "aspect_over_classification", "g3")
        self.assertOnly(_mutate("g5", aspect="present"), "aspect_mismatch", "g5")

    def test_detects_unknown_promoted_to_known(self) -> None:
        self.assertOnly(_mutate("g3", status="known", entity="user", property="x", value="y"), "unknown_promoted_to_known", "g3")
        self.assertOnly(_mutate("g4", status="known", entity="user", property="owns", value="a bike"), "unknown_promoted_to_known", "g4")

    def test_detects_benchmark_timestamp_leakage(self) -> None:
        self.assertOnly(_mutate("g1", declared_observed_at="2023-05-20T02:21:00Z"), "timestamp_leakage", "g1")
        self.assertOnly(_mutate("g3", note="valid until 2023/05/20 (Sat) 02:21"), "timestamp_leakage", "g3")

    def test_property_aliases_are_explicit_not_fitted(self) -> None:
        predictions = _mutate("g1", property="lives_in")
        self.assertEqual(_run(predictions)["failure_counts"].get("wrong_slot"), 1)
        report = E.evaluate(GOLD, predictions, property_aliases={"residence": ["lives in"]})
        self.assertNotIn("wrong_slot", report["failure_counts"])

    def test_missing_predictions_are_reported_not_scored(self) -> None:
        predictions = copy.deepcopy(PERFECT)
        del predictions["g4"]
        report = _run(predictions)
        self.assertEqual(report["missing_predictions"], ["g4"])
        self.assertEqual(report["items_evaluated"], 4)

    def test_evaluation_is_deterministic(self) -> None:
        self.assertEqual(json.dumps(_run(PERFECT), sort_keys=True), json.dumps(_run(copy.deepcopy(PERFECT)), sort_keys=True))

    def test_runtime_prediction_mapping_is_schema_only(self) -> None:
        record = E.normalize_runtime_prediction({
            "proposition": {"status": "known", "entity": "user", "property": "residence", "value": "Lisbon"},
            "cardinality": {"class": "single_valued", "basis": "interpreted_replacement_marker"},
            "markers": {"change": ["moved"], "aspect": {"present": ["currently"]}, "hedge": []},
        })
        self.assertEqual((record["status"], record["replacement"], record["change"], record["aspect"], record["declared_observed_at"]),
                         ("known", True, True, "present", None))


class GoldFreezeTests(unittest.TestCase):
    def test_draft_annotations_are_refused(self) -> None:
        for name in ("draft-annotations-v1.json", "draft-annotations-v2.json"):
            with self.assertRaises(E.GoldNotAccepted):
                E.load_gold(FIXTURES / name)

    def test_only_explicitly_accepted_gold_loads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.json"
            path.write_text(json.dumps({"status_labels": ["ACCEPTED GOLD"], "items": []}))
            with self.assertRaises(E.GoldNotAccepted):
                E.load_gold(path)
            path.write_text(json.dumps({"status_labels": ["ACCEPTED GOLD"], "acceptance": {"accepted_by": "maintainer", "accepted_at": "2026-10-01"}, "items": []}))
            self.assertEqual(E.load_gold(path)["items"], [])


class SampleIndependenceTests(unittest.TestCase):
    """Pin the Phase B freeze: the sample is selected without Agent Memory and without gold."""

    def test_selector_imports_nothing_from_agent_memory(self) -> None:
        source = (FIXTURES / "select_sample.py").read_text(encoding="utf-8")
        imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
        self.assertFalse([line for line in imports if "agentmem" in line or "run_longmemeval" in line or "proposition" in line])
        code = source.split('"""', 2)[2]
        self.assertNotIn("has_answer", code)
        self.assertNotIn("answer_session_ids", code)

    def test_frozen_sample_matches_manifest(self) -> None:
        manifest = json.loads((FIXTURES / "sample-v1.manifest.json").read_text(encoding="utf-8"))
        sample_bytes = (FIXTURES / "sample-v1.json").read_bytes()
        self.assertEqual(hashlib.sha256(sample_bytes).hexdigest(), manifest["sample"]["sample_file_sha256"])
        self.assertEqual(hashlib.sha256((FIXTURES / "select_sample.py").read_bytes()).hexdigest(), manifest["selection"]["script_sha256"])
        items = json.loads(sample_bytes)["items"]
        self.assertEqual(len(items), manifest["sample"]["size"])
        for item in items:
            self.assertEqual(hashlib.sha256(item["text"].encode("utf-8")).hexdigest(), item["text_sha256"])
        self.assertFalse(manifest["selection"]["interpreter_used"])
        self.assertFalse(manifest["selection"]["gold_fields_used"])

    def test_draft_annotations_cover_the_sample_and_stay_marked_draft(self) -> None:
        sample = json.loads((FIXTURES / "sample-v1.json").read_text(encoding="utf-8"))
        for name, rubric in (("draft-annotations-v1.json", "annotation-rubric.md"), ("draft-annotations-v2.json", "annotation-rubric-v2.md")):
            draft = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
            self.assertEqual(set(draft["status_labels"]), {"DRAFT", "MODEL-ASSISTED", "NOT ACCEPTED GOLD", "NOT SCORED"})
            self.assertFalse(draft["provenance"]["interpreter_output_consulted"])
            self.assertEqual([i["item_id"] for i in draft["items"]], [i["item_id"] for i in sample["items"]])
            self.assertEqual([i["text_sha256"] for i in draft["items"]], [i["text_sha256"] for i in sample["items"]])
            self.assertEqual(draft["sample_file_sha256"], hashlib.sha256((FIXTURES / "sample-v1.json").read_bytes()).hexdigest())
            self.assertEqual(draft["rubric_sha256"], hashlib.sha256((FIXTURES / rubric).read_bytes()).hexdigest())

    def test_v2_preserves_v1_and_its_change_manifest_is_complete(self) -> None:
        v1_bytes = (FIXTURES / "draft-annotations-v1.json").read_bytes()
        v1 = json.loads(v1_bytes)
        v2 = json.loads((FIXTURES / "draft-annotations-v2.json").read_text(encoding="utf-8"))
        manifest = json.loads((FIXTURES / "draft-v1-to-v2-changes.json").read_text(encoding="utf-8"))
        self.assertEqual(v2["supersedes"]["sha256"], hashlib.sha256(v1_bytes).hexdigest())
        self.assertEqual(manifest["v2"]["sha256"], hashlib.sha256((FIXTURES / "draft-annotations-v2.json").read_bytes()).hexdigest())
        label_fields = ("status", "propositions", "principal", "cardinality", "temporal_aspect", "aspect_explicit",
                        "change_marker", "coexistence_marker", "hedged", "self_authority_claim", "temporal_language_non_temporal")
        changed = {a["item_id"] for a, b in zip(v1["items"], v2["items"]) if any(a[f] != b[f] for f in label_fields)}
        listed = {c["item_id"] for group in manifest["by_reason"].values() for c in group["items"]}
        self.assertEqual(changed, listed)
        self.assertEqual(manifest["items_changed"], len(changed))
        rulings = [i for i in v2["items"] if i["maintainer_ruling"]]
        self.assertEqual(len(rulings), 15)
        self.assertEqual({i["item_id"] for i in rulings}, {i["item_id"] for i in v1["items"] if i["boundary_case"]})


if __name__ == "__main__":
    unittest.main()
