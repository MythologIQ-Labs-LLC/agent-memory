"""#594: the proposition evaluator detects each failure class (evaluator-only fixtures).

These synthetic fixtures prove the evaluator works. They are not Agent Memory
performance evidence and never touch the runtime interpreter.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
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
        for name in ("draft-annotations-v1.json", "draft-annotations-v2.json", "draft-annotations-v3.json", "draft-annotations-v4.json",
                     "draft-annotations-v5.json"):
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
        for name, rubric in (("draft-annotations-v1.json", "annotation-rubric.md"), ("draft-annotations-v2.json", "annotation-rubric-v2.md"),
                             ("draft-annotations-v3.json", "annotation-rubric-v3.md"), ("draft-annotations-v4.json", "annotation-rubric-v4.md"),
                             ("draft-annotations-v5.json", "annotation-rubric-v5.md")):
            draft = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
            self.assertEqual(set(draft["status_labels"]), {"DRAFT", "MODEL-ASSISTED", "NOT ACCEPTED GOLD", "NOT SCORED"})
            self.assertFalse(draft["provenance"]["interpreter_output_consulted"])
            self.assertEqual([i["item_id"] for i in draft["items"]], [i["item_id"] for i in sample["items"]])
            self.assertEqual([i["text_sha256"] for i in draft["items"]], [i["text_sha256"] for i in sample["items"]])
            self.assertEqual(draft["sample_file_sha256"], hashlib.sha256((FIXTURES / "sample-v1.json").read_bytes()).hexdigest())
            self.assertEqual(draft["rubric_sha256"], hashlib.sha256((FIXTURES / rubric).read_bytes()).hexdigest())

    LABEL_FIELDS = ("status", "propositions", "principal", "cardinality", "temporal_aspect", "aspect_explicit",
                    "change_marker", "coexistence_marker", "hedged", "self_authority_claim", "temporal_language_non_temporal")

    def assertManifestComplete(self, old_version: str, new_version: str) -> dict:
        old_bytes = (FIXTURES / f"draft-annotations-{old_version}.json").read_bytes()
        new_bytes = (FIXTURES / f"draft-annotations-{new_version}.json").read_bytes()
        old, new = json.loads(old_bytes), json.loads(new_bytes)
        manifest = json.loads((FIXTURES / f"draft-{old_version}-to-{new_version}-change-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(new["supersedes"]["sha256"], hashlib.sha256(old_bytes).hexdigest())
        self.assertEqual(manifest["new"]["sha256"], hashlib.sha256(new_bytes).hexdigest())
        self.assertEqual(manifest["old"]["sha256"], hashlib.sha256(old_bytes).hexdigest())
        changed = {a["item_id"] for a, b in zip(old["items"], new["items"]) if any(a[f] != b[f] for f in self.LABEL_FIELDS)}
        self.assertEqual(changed, {c["item_id"] for c in manifest["changes"]})
        self.assertEqual(changed, {i for group in manifest["by_reason"].values() for i in group["items"]})
        self.assertEqual(manifest["items_changed"], len(changed))
        required = {"item_id", "reason", "ruling_class", "part", "stratum"} | {
            f"{field}_{version}" for field in ("status", "principal", "cardinality", "temporal_aspect") for version in (old_version, new_version)}
        for change in manifest["changes"]:
            self.assertLessEqual(required, set(change))
        return manifest

    def test_v2_preserves_v1_and_its_change_manifest_is_complete(self) -> None:
        self.assertManifestComplete("v1", "v2")
        v1 = json.loads((FIXTURES / "draft-annotations-v1.json").read_text(encoding="utf-8"))
        v2 = json.loads((FIXTURES / "draft-annotations-v2.json").read_text(encoding="utf-8"))
        rulings = [i for i in v2["items"] if i["maintainer_ruling"]]
        self.assertEqual(len(rulings), 15)
        self.assertEqual({i["item_id"] for i in rulings}, {i["item_id"] for i in v1["items"] if i["boundary_case"]})

    def test_original_v1_to_v2_manifest_is_preserved_and_agrees(self) -> None:
        original = json.loads((FIXTURES / "draft-v1-to-v2-changes.json").read_text(encoding="utf-8"))
        generated = json.loads((FIXTURES / "draft-v1-to-v2-change-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(original["v2"]["sha256"], generated["new"]["sha256"])
        self.assertEqual({i["item_id"] for group in original["by_reason"].values() for i in group["items"]},
                         {c["item_id"] for c in generated["changes"]})

    def test_v3_preserves_v2_and_its_change_manifest_is_complete(self) -> None:
        manifest = self.assertManifestComplete("v2", "v3")
        rereview = manifest["rereview_of_v1_to_v2_changes"]
        v1_to_v2 = json.loads((FIXTURES / "draft-v1-to-v2-change-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(rereview["outcomes"]), {c["item_id"] for c in v1_to_v2["changes"]})
        self.assertEqual(rereview["confirmed"] + rereview["revised"], v1_to_v2["items_changed"])

    def test_v4_preserves_v3_and_its_change_manifest_is_complete(self) -> None:
        manifest = self.assertManifestComplete("v3", "v4")
        direct = set(manifest["by_ruling_class"]["maintainer_third_review"]["items"])
        self.assertEqual(direct, {"ps1-063", "ps1-068", "ps1-082", "ps1-086", "ps1-103"})

    # Frozen draft provenance (maintainer rulings on PR #595): these bytes may never change.
    FROZEN_SHA256 = {
        "annotation-rubric.md": "47df0caf2413a0e65f9fe609181f162f54c2a6a857583a92e050ac89a33dff26",
        "draft-annotations-v1.json": "5cba499b99c820c8b8462d2ae28197f690fe1c2b88a9d97a598f9398184295f4",
        "annotation-rubric-v2.md": "ac13697f6a1a301dee7c088cfbf88925636e28fd224e22e9050a8b7cf10c92a2",
        "draft-annotations-v2.json": "8f333b3800bb2ce7553ac5968c8b6978f5fe64662e2863b58fea16dc463f1b2d",
        "draft-v1-to-v2-changes.json": "0cd415b9d8b8b61b1d2e4676b5d285cc9cc3b36443faee7ccd968dad024569be",
        "draft-v1-to-v2-change-manifest.json": "be6983311639d9407581a0c8c8df71ba0e63d7b8f96a24cf301efe1a8e3543bb",
        "annotation-rubric-v3.md": "d8b9da4900c9996e0a9843587d827800a14b97b5ac8ee569d597d5b35bf249b7",
        "draft-annotations-v3.json": "e9fe56ee6b15c6c7fce8e129a836046c4c25adf503e764aa9984cd1d66f32fa4",
        "draft-v2-to-v3-change-manifest.json": "d9af0eab27160d045d73dc08b84654b92821d51a1bc40043d1569cee3a5f28bb",
        # v4 frozen by the gold-freeze review (PR #595 review 5339604740)
        "annotation-rubric-v4.md": "1b8fe1132986d2b8c1094a7844f5a55fac9e05aea2906d64954b428d4297e94d",
        "draft-annotations-v4.json": "9314154aa65d1240a7af454bae04f46fdcce9bc132e1c0892bae629c226d356c",
        "draft-v3-to-v4-change-manifest.json": "e529a259c1c1b8b4c546a353d012be779c3b79df6b7f44cddf2543571c40d47a",
    }

    def test_frozen_drafts_v1_to_v4_are_unchanged(self) -> None:
        for name, digest in self.FROZEN_SHA256.items():
            self.assertEqual(hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest(), digest, name)

    def test_v4_and_v5_record_no_request_only_content_as_a_proposition(self) -> None:
        for version in ("v4", "v5"):
            self.assertNoRequestOnlyContent(json.loads((FIXTURES / f"draft-annotations-{version}.json").read_text(encoding="utf-8")))

    def assertNoRequestOnlyContent(self, draft: dict) -> None:
        by_id = {item["item_id"]: item for item in draft["items"]}
        excluded = {item_id for item_id, item in by_id.items() if item["excluded_request_only_content"]}
        self.assertLessEqual({"ps1-063", "ps1-082", "ps1-086", "ps1-103"}, excluded)
        for item in draft["items"]:
            rendered = json.dumps(item["propositions"]).lower()
            for entry in item["excluded_request_only_content"]:
                for term in entry["absent_terms"]:
                    self.assertNotIn(term.lower(), rendered, (item["item_id"], entry["value"]))
            self.assertTrue(all(p["polarity"] in {"affirmed", "ended", "negated"} for p in item["propositions"]))
        principal = by_id["ps1-063"]["propositions"][by_id["ps1-063"]["principal"]]
        self.assertEqual((principal["property"], principal["value"]),
                         ("looking for", "a hotel in Seattle, close to the city center and not too expensive"))
        self.assertIn("vinyl", json.dumps(by_id["ps1-086"]["propositions"]))
        self.assertIn("dessert adventure", json.dumps(by_id["ps1-103"]["propositions"]))

    def test_no_prediction_file_and_no_runtime_change(self) -> None:
        names = {path.name for path in FIXTURES.iterdir()}
        self.assertFalse([name for name in names if "prediction" in name or "accepted-gold" in name])
        for name in names:
            if name.startswith("draft-annotations-"):
                self.assertFalse(json.loads((FIXTURES / name).read_text(encoding="utf-8"))["provenance"]["interpreter_output_consulted"])
        base = "691251ca27f5e8e87a7c259c1a47a7050f32291b"  # #594 base on main
        probe = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{base}^{{commit}}"], capture_output=True)
        if probe.returncode != 0:
            self.skipTest("base commit not available in this checkout (shallow clone)")
        diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", base, "HEAD", "--", "reference/agentmem_ref"], capture_output=True)
        self.assertEqual(diff.returncode, 0, "runtime files under reference/agentmem_ref changed")

    def test_v5_preserves_v4_and_its_change_manifest_is_complete(self) -> None:
        manifest = self.assertManifestComplete("v4", "v5")
        self.assertEqual(set(manifest["by_ruling_class"]["maintainer_gold_freeze_review"]["items"]), {"ps1-046", "ps1-072"})
        self.assertIn("upstream_proposition_defect_turn_alone_budget_object", manifest["by_reason"])

    def test_v5_cardinality_invariants(self) -> None:
        v4 = {i["item_id"]: i for i in json.loads((FIXTURES / "draft-annotations-v4.json").read_text(encoding="utf-8"))["items"]}
        v5 = json.loads((FIXTURES / "draft-annotations-v5.json").read_text(encoding="utf-8"))
        by_id = {item["item_id"]: item for item in v5["items"]}
        for item in v5["items"]:
            # single_valued needs a recorded exclusive slot; uncertainty never defaults to it.
            self.assertEqual(item["cardinality"] == "single_valued", bool(item["cardinality_basis"]), item["item_id"])
            properties = " ".join(p["property"].lower() for p in item["propositions"])
            self.assertNotIn("overall state", properties, item["item_id"])
            old = v4[item["item_id"]]
            # A cardinality decision never rewrites the principal property.
            if item["cardinality"] != old["cardinality"] and item["status"] == old["status"] == "known":
                self.assertEqual(item["propositions"][item["principal"]]["property"], old["propositions"][old["principal"]]["property"], item["item_id"])
        # Gold-freeze review rulings.
        self.assertEqual((by_id["ps1-072"]["status"], by_id["ps1-072"]["principal"], by_id["ps1-072"]["cardinality"]), ("ambiguous", None, "unknown"))
        self.assertNotIn("gift budget", json.dumps(by_id["ps1-072"]["propositions"]))
        self.assertEqual(by_id["ps1-046"]["cardinality"], "multi_valued")
        for item_id in ("ps1-095", "ps1-156"):
            self.assertEqual(by_id[item_id]["status"], "known")
        for item_id in ("ps1-089", "ps1-234", "ps1-190", "ps1-052"):
            self.assertEqual(by_id[item_id]["status"], "ambiguous")

    def test_v5_labels_are_internally_consistent(self) -> None:
        v5 = json.loads((FIXTURES / "draft-annotations-v5.json").read_text(encoding="utf-8"))
        v4 = {i["item_id"]: i for i in json.loads((FIXTURES / "draft-annotations-v4.json").read_text(encoding="utf-8"))["items"]}
        for item in v5["items"]:
            status = item["status"]
            self.assertEqual(item["principal"] is not None, status == "known", item["item_id"])
            self.assertEqual(bool(item["propositions"]), status != "unknown", item["item_id"])
            if status == "known":
                self.assertLess(item["principal"], len(item["propositions"]))
            if item["item_id"] != "ps1-072":
                self.assertEqual(status, v4[item["item_id"]]["status"], item["item_id"])
            self.assertNotRegex(item["notes"], r"(?i)\b(transient|not (clearly )?durable|momentary)\b", item["item_id"])

    def test_change_manifests_are_regenerated_from_the_annotation_files(self) -> None:
        spec = importlib.util.spec_from_file_location("build_change_manifest", FIXTURES / "build_change_manifest.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in module.PAIRS:
            self.assertEqual(module.render(name), (FIXTURES / name).read_text(encoding="utf-8"), name)

    def test_v4_labels_are_internally_consistent(self) -> None:
        v4 = json.loads((FIXTURES / "draft-annotations-v4.json").read_text(encoding="utf-8"))
        rulings = {"ps1-006": "known", "ps1-051": "ambiguous", "ps1-087": "known", "ps1-098": "known", "ps1-134": "ambiguous",
                   "ps1-150": "known", "ps1-158": "ambiguous", "ps1-166": "known", "ps1-180": "known", "ps1-181": "known",
                   "ps1-197": "known", "ps1-205": "ambiguous", "ps1-218": "ambiguous", "ps1-257": "ambiguous", "ps1-267": "known",
                   # second maintainer review (PR #595 review 5338941285)
                   "ps1-010": "known", "ps1-252": "ambiguous",
                   # third maintainer review (PR #595 review 5339238113)
                   "ps1-063": "known", "ps1-068": "known", "ps1-082": "known", "ps1-086": "known", "ps1-103": "ambiguous"}
        by_id = {item["item_id"]: item for item in v4["items"]}
        # Third review: request-only content is not recorded as an asserted proposition.
        self.assertEqual([p["property"] for p in by_id["ps1-082"]["propositions"]], ["uses paint (for the T-34 tank model)"])
        self.assertNotIn("looking for", [p["property"] for p in by_id["ps1-086"]["propositions"]])
        self.assertNotIn("Orlando", json.dumps(by_id["ps1-103"]["propositions"]))
        self.assertEqual(by_id["ps1-068"]["propositions"][by_id["ps1-068"]["principal"]]["value"], "some of my vintage items")
        for item in v4["items"]:
            status = item["status"]
            self.assertIn(status, E.STATUSES)
            self.assertEqual(item["principal"] is not None, status == "known", item["item_id"])
            self.assertEqual(bool(item["propositions"]), status != "unknown", item["item_id"])
            if status == "known":
                self.assertLess(item["principal"], len(item["propositions"]))
                self.assertNotEqual(item["cardinality"], "unknown", item["item_id"])
            if item["item_id"] in rulings:
                self.assertEqual(status, rulings[item["item_id"]], item["item_id"])
            # Semantic interpretation is not retention policy: duration is never a stated reason.
            self.assertNotRegex(item["notes"], r"(?i)\b(transient|not (clearly )?durable|momentary)\b", item["item_id"])


if __name__ == "__main__":
    unittest.main()
