from __future__ import annotations

import hashlib
import json
import math
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
from agentmem_ref.substrate import Episode, Fact  # noqa: E402
from canonical_json_v2_migration_preflight import MigrationPreflightError  # noqa: E402
from canonical_json_v2_sqlite_preflight import qualify_sqlite_migration_preflight  # noqa: E402


TENANT = "tenant-acme"


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


def _create_source(root: Path, *, attributes: dict | None = None) -> tuple[Path, dict]:
    runtime = SQLiteRestartSafeRuntime.create(root, tenant=TENANT, profile=_profile())
    try:
        runtime.substrate.add_episode(
            Episode(
                uuid="episode:1",
                content="source observation",
                source_description="migration qualification",
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
                attributes=dict(attributes or {"priority": 1}),
            )
        )
        runtime.checkpoint()
        state = runtime.substrate.read_runtime_state()
        assert state is not None
        return runtime.database_path, state
    finally:
        runtime.close()


def _database_artifact_hashes(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if candidate.exists():
            result[candidate.name] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    return result


def _read_runtime_payload(path: Path) -> str:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT payload_json FROM runtime_state WHERE singleton = 1").fetchone()
        assert row is not None
        return str(row[0])
    finally:
        connection.close()


def _json_text(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class CanonicalJsonV2SQLitePreflightTests(unittest.TestCase):
    def test_current_sqlite_state_verifies_from_read_only_source_and_computes_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_root = base / "source"
            source_db, state = _create_source(source_root)
            before_payload = _read_runtime_payload(source_db)
            before_hashes = _database_artifact_hashes(source_db)

            result = qualify_sqlite_migration_preflight(
                source_database=source_db,
                snapshot_root=base / "snapshot",
            )

            evidence = result.evidence
            self.assertEqual(evidence.source_runtime_generation, int(state["generation"]))
            self.assertEqual(evidence.source_runtime_state_schema, "1.1.0")
            self.assertEqual(evidence.source_substrate_binding_id, "substrate-bmerkle-v1")
            self.assertEqual(evidence.source_governance_binding_id, "governance-gsect-v1")
            self.assertEqual(evidence.target_substrate_binding_id, "substrate-bmerkle-v2-candidate")
            self.assertEqual(evidence.target_governance_binding_id, "governance-gsect-v2-candidate")
            self.assertTrue(evidence.target_substrate_commitment.startswith("bmerkle-v2:"))
            self.assertTrue(evidence.target_governance_commitment.startswith("gsect-v2:"))
            self.assertTrue(evidence.pre_migration_logical_state_digest.startswith("sha256:"))
            self.assertTrue(evidence.source_store_read_only)
            self.assertEqual(evidence.source_open_mode, "sqlite_mode_ro")
            self.assertTrue(Path(evidence.snapshot_database).is_file())

            self.assertEqual(_read_runtime_payload(source_db), before_payload)
            self.assertEqual(_database_artifact_hashes(source_db), before_hashes)

    def test_tampered_substrate_row_refuses_during_existing_recovery_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_db, _ = _create_source(base / "source")
            connection = sqlite3.connect(str(source_db))
            try:
                connection.execute("UPDATE facts SET fact_text = ? WHERE uuid = ?", ("tampered", "fact:1"))
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(MigrationPreflightError) as caught:
                qualify_sqlite_migration_preflight(
                    source_database=source_db,
                    snapshot_root=base / "snapshot",
                )
            self.assertEqual(caught.exception.reason, "source_substrate_verification_failed")

    def test_tampered_governance_residual_refuses_during_existing_recovery_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_db, _ = _create_source(base / "source")
            connection = sqlite3.connect(str(source_db))
            try:
                connection.execute(
                    "UPDATE governance_residual SET value_json = ? WHERE singleton = 1",
                    (_json_text({"tampered": True}),),
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(MigrationPreflightError) as caught:
                qualify_sqlite_migration_preflight(
                    source_database=source_db,
                    snapshot_root=base / "snapshot",
                )
            self.assertEqual(caught.exception.reason, "source_governance_verification_failed")

    def test_broken_runtime_journal_chain_refuses_before_candidate_work(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_db, _ = _create_source(base / "source")
            connection = sqlite3.connect(str(source_db))
            try:
                row = connection.execute(
                    "SELECT generation, payload_json FROM runtime_journal ORDER BY generation DESC LIMIT 1"
                ).fetchone()
                assert row is not None
                record = json.loads(row[1])
                record["previous_record_digest"] = "broken-chain"
                connection.execute(
                    "UPDATE runtime_journal SET payload_json = ? WHERE generation = ?",
                    (_json_text(record), int(row[0])),
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(MigrationPreflightError) as caught:
                qualify_sqlite_migration_preflight(
                    source_database=source_db,
                    snapshot_root=base / "snapshot",
                )
            self.assertEqual(caught.exception.reason, "source_journal_or_envelope_verification_failed")

    def test_unknown_source_scheme_refuses_through_frozen_registry_before_candidate_work(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_db, _ = _create_source(base / "source")
            connection = sqlite3.connect(str(source_db))
            try:
                row = connection.execute("SELECT payload_json FROM runtime_state WHERE singleton = 1").fetchone()
                assert row is not None
                state = json.loads(row[0])
                state["substrate_digest"] = "mystery-v9:" + ("f" * 64)
                connection.execute(
                    "UPDATE runtime_state SET payload_json = ? WHERE singleton = 1",
                    (_json_text(state),),
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(MigrationPreflightError) as caught:
                qualify_sqlite_migration_preflight(
                    source_database=source_db,
                    snapshot_root=base / "snapshot",
                )
            self.assertEqual(caught.exception.reason, "source_scheme_binding_failed")

    def test_v1_accepted_nonfinite_fact_attribute_refuses_before_candidate_transaction(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_db, _ = _create_source(base / "source", attributes={"bad": math.nan})

            with self.assertRaises(MigrationPreflightError) as caught:
                qualify_sqlite_migration_preflight(
                    source_database=source_db,
                    snapshot_root=base / "snapshot",
                )
            self.assertEqual(caught.exception.reason, "candidate_value_domain_invalid")


if __name__ == "__main__":
    unittest.main()
