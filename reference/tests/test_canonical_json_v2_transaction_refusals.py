from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_json_v2_candidate import canonical_bytes_v2  # noqa: E402
from canonical_json_v2_migration_preflight import compute_candidate_commitments  # noqa: E402
from canonical_json_v2_restart_qualification import qualify_candidate_v2_restart  # noqa: E402
from canonical_json_v2_transaction_qualification import (  # noqa: E402
    CandidateMigrationError,
    _candidate_journal_record,
    _canonical_digest,
    _read_logical_state,
    _rebuild_substrate_index,
    transactional_recommit_candidate_v2,
)
from canonical_scheme_registry_candidate import CandidateSchemeRegistry, SchemeRegistryError  # noqa: E402

try:  # Support repo-root targeted execution and reference-root discovery.
    from reference.tests.test_canonical_json_v2_transaction_qualification import (  # noqa: E402
        _fresh_preflight,
        _runtime_state,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised by alternate discovery root
    from tests.test_canonical_json_v2_transaction_qualification import (  # type: ignore[no-redef]  # noqa: E402
        _fresh_preflight,
        _runtime_state,
    )


LEGACY_CANONICALIZER = "legacy-python-sorted-json-v1"
CANDIDATE_CANONICALIZER = "agent-memory-canonical-json-v2"
LEGACY_SUBSTRATE_ROOT = "substrate-bucketed-merkle-sha256-v1"
CANDIDATE_SUBSTRATE_ROOT = "substrate-bucketed-merkle-sha256-v2-candidate"


def _write_canonical_runtime_state(connection: sqlite3.Connection, state: dict) -> None:
    connection.execute(
        "UPDATE runtime_state SET payload_json = ? WHERE singleton = 1",
        (canonical_bytes_v2(state).decode("utf-8"),),
    )


class CanonicalJsonV2TransactionRefusalTests(unittest.TestCase):
    def test_legacy_scheme_cannot_be_reinterpreted_with_v2_canonicalizer(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            registry = CandidateSchemeRegistry.from_frozen_fixture()

            with self.assertRaises(SchemeRegistryError) as caught:
                registry.resolve(
                    operation="verify",
                    domain="substrate_state",
                    recorded_commitment=preflight.evidence.source_substrate_commitment,
                    requested_canonicalizer=CANDIDATE_CANONICALIZER,
                    requested_root_contract=LEGACY_SUBSTRATE_ROOT,
                    runtime_state_schema=preflight.evidence.source_runtime_state_schema,
                )
            self.assertEqual(caught.exception.reason, "canonicalizer_mismatch")

    def test_candidate_scheme_cannot_be_verified_under_legacy_runtime_envelope(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            registry = CandidateSchemeRegistry.from_frozen_fixture()

            with self.assertRaises(SchemeRegistryError) as caught:
                registry.resolve(
                    operation="verify",
                    domain="substrate_state",
                    recorded_commitment=preflight.evidence.target_substrate_commitment,
                    requested_canonicalizer=CANDIDATE_CANONICALIZER,
                    requested_root_contract=CANDIDATE_SUBSTRATE_ROOT,
                    runtime_state_schema=preflight.evidence.source_runtime_state_schema,
                )
            self.assertEqual(caught.exception.reason, "runtime_schema_binding_mismatch")

    def test_candidate_rows_with_legacy_runtime_schema_refuse_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            connection = sqlite3.connect(str(candidate_db))
            try:
                state = _runtime_state(candidate_db)
                state["schema_version"] = preflight.evidence.source_runtime_state_schema
                _write_canonical_runtime_state(connection, state)
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_runtime_schema_mismatch")

    def test_mixed_source_candidate_generation_refuses_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            connection = sqlite3.connect(str(candidate_db))
            try:
                state = _runtime_state(candidate_db)
                state["generation"] = int(state["generation"]) + 1
                _write_canonical_runtime_state(connection, state)
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_generation_mismatch")

    def test_provenance_presence_cannot_authorize_invalid_candidate_commitment(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            connection = sqlite3.connect(str(candidate_db))
            try:
                state = _runtime_state(candidate_db)
                state["substrate_digest"] = "bmerkle-v2:" + ("0" * 64)
                _write_canonical_runtime_state(connection, state)
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_substrate_commitment_mismatch")

    def test_self_consistent_forged_candidate_and_provenance_cannot_override_preflight_target(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, preflight = _fresh_preflight(base)
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            connection = sqlite3.connect(str(candidate_db), isolation_level=None)
            connection.row_factory = sqlite3.Row
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "UPDATE facts SET fact_text = ? WHERE uuid = ?",
                    ("forged deploy window is Friday", "fact:1"),
                )
                substrate, maps, logs, residual = _read_logical_state(connection, require_exact_v2=True)
                _rebuild_substrate_index(connection, substrate)
                forged = compute_candidate_commitments(
                    substrate_state=substrate,
                    governance_maps=maps,
                    governance_logs=logs,
                    governance_residual=residual,
                )
                self.assertNotEqual(
                    forged.substrate_commitment,
                    preflight.evidence.target_substrate_commitment,
                )
                self.assertNotEqual(
                    forged.logical_state_digest,
                    preflight.evidence.pre_migration_logical_state_digest,
                )

                provenance_row = connection.execute(
                    "SELECT payload_json FROM canonicalization_migration WHERE singleton = 1"
                ).fetchone()
                assert provenance_row is not None
                provenance = json.loads(provenance_row["payload_json"])
                provenance["target_substrate_commitment"] = forged.substrate_commitment
                provenance["pre_migration_logical_state_digest"] = forged.logical_state_digest
                provenance["post_migration_logical_state_digest"] = forged.logical_state_digest
                provenance_digest = _canonical_digest(provenance)
                connection.execute(
                    "UPDATE canonicalization_migration SET payload_json = ? WHERE singleton = 1",
                    (canonical_bytes_v2(provenance).decode("utf-8"),),
                )

                state_row = connection.execute(
                    "SELECT payload_json FROM runtime_state WHERE singleton = 1"
                ).fetchone()
                assert state_row is not None
                state = json.loads(state_row["payload_json"])
                state["substrate_digest"] = forged.substrate_commitment
                state["migration_provenance_digest"] = provenance_digest

                journal_row = connection.execute(
                    "SELECT generation, payload_json FROM runtime_journal ORDER BY generation DESC LIMIT 1"
                ).fetchone()
                assert journal_row is not None
                journal = json.loads(journal_row["payload_json"])
                forged_journal = _candidate_journal_record(
                    generation=int(journal["generation"]),
                    substrate_digest=forged.substrate_commitment,
                    governance_digest=str(journal["governance_digest"]),
                    interpretation_digest=str(journal["interpretation_digest"]),
                    previous_record_digest=str(journal["previous_record_digest"]),
                    migration_provenance_digest=provenance_digest,
                )
                connection.execute(
                    "UPDATE runtime_journal SET payload_json = ? WHERE generation = ?",
                    (canonical_bytes_v2(forged_journal).decode("utf-8"), int(journal_row["generation"])),
                )
                state["journal_record_digest"] = forged_journal["record_digest"]
                _write_canonical_runtime_state(connection, state)
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                connection.close()

            # Rows, derived index, envelope, final journal and provenance now agree
            # with one another. The frozen phase-3 preflight target still wins.
            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_substrate_commitment_mismatch")


if __name__ == "__main__":
    unittest.main()
