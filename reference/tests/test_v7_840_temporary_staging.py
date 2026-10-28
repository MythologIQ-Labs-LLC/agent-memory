"""#840 on the integrated v7 candidate: whole-file writes stage through exclusive, unpredictable temporaries.

Preregistered in reports/validation/v7-integration/840-temporary-staging/PREREGISTRATION.md (S1-S6, I1-I4).
An actor that can only create directory entries in a store must not redirect, truncate or tear a store write;
concurrent writers and a crash or ENOSPC between create and rename must not either.
"""
from __future__ import annotations

import errno
import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from agentmem_ref import AgentMemory
from agentmem_ref.api import surface
from agentmem_ref.memory import checkpoint_migration
from agentmem_ref.runtime import checkpoint_transactions, configured_restart, restart_runtime
from agentmem_ref.runtime.sqlite_composition import SQLiteConfiguredCompositionRuntime

VICTIM = b"victim bytes outside the store\n"


def _surface(path: Path, n: int) -> bytes:
    text = json.dumps({"writer": "surface", "n": n})
    surface._atomic_write_text(path, text)
    return (text + "\n").encode()


def _json_writer(module):
    def write(path: Path, n: int) -> bytes:
        value = {"writer": module.__name__, "n": n}
        module._atomic_json_write(path, value)
        return module._canonical_bytes(value) + b"\n"
    return write


def _journal(path: Path, n: int) -> bytes:
    records = ({"writer": "journal", "n": n}, {"writer": "journal", "n": n + 1})
    support = SimpleNamespace(_store=SimpleNamespace(journal_path=path))
    checkpoint_transactions.CheckpointTransactionSupport._atomic_journal_write(support, records)
    return b"".join(restart_runtime._canonical_bytes(dict(r)) + b"\n" for r in records)


WRITERS = {
    "surface._atomic_write_text": _surface,
    "restart_runtime._atomic_json_write": _json_writer(restart_runtime),
    "configured_restart._atomic_json_write": _json_writer(configured_restart),
    "checkpoint_migration._atomic_json_write": _json_writer(checkpoint_migration),
    "checkpoint_transactions._atomic_journal_write": _journal,
}

_real_fsync = os.fsync
_real_replace = os.replace


def _is_regular(fd: int) -> bool:
    return stat.S_ISREG(os.fstat(fd).st_mode)


def _predictable_names(path: Path) -> list[Path]:
    """Every temporary name the pre-repair writers derive from the target, pid and thread."""
    return [path.with_name(f".{path.name}.tmp"),
            path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")]


class _Dirs(unittest.TestCase):
    def setUp(self):
        self._store = tempfile.TemporaryDirectory()
        self._outside = tempfile.TemporaryDirectory()
        self.store = Path(self._store.name)
        self.victim = Path(self._outside.name) / "victim.txt"
        self.victim.write_bytes(VICTIM)

    def tearDown(self):
        self._store.cleanup()
        self._outside.cleanup()

    def leftovers(self, keep: set[str], directory: Path | None = None) -> list[str]:
        return sorted(p.name for p in (directory or self.store).iterdir() if p.name not in keep)

    def target(self, writer: str) -> Path:
        """Each writer stages in its own directory, so one writer's leak is never another's."""
        directory = self.store / writer
        directory.mkdir()
        return directory / "record.json"


class WriterStagingTests(_Dirs):
    def test_s1_planted_symlinks_are_never_followed(self):
        for name, write in WRITERS.items():
            with self.subTest(writer=name):
                target = self.target(name)
                planted = _predictable_names(target)
                for link in planted:
                    link.symlink_to(self.victim)
                payload = write(target, 1)
                self.assertEqual(self.victim.read_bytes(), VICTIM, "a planted temporary redirected the write")
                self.assertFalse(target.is_symlink())
                self.assertEqual(target.read_bytes(), payload)
                for link in planted:
                    link.unlink(missing_ok=True)

    def test_s2_temporary_names_are_unpredictable(self):
        for name, write in WRITERS.items():
            with self.subTest(writer=name):
                target = self.target(name)
                staged = []

                def recording_replace(src, dst, *a, **kw):
                    staged.append(Path(src).name)
                    return _real_replace(src, dst, *a, **kw)

                with mock.patch("os.replace", recording_replace):
                    write(target, 1)
                    write(target, 2)
                self.assertEqual(len(staged), 2, staged)
                self.assertNotEqual(staged[0], staged[1], "one thread reused a predictable temporary")
                for candidate in _predictable_names(target):
                    self.assertNotIn(candidate.name, staged)

    def test_s3_concurrent_writers_publish_one_complete_record(self):
        writers = 6
        for name, write in WRITERS.items():
            with self.subTest(writer=name):
                target = self.target(name)
                barrier = threading.Barrier(writers, timeout=3)
                errors, payloads = [], {}

                def held_fsync(fd):
                    if _is_regular(fd):
                        try:
                            barrier.wait()  # every writer has staged before any renames
                        except threading.BrokenBarrierError:
                            pass
                    return _real_fsync(fd)

                def run(n):
                    try:
                        payloads[n] = write(target, n * 10)
                    except BaseException as exc:  # noqa: BLE001 - the failure is the observation
                        errors.append(f"{type(exc).__name__}: {exc}")

                with mock.patch("os.fsync", held_fsync):
                    threads = [threading.Thread(target=run, args=(n,)) for n in range(writers)]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(10)
                self.assertEqual(errors, [])
                self.assertIn(target.read_bytes(), set(payloads.values()))
                self.assertEqual(self.leftovers({target.name}, target.parent), [])

    def test_s4_fsync_failure_keeps_the_previous_record_and_no_temporary(self):
        def enospc(fd):
            if _is_regular(fd):
                raise OSError(errno.ENOSPC, "No space left on device")
            return _real_fsync(fd)

        for name, write in WRITERS.items():
            with self.subTest(writer=name):
                target = self.target(name)
                before = write(target, 1)
                with mock.patch("os.fsync", enospc), self.assertRaises(OSError):
                    write(target, 2)
                self.assertEqual(target.read_bytes(), before)
                self.assertEqual(self.leftovers({target.name}, target.parent), [])

    def test_s5_replace_failure_keeps_the_previous_record_and_no_temporary(self):
        def failing_replace(src, dst, *a, **kw):
            raise OSError(errno.EIO, "replace failed")

        for name, write in WRITERS.items():
            with self.subTest(writer=name):
                target = self.target(name)
                before = write(target, 1)
                with mock.patch("os.replace", failing_replace), self.assertRaises(OSError):
                    write(target, 2)
                self.assertEqual(target.read_bytes(), before)
                self.assertEqual(self.leftovers({target.name}, target.parent), [])

    def test_s6_published_file_mode_is_unchanged(self):
        previous = os.umask(0o022)
        try:
            for name, write in WRITERS.items():
                with self.subTest(writer=name):
                    target = self.target(name)
                    write(target, 1)
                    self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o666 & ~0o022)
        finally:
            os.umask(previous)


