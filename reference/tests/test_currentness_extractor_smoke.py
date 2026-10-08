"""Offline contract tests for the #732 Claude subscription smoke harness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "smoke_currentness_extractor.py"


class CurrentnessExtractorSmokeTests(unittest.TestCase):
    def test_dry_run_binds_subscription_provider_without_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "smoke.json"
            env = os.environ.copy()
            for name in (
                "CLAUDE_CODE_OAUTH_TOKEN",
                "ANTHROPIC_API_KEY",
                "ANTHROPIC_AUTH_TOKEN",
            ):
                env.pop(name, None)
            env["PYTHONPATH"] = str(ROOT / "reference")
            subprocess.run(
                [sys.executable, str(SCRIPT), "--dry-run", "--output", str(out)],
                cwd=ROOT,
                env=env,
                check=True,
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(
                data["response"],
                {"status": "not_executed", "reason": "dry_run"},
            )
            self.assertEqual(data["extractor"]["provider"], "claude-code-cli")
            self.assertEqual(data["extractor"]["cli_version"], "2.1.294")
            self.assertEqual(data["extractor"]["model"], "claude-sonnet-5-5")
            self.assertEqual(
                data["extractor"]["extractor_version"],
                "1.0.0/claude-code-2.1.294/claude-sonnet-5-5/high/9974ab010b12",
            )
            self.assertIsNone(data["generalization_score"])
            self.assertFalse(data["synthetic_fixture"]["contains_user_data"])

    def test_live_mode_fails_closed_without_oauth_token(self):
        env = os.environ.copy()
        for name in (
            "CLAUDE_CODE_OAUTH_TOKEN",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        ):
            env.pop(name, None)
        env["PYTHONPATH"] = str(ROOT / "reference")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN is required", proc.stderr)

    def test_egress_denial_happens_before_any_process(self):
        from agentmem_ref.evaluation.claude_code_proposition_extractor import (
            ClaudeCodeCLIExtractor,
        )

        seen = []
        extractor = ClaudeCodeCLIExtractor(
            egress_policy=lambda payload: seen.append(json.loads(payload)) or False
        )
        with mock.patch("subprocess.run", side_effect=AssertionError("CLI invoked")):
            with self.assertRaises(PermissionError):
                extractor.extract(
                    "New endpoint: https://new.example.test",
                    [{"fact_uuid": "old", "text": "Secret old endpoint"}],
                )
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["candidates"][0]["text"], "Secret old endpoint")
        self.assertIn("new.example.test", seen[0]["new_text"])

    def test_candidate_budget_rejected_before_any_process(self):
        from agentmem_ref.evaluation.claude_code_proposition_extractor import (
            ClaudeCodeCLIExtractor,
        )
        from agentmem_ref.runtime import proposition_extraction as px

        extractor = ClaudeCodeCLIExtractor(egress_policy=lambda _payload: True)
        with mock.patch("subprocess.run", side_effect=AssertionError("CLI invoked")):
            with self.assertRaises(ValueError):
                extractor.extract(
                    "Test",
                    [{"fact_uuid": str(n), "text": "candidate"} for n in range(px.MAX_CANDIDATES + 1)],
                )

    def test_direct_api_credentials_are_refused_even_in_dry_run(self):
        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = "must-not-be-used"
        env["PYTHONPATH"] = str(ROOT / "reference")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--dry-run"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("direct Anthropic API credentials are forbidden", proc.stderr)


if __name__ == "__main__":
    unittest.main()
