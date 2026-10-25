"""Portable host isolation helpers (hostenv.py). Windows-only branches are tested here through
pure functions and injected platform inputs; the native NTFS checks run in test_windows_native.py
on Windows only, and a skip there is not a pass."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hostenv

USER = "S-1-5-21-1111-2222-3333-1001"


class MinimalEnvironmentTests(unittest.TestCase):
    def test_posix_gets_a_fixed_path_and_nothing_else(self):
        self.assertEqual(hostenv.minimal_os_env(platform="posix", environ={"SECRET": "x", "PATH": "/evil"}),
                         {"PATH": "/usr/bin:/bin"})

    def test_windows_gets_what_python_and_winsock_need_and_a_private_temp(self):
        env = hostenv.minimal_os_env(platform="nt", environ={"SYSTEMROOT": r"C:\Windows", "API_TOKEN": "x",
                                                             "PATHEXT": ".COM;.EXE", "PATH": r"C:\evil"},
                                     temp_dir=r"C:\dev\run\tmp")
        self.assertEqual(env, {"SYSTEMROOT": r"C:\Windows", "WINDIR": r"C:\Windows",
                               "PATH": r"C:\Windows\System32;C:\Windows", "PATHEXT": ".COM;.EXE",
                               "TEMP": r"C:\dev\run\tmp", "TMP": r"C:\dev\run\tmp"})

    def test_windows_without_systemroot_or_temp_fails_closed(self):
        with self.assertRaises(hostenv.IsolationError):
            hostenv.minimal_os_env(platform="nt", environ={}, temp_dir=r"C:\t")
        with self.assertRaises(hostenv.IsolationError):
            hostenv.minimal_os_env(platform="nt", environ={"SYSTEMROOT": r"C:\Windows"})


class SddlTests(unittest.TestCase):
    def test_protected_dacl_for_the_user_and_system_is_private(self):
        sddl = f"D:PAI(A;OICI;FA;;;{USER})(A;OICI;FA;;;SY)"
        self.assertTrue(hostenv.dacl_is_private(sddl, USER, directory=True))

    def test_broad_or_foreign_principals_are_not_private(self):
        for extra in ("(A;OICI;0x1200a9;;;BU)", "(A;;FA;;;WD)", "(A;OICI;FA;;;AU)", "(A;OICI;FA;;;S-1-5-21-9-9-9-500)",
                      "(A;OICI;FA;;;BA)"):
            with self.subTest(extra=extra):
                self.assertFalse(hostenv.dacl_is_private(f"D:PAI(A;OICI;FA;;;{USER}){extra}", USER, directory=True))

    def test_an_inheriting_directory_dacl_or_a_missing_dacl_is_not_private(self):
        self.assertFalse(hostenv.dacl_is_private(f"D:AI(A;OICI;FA;;;{USER})", USER, directory=True))
        self.assertFalse(hostenv.dacl_is_private("O:SYG:SY", USER, directory=True))
        self.assertFalse(hostenv.dacl_is_private("D:P", USER, directory=True))

    def test_a_file_inheriting_from_a_private_directory_is_private(self):
        self.assertTrue(hostenv.dacl_is_private(f"D:AI(A;ID;FA;;;{USER})(A;ID;FA;;;SY)", USER, directory=False))

    def test_deny_aces_do_not_widen_access(self):
        self.assertTrue(hostenv.dacl_is_private(f"D:PAI(D;;FA;;;WD)(A;OICI;FA;;;{USER})", USER, directory=True))

    def test_icacls_save_output_is_decoded(self):
        saved = ("run\r\n" + f"D:PAI(A;OICI;FA;;;{USER})(A;OICI;FA;;;SY)\r\n").encode("utf-16")
        self.assertEqual(hostenv.sddl_from_icacls_save(saved), f"D:PAI(A;OICI;FA;;;{USER})(A;OICI;FA;;;SY)")


class PrivateDirectoryTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_posix_private_directory_and_file(self):
        with tempfile.TemporaryDirectory() as temp:
            d = hostenv.private_dir(Path(temp) / "run")
            self.assertEqual(d.stat().st_mode & 0o777, 0o700)
            f = d / "record.json"
            hostenv.private_file(f, b"{}")
            self.assertEqual(f.stat().st_mode & 0o777, 0o600)
            hostenv.verify_private(d, directory=True)
            hostenv.verify_private(f, directory=False)

    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_posix_group_or_world_access_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp) / "open"
            d.mkdir()
            os.chmod(d, 0o750)
            with self.assertRaises(hostenv.IsolationError):
                hostenv.verify_private(d, directory=True)


class ProcessProbeTests(unittest.TestCase):
    def test_finds_a_process_by_a_literal_command_line_fragment_then_not_after_exit(self):
        marker = f"/no/such/dir/agent-memory-probe-{os.getpid()}-[x].py"
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", marker])
        try:
            found = hostenv.processes_with(marker)
            self.assertIsNotNone(found, "process inspection unavailable on this platform")
            self.assertIn(child.pid, found)
        finally:
            child.kill()
            child.wait()
        deadline = time.time() + 5
        while hostenv.processes_with(marker) and time.time() < deadline:
            time.sleep(0.2)
        self.assertEqual(hostenv.processes_with(marker), [])


class CommandTests(unittest.TestCase):
    def test_batch_launchers_refuse_cmd_metacharacters(self):
        for bad in ('a"b', "a&b", "a|b", "a<b", "a>b", "a^b", "%PATH%", "a!b", "a\nb"):
            with self.subTest(arg=bad), self.assertRaises(hostenv.IsolationError):
                hostenv.assert_launchable([r"C:\npm\claude.cmd", "-p", bad])
        hostenv.assert_launchable([r"C:\npm\claude.cmd", "-p", "--mcp-config", r"C:\dev\run\S01-mcp.json"])
        hostenv.assert_launchable(["/usr/bin/claude", 'a"&|b'])

    def test_missing_cli_fails_closed(self):
        with self.assertRaises(hostenv.IsolationError):
            hostenv.resolve_cli("agent-memory-no-such-cli-xyz")


if __name__ == "__main__":
    unittest.main()
