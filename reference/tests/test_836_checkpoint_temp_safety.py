"""#836 security regression: checkpoint staging must never follow legacy temporary symlinks.

Exercise both file-profile checkpoint writers; SQLite's own atomic generation
publication remains governed by separate restart and journal evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from agentmem_ref.runtime import configured_restart, restart_runtime

WRITERS = (restart_runtime, configured_restart)


class CheckpointTemporarySafety(unittest.TestCase):
    def test_old_predictable_temporary_symlink_cannot_overwrite_unrelated_file(self):
        for writer in WRITERS:
            with self.subTest(writer=writer.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "checkpoint.json"
                victim = root / "unrelated-secret.txt"
                victim.write_text("UNCHANGED", encoding="utf-8")
                try:
                    (root / ".checkpoint.json.tmp").symlink_to(victim)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"symlinks unavailable: {exc}")
                writer._atomic_json_write(target, {"test": "safe"})
                self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"test": "safe"})
                self.assertEqual(victim.read_text(encoding="utf-8"), "UNCHANGED")
                self.assertTrue((root / ".checkpoint.json.tmp").is_symlink())

    def test_replace_error_preserves_target_and_removes_only_its_private_temporary(self):
        for writer in WRITERS:
            with self.subTest(writer=writer.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "checkpoint.json"
                target.write_text("ORIGINAL", encoding="utf-8")
                bystander = root / ".checkpoint.json.tmp"
                bystander.write_text("BYSTANDER", encoding="utf-8")
                with patch.object(writer.os, "replace", side_effect=OSError("rename refused")):
                    with self.assertRaisesRegex(OSError, "rename refused"):
                        writer._atomic_json_write(target, {"new": 1})
                self.assertEqual(target.read_text(encoding="utf-8"), "ORIGINAL")
                self.assertEqual(bystander.read_text(encoding="utf-8"), "BYSTANDER")
                self.assertEqual(list(root.glob(".checkpoint.json.*.tmp")), [])

    def test_fsync_failure_preserves_target_and_cleans_incomplete_private_temporary(self):
        for writer in WRITERS:
            with self.subTest(writer=writer.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "checkpoint.json"
                target.write_text("ORIGINAL", encoding="utf-8")
                with patch.object(writer.os, "fsync", side_effect=OSError("write flush failed")):
                    with self.assertRaisesRegex(OSError, "write flush failed"):
                        writer._atomic_json_write(target, {"new": 1})
                self.assertEqual(target.read_text(encoding="utf-8"), "ORIGINAL")
                self.assertEqual(list(root.glob(".checkpoint.json.*.tmp")), [])

    def test_parallel_writers_never_share_temporary_inodes_or_publish_partial_json(self):
        for writer in WRITERS:
            with self.subTest(writer=writer.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "checkpoint.json"
                payloads = ({"large": "A" * 8192}, {"large": "B" * 8192})
                gate = threading.Barrier(2)
                originals: list[str] = []
                errors: list[BaseException] = []
                original_replace = writer.os.replace

                def race(source, destination):
                    originals.append(str(source))
                    gate.wait(timeout=10)
                    return original_replace(source, destination)

                def commit(value):
                    try:
                        writer._atomic_json_write(target, value)
                    except BaseException as exc:
                        errors.append(exc)

                with patch.object(writer.os, "replace", side_effect=race):
                    workers = [threading.Thread(target=commit, args=(p,)) for p in payloads]
                    for worker in workers:
                        worker.start()
                    for worker in workers:
                        worker.join(timeout=15)
                    self.assertFalse(any(worker.is_alive() for worker in workers))
                self.assertEqual(errors, [])
                self.assertEqual(len(set(originals)), 2)
                self.assertIn(json.loads(target.read_text(encoding="utf-8")), payloads)
                self.assertEqual(list(root.glob(".checkpoint.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
