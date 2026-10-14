"""Derived vector store (#669): derived, rebuildable, integrity-checked, never authority."""

from __future__ import annotations

import os
import sqlite3
import stat
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref.runtime.representation_cache import (  # noqa: E402
    DerivedVectorStore, DerivedCacheReconciliationError, float32_canonical,
    reconcile_derived_vector_stores,
)

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

    def test_purge_fact_removes_all_content_versions_and_keeps_other_facts(self):
        self.store.vector_for("deleted", "first version", self.embed)
        self.store.vector_for("deleted", "second version", self.embed)
        retained = self.store.vector_for("retained", "other data", self.embed)
        self.assertEqual(self.store.row_count(), 3)
        self.assertEqual(self.store.purge_fact("deleted"), 2)
        self.assertEqual(self.store.row_count(), 1)
        self.assertEqual(self.store.purge_fact("deleted"), 0)
        self.assertEqual(self.store.vector_for("retained", "other data", self.embed), retained)
        self.assertEqual(self.store.row_count(), 1)

    def test_purge_fact_is_durable_across_reopen_without_representation_provider(self):
        self.store.vector_for("deleted", "delete me", self.embed)
        self.store.vector_for("retained", "keep me", self.embed)
        self.assertEqual(self.store.purge_fact("deleted"), 1)
        self.store.close()
        self.store = DerivedVectorStore(self.root, DIGEST, 3)
        rows = self.store._connection.execute(
            "SELECT fact_uuid FROM vectors ORDER BY fact_uuid"
        ).fetchall()
        self.assertEqual(rows, [("retained",)])

    def test_purge_fact_rejects_invalid_identity_without_changing_rows(self):
        self.store.vector_for("retained", "keep me", self.embed)
        for invalid in ("", None, 0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.store.purge_fact(invalid)
        self.assertEqual(self.store.row_count(), 1)

    def test_reconcile_derived_root_handles_old_config_and_retains_live_facts(self):
        alternate = DerivedVectorStore(self.root, "sha256:" + "bb" * 32, 3)
        try:
            for store in (self.store, alternate):
                store.vector_for("gone", "private text", self.embed)
                store.vector_for("live", "public text", self.embed)
            result = reconcile_derived_vector_stores(
                self.root, {"live": "public text"}, deleted_fact_uuid="gone"
            )
            self.assertEqual(
                (result["status"], result["stores_checked"], result["rows_purged"]), ("complete", 2, 2)
            )
            self.assertEqual(self.store.row_count(), 1)
            self.assertEqual(alternate.row_count(), 1)
            again = reconcile_derived_vector_stores(self.root, {"live": "public text"})
            self.assertEqual((again["status"], again["stores_checked"], again["rows_purged"]), ("complete", 2, 0))
        finally:
            alternate.close()

    def test_reconcile_derived_root_cleans_stale_content_after_restart(self):
        self.store.vector_for("live", "old", self.embed)
        self.store.vector_for("live", "new", self.embed)
        self.store.close()
        result = reconcile_derived_vector_stores(self.root, {"live": "new"})
        self.assertEqual((result["stores_checked"], result["rows_purged"]), (1, 1))
        self.store = DerivedVectorStore(self.root, DIGEST, 3)
        self.assertEqual(self.store.row_count(), 1)

    def test_root_reconciliation_accepts_relative_root(self):
        self.store.vector_for("orphan", "old value", self.embed)
        relative = Path(os.path.relpath(self.root, Path.cwd()))
        result = reconcile_derived_vector_stores(relative, {})
        self.assertEqual((result["stores_checked"], result["rows_purged"]), (1, 1))
        self.assertEqual(self.store.row_count(), 0)

    def test_reconcile_refuses_symlinked_derived_directory_and_preserves_external_rows(self):
        with tempfile.TemporaryDirectory() as other_root:
            outside = DerivedVectorStore(other_root, "sha256:" + "cc" * 32, 3)
            try:
                outside.vector_for("foreign-fact", "external payload", self.embed)
                internal = Path(self.root) / "other-workspace"
                internal.mkdir()
                (internal / "derived").symlink_to(
                    Path(other_root) / "derived", target_is_directory=True
                )
                report = reconcile_derived_vector_stores(internal, {})
                self.assertEqual(report["status"], "incomplete")
                self.assertIn(str(internal / "derived"), report["unsafe"])
                self.assertEqual(report["stores_checked"], 0)
                self.assertEqual(outside.row_count(), 1)
                self.assertEqual(
                    outside._connection.execute("SELECT fact_uuid FROM vectors").fetchone()[0],
                    "foreign-fact",
                )
            finally:
                outside.close()

    def test_reconcile_derived_root_rejects_symlink_without_touching_target(self):
        target = Path(self.root) / "outside.sqlite"
        target.write_bytes(b"not an agent-memory store")
        link = Path(self.root) / "derived" / ("vectors-" + "cc" * 8 + ".sqlite")
        link.symlink_to(target)
        report = reconcile_derived_vector_stores(self.root, {})
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["unsafe"], [str(link)])
        self.assertEqual(report["stores_discarded"], [])
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_bytes(), b"not an agent-memory store")
        link.unlink()

    def test_reconcile_derived_root_discards_unreadable_or_foreign_stores_and_reports(self):
        self.store.vector_for("orphan", "stale text", self.embed)
        self.store._connection.execute("UPDATE meta SET value = 'invalid' WHERE key = 'format'")
        self.store._connection.commit()
        self.store.close()
        garbage = Path(self.root) / "derived" / ("vectors-" + "dd" * 8 + ".sqlite")
        garbage.write_bytes(b"\x00garbage" * 128)
        foreign = Path(self.root) / "derived" / ("vectors-" + "ee" * 8 + ".sqlite")
        sqlite3.connect(foreign).execute("CREATE TABLE other (x)").connection.close()
        stray = Path(self.root) / "derived" / "vectors-not-ours.sqlite"
        stray.write_bytes(b"stray")
        report = reconcile_derived_vector_stores(self.root, {})
        # An unreadable derived store cannot be reconciled: it is discarded (rebuildable,
        # never authority) so its residue goes with it; a stray name is not ours and stays.
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["stores_checked"], 0)
        self.assertEqual(
            sorted(path for path, _reason in report["stores_discarded"]),
            sorted(str(path) for path in (self.store.path, garbage, foreign)),
        )
        for path in (self.store.path, garbage, foreign):
            self.assertFalse(path.exists())
        self.assertEqual(stray.read_bytes(), b"stray")
        self.store = DerivedVectorStore(self.root, DIGEST, 3)
        self.assertEqual(self.store.row_count(), 0)

    def test_reconcile_reports_a_store_it_cannot_write_without_discarding_it(self):
        self.store.vector_for("orphan", "stale text", self.embed)
        real_connect = sqlite3.connect

        def readonly_connect(database, *args, **kwargs):
            if isinstance(database, str) and database.startswith("file:"):
                raise sqlite3.OperationalError("attempt to write a readonly database")
            return real_connect(database, *args, **kwargs)

        with mock.patch.object(sqlite3, "connect", readonly_connect):
            report = reconcile_derived_vector_stores(self.root, {})
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["failed"][0][0], str(self.store.path))
        self.assertIn("readonly", report["failed"][0][1])
        self.assertEqual(report["stores_discarded"], [])
        self.assertEqual(self.store.row_count(), 1)

    def test_secure_delete_is_on_for_the_store_connection(self):
        self.assertEqual(self.store._connection.execute("PRAGMA secure_delete").fetchone()[0], 1)
        self.store.vector_for("gone", "secret text", self.embed)
        self.store.verify({}, self.embed, rebuild=True)
        self.store.close()
        self.assertNotIn(b"gone", self.store.path.read_bytes())
        self.store = DerivedVectorStore(self.root, DIGEST, 3)

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
