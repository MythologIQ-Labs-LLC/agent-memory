"""Executable benchmark-author golden path (#652).

Proves that a benchmark integration descriptor, a frozen input, a Gauntlet-bound runner,
descriptor-driven normalization, and evaluator-integrity negative controls work together
through the same neutral surface an external system author uses.
"""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.evaluation.benchmark_golden_keyed_retrieval import (
    INTEGRATION_ID,
    execute_native,
    input_path,
    load_frozen_input,
    normalize_golden_keyed_retrieval,
    run_integrity_controls,
)
from agentmem_ref.evaluation.contract import load_run, validate_run
from agentmem_ref.evaluation.gauntlet_orchestrator import load_adapter_manifest, run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import GOLDEN_KEYED_RETRIEVAL_PROFILE_ID
from agentmem_ref.evaluation.gauntlet_transport import AdapterSession, GauntletExecutionError
from agentmem_ref.evaluation.registry import get_integration

FIXTURES = REPO_ROOT / "fixtures" / "gauntlet"
LEXICAL = FIXTURES / "lexical-adapter.json"
NO_MEMORY = FIXTURES / "no-memory-adapter.json"
EXTERNAL_STDIO = REPO_ROOT / "examples" / "gauntlet" / "minimal-stdio-adapter.json"
COMMITTED_INTEGRITY_REPORT = REPO_ROOT / "reports" / "benchmarks" / "golden-keyed-retrieval" / "integrity-controls-v1.json"


