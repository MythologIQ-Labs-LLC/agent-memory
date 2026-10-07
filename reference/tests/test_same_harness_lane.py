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
LME_LANE_ID = "longmemeval-s-retrieval-parity-v1"
AMB_V2_LANE_ID = "amb-precisionmembench-retrieval-v2"
LME_V2_LANE_ID = "longmemeval-s-retrieval-parity-v2"
V2_DECLARATION = "reports/runtime/baseline-v2-declaration.json"


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
        bindings = [item for item in check_evidence_binding(integration, repo_root=repo_root) if item["variant"].startswith(f"lane:{LANE_ID}:")]
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
        # lanes list in sorted id order: the accepted v1 and -v2 lanes and the two frozen -v3 lanes (#669)
        self.assertEqual(
            [lane["lane_id"] for lane in report["lanes"]],
            [LANE_ID, AMB_V2_LANE_ID, "amb-precisionmembench-retrieval-v3", LME_LANE_ID, LME_V2_LANE_ID, "longmemeval-s-retrieval-parity-v3"],
        )
        self.assertEqual([lane["status"] for lane in report["lanes"]], ["accepted", "accepted", "frozen", "accepted", "accepted", "frozen"])

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


class LongMemEvalParityLaneTests(unittest.TestCase):
    """Lane v2: frozen LongMemEval_S retrieval parity (#640), no score, bound to its evaluator and adapter blobs."""

    def _lane(self) -> dict:
        return get_lane(LME_LANE_ID)

    def test_lane_is_accepted_without_scores_and_resolves_to_the_longmemeval_integration(self):
        lane = self._lane()
        self.assertEqual(lane["status"], "accepted")
        self.assertIs(lane["frozen_before_any_score"], True)
        self.assertEqual(lane["authority_effect"], "none")
        self.assertIs(lane["evaluator"]["llm_calls"], False)
        self.assertEqual(_score_keys(lane), [])
        resolved = resolve_lane(lane)
        self.assertEqual(resolved["integration_id"], "agent-memory-longmemeval-retrieval-currentness-v1")
        self.assertEqual(resolved["provenance_class"], "external_adapted")
        self.assertEqual(resolved["harness_revision"], "9e0b455f4ef0e2ab8f2e582289761153549043fc")
        rows = {row["row_id"]: row for row in resolved["rows"]}
        self.assertEqual({key: row["status"] for key, row in rows.items()}, {
            "agent-memory-public-facade": "accepted",
            "lexical-overlap-profile-baseline": "accepted",
            "mem0-oss-2.2.1-explicit-memory": "accepted",
            "hindsight-0.10.2": "deferred",
        })
        self.assertEqual({row["role"] for row in lane["systems"]}, {"control", "baseline", "comparator"})
        self.assertEqual(sum(lane["dataset"]["query_partition"].values()), lane["dataset"]["query_count"])
        integration = get_integration(lane["benchmark_integration"])
        self.assertEqual(integration["input_contract"]["known_dataset_revision"].split("@")[1], "98d7416c24c778c2fee6e6f3006e7a073259d48f")
        (fixture,) = lane["dataset"]["fixtures"]
        self.assertIn("98d7416c24c778c2fee6e6f3006e7a073259d48f", fixture["url"])
        self.assertEqual(fixture["sha256"], lane["dataset"]["input_sha256"])
        accepted = next(item for item in integration["evidence_history"] if item["variant"] == "longmemeval_s_cleaned")
        self.assertEqual(accepted["input_sha256"], lane["dataset"]["input_sha256"], "the lane freezes the input the accepted Agent Memory evidence used")
        entries = {item["variant"]: item for item in integration["evidence_history"]}
        for key in ("agent_memory", "lexical_overlap", "mem0_explicit"):
            row = next(item for item in lane["systems"] if item["provider_key"] == key)
            self.assertEqual(row["status"], "accepted")
            for plane in ("session", "turn"):
                entry = entries[f"lane:{LME_LANE_ID}:{key}:{plane}"]
                self.assertEqual(entry["status"], "complete")
                self.assertEqual(entry["input_sha256"], lane["dataset"]["input_sha256"])
                self.assertEqual(entry["system_id"], row["system_id"])
                self.assertEqual(entry["report_binding"], {"input_sha256_path": "input.sha256", "system_revision_path": "system.revision"})
                self.assertIn(entry["report"].rsplit("/", 2)[-2], row["status_reason"])
                self.assertIn(f"{key}-{plane}-", entry["report"])
        self.assertEqual(entries[f"lane:{LME_LANE_ID}:hindsight"]["status"], "blocked")
        self.assertEqual(integration["gauntlet"]["relationship"], "eligible")

    def test_accepted_rows_are_bound_to_committed_evidence_records(self):
        import gzip

        from agentmem_ref.evaluation.registry import check_evidence_binding

        lane = self._lane()
        integration = get_integration(lane["benchmark_integration"])
        repo_root = Path(__file__).resolve().parents[2]
        bindings = [item for item in check_evidence_binding(integration, repo_root=repo_root) if item["variant"].startswith(f"lane:{LME_LANE_ID}:")]
        self.assertEqual(len(bindings), 6)
        runner_blob = lane["harness"]["source_blobs"]["reference/run_longmemeval.py"]
        frozen_selection = [token for token in lane["selection"]["selection_method"].split() if len(token) == 64][0]
        for binding in bindings:
            self.assertTrue(binding["bound"], binding)
            directory = (repo_root / binding["report"]).parent
            record = json.loads((repo_root / binding["report"]).read_text(encoding="utf-8"))
            self.assertEqual(record["lane_id"], LME_LANE_ID)
            self.assertEqual(record["authority_effect"], "none")
            self.assertEqual(record["lane_digest_at_execution"], record["execution"]["lane_digest_sha256"])
            self.assertIs(record["execution"]["full_selection"], True)
            self.assertEqual(record["execution"]["source_blobs"]["reference/run_longmemeval.py"], runner_blob)
            self.assertEqual(record["input"]["question_ids_sha256"], frozen_selection)
            self.assertEqual(record["native_summary"]["evaluated_question_count"], 419)
            self.assertEqual(record["native_summary"]["failures"]["runtime_failure_count"], 0)
            report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
            plane, backend = record["row"]["plane"], record["row"]["backend"]
            self.assertEqual(report["input"]["sha256"], lane["dataset"]["input_sha256"])
            self.assertEqual(report["input"]["corpus_class"], "external_frozen")
            self.assertEqual(report["execution"]["backends"], [backend])
            self.assertEqual(report["execution"]["agent_memory_configuration"], {"temporal_metadata": "none", "ranking_variant": "default"})
            self.assertNotIn("rows", report["planes"][plane]["backends"][backend])
            rows = json.loads(gzip.open(directory / "report.rows.json.gz", "rt", encoding="utf-8").read())
            self.assertEqual(len(rows[plane][backend]), lane["dataset"]["query_count"])
            for name in ("execution-identity.json", "lane-validation.json", "sha256.txt"):
                self.assertTrue((directory / name).is_file(), name)
            if backend == "mem0_explicit":
                external = report["execution"]["external_backends"]["mem0_explicit"]
                self.assertEqual(external["system_revision"], record["system"]["revision"])
                self.assertEqual(external["install_posture"], {"mem0ai": "2.2.1", "fastembed_installed": False, "spacy_installed": False})
                self.assertEqual(record["execution"]["resolved_packages"]["torch"], "2.10.0")

    def test_lane_binds_the_runner_and_bridge_blobs_it_freezes(self):
        import subprocess
        import sys

        lane = self._lane()
        repo_root = Path(__file__).resolve().parents[2]
        blobs = lane["harness"]["source_blobs"]
        bound = {path: blob for path, blob in blobs.items() if path.startswith("reference/")}
        self.assertEqual(set(bound), {
            "reference/run_longmemeval.py",
            "reference/longmemeval_mem0_explicit_bridge.py",
            "reference/amb_mem0_explicit_bridge.py",
        })
        # The lane is accepted: its pins are a fact about the runs it bound, so they are
        # compared with the committed evidence records, not with HEAD (a later lane
        # generation re-pins the runner under its own id).
        evidence_root = repo_root / "reports" / "benchmarks" / "longmemeval" / LME_LANE_ID
        records = sorted(evidence_root.glob("*/evidence.json"))
        self.assertEqual(len(records), 6)
        for record_path in records:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["execution"]["source_blobs"], bound, record_path.name)
        for path in ("src/retrieval/run_retrieval.py", "src/retrieval/eval_utils.py", "LICENSE"):
            self.assertRegex(blobs[path], r"^[0-9a-f]{40}$")
        self.assertIn(blobs["reference/run_longmemeval.py"], lane["evaluator"]["scorer"])

        sys.path.insert(0, str(repo_root / "reference"))
        try:
            import longmemeval_mem0_explicit_bridge as bridge
        finally:
            sys.path.pop(0)
        row = next(item for item in lane["systems"] if item["provider_key"] == bridge.BACKEND_NAME)
        self.assertEqual(row["system_id"], bridge.SYSTEM_ID)
        self.assertEqual(row["source"]["revision"], bridge.MEM0_TAG_COMMIT)
        self.assertEqual(row["dependency_pins"], list(bridge.DEPENDENCY_PINS))
        self.assertEqual(row["adapter"]["module"], bridge.ADAPTER_ID)
        self.assertEqual(row["adapter"]["install_entry"], f"longmemeval_mem0_explicit_bridge:{bridge.install_longmemeval_mem0_explicit_backend.__name__}")
        frozen = bridge.frozen_configuration()
        self.assertEqual(row["configuration"]["embedder"], frozen["embedder"])
        self.assertEqual(row["configuration"]["vector_store"]["collection"], frozen["vector_store"]["collection"])
        self.assertEqual(row["configuration"]["optional_components"], frozen["optional_components"])
        self.assertIn(f"top_k={bridge.SEARCH_TOP_K}", row["configuration"]["search"])
        self.assertEqual(lane["budget"]["default_k"], bridge.SEARCH_TOP_K)
        self.assertEqual(row["inference_posture"], "explicit_memory_no_inference")
        self.assertEqual(lane["execution"]["concurrency"], frozen["concurrency"])
        self.assertEqual(lane["lane_id"], bridge.LANE_ID)
        control = next(item for item in lane["systems"] if item["role"] == "control")
        self.assertEqual(control["configuration"]["temporal_metadata"], "none")
        self.assertEqual(control["configuration"]["ranking_variant"], "default")

    def test_lane_workflow_executes_only_frozen_rows_of_this_lane(self):
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "longmemeval-competitive.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch", workflow)
        self.assertNotIn("pull_request", workflow.split("permissions:")[0])
        self.assertIn("lanes/${{ inputs.lane_id }}.json", workflow)
        self.assertIn(f"- {LME_LANE_ID}", workflow)
        self.assertIn("validate-lane", workflow)
        self.assertIn('lane["status"] == "frozen"', workflow)  # the workflow executes frozen lanes only; accepted rows are re-run under a new lane id
        self.assertIn('["git", "hash-object", path]', workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("timeout-minutes:", workflow)
        self.assertIn("mem0ai==2.2.1 qdrant-client==1.17.0 sentence-transformers==5.2.3 torch==2.10.0", workflow)
        self.assertIn("longmemeval_mem0_explicit_bridge:install_longmemeval_mem0_explicit_backend", workflow)
        lane = self._lane()
        self.assertEqual(lane["execution"]["environment"]["workflow"], ".github/workflows/longmemeval-competitive.yml")

    def test_lane_contradictions_refuse(self):
        lane = self._lane()
        lane["status"] = "frozen"
        with self.assertRaisesRegex(SameHarnessLaneError, "frozen lane may not carry an accepted row"):
            validate_lane(lane)
        lane = self._lane()
        lane["systems"][2]["dependency_pins"] = []
        with self.assertRaisesRegex(SameHarnessLaneError, "exact dependency_pins"):
            validate_lane(lane)
        lane = self._lane()
        lane["harness"]["revision"] = "f" * 40
        with self.assertRaisesRegex(SameHarnessLaneError, "differs from the integration's source_revision"):
            resolve_lane(lane)


if __name__ == "__main__":
    unittest.main()


def _hash_object(repo_root: Path, path: str) -> str:
    import subprocess

    return subprocess.run(["git", "hash-object", str(repo_root / path)], capture_output=True, text=True, check=True).stdout.strip()


def _frozen_view(lane: dict) -> dict:
    """The accepted lane as it was frozen: statuses back to frozen, status_reasons and the acceptance note removed."""

    frozen = copy.deepcopy(lane)
    frozen["status"] = "frozen"
    for row in frozen["systems"]:
        if row["status"] == "accepted":
            row["status"] = "frozen"
            del row["status_reason"]
    assert frozen["findings"][-1].startswith("accepted rows "), frozen["findings"][-1]
    frozen["findings"] = frozen["findings"][:-1]
    return frozen


class _AcceptedV2LaneMixin:
    """What an accepted -v2 lane binds: the budgeted control under the declared transition, every row's evidence record, the pins those records carry."""

    lane_id = ""
    predecessor_id = ""
    workflow_path = ""
    pinned_reference_paths: set[str] = set()
    planes: tuple[str, ...] = ()
    evidence_blob_key = ""

    def _lane(self) -> dict:
        return get_lane(self.lane_id)

    def _records(self) -> list[dict]:
        from agentmem_ref.evaluation.registry import check_evidence_binding

        lane = self._lane()
        integration = get_integration(lane["benchmark_integration"])
        repo_root = Path(__file__).resolve().parents[2]
        bindings = [item for item in check_evidence_binding(integration, repo_root=repo_root) if item["variant"].startswith(f"lane:{self.lane_id}:")]
        self.assertEqual(len(bindings), 3 * max(1, len(self.planes)))
        records = []
        for binding in bindings:
            self.assertTrue(binding["bound"], binding)
            record = json.loads((repo_root / binding["report"]).read_text(encoding="utf-8"))
            self.assertEqual(record["lane_id"], self.lane_id)
            self.assertEqual(record["authority_effect"], "none")
            # The digest the run executed is the frozen lane's. Acceptance adds exactly the
            # statuses, the status_reasons and one findings note on top, so undoing those
            # (no git history needed: CI checks out at depth 1) must give the executed digest.
            self.assertEqual(record["lane_digest_at_execution"], lane_digest(_frozen_view(lane)))
            self.assertEqual(record["lane_digest_at_execution"], record["execution"]["lane_digest_sha256"])
            records.append(record)
        return records

    def test_lane_is_accepted_without_scores_and_resolves(self):
        lane = self._lane()
        self.assertEqual(lane["status"], "accepted")
        self.assertIs(lane["frozen_before_any_score"], True)
        self.assertEqual(lane["authority_effect"], "none")
        self.assertEqual(_score_keys(lane), [])
        integration = get_integration(lane["benchmark_integration"])
        entries = {item["variant"]: item for item in integration["evidence_history"]}
        for row in lane["systems"]:
            self.assertIn(row["status"], {"accepted", "deferred"}, row["row_id"])
            if row["status"] == "deferred":
                self.assertEqual(entries[f"lane:{self.lane_id}:{row['provider_key']}"]["status"], "blocked")
                continue
            self.assertIn(self.lane_id, row["status_reason"])
            for suffix in [f":{plane}" for plane in self.planes] or [""]:
                entry = entries[f"lane:{self.lane_id}:{row['provider_key']}{suffix}"]
                self.assertEqual(entry["status"], "complete")
                self.assertEqual(entry["input_sha256"], lane["dataset"]["input_sha256"])
                self.assertEqual(entry["system_id"], row["system_id"])
                self.assertEqual(entry["report_binding"], {"input_sha256_path": "input.sha256", "system_revision_path": "system.revision"})
                self.assertIn(entry["report"].rsplit("/", 2)[-2], row["status_reason"])
        self.assertEqual({row["role"] for row in lane["systems"]}, {"control", "baseline", "comparator"})
        resolved = resolve_lane(lane)
        self.assertEqual(resolved["lane_id"], self.lane_id)
        self.assertIn(self.predecessor_id, " ".join(lane["comparability"]["not_comparable_to"]))
        self.assertNotIn(self.lane_id, [item["lane_id"] for item in lane.get("deferred_lanes", [])])

    def test_reference_blobs_are_the_ones_the_accepted_runs_executed(self):
        # An accepted lane's pins are a fact about the runs it bound, not about HEAD: every
        # evidence record carries the blobs its run hashed, and they equal the lane's pins.
        lane = self._lane()
        bound = {path: blob for path, blob in lane["harness"]["source_blobs"].items() if path.startswith("reference/")}
        self.assertEqual(set(bound), self.pinned_reference_paths)
        for record in self._records():
            self.assertEqual(record["execution"][self.evidence_blob_key], bound, record["row"]["row_id"])

    def test_accepted_rows_executed_under_the_declared_transition(self):
        lane = self._lane()
        posture = next(row for row in lane["systems"] if row["role"] == "control")["configuration"]["runtime_baseline_posture"]
        for record in self._records():
            binding = record["system"]["runtime_baseline"]
            self.assertEqual(binding["state"], "TRANSITION", record["row"]["row_id"])
            self.assertEqual(binding["declaration_blob"], posture["declaration_blob"])
            self.assertEqual(binding["declared_successor"], posture["declared_successor"])
            self.assertIn("declared_successor=agent-memory-runtime-baseline-v2", binding["line"])
            self.assertIs(record["execution"]["full_selection"], True)

    def test_lane_workflow_checks_out_the_history_the_checker_needs(self):
        # The posture step runs scripts/check_runtime_baseline_equivalence.py, which diffs the
        # checkout against the frozen runtime revision: a depth-1 checkout aborts it (runs
        # 37542447011-37542464528 on main 15404ac failed exactly there), so the Agent Memory
        # checkout must fetch full history.
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / self.workflow_path).read_text(encoding="utf-8")
        self.assertIn(f"- {self.lane_id}", workflow)
        self.assertIn("check_runtime_baseline_equivalence.py --candidate HEAD", workflow)
        first_checkout = workflow.index("uses: actions/checkout@")
        checkout_block = workflow[first_checkout : workflow.index("- name:", first_checkout)]
        self.assertNotIn("repository:", checkout_block, "the first checkout is the Agent Memory checkout")
        self.assertIn("fetch-depth: 0", checkout_block)

    def test_control_declares_the_budget_and_the_transition_posture(self):
        lane = self._lane()
        repo_root = Path(__file__).resolve().parents[2]
        control = next(row for row in lane["systems"] if row["role"] == "control")
        self.assertEqual(control["source"]["kind"], "repository_runtime")
        self.assertIn("Runtime Baseline v2", control["display_name"])
        posture = control["configuration"]["runtime_baseline_posture"]
        self.assertEqual(posture["predecessor"], "agent-memory-runtime-baseline-v1")
        self.assertEqual(posture["declared_successor"], "agent-memory-runtime-baseline-v2")
        self.assertEqual(posture["declaration"], V2_DECLARATION)
        self.assertEqual(posture["declaration_blob"], _hash_object(repo_root, V2_DECLARATION))
        self.assertEqual(posture["checker_state_required"], ["PASS", "TRANSITION"])
        self.assertIn("check_runtime_baseline_equivalence.py", control["source"]["revision_rule"])
        self.assertIn("returned", control["configuration"]["recall"])
        self.assertIn("contract 1.4.0", control["configuration"]["recall"])


