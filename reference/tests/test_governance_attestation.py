"""Incremental governance-state attestation for the SQLite runtime (#562).

Governance state used to be canonical-JSON serialized, hashed, and rewritten whole on
every generation (``full-json-v1``). It is now persisted as sections (``gsect-v1``):

* keyed map sections, committed by per-section bucketed roots;
* the append-only audit log, committed by a hash chain (count + head);
* a small residual, committed by one digest.

The three #522 layers stay distinct for governance too:

* per-generation integrity: only changed entries and appended records are written, and
  the journal record binds the resulting root;
* current-state commitment: bucket digests, log heads, and the residual digest are
  maintained incrementally (derived data, trusted only after rebuild or verification);
* recovery-time full verification: every entry hash, bucket, chain link, and the root
  are recomputed from the stored rows alone.

These tests prove equivalence with a full recomputation, locality, fail-closed recovery
under tampering, atomic publication, and explicit migration from full-json-v1.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.restart_runtime import RuntimeRecoveryError
from agentmem_ref.runtime import sqlite_runtime
from agentmem_ref.runtime.sqlite_runtime import (
    GOVERNANCE_SELF_CHECK_ENV,
    LEGACY_RUNTIME_STATE_SCHEMA_VERSION,
    SQLITE_RUNTIME_STATE_SCHEMA_VERSION,
    _assemble_governance,
    _digest,
    _journal_record,
    _validate_journal,
)
from agentmem_ref.state.sqlite_substrate import GOVERNANCE_SCHEME

TENANT = "tenant:gov"
SCOPE = "project:gov"


def _open(root: str) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id="agent:gov", scope=SCOPE, purpose="governance attestation")


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:gov-correction",
        version=1,
        purpose="correct retained test memory",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the correction against the current source.",
        provenance_refs=("evidence:gov-correction",),
    )
    return pm.evidence_for(skill)


def _base(memory: AgentMemory):
    return memory.runtime.durable_runtime.base


def _exercise(memory: AgentMemory) -> None:
    """remember, recall, correct (both kinds), forget, dispute: every governance section moves."""
    for index in range(6):
        memory.remember(f"memory:item-{index}", f"item {index} deploy window value {index}")
    memory.recall("deploy window value")
    memory.correct("memory:item-1", "item 1 corrected deploy window", evidence=_evidence(), risk_class="low")
    memory.correct(
        "memory:item-2", "item 2 moved deploy window", evidence=_evidence(), risk_class="low",
        replacement_kind="state_change",
    )
    memory.forget("memory:item-3")
    fact = memory.history("memory:item-4")["history"]["current_fact_uuid"]
    disputed = memory.dispute("memory:item-4", fact_uuid=fact, evidence=_evidence(), risk_class="low")
    if not disputed.get("committed"):
        raise AssertionError(f"governed dispute did not commit: {disputed}")
    memory.recall("item deploy")


class GovernanceAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = self.temp.name

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _db(self) -> Path:
        if not hasattr(self, "_db_path"):
            with _open(self.root) as memory:
                self._db_path = _base(memory).database_path
        return self._db_path

    def _raw(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db())

    def _state(self) -> dict:
        with self._raw() as raw:
            return json.loads(raw.execute("SELECT payload_json FROM runtime_state").fetchone()[0])

    def _refused(self, pattern: str = "") -> None:
        with self.assertRaisesRegex(RuntimeRecoveryError, pattern):
            _open(self.root).close()

    def _built(self) -> None:
        with _open(self.root) as memory:
            _exercise(memory)

    # -- equivalence and locality --

    def test_incremental_root_equals_full_recomputation_and_full_export(self):
        with _open(self.root) as memory:
            _exercise(memory)
            base = _base(memory)
            root = self._state()["governance_digest"]
            self.assertTrue(root.startswith(f"{GOVERNANCE_SCHEME}:"))
            loaded = base.substrate.governance.load_verified(root)
            self.assertEqual(_digest(_assemble_governance(loaded)), _digest(base._governance_snapshot()))
            before = _digest(base._governance_snapshot())
        with _open(self.root) as memory:
            self.assertEqual(_digest(_base(memory)._governance_snapshot()), before)

    def test_normal_operations_publish_changes_not_the_state(self):
        with _open(self.root) as memory:
            base = _base(memory)
            store = base.substrate.governance
            for index in range(20):
                memory.remember(f"memory:bulk-{index}", f"bulk value {index}")
            rewrites = store.full_rewrites
            events_before = store.log_count("events")
            statements = []
            with self._raw() as raw:
                changes_before = raw.total_changes
            base.substrate._connection.set_trace_callback(statements.append)
            try:
                memory.remember("memory:one-more", "one more value")
                memory.recall("bulk value")
            finally:
                base.substrate._connection.set_trace_callback(None)
            self.assertEqual(store.full_rewrites, rewrites, "no full governance rewrite on ordinary operations")
            self.assertGreater(store.log_count("events"), events_before)
            entry_writes = [s for s in statements if s.lstrip().upper().startswith("INSERT INTO GOVERNANCE_ENTRIES")]
            # remember touches fact_scope, fact_memory, current_fact_by_memory, state_version: one entry each.
            self.assertLessEqual(len(entry_writes), 4)
            self.assertFalse([s for s in statements if "DELETE FROM governance_" in s and "WHERE" not in s])
            state_writes = [s for s in statements if "INSERT INTO runtime_state" in s]
            self.assertTrue(all(len(s) < 4096 for s in state_writes), "runtime-state envelope no longer embeds governance")

    def test_restart_preserves_semantics_across_every_section(self):
        with _open(self.root) as memory:
            _exercise(memory)
            expected = {
                ref: memory.history(ref)["history"]
                for ref in ("memory:item-1", "memory:item-2", "memory:item-3", "memory:item-4")
            }
            recall_before = memory.recall("deploy window", reference_time="2030-01-01T00:00:00Z")
        with _open(self.root) as memory:
            for ref, history in expected.items():
                self.assertEqual(memory.history(ref)["history"], history)
            recall_after = memory.recall("deploy window", reference_time="2030-01-01T00:00:00Z")
            self.assertEqual(recall_after["admitted"], recall_before["admitted"])
            self.assertEqual(
                {k: v.get("refusal") for k, v in recall_after["admissions"].items()},
                {k: v.get("refusal") for k, v in recall_before["admissions"].items()},
            )

    # -- tamper model: recovery fails closed --

    def test_tampered_governance_entry_refuses_recovery(self):
        self._built()
        with self._raw() as raw:
            raw.execute(
                "UPDATE governance_entries SET value_json = '\"memory:forged\"' "
                "WHERE section = 'current_fact_by_memory' AND rowid = (SELECT MIN(rowid) FROM governance_entries "
                "WHERE section = 'current_fact_by_memory')"
            )
        self._refused("governance")

    def test_entry_with_recomputed_hash_still_refuses_recovery(self):
        # Syntactically valid and self-consistent, but semantically not what was committed.
        self._built()
        from agentmem_ref.state.sqlite_substrate import _governance_entry_hash

        with self._raw() as raw:
            section, key = raw.execute(
                "SELECT section, entry_key FROM governance_entries WHERE section = 'state_version' LIMIT 1"
            ).fetchone()
            value_json = "999"
            raw.execute(
                "UPDATE governance_entries SET value_json = ?, entry_hash = ? WHERE section = ? AND entry_key = ?",
                (value_json, _governance_entry_hash(section, key, value_json), section, key),
            )
        self._refused("commitment mismatch")

    def test_deleted_or_injected_entry_refuses_recovery(self):
        self._built()
        with self._raw() as raw:
            raw.execute("DELETE FROM governance_entries WHERE rowid = (SELECT MIN(rowid) FROM governance_entries)")
        self._refused("governance")

    def test_unknown_section_row_refuses_recovery(self):
        self._built()
        with self._raw() as raw:
            raw.execute(
                "INSERT INTO governance_entries(section, entry_key, bucket, value_json, entry_hash) "
                "VALUES('permissions', 'k', 0, 'true', 'x')"
            )
        self._refused("unknown governance section")

    def test_tampered_audit_log_record_refuses_recovery(self):
        self._built()
        with self._raw() as raw:
            raw.execute(
                "UPDATE governance_log SET value_json = json_set(value_json, '$.event_type', 'memory.forged') "
                "WHERE seq = 2"
            )
        self._refused("chain mismatch")

    def test_truncated_or_extended_audit_log_refuses_recovery(self):
        self._built()
        with self._raw() as raw:
            raw.execute("DELETE FROM governance_log WHERE seq = (SELECT MAX(seq) FROM governance_log)")
        self._refused("commitment mismatch")

    def test_forged_log_record_with_valid_chain_refuses_recovery(self):
        self._built()
        from agentmem_ref.state.sqlite_substrate import _governance_chain

        with self._raw() as raw:
            seq, chain = raw.execute(
                "SELECT seq, chain FROM governance_log WHERE section = 'events' ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            value_json = '{"event_type":"memory.forged"}'
            raw.execute(
                "INSERT INTO governance_log(section, seq, value_json, chain) VALUES('events', ?, ?, ?)",
                (seq + 1, value_json, _governance_chain("events", seq + 1, chain, value_json)),
            )
        self._refused("commitment mismatch")

    def test_tampered_residual_refuses_recovery(self):
        self._built()
        with self._raw() as raw:
            raw.execute("UPDATE governance_residual SET value_json = json_set(value_json, '$.tenant', 'tenant:other')")
        self._refused("commitment mismatch")

    def test_forged_root_in_runtime_state_refuses_recovery(self):
        self._built()
        with self._raw() as raw:
            raw.execute(
                "UPDATE runtime_state SET payload_json = json_set(payload_json, '$.governance_digest', 'gsect-v1:00')"
            )
        self._refused("governance")

    def test_journal_generation_binding_mismatch_refuses_recovery(self):
        self._built()
        with self._raw() as raw:
            raw.execute(
                "UPDATE runtime_journal SET payload_json = json_set(payload_json, '$.governance_digest', 'gsect-v1:00') "
                "WHERE generation = (SELECT MAX(generation) FROM runtime_journal)"
            )
        self._refused("journal")

    def test_stale_governance_rows_with_newer_journal_tail_refuse_recovery(self):
        with _open(self.root) as memory:
            memory.remember("memory:a", "first value")
            stale = Path(self.root) / "stale.sqlite3"
            _base(memory).backup_to(stale)
            memory.remember("memory:b", "second value")
            memory.recall("value")
        tables = ("governance_entries", "governance_buckets", "governance_log", "governance_residual")
        with self._raw() as raw:
            raw.execute("ATTACH DATABASE ? AS stale", (str(stale),))
            for table in tables:
                raw.execute(f"DELETE FROM main.{table}")
                raw.execute(f"INSERT INTO main.{table} SELECT * FROM stale.{table}")
            raw.commit()
            raw.execute("DETACH DATABASE stale")
        self._refused("commitment mismatch")

    def test_tampered_commitment_index_alone_is_rebuilt_not_trusted(self):
        # The bucket index is derived data: tampering with it cannot change a recovery
        # answer; the next publication rebuilds it from the verified entries.
        self._built()
        with self._raw() as raw:
            raw.execute("UPDATE governance_buckets SET digest = 'forged' WHERE rowid = (SELECT MIN(rowid) FROM governance_buckets)")
        with _open(self.root) as memory:
            store = _base(memory).substrate.governance
            self.assertFalse(store.trusted)
            rewrites = store.full_rewrites
            memory.remember("memory:after", "after tamper")
            self.assertEqual(store.full_rewrites, rewrites + 1)
            self.assertTrue(store.trusted)
        with self._raw() as raw:
            self.assertEqual(raw.execute("SELECT COUNT(*) FROM governance_buckets WHERE digest = 'forged'").fetchone()[0], 0)
        _open(self.root).close()

    def test_mixed_scheme_envelopes_are_refused_not_reinterpreted(self):
        self._built()
        with self._raw() as raw:
            raw.execute("UPDATE runtime_state SET payload_json = json_set(payload_json, '$.schema_version', '1.0.0')")
        self._refused("scheme does not match")
        with self._raw() as raw:
            raw.execute("UPDATE runtime_state SET payload_json = json_set(payload_json, '$.schema_version', '1.1.0', "
                        "'$.governance', json('{}'))")
        self._refused("scheme does not match")

    # -- atomicity --

    def test_failed_generation_publishes_neither_canonical_nor_governance_state(self):
        with _open(self.root) as memory:
            memory.remember("memory:a", "first value")
            base = _base(memory)
            before_state = self._state()
            with self._raw() as raw:
                entries_before = raw.execute("SELECT COUNT(*) FROM governance_entries").fetchone()[0]
                log_before = raw.execute("SELECT COUNT(*) FROM governance_log").fetchone()[0]
                facts_before = raw.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
            snapshot_before = _digest(base._governance_snapshot())
            with mock.patch.object(base.substrate, "append_runtime_journal", side_effect=RuntimeError("disk")):
                with self.assertRaises(RuntimeError):
                    memory.remember("memory:b", "second value")
            self.assertEqual(self._state(), before_state)
            with self._raw() as raw:
                self.assertEqual(raw.execute("SELECT COUNT(*) FROM governance_entries").fetchone()[0], entries_before)
                self.assertEqual(raw.execute("SELECT COUNT(*) FROM governance_log").fetchone()[0], log_before)
                self.assertEqual(raw.execute("SELECT COUNT(*) FROM facts").fetchone()[0], facts_before)
            self.assertEqual(_digest(base._governance_snapshot()), snapshot_before)
            # The handle continues from the committed generation with a consistent commitment.
            memory.remember("memory:c", "third value")
            root = self._state()["governance_digest"]
            loaded = base.substrate.governance.load_verified(root)
            self.assertEqual(_digest(_assemble_governance(loaded)), _digest(base._governance_snapshot()))
        _open(self.root).close()

    # -- self-check makes untracked governance mutation fail loudly --

    def test_untracked_in_place_edit_of_published_audit_is_caught_by_self_check(self):
        with _open(self.root) as memory:
            memory.remember("memory:a", "first value")
            base = _base(memory)
            base.adapter.events[0]["event_type"] = "memory.rewritten"  # in place, not via the log
            with mock.patch.dict(os.environ, {GOVERNANCE_SELF_CHECK_ENV: "1"}):
                with self.assertRaisesRegex(RuntimeRecoveryError, "diverged"):
                    memory.remember("memory:b", "second value")

    def test_non_append_log_edit_republishes_the_log_consistently(self):
        with _open(self.root) as memory:
            memory.remember("memory:a", "first value")
            base = _base(memory)
            store = base.substrate.governance
            rewrites = store.full_rewrites
            base.adapter.events.insert(0, {"event_type": "memory.inserted"})
            memory.remember("memory:b", "second value")
            self.assertEqual(store.full_rewrites, rewrites + 1)
        _open(self.root).close()


def _legacy_persist(self) -> sqlite_runtime.SQLiteRecoveryEvidence:
    """The pre-#562 full-json-v1 publication, reproduced to build legacy fixtures."""
    binding = self.substrate.read_runtime_binding()
    current_generation = 0 if binding is None else binding[0]
    governance = self._governance_snapshot()
    governance_digest = _digest(governance)
    substrate_digest = self.substrate.incremental_state_digest()
    generation = current_generation + 1
    tail = self.substrate.read_runtime_journal_tail()
    previous_digest = "" if tail is None else str(tail["record_digest"])
    record = _journal_record(
        generation=generation,
        substrate_digest=substrate_digest,
        governance_digest=governance_digest,
        interpretation_digest=self.profile.interpretation_digest,
        previous_record_digest=previous_digest,
    )
    self.substrate.write_runtime_state({
        "schema_version": LEGACY_RUNTIME_STATE_SCHEMA_VERSION,
        "durability_profile": sqlite_runtime.SQLITE_DURABILITY_PROFILE,
        "transaction_protocol": sqlite_runtime.SQLITE_TRANSACTION_PROTOCOL,
        "generation": generation,
        "profile": self.profile.to_dict(),
        "interpretation_digest": self.profile.interpretation_digest,
        "substrate_digest": substrate_digest,
        "governance_digest": governance_digest,
        "governance": governance,
        "substrate_identity": self.substrate.operational_identity(),
        "journal_record_digest": record["record_digest"],
    })
    self.substrate.append_runtime_journal(generation, record)
    return sqlite_runtime.SQLiteRecoveryEvidence(
        generation=generation,
        durability_profile=sqlite_runtime.SQLITE_DURABILITY_PROFILE,
        substrate_digest=substrate_digest,
        governance_digest=governance_digest,
        interpretation_digest=self.profile.interpretation_digest,
        recovered_visibility_operations=tuple(sorted(self.visibility_snapshots)),
        sqlite_version=self.substrate.sqlite_version,
    )


class LegacyGovernanceMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = self.temp.name
        with mock.patch.dict(os.environ, {GOVERNANCE_SELF_CHECK_ENV: "0"}), mock.patch.object(
            sqlite_runtime.SQLiteRestartSafeRuntime, "_persist_unlocked", _legacy_persist
        ):
            with _open(self.root) as memory:
                _exercise(memory)
                self.legacy_snapshot = _digest(_base(memory)._governance_snapshot())
                self.db = _base(memory).database_path

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _state(self) -> dict:
        with sqlite3.connect(self.db) as raw:
            return json.loads(raw.execute("SELECT payload_json FROM runtime_state").fetchone()[0])

    def test_fixture_is_a_full_json_v1_store(self):
        state = self._state()
        self.assertEqual(state["schema_version"], LEGACY_RUNTIME_STATE_SCHEMA_VERSION)
        self.assertTrue(state["governance_digest"].startswith("sha256:"))
        self.assertIn("governance", state)

    def test_legacy_store_recovers_then_migrates_atomically_at_the_next_generation(self):
        with _open(self.root) as memory:
            base = _base(memory)
            self.assertEqual(_digest(base._governance_snapshot()), self.legacy_snapshot)
            legacy_generation = self._state()["generation"]
            memory.remember("memory:after-migration", "value after migration")
            state = self._state()
            self.assertEqual(state["schema_version"], SQLITE_RUNTIME_STATE_SCHEMA_VERSION)
            self.assertEqual(state["governance_scheme"], GOVERNANCE_SCHEME)
            self.assertNotIn("governance", state)
            self.assertTrue(state["governance_digest"].startswith(f"{GOVERNANCE_SCHEME}:"))
            self.assertEqual(state["generation"], legacy_generation + 1)
            migrated_snapshot = _digest(base._governance_snapshot())
        with sqlite3.connect(self.db) as raw:
            records = [json.loads(row[0]) for row in raw.execute("SELECT payload_json FROM runtime_journal ORDER BY generation")]
        # Historical records keep their full-json-v1 commitments; the chain verifies end to end.
        schemes = [record["governance_digest"].split(":", 1)[0] for record in records]
        self.assertEqual(schemes[:legacy_generation], ["sha256"] * legacy_generation)
        self.assertEqual(schemes[legacy_generation:], [GOVERNANCE_SCHEME])
        self.assertIsNotNone(_validate_journal(records))
        with _open(self.root) as memory:
            self.assertEqual(_digest(_base(memory)._governance_snapshot()), migrated_snapshot)

    def test_tampered_legacy_governance_refuses_recovery(self):
        with sqlite3.connect(self.db) as raw:
            raw.execute(
                "UPDATE runtime_state SET payload_json = json_set(payload_json, '$.governance.adapter.clock_tick', 1)"
            )
        with self.assertRaisesRegex(RuntimeRecoveryError, "governance state digest mismatch"):
            _open(self.root).close()

    def test_failed_migration_generation_leaves_the_legacy_store_intact(self):
        with _open(self.root) as memory:
            base = _base(memory)
            with mock.patch.object(base.substrate, "append_runtime_journal", side_effect=RuntimeError("disk")):
                with self.assertRaises(RuntimeError):
                    memory.remember("memory:x", "never committed")
        state = self._state()
        self.assertEqual(state["schema_version"], LEGACY_RUNTIME_STATE_SCHEMA_VERSION)
        with sqlite3.connect(self.db) as raw:
            self.assertEqual(raw.execute("SELECT COUNT(*) FROM governance_entries").fetchone()[0], 0)
        with _open(self.root) as memory:
            self.assertEqual(_digest(_base(memory)._governance_snapshot()), self.legacy_snapshot)

    def test_backup_of_a_migrated_store_recovers(self):
        with _open(self.root) as memory:
            memory.remember("memory:after-migration", "value")
            target = Path(self.root) / "backup" / "agent-memory.sqlite3"
            _base(memory).backup_to(target)
        shutil.copy(target, self.db)
        _open(self.root).close()


if __name__ == "__main__":
    unittest.main()
