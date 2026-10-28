from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.evaluation.contract import load_run
from agentmem_ref.evaluation.gauntlet_orchestrator import run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import (
    DURABILITY_RECOVERY_PROFILE_ID,
    get_gauntlet_profile,
    list_gauntlet_profiles,
)

FIXTURE_DIR = REPO_ROOT / "fixtures" / "gauntlet"
REAL_MANIFEST = FIXTURE_DIR / "agent-memory-public-durability-adapter.json"
# v7 integration: the frozen v1 contestant recovers a second scope in its one store, which the
# #786 single_project_v1 profile refuses; its qualifying successor is the scope_distinct_v1 v2.
SUCCESSOR_MANIFEST = FIXTURE_DIR / "agent-memory-public-durability-adapter-v2.json"
LOSSY_MANIFEST = FIXTURE_DIR / "durability-lossy-recovery-adapter.json"


@contextlib.contextmanager
def _qualified_contestant_launch():
    """Launch the real stdio contestant under this harness's qualified interpreter.

    The frozen manifest starts ``python examples/gauntlet/...``: a bare PATH lookup
    and a repo-root-relative script. Whichever ``python`` is first on PATH (often a
    system interpreter without the pinned dependencies) otherwise dies on import and
    surfaces only as ``adapter_eof``, while the run records this interpreter's
    version as its environment. Pin both to the interpreter actually under test.
    """
    with tempfile.TemporaryDirectory() as shim:
        # A symlink would lose a virtual environment (pyvenv.cfg is found
        # relative to the invoked path), so prefer the interpreter's own
        # directory when its bare ``python`` is this interpreter.
        home = Path(sys.executable).parent
        bare = home / ("python.exe" if os.name == "nt" else "python")
        if bare.exists() and os.path.samefile(bare, sys.executable):
            search = str(home)
        elif os.name != "nt":
            launcher = Path(shim) / "python"
            launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
            launcher.chmod(0o755)
            search = shim
        else:
            search = str(home)
        path = search + os.pathsep + os.environ.get("PATH", "")
        previous = os.getcwd()
        with mock.patch.dict(os.environ, {"PATH": path}):
            os.chdir(REPO_ROOT)
            try:
                yield
            finally:
                os.chdir(previous)


def _case_map(run: dict) -> dict[str, dict]:
    return {case["case_id"]: case for case in run["native_results"]["cases"]}


def _metric_map(run: dict, dimension: str) -> dict[str, dict]:
    return {
        metric["metric_id"]: metric
        for metric in run["dimensions"][dimension]["metrics"]
    }