class AmbPrecisionMemBenchV2LaneTests(_AcceptedV2LaneMixin, unittest.TestCase):
    lane_id = AMB_V2_LANE_ID
    predecessor_id = LANE_ID
    workflow_path = ".github/workflows/amb-competitive.yml"
    evidence_blob_key = "bridge_blobs"
    pinned_reference_paths = {"reference/amb_agent_memory_bridge.py", "reference/amb_mem0_explicit_bridge.py"}

    def test_bridge_0_2_0_is_the_pinned_adapter(self):
        import sys

        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root / "reference"))
        import amb_agent_memory_bridge as bridge

        lane = self._lane()
        control = next(row for row in lane["systems"] if row["role"] == "control")
        self.assertEqual(bridge.BRIDGE_VERSION, "0.2.0")
        self.assertIn("bridge_version 0.2.0", control["adapter"]["revision_rule"])
        self.assertIn(lane["harness"]["source_blobs"]["reference/amb_agent_memory_bridge.py"], control["adapter"]["revision_rule"])
        self.assertIn("never a bridge-side cap", control["configuration"]["k"])


class LongMemEvalParityV2LaneTests(_AcceptedV2LaneMixin, unittest.TestCase):
    lane_id = LME_V2_LANE_ID
    predecessor_id = LME_LANE_ID
    workflow_path = ".github/workflows/longmemeval-competitive.yml"
    planes = ("session", "turn")
    evidence_blob_key = "source_blobs"
    pinned_reference_paths = {
        "reference/run_longmemeval.py",
        "reference/longmemeval_mem0_explicit_bridge.py",
        "reference/amb_mem0_explicit_bridge.py",
    }

    def test_control_budget_is_fifty_and_the_runner_blob_is_pinned_everywhere(self):
        lane = self._lane()
        control = next(row for row in lane["systems"] if row["role"] == "control")
        self.assertEqual(control["configuration"]["budget"], "50")
        self.assertEqual(control["configuration"]["temporal_metadata"], "none")
        self.assertEqual(control["configuration"]["ranking_variant"], "default")
        runner_blob = lane["harness"]["source_blobs"]["reference/run_longmemeval.py"]
        self.assertIn(runner_blob, lane["evaluator"]["scorer"])
        self.assertIn(runner_blob, control["adapter"]["revision_rule"])
        baseline = next(row for row in lane["systems"] if row["role"] == "baseline")
        self.assertEqual(baseline["source"]["revision"], runner_blob)
        self.assertIn("budget=50", lane["budget"]["retrieval_k_rule"])
        self.assertIn("--agent-memory-budget", lane["execution"]["environment"]["dispatch_unit"])
