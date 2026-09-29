from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentmem_ref.restart_runtime import CapabilityBinding, RuntimeProfile  # noqa: E402
from agentmem_ref.sqlite_runtime import SQLiteRestartSafeRuntime  # noqa: E402
from agentmem_ref.substrate import Episode, Fact, TypedRelation  # noqa: E402
from canonical_json_v2_candidate import canonical_bytes_v2  # noqa: E402
from canonical_json_v2_restart_qualification import (  # noqa: E402
    prove_production_runtime_refusal,
    qualify_candidate_v2_restart,
)
from canonical_json_v2_sqlite_preflight import qualify_sqlite_migration_preflight  # noqa: E402
from canonical_json_v2_transaction_qualification import (  # noqa: E402
    CandidateMigrationError,
    InjectedMigrationFailure,
    QUALIFICATION_RUNTIME_STATE_SCHEMA,
    TRANSACTION_OUTCOME,
    transactional_recommit_candidate_v2,
)


TENANT = "tenant-acme"
PHASE4_FAULTS = (
    "before_transaction",
    "after_persisted_byte_rewrite",
    "after_derived_integrity_rebuild",
    "after_provenance_write",
    "before_envelope_and_journal",
    "after_envelope_before_journal",
    "before_commit",
)


def _binding() -> CapabilityBinding:
    return CapabilityBinding(
        component_id="reference-governed-memory",
        component_version="1.0.0",
        capability_id="governed-memory-core",
        capability_version="1.0.0",
        maturity="reference_qualified",
        evidence_ref="evidence:reference-runtime-core-v1",
    )


def _profile() -> RuntimeProfile:
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="reference-project-memory",
        profile_version="1.0.0",
        bindings=(_binding(),),
    )


def _create_source(root: Path) -> tuple[Path, dict]:
    runtime = SQLiteRestartSafeRuntime.create(root, tenant=TENANT, profile=_profile())
    try:
        runtime.substrate.add_episode(
            Episode(
                uuid="episode:1",
                content="source observation",
                source_description="transaction qualification",
                valid_at="2026-09-29T00:00:00Z",
                group_id=TENANT,
            )
        )
        runtime.substrate.write_fact(
            Fact(
                uuid="fact:1",
                fact_text="deploy window is Thursday",
                group_id=TENANT,
                episode_uuids=("episode:1",),
                attributes={"float_boundary": 1e20, "priority": 1},
            )
        )
        runtime.substrate.write_fact(
            Fact(
                uuid="fact:2",
                fact_text="deploy owner is platform",
                group_id=TENANT,
                episode_uuids=("episode:1",),
                attributes={"team": "platform"},
            )
        )
        runtime.substrate.write_relation(
            TypedRelation(
                relation_id="relation:1",
                source_uuid="fact:1",
                target_uuid="fact:2",
                relation_type="supports",
                group_id=TENANT,
                evidence_refs=("episode:1",),
                retrieval_weight=0.75,
                attributes={"kind": "qualification"},
            )
        )
        runtime.checkpoint()
        state = runtime.substrate.read_runtime_state()
        assert state is not None
        return runtime.database_path, state
    finally:
        runtime.close()


def _database_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_one(path: Path, query: str, parameters: tuple = ()) -> tuple:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        row = connection.execute(query, parameters).fetchone()
        assert row is not None
        return tuple(row)
    finally:
        connection.close()


def _runtime_state(path: Path) -> dict:
    return json.loads(_read_one(path, "SELECT payload_json FROM runtime_state WHERE singleton = 1")[0])


def _provenance(path: Path) -> dict:
    return json.loads(_read_one(path, "SELECT payload_json FROM canonicalization_migration WHERE singleton = 1")[0])


def _fresh_preflight(base: Path):
    source_db, source_state = _create_source(base / "source")
    result = qualify_sqlite_migration_preflight(
        source_database=source_db,
        snapshot_root=base / "candidate",
    )
    return source_db, source_state, result


