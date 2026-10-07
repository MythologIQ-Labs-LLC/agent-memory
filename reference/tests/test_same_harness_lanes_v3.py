"""The -v3 same-harness lanes (#669 Step B; docs/plan-669-lanes-v3.md D1-D6, IA1).

Each -v3 lane equals its accepted -v2 lane field for field except exactly the D5 (and IA1)
differences; the LongMemEval lane adds the measured ``agent_memory_semantic`` row (D2) and
the AMB lane carries it deferred (D3). The control runs the shipped default (no semantic
key, read as ``off``) under the declared transition to Runtime Baseline v3.
"""

from __future__ import annotations

import copy
import json
import subprocess
import unittest
from pathlib import Path

from agentmem_ref.evaluation.registry import get_integration
from agentmem_ref.evaluation.same_harness_lane import get_lane, lane_digest, resolve_lane, validate_lane
from agentmem_ref.runtime import representation_onnx

REPO_ROOT = Path(__file__).resolve().parents[2]
V3_DECLARATION = "reports/runtime/baseline-v3-declaration.json"
SEMANTIC_KEY = "agent_memory_semantic"


def _blob(path: str) -> str:
    return subprocess.run(["git", "hash-object", str(REPO_ROOT / path)], capture_output=True, text=True, check=True).stdout.strip()


def _flat(value, path: str = "") -> dict:
    """JSON leaves by path; rows keyed by provider_key; lists of scalars compared whole."""

    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key == "systems" and path == "":
                item = {row["provider_key"]: row for row in item}
            out.update(_flat(item, f"{path}/{key}"))
        return out
    if isinstance(value, list) and any(isinstance(item, (dict, list)) for item in value):
        out = {}
        for index, item in enumerate(value):
            out.update(_flat(item, f"{path}[{index}]"))
        return out
    return {path: value}


def _as_frozen(lane: dict) -> dict:
    """A lane as frozen: accepted rows back to frozen, status_reasons and the acceptance finding dropped."""

    frozen = copy.deepcopy(lane)
    frozen["status"] = "frozen"
    for row in frozen["systems"]:
        if row["status"] in {"executed", "accepted"}:
            row["status"] = "frozen"
            del row["status_reason"]
    frozen["findings"] = [item for item in frozen["findings"] if not item.startswith("accepted rows ")]
    return frozen


LANE_LEVEL = {"/lane_id", "/status", "/frozen_on", "/owning_issue", "/description", "/freeze_rationale",
              "/comparability/notes", "/comparability/not_comparable_to", "/findings"}
POSTURE = {f"/configuration/runtime_baseline_posture/{key}" for key in ("predecessor", "declared_successor", "declaration", "declaration_blob")}


