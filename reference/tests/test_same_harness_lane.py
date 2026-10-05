"""Same-harness lane freeze contract tests (#640)."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref.console import main
from agentmem_ref.evaluation.registry import get_integration, list_integrations
from agentmem_ref.evaluation.same_harness_lane import (
    SameHarnessLaneError,
    contract_version_compatible,
    get_lane,
    lane_digest,
    lane_paths,
    list_lanes,
    load_lane,
    resolve_lane,
    validate_lane,
)

LANE_ID = "amb-precisionmembench-retrieval-v1"


def _lane() -> dict:
    return get_lane(LANE_ID)


_SCORE_KEYS = {"results", "accuracy", "score", "scores", "correct", "active_passes", "mean_precision", "mean_recall"}


def _score_keys(value, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _SCORE_KEYS:
                found.append(f"{path}.{key}")
            found.extend(_score_keys(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_score_keys(item, f"{path}[{index}]"))
    return found


class SameHarnessLaneTests(unittest.TestCase):
    def test_committed_lane_is_frozen_without_scores_and_resolves_to_an_external_integration(self):
        lanes = list_lanes()
        self.assertEqual(len(lanes), len(lane_paths()))
        lane = _lane()
        self.assertEqual(lane["status"], "frozen")
        self.assertIs(lane["frozen_before_any_score"], True)
        self.assertEqual(lane["authority_effect"], "none")
        self.assertIs(lane["evaluator"]["llm_calls"], False)
        self.assertIsNone(lane["evaluator"]["answer_model"])
        self.assertEqual(_score_keys(lane), [], "a frozen lane must carry no score-bearing keys")
        resolved = resolve_lane(lane)
        self.assertEqual(resolved["provenance_class"], "external_independent")
        self.assertEqual(resolved["harness_revision"], lane["harness"]["revision"])
        self.assertEqual(resolved["lane_digest_sha256"], lane_digest(lane))
        rows = {row["row_id"]: row for row in resolved["rows"]}
        self.assertEqual(rows["mem0-oss-2.2.1-explicit-memory"]["status"], "frozen")
        self.assertEqual(rows["hindsight-0.10.2"]["status"], "deferred")
        integration = get_integration(lane["benchmark_integration"])
        self.assertEqual(integration["input_contract"]["known_input_sha256"], lane["dataset"]["input_sha256"])
        statuses = {item["variant"]: item["status"] for item in integration["evidence_history"]}
        self.assertEqual(statuses[f"lane:{LANE_ID}:mem0-explicit"], "not_run")
        self.assertEqual(statuses[f"lane:{LANE_ID}:hindsight"], "blocked")

    def test_lane_binds_the_bridge_constants_it_freezes(self):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        try:
            import amb_agent_memory_bridge as agent_bridge
            import amb_mem0_explicit_bridge as mem0_bridge
        finally:
            sys.path.pop(0)
        lane = _lane()
        self.assertEqual(lane["harness"]["revision"], agent_bridge.AMB_REVISION)
        self.assertEqual(lane["harness"]["revision"], mem0_bridge.AMB_REVISION)
        mem0_row = next(row for row in lane["systems"] if row["provider_key"] == mem0_bridge.AMB_PROVIDER_KEY)
        self.assertEqual(mem0_row["source"]["revision"], mem0_bridge.MEM0_TAG_COMMIT)
        self.assertIn(f"mem0ai=={mem0_bridge.MEM0_VERSION}", mem0_row["dependency_pins"])
        frozen = mem0_bridge.frozen_configuration()
        self.assertEqual(mem0_row["configuration"]["embedder"]["revision"], frozen["embedder"]["revision"])
        self.assertEqual(mem0_row["configuration"]["embedder"]["model"], frozen["embedder"]["model"])
        self.assertEqual(mem0_row["configuration"]["vector_store"]["collection"], frozen["vector_store"]["collection"])
        self.assertEqual(mem0_row["inference_posture"], "explicit_memory_no_inference")
        self.assertEqual(lane["execution"]["concurrency"], frozen["concurrency"])

    def test_malformed_and_contradictory_lanes_refuse(self):
        with self.assertRaises(SameHarnessLaneError):
            validate_lane({})
        lane = _lane()
        lane["dataset"]["input_sha256"] = "0" * 64
        with self.assertRaisesRegex(SameHarnessLaneError, "placeholder"):
            validate_lane(lane)
        lane = _lane()
        lane["systems"][2]["status"] = "accepted"
        with self.assertRaisesRegex(SameHarnessLaneError, "frozen lane may not carry an accepted row"):
            validate_lane(lane)
        lane = _lane()
        lane["evaluator"]["answer_model"] = "gemini:gemini-2.5-flash-lite"
        with self.assertRaisesRegex(SameHarnessLaneError, "may not name an answer or judge model"):
            validate_lane(lane)
        lane = _lane()
        lane["systems"][2]["inference_posture"] = "reflective_llm_extraction"
        with self.assertRaisesRegex(SameHarnessLaneError, "requires credentials"):
            validate_lane(lane)
        lane = _lane()
        lane["systems"][2]["dependency_pins"] = []
        with self.assertRaisesRegex(SameHarnessLaneError, "exact dependency_pins"):
            validate_lane(lane)
        lane = _lane()
        lane["systems"] = [row for row in lane["systems"] if row["role"] != "comparator"]
        with self.assertRaisesRegex(SameHarnessLaneError, "at least one comparator"):
            validate_lane(lane)
        lane = _lane()
        lane["systems"][3]["status_reason"] = None
        with self.assertRaisesRegex(SameHarnessLaneError, "requires a status_reason"):
            validate_lane(lane)
        lane = _lane()
        lane["contract_version"] = "2.0.0"
        with self.assertRaisesRegex(SameHarnessLaneError, "unsupported same-harness lane contract version"):
            validate_lane(lane)
        self.assertTrue(contract_version_compatible("1.0.3"))
        self.assertFalse(contract_version_compatible("1.1.0"))

    def test_lane_cannot_claim_a_harness_or_input_its_integration_does_not_describe(self):
        lane = _lane()
        lane["harness"]["revision"] = "f" * 39 + "0"
        with self.assertRaisesRegex(SameHarnessLaneError, "differs from the integration's source_revision"):
            resolve_lane(lane)
        lane = _lane()
        lane["dataset"]["input_sha256"] = "1" * 63 + "2"
        with self.assertRaisesRegex(SameHarnessLaneError, "differs from the integration's known_input_sha256"):
            resolve_lane(lane)
        lane = _lane()
        lane["benchmark_integration"] = "golden-keyed-retrieval-v1"
        with self.assertRaisesRegex(SameHarnessLaneError, "not an external harness"):
            resolve_lane(lane)
        lane = _lane()
        lane["benchmark_integration"] = "no-such-integration"
        with self.assertRaisesRegex(SameHarnessLaneError, "unknown benchmark integration"):
            resolve_lane(lane)

    def test_lane_digest_is_stable_and_changes_with_any_frozen_fact(self):
        lane = _lane()
        digest = lane_digest(lane)
        self.assertEqual(digest, lane_digest(copy.deepcopy(lane)))
        changed = copy.deepcopy(lane)
        changed["budget"]["default_k"] = 50
        self.assertNotEqual(digest, lane_digest(changed))

    def test_cli_lists_and_validates_lanes_without_execution(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["benchmark", "lanes", "--json"])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["command"], "benchmark_lanes")
        self.assertEqual(report["authority_effect"], "none")
        self.assertEqual([lane["lane_id"] for lane in report["lanes"]], [LANE_ID])
        self.assertEqual(report["lanes"][0]["status"], "frozen")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["benchmark", "validate-lane", str(lane_paths()[0]), "--json"])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report["valid"])
        self.assertFalse(report["executed"])
        self.assertEqual(report["resolution"]["provenance_class"], "external_independent")
        self.assertEqual(report["lane_digest_sha256"], lane_digest(_lane()))

        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "lane.json"
            tampered = _lane()
            tampered["status"] = "accepted"
            bad.write_text(json.dumps(tampered), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["benchmark", "validate-lane", str(bad), "--json"])
            # An accepted lane whose rows are still frozen contradicts itself only through
            # its integration evidence; the validator accepts the shape, so prove the
            # digest moved and the resolution still reports the declared status.
            self.assertEqual(code, 0)
            self.assertNotEqual(json.loads(output.getvalue())["lane_digest_sha256"], lane_digest(_lane()))
            bad.write_text("{}", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["benchmark", "validate-lane", str(bad), "--json"])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output.getvalue())["status"], "refused")

    def test_lane_integration_is_registered_with_external_provenance_and_no_gauntlet_binding(self):
        integration = next(item for item in list_integrations() if item["integration_id"] == LANE_ID)
        self.assertEqual(integration["benchmark"]["provenance_class"], "external_independent")
        self.assertEqual(integration["gauntlet"]["relationship"], "not_applicable")
        self.assertEqual(integration["provider_requirements"]["credentials"], "credential_free")
        self.assertIsNone(integration["normalization"]["normalizer"])
        self.assertEqual(integration["normalization"]["mappings"], [])


if __name__ == "__main__":
    unittest.main()
