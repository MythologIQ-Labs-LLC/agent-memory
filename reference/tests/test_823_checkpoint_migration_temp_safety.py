"""#823: migration and journal recovery must never follow predictable temp symlinks.

File-checkpoint compatibility path only. These tests do not qualify the SQLite
baseline and do not bypass governed checkpoint generation checks.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from agentmem_ref.memory import checkpoint_migration
from agentmem_ref.runtime import checkpoint_transactions, restart_runtime


def _writer_cases(root: Path):
    journal = checkpoint_transactions.CheckpointTransactionSupport(
        restart_runtime.JsonRuntimeStateStore(root)
    )
    return (
        (
            "recovery_journal",
            root / "runtime-generation-journal.jsonl",
            lambda value: journal._atomic_journal_write((value,)),
            restart_runtime.os,
        ),
        (
            "migration",
            root / "runtime-migration-intent.json",
            lambda value: checkpoint_migration._atomic_json_write(
                root / "runtime-migration-intent.json", value
            ),
            checkpoint_migration.os,
        ),
    )


class MigrationCheckpointTemporarySafety(unittest.TestCase):
    def test_planted_old_temp_symlink_never_mutates_its_victim(self):
        for name in ("recovery_journal", "migration"):
            with self.subTest(writer=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                cases = {item[0]: item for item in _writer_cases(root)}
                _, target, write, _ = cases[name]
                victim = root / "victim.txt"
                victim.write_text("DO NOT TOUCH", encoding="utf-8")
                planted = root / f".{target.name}.tmp"
                try:
                    planted.symlink_to(victim)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"symlinks unavailable: {exc}")
                write({"value": "safe"})
                self.assertEqual(victim.read_text(encoding="utf-8"), "DO NOT TOUCH")
                self.assertTrue(planted.is_symlink())
                self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"value": "safe"})

    def test_rename_error_preserves_target_and_cleans_only_private_staging(self):
        for name in ("recovery_journal", "migration"):
            with self.subTest(writer=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                cases = {item[0]: item for item in _writer_cases(root)}
                _, target, write, module_os = cases[name]
                target.write_text("ORIGINAL", encoding="utf-8")
                bystander = root / f".{target.name}.tmp"
                bystander.write_text("BYSTANDER", encoding="utf-8")
                with patch.object(module_os, "replace", side_effect=OSError("rename failed")):
                    with self.assertRaisesRegex(OSError, "rename failed"):
                        write({"new": 1})
                self.assertEqual(target.read_text(encoding="utf-8"), "ORIGINAL")
                self.assertEqual(bystander.read_text(encoding="utf-8"), "BYSTANDER")
                self.assertEqual(list(root.glob(f".{target.name}.*.tmp")), [])

    def test_file_fsync_error_preserves_target_and_removes_partial_staging(self):
        for name in ("recovery_journal", "migration"):
            with self.subTest(writer=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                cases = {item[0]: item for item in _writer_cases(root)}
                _, target, write, module_os = cases[name]
                target.write_text("ORIGINAL", encoding="utf-8")
                with patch.object(module_os, "fsync", side_effect=OSError("fsync failed")):
                    with self.assertRaisesRegex(OSError, "fsync failed"):
                        write({"new": 1})
                self.assertEqual(target.read_text(encoding="utf-8"), "ORIGINAL")
                self.assertEqual(list(root.glob(f".{target.name}.*.tmp")), [])

    def test_parallel_writers_use_distinct_staging_and_complete_json(self):
        for name in ("recovery_journal", "migration"):
            with self.subTest(writer=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                cases = {item[0]: item for item in _writer_cases(root)}
                _, target, write, module_os = cases[name]
                data = ({"large": "A" * 8192}, {"large": "B" * 8192})
                gate = threading.Barrier(2)
                sources: list[str] = []
                errors: list[Exception] = []
                replace = module_os.replace

                def barrier_replace(source, destination):
                    sources.append(str(source))
                    gate.wait(timeout=10)
                    return replace(source, destination)

                def execute(value):
                    try:
                        write(value)
                    except Exception as exc:
                        errors.append(exc)

                with patch.object(module_os, "replace", side_effect=barrier_replace):
                    threads = [threading.Thread(target=execute, args=(v,)) for v in data]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(timeout=15)
                    self.assertFalse(any(thread.is_alive() for thread in threads))
                self.assertEqual(errors, [])
                self.assertEqual(len(set(sources)), 2)
                self.assertIn(json.loads(target.read_text(encoding="utf-8")), data)
                self.assertEqual(list(root.glob(f".{target.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