class CanonicalJsonV2TransactionQualificationTests(unittest.TestCase):
    def test_full_transaction_and_restart_qualification_preserve_source_and_logical_state(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_db, source_state, preflight = _fresh_preflight(base)
            source_before = _database_hash(source_db)

            transaction = transactional_recommit_candidate_v2(preflight)
            self.assertEqual(transaction.source_generation, int(source_state["generation"]))
            self.assertEqual(transaction.migration_generation, int(source_state["generation"]) + 1)
            self.assertEqual(transaction.substrate_commitment, preflight.evidence.target_substrate_commitment)
            self.assertEqual(transaction.governance_commitment, preflight.evidence.target_governance_commitment)
            self.assertEqual(transaction.logical_state_digest, preflight.evidence.pre_migration_logical_state_digest)
            self.assertEqual(transaction.transaction_outcome, TRANSACTION_OUTCOME)

            candidate_db = Path(preflight.evidence.snapshot_database)
            state_after_transaction = _runtime_state(candidate_db)
            provenance_after_transaction = _provenance(candidate_db)
            self.assertEqual(state_after_transaction["schema_version"], QUALIFICATION_RUNTIME_STATE_SCHEMA)
            self.assertEqual(state_after_transaction["profile"], source_state["profile"])
            self.assertEqual(state_after_transaction["interpretation_digest"], source_state["interpretation_digest"])
            self.assertEqual(state_after_transaction["substrate_identity"], source_state["substrate_identity"])
            self.assertEqual(provenance_after_transaction["transaction_outcome"], TRANSACTION_OUTCOME)
            self.assertNotIn("restart_verified", provenance_after_transaction)
            self.assertNotIn("outcome", provenance_after_transaction)

            before_phase5_db_hash = _database_hash(candidate_db)
            qualification = qualify_candidate_v2_restart(preflight)
            after_phase5_db_hash = _database_hash(candidate_db)

            self.assertTrue(qualification.restart_verified)
            self.assertEqual(qualification.outcome, "committed")
            self.assertEqual(qualification.authority_effect, "none")
            self.assertFalse(qualification.durable_runtime_write)
            self.assertEqual(qualification.generation, int(source_state["generation"]) + 1)
            self.assertEqual(qualification.substrate_commitment, preflight.evidence.target_substrate_commitment)
            self.assertEqual(qualification.governance_commitment, preflight.evidence.target_governance_commitment)
            self.assertEqual(qualification.logical_state_digest, preflight.evidence.pre_migration_logical_state_digest)
            self.assertEqual(_runtime_state(candidate_db), state_after_transaction)
            self.assertEqual(_provenance(candidate_db), provenance_after_transaction)
            self.assertEqual(_database_hash(source_db), source_before)
            self.assertEqual(after_phase5_db_hash, before_phase5_db_hash)

    def test_every_phase4_fault_rolls_back_to_old_verified_state(self):
        for fault in PHASE4_FAULTS:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                _, source_state, preflight = _fresh_preflight(base)
                candidate_db = Path(preflight.evidence.snapshot_database)
                before_db_hash = _database_hash(candidate_db)

                with self.assertRaises(InjectedMigrationFailure) as caught:
                    transactional_recommit_candidate_v2(preflight, fault=fault)
                self.assertEqual(caught.exception.point, fault)

                repeated = qualify_sqlite_migration_preflight(
                    source_database=candidate_db,
                    snapshot_root=base / f"reverify-{fault}",
                )
                self.assertEqual(repeated.evidence.source_runtime_generation, int(source_state["generation"]))
                self.assertEqual(repeated.evidence.source_substrate_commitment, preflight.evidence.source_substrate_commitment)
                self.assertEqual(repeated.evidence.source_governance_commitment, preflight.evidence.source_governance_commitment)
                self.assertEqual(
                    repeated.evidence.pre_migration_logical_state_digest,
                    preflight.evidence.pre_migration_logical_state_digest,
                )
                self.assertEqual(_database_hash(candidate_db), before_db_hash)

    def test_phase5_injected_failure_never_records_final_committed_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)
            state_before = _runtime_state(candidate_db)
            provenance_before = _provenance(candidate_db)
            db_hash_before = _database_hash(candidate_db)

            with self.assertRaises(InjectedMigrationFailure) as caught:
                qualify_candidate_v2_restart(
                    preflight,
                    fault="during_phase5_restart_verification",
                    prove_production_refusal=False,
                )
            self.assertEqual(caught.exception.point, "during_phase5_restart_verification")
            self.assertEqual(_runtime_state(candidate_db), state_before)
            self.assertEqual(_provenance(candidate_db), provenance_before)
            self.assertEqual(_database_hash(candidate_db), db_hash_before)
            self.assertEqual(provenance_before["transaction_outcome"], TRANSACTION_OUTCOME)
            self.assertNotIn("committed", provenance_before.values())

    def test_production_runtime_refusal_is_proved_on_second_disposable_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)
            candidate_hash_before = _database_hash(candidate_db)

            evidence = prove_production_runtime_refusal(preflight)

            self.assertTrue(evidence.production_recovery_refused)
            self.assertEqual(evidence.tested_database_kind, "disposable_backup")
            self.assertEqual(_database_hash(candidate_db), candidate_hash_before)

    def test_candidate_scheme_with_legacy_json_bytes_refuses_even_when_json_value_is_equal(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            connection = sqlite3.connect(str(candidate_db))
            try:
                row = connection.execute("SELECT attributes_json FROM facts WHERE uuid = 'fact:1'").fetchone()
                assert row is not None
                v2_text = str(row[0])
                value = json.loads(v2_text)
                legacy_text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                self.assertNotEqual(legacy_text, v2_text)
                self.assertEqual(json.loads(legacy_text), json.loads(v2_text))
                connection.execute("UPDATE facts SET attributes_json = ? WHERE uuid = 'fact:1'", (legacy_text,))
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_persisted_bytes_not_v2")

    def test_candidate_derived_index_tamper_refuses_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            connection = sqlite3.connect(str(candidate_db))
            try:
                connection.execute("UPDATE digest_buckets SET digest = ? WHERE bucket = 0", ("tampered",))
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_substrate_index_mismatch")

    def test_migration_provenance_tamper_refuses_even_if_json_remains_canonical(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            connection = sqlite3.connect(str(candidate_db))
            try:
                row = connection.execute("SELECT payload_json FROM canonicalization_migration WHERE singleton = 1").fetchone()
                assert row is not None
                value = json.loads(row[0])
                value["migration_implementation_id"] = "tampered"
                connection.execute(
                    "UPDATE canonicalization_migration SET payload_json = ? WHERE singleton = 1",
                    (canonical_bytes_v2(value).decode("utf-8"),),
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_migration_provenance_mismatch")

    def test_candidate_journal_provenance_binding_tamper_refuses_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            connection = sqlite3.connect(str(candidate_db))
            try:
                row = connection.execute(
                    "SELECT generation, payload_json FROM runtime_journal ORDER BY generation DESC LIMIT 1"
                ).fetchone()
                assert row is not None
                value = json.loads(row[1])
                value["migration_provenance_digest"] = "sha256:" + ("0" * 64)
                connection.execute(
                    "UPDATE runtime_journal SET payload_json = ? WHERE generation = ?",
                    (canonical_bytes_v2(value).decode("utf-8"), int(row[0])),
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_journal_provenance_binding_broken")


if __name__ == "__main__":
    unittest.main()
