"""Incremental integrity attestation for the SQLite runtime (#522).

Three layers stay distinct:

* operation integrity at commit: compare-and-swap on the bound generation plus
  verification of the journal tail being extended;
* current-state attestation at commit: an incrementally maintained bucketed
  Merkle root over canonical rows;
* recovery-time full verification: the root recomputed from canonical rows
  (never from the maintained index) and the full journal chain.

The maintained index is derived data. Tampering with canonical rows or the
journal must refuse recovery; tampering with the index alone must not change
any answer, only force a rebuild.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.qualified_fixtures import registry_for
from tests.test_sqlite_production_substrate import MEMORY, _context, _corpus, _profile, _proposal

from agentmem_ref.restart_runtime import RuntimeCheckpointConflict, RuntimeRecoveryError
from agentmem_ref.sqlite_runtime import SQLiteRestartSafeRuntime
from agentmem_ref.state import sqlite_substrate
from agentmem_ref.sqlite_substrate import BUCKETED_DIGEST_SCHEME, LEGACY_DIGEST_PREFIX, SQLiteTemporalGraph
from agentmem_ref.substrate import Episode


class IncrementalAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile = _profile()
        self.corpus = _corpus()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _create(self) -> SQLiteRestartSafeRuntime:
        return SQLiteRestartSafeRuntime.create(
            self.root, tenant="tenant-acme", profile=self.profile, verifier_registry=registry_for(self.corpus)
        )

    def _recover(self) -> SQLiteRestartSafeRuntime:
        return SQLiteRestartSafeRuntime.recover(
            self.root, profile=self.profile, verifier_registry=registry_for(self.corpus)
        )

    def _raw(self) -> sqlite3.Connection:
        return sqlite3.connect(self.root / "agent-memory.sqlite3")

    def _populate(self, runtime: SQLiteRestartSafeRuntime, count: int = 3) -> list[str]:
        facts = []
        for index in range(count):
            result = runtime.commit_proposal(
                _proposal(f"proposal:{index}", operation="promotion", target_reference=f"memory:item-{index}"),
                f"item {index} value",
            )
            self.assertTrue(result.committed)
            facts.append(result.fact_uuid)
        return facts

    def _recorded_digest(self, runtime: SQLiteRestartSafeRuntime) -> str:
        return runtime.substrate.read_runtime_state()["substrate_digest"]

    def test_incremental_root_equals_full_recomputation_across_lifecycle(self) -> None:
        runtime = self._create()
        try:
            self._populate(runtime)
            runtime.commit_proposal(_proposal("proposal:initial", operation="promotion"), "deploy window is Thursday")
            runtime.governed_recall("item value", _context())
            runtime.commit_proposal(
                _proposal("proposal:prune", operation="pruning", target_reference="memory:item-1"), ""
            )
            recorded = self._recorded_digest(runtime)
            self.assertTrue(recorded.startswith(f"{BUCKETED_DIGEST_SCHEME}:"))
            self.assertEqual(recorded, runtime.substrate.recompute_bucketed_digest())
        finally:
            runtime.close()
        recovered = self._recover()
        try:
            self.assertEqual(recovered.recovery_evidence.substrate_digest, recorded)
            self.assertEqual(recovered.governed_recall("item value", _context()).admitted.__class__, list)
        finally:
            recovered.close()

    def test_commit_hashes_only_changed_rows_not_the_store(self) -> None:
        runtime = self._create()
        try:
            self._populate(runtime, count=60)
            with mock.patch.object(sqlite_substrate, "_row_hash", wraps=sqlite_substrate._row_hash) as hashed:
                runtime.commit_proposal(
                    _proposal("proposal:one-more", operation="promotion", target_reference="memory:one-more"),
                    "one more value",
                )
            # A promotion touches an episode and a fact; the legacy commitment re-serialized
            # all 120+ canonical rows on every commit.
            self.assertLessEqual(hashed.call_count, 4)
            self.assertEqual(self._recorded_digest(runtime), runtime.substrate.recompute_bucketed_digest())
        finally:
            runtime.close()

    def test_tampered_fact_row_refuses_recovery(self) -> None:
        runtime = self._create()
        facts = self._populate(runtime)
        runtime.close()
        with self._raw() as raw:
            raw.execute("UPDATE facts SET fact_text = 'forged' WHERE uuid = ?", (facts[0],))
        with self.assertRaisesRegex(RuntimeRecoveryError, "canonical substrate digest mismatch"):
            self._recover()

    def test_tamper_while_open_is_not_laundered_into_the_next_commitment(self) -> None:
        runtime = self._create()
        try:
            facts = self._populate(runtime)
            with self._raw() as raw:
                raw.execute("UPDATE facts SET fact_text = 'forged' WHERE uuid = ?", (facts[0],))
            # The next commit updates the root only for rows it changed, so the forged row
            # is not folded into a fresh commitment.
            runtime.commit_proposal(
                _proposal("proposal:after", operation="promotion", target_reference="memory:after"), "after value"
            )
        finally:
            runtime.close()
        with self.assertRaisesRegex(RuntimeRecoveryError, "canonical substrate digest mismatch"):
            self._recover()

    def test_tampered_interior_journal_record_refuses_recovery(self) -> None:
        runtime = self._create()
        self._populate(runtime)
        runtime.close()
        with self._raw() as raw:
            raw.execute(
                "UPDATE runtime_journal SET payload_json = json_set(payload_json, '$.governance_digest', 'sha256:forged') "
                "WHERE generation = 2"
            )
        with self.assertRaises(RuntimeRecoveryError):
            self._recover()

    def test_truncated_journal_refuses_recovery(self) -> None:
        runtime = self._create()
        self._populate(runtime)
        runtime.close()
        with self._raw() as raw:
            raw.execute("DELETE FROM runtime_journal WHERE generation = (SELECT MAX(generation) FROM runtime_journal)")
        with self.assertRaisesRegex(RuntimeRecoveryError, "generation/journal mismatch"):
            self._recover()

    def test_tampered_journal_tail_blocks_the_next_commit(self) -> None:
        runtime = self._create()
        try:
            self._populate(runtime)
            with self._raw() as raw:
                raw.execute(
                    "UPDATE runtime_journal SET payload_json = json_set(payload_json, '$.substrate_digest', 'sha256:forged') "
                    "WHERE generation = (SELECT MAX(generation) FROM runtime_journal)"
                )
            with self.assertRaisesRegex(RuntimeRecoveryError, "record digest mismatch"):
                runtime.commit_proposal(
                    _proposal("proposal:blocked", operation="promotion", target_reference="memory:blocked"), "blocked"
                )
            self.assertIsNone(runtime.adapter.current_fact_uuid("memory:blocked"))
        finally:
            runtime.close()

    def test_rebound_state_without_matching_tail_is_refused(self) -> None:
        runtime = self._create()
        self._populate(runtime)
        runtime.close()
        with self._raw() as raw:
            raw.execute(
                "UPDATE runtime_state SET payload_json = json_set(payload_json, '$.journal_record_digest', 'sha256:other')"
            )
        with self.assertRaisesRegex(RuntimeRecoveryError, "does not bind the journal tail"):
            self._recover()

    def test_tampered_index_alone_is_rebuilt_not_trusted(self) -> None:
        runtime = self._create()
        self._populate(runtime)
        runtime.close()
        with self._raw() as raw:
            raw.execute("UPDATE digest_rows SET row_hash = 'forged' WHERE rowid = (SELECT MIN(rowid) FROM digest_rows)")
        recovered = self._recover()
        try:
            self.assertFalse(recovered.substrate._digest_index_trusted)
            recovered.commit_proposal(
                _proposal("proposal:rebuild", operation="promotion", target_reference="memory:rebuild"), "rebuild"
            )
            self.assertEqual(self._recorded_digest(recovered), recovered.substrate.recompute_bucketed_digest())
        finally:
            recovered.close()
        again = self._recover()
        try:
            self.assertTrue(again.substrate._digest_index_trusted)
        finally:
            again.close()

    def test_legacy_full_digest_store_recovers_and_upgrades(self) -> None:
        with mock.patch.object(SQLiteTemporalGraph, "incremental_state_digest", SQLiteTemporalGraph.state_digest):
            runtime = self._create()
            self._populate(runtime)
            runtime.close()
        with self._raw() as raw:
            raw.execute("DELETE FROM digest_rows")
            raw.execute("DELETE FROM digest_buckets")
        recovered = self._recover()
        try:
            self.assertTrue(recovered.recovery_evidence.substrate_digest.startswith(LEGACY_DIGEST_PREFIX))
            recovered.commit_proposal(
                _proposal("proposal:upgrade", operation="promotion", target_reference="memory:upgrade"), "upgrade"
            )
            self.assertTrue(self._recorded_digest(recovered).startswith(f"{BUCKETED_DIGEST_SCHEME}:"))
        finally:
            recovered.close()
        upgraded = self._recover()
        try:
            self.assertIsNotNone(upgraded.adapter.current_fact_uuid("memory:upgrade"))
            # Mixed-scheme journal chains remain verifiable end to end.
            self.assertTrue(upgraded.substrate.read_runtime_journal()[0]["substrate_digest"].startswith(LEGACY_DIGEST_PREFIX))
        finally:
            upgraded.close()

    def test_tampered_legacy_store_refuses_recovery(self) -> None:
        with mock.patch.object(SQLiteTemporalGraph, "incremental_state_digest", SQLiteTemporalGraph.state_digest):
            runtime = self._create()
            facts = self._populate(runtime)
            runtime.close()
        with self._raw() as raw:
            raw.execute("UPDATE facts SET fact_text = 'forged' WHERE uuid = ?", (facts[0],))
        with self.assertRaisesRegex(RuntimeRecoveryError, "canonical substrate digest mismatch"):
            self._recover()

    def test_unknown_digest_scheme_refuses_recovery(self) -> None:
        runtime = self._create()
        runtime.close()
        with self._raw() as raw:
            raw.execute("UPDATE runtime_state SET payload_json = json_set(payload_json, '$.substrate_digest', 'md5:abc')")
        with self.assertRaises(RuntimeRecoveryError):
            self._recover()

    def test_stale_writer_still_conflicts(self) -> None:
        writer_a = self._create()
        writer_b = self._recover()
        try:
            self._populate(writer_a, count=1)
            with self.assertRaises(RuntimeCheckpointConflict):
                writer_b.commit_proposal(
                    _proposal("proposal:stale", operation="promotion", target_reference="memory:stale"), "stale"
                )
        finally:
            writer_a.close()
            writer_b.close()
        recovered = self._recover()
        try:
            self.assertEqual(self._recorded_digest(recovered), recovered.substrate.recompute_bucketed_digest())
        finally:
            recovered.close()

    def test_rolled_back_transaction_leaves_root_consistent(self) -> None:
        runtime = self._create()
        try:
            self._populate(runtime)

            def failing():
                runtime.substrate.add_episode(
                    Episode(uuid="episode:rolled-back", content="x", source_description="t", valid_at="2026-01-01T00:00:00Z", group_id="g")
                )
                raise ValueError("abort")

            with self.assertRaises(ValueError):
                runtime._transactional_operation(failing)
            self.assertIsNone(runtime.substrate.get_episode("episode:rolled-back"))
            runtime.commit_proposal(
                _proposal("proposal:after-rollback", operation="promotion", target_reference="memory:after-rollback"),
                "after rollback",
            )
            self.assertEqual(self._recorded_digest(runtime), runtime.substrate.recompute_bucketed_digest())
        finally:
            runtime.close()

    def test_unmapped_canonical_write_is_rejected(self) -> None:
        graph = SQLiteTemporalGraph(self.root / "direct.sqlite3")
        try:
            with self.assertRaisesRegex(RuntimeError, "no digest table mapping"):
                graph._log("rename_everything", "x")
        finally:
            graph.close()


if __name__ == "__main__":
    unittest.main()
