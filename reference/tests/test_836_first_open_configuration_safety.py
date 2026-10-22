"""First-open configuration writer: adversarial regression controls for #836/#821.

These tests exercise the exact public facade helper, not a copied implementation.
They intentionally do not alter the frozen v7 declaration or acceptance records.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from agentmem_ref import AgentMemory
from agentmem_ref.api import surface


class FirstOpenConfigurationSafety(unittest.TestCase):
    def test_preplanted_legacy_temp_symlink_does_not_clobber_its_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            root.mkdir()
            victim = Path(directory) / "unrelated-sensitive.txt"
            victim.write_text("KEEP ME", encoding="utf-8")
            try:
                (root / ".runtime-config.json.tmp").symlink_to(victim)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            memory = AgentMemory.open(root)
            try:
                self.assertTrue((root / "runtime-config.json").is_file())
                self.assertEqual(victim.read_text(encoding="utf-8"), "KEEP ME")
                self.assertTrue((root / ".runtime-config.json.tmp").is_symlink())
            finally:
                memory.close()

    def test_two_simultaneous_writers_use_distinct_private_temporaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "runtime-config.json"
            payloads = ("A" * 8192, "B" * 8192)
            gate = threading.Barrier(2)
            touched: list[str] = []
            original = surface.os.replace
            errors: list[Exception] = []

            def pause_at_replace(source, destination):
                touched.append(str(source))
                gate.wait(timeout=10)
                return original(source, destination)

            def write(value):
                try:
                    surface._atomic_write_text(target, value)
                except Exception as exc:
                    errors.append(exc)

            with patch.object(surface.os, "replace", side_effect=pause_at_replace):
                threads = [threading.Thread(target=write, args=(v,)) for v in payloads]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=15)
                self.assertFalse(any(thread.is_alive() for thread in threads))

            self.assertEqual(errors, [])
            self.assertEqual(len(set(touched)), 2)
            self.assertIn(target.read_text(encoding="utf-8"), tuple(p + "\n" for p in payloads))
            self.assertEqual(list(root.glob(".runtime-config.json.*.tmp")), [])

    def test_two_separate_processes_never_share_staging_inode(self):
        # The original fixed-temp regression was an inter-process truncation race.
        # Both children reach the rename boundary before either may publish.
        worker = """
import os, sys, time
from pathlib import Path
from agentmem_ref.api import surface
root = Path(sys.argv[1])
name = sys.argv[2]
real_replace = os.replace
def synchronized_replace(source, target):
    (root / ("ready-" + name)).write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 12
    while not (root / "go").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("other writer never reached the replace boundary")
        time.sleep(0.01)
    return real_replace(source, target)
surface.os.replace = synchronized_replace
surface._atomic_write_text(root / "runtime-config.json", name * 8192)
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = os.environ.copy()
            reference_dir = str(Path(__file__).resolve().parents[1])
            environment["PYTHONPATH"] = reference_dir + os.pathsep + environment.get("PYTHONPATH", "")
            children = [
                subprocess.Popen(
                    [sys.executable, "-c", worker, str(root), name],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    env=environment,
                )
                for name in ("A", "B")
            ]
            try:
                deadline = time.monotonic() + 15
                while not all((root / ("ready-" + name)).exists() for name in ("A", "B")):
                    if any(child.poll() is not None for child in children):
                        self.fail("a writer exited before both reached the synchronization point")
                    if time.monotonic() > deadline:
                        self.fail("two writers never reached the synchronization point")
                    time.sleep(0.02)
                (root / "go").write_text("go", encoding="utf-8")
                outcomes = [child.communicate(timeout=15) for child in children]
                for child, (out, err) in zip(children, outcomes):
                    self.assertEqual(child.returncode, 0, (out, err))
                self.assertIn(
                    (root / "runtime-config.json").read_text(encoding="utf-8"),
                    ("A" * 8192 + "\\n", "B" * 8192 + "\\n"),
                )
                self.assertEqual(list(root.glob(".runtime-config.json.*.tmp")), [])
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.communicate()

    def test_replace_failure_removes_only_own_temp_and_preserves_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "runtime-config.json"
            target.write_text("ORIGINAL", encoding="utf-8")
            bystander = root / ".runtime-config.json.tmp"
            bystander.write_text("UNRELATED", encoding="utf-8")
            with patch.object(surface.os, "replace", side_effect=OSError("denied")):
                with self.assertRaisesRegex(OSError, "denied"):
                    surface._atomic_write_text(target, "NEW")
            self.assertEqual(target.read_text(encoding="utf-8"), "ORIGINAL")
            self.assertEqual(bystander.read_text(encoding="utf-8"), "UNRELATED")
            self.assertEqual(list(root.glob(".runtime-config.json.*.tmp")), [])

    def test_fsync_failure_never_publishes_incomplete_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "runtime-config.json"
            target.write_text("ORIGINAL", encoding="utf-8")
            with patch.object(surface.os, "fsync", side_effect=OSError("disk failure")):
                with self.assertRaisesRegex(OSError, "disk failure"):
                    surface._atomic_write_text(target, "NEW")
            self.assertEqual(target.read_text(encoding="utf-8"), "ORIGINAL")
            self.assertEqual(list(root.glob(".runtime-config.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