def _write(root: Path, value: dict, name: str) -> Path:
    path = root / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class BenchmarkAuthorGoldenPathTests(unittest.TestCase):
    def test_frozen_input_identity_is_exact_and_fail_closed(self):
        descriptor = get_integration(INTEGRATION_ID)
        fixture, digest = load_frozen_input(descriptor)
        self.assertEqual(digest, descriptor["input_contract"]["known_input_sha256"])
        self.assertEqual(hashlib.sha256(input_path(descriptor).read_bytes()).hexdigest(), digest)
        ids = [record["id"] for record in fixture["records"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(query["gold_id"] in ids for query in fixture["queries"]))
        tampered = copy.deepcopy(descriptor)
        tampered["input_contract"]["known_input_sha256"] = "1" * 63 + "2"
        with self.assertRaises(GauntletExecutionError) as raised:
            load_frozen_input(tampered)
        self.assertEqual(raised.exception.source, "benchmark_input")
        self.assertEqual(raised.exception.code, "input_digest_mismatch")

    def test_native_results_survive_normalization_without_mutation(self):
        descriptor = get_integration(INTEGRATION_ID)
        fixture, digest = load_frozen_input(descriptor)
        manifest = load_adapter_manifest(LEXICAL)
        with AdapterSession(manifest) as session:
            native = execute_native(session, run_id="t", namespace="t", fixture=fixture, input_sha256=digest, document=descriptor)
        frozen = copy.deepcopy(native)
        dimensions = normalize_golden_keyed_retrieval(native, descriptor)
        self.assertEqual(native, frozen)
        self.assertEqual(dimensions["retrieval"]["status"], "measured")
        self.assertEqual({m["metric_id"] for m in dimensions["retrieval"]["metrics"]}, {"exact_top1", "recall_at_3"})
        self.assertEqual(dimensions["currentness"]["status"], "not_applicable")
        self.assertEqual(dimensions["efficiency"]["status"], "not_measured")
        self.assertEqual(dimensions["efficiency"]["metrics"], [])
        self.assertEqual(native["profile_kind"], "baseline_or_probe")

    def test_gauntlet_bound_profile_runs_baselines_and_external_contestant(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lexical = run_gauntlet(LEXICAL, GOLDEN_KEYED_RETRIEVAL_PROFILE_ID, output_dir=root / "lexical")
            no_memory = run_gauntlet(NO_MEMORY, GOLDEN_KEYED_RETRIEVAL_PROFILE_ID, output_dir=root / "none")
            external = run_gauntlet(
                EXTERNAL_STDIO, GOLDEN_KEYED_RETRIEVAL_PROFILE_ID, output_dir=root / "external",
                allow_external_process=True, allow_destructive_reset=True,
            )
            for qualification in (lexical, no_memory, external):
                self.assertEqual(qualification["status"], "complete", qualification.get("failure"))
                self.assertEqual(qualification["benchmark_integration"], INTEGRATION_ID)
                self.assertEqual(qualification["profile"]["kind"], "baseline_or_probe")
                normalized = load_run(qualification["artifacts"]["normalized_run"]["path"])
                native = json.loads(Path(qualification["artifacts"]["native_results"]["path"]).read_text(encoding="utf-8"))
                self.assertEqual(normalized["benchmark"]["id"], "golden-keyed-retrieval")
                self.assertEqual(normalized["benchmark"]["input_sha256"], get_integration(INTEGRATION_ID)["input_contract"]["known_input_sha256"])
                self.assertEqual(normalized["native_results"]["rows"], native["rows"])
                self.assertEqual(normalized["native_results"]["metrics"], native["metrics"])
                self.assertEqual(normalized["native_results"]["profile_kind"], "baseline_or_probe")
                self.assertEqual(normalized["authority_effect"], "none")
            lex = load_run(lexical["artifacts"]["normalized_run"]["path"])
            none = load_run(no_memory["artifacts"]["normalized_run"]["path"])
            ext = load_run(external["artifacts"]["normalized_run"]["path"])
            top1 = lambda run: next(m for m in run["dimensions"]["retrieval"]["metrics"] if m["metric_id"] == "exact_top1")["value"]
            self.assertEqual(top1(lex), 1.0)
            self.assertEqual(top1(none), 0.0)
            self.assertEqual(top1(ext), 1.0)
            self.assertEqual(ext["system"]["kind"], "external_memory")

    def test_unsupported_and_blocked_stay_distinct_from_failed_and_zero(self):
        manifest = load_adapter_manifest(LEXICAL)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unsupported = copy.deepcopy(manifest)
            unsupported["capabilities"]["recall"] = {"support": "unsupported"}
            qualification = run_gauntlet(_write(root, unsupported, "unsupported.json"), GOLDEN_KEYED_RETRIEVAL_PROFILE_ID, output_dir=root / "u")
            self.assertEqual(qualification["status"], "unsupported")
            self.assertNotIn("failure", qualification)
            self.assertEqual(qualification["negotiation"]["outcome"], "unsupported")
            self.assertEqual(set(qualification["coverage"].values()), {"unsupported"})
            self.assertNotIn("normalized_run", qualification["artifacts"])

            blocked = run_gauntlet(EXTERNAL_STDIO, GOLDEN_KEYED_RETRIEVAL_PROFILE_ID, output_dir=root / "b")
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["failure"]["code"], "external_process_opt_in_required")
            self.assertEqual(blocked["failure"]["source"], "orchestrator")
            self.assertEqual(blocked["coverage"]["retrieval"], "blocked")
            self.assertNotIn("normalized_run", blocked["artifacts"])

    def test_capability_posture_survives_into_qualification_output(self):
        manifest = load_adapter_manifest(LEXICAL)
        limited = copy.deepcopy(manifest)
        limited["capabilities"]["health"] = {"support": "unsupported", "notes": "declared unsupported on purpose"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qualification = run_gauntlet(_write(root, limited, "limited.json"), GOLDEN_KEYED_RETRIEVAL_PROFILE_ID, output_dir=root)
            self.assertEqual(qualification["status"], "complete")
            self.assertEqual(qualification["negotiation"]["outcome"], "eligible_with_limitations")
            optional = {row["capability"]: row for row in qualification["negotiation"]["optional"]}
            self.assertEqual(optional["health"]["state"], "unsupported_optional")
            self.assertEqual(optional["health"]["declared_support"], "unsupported")
            persisted = json.loads(Path(qualification["artifacts"]["qualification"]["path"]).read_text(encoding="utf-8"))
            self.assertEqual(persisted["negotiation"]["outcome"], "eligible_with_limitations")
            normalized = load_run(qualification["artifacts"]["normalized_run"]["path"])
            self.assertEqual(normalized["dimensions"]["retrieval"]["metrics"][0]["value"], 1.0)

    def test_integrity_controls_detect_deliberately_broken_evaluator_arms(self):
        manifest = load_adapter_manifest(LEXICAL)
        report = run_integrity_controls(manifest)
        self.assertTrue(report["all_as_expected"], report["controls"])
        controls = {row["control_id"]: row for row in report["controls"]}
        self.assertEqual(report["healthy"]["exact_top1"], 1.0)
        self.assertTrue(controls["gold_omission"]["detected"])
        self.assertLess(controls["gold_omission"]["control_value"], report["healthy"]["exact_top1"])
        self.assertTrue(controls["rank_inversion"]["detected"])
        self.assertEqual(controls["rank_inversion"]["recall_at_3"], report["healthy"]["recall_at_3"])
        self.assertTrue(controls["identity_corruption"]["detected"])
        self.assertFalse(controls["unrelated_record_omission"]["detected"])
        self.assertEqual(controls["unrelated_record_omission"]["control_value"], report["healthy"]["exact_top1"])
        self.assertEqual(report["profile_kind"], "baseline_or_probe")
        self.assertEqual(report["authority_effect"], "none")

        # A control that breaks the evaluator's declared expectation is a failed qualification.
        declared = {c["control_id"] for c in get_integration(INTEGRATION_ID)["evaluator_integrity"]["negative_controls"]}
        self.assertEqual(declared, set(controls))

        committed = json.loads(COMMITTED_INTEGRITY_REPORT.read_text(encoding="utf-8"))
        self.assertEqual(committed, report, "committed integrity evidence drifted from the regenerated report")

    def test_no_memory_contestant_fails_every_control_arm_but_is_not_the_evaluator_verdict(self):
        manifest = load_adapter_manifest(NO_MEMORY)
        report = run_integrity_controls(manifest)
        self.assertEqual(report["healthy"]["exact_top1"], 0.0)
        # With a healthy value of zero nothing can fall further: detection controls cannot be
        # established, and the report says so rather than claiming the evaluator passed.
        self.assertFalse(report["all_as_expected"])

    def test_profile_runner_input_is_the_descriptor_not_a_restated_identity(self):
        descriptor = get_integration(INTEGRATION_ID)
        self.assertEqual(descriptor["gauntlet"]["profile_id"], GOLDEN_KEYED_RETRIEVAL_PROFILE_ID)
        self.assertEqual(descriptor["native_protocol"]["runner"]["kind"], "gauntlet_profile_runner")
        self.assertEqual(descriptor["system_requirements"]["invocation_surface"], "gauntlet_operation_envelope")
        source = (REPO_ROOT / "reference" / "agentmem_ref" / "evaluation" / "benchmark_golden_keyed_retrieval.py").read_text(encoding="utf-8")
        self.assertNotIn("AgentMemory", source)
        self.assertNotIn("agentmem_ref.runtime", source)
        self.assertNotIn("agentmem_ref.memory", source)
        self.assertNotIn(descriptor["input_contract"]["known_input_sha256"], source)
        validate_run_document = {
            "schema_version": "1.0.0", "run_id": "x", "status": "not_run",
            "benchmark": {"id": "golden-keyed-retrieval", "source_revision": "1.0.0", "input_sha256": None},
            "system": {"id": "s", "kind": "other", "revision": "r"},
            "execution": {"selection_id": "none", "selection_method": "none", "sample_count": 0},
            "dimensions": {name: {"status": "not_measured", "metrics": [], "notes": []} for name in ("retrieval", "currentness", "reasoning", "governance", "efficiency", "evaluator_integrity", "reproducibility")},
            "native_results": {}, "limitations": [], "artifacts": [], "authority_effect": "none",
        }
        validate_run(validate_run_document)


if __name__ == "__main__":
    unittest.main()
