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
                    ("A" * 8192 + "\n", "B" * 8192 + "\n"),
                )
                self.assertEqual(list(root.glob(".runtime-config.json.*.tmp")), [])
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.communicate()


    def test_simultaneous_fresh_runtime_initializers_leave_recoverable_root(self):
        """Two legitimate processes may race at the complete first-open boundary.

        Each can succeed or fail closed, but neither may publish partial config,
        and the resulting root must be recoverable with one canonical SQLite
        interpretation. This tests more than the helper-only writer barrier.
        """
        worker = """
import os, sys, time
from pathlib import Path
from agentmem_ref import AgentMemory
root = Path(sys.argv[1])
name = sys.argv[2]
(root / ("start-ready-" + name)).write_text("ready", encoding="utf-8")
deadline = time.monotonic() + 15
while not (root / "start-go").exists():
    if time.monotonic() > deadline:
        raise TimeoutError("missing start barrier")
    time.sleep(0.01)
try:
    runtime = AgentMemory.open(root)
except Exception as exc:
    print("REFUSED:" + type(exc).__name__)
else:
    try:
        print("OPENED")
    finally:
        runtime.close()
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            root.mkdir()
            environment = os.environ.copy()
            reference_dir = str(Path(__file__).resolve().parents[1])
            environment["PYTHONPATH"] = reference_dir + os.pathsep + environment.get("PYTHONPATH", "")
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", worker, str(root), name],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    env=environment,
                )
                for name in ("A", "B")
            ]
            try:
                deadline = time.monotonic() + 20
                while not all((root / ("start-ready-" + name)).exists() for name in ("A", "B")):
                    if any(p.poll() is not None for p in processes):
                        self.fail("first-open worker exited before synchronized start")
                    if time.monotonic() > deadline:
                        self.fail("first-open workers did not reach start barrier")
                    time.sleep(0.02)
                (root / "start-go").write_text("go", encoding="utf-8")
                outcomes = [p.communicate(timeout=30) for p in processes]
                for p, (stdout, stderr) in zip(processes, outcomes):
                    self.assertEqual(p.returncode, 0, (stdout, stderr))
                    self.assertTrue(stdout.strip() == "OPENED" or stdout.startswith("REFUSED:"), (stdout, stderr))
                self.assertTrue((root / "runtime-config.json").is_file())
                self.assertEqual(list(root.glob(".runtime-config.json.*.tmp")), [])
                with AgentMemory.open(root) as recovered:
                    self.assertTrue(recovered.remember("memory:recovery", "after concurrent startup")["committed"])
                    self.assertEqual(recovered.legacy_upgrade_status()["status"], "fresh")
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.kill()
                        p.communicate()

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
            # no staged file of any name survives, including the predictable legacy name
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["runtime-config.json"])

    def test_forced_two_creator_race_admits_exactly_one_initializer(self):
        """Deterministic form of the fresh-root race: both processes pass the database-exists
        check and both call the fresh-store creator. Exactly one may initialise the root; the
        other must fail closed; the survivor's write is durable and the root reopens cleanly."""
        worker = """
import sys, time
from pathlib import Path
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import sqlite_composition as composition
root = Path(sys.argv[1])
name = sys.argv[2]
real_create = composition.SQLiteConfiguredCompositionRuntime.create.__func__
def gated_create(cls, *args, **kwargs):
    (root / ("create-ready-" + name)).write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 20
    while not (root / "create-go").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("other initializer never reached the creator")
        time.sleep(0.005)
    return real_create(cls, *args, **kwargs)
composition.SQLiteConfiguredCompositionRuntime.create = classmethod(gated_create)
try:
    runtime = AgentMemory.open(root)
except Exception as exc:
    print("REFUSED:" + type(exc).__name__)
else:
    try:
        print("OPENED:" + str(runtime.remember("memory:" + name, "written by " + name)["committed"]))
    finally:
        runtime.close()
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            root.mkdir()
            environment = os.environ.copy()
            reference_dir = str(Path(__file__).resolve().parents[1])
            environment["PYTHONPATH"] = reference_dir + os.pathsep + environment.get("PYTHONPATH", "")
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", worker, str(root), name],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    env=environment,
                )
                for name in ("A", "B")
            ]
            try:
                deadline = time.monotonic() + 20
                while not all((root / ("create-ready-" + name)).exists() for name in ("A", "B")):
                    if any(p.poll() is not None for p in processes):
                        self.fail("an initializer exited before both reached the creator")
                    if time.monotonic() > deadline:
                        self.fail("initializers did not both reach the creator")
                    time.sleep(0.02)
                (root / "create-go").write_text("go", encoding="utf-8")
                outcomes = [p.communicate(timeout=30) for p in processes]
                results = []
                for p, (stdout, stderr) in zip(processes, outcomes):
                    self.assertEqual(p.returncode, 0, (stdout, stderr))
                    results.append(stdout.strip())
                self.assertEqual(sorted(r.split(":")[0] for r in results), ["OPENED", "REFUSED"], results)
                self.assertIn("OPENED:True", results)
                self.assertIn("REFUSED:RuntimeRecoveryError", results)
                self.assertEqual(list(root.glob(".runtime-config.json.*.tmp")), [])
                with AgentMemory.open(root) as recovered:
                    survivor = [n for n in ("A", "B") if recovered.history(f"memory:{n}")["history"]["current_fact_uuid"]]
                    self.assertEqual(len(survivor), 1, survivor)
                    self.assertEqual(recovered.legacy_upgrade_status()["status"], "fresh")
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.kill()
                        p.communicate()


if __name__ == "__main__":
    unittest.main()