class DurabilityRecoveryGauntletTests(unittest.TestCase):
    def test_profile_is_discoverable_and_checkpoint_remains_optional(self):
        profile = get_gauntlet_profile(DURABILITY_RECOVERY_PROFILE_ID)
        self.assertEqual(profile["kind"], "gauntlet_native_gap")
        self.assertEqual(profile["destructive_operations"]["forget"], "durable_deletion")
        self.assertIn("recover", profile["requirements"]["requires"])
        self.assertIn("checkpoint", profile["requirements"]["optional"])
        self.assertIn("durable_correction", profile["requirements"]["optional"])
        ids = {item["profile_id"] for item in list_gauntlet_profiles()}
        self.assertIn(DURABILITY_RECOVERY_PROFILE_ID, ids)

    def test_real_agent_memory_contestant_requires_broad_destructive_consent(self):
        with tempfile.TemporaryDirectory() as temporary:
            blocked = run_gauntlet(
                REAL_MANIFEST,
                DURABILITY_RECOVERY_PROFILE_ID,
                output_dir=Path(temporary) / "runs",
                allow_external_process=True,
                allow_destructive_reset=True,
            )
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(
                blocked["failure"]["code"],
                "destructive_operation_opt_in_required",
            )
            self.assertIn("forget", blocked["failure"]["message"])
            self.assertIn("--allow-destructive-operations", blocked["failure"]["message"])

    def test_frozen_v1_contestant_is_stopped_only_at_wrong_scope_recovery(self):
        # Classification, not a pass: v1 is incompatible with #786 store profiles.
        with tempfile.TemporaryDirectory() as temporary, _qualified_contestant_launch():
            result = run_gauntlet(
                REAL_MANIFEST,
                DURABILITY_RECOVERY_PROFILE_ID,
                output_dir=Path(temporary) / "runs",
                allow_external_process=True,
                allow_destructive_operations=True,
            )
            self.assertEqual(result["status"], "complete", result)
            cases = _case_map(load_run(result["artifacts"]["normalized_run"]["path"]))
            isolation = cases["DUR-ISO-001"]
            self.assertEqual(isolation["behavioral_outcome"], "blocked", isolation)
            self.assertEqual(isolation["transition"], {"recover_right_scope": "ok", "recover_wrong_scope": "adapter_error"})
            for case_id in ("DUR-REC-001", "DUR-DEL-001", "DUR-DET-001"):
                self.assertEqual(cases[case_id]["behavioral_outcome"], "pass", cases[case_id])

    def test_real_agent_memory_public_facade_qualifies_first_durability_slice(self):
        with tempfile.TemporaryDirectory() as temporary, _qualified_contestant_launch():
            result = run_gauntlet(
                SUCCESSOR_MANIFEST,
                DURABILITY_RECOVERY_PROFILE_ID,
                output_dir=Path(temporary) / "runs",
                allow_external_process=True,
                allow_destructive_operations=True,
            )
            self.assertEqual(result["status"], "complete", result)
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            cases = _case_map(run)

            for case_id in (
                "DUR-REC-001",
                "DUR-DEL-001",
                "DUR-DET-001",
                "DUR-ISO-001",
            ):
                self.assertEqual(cases[case_id]["behavioral_outcome"], "pass", cases[case_id])
                self.assertEqual(
                    cases[case_id]["evidence_qualification"],
                    "sufficient",
                    cases[case_id],
                )
                self.assertIn("pre_state", cases[case_id])
                self.assertIn("transition", cases[case_id])
                self.assertIn("expected_boundary", cases[case_id])
                self.assertIn("post_state", cases[case_id])

            correction = cases["DUR-COR-001"]
            self.assertEqual(correction["behavioral_outcome"], "unsupported")
            self.assertEqual(correction["evidence_qualification"], "sufficient")
            self.assertFalse(correction["transition"]["operation_executed"])

            checkpoint = cases["DUR-CHK-001"]
            self.assertEqual(checkpoint["behavioral_outcome"], "unsupported")
            self.assertEqual(checkpoint["evidence_qualification"], "sufficient")
            self.assertFalse(checkpoint["transition"]["operation_executed"])

            self.assertEqual(run["native_results"]["profile_kind"], "gauntlet_native_gap")
            self.assertEqual(run["dimensions"]["governance"]["status"], "partial")
            self.assertEqual(run["authority_effect"], "none")
            self.assertIn(
                "not abrupt process-kill/crash recovery",
                " ".join(run["limitations"]),
            )

            behavior_metrics = _metric_map(run, "governance")
            self.assertEqual(behavior_metrics["dur_rec_001"]["value"], True)
            self.assertEqual(behavior_metrics["dur_cor_001"]["state"], "not_applicable")
            self.assertEqual(behavior_metrics["dur_chk_001"]["state"], "not_applicable")
            evidence_metrics = _metric_map(run, "evaluator_integrity")
            for case_id in (
                "dur_rec_001",
                "dur_del_001",
                "dur_cor_001",
                "dur_det_001",
                "dur_iso_001",
                "dur_chk_001",
            ):
                self.assertEqual(
                    evidence_metrics[f"{case_id}_evidence_sufficient"]["value"],
                    True,
                )

    def test_lossy_recovery_is_measured_failure_not_execution_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_gauntlet(
                LOSSY_MANIFEST,
                DURABILITY_RECOVERY_PROFILE_ID,
                output_dir=Path(temporary) / "runs",
            )
            self.assertEqual(result["status"], "complete", result)
            self.assertNotIn("failure", result)
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            cases = _case_map(run)

            recovery = cases["DUR-REC-001"]
            self.assertEqual(recovery["behavioral_outcome"], "fail")
            self.assertEqual(recovery["evidence_qualification"], "sufficient")
            self.assertTrue(recovery["pre_state"]["visible_before_recover"])
            self.assertFalse(recovery["post_state"]["visible_after_recover"])

            for case_id in (
                "DUR-DEL-001",
                "DUR-COR-001",
                "DUR-DET-001",
                "DUR-ISO-001",
                "DUR-CHK-001",
            ):
                self.assertEqual(cases[case_id]["behavioral_outcome"], "unsupported")
                self.assertEqual(cases[case_id]["evidence_qualification"], "sufficient")

            metrics = _metric_map(run, "governance")
            self.assertEqual(metrics["dur_rec_001"]["state"], "measured")
            self.assertEqual(metrics["dur_rec_001"]["value"], False)
            self.assertEqual(metrics["dur_del_001"]["state"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