class InterruptedInitializationTests(_Dirs):
    TENANT, ACTOR = "tenant:840", "agent:840"

    def open(self, scope="project:a"):
        return AgentMemory.open(self.store, tenant=self.TENANT, actor_id=self.ACTOR, scope=scope, purpose="840")

    def durable_names(self) -> set[str]:
        return {p.name for p in self.store.iterdir() if not p.name.startswith(".")}

    def test_i1_interrupted_configuration_write_retries_cleanly(self):
        def enospc(fd):
            if _is_regular(fd):
                raise OSError(errno.ENOSPC, "No space left on device")
            return _real_fsync(fd)

        with mock.patch("os.fsync", enospc), self.assertRaises(OSError):
            self.open()
        self.assertEqual(self.leftovers(set()), [], "an interrupted first open left a temporary behind")
        with self.open() as memory:
            memory.remember("memory:840", "first open completed after an interrupted configuration write")
        record = json.loads((self.store / surface.STORE_PROFILE_FILE).read_text(encoding="utf-8"))
        self.assertEqual((record["profile"], record["bound_project"]), (surface.STORE_PROFILE_SINGLE_PROJECT, "project:a"))
        self.assertEqual(self.leftovers(self.durable_names()), [])

    def test_i2_planted_configuration_temporary_is_not_followed(self):
        config = self.store / surface._DEFAULT_CONFIG_NAME
        for link in _predictable_names(config):
            link.symlink_to(self.victim)
        with self.open() as memory:
            memory.remember("memory:840", "configuration staging ignored a planted symlink")
        self.assertEqual(self.victim.read_bytes(), VICTIM)
        self.assertFalse(config.is_symlink())
        json.loads(config.read_text(encoding="utf-8"))

    def test_i3_interrupted_creation_is_completed_by_the_claiming_identity(self):
        original = SQLiteConfiguredCompositionRuntime.create

        def interrupted(cls, *args, **kwargs):
            raise OSError(errno.EIO, "interrupted before the first checkpoint")

        with mock.patch.object(SQLiteConfiguredCompositionRuntime, "create", classmethod(interrupted)), \
                self.assertRaises(OSError):
            self.open()
        with self.assertRaises(surface.StoreIdentityError):
            self.open(scope="project:b")
        self.assertIs(SQLiteConfiguredCompositionRuntime.create.__func__, original.__func__)
        with self.open() as memory:
            memory.remember("memory:840", "the claiming identity completed the creation")
        self.assertEqual(self.leftovers(self.durable_names()), [])

    def test_i4_planted_claim_temporary_is_not_followed(self):
        claim = self.store / surface.STORE_PROFILE_FILE
        planted = claim.with_name(f".{claim.name}.{os.getpid()}.{threading.get_ident()}.claim")
        planted.symlink_to(self.victim)
        try:
            with self.open() as memory:
                memory.remember("memory:840", "claim staging")
        except (OSError, surface.StoreIdentityError):
            pass
        self.assertEqual(self.victim.read_bytes(), VICTIM)


if __name__ == "__main__":
    unittest.main()
