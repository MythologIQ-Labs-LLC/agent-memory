"""#662: no-hosted-CI local preflight must be explicit and non-authoritative."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import run_finops_local_preflight as preflight  # noqa: E402


class LocalFinOpsPreflightTests(unittest.TestCase):
    def test_modes_have_no_network_or_actions_dispatch(self):
        quick = preflight.test_commands("quick")
        full = preflight.test_commands("full")
        self.assertEqual([x[0] for x in quick], [
            "workflow_policy_and_retention", "focused_workflow_policy_tests"
        ])
        self.assertEqual([x[0] for x in full], [
            "workflow_policy_and_retention", "complete_reference_regression",
            "repository_compatibility_tests",
        ])
        for mode in (quick, full):
            for _name, args in mode:
                self.assertEqual(args[0], sys.executable)
                self.assertFalse(any(
                    token in {"gh", "curl", "workflow_dispatch", "git", "ssh"}
                    for token in args
                ))
        with self.assertRaises(ValueError):
            preflight.test_commands("release")

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"})
    def test_never_executed_by_hosted_actions(self):
        with self.assertRaisesRegex(ValueError, "must not run"):
            preflight.run_preflight("quick")

    @patch.object(preflight, "local_git")
    def test_dirty_revision_requires_explicit_exception(self, git):
        git.side_effect = ["a" * 40, "quiet-branch", " M file.py"]
        with self.assertRaisesRegex(ValueError, "dirty"):
            preflight.run_preflight("quick")

    @patch.object(preflight, "local_git")
    @patch.object(preflight, "test_commands")
    @patch.object(preflight.subprocess, "run")
    def test_local_receipt_fails_closed_on_first_exit(self, run, commands, git):
        git.side_effect = ["a" * 40, "finops/staging", ""]
        commands.return_value = [
            ("first", [sys.executable, "fake-one.py"]),
            ("second", [sys.executable, "fake-two.py"]),
        ]
        run.return_value = subprocess.CompletedProcess(
            args=["fake-one.py"], returncode=3, stdout="", stderr="synthetic failure"
        )
        report = preflight.run_preflight("quick")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(len(report["steps"]), 1)
        self.assertEqual(report["steps"][0]["exit_code"], 3)
        self.assertNotIn("stderr_tail", report["steps"][0])
        self.assertFalse(report["external_qualification"])
        self.assertFalse(report["billed_minutes_known"])
        self.assertFalse(report["branch_protection_verified"])
        self.assertEqual(report["github_actions_dispatches"], 0)
        self.assertEqual(report["authority_effect"], "none")
        self.assertEqual(run.call_count, 1)

    @patch.object(preflight, "local_git")
    @patch.object(preflight, "test_commands")
    @patch.object(preflight.subprocess, "run")
    def test_green_local_receipt_never_grants_release(self, run, commands, git):
        git.side_effect = ["b" * 40, "finops/staging", ""]
        commands.return_value = [
            ("policy", [sys.executable, "fake.py"]),
        ]
        run.return_value = subprocess.CompletedProcess(
            args=["fake.py"], returncode=0, stdout="ok", stderr=""
        )
        report = preflight.run_preflight("full")
        self.assertEqual(report["status"], "passed_local_only")
        self.assertTrue(report["worktree_clean"])
        self.assertEqual(report["repo_head_sha"], "b" * 40)
        self.assertFalse(report["external_qualification"])
        self.assertFalse(report["branch_protection_verified"])
        self.assertEqual(report["authority_effect"], "none")
        self.assertNotIn("stdout_tail", report["steps"][0])


if __name__ == "__main__":
    unittest.main()
