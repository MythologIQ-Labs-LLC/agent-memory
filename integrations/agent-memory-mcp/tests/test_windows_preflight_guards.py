"""Portable regression tests for W1 fail-closed admission guards."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

WINDOWS_DIR = Path(__file__).resolve().parents[1] / "windows"
sys.path.insert(0, str(WINDOWS_DIR))
import preflight  # noqa: E402


class IntegrityLevelTests(unittest.TestCase):
    def test_failed_inspection_is_unknown_not_non_elevated(self):
        with patch.object(preflight, "run", return_value=(-1, "Access denied")):
            self.assertIsNone(preflight.elevated())

    def test_missing_integrity_sid_is_unknown(self):
        with patch.object(preflight, "run", return_value=(0, "BUILTIN\\Users")):
            self.assertIsNone(preflight.elevated())

    def test_medium_is_not_elevated(self):
        with patch.object(preflight, "run", return_value=(0, "Mandatory Label\\Medium Mandatory Level S-1-16-8192")):
            self.assertIs(preflight.elevated(), False)

    def test_high_and_system_are_elevated(self):
        for level in (12288, 16384):
            with self.subTest(level=level), patch.object(preflight, "run", return_value=(0, f"S-1-16-{level}")):
                self.assertIs(preflight.elevated(), True)


class ClaudeConfigBaselineTests(unittest.TestCase):
    def test_default_config_is_snapshotted_with_isolated_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            default = root / "default.json"
            isolated = root / "isolated.json"
            default.write_text("before", encoding="utf-8")
            isolated.write_text("isolated", encoding="utf-8")
            with patch.object(preflight, "claude_config_files", side_effect=lambda config: [isolated] if config else [default]):
                before = preflight.config_snapshot(root)
                default.write_text("modified", encoding="utf-8")
                after = preflight.config_snapshot(root)
            self.assertNotEqual(before["default"], after["default"])
            self.assertEqual(before["isolated"], after["isolated"])

    def test_default_only_snapshot_is_present_without_isolation(self):
        with patch.object(preflight, "claude_config_files", return_value=[]):
            self.assertEqual(preflight.config_snapshot(None), {"default": {}, "isolated": {}})



class IsolatedConfigPathTests(unittest.TestCase):
    def test_only_strict_child_of_dev_root_is_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            dev = Path(folder) / "dev"
            inside = dev / "claude-config"
            sibling = Path(folder) / "other"
            self.assertTrue(preflight.is_strict_child(inside, dev))
            self.assertFalse(preflight.is_strict_child(dev, dev))
            self.assertFalse(preflight.is_strict_child(sibling, dev))
            self.assertFalse(preflight.is_strict_child(Path(folder), dev))


if __name__ == "__main__":
    unittest.main()
