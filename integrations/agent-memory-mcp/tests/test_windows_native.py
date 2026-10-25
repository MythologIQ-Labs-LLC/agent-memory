"""Native Windows security negatives: real NTFS junctions, symlinks and ACLs, no mocks.

Every test here is skipped off Windows. On Windows, a test whose OS capability is missing (for
example creating a symlink without Developer Mode or the symlink privilege) is skipped with a
reason starting "capability unavailable"; the qualification runner counts every skip in this
module as NOT passed. Each test works only inside its own disposable temporary directory.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import bridge  # noqa: E402
import hostenv  # noqa: E402

WINDOWS = os.name == "nt"
HOST = {"AGENT_MEMORY_MCP_TENANT": "tenant:win-native", "AGENT_MEMORY_MCP_ACTOR": "agent:win-native",
        "AGENT_MEMORY_MCP_SCOPE": "project:win-native"}


def junction(link: Path, target: Path) -> None:
    """mklink /J needs no elevation; failure is a real failure, not a missing capability."""
    done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
    if done.returncode != 0:
        raise AssertionError(f"could not create an NTFS junction: {done.stderr!r}")


def symlink_or_skip(link: Path, target: Path, *, directory: bool) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:  # no SeCreateSymbolicLinkPrivilege and no Developer Mode
        raise unittest.SkipTest(f"capability unavailable: symlink creation ({exc.winerror if hasattr(exc, 'winerror') else exc})")


def files_under(path: Path) -> list[str]:
    return sorted(str(p.relative_to(path)) for p in path.rglob("*"))


@unittest.skipUnless(WINDOWS, "native Windows only")
class NativeRootGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="am-win-native-"))
        self.addCleanup(lambda: subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(self.temp)], capture_output=True))

    def host_config(self, root: Path):
        with patch.dict(os.environ, {"AGENT_MEMORY_MCP_ROOT": str(root), **HOST}):
            return bridge.HostConfig.from_environment()

    def test_temp_volume_is_ntfs_on_a_fixed_drive(self):
        import ctypes
        drive = self.temp.drive
        self.assertEqual(bridge._drive_type(drive), 3)
        name = ctypes.create_unicode_buffer(64)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(drive + "\\", None, 0, None, None, None, name, 64)
        self.assertTrue(ok)
        self.assertEqual(name.value, "NTFS")

    def test_plain_local_root_is_accepted(self):
        self.assertEqual(self.host_config(self.temp / "store").root, self.temp / "store")

    def test_junctioned_ancestor_is_refused_and_nothing_is_written_behind_it(self):
        target = self.temp / "elsewhere"
        target.mkdir()
        junction(self.temp / "jn", target)
        with self.assertRaisesRegex(ValueError, "junction"):
            self.host_config(self.temp / "jn" / "store")
        self.assertEqual(files_under(target), [])

    def test_junction_as_the_root_itself_is_refused(self):
        target = self.temp / "elsewhere"
        target.mkdir()
        junction(self.temp / "store", target)
        with self.assertRaisesRegex(ValueError, "junction"):
            self.host_config(self.temp / "store")

    def test_directory_symlink_ancestor_is_refused(self):
        target = self.temp / "elsewhere"
        target.mkdir()
        symlink_or_skip(self.temp / "ln", target, directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.host_config(self.temp / "ln" / "store")
        self.assertEqual(files_under(target), [])

    def test_unc_and_ads_and_device_roots_are_refused(self):
        for raw in (r"\\localhost\C$\am-store", str(self.temp / "store:ads"), str(self.temp / "NUL" / "store")):
            with self.subTest(root=raw), patch.dict(os.environ, {"AGENT_MEMORY_MCP_ROOT": raw, **HOST}):
                with self.assertRaises(ValueError):
                    bridge.HostConfig.from_environment()

    def test_real_mcp_call_through_a_junctioned_root_is_a_tool_error_without_writing(self):
        from mcp import Client, StdioServerParameters
        target = self.temp / "elsewhere"
        target.mkdir()
        junction(self.temp / "jn", target)
        env = {**hostenv.minimal_os_env(temp_dir=self.temp), "AGENT_MEMORY_MCP_ROOT": str(self.temp / "jn" / "store"), **HOST}

        async def call():
            async with Client(StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")], env=env)) as client:
                return await client.call_tool("memory_remember", {"key": "memory:win:x", "text": "Fictional."})
        result = asyncio.run(call())
        self.assertTrue(result.is_error)
        self.assertEqual(files_under(target), [])


@unittest.skipUnless(WINDOWS, "native Windows only")
class NativeCorrectionRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="am-win-record-"))
        self.addCleanup(lambda: subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(self.temp)], capture_output=True))
        self.real = self.temp / "real"
        self.real.mkdir()
        self.record = self.real / "record.json"
        self.record.write_text(json.dumps({"key": "memory:win:x", "text": "Fictional."}), encoding="utf-8")

    def test_plain_record_is_read(self):
        self.assertIsNotNone(bridge._read_correction_record(self.record, "memory:win:x", "Fictional."))

    def test_record_under_a_junction_is_refused(self):
        junction(self.temp / "jn", self.real)
        self.assertIsNone(bridge._read_correction_record(self.temp / "jn" / "record.json", "memory:win:x", "Fictional."))

    def test_record_that_is_a_file_symlink_is_refused(self):
        link = self.temp / "link.json"
        symlink_or_skip(link, self.record, directory=False)
        self.assertIsNone(bridge._read_correction_record(link, "memory:win:x", "Fictional."))


@unittest.skipUnless(WINDOWS, "native Windows only")
class NativeAclTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="am-win-acl-"))
        self.addCleanup(lambda: subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(self.temp)], capture_output=True))

    def test_private_dir_and_file_are_limited_to_the_user_and_system(self):
        d = hostenv.private_dir(self.temp / "run")
        f = hostenv.private_file(d / "record.json", b"{}")
        hostenv.verify_private(d, directory=True)
        hostenv.verify_private(f, directory=False)

    def test_a_directory_open_to_users_is_not_private(self):
        d = self.temp / "open"
        d.mkdir()
        subprocess.run(["icacls", str(d), "/grant", "*S-1-5-32-545:(OI)(CI)R"], capture_output=True, check=True)
        with self.assertRaises(hostenv.IsolationError):
            hostenv.verify_private(d, directory=True)


@unittest.skipUnless(WINDOWS, "native Windows only")
class NativeProcessTests(unittest.TestCase):
    def test_process_inspection_is_available(self):
        self.assertIsNotNone(hostenv.processes_with("agent-memory-no-such-process-fragment"))


if __name__ == "__main__":
    unittest.main()
