"""Adversarial tests for the benchmark integration contract, registry convergence, and CLI (#652)."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.console import main
from agentmem_ref.evaluation import (
    BenchmarkIntegrationError,
    ComparisonCompatibilityError,
    check_profile_binding,
    compare_runs,
    dimension_report,
    integration_digest,
    load_integration,
    mapped_metric_observations,
    validate_integration,
)
from agentmem_ref.evaluation.benchmark_integration import (
    PROVENANCE_CLASSES,
    contract_version_compatible,
    declared_mapping,
    is_placeholder_sha256,
)
from agentmem_ref.evaluation.gauntlet_orchestrator import _bind_profile_kind
from agentmem_ref.evaluation.gauntlet_profiles import (
    GOLDEN_KEYED_RETRIEVAL_PROFILE_ID,
    get_gauntlet_profile,
    list_gauntlet_profiles,
)
from agentmem_ref.evaluation.gauntlet_transport import GauntletExecutionError
from agentmem_ref.evaluation.registry import (
    check_evidence_binding,
    get_integration,
    integration_paths,
    list_integrations,
    list_profiles,
    validate_registry_relationships,
)

GOLDEN_ID = "golden-keyed-retrieval-v1"


def _golden() -> dict:
    return get_integration(GOLDEN_ID)


def _empty_dimensions(status: str = "not_measured") -> dict:
    return {
        name: dimension_report(status, notes=["fixture"])
        for name in ("retrieval", "currentness", "reasoning", "governance", "efficiency", "evaluator_integrity", "reproducibility")
    }


def _run(status: str, input_sha: str | None) -> dict:
    return {
        "schema_version": "1.0.0",
        "run_id": f"run:{status}",
        "status": status,
        "benchmark": {"id": "bench", "source_revision": "rev", "input_sha256": input_sha},
        "system": {"id": "sys", "kind": "lexical", "revision": "r1"},
        "execution": {"selection_id": "all", "selection_method": "all", "sample_count": 1},
        "dimensions": _empty_dimensions("blocked" if status == "blocked" else "not_measured"),
        "native_results": {},
        "limitations": [],
        "artifacts": [],
        "authority_effect": "none",
    }


class BenchmarkIntegrationContractTests(unittest.TestCase):
    def test_committed_descriptors_validate_and_bind_to_committed_reports(self):
        descriptors = list_integrations()
        self.assertGreaterEqual(len(descriptors), 4)
        self.assertEqual(len(integration_paths()), len(descriptors))
        for descriptor in descriptors:
            self.assertEqual(descriptor["authority_effect"], "none")
            self.assertIn(descriptor["benchmark"]["provenance_class"], PROVENANCE_CLASSES)
            for row in check_evidence_binding(descriptor, repo_root=REPO_ROOT):
                self.assertTrue(row["bound"], row)
            digest = integration_digest(descriptor)
            self.assertEqual(len(digest), 64)
            self.assertEqual(digest, integration_digest(descriptor))

    def test_registry_relationships_are_mutual_and_class_preserving(self):
        summary = validate_registry_relationships()
        self.assertEqual(summary["authority_effect"], "none")
        bindings = {row["integration_id"]: row for row in summary["bindings"]}
        self.assertIn(GOLDEN_ID, bindings)
        self.assertEqual(bindings[GOLDEN_ID]["provenance_class"], "baseline_or_probe")
        for profile in list_gauntlet_profiles():
            self.assertIn("benchmark_integration", profile)
            if profile["benchmark_integration"] is None:
                self.assertIn(profile["kind"], {"baseline_or_probe", "gauntlet_native_gap", "agent_memory_conformance"})

    def test_malformed_descriptor_refuses(self):
        with self.assertRaises(BenchmarkIntegrationError):
            validate_integration({})
        descriptor = _golden()
        descriptor["normalization"]["normalizer"] = None
        with self.assertRaisesRegex(BenchmarkIntegrationError, "invents evidence"):
            validate_integration(descriptor)
        descriptor = _golden()
        descriptor["provider_requirements"]["judge"] = {"required": True, "identity": None}
        with self.assertRaisesRegex(BenchmarkIntegrationError, "credential_free"):
            validate_integration(descriptor)
        descriptor = _golden()
        del descriptor["normalization"]["unmapped_dimensions"]["reasoning"]
        with self.assertRaisesRegex(BenchmarkIntegrationError, "every common dimension"):
            validate_integration(descriptor)
        descriptor = _golden()
        descriptor["evidence_history"][0].pop("report")
        with self.assertRaisesRegex(BenchmarkIntegrationError, "requires exact report"):
            validate_integration(descriptor)
        descriptor = _golden()
        descriptor["gauntlet"]["profile_id"] = None
        with self.assertRaisesRegex(BenchmarkIntegrationError, "bound_profile requires"):
            validate_integration(descriptor)

    def test_unknown_contract_version_refuses_unless_policy_compatible(self):
        self.assertTrue(contract_version_compatible("1.0.0"))
        self.assertTrue(contract_version_compatible("1.0.7"))
        self.assertFalse(contract_version_compatible("1.1.0"))
        self.assertFalse(contract_version_compatible("2.0.0"))
        self.assertFalse(contract_version_compatible("0.9.0"))
        for version in ("2.0.0", "1.1.0", "0.9.0"):
            descriptor = _golden()
            descriptor["contract_version"] = version
            with self.assertRaisesRegex(BenchmarkIntegrationError, "unsupported benchmark integration contract version"):
                validate_integration(descriptor)
        descriptor = _golden()
        descriptor["contract_version"] = "1.0.9"
        validate_integration(descriptor)

    def test_placeholder_digests_cannot_disguise_missing_inputs(self):
        self.assertTrue(is_placeholder_sha256("a" * 64))
        self.assertTrue(is_placeholder_sha256("0" * 64))
        self.assertTrue(is_placeholder_sha256(hashlib.sha256(b"").hexdigest()))
        self.assertTrue(is_placeholder_sha256("A" * 64))
        self.assertFalse(is_placeholder_sha256(_golden()["input_contract"]["known_input_sha256"]))
        descriptor = _golden()
        descriptor["input_contract"]["known_input_sha256"] = "0" * 64
        with self.assertRaisesRegex(BenchmarkIntegrationError, "placeholder"):
            validate_integration(descriptor)
        descriptor = _golden()
        descriptor["input_contract"]["known_input_sha256"] = None
        with self.assertRaisesRegex(BenchmarkIntegrationError, "known_input_sha256 is required"):
            validate_integration(descriptor)
        descriptor = _golden()
        descriptor["evidence_history"][0]["input_sha256"] = "f" * 64
        with self.assertRaisesRegex(BenchmarkIntegrationError, "placeholder"):
            validate_integration(descriptor)

    def test_provenance_cannot_be_claimed_or_laundered_by_descriptor_fields(self):
        descriptor = _golden()
        descriptor["benchmark"]["provenance_class"] = "external_independent"
        with self.assertRaisesRegex(BenchmarkIntegrationError, "requires benchmark.upstream"):
            validate_integration(descriptor)
        descriptor = _golden()
        descriptor["benchmark"]["upstream"] = {"repository": "someone/bench", "url": "https://example.invalid"}
        with self.assertRaisesRegex(BenchmarkIntegrationError, "baseline_or_probe benchmark may not claim"):
            validate_integration(descriptor)

    def test_executed_result_without_exact_input_identity_cannot_compare(self):
        with self.assertRaises(BenchmarkIntegrationError.__mro__[1]):
            # complete run with null digest is refused at validation
            compare_runs(_run("complete", None), _run("complete", None))
        blocked = _run("blocked", None)
        with self.assertRaises(ComparisonCompatibilityError):
            compare_runs(blocked, blocked)

    def test_common_mapping_cannot_manufacture_a_measurement(self):
        descriptor = _golden()
        descriptor["normalization"]["mappings"].append(
            {"dimension": "retrieval", "metric_id": "phantom", "native_evidence": "metrics.phantom", "semantics": "absent", "direction": "higher_better"}
        )
        native = {"sample_count": 8, "metrics": {"exact_top1": 0.5, "recall_at_3": 1.0, "nested": {"x": 1}}}
        observations = {m["metric_id"]: m for m in mapped_metric_observations(descriptor, native, dimension="retrieval")}
        self.assertEqual(observations["exact_top1"]["state"], "measured")
        self.assertEqual(observations["exact_top1"]["value"], 0.5)
        self.assertEqual(observations["phantom"]["state"], "not_measured")
        self.assertNotIn("value", observations["phantom"])
        descriptor["normalization"]["mappings"].append(
            {"dimension": "retrieval", "metric_id": "object", "native_evidence": "metrics.nested", "semantics": "non-scalar", "direction": "descriptive"}
        )
        observations = {m["metric_id"]: m for m in mapped_metric_observations(descriptor, native, dimension="retrieval")}
        self.assertEqual(observations["object"]["state"], "not_measured")

    def test_gauntlet_registration_cannot_upgrade_provenance(self):
        descriptor = _golden()
        profile = get_gauntlet_profile(GOLDEN_KEYED_RETRIEVAL_PROFILE_ID)
        self.assertEqual(check_profile_binding(profile, descriptor)["status"], "bound")
        for kind in ("external_independent", "external_adapted", "gauntlet_native_gap"):
            upgraded = dict(profile, kind=kind)
            with self.assertRaisesRegex(BenchmarkIntegrationError, "cannot change evidence class"):
                check_profile_binding(upgraded, descriptor)
        unbound = dict(profile, benchmark_integration=None)
        with self.assertRaisesRegex(BenchmarkIntegrationError, "does not declare benchmark_integration"):
            check_profile_binding(unbound, descriptor)
        other_runner = dict(profile, runner="agentmem_ref.evaluation.gauntlet_probe:run_retrieval_probe")
        with self.assertRaisesRegex(BenchmarkIntegrationError, "differs from the integration runner"):
            check_profile_binding(other_runner, descriptor)

        # A profile presenting itself as external evidence without any bound benchmark is refused.
        fake = dict(get_gauntlet_profile("gauntlet-orchestration-retrieval-probe-v1"), kind="external_independent")
        with mock.patch("agentmem_ref.evaluation.gauntlet_profiles.list_gauntlet_profiles", return_value=[fake]):
            with self.assertRaisesRegex(BenchmarkIntegrationError, "registration cannot create external evidence"):
                validate_registry_relationships()

        # A runner cannot upgrade the registered kind at execution time either.
        with self.assertRaises(GauntletExecutionError) as raised:
            _bind_profile_kind({"profile_kind": "external_independent"}, {"kind": "baseline_or_probe"})
        self.assertEqual(raised.exception.code, "provenance_mismatch")
        bound = _bind_profile_kind({"sample_count": 0}, {"kind": "gauntlet_native_gap"})
        self.assertEqual(bound["profile_kind"], "gauntlet_native_gap")

    def test_validation_does_not_execute_benchmark_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sentinel = root / "executed.txt"
            module = root / "sentinel_benchmark_runner.py"
            module.write_text(
                "from pathlib import Path\n"
                f"Path({str(sentinel)!r}).write_text('executed')\n"
                "def run(*args, **kwargs):\n    raise RuntimeError('must not run')\n",
                encoding="utf-8",
            )
            descriptor = _golden()
            descriptor["native_protocol"]["runner"]["entry_point"] = "sentinel_benchmark_runner:run"
            descriptor["normalization"]["normalizer"] = "sentinel_benchmark_runner:run"
            descriptor["evaluator_integrity"]["runner"] = "sentinel_benchmark_runner.py"
            descriptor["gauntlet"] = {"relationship": "eligible", "profile_id": None, "reason": "test"}
            path = root / "descriptor.json"
            path.write_text(json.dumps(descriptor), encoding="utf-8")
            sys.path.insert(0, str(root))
            try:
                load_integration(path)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["benchmark", "validate-integration", str(path), "--json"])
            finally:
                sys.path.remove(str(root))
            self.assertEqual(code, 0)
            report = json.loads(output.getvalue())
            self.assertTrue(report["valid"])
            self.assertFalse(report["executed"])
            self.assertFalse(sentinel.exists(), "validation imported/executed the runner")
            self.assertNotIn("sentinel_benchmark_runner", sys.modules)

    def test_cli_inspect_and_validate_integration_are_stable_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["benchmark", "inspect", GOLDEN_ID, "--json"])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        for key in (
            "schema_version", "command", "valid", "integration_id", "integration_digest_sha256", "contract_version",
            "admission_state", "benchmark", "provenance_class", "invocation_surface", "external_system_entry",
            "credentials", "runner", "gauntlet", "evidence_binding", "identity_findings", "mapped_dimensions",
            "unmapped_dimensions", "negative_control_count", "executed", "descriptor", "profile", "authority_effect",
        ):
            self.assertIn(key, report)
        self.assertEqual(report["command"], "benchmark_inspect")
        self.assertEqual(report["gauntlet"]["status"], "bound")
        self.assertEqual(report["gauntlet"]["profile_kind"], "baseline_or_probe")
        self.assertEqual(report["authority_effect"], "none")
        self.assertTrue(all(row["bound"] for row in report["evidence_binding"]))

        path = next(p for p in integration_paths() if p.name.startswith("swe-context-bench"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["benchmark", "validate-integration", str(path), "--json"])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["command"], "benchmark_validate_integration")
        self.assertEqual(report["gauntlet"]["status"], "not_applicable")
        self.assertIn("source revision is manifest-bound per run, not static", report["identity_findings"])
        self.assertEqual(report["admission_state"], "blocked")

        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.json"
            bad.write_text(json.dumps({"contract_family": "agent-memory-benchmark-integration"}), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["benchmark", "validate-integration", str(bad), "--json"])
            self.assertEqual(code, 2)
            refusal = json.loads(output.getvalue())
            self.assertEqual(refusal["status"], "refused")
            self.assertFalse(refusal["valid"])
            self.assertEqual(refusal["authority_effect"], "none")

    def test_cli_human_output_for_integrations(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["benchmark", "inspect", GOLDEN_ID])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("Provenance class: baseline_or_probe", text)
        self.assertIn("Executed: no", text)
        self.assertIn("Authority effect: none", text)

    def test_legacy_list_projection_remains_compatible(self):
        profiles = {profile["profile_id"]: profile for profile in list_profiles()}
        self.assertIn("swe-context-bench-lite-external-retrieval-v1", profiles)
        for profile in profiles.values():
            for key in ("profile_id", "benchmark_id", "owning_issue", "runner", "external_evidence_status", "external_evidence", "dimensions", "description"):
                self.assertIn(key, profile)
            self.assertEqual(profile["authority_effect"], "none")
            self.assertEqual(profile["provenance_class"], get_integration(profile["profile_id"])["benchmark"]["provenance_class"])

    def test_committed_normalized_reports_emit_only_declared_mappings(self):
        """A normalizer may not emit a measured common metric the descriptor never declared."""

        by_benchmark = {d["benchmark"]["id"]: d for d in list_integrations()}
        normalized = sorted((REPO_ROOT / "reports" / "benchmarks" / "normalized").glob("*.json"))
        self.assertTrue(normalized)
        checked = 0
        for path in normalized:
            run = json.loads(path.read_text(encoding="utf-8"))
            descriptor = by_benchmark[run["benchmark"]["id"]]
            self.assertEqual(descriptor["normalization"]["normalizer"].split(":")[0], "agentmem_ref.evaluation.normalize")
            for dimension, report in run["dimensions"].items():
                for metric in report["metrics"]:
                    mapping = declared_mapping(descriptor, dimension, metric["metric_id"])
                    self.assertIsNotNone(mapping, f"{path.name}: {dimension}.{metric['metric_id']} is not declared by {descriptor['integration_id']}")
                    if metric["state"] == "measured":
                        self.assertEqual(mapping.get("direction", "descriptive"), metric["direction"], f"{path.name}: {dimension}.{metric['metric_id']} direction")
                    checked += 1
        self.assertGreater(checked, 50)
        self.assertIsNone(declared_mapping(by_benchmark["longmemeval"], "retrieval", "phantom_metric"))
        self.assertIsNotNone(declared_mapping(by_benchmark["longmemeval"], "retrieval", "recall_all@50"))
        self.assertIsNone(declared_mapping(by_benchmark["longmemeval"], "retrieval", "recall_all@"))

    def test_runtime_import_remains_independent_from_evaluation(self):
        code = (
            "import sys, agentmem_ref, agentmem_ref.runtime.cli\n"
            "loaded = sorted(m for m in sys.modules if m.startswith('agentmem_ref.evaluation'))\n"
            "assert not loaded, loaded\n"
            "print('independent')\n"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("independent", result.stdout)

    def test_evaluation_only_change_keeps_runtime_baseline_equivalence(self):
        boundary = json.loads((REPO_ROOT / "reports" / "runtime" / "baseline-v1-source-boundary.json").read_text(encoding="utf-8"))
        excluded = [item["path"] for item in boundary["excluded_non_runtime_paths"]]
        self.assertEqual(excluded, ["reference/agentmem_ref/evaluation"])
        self.assertIs(boundary["baseline_mutation"], False)
        available = subprocess.run(
            ["git", "cat-file", "-e", f"{boundary['frozen_revision']}^{{commit}}"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        if available.returncode != 0:
            self.skipTest("frozen Runtime Baseline v1 revision is not available in this checkout")
        result = subprocess.run(
            [sys.executable, "scripts/check_runtime_baseline_equivalence.py", "--candidate", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
