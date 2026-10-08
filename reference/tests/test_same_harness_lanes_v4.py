"""The -v4 same-harness lanes (#644 S9; docs/plan-644-lanes-v4.md L1-L9).

Each -v4 lane equals its accepted -v3 lane field for field except exactly the L5 differences:
lane-level fields, the v4 runtime-baseline posture, the control's display name, the new shadow
row, and per lane the runner (LongMemEval) or bridge 0.3.0 (AMB) pins, the deferred LongMemEval
semantic row, and the shadow identity/artifact requirements. The control runs the shipped
default (no recall_control key, read as off).
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from agentmem_ref.evaluation.registry import get_integration
from agentmem_ref.evaluation.same_harness_lane import get_lane, lane_digest, resolve_lane, validate_lane

from tests.test_same_harness_lanes_v3 import POSTURE, SEMANTIC_KEY, _as_frozen, _flat

REPO_ROOT = Path(__file__).resolve().parents[2]
V4_DECLARATION = "reports/runtime/baseline-v4-declaration.json"
SHADOW_ROW_ID = "agent-memory-recall-control-shadow"


def _blob(path: str) -> str:
    return subprocess.run(["git", "hash-object", str(REPO_ROOT / path)], capture_output=True, text=True, check=True).stdout.strip()


# frozen_on is listed by L5 but equals -v3's date (both froze on 2026-10-07), so it shows no difference.
LANE_LEVEL = {"/lane_id", "/owning_issue", "/description", "/freeze_rationale", "/comparability/notes",
              "/comparability/not_comparable_to"}


class _V4LaneMixin:
    lane_id: str
    v3_id: str
    control_key: str
    shadow_key: str
    extra_differences: set[str]
    workflow_path: str

    def _lane(self) -> dict:
        return get_lane(self.lane_id)

    def test_lane_validates_resolves_and_was_frozen_before_any_score(self):
        lane = validate_lane(self._lane())
        resolve_lane(lane)
        self.assertIn(lane["status"], {"frozen", "accepted"})
        self.assertIs(lane["frozen_before_any_score"], True)
        self.assertEqual(lane["owning_issue"], 644)

    def test_accepted_rows_are_bound_to_evidence_executed_under_the_v4_transition(self):
        # plan-644-lanes-v4 L7: every executed row is accepted and bound by its evidence_history
        # entries; deferred rows are recorded as blocked. Acceptance adds only statuses,
        # status_reasons and one findings note, so undoing them gives the digest the run executed.
        lane = self._lane()
        self.assertEqual(lane["status"], "accepted")
        integration = get_integration(lane["benchmark_integration"])
        history = {entry["variant"]: entry for entry in integration["evidence_history"]}
        for row in lane["systems"]:
            prefix = f"lane:{self.lane_id}:{row['provider_key']}"
            variants = [variant for variant in history if variant == prefix or variant.startswith(prefix + ":")]
            if row["status"] == "deferred":
                self.assertEqual([history[v]["status"] for v in variants], ["blocked"], row["row_id"])
                continue
            self.assertEqual(row["status"], "accepted", row["row_id"])
            self.assertEqual(len(variants), self.planes_per_row, row["row_id"])
            for variant in variants:
                entry = history[variant]
                self.assertEqual(entry["status"], "complete")
                self.assertIn(variant, row["status_reason"])
                record = json.loads((REPO_ROOT / entry["report"]).read_text(encoding="utf-8"))
                self.assertEqual(record["row"]["provider_key"], row["provider_key"])
                binding = record["system"]["runtime_baseline"]
                self.assertEqual(binding["state"], "TRANSITION")
                self.assertEqual(binding["declared_successor"], "agent-memory-runtime-baseline-v4")
                self.assertEqual(record["lane_digest_at_execution"], lane_digest(_as_frozen(lane)))
                self.assertEqual(record["lane_digest_at_execution"], record["execution"]["lane_digest_sha256"])
                # plan-644-lanes-v4 L4: the shadow row stays out of the scorecards
                self.assertEqual(bool(entry.get("normalized_reports")), row["provider_key"] != self.shadow_key and self.planes_per_row == 2, variant)
                for path in entry.get("normalized_reports", []):
                    self.assertTrue((REPO_ROOT / path).is_file(), path)

    def test_differs_from_v3_by_exactly_the_l5_list(self):
        v3, v4 = _flat(_as_frozen(get_lane(self.v3_id))), _flat(_as_frozen(self._lane()))
        changed = {path for path in set(v3) | set(v4) if v3.get(path, "<absent>") != v4.get(path, "<absent>")}
        new_row = {path for path in changed if path.startswith(f"/systems/{self.shadow_key}/")}
        changed -= new_row
        allowed = LANE_LEVEL | {f"/systems/{self.control_key}{suffix}" for suffix in POSTURE | {"/display_name"}} | self.extra_differences
        self.assertEqual(changed, allowed)
        self.assertTrue(new_row)
        # executed -v3 rows are re-frozen here; deferred rows keep their status unless L3 says otherwise
        v3_rows = {row["provider_key"]: row["status"] for row in get_lane(self.v3_id)["systems"]}
        v4_rows = {row["provider_key"]: row["status"] for row in self._lane()["systems"] if row["provider_key"] != self.shadow_key}
        self.assertEqual(set(v3_rows), set(v4_rows))

    def test_control_runs_the_shipped_default_under_the_v4_transition(self):
        control = next(row for row in self._lane()["systems"] if row["role"] == "control")
        configuration = control["configuration"]
        self.assertNotIn("recall_control", configuration)  # absence is read as off (L1)
        self.assertNotIn("semantic_retrieval", configuration)
        self.assertIn("Runtime Baseline v4", control["display_name"])
        self.assertEqual(configuration["runtime_baseline_posture"], {
            "predecessor": "agent-memory-runtime-baseline-v3",
            "declared_successor": "agent-memory-runtime-baseline-v4",
            "declaration": V4_DECLARATION,
            "declaration_blob": _blob(V4_DECLARATION),
            "checker_state_required": ["PASS", "TRANSITION"],
        })

    def test_shadow_row_is_the_control_with_recall_control_shadow(self):
        lane = self._lane()
        control = next(row for row in lane["systems"] if row["role"] == "control")
        row = next(row for row in lane["systems"] if row["provider_key"] == self.shadow_key)
        self.assertEqual((row["row_id"], row["role"], row["system_id"]), (SHADOW_ROW_ID, "comparator", control["system_id"]))
        self.assertIn(row["status"], {"frozen", "accepted"})
        self.assertIn("shadow recall control", row["display_name"])
        self.assertNotEqual(row["display_name"], control["display_name"])
        for key in ("source", "adapter", "inference_posture", "credentials", "capability_posture", "dependency_pins"):
            self.assertEqual(row[key], control[key], key)
        configuration = dict(row["configuration"])
        self.assertEqual(configuration.pop("recall_control"), "shadow")
        self.assertIn("never benchmark authority", configuration.pop("recall_control_telemetry"))
        self.assertEqual(configuration, control["configuration"])
        self.assertIn("not the v4 publication control", row["notes"][0])

    def test_prediction_is_registered_before_any_score(self):
        rationale = " ".join(self._lane()["freeze_rationale"])
        for phrase in ("frontier_exhausted", "no_evidence", "max_candidates never appears", "complete"):
            self.assertIn(phrase, rationale)

    def test_workflow_offers_and_defaults_to_this_lane_and_the_shadow_row(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        self.assertIn(f"- {self.lane_id}", workflow)
        # The default moved to the -v5 lane (plan-671-evidence-v5 E4/E8), then to -v6 (plan-732-evidence-v6
        # V6-E8); this accepted lane stays offered.
        self.assertRegex(workflow, r'default: "' + self.lane_id.rsplit("-v", 1)[0] + r'-v[456]"')
        self.assertIn(f"- {self.shadow_key}", workflow)
        self.assertIn('python-version: "3.12"', workflow)  # the AMB join relies on 3.12's FIFO semaphore


class LongMemEvalParityV4LaneTests(_V4LaneMixin, unittest.TestCase):
    lane_id = "longmemeval-s-retrieval-parity-v4"
    v3_id = "longmemeval-s-retrieval-parity-v3"
    control_key = "agent_memory"
    shadow_key = "agent_memory_shadow"
    planes_per_row = 2
    workflow_path = ".github/workflows/longmemeval-competitive.yml"
    extra_differences = {
        "/harness/source_blobs/reference/run_longmemeval.py",
        "/evaluator/scorer",
        "/systems/agent_memory/adapter/revision_rule",
        "/systems/lexical_overlap/source/revision",
        f"/systems/{SEMANTIC_KEY}/adapter/revision_rule",
        f"/systems/{SEMANTIC_KEY}/status",
        f"/systems/{SEMANTIC_KEY}/status_reason",
        f"/systems/{SEMANTIC_KEY}/display_name",
        *{f"/systems/{SEMANTIC_KEY}{suffix}" for suffix in POSTURE},
        "/budget/forbidden_overrides",
        "/execution/environment/dispatch_unit",
        "/execution/execution_identity_requirements",
    }

    def test_runner_blob_is_pinned_everywhere(self):
        lane = self._lane()
        runner_blob = lane["harness"]["source_blobs"]["reference/run_longmemeval.py"]
        # The lane is accepted: its runner pin is a fact about the runs it bound, compared with the
        # committed evidence records, not HEAD (the -v5 lanes re-pin the runner; plan-671-evidence-v5 E8).
        records = sorted((REPO_ROOT / "reports/benchmarks/longmemeval" / self.lane_id).glob("*/evidence.json"))
        self.assertEqual(len(records), 8)
        for record_path in records:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["execution"]["source_blobs"]["reference/run_longmemeval.py"], runner_blob, record_path.parent.name)
        self.assertIn(runner_blob, lane["evaluator"]["scorer"])
        v3_blob = get_lane(self.v3_id)["harness"]["source_blobs"]["reference/run_longmemeval.py"]
        self.assertNotIn(v3_blob, json.dumps(lane))  # every text naming the runner blob was updated
        self.assertIn(runner_blob, next(row for row in lane["systems"] if row["role"] == "control")["adapter"]["revision_rule"])
        self.assertEqual(next(row for row in lane["systems"] if row["role"] == "baseline")["source"]["revision"], runner_blob)

    def test_semantic_row_is_deferred_with_its_declaration_kept(self):
        lane = self._lane()
        row = next(row for row in lane["systems"] if row["provider_key"] == SEMANTIC_KEY)
        v3_row = next(row for row in get_lane(self.v3_id)["systems"] if row["provider_key"] == SEMANTIC_KEY)
        self.assertEqual(row["status"], "deferred")
        self.assertIn("plan-644-lanes-v4 L3", row["status_reason"])
        self.assertEqual(row["configuration"]["semantic_representation"], v3_row["configuration"]["semantic_representation"])

    def test_workflow_passes_the_rows_recall_control(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        self.assertIn('configuration.get("recall_control", "off")', workflow)
        self.assertIn("--agent-memory-recall-control", workflow)


class AmbPrecisionMemBenchV4LaneTests(_V4LaneMixin, unittest.TestCase):
    lane_id = "amb-precisionmembench-retrieval-v4"
    v3_id = "amb-precisionmembench-retrieval-v3"
    control_key = "agent-memory"
    shadow_key = "agent-memory-shadow"
    planes_per_row = 1
    workflow_path = ".github/workflows/amb-competitive.yml"
    extra_differences = {
        "/harness/source_blobs/reference/amb_agent_memory_bridge.py",
        "/systems/agent-memory/adapter/revision_rule",
        "/execution/execution_identity_requirements",
        "/execution/artifact_requirements",
    }

    def test_bridge_0_3_0_is_pinned_and_the_semantic_row_stays_deferred(self):
        import amb_agent_memory_bridge as bridge

        lane = self._lane()
        control = next(row for row in lane["systems"] if row["role"] == "control")
        blob = lane["harness"]["source_blobs"]["reference/amb_agent_memory_bridge.py"]
        # The lane is accepted (plan-671-evidence-v5 E8, A6): the bridge blob is compared with the
        # committed evidence records, not HEAD, and bridge_version 0.3.0 with the lane's own
        # revision_rule; the live bridge moved to 0.4.0 under the -v5 lane.
        records = sorted((REPO_ROOT / "reports/benchmarks/amb" / self.lane_id).glob("*/evidence.json"))
        self.assertEqual(len(records), 4)
        for record_path in records:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["execution"]["bridge_blobs"]["reference/amb_agent_memory_bridge.py"], blob, record_path.parent.name)
        self.assertIn("bridge_version 0.3.0", control["adapter"]["revision_rule"])
        self.assertIn(blob, control["adapter"]["revision_rule"])
        self.assertEqual(bridge.AMB_SHADOW_PROVIDER_KEY, self.shadow_key)
        row = next(row for row in lane["systems"] if row["provider_key"] == SEMANTIC_KEY)
        v3_row = next(row for row in get_lane(self.v3_id)["systems"] if row["provider_key"] == SEMANTIC_KEY)
        self.assertEqual(row, v3_row)

    def test_workflow_sets_the_sidecar_for_the_shadow_row_only(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        self.assertIn('if [ "${{ inputs.memory }}" = "agent-memory-shadow" ]; then', workflow)
        self.assertIn('AGENT_MEMORY_AMB_RECALL_CONTROL_SIDECAR="$RUNNER_TEMP/amb-output/recall-control.jsonl"', workflow)
        self.assertIn('[ "$memory" = "agent-memory-shadow" ]', workflow)


if __name__ == "__main__":
    unittest.main()
