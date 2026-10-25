"""Logic of the Windows preflight and qualification runner that does not need Windows, plus the
guarantee that neither of them reports anything but NO-GO off native Windows."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

WINDOWS_DIR = Path(__file__).resolve().parents[1] / "windows"
sys.path.insert(0, str(WINDOWS_DIR))
import preflight  # noqa: E402
import qualify  # noqa: E402

VERBOSE = """test_a (test_bridge.BridgeTests.test_a) ... ok
test_junction (test_windows_native.NativeRootGuardTests.test_junction) ... skipped 'capability unavailable: symlink creation (1314)'
test_other (test_bridge.BridgeTests.test_other) ... skipped 'POSIX permission bits'
----------------------------------------------------------------------
Ran 3 tests in 0.1s

OK (skipped=2, expected failures=1)
"""


class ParsingTests(unittest.TestCase):
    def test_py_launcher_listing(self):
        listing = (" -V:3.13          C:\\Python313\\python.exe\n -V:3.12 *        C:\\Users\\u\\AppData\\Local\\Programs\\Python\\Python312\\python.exe\n"
                   " -V:3.11          C:\\Python311\\python.exe\n")
        self.assertEqual(preflight.parse_py_list(listing)["3.12"], "C:\\Users\\u\\AppData\\Local\\Programs\\Python\\Python312\\python.exe")
        self.assertEqual(sorted(preflight.parse_py_list(listing)), ["3.11", "3.12", "3.13"])

    def test_unittest_summary_and_native_skips_are_not_passes(self):
        result = qualify.parse_unittest(VERBOSE)
        self.assertEqual((result["ran"], result["ok"], result["expected_failures"]), (3, True, 1))
        self.assertEqual(len(result["skipped"]), 2)
        self.assertFalse(qualify.native_negatives_passed(result))
        clean = qualify.parse_unittest(VERBOSE.replace("skipped 'capability unavailable: symlink creation (1314)'", "ok"))
        self.assertTrue(qualify.native_negatives_passed(clean))
        failed = qualify.parse_unittest("Ran 2 tests in 0.1s\n\nFAILED (failures=1, errors=1)\n")
        self.assertEqual((failed["ok"], failed["failures"], failed["errors"]), (False, 1, 1))

    def test_redaction_covers_both_separators_and_case(self):
        text = r"C:\Dev\AM\venv-3.12\Scripts\python.exe and c:/dev/am/tmp"
        self.assertEqual(qualify.redact_text(text, [(r"C:\Dev\AM", "<DEV>")]), r"<DEV>\venv-3.12\Scripts\python.exe and <DEV>/tmp")

    def test_child_environment_drops_agent_memory_variables(self):
        os.environ["AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY"] = "memory:x"
        try:
            env = qualify.child_env(Path("/dev/tmp"), "/dev/claude")
        finally:
            os.environ.pop("AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY")
        self.assertFalse([k for k in env if k.upper().startswith("AGENT_MEMORY")])
        self.assertEqual((env["TEMP"], env["CLAUDE_CONFIG_DIR"]), ("/dev/tmp", "/dev/claude"))

    def test_overlap(self):
        self.assertTrue(preflight.overlaps(Path("/a/b"), Path("/a/b/c")))
        self.assertFalse(preflight.overlaps(Path("/a/b"), Path("/a/bc")))


@unittest.skipIf(os.name == "nt", "the non-Windows refusal")
class NotWindowsTests(unittest.TestCase):
    def test_preflight_and_runner_refuse_off_windows(self):
        with tempfile.TemporaryDirectory() as temp:
            for script, args in (("preflight.py", ["--dev-dir", temp]), ("qualify.py", ["--dev-dir", temp, "--python", "3.12"])):
                with self.subTest(script=script):
                    done = subprocess.run([sys.executable, str(WINDOWS_DIR / script), *args], capture_output=True, text=True)
                    self.assertEqual(done.returncode, 1)
                    self.assertIn("NO-GO", done.stdout)
            self.assertEqual(os.listdir(temp), [])


if __name__ == "__main__":
    unittest.main()
