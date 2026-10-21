"""Independent reproducers for the #770 v7 lane freeze (validation of f6c0fa5).

Each -v7 lane must equal its accepted -v6 lane, read as frozen (``_as_frozen``), field for
field except exactly the identity-only list the -v5 to -v6 generation established: the
lane-level fields, the v7 runtime-baseline posture in every Agent Memory row that has one, the
control's display name, a v7 sentence on the deferred shadow and semantic reasons, and on
LongMemEval the dispatch unit naming the -v7 lane. Everything else (dataset, selection, budget,
gold identity, evaluator, harness, sources, adapters, findings) carries over unchanged.

L1  both v7 lanes must satisfy the lane schema; ``list_lanes()`` validates every committed lane,
    so one invalid record breaks every lane lookup, the v1 to v6 lanes included.
L2  comparability, description and freeze rationale must state the v7 rule (equality with the
    accepted -v6 control, any difference blocks Runtime Baseline v7 publication), not the
    inherited v6 rule against -v5.
L3  every Agent Memory row that carries a runtime-baseline posture must carry the v7 posture,
    deferred rows included, as at -v6.
L4  frozen rows carry no status_reason, and the v6 findings carry over without the v6
    acceptance note, so the acceptance-digest reconstruction (``_as_frozen``) round-trips.
L5  the importers must admit exactly the v7 posture and refuse every other declaration blob,
    checker state, lane digest or lane id.
L6  lane records under reference/agentmem_ref/evaluation are not runtime: the five v7 replay
    records must stay VERIFIED (not STALE) while the runtime source boundary is unchanged, and
    a runtime edit must still make them STALE.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import runpy
import subprocess
import sys
import unittest
from pathlib import Path

from agentmem_ref.evaluation.same_harness_lane import lane_digest, list_lanes, resolve_lane, validate_lane

from tests.test_same_harness_lanes_v3 import POSTURE, SEMANTIC_KEY, _as_frozen, _flat

REPO_ROOT = Path(__file__).resolve().parents[2]
LANES = REPO_ROOT / "reference/agentmem_ref/evaluation/lanes"
V7_DECLARATION = "reports/runtime/baseline-v7-declaration.json"
V6_DECLARATION_BLOB = "1ac4d7d87b6b86250b7f4497478e36b2ea17f48a"
PRE_770_V7_DECLARATION_BLOB = "6e13cbaefa3805bc635219f2996fea809af4b224"
LANE_LEVEL = {"/lane_id", "/frozen_on", "/owning_issue", "/description", "/freeze_rationale", "/comparability/notes",
              "/comparability/not_comparable_to"}


def _blob(path: str) -> str:
    return subprocess.run(["git", "hash-object", str(REPO_ROOT / path)], capture_output=True, text=True, check=True).stdout.strip()


def _read(lane_id: str) -> dict:
    return json.loads((LANES / f"{lane_id}.json").read_text(encoding="utf-8"))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LME_IMPORT = _load("import_longmemeval_lane_evidence", REPO_ROOT / "scripts" / "import_longmemeval_lane_evidence.py")
AMB_IMPORT = _load("import_amb_lane_evidence", REPO_ROOT / "scripts" / "import_amb_lane_evidence.py")


class _V7LaneMixin:
    lane_id: str
    v6_id: str
    control_key: str
    posture_rows: set[str]
    deferred_with_sentence: set[str]
    extra_differences: set[str]
    expected_verdicts: int

    def _lane(self) -> dict:
        return _read(self.lane_id)

    def _v6(self) -> dict:
        return _read(self.v6_id)

    # L1
    def test_lane_validates_and_resolves(self):
        lane = validate_lane(self._lane())
        resolve_lane(lane)
        self.assertEqual(lane["status"], "frozen")
        self.assertIs(lane["frozen_before_any_score"], True)

    def test_every_committed_lane_still_lists(self):
        ids = {lane["lane_id"] for lane in list_lanes()}
        self.assertIn(self.lane_id, ids)
        self.assertIn(self.v6_id, ids)

    # field-by-field v6 -> v7
    def test_differs_from_v6_by_exactly_the_identity_list(self):
        v6, v7 = _flat(_as_frozen(self._v6())), _flat(self._lane())
        changed = {path for path in set(v6) | set(v7) if v6.get(path, "<absent>") != v7.get(path, "<absent>")}
        allowed = (
            LANE_LEVEL
            | {f"/systems/{key}{suffix}" for key in self.posture_rows for suffix in POSTURE}
            | {f"/systems/{self.control_key}/display_name"}
            | {f"/systems/{key}/status_reason" for key in self.deferred_with_sentence}
            | self.extra_differences
        )
        self.assertEqual(sorted(changed - allowed), [], "unlisted v6 -> v7 changes")
        self.assertEqual(sorted(allowed - changed), [], "listed identity changes missing")

    # L4
    def test_findings_and_rows_carry_over_without_v6_acceptance(self):
        v6, lane = _as_frozen(self._v6()), self._lane()
        self.assertEqual(lane["findings"], v6["findings"])
        self.assertFalse(any(item.startswith("accepted rows ") for item in lane["findings"]))
        before = {row["provider_key"]: row for row in self._v6()["systems"]}
        for row in lane["systems"]:
            if before[row["provider_key"]]["status"] == "accepted":
                self.assertEqual(row["status"], "frozen", row["provider_key"])
                self.assertNotIn("status_reason", row, row["provider_key"])

    def test_acceptance_digest_reconstruction_round_trips(self):
        lane = self._lane()
        accepted = copy.deepcopy(lane)
        accepted["status"] = "accepted"
        for row in accepted["systems"]:
            if row["status"] == "frozen":
                row["status"], row["status_reason"] = "accepted", "accepted (simulated)"
        accepted["findings"] = accepted["findings"] + ["accepted rows (simulated)"]
        self.assertEqual(lane_digest(_as_frozen(accepted)), lane_digest(lane))

    # L3
    def test_every_agent_memory_row_carries_the_v7_posture(self):
        expected = {
            "predecessor": "agent-memory-runtime-baseline-v6",
            "declared_successor": "agent-memory-runtime-baseline-v7",
            "declaration": V7_DECLARATION,
            "declaration_blob": _blob(V7_DECLARATION),
            "checker_state_required": ["PASS", "TRANSITION"],
        }
        carrying = {row["provider_key"]: row["configuration"]["runtime_baseline_posture"]
                    for row in self._lane()["systems"] if "runtime_baseline_posture" in (row.get("configuration") or {})}
        self.assertEqual(set(carrying), self.posture_rows)
        for key, posture in carrying.items():
            self.assertEqual(posture, expected, key)

    # L2
    def test_comparability_and_rationale_state_the_v7_rule(self):
        lane, v6 = self._lane(), self._v6()
        first = lane["comparability"]["not_comparable_to"][0]
        self.assertTrue(first.startswith(f"{self.v6_id} rows for the same system"), first)
        self.assertIn("declared transition to Runtime Baseline v7", first)
        self.assertIn("relation to the -v6 control is equality", first)
        self.assertIn("not attribution", first)
        self.assertEqual(lane["comparability"]["not_comparable_to"][1:], v6["comparability"]["not_comparable_to"][1:])
        notes = lane["comparability"]["notes"]
        self.assertEqual(notes[:-2], v6["comparability"]["notes"][:-2])
        self.assertIn("against the accepted -v6 control", notes[-2])
        self.assertIn("blocks Runtime Baseline v7 publication", notes[-2])
        self.assertIn("the -v7 control is the single Agent Memory system", notes[-1])
        rationale = " ".join(lane["freeze_rationale"])
        for phrase in ("the -v6 lane is accepted", "equality, not attribution", "any difference blocks v7 publication",
                       f"verdict_counts {{EQUAL: {self.expected_verdicts}}}", "scripts/check_cross_fact_attribution.py",
                       "accepted -v6 rows are never copied forward"):
            self.assertIn(phrase, rationale)
        self.assertIn("Runtime Baseline v7", lane["description"])
        self.assertIn(f"re-executing every executed row of {self.v6_id}", lane["description"])
        for text in [lane["description"], rationale, first, notes[-2], notes[-1]]:
            self.assertNotIn("blocks Runtime Baseline v6 publication", text)
            self.assertNotIn("against the accepted -v5 control", text)


class AmbPrecisionMemBenchV7FreezeTests(_V7LaneMixin, unittest.TestCase):
    lane_id = "amb-precisionmembench-retrieval-v7"
    v6_id = "amb-precisionmembench-retrieval-v6"
    control_key = "agent-memory"
    posture_rows = {"agent-memory", "agent-memory-shadow"}
    deferred_with_sentence = {"agent-memory-shadow", SEMANTIC_KEY}
    extra_differences: set[str] = set()
    expected_verdicts = 77


class LongMemEvalParityV7FreezeTests(_V7LaneMixin, unittest.TestCase):
    lane_id = "longmemeval-s-retrieval-parity-v7"
    v6_id = "longmemeval-s-retrieval-parity-v6"
    control_key = "agent_memory"
    posture_rows = {"agent_memory", "agent_memory_shadow", SEMANTIC_KEY}
    deferred_with_sentence = {"agent_memory_shadow", SEMANTIC_KEY}
    extra_differences = {"/execution/environment/dispatch_unit"}
    expected_verdicts = 1000


# L5: importer negative controls against the v7 lanes (no artifacts, no network, no Actions).
class V7ImporterRefusals(unittest.TestCase):
    def _identity(self, **overrides) -> dict:
        identity = {"runtime_baseline_state": "TRANSITION", "runtime_baseline_line": "Runtime Baseline equivalence: TRANSITION",
                    "declaration_blob": _blob(V7_DECLARATION)}
        identity.update(overrides)
        return identity

    def test_binding_admits_only_the_v7_posture(self):
        for importer, lane_id in ((AMB_IMPORT, "amb-precisionmembench-retrieval-v7"),
                                  (LME_IMPORT, "longmemeval-s-retrieval-parity-v7")):
            lane = validate_lane(_read(lane_id))
            with self.subTest(lane=lane_id, case="v7 TRANSITION admitted"):
                bound = importer.runtime_baseline_binding(self._identity(), lane)
                self.assertEqual(bound["declared_successor"], "agent-memory-runtime-baseline-v7")
            for case, identity in (("v6 declaration blob", self._identity(declaration_blob=V6_DECLARATION_BLOB)),
                                   ("pre-#770 v7 declaration blob", self._identity(declaration_blob=PRE_770_V7_DECLARATION_BLOB)),
                                   ("no declaration blob", self._identity(declaration_blob=None)),
                                   ("checker FAIL", self._identity(runtime_baseline_state="FAIL"))):
                with self.subTest(lane=lane_id, case=case), self.assertRaises(importer.ImportError_):
                    importer.runtime_baseline_binding(identity, lane)

    def test_v6_lanes_refuse_the_v7_declaration(self):
        for importer, lane_id in ((AMB_IMPORT, "amb-precisionmembench-retrieval-v6"),
                                  (LME_IMPORT, "longmemeval-s-retrieval-parity-v6")):
            with self.subTest(lane=lane_id), self.assertRaises(importer.ImportError_):
                importer.runtime_baseline_binding(self._identity(), validate_lane(_read(lane_id)))

    def test_lane_digest_and_lane_id_are_bound(self):
        amb = validate_lane(_read("amb-precisionmembench-retrieval-v7"))
        with self.assertRaises(AMB_IMPORT.ImportError_):
            AMB_IMPORT.check_lane_pins({"bridge_blobs": AMB_IMPORT.lane_reference_blobs(amb),
                                        "lane_digest_sha256": lane_digest(_read("amb-precisionmembench-retrieval-v6"))}, amb)
        AMB_IMPORT.check_lane_pins({"bridge_blobs": AMB_IMPORT.lane_reference_blobs(amb), "lane_digest_sha256": lane_digest(amb)}, amb)
        lme = validate_lane(_read("longmemeval-s-retrieval-parity-v7"))
        good = {"workflow_run_id": "1", "lane_id": lme["lane_id"], "full_selection": True, "subset_size": "0",
                "lane_digest_sha256": lane_digest(lme), "upstream_revision": lme["harness"]["revision"],
                "input_sha256": lme["dataset"]["input_sha256"], "source_blobs": LME_IMPORT.lane_reference_blobs(lme),
                "granularity": "session", "backend": "agent_memory"}
        self.assertEqual(LME_IMPORT._check_identity("1", good, lme)["provider_key"], "agent_memory")
        for case, change in (("v6 lane id", {"lane_id": "longmemeval-s-retrieval-parity-v6"}),
                             ("v6 lane digest", {"lane_digest_sha256": lane_digest(_read("longmemeval-s-retrieval-parity-v6"))}),
                             ("deferred row", {"backend": "agent_memory_shadow"})):
            with self.subTest(case=case), self.assertRaises(LME_IMPORT.ImportError_):
                LME_IMPORT._check_identity("1", {**good, **change}, lme)

    def test_a_revision_without_the_v7_lane_is_refused(self):
        # the importers read the lane at the executing revision; 16a248b predates the v7 lanes
        lane_file = "reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v7.json"
        with self.assertRaises(subprocess.CalledProcessError):
            AMB_IMPORT.lane_at_revision(REPO_ROOT, lane_file, "16a248b1e28f455fbf19217114175f0c20df2a01", at_head=False)


# L6
class ReplayEvidenceFreshness(unittest.TestCase):
    def test_lane_records_do_not_make_replay_evidence_stale(self):
        verifier = runpy.run_path(str(REPO_ROOT / "scripts/verify_644_v7_replays.py"))
        result = verifier["verify"]()
        self.assertEqual({row["replay"]: row["status"] for row in result["replays"]},
                         {row["replay"]: "VERIFIED" for row in result["replays"]}, result)
        self.assertEqual(len(result["replays"]), 5)

    def test_a_runtime_edit_still_makes_replay_evidence_stale(self):
        verifier = runpy.run_path(str(REPO_ROOT / "scripts/verify_644_v7_replays.py"))
        target = REPO_ROOT / "reference/agentmem_ref/runtime/adapter.py"
        original = target.read_bytes()
        try:
            target.write_bytes(original + b"\n# runtime edit probe\n")
            stale = verifier["runtime_changed_since"]("16a248b1e28f455fbf19217114175f0c20df2a01")
        finally:
            target.write_bytes(original)
        self.assertTrue(stale)
        self.assertFalse(verifier["runtime_changed_since"]("16a248b1e28f455fbf19217114175f0c20df2a01"))


if __name__ == "__main__":
    unittest.main()
