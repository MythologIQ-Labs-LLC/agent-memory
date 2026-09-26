from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.evaluation.contract import load_run
from agentmem_ref.evaluation.gauntlet_orchestrator import run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import (
    GOVERNANCE_ALPHA_PROFILE_ID,
    get_gauntlet_profile,
    list_gauntlet_profiles,
)


FIXTURE_DIR = REPO_ROOT / "fixtures" / "gauntlet"


def _case_map(native_results: dict) -> dict[str, dict]:
    return {case["case_id"]: case for case in native_results["cases"]}


def _metric_map(run: dict) -> dict[str, dict]:
    return {
        metric["metric_id"]: metric
        for metric in run["dimensions"]["governance"]["metrics"]
    }


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _write_manifest(root: Path, manifest: dict) -> Path:
    path = root / "adapter.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class GovernanceGauntletAlphaTests(unittest.TestCase):
    def test_profile_is_discoverable_as_gauntlet_native_gap_evidence(self):
        profile = get_gauntlet_profile(GOVERNANCE_ALPHA_PROFILE_ID)
        self.assertEqual(profile["kind"], "gauntlet_native_gap")
        self.assertEqual(profile["destructive_operations"]["forget"], "deletion")
        ids = {item["profile_id"] for item in list_gauntlet_profiles()}
        self.assertIn(GOVERNANCE_ALPHA_PROFILE_ID, ids)

    def test_strict_fixture_passes_exercised_claims_and_preserves_unsupported(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_gauntlet(
                FIXTURE_DIR / "governance-strict-adapter.json",
                GOVERNANCE_ALPHA_PROFILE_ID,
                output_dir=temporary,
            )
            self.assertEqual(result["status"], "complete")
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            cases = _case_map(run["native_results"])

            for case_id in (
                "GOV-ISO-001",
                "GOV-ISO-002",
                "GOV-ISO-005",
                "GOV-DEL-001",
                "GOV-AUTH-002",
                "GOV-AUTH-003",
            ):
                self.assertEqual(cases[case_id]["result"], "pass", case_id)

            self.assertEqual(cases["GOV-DEL-002"]["result"], "unsupported")
            self.assertEqual(cases["GOV-AUTH-004"]["result"], "unsupported")
            self.assertEqual(cases["GOV-AUTH-005"]["result"], "unsupported")
            self.assertEqual(cases["GOV-SRC-002"]["result"], "unsupported")
            self.assertEqual(run["native_results"]["profile_kind"], "gauntlet_native_gap")
            self.assertEqual(run["dimensions"]["governance"]["status"], "partial")
            self.assertEqual(run["authority_effect"], "none")

            metrics = _metric_map(run)
            self.assertEqual(metrics["gov_iso_001"]["value"], True)
            self.assertEqual(metrics["gov_del_002"]["state"], "not_applicable")
            evaluator_metrics = {
                metric["metric_id"]: metric
                for metric in run["dimensions"]["evaluator_integrity"]["metrics"]
            }
            self.assertEqual(
                evaluator_metrics["aggregate_governance_score_emitted"]["value"], False
            )

    def test_leaky_fixture_produces_measured_governance_failures_not_execution_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_gauntlet(
                FIXTURE_DIR / "governance-leaky-adapter.json",
                GOVERNANCE_ALPHA_PROFILE_ID,
                output_dir=temporary,
            )
            self.assertEqual(result["status"], "complete")
            self.assertNotIn("failure", result)
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            cases = _case_map(run["native_results"])
            self.assertEqual(cases["GOV-ISO-001"]["result"], "fail")
            self.assertTrue(cases["GOV-ISO-001"]["observations"]["identifier_leak"])
            self.assertTrue(cases["GOV-ISO-001"]["observations"]["content_leak"])
            self.assertEqual(cases["GOV-ISO-002"]["result"], "fail")
            self.assertEqual(cases["GOV-ISO-005"]["result"], "fail")
            self.assertEqual(cases["GOV-AUTH-002"]["result"], "fail")
            self.assertEqual(cases["GOV-AUTH-003"]["result"], "fail")
            metrics = _metric_map(run)
            self.assertEqual(metrics["gov_iso_001"]["state"], "measured")
            self.assertEqual(metrics["gov_iso_001"]["value"], False)

    def test_cardinality_leak_fails_independently_of_content_and_identifier_isolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_gauntlet(
                FIXTURE_DIR / "governance-count-leak-adapter.json",
                GOVERNANCE_ALPHA_PROFILE_ID,
                output_dir=temporary,
            )
            self.assertEqual(result["status"], "complete")
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            cases = _case_map(run["native_results"])
            self.assertEqual(cases["GOV-ISO-001"]["result"], "pass")
            self.assertEqual(cases["GOV-ISO-002"]["result"], "pass")
            self.assertFalse(cases["GOV-ISO-001"]["observations"]["identifier_leak"])
            self.assertFalse(cases["GOV-ISO-001"]["observations"]["content_leak"])
            self.assertEqual(cases["GOV-ISO-005"]["result"], "fail")
            self.assertFalse(
                cases["GOV-ISO-005"]["observations"][
                    "caller_visible_result_stable_across_foreign_counts"
                ]
            )

    def test_claimed_durable_deletion_is_blocked_until_restart_lifecycle_is_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _load_fixture("governance-strict-adapter.json")
            manifest["capabilities"]["durable_deletion"] = {"support": "derived"}
            path = _write_manifest(root, manifest)
            result = run_gauntlet(path, GOVERNANCE_ALPHA_PROFILE_ID, output_dir=root / "runs")
            self.assertEqual(result["status"], "complete")
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            case = _case_map(run["native_results"])["GOV-DEL-002"]
            self.assertEqual(case["result"], "blocked")
            self.assertIn("restart/recovery lifecycle", case["note"])

    def test_claimed_injection_semantics_are_blocked_not_faked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _load_fixture("governance-strict-adapter.json")
            manifest["capabilities"]["route_authority_isolation"] = {"support": "derived"}
            manifest["capabilities"]["classifier_authority_isolation"] = {"support": "derived"}
            manifest["capabilities"]["source_trust"] = {"support": "derived"}
            path = _write_manifest(root, manifest)
            result = run_gauntlet(path, GOVERNANCE_ALPHA_PROFILE_ID, output_dir=root / "runs")
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            cases = _case_map(run["native_results"])
            for case_id in ("GOV-AUTH-004", "GOV-AUTH-005", "GOV-SRC-002"):
                self.assertEqual(cases[case_id]["result"], "blocked")
                self.assertIn("not yet part", cases[case_id]["note"])

    def test_external_deletion_claim_requires_broad_destructive_consent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _load_fixture("governance-strict-adapter.json")
            manifest["system"] = dict(manifest["system"], id="governance-external-consent")
            manifest["adapter"] = dict(
                manifest["adapter"], id="governance-external-consent-adapter"
            )
            manifest["metadata"] = {"provenance_class": "baseline_or_probe"}
            manifest["transport"] = {
                "kind": "stdio",
                "startup": [sys.executable, "definitely-not-executed.py"],
            }
            path = _write_manifest(root, manifest)

            blocked = run_gauntlet(
                path,
                GOVERNANCE_ALPHA_PROFILE_ID,
                output_dir=root / "runs-reset-only",
                allow_external_process=True,
                allow_destructive_reset=True,
            )
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(
                blocked["failure"]["code"], "destructive_operation_opt_in_required"
            )
            self.assertIn("forget", blocked["failure"]["message"])
            self.assertIn("--allow-destructive-operations", blocked["failure"]["message"])


if __name__ == "__main__":
    unittest.main()
