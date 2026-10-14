"""Derived vector store (#669): derived, rebuildable, integrity-checked, never authority."""

from __future__ import annotations

import os
import sqlite3
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref.runtime.representation_cache import (  # noqa: E402
    DerivedVectorStore, DerivedCacheReconciliationError, ForeignDerivedStore, UnsafeDerivedEntry,
    float32_canonical, reconcile_derived_vector_stores,
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

    def test_active_store_refuses_linked_derived_directory_without_touching_external_cache(self):
        # The active semantic route constructs DerivedVectorStore BEFORE the
        # facade invokes #802 recovery reconciliation. Refuse the parent link
        # at construction, not just the later reconciliation path.
        with tempfile.TemporaryDirectory() as second_root:
            external = DerivedVectorStore(second_root, DIGEST, 3)
            try:
                external.vector_for("private-external", "external content", self.embed)
                other = Path(self.root) / "linked-runtime"
                other.mkdir()
                (other / "derived").symlink_to(
                    Path(second_root) / "derived", target_is_directory=True
                )
                before = external.path.read_bytes()
                with self.assertRaisesRegex(
                    ValueError, "symlinked derived vector cache directory"
                ):
                    DerivedVectorStore(other, DIGEST, 3)
                self.assertEqual(external.path.read_bytes(), before)
                self.assertEqual(external.row_count(), 1)
            finally:
                external.close()

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

    def test_reconcile_never_acts_through_a_symlink_swapped_in_after_the_check(self):
        """The lstat passes on a regular file; the entry is replaced by a link to an external
        store before SQLite opens it. The open follows the link (SQLite has no no-follow
        option here), so the reconciler must detect the swap after the open and act on
        nothing: no purge, no unlink, the external rows and the link itself intact."""
        import sqlite3 as _sqlite3
        from agentmem_ref.runtime import representation_cache as module
        with tempfile.TemporaryDirectory() as other_root:
            outside = DerivedVectorStore(other_root, self.store.config_digest, 3)
            try:
                outside.vector_for("foreign-fact", "external payload", self.embed)
                outside.close()
                external = next((Path(other_root) / "derived").glob("vectors-*.sqlite"))
                victim = Path(self.root) / "derived" / external.name
                victim.write_bytes(external.read_bytes())  # a regular file passes the lstat
                real_connect = _sqlite3.connect

                def swap_then_connect(*args, **kwargs):
                    victim.unlink()
                    victim.symlink_to(external)
                    return real_connect(*args, **kwargs)

                with patch.object(module.sqlite3, "connect", side_effect=swap_then_connect):
                    report = reconcile_derived_vector_stores(self.root, {})
                self.assertIn(str(victim), report["unsafe"])
                self.assertEqual(report["status"], "incomplete")
                self.assertEqual(report["rows_purged"], 0)
                self.assertEqual(report["stores_discarded"], [])
                self.assertTrue(victim.is_symlink())
                check = real_connect(external)
                try:
                    self.assertEqual(check.execute("SELECT fact_uuid FROM vectors").fetchall(), [("foreign-fact",)])
                finally:
                    check.close()
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

    def test_reconcile_discards_unreadable_stores_and_keeps_foreign_ones_reported(self):
        """Damaged or unreadable files under our name are ours to discard (rebuildable); a
        readable database of another format or version is never touched: it may be another
        version's data, so it is reported ``foreign`` and the status is incomplete."""
        self.store.vector_for("orphan", "stale text", self.embed)
        self.store._connection.execute("UPDATE meta SET value = 'invalid' WHERE key = 'format'")
        self.store._connection.commit()
        self.store.close()
        tampered_bytes = self.store.path.read_bytes()
        garbage = Path(self.root) / "derived" / ("vectors-" + "dd" * 8 + ".sqlite")
        garbage.write_bytes(b"\x00garbage" * 128)
        foreign = Path(self.root) / "derived" / ("vectors-" + "ee" * 8 + ".sqlite")
        sqlite3.connect(foreign).execute("CREATE TABLE other (x)").connection.close()
        foreign_bytes = foreign.read_bytes()
        stray = Path(self.root) / "derived" / "vectors-not-ours.sqlite"
        stray.write_bytes(b"stray")
        report = reconcile_derived_vector_stores(self.root, {})
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["stores_checked"], 0)
        self.assertEqual(report["stores_discarded"], [[str(garbage), "unreadable: file is not a database"]])
        self.assertFalse(garbage.exists())
        self.assertEqual(
            sorted(report["foreign"]),
            sorted([[str(self.store.path), "unknown store format 'invalid'"],
                    [str(foreign), "schema without meta and vectors tables"]]),
        )
        self.assertEqual(report["unsafe"], [])
        self.assertEqual(self.store.path.read_bytes(), tampered_bytes)
        self.assertEqual(foreign.read_bytes(), foreign_bytes)
        self.assertEqual(stray.read_bytes(), b"stray")
        # The active store does not discard foreign data at its own path either.
        with self.assertRaises(ForeignDerivedStore):
            DerivedVectorStore(self.root, DIGEST, 3)
        self.assertEqual(self.store.path.read_bytes(), tampered_bytes)
        self.store.path.unlink()
        self.store = DerivedVectorStore(self.root, DIGEST, 3)
        self.assertEqual(self.store.row_count(), 0)

    def test_reconcile_keeps_another_runtime_versions_store_and_reports_it_foreign(self):
        other = Path(self.root) / "derived" / ("vectors-" + "ff" * 8 + ".sqlite")
        connection = sqlite3.connect(other)
        connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("CREATE TABLE vectors (fact_uuid TEXT, content_sha256 TEXT, vector BLOB, "
                           "row_sha256 TEXT, extra TEXT)")
        connection.executemany("INSERT INTO meta VALUES (?, ?)", [
            ("format", "agent-memory-derived-vectors/2.0.0"), ("config_digest", "sha256:" + "ff" * 32),
            ("dimensions", "3")])
        connection.execute("INSERT INTO vectors VALUES ('newer-fact', 'x', X'00', 'y', 'z')")
        connection.commit()
        connection.close()
        before = other.read_bytes()
        report = reconcile_derived_vector_stores(self.root, {})
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["foreign"],
                         [[str(other), "store format 'agent-memory-derived-vectors/2.0.0' of another runtime version"]])
        self.assertEqual(report["stores_discarded"], [])
        self.assertEqual(report["rows_purged"], 0)
        self.assertEqual(other.read_bytes(), before)

    def test_active_store_never_initialises_a_readable_foreign_database_at_its_path(self):
        self.store.close()
        self.store.path.unlink()
        connection = sqlite3.connect(self.store.path)
        connection.execute("CREATE TABLE other (x)")
        connection.execute("INSERT INTO other VALUES (1)")
        connection.commit()
        connection.close()
        before = self.store.path.read_bytes()
        with self.assertRaisesRegex(ForeignDerivedStore, "schema without meta and vectors tables"):
            DerivedVectorStore(self.root, DIGEST, 3)
        self.assertEqual(self.store.path.read_bytes(), before)
        check = sqlite3.connect(self.store.path)
        try:
            self.assertEqual([r[0] for r in check.execute("SELECT name FROM sqlite_master")], ["other"])
        finally:
            check.close()
        self.store.path.unlink()
        self.store = DerivedVectorStore(self.root, DIGEST, 3)

    def test_reconcile_refuses_parent_directory_swapped_in_and_back_out_around_the_open(self):
        """The directory entry is intact before and after the open; only during SQLite's own
        open does ``derived`` point at an external cache directory. The leaf inode's change
        time never moves, so an entry re-check cannot see it: the descriptor-table
        verification must, and nothing may be read, purged or unlinked outside the root."""
        import sqlite3 as _sqlite3
        from agentmem_ref.runtime import representation_cache as module
        self.store.vector_for("mine", "own text", self.embed)
        self.store.close()
        with tempfile.TemporaryDirectory() as other_root:
            outside = DerivedVectorStore(other_root, DIGEST, 3)
            outside.vector_for("foreign-fact", "external payload", self.embed)
            outside.close()
            derived = Path(self.root) / "derived"
            real_connect = _sqlite3.connect

            def swap_around_connect(*args, **kwargs):
                os.rename(derived, derived.with_name("derived.real"))
                derived.symlink_to(Path(other_root) / "derived", target_is_directory=True)
                try:
                    return real_connect(*args, **kwargs)
                finally:
                    derived.unlink()
                    os.rename(derived.with_name("derived.real"), derived)

            with patch.object(module.sqlite3, "connect", side_effect=swap_around_connect):
                report = reconcile_derived_vector_stores(self.root, {})
            self.assertEqual(report["status"], "incomplete")
            self.assertEqual(report["unsafe"], [str(self.store.path)])
            self.assertEqual(report["rows_purged"], 0)
            self.assertEqual(report["stores_discarded"], [])
            check = real_connect(outside.path)
            try:
                self.assertEqual(check.execute("SELECT fact_uuid FROM vectors").fetchall(), [("foreign-fact",)])
            finally:
                check.close()
        self.store = DerivedVectorStore(self.root, DIGEST, 3)
        self.assertEqual(self.store.row_count(), 1)

    def test_active_store_open_refuses_a_leaf_link_swapped_in_around_the_open_without_chmod_or_writes(self):
        """A link to an external database swapped in while SQLite opens the active store
        must be refused before any statement: no table is created in the external file,
        and its mode is not changed (chmod goes through the pinned descriptor only)."""
        import sqlite3 as _sqlite3
        from agentmem_ref.runtime import representation_cache as module
        self.store.close()
        with tempfile.TemporaryDirectory() as other_root:
            external = Path(other_root) / "external.sqlite"
            connection = _sqlite3.connect(external)
            connection.execute("CREATE TABLE other (x)")
            connection.commit()
            connection.close()
            os.chmod(external, 0o644)
            before = external.read_bytes()
            real_connect = _sqlite3.connect
            victim = self.store.path

            def swap_then_connect(*args, **kwargs):
                victim.unlink()
                victim.symlink_to(external)
                return real_connect(*args, **kwargs)

            with patch.object(module.sqlite3, "connect", side_effect=swap_then_connect):
                with self.assertRaises(UnsafeDerivedEntry):
                    DerivedVectorStore(self.root, DIGEST, 3)
            self.assertEqual(external.read_bytes(), before)
            self.assertEqual(stat.S_IMODE(os.stat(external).st_mode), 0o644)
            self.assertTrue(victim.is_symlink())
            victim.unlink()
        self.store = DerivedVectorStore(self.root, DIGEST, 3)

    @unittest.skipUnless(hasattr(os, "geteuid") and os.geteuid() == 0, "needs root to chown")
    def test_reconcile_and_open_refuse_a_derived_directory_owned_by_another_user(self):
        self.store.vector_for("mine", "own text", self.embed)
        self.store.close()
        derived = Path(self.root) / "derived"
        os.chown(derived, 65534, 65534)
        try:
            report = reconcile_derived_vector_stores(self.root, {})
            self.assertEqual(report["status"], "incomplete")
            self.assertEqual(report["unsafe"], [str(derived)])
            with self.assertRaisesRegex(UnsafeDerivedEntry, "owned by uid 65534"):
                DerivedVectorStore(self.root, DIGEST, 3)
        finally:
            os.chown(derived, os.geteuid(), os.getegid())
        self.store = DerivedVectorStore(self.root, DIGEST, 3)
        self.assertEqual(self.store.row_count(), 1)

    def test_derived_directory_is_created_private(self):
        self.assertEqual(stat.S_IMODE(os.stat(Path(self.root) / "derived").st_mode), 0o700)

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
