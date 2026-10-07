"""Derived vector store (#669): derived, rebuildable, integrity-checked, never authority."""

from __future__ import annotations

import os
import sqlite3
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref.runtime.representation_cache import DerivedVectorStore, float32_canonical  # noqa: E402

DIGEST = "sha256:" + "ab" * 32


class _Counter:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, text: str) -> tuple[float, ...]:
        self.calls += 1
        base = float(len(text))
        return (base / 10.0, 0.1234567891234, -0.5)


class DerivedVectorStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp()
        self.store = DerivedVectorStore(self.root, DIGEST, 3)
        self.embed = _Counter()

    def tearDown(self) -> None:
        self.store.close()

    def test_miss_then_hit_embeds_once(self):
        first = self.store.vector_for("f1", "hello world", self.embed)
        second = self.store.vector_for("f1", "hello world", self.embed)
        self.assertEqual(first, second)
        self.assertEqual(self.embed.calls, 1)
        self.assertEqual(self.store.row_count(), 1)

    def test_cached_equals_recomputed_float32(self):
        cached = self.store.vector_for("f1", "hello", self.embed)
        self.assertEqual(cached, float32_canonical(self.embed("hello")))
        self.assertNotEqual(self.embed("hello")[1], cached[1])  # float64 input, float32 output

    def test_changed_text_is_a_new_key(self):
        self.store.vector_for("f1", "a", self.embed)
        self.store.vector_for("f1", "ab", self.embed)
        self.assertEqual(self.embed.calls, 2)

    def test_tampered_row_fails_checksum_and_is_recomputed(self):
        original = self.store.vector_for("f1", "hello", self.embed)
        connection = sqlite3.connect(self.store.path)
        connection.execute("UPDATE vectors SET vector = ?", (b"\x00" * 12,))
        connection.commit()
        connection.close()
        again = self.store.vector_for("f1", "hello", self.embed)
        self.assertEqual(again, original)
        self.assertEqual(self.store.checksum_failures, 1)

    def test_verify_reports_and_rebuilds_tampered_rows(self):
        self.store.vector_for("f1", "hello", self.embed)
        self.store.vector_for("gone", "orphan text", self.embed)
        connection = sqlite3.connect(self.store.path)
        connection.execute("UPDATE vectors SET vector = ? WHERE fact_uuid = 'f1'", (b"\x00" * 12,))
        connection.commit()
        connection.close()
        report = self.store.verify({"f1": "hello"}, self.embed)
        self.assertEqual(report["mismatched"], ["f1"])
        self.assertEqual(report["orphans"], ["gone"])
        rebuilt = self.store.verify({"f1": "hello"}, self.embed, rebuild=True)
        self.assertTrue(rebuilt["rebuilt"])
        self.assertEqual(self.store.verify({"f1": "hello"}, self.embed)["mismatched"], [])
        self.assertEqual(self.store.row_count(), 1)

    def test_file_mode_is_0600_and_name_has_no_colon(self):
        mode = stat.S_IMODE(os.stat(self.store.path).st_mode)
        self.assertEqual(mode, 0o600)
        self.assertNotIn(":", self.store.path.name)

    def test_config_digest_mismatch_discards_store(self):
        self.store.vector_for("f1", "hello", self.embed)
        self.store.close()
        connection = sqlite3.connect(self.store.path)
        connection.execute("UPDATE meta SET value = 'other' WHERE key = 'config_digest'")
        connection.commit()
        connection.close()
        reopened = DerivedVectorStore(self.root, DIGEST, 3)
        self.assertEqual(reopened.row_count(), 0)
        reopened.close()
        self.store = DerivedVectorStore(self.root, DIGEST, 3)

    def test_symlinked_store_is_refused(self):
        self.store.close()
        target = Path(self.root) / "elsewhere.sqlite"
        self.store.path.rename(target)
        self.store.path.symlink_to(target)
        with self.assertRaises(ValueError):
            DerivedVectorStore(self.root, DIGEST, 3)
        self.store.path.unlink()
        self.store = DerivedVectorStore(self.root, DIGEST, 3)

    def test_invalid_vector_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.vector_for("f1", "x", lambda text: (1.0, 2.0))


if __name__ == "__main__":
    unittest.main()
