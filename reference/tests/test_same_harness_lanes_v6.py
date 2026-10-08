"""The -v6 same-harness lanes (#732; docs/plan-732-evidence-v6.md V6-E1, V6-E2, V6-E3, V6-E8).

Each -v6 lane equals its accepted -v5 lane field for field except exactly the V6-E3 list:
the lane-level fields, the v6 runtime-baseline posture in every Agent Memory row that has one,
the control's display name, the V6-E2 sentence on the deferred shadow and semantic reasons, the
equality relation in ``comparability.not_comparable_to[0]`` and, on LongMemEval, the dispatch
unit naming the -v6 lane. The runner blob, the bridge blob and version 0.4.0, every identity and
artifact requirement line and every ``adapter.revision_rule`` carry over unchanged; v5 E4's line
edits are not re-applied. No harness changes at v6, so the -v5 harness tests stay the only ones.

The L1 acceptance assertions (verdict_counts ``{"EQUAL": 1000}`` / ``{"EQUAL": 77}`` and per-row
cross-fact equality with -v5) read the imported -v6 evidence. Until that evidence is imported
(V6-E7 step 4) they skip while the lane is ``frozen``; once the lane leaves ``frozen`` a missing
evidence directory fails them.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from agentmem_ref.evaluation.same_harness_lane import get_lane, resolve_lane, validate_lane

from tests.test_same_harness_lanes_v3 import POSTURE, SEMANTIC_KEY, _as_frozen, _flat

REPO_ROOT = Path(__file__).resolve().parents[2]

V6_DECLARATION = "reports/runtime/baseline-v6-declaration.json"
V6_SENTENCE = ("ranking policy 3.4.0 and assertion filter 6.1.0 add only typed-basis branches that no lane input reaches; "
               "the next measurement belongs to #673's lanes")
DEFERRED_SUFFIX = "; at -v6 (plan-732-evidence-v6 V6-E2): " + V6_SENTENCE
# Carried over unchanged from -v5 (V6-E3, L2).
RUNNER_BLOB = "6b9c237380f1d527e564161c2dac7fe32ada0ef9"
BRIDGE_BLOB = "3d9ccb31587b55edf4ddb714d6e8ff41d5b03228"
# The E1 script is reused unchanged (V6-E1): its blob as committed with the -v5 lanes (99847c7).
ATTRIBUTION_SCRIPT_BLOB = "6cfdb2de1de485eced07fbd6036c4f8b16d628ca"
# V6-E3 top level; /status is frozen against the -v5 lane read as frozen, so it shows no difference.
LANE_LEVEL = {"/lane_id", "/frozen_on", "/owning_issue", "/description", "/freeze_rationale", "/comparability/notes",
              "/comparability/not_comparable_to"}
CROSS_FACT_COMPARED = {
    "longmemeval": ("limited_count", "limited_item_ids", "refusal_counts"),
    "amb": ("limited_count", "limited_document_ids", "refusal_counts"),
}


def _blob(path: str) -> str:
    return subprocess.run(["git", "hash-object", str(REPO_ROOT / path)], capture_output=True, text=True, check=True).stdout.strip()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LME_IMPORT = _load("import_longmemeval_lane_evidence", REPO_ROOT / "scripts" / "import_longmemeval_lane_evidence.py")
AMB_IMPORT = _load("import_amb_lane_evidence", REPO_ROOT / "scripts" / "import_amb_lane_evidence.py")
ATTRIBUTION = _load("check_cross_fact_attribution", REPO_ROOT / "scripts" / "check_cross_fact_attribution.py")


# =========================================================================== lane files (V6-E2, V6-E3)
class _V6LaneMixin:
    lane_id: str
    v5_id: str
    benchmark: str
    control_key: str
    shadow_key: str
    blob_path: str
    blob: str
    posture_rows: set[str]
    deferred_with_sentence: set[str]
    extra_differences: set[str]
    workflow_path: str
    expected_verdicts: dict[str, int]

    def _lane(self) -> dict:
        return get_lane(self.lane_id)

    def _v5(self) -> dict:
        return get_lane(self.v5_id)

    def test_lane_validates_resolves_and_is_frozen_before_any_score(self):
        lane = validate_lane(self._lane())
        resolve_lane(lane)
        self.assertEqual(lane["status"], "frozen")
        self.assertIs(lane["frozen_before_any_score"], True)
        self.assertEqual(lane["owning_issue"], 732)
        self.assertEqual(lane["frozen_on"], "2026-10-08")
        self.assertEqual(self._v5()["status"], "accepted")  # the -v5 lane is never edited

    def test_differs_from_v5_by_exactly_the_v6_e3_list(self):
        v5, v6 = _flat(_as_frozen(self._v5())), _flat(_as_frozen(self._lane()))
        changed = {path for path in set(v5) | set(v6) if v5.get(path, "<absent>") != v6.get(path, "<absent>")}
        allowed = (
            LANE_LEVEL
            | {f"/systems/{key}{suffix}" for key in self.posture_rows for suffix in POSTURE}
            | {f"/systems/{self.control_key}/display_name"}
            | {f"/systems/{key}/status_reason" for key in self.deferred_with_sentence}
            | self.extra_differences
        )
        self.assertEqual(changed, allowed)

    def test_rows_findings_and_statuses_follow_v6_e2_e3(self):
        v5, lane = self._v5(), self._lane()
        self.assertEqual(lane["findings"], [item for item in v5["findings"] if not item.startswith("accepted rows ")])
        self.assertEqual(len(lane["findings"]), len(v5["findings"]) - 1)
        before = {row["provider_key"]: row for row in v5["systems"]}
        self.assertEqual([row["provider_key"] for row in lane["systems"]], list(before))
        for row in lane["systems"]:
            key = row["provider_key"]
            if before[key]["status"] == "accepted":
                self.assertEqual(row["status"], "frozen", key)
                self.assertNotIn("status_reason", row)
            elif key in self.deferred_with_sentence:
                self.assertEqual(row["status"], "deferred", key)
                self.assertEqual(row["status_reason"], before[key]["status_reason"] + DEFERRED_SUFFIX, key)
            else:
                self.assertEqual(row, before[key], key)  # Hindsight: unchanged
        executed = {row["provider_key"] for row in lane["systems"] if row["status"] == "frozen"}
        self.assertEqual(executed, self.executed_rows)

    def test_control_and_every_agent_memory_row_carry_the_v6_posture(self):
        lane = self._lane()
        control = next(row for row in lane["systems"] if row["role"] == "control")
        self.assertEqual(control["provider_key"], self.control_key)
        self.assertNotIn("recall_control", control["configuration"])
        self.assertNotIn("semantic_retrieval", control["configuration"])
        self.assertEqual(control["display_name"], "Agent Memory (public facade, declared transition to Runtime Baseline v6)")
        expected = {
            "predecessor": "agent-memory-runtime-baseline-v5",
            "declared_successor": "agent-memory-runtime-baseline-v6",
            "declaration": V6_DECLARATION,
            "declaration_blob": _blob(V6_DECLARATION),
            "checker_state_required": ["PASS", "TRANSITION"],
        }
        carrying = [row for row in lane["systems"] if "runtime_baseline_posture" in (row.get("configuration") or {})]
        self.assertEqual({row["provider_key"] for row in carrying}, self.posture_rows)
        for row in carrying:
            self.assertEqual(row["configuration"]["runtime_baseline_posture"], expected, row["provider_key"])
        declaration = json.loads((REPO_ROOT / V6_DECLARATION).read_text(encoding="utf-8"))
        self.assertEqual(declaration["predecessor_baseline_id"], "agent-memory-runtime-baseline-v5")
        self.assertIn({"kind": "lane", "ref": self.lane_id}, declaration["acceptance_evidence_required"])

    def test_comparability_states_equality_not_attribution(self):
        lane = self._lane()
        first = lane["comparability"]["not_comparable_to"][0]
        self.assertTrue(first.startswith(f"{self.v5_id} rows for the same system"))
        self.assertIn("is equality (plan-732-evidence-v6 V6-E1", first)
        self.assertIn("not attribution", first)
        self.assertNotIn("causally attributed", first)
        self.assertEqual(lane["comparability"]["not_comparable_to"][1:], self._v5()["comparability"]["not_comparable_to"][1:])
        notes, v5_notes = lane["comparability"]["notes"], self._v5()["comparability"]["notes"]
        self.assertEqual(notes[:-2], v5_notes[:-2])
        self.assertIn("plan-732-evidence-v6 V6-E1 equality rule", notes[-2])
        self.assertIn("blocks Runtime Baseline v6 publication", notes[-2])
        self.assertIn("the -v6 control is the single Agent Memory system", notes[-1])
        self.assertFalse(any("causal attribution" in note for note in notes))
        rationale = " ".join(lane["freeze_rationale"])
        for phrase in ("plan-732-evidence-v6 V6-E1", "equality, not attribution", "scripts/check_cross_fact_attribution.py",
                       "reported, never gated", "must be zero", f"verdict_counts {{EQUAL: {self.expected_verdicts['EQUAL']}}}",
                       "proposition extractor", "assertion filter 6.1.0", V6_SENTENCE):
            self.assertIn(phrase, rationale)
        self.assertIn("Runtime Baseline v6", lane["description"])

    def test_blobs_identity_and_revision_rules_carry_over_unchanged(self):
        lane, v5 = self._lane(), self._v5()
        self.assertEqual(lane["harness"], v5["harness"])
        self.assertEqual(lane["harness"]["source_blobs"][self.blob_path], self.blob)
        self.assertEqual(self.blob, _blob(self.blob_path))  # frozen: the pin is HEAD's blob until runs bind it
        self.assertEqual(lane["evaluator"], v5["evaluator"])
        for field in ("execution_identity_requirements", "artifact_requirements"):
            self.assertEqual(lane["execution"].get(field), v5["execution"].get(field), field)
        before = {row["provider_key"]: row for row in v5["systems"]}
        for row in lane["systems"]:
            self.assertEqual(row["adapter"], before[row["provider_key"]]["adapter"], row["provider_key"])
            self.assertEqual(row["source"], before[row["provider_key"]]["source"], row["provider_key"])

    def test_importers_bind_the_cross_fact_records_for_this_generation(self):
        lane = self._lane()
        importer = LME_IMPORT if self.benchmark == "longmemeval" else AMB_IMPORT
        self.assertEqual(importer.lane_generation(lane), 6)
        self.assertGreaterEqual(importer.lane_generation(lane), importer.CROSS_FACT_FIRST_GENERATION)
        self.assertEqual(importer.CROSS_FACT_PROVIDER_KEY, self.control_key)

    def test_the_attribution_script_is_reused_unchanged(self):
        self.assertEqual(_blob("scripts/check_cross_fact_attribution.py"), ATTRIBUTION_SCRIPT_BLOB)

    def test_workflow_offers_and_defaults_to_this_lane(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        self.assertIn(f"- {self.lane_id}", workflow)
        self.assertIn(f"- {self.v5_id}", workflow)
        self.assertIn(f'default: "{self.lane_id}"', workflow)
        self.assertIn('lane["status"] == "frozen"', workflow)  # an accepted lane is refused

    # ----------------------------------------------------------------- L1 acceptance (V6-E1)
    def _evidence_roots(self) -> tuple[Path, Path]:
        root = REPO_ROOT / "reports" / "benchmarks" / self.benchmark
        v5_root, v6_root = root / self.v5_id, root / self.lane_id
        if not v6_root.is_dir():
            if self._lane()["status"] == "frozen":
                self.skipTest(f"{self.lane_id} evidence is not imported yet (plan-732-evidence-v6 V6-E7 step 4)")
            self.fail(f"{self.lane_id} left frozen without imported evidence under {v6_root}")
        return v5_root, v6_root

    def test_acceptance_every_control_output_equals_v5(self):
        # L1: the script exits 0 on ATTRIBUTED; V6-E1 requires every verdict EQUAL.
        v5_root, v6_root = self._evidence_roots()
        check = ATTRIBUTION.check_longmemeval if self.benchmark == "longmemeval" else ATTRIBUTION.check_amb
        result = check(v5_root, v6_root)
        self.assertEqual(ATTRIBUTION._counts(item["verdict"] for item in result["verdicts"]), self.expected_verdicts)

    def test_acceptance_cross_fact_records_equal_v5_row_by_row(self):
        # L1: the script never compares cross-fact records; V6-E1 requires equality with -v5, 0 limited carried over.
        v5_root, v6_root = self._evidence_roots()
        before, after = self._cross_fact_records(v5_root), self._cross_fact_records(v6_root)
        self.assertEqual(list(after), list(before))
        for key, record in after.items():
            self.assertEqual(record, before[key], key)
            self.assertIn((record or {}).get("limited_count", 0), (0, None), key)


class LongMemEvalParityV6LaneTests(_V6LaneMixin, unittest.TestCase):
    lane_id = "longmemeval-s-retrieval-parity-v6"
    v5_id = "longmemeval-s-retrieval-parity-v5"
    benchmark = "longmemeval"
    control_key = "agent_memory"
    shadow_key = "agent_memory_shadow"
    blob_path = "reference/run_longmemeval.py"
    blob = RUNNER_BLOB
    posture_rows = {"agent_memory", "agent_memory_shadow", SEMANTIC_KEY}
    deferred_with_sentence = {"agent_memory_shadow", SEMANTIC_KEY}
    executed_rows = {"agent_memory", "lexical_overlap", "mem0_explicit"}
    extra_differences = {"/execution/environment/dispatch_unit"}
    workflow_path = ".github/workflows/longmemeval-competitive.yml"
    expected_verdicts = {"EQUAL": 1000}

    def test_dispatch_unit_names_the_v6_lane(self):
        lane, v5 = self._lane(), self._v5()
        dispatch = lane["execution"]["environment"]["dispatch_unit"]
        self.assertIn("lane_id longmemeval-s-retrieval-parity-v6:", dispatch)
        self.assertEqual(dispatch.replace(self.lane_id, self.v5_id), v5["execution"]["environment"]["dispatch_unit"])
        self.assertIn("{agent_memory, lexical_overlap, mem0_explicit}", dispatch)

    def test_runner_blob_is_unchanged_everywhere(self):
        text = json.dumps(self._lane())
        self.assertEqual(text.count(RUNNER_BLOB), json.dumps(self._v5()).count(RUNNER_BLOB))
        self.assertIn(RUNNER_BLOB, self._lane()["evaluator"]["scorer"])

    def _cross_fact_records(self, lane_root: Path) -> dict:
        records = {}
        for plane in ATTRIBUTION.PLANES:
            directory = ATTRIBUTION._lme_control_dir(lane_root, plane)
            with gzip.open(directory / "report.rows.json.gz") as handle:
                rows = json.loads(handle.read())[plane]["agent_memory"]
            for row in rows:
                record = row.get("cross_fact")
                records[f"{plane}:{row['question_id']}"] = (
                    None if record is None else {field: record.get(field) for field in CROSS_FACT_COMPARED[self.benchmark]}
                )
        return records


class AmbPrecisionMemBenchV6LaneTests(_V6LaneMixin, unittest.TestCase):
    lane_id = "amb-precisionmembench-retrieval-v6"
    v5_id = "amb-precisionmembench-retrieval-v5"
    benchmark = "amb"
    control_key = "agent-memory"
    shadow_key = "agent-memory-shadow"
    blob_path = "reference/amb_agent_memory_bridge.py"
    blob = BRIDGE_BLOB
    posture_rows = {"agent-memory", "agent-memory-shadow"}  # the AMB semantic row carries none (v5 A7)
    deferred_with_sentence = {"agent-memory-shadow", SEMANTIC_KEY}
    executed_rows = {"agent-memory", "bm25", "mem0-explicit"}
    extra_differences: set[str] = set()
    workflow_path = ".github/workflows/amb-competitive.yml"
    expected_verdicts = {"EQUAL": 77}

    def test_bridge_0_4_0_is_carried_over(self):
        import amb_agent_memory_bridge as bridge

        lane = self._lane()
        self.assertEqual(bridge.BRIDGE_VERSION, "0.4.0")
        for key in ("agent-memory", "agent-memory-shadow"):
            row = next(row for row in lane["systems"] if row["provider_key"] == key)
            self.assertIn("bridge_version 0.4.0", row["adapter"]["revision_rule"])
            self.assertIn(BRIDGE_BLOB, row["adapter"]["revision_rule"])
        self.assertNotIn("dispatch_unit", lane["execution"]["environment"])

    def test_workflow_cross_fact_sidecar_is_unchanged(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR"), 1)
        self.assertIn('export AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR="$RUNNER_TEMP/amb-output/cross-fact.jsonl"', workflow)

    def _cross_fact_records(self, lane_root: Path) -> dict:
        directory = ATTRIBUTION._amb_control_dir(lane_root)
        lines = (directory / ATTRIBUTION.CROSS_FACT_SIDECAR_NAME).read_text(encoding="utf-8").splitlines()
        records = {}
        for line in lines:
            if line.strip():
                record = json.loads(line)
                records[f"{record['call_index']}:{record['query_sha256']}"] = {
                    field: record.get(field) for field in CROSS_FACT_COMPARED[self.benchmark]
                }
        return records


if __name__ == "__main__":
    unittest.main()
