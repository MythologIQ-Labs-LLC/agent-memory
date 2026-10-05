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
    def test_committed_lane_is_accepted_without_scores_and_resolves_to_an_external_integration(self):
        lanes = list_lanes()
        self.assertEqual(len(lanes), len(lane_paths()))
        lane = _lane()
        self.assertEqual(lane["status"], "accepted")
        self.assertIs(lane["frozen_before_any_score"], True)
        self.assertEqual(lane["authority_effect"], "none")
        self.assertIs(lane["evaluator"]["llm_calls"], False)
        self.assertIsNone(lane["evaluator"]["answer_model"])
        self.assertEqual(_score_keys(lane), [], "a lane must carry no score-bearing keys, accepted or not")
        resolved = resolve_lane(lane)
        self.assertEqual(resolved["provenance_class"], "external_independent")
        self.assertEqual(resolved["harness_revision"], lane["harness"]["revision"])
        self.assertEqual(resolved["lane_digest_sha256"], lane_digest(lane))
        rows = {row["row_id"]: row for row in resolved["rows"]}
        self.assertEqual(rows["agent-memory-public-facade"]["status"], "accepted")
        self.assertEqual(rows["bm25-harness-baseline"]["status"], "accepted")
        self.assertEqual(rows["mem0-oss-2.2.1-explicit-memory"]["status"], "accepted")
        self.assertEqual(rows["hindsight-0.10.2"]["status"], "deferred")
        integration = get_integration(lane["benchmark_integration"])
        self.assertEqual(integration["input_contract"]["known_input_sha256"], lane["dataset"]["input_sha256"])
        entries = {item["variant"]: item for item in integration["evidence_history"]}
        for key in ("agent-memory", "bm25", "mem0-explicit"):
            entry = entries[f"lane:{LANE_ID}:{key}"]
            self.assertEqual(entry["status"], "complete")
            self.assertEqual(entry["input_sha256"], lane["dataset"]["input_sha256"])
            self.assertEqual(entry["report_binding"], {"input_sha256_path": "input.sha256", "system_revision_path": "system.revision"})
            row = next(item for item in lane["systems"] if item["provider_key"] == key)
            self.assertEqual(entry["system_id"], row["system_id"])
            self.assertEqual(row["status"], "accepted")
            self.assertIn(entry["report"].rsplit("/", 2)[-2], row["status_reason"])
        self.assertEqual(entries[f"lane:{LANE_ID}:hindsight"]["status"], "blocked")

    def test_accepted_rows_are_bound_to_committed_evidence_records(self):
        from agentmem_ref.evaluation.registry import check_evidence_binding

        lane = _lane()
        integration = get_integration(lane["benchmark_integration"])
        repo_root = Path(__file__).resolve().parents[2]
        bindings = check_evidence_binding(integration, repo_root=repo_root)
        self.assertEqual(len(bindings), 3)
        for binding in bindings:
            self.assertTrue(binding["bound"], binding)
            record = json.loads((repo_root / binding["report"]).read_text(encoding="utf-8"))
            self.assertEqual(record["lane_id"], LANE_ID)
            self.assertEqual(record["authority_effect"], "none")
            self.assertEqual(record["execution"]["amb_revision"], lane["harness"]["revision"])
            self.assertIs(record["execution"]["full_selection"], True)
            self.assertIsNone(record["execution"]["amb_pmb_return_cap"])
            self.assertEqual(record["execution"]["harness_constraints"]["uv_lock_git_blob"], lane["execution"]["environment"]["harness_lock"]["git_blob"])
            self.assertEqual(record["native_summary"]["total_queries"], lane["dataset"]["query_count"])
            self.assertEqual(record["native_summary"]["active_total"], 43)
            directory = (repo_root / binding["report"]).parent
            for name in ("single-turn.json", "execution-identity.json", "sha256.txt"):
                self.assertTrue((directory / name).is_file(), name)
            raw = json.loads((directory / "single-turn.json").read_text(encoding="utf-8"))
            self.assertEqual(raw["correct"], record["native_summary"]["total_passes"])
            self.assertEqual(raw["mode"], "retrieval")
            self.assertIsNone(raw["answer_llm"])
            if record["row"]["provider_key"] == "mem0-explicit":
                self.assertEqual(record["execution"]["resolved_packages"]["mem0ai"], "2.2.1")
                self.assertIs(record["execution"]["mem0_optional_components"]["fastembed_installed"], False)

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
        lane["status"] = "frozen"
        with self.assertRaisesRegex(SameHarnessLaneError, "frozen lane may not carry an accepted row"):
            validate_lane(lane)
        lane = _lane()
        lane["systems"][2]["status_reason"] = None
        with self.assertRaisesRegex(SameHarnessLaneError, "accepted row .* requires a status_reason"):
            validate_lane(lane)
        lane = _lane()
        for row in lane["systems"]:
            if row["status"] == "accepted":
                row["status"] = "executed"
        with self.assertRaisesRegex(SameHarnessLaneError, "accepted lane must carry at least one accepted row"):
            validate_lane(lane)
        lane = _lane()
        lane["status"] = "executed"
        with self.assertRaisesRegex(SameHarnessLaneError, "accepted row requires an accepted lane"):
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
        del lane["systems"][2]["inference_posture"]
        with self.assertRaisesRegex(SameHarnessLaneError, "must declare inference_posture"):
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
        self.assertEqual(report["lanes"][0]["status"], "accepted")

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
            tampered["budget"]["default_k"] = 50
            bad.write_text(json.dumps(tampered), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["benchmark", "validate-lane", str(bad), "--json"])
            # A changed frozen fact keeps a valid shape; prove the digest moved so the
            # committed records (which carry the executing digest) no longer match it.
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
        self.assertEqual(integration["normalization"]["normalizer"], "agentmem_ref.evaluation.normalize:normalize_amb_precisionmembench")
        mapped = {mapping["dimension"] for mapping in integration["normalization"]["mappings"]}
        self.assertEqual(mapped, {"retrieval", "efficiency", "reproducibility"})
        self.assertEqual(set(integration["normalization"]["unmapped_dimensions"]), {"currentness", "reasoning", "governance", "evaluator_integrity"})


if __name__ == "__main__":
    unittest.main()
