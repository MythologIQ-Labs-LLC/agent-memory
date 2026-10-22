"""#821 follow-up: ``save_config`` stages through a temporary only it can open.

Up to ``5ca4bc5b`` it wrote ``config.tmp`` (``with_suffix``), then chmodded and renamed it. A symlink
planted at that name was followed by both the write and the chmod, so a file elsewhere was
overwritten and made 0600; a FIFO there blocked; a failed rename left the temporary behind. Tests
marked FAIL-FIRST fail on ``5ca4bc5b``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from agent_memory_hermes.config import IntegrationConfig, config_path, save_config

SOURCE = Path(sys.modules["agent_memory_hermes.config"].__file__).resolve().parents[1]
CONFIG = IntegrationConfig(mode="observe")


class SaveConfigTemporary(unittest.TestCase):
    def setUp(self) -> None:
        self._folder = tempfile.TemporaryDirectory()
        self.addCleanup(self._folder.cleanup)
        self.base = Path(self._folder.name)
        self.home = self.base / "home"
        self.path = config_path(self.home)
        self.path.parent.mkdir(parents=True)

    def temporaries(self) -> list[str]:
        return sorted(p.name for p in self.path.parent.iterdir() if p.name != self.path.name)

    def assert_saved(self) -> None:
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), CONFIG.to_dict())
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_a_symlink_at_the_old_fixed_name_is_never_followed(self):  # FAIL-FIRST
        target = self.base / "outside.txt"
        target.write_text("must not change\n")
        target.chmod(0o644)
        os.symlink(target, self.path.with_suffix(".tmp"))
        save_config(self.home, CONFIG)
        self.assertEqual(target.read_text(), "must not change\n")
        self.assertEqual(target.stat().st_mode & 0o777, 0o644)
        self.assert_saved()

    def test_a_fifo_at_the_old_fixed_name_does_not_block(self):  # FAIL-FIRST
        os.mkfifo(self.path.with_suffix(".tmp"))
        script = (
            "import sys; sys.path.insert(0, sys.argv[1]);"
            "from agent_memory_hermes.config import IntegrationConfig, save_config;"
            "save_config(sys.argv[2], IntegrationConfig(mode='observe'))"
        )
        try:
            done = subprocess.run([sys.executable, "-c", script, str(SOURCE), str(self.home)],
                                  capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired:
            self.fail("save_config blocked on a FIFO at its old temporary name")
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        self.assert_saved()

    def test_a_failed_rename_removes_the_temporary_and_keeps_the_previous_config(self):  # FAIL-FIRST
        self.path.write_text("previous\n")
        with mock.patch("os.replace", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                save_config(self.home, CONFIG)
        self.assertEqual(self.path.read_text(), "previous\n")
        self.assertEqual(self.temporaries(), [])

    def test_another_writer_temporary_is_never_opened_or_truncated(self):
        taken = self.path.with_name(f".{self.path.name}.{os.getpid()}.{'0' * 16}.tmp")
        taken.write_bytes(b"another writer's bytes")
        tokens = iter(["0" * 16, "1" * 16])
        with mock.patch("secrets.token_hex", lambda _n: next(tokens)):
            save_config(self.home, CONFIG)
        self.assertEqual(taken.read_bytes(), b"another writer's bytes")
        self.assertEqual(self.temporaries(), [taken.name])
        self.assert_saved()

    def test_the_config_is_0600_whatever_the_umask(self):
        previous = os.umask(0)
        try:
            save_config(self.home, CONFIG)
        finally:
            os.umask(previous)
        self.assert_saved()


if __name__ == "__main__":
    unittest.main()
