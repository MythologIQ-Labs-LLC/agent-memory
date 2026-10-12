"""#771 R-A2/R-A3: declared evaluation instant and separated runtime provenance.

Adversarial cases use REAL git objects of this repository: HEAD, and the
frozen v7 parent 9b025f9 as a genuinely different runtime source.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import served_memory_v3 as v3  # noqa: E402
import run_served_memory_lifecycle_scenarios as lifecycle  # noqa: E402

V7_PARENT = "9b025f945e7ec4a1e349e56bba251e3122413e88"
SELECTOR_773 = "6e00f42f2dc2e81ec137eeecc2ca68f9d1c160e6"  # different runtime_composition.py blob
T = "2026-10-12T12:00:00Z"
V2 = {
    "schema": "served-memory-lifecycle-v2", "tenant": "tenant-a", "project": "proj-a", "purpose": "v3-test",
    "events": [
        {"id": "freeze", "op": "retain", "memory": "freeze", "text": "Deploys are frozen for the holiday window.",
         "temporal": {"valid_from": "2025-11-20T00:00:00Z", "valid_until": "2025-12-01T00:00:00Z"}},
        {"id": "days", "op": "retain", "memory": "days", "text": "Deploys happen on Tuesdays and Thursdays."},
        {"id": "launch", "op": "retain", "memory": "launch", "text": "Deploys move to daily cadence next year.",
         "temporal": {"valid_from": "2027-01-01T00:00:00Z"}},
    ],
    "queries": [{"id": "q", "query": "When do deploys happen?", "intent": "current", "budget": 3}],
}


def _gold(stale):
    return {"schema": "served-memory-quality-v1", "cases": [{
        "id": "q", "scenario": "When do deploys happen?", "intent": "current", "budget": 3,
        "relevance": {"freeze": 1, "days": 3, "launch": 1}, "critical_groups": [["days"]],
        "prohibited": [], "stale": list(stale), "safe_answer_exists": True}]}


def _git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout.strip()


def _provenance(commit, *, evaluator=None):
    return {"evaluator": {"commit": evaluator or _git("rev-parse", "HEAD"), "clean": True},
            "runtime": {"commit": commit, "clean": True,
                        "protected_tree": _git("rev-parse", f"{commit}:{v3.PROTECTED_DIR}"),
                        "loaded_module": v3.MODULE,
                        "loaded_module_blob": _git("rev-parse", f"{commit}:{v3.MODULE}")}}


class ReferenceInstant(unittest.TestCase):
    def test_strict_zone_aware_instants(self):
        for ok in ("2026-10-12T12:00:00Z", "2026-10-12T17:30:00+05:30", "2026-10-12T12:00:00.123456Z"):
            v3.parse_reference_time(ok)
        for bad in (None, 20261012, "2026-10-12T12:00:00", "2026-10-12T12:00:00-00:00", "2026-10-12T12:00:00z",
                    "2026-10-12 12:00:00Z", "2026-10-12T12:00Z", "2026-10-12", "2026-13-01T00:00:00Z",
                    "2026-10-12T12:00:00+24:00", "2026-10-12T12:00:00.1234567Z", "2026-02-30T00:00:00Z"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                v3.parse_reference_time(bad)

    def test_equivalent_offsets_normalize_to_one_instant(self):
        self.assertEqual(v3.parse_reference_time("2026-10-12T14:00:00+02:00"), v3.parse_reference_time(T))

    def test_v2_meaning_is_never_changed(self):
        before = json.dumps(V2, sort_keys=True)
        digest = lifecycle.canonical_input_digest(copy.deepcopy(V2))
        derived = v3.derive_v3(V2, T)
        self.assertEqual(json.dumps(V2, sort_keys=True), before)
        self.assertEqual(lifecycle.canonical_input_digest(copy.deepcopy(V2)), digest)
        with self.assertRaises(ValueError):  # a v2 document may not smuggle an instant
            lifecycle.validate_inputs(dict(copy.deepcopy(V2), reference_time=T))
        missing = dict(derived)
        del missing["reference_time"]
        with self.assertRaises(ValueError):
            v3.validate_inputs_v3(missing, lifecycle)
        self.assertNotEqual(v3.canonical_input_digest_v3(derived, lifecycle), digest)
        self.assertNotEqual(v3.canonical_input_digest_v3(derived, lifecycle),
                            v3.canonical_input_digest_v3(v3.derive_v3(V2, "2026-10-12T14:00:00+02:00"), lifecycle))

    def test_declared_windows_are_evaluated_at_the_declared_instant(self):
        self.assertEqual(v3.temporally_inapplicable(v3.derive_v3(V2, T), lifecycle), ["freeze", "launch"])
        self.assertEqual(v3.temporally_inapplicable(v3.derive_v3(V2, "2025-11-25T00:00:00Z"), lifecycle), ["launch"])
        self.assertEqual(v3.temporally_inapplicable(v3.derive_v3(V2, "2025-12-01T00:00:00Z"), lifecycle),
                         ["freeze", "launch"])  # exclusive end


class RuntimeIdentity(unittest.TestCase):
    def test_true_identity_verifies(self):
        v3.verify_runtime_provenance(_provenance(_git("rev-parse", "HEAD")), ROOT)
        v3.verify_runtime_provenance(_provenance(V7_PARENT), ROOT)

    def test_evaluator_commit_cannot_stand_in_for_a_different_runtime(self):
        # Ran the v7 runtime, but recorded the evaluator's HEAD as the runtime commit.
        prov = _provenance(V7_PARENT)
        prov["runtime"]["commit"] = prov["evaluator"]["commit"]
        with self.assertRaisesRegex(ValueError, "does not match runtime.commit"):
            v3.verify_runtime_provenance(prov, ROOT)

    def test_source_identity_substitution_is_refused(self):
        for field, value in (("protected_tree", _git("rev-parse", f"{SELECTOR_773}:{v3.PROTECTED_DIR}")),
                             ("loaded_module_blob", _git("rev-parse", f"{SELECTOR_773}:{v3.MODULE}"))):
            prov = _provenance(V7_PARENT)
            self.assertNotEqual(prov["runtime"][field], value)
            prov["runtime"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "does not match"):
                v3.verify_runtime_provenance(prov, ROOT)

    def test_unknown_unclean_or_malformed_identity_is_refused(self):
        cases = []
        p = _provenance(V7_PARENT); p["runtime"]["commit"] = "0" * 40; cases.append(p)
        p = _provenance(V7_PARENT); p["runtime"]["clean"] = False; cases.append(p)
        p = _provenance(V7_PARENT); p["evaluator"]["clean"] = False; cases.append(p)
        p = _provenance(V7_PARENT); p["runtime"]["commit"] = V7_PARENT[:12]; cases.append(p)
        p = _provenance(V7_PARENT); p["runtime"]["loaded_module"] = "elsewhere/runtime_composition.py"; cases.append(p)
        p = _provenance(V7_PARENT); del p["evaluator"]; cases.append(p)
        p = _provenance(V7_PARENT); p["runtime_revision"] = V7_PARENT; cases.append(p)
        for i, prov in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ValueError):
                v3.verify_runtime_provenance(prov, ROOT)


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.inputs = v3.derive_v3(V2, T)
        (d / "in.json").write_text(json.dumps(cls.inputs))
        subprocess.run([sys.executable, str(ROOT / "scripts/served_memory_v3.py"), "run", "--runtime-root", str(ROOT),
                        "--inputs", str(d / "in.json"), "--store", str(d / "store"), "--output", str(d / "run.json"),
                        "--lane-id", "v3-test"], check=True, capture_output=True)
        cls.manifest = json.loads((d / "run.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_manifest_separates_runtime_and_evaluator_identity(self):
        m = self.manifest
        self.assertEqual(m["schema"], v3.RUN_SCHEMA_V2)
        self.assertNotIn("runtime_revision", m)
        self.assertEqual(m["provenance"]["runtime"]["protected_tree"], _git("rev-parse", f"HEAD:{v3.PROTECTED_DIR}"))
        self.assertEqual(m["reference_time"], T)
        self.assertEqual(m["reference_time_applied_to"], ["q"])
        self.assertNotIn("freeze", m["rows"][0]["returned"][:1])

    def test_qualification_requires_clean_identity_and_temporal_gold(self):
        clean = self.manifest["provenance"]["evaluator"]["clean"]
        if clean:
            report = v3.qualify_v3(copy.deepcopy(self.inputs), _gold(["freeze", "launch"]),
                                   copy.deepcopy(self.manifest), repo=ROOT)
            self.assertIsNone(report["runtime_revision"])
            self.assertEqual(report["provenance"], self.manifest["provenance"])
            self.assertEqual(len(report["gold_sha256"]), 64)
        else:  # uncommitted evaluator edits: identity cannot be qualified
            with self.assertRaisesRegex(ValueError, "clean"):
                v3.qualify_v3(copy.deepcopy(self.inputs), _gold(["freeze", "launch"]),
                              copy.deepcopy(self.manifest), repo=ROOT)
        with self.assertRaisesRegex(ValueError, "declared window"):
            v3.qualify_v3(copy.deepcopy(self.inputs), _gold(["launch"]), copy.deepcopy(self.manifest), repo=ROOT)

    def test_mismatched_instant_or_inputs_are_refused(self):
        other = v3.derive_v3(V2, "2026-10-12T14:00:00+02:00")  # same instant, different declaration
        with self.assertRaises(ValueError):
            v3.qualify_v3(other, _gold(["freeze", "launch"]), copy.deepcopy(self.manifest), repo=ROOT)
        forged = copy.deepcopy(self.manifest)
        forged["reference_time_utc"] = "2026-10-12T12:00:01.000000Z"
        with self.assertRaises(ValueError):
            v3.qualify_v3(copy.deepcopy(self.inputs), _gold(["freeze", "launch"]), forged, repo=ROOT)


if __name__ == "__main__":
    unittest.main()