class _V3LaneMixin:
    lane_id: str
    v2_id: str
    control_key: str
    extra_differences: set[str]
    workflow_path: str

    def _lane(self) -> dict:
        return get_lane(self.lane_id)

    def test_lane_is_accepted_without_scores_and_resolves(self):
        lane = validate_lane(self._lane())
        self.assertEqual(lane["status"], "accepted")
        self.assertIs(lane["frozen_before_any_score"], True)
        self.assertEqual(lane["owning_issue"], 669)
        resolve_lane(lane)
        for row in lane["systems"]:
            self.assertIn(row["status"], {"accepted", "deferred"}, row["row_id"])
            self.assertTrue(row["status_reason"], row["row_id"])
        self.assertTrue(lane["findings"][-1].startswith("accepted rows 2026-10-07"))

    def test_accepted_rows_are_bound_to_evidence_executed_under_the_v3_transition(self):
        lane = self._lane()
        integration = get_integration(lane["benchmark_integration"])
        history = {entry["variant"]: entry for entry in integration["evidence_history"]}
        for row in lane["systems"]:
            prefix = f"lane:{self.lane_id}:{row['provider_key']}"
            variants = [variant for variant in history if variant == prefix or variant.startswith(prefix + ":")]
            if row["status"] == "deferred":
                self.assertEqual([history[v]["status"] for v in variants], ["blocked"], row["row_id"])
                continue
            self.assertEqual(len(variants), self.planes_per_row, row["row_id"])
            for variant in variants:
                entry = history[variant]
                self.assertEqual(entry["status"], "complete")
                self.assertIn(variant, row["status_reason"])
                record = json.loads((REPO_ROOT / entry["report"]).read_text(encoding="utf-8"))
                self.assertEqual(record["row"]["provider_key"], row["provider_key"])
                self.assertEqual(record["input"]["sha256"], entry["input_sha256"])
                self.assertEqual(record["system"]["revision"], entry["system_revision"])
                binding = record["system"]["runtime_baseline"]
                self.assertEqual(binding["state"], "TRANSITION")
                self.assertEqual(binding["declared_successor"], "agent-memory-runtime-baseline-v3")
                self.assertIn("declared_successor=agent-memory-runtime-baseline-v3", binding["line"])
                # Acceptance adds only statuses, status_reasons and one findings note; undoing them
                # (no git history: CI checks out at depth 1) must give the digest the run executed.
                self.assertEqual(record["lane_digest_at_execution"], lane_digest(_as_frozen(lane)))
                self.assertEqual(record["lane_digest_at_execution"], record["execution"]["lane_digest_sha256"])
                for path in entry.get("normalized_reports", []):
                    self.assertTrue((REPO_ROOT / path).is_file(), path)

    def test_differs_from_v2_by_exactly_the_d5_list(self):
        v2, v3 = _flat(_as_frozen(get_lane(self.v2_id))), _flat(_as_frozen(self._lane()))
        changed = {path for path in set(v2) | set(v3) if v2.get(path, "<absent>") != v3.get(path, "<absent>")}
        new_row = {path for path in changed if path.startswith(f"/systems/{SEMANTIC_KEY}/")}
        changed -= new_row
        # findings differs only by the dropped acceptance entry (removed by _as_frozen on both sides)
        allowed = (LANE_LEVEL - {"/findings", "/status"}) | {f"/systems/{self.control_key}{suffix}" for suffix in POSTURE | {"/display_name"}} | self.extra_differences
        self.assertEqual(changed, allowed)
        self.assertTrue(new_row)
        # every row of the -v2 lane is here with the same status (accepted, or still deferred)
        v2_rows = {row["provider_key"]: row["status"] for row in get_lane(self.v2_id)["systems"]}
        v3_rows = {row["provider_key"]: row["status"] for row in self._lane()["systems"]}
        self.assertEqual(v2_rows, {key: status for key, status in v3_rows.items() if key != SEMANTIC_KEY})

    def test_control_runs_the_shipped_default_under_the_v3_transition(self):
        control = next(row for row in self._lane()["systems"] if row["role"] == "control")
        configuration = control["configuration"]
        self.assertNotIn("semantic_retrieval", configuration)  # absence is read as off (D1)
        self.assertNotIn("semantic_representation", configuration)
        self.assertIn("Runtime Baseline v3", control["display_name"])
        posture = configuration["runtime_baseline_posture"]
        self.assertEqual(posture, {
            "predecessor": "agent-memory-runtime-baseline-v2",
            "declared_successor": "agent-memory-runtime-baseline-v3",
            "declaration": V3_DECLARATION,
            "declaration_blob": _blob(V3_DECLARATION),
            "checker_state_required": ["PASS", "TRANSITION"],
        })
        # The register declares v3 as the open successor until Step B1 publishes it; after that the
        # published v3 record names the same declaration as its predecessor block (docs/67).
        register = json.loads((REPO_ROOT / "reports/runtime/baseline-register.json").read_text(encoding="utf-8"))
        declared = register["declared_successor"]
        if declared is not None and declared["baseline_id"] == "agent-memory-runtime-baseline-v3":
            self.assertEqual(declared["declaration"], V3_DECLARATION)
        else:
            entry = next(item for item in register["baselines"] if item["baseline_id"] == "agent-memory-runtime-baseline-v3")
            record = json.loads((REPO_ROOT / entry["record"]).read_text(encoding="utf-8"))
            self.assertEqual(record["predecessor"]["declaration"], V3_DECLARATION)
            self.assertEqual(record["predecessor"]["declaration_blob"], posture["declaration_blob"])

    def test_reference_blobs_are_the_ones_the_accepted_runs_executed(self):
        lane = self._lane()
        integration = get_integration(lane["benchmark_integration"])
        reports = [entry["report"] for entry in integration["evidence_history"]
                   if entry["variant"].startswith(f"lane:{self.lane_id}:") and entry["status"] == "complete"]
        self.assertTrue(reports)
        expected = {path: blob for path, blob in lane["harness"]["source_blobs"].items() if path.startswith("reference/")}
        for report in reports:
            execution = json.loads((REPO_ROOT / report).read_text(encoding="utf-8"))["execution"]
            self.assertEqual(execution.get("source_blobs") or execution.get("bridge_blobs"), expected, report)

    def test_workflow_offers_and_defaults_to_this_lane(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        self.assertIn(f"- {self.lane_id}", workflow)
        self.assertIn(f'default: "{self.lane_id}"', workflow)
        self.assertIn('lane["status"] == "frozen"', workflow)  # an accepted lane is refused


class LongMemEvalParityV3LaneTests(_V3LaneMixin, unittest.TestCase):
    lane_id = "longmemeval-s-retrieval-parity-v3"
    v2_id = "longmemeval-s-retrieval-parity-v2"
    control_key = "agent_memory"
    planes_per_row = 2
    workflow_path = ".github/workflows/longmemeval-competitive.yml"
    extra_differences = {
        "/harness/source_blobs/reference/run_longmemeval.py",
        "/evaluator/scorer",
        "/systems/agent_memory/adapter/revision_rule",
        "/systems/lexical_overlap/source/revision",
        "/budget/forbidden_overrides",
        "/execution/environment/dispatch_unit",
        "/execution/environment/semantic_row_install",
        "/execution/execution_identity_requirements",
        "/execution/timeout",  # IA1: 240 minutes
    }

    def test_runner_blob_is_pinned_everywhere(self):
        lane = self._lane()
        runner_blob = lane["harness"]["source_blobs"]["reference/run_longmemeval.py"]
        control = next(row for row in lane["systems"] if row["role"] == "control")
        self.assertIn(runner_blob, lane["evaluator"]["scorer"])
        self.assertIn(runner_blob, control["adapter"]["revision_rule"])
        self.assertEqual(next(row for row in lane["systems"] if row["role"] == "baseline")["source"]["revision"], runner_blob)
        self.assertEqual(control["configuration"]["budget"], "50")
        self.assertIn("240 min", lane["execution"]["timeout"])

    def test_semantic_row_is_a_measured_comparator_pinned_to_the_representation(self):
        lane = self._lane()
        control = next(row for row in lane["systems"] if row["role"] == "control")
        row = next(row for row in lane["systems"] if row["provider_key"] == SEMANTIC_KEY)
        self.assertEqual((row["role"], row["status"], row["row_id"]), ("comparator", "accepted", "agent-memory-semantic-route"))
        self.assertEqual(row["system_id"], control["system_id"])
        for key in ("source", "adapter", "inference_posture", "credentials", "capability_posture"):
            self.assertEqual(row[key], control[key], key)
        self.assertEqual(row["dependency_pins"], [*control["dependency_pins"], "reference/requirements-semantic.txt"])
        configuration = dict(row["configuration"])
        pin = configuration.pop("semantic_representation")
        self.assertEqual(configuration.pop("semantic_retrieval"), "required")
        self.assertIn("route_diagnostics", configuration)
        configuration.pop("route_diagnostics")
        self.assertEqual(configuration, control["configuration"])
        self.assertEqual(pin, {
            "representation_ref": representation_onnx.REPRESENTATION_REF,
            "representation_version": representation_onnx.REPRESENTATION_VERSION,
            "config_digest": representation_onnx.config_digest({"onnxruntime": "1.30.0", "tokenizers": "0.23.2", "numpy": "2.4.6"}),
            "dimensions": representation_onnx.DIMENSIONS,
            "minimum_similarity": 0.3,
            "candidate_limit": 16,
        })
        self.assertIn("not the v3 publication control", row["notes"][0])

    def test_semantic_pin_binds_the_constraint_file_versions(self):
        pins = dict(line.split("==") for line in (REPO_ROOT / "reference/requirements-semantic.txt").read_text().splitlines()
                    if line and not line.startswith("#"))
        self.assertEqual({key: pins[key] for key in ("onnxruntime", "tokenizers", "numpy")},
                         {"onnxruntime": "1.30.0", "tokenizers": "0.23.2", "numpy": "2.4.6"})

    def test_workflow_runs_the_semantic_row_from_the_lane_only(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        self.assertIn(f"- {SEMANTIC_KEY}", workflow)
        self.assertIn("timeout-minutes: 240", workflow)
        self.assertIn("-c reference/requirements-semantic.txt", workflow)
        self.assertIn("representation_onnx fetch", workflow)
        self.assertIn('configuration.get("semantic_retrieval", "off")', workflow)
        self.assertIn('"runner_backend":', workflow)
        self.assertIn("has no {backend} row", workflow)


class AmbPrecisionMemBenchV3LaneTests(_V3LaneMixin, unittest.TestCase):
    lane_id = "amb-precisionmembench-retrieval-v3"
    v2_id = "amb-precisionmembench-retrieval-v2"
    control_key = "agent-memory"
    planes_per_row = 1
    workflow_path = ".github/workflows/amb-competitive.yml"
    extra_differences = {"/execution/execution_identity_requirements"}  # IA1: names the deferred row

    def test_semantic_row_is_deferred_for_the_lock_conflict_and_the_bridge_is_unchanged(self):
        lane = self._lane()
        row = next(row for row in lane["systems"] if row["provider_key"] == SEMANTIC_KEY)
        self.assertEqual((row["role"], row["status"]), ("comparator", "deferred"))
        self.assertIn("uv.lock", row["status_reason"])
        self.assertEqual((row["configuration"], row["capability_posture"]), ({}, {}))
        self.assertTrue(any("deferred" in item and "uv.lock" in item for item in lane["freeze_rationale"]))
        v2 = get_lane(self.v2_id)
        self.assertEqual(lane["harness"]["source_blobs"], v2["harness"]["source_blobs"])


if __name__ == "__main__":
    unittest.main()
