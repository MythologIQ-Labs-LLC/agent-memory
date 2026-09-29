from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import canonical_json_v2_restart_qualification as restart_module  # noqa: E402
import validate_canonical_json_v2_transaction_qualification_contract as contract  # noqa: E402
import canonical_json_v2_transaction_qualification as transaction_module  # noqa: E402
from agentmem_ref.restart_runtime import CapabilityBinding, RuntimeProfile, RuntimeRecoveryError  # noqa: E402
from agentmem_ref.sqlite_runtime import (  # noqa: E402
    SQLiteRestartSafeRuntime,
    _canonical_bytes as legacy_canonical_bytes,
    _digest as legacy_digest,
    _validate_journal,
)
from canonical_json_v2_candidate import canonical_bytes_v2  # noqa: E402
from canonical_json_v2_restart_qualification import (  # noqa: E402
    EXPECTED_PRODUCTION_REFUSAL_REASON,
    prove_production_runtime_refusal,
    qualify_candidate_v2_restart,
)
from canonical_json_v2_sqlite_preflight import historical_journal_anchor_digest  # noqa: E402
from canonical_json_v2_transaction_qualification import (  # noqa: E402
    CANDIDATE_JOURNAL_FIELDS,
    CANDIDATE_JOURNAL_MATERIAL_FIELDS,
    CANDIDATE_RUNTIME_STATE_FIELDS,
    CandidateMigrationError,
    _canonical_digest,
    transactional_recommit_candidate_v2,
)

try:  # Support repo-root targeted execution and reference-root discovery.
    from reference.tests.test_canonical_json_v2_transaction_qualification import (  # noqa: E402
        _database_hash,
        _fresh_preflight,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised by alternate discovery root
    from tests.test_canonical_json_v2_transaction_qualification import (  # type: ignore[no-redef]  # noqa: E402
        _database_hash,
        _fresh_preflight,
    )


LEGACY_JOURNAL_MATERIAL_FIELDS = (
    "schema_version",
    "transaction_protocol",
    "generation",
    "substrate_digest",
    "governance_digest",
    "interpretation_digest",
    "previous_record_digest",
)
FIXTURE = ROOT / "fixtures/runtime/canonical-json-v2-transaction-qualification-v1.json"
AMENDMENT = ROOT / "fixtures/runtime/canonical-json-v2-transaction-qualification-v1-amendment-1.json"


def _mutate(path: Path, change: Callable[[sqlite3.Connection], None]) -> None:
    connection = sqlite3.connect(str(path), isolation_level=None)
    try:
        connection.execute("BEGIN IMMEDIATE")
        change(connection)
        connection.execute("COMMIT")
    finally:
        connection.close()


def _journal(connection: sqlite3.Connection) -> list[tuple[int, str]]:
    return [(int(g), str(p)) for g, p in connection.execute("SELECT generation, payload_json FROM runtime_journal ORDER BY generation")]


def _state(connection: sqlite3.Connection) -> dict:
    return json.loads(connection.execute("SELECT payload_json FROM runtime_state WHERE singleton = 1").fetchone()[0])


def _write_state(connection: sqlite3.Connection, state: dict, *, v2: bool) -> None:
    encoded = canonical_bytes_v2(state) if v2 else legacy_canonical_bytes(state)
    connection.execute("UPDATE runtime_state SET payload_json = ? WHERE singleton = 1", (encoded.decode("utf-8"),))


def _write_journal(connection: sqlite3.Connection, generation: int, record: dict, *, v2: bool) -> None:
    encoded = canonical_bytes_v2(record) if v2 else legacy_canonical_bytes(record)
    connection.execute(
        "UPDATE runtime_journal SET payload_json = ? WHERE generation = ?", (encoded.decode("utf-8"), generation)
    )


def _rebuild_candidate_tail(connection: sqlite3.Connection, edit_final=None, edit_state=None, extra_material=()) -> None:
    """Rebuild final candidate record digest and envelope binding around an edit."""

    generation, text = _journal(connection)[-1]
    final = json.loads(text)
    state = _state(connection)
    if edit_final is not None:
        edit_final(final)
    material_fields = (*CANDIDATE_JOURNAL_MATERIAL_FIELDS, *extra_material)
    final["record_digest"] = _canonical_digest({key: final[key] for key in material_fields if key in final})
    _write_journal(connection, generation, final, v2=True)
    state["journal_record_digest"] = final["record_digest"]
    for field in ("substrate_digest", "governance_digest", "interpretation_digest"):
        if field in final:
            state[field] = final[field]
    if edit_state is not None:
        edit_state(state)
    _write_state(connection, state, v2=True)


def _forge_history(connection: sqlite3.Connection, rows: list[tuple[int, str]]) -> str:
    """Modify every historical record and recompute the full legacy chain."""

    previous = ""
    for generation, text in rows:
        record = json.loads(text)
        record["substrate_digest"] = "sha256:" + hashlib.sha256(f"forged-{generation}".encode()).hexdigest()
        record["previous_record_digest"] = previous
        record["record_digest"] = legacy_digest({key: record[key] for key in LEGACY_JOURNAL_MATERIAL_FIELDS})
        _write_journal(connection, generation, record, v2=False)
        previous = record["record_digest"]
    return previous


def _reserialize_history(connection: sqlite3.Connection, rows: list[tuple[int, str]]) -> None:
    for generation, text in rows:
        value = json.loads(text)
        reserialized = json.dumps(value, sort_keys=False, indent=1, ensure_ascii=True)
        assert reserialized != text and json.loads(reserialized) == value
        connection.execute("UPDATE runtime_journal SET payload_json = ? WHERE generation = ?", (reserialized, generation))


class HistoricalJournalAnchorTests(unittest.TestCase):
    def test_phase5_refuses_fully_rewritten_self_consistent_legacy_history(self):
        with tempfile.TemporaryDirectory() as temp:
            _, _, preflight = _fresh_preflight(Path(temp))
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            def forge(connection: sqlite3.Connection) -> None:
                historical = _journal(connection)[:-1]
                self.assertGreaterEqual(len(historical), 1)
                tail = _forge_history(connection, historical)
                _rebuild_candidate_tail(connection, edit_final=lambda final: final.update(previous_record_digest=tail))
                forged = [json.loads(text) for _, text in _journal(connection)[:-1]]
                # The forged legacy chain is internally valid under the legacy validator.
                self.assertEqual(_validate_journal(forged)["record_digest"], tail)
                for original, rewritten in zip(historical, forged):
                    self.assertNotEqual(json.loads(original[1]), rewritten)

            _mutate(candidate_db, forge)
            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_historical_journal_anchor_mismatch")

    def test_phase5_refuses_equal_value_reserialized_history(self):
        with tempfile.TemporaryDirectory() as temp:
            _, _, preflight = _fresh_preflight(Path(temp))
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)

            def reserialize(connection: sqlite3.Connection) -> None:
                historical = _journal(connection)[:-1]
                _reserialize_history(connection, historical)
                after = _journal(connection)[:-1]
                # Same decoded values, same legacy record digests, still a valid chain.
                self.assertEqual([json.loads(t) for _, t in after], [json.loads(t) for _, t in historical])
                _validate_journal([json.loads(t) for _, t in after])

            _mutate(candidate_db, reserialize)
            with self.assertRaises(CandidateMigrationError) as caught:
                qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
            self.assertEqual(caught.exception.reason, "candidate_historical_journal_anchor_mismatch")

    def test_phase4_rechecks_history_anchor_inside_transaction(self):
        for label, tamper in (
            ("reserialized", lambda c: _reserialize_history(c, _journal(c))),
            ("rewritten_chain", "forge"),
        ):
            with self.subTest(tamper=label), tempfile.TemporaryDirectory() as temp:
                _, _, preflight = _fresh_preflight(Path(temp))
                candidate_db = Path(preflight.evidence.snapshot_database)

                def apply(connection: sqlite3.Connection) -> None:
                    if tamper == "forge":
                        tail = _forge_history(connection, _journal(connection))
                        state = _state(connection)
                        state["journal_record_digest"] = tail
                        _write_state(connection, state, v2=False)
                    else:
                        tamper(connection)

                _mutate(candidate_db, apply)
                before = _database_hash(candidate_db)
                # Simulate the copy changing after the out-of-transaction reverify.
                with mock.patch.object(transaction_module, "_reverify_old_copy", lambda preflight: None):
                    with self.assertRaises(CandidateMigrationError) as caught:
                        transactional_recommit_candidate_v2(preflight)
                self.assertEqual(caught.exception.reason, "source_historical_journal_anchor_mismatch")
                self.assertEqual(_database_hash(candidate_db), before)

    def test_phase4_reverify_refuses_changed_history_anchor(self):
        with tempfile.TemporaryDirectory() as temp:
            _, _, preflight = _fresh_preflight(Path(temp))
            candidate_db = Path(preflight.evidence.snapshot_database)
            _mutate(candidate_db, lambda c: _reserialize_history(c, _journal(c)))
            with self.assertRaises(CandidateMigrationError) as caught:
                transactional_recommit_candidate_v2(preflight)
            self.assertEqual(caught.exception.reason, "source_identity_anchor_changed_before_transaction")

    def test_phase3_history_anchor_is_framed_over_raw_bytes_and_sql_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            _, source_state, preflight = _fresh_preflight(Path(temp))
            evidence = preflight.evidence
            connection = sqlite3.connect(evidence.snapshot_database)
            try:
                raw = [
                    (int(g), bytes(p))
                    for g, p in connection.execute(
                        "SELECT generation, CAST(payload_json AS BLOB) FROM runtime_journal ORDER BY generation"
                    )
                ]
            finally:
                connection.close()
            self.assertEqual(evidence.historical_journal_row_count, int(source_state["generation"]))
            self.assertEqual(evidence.historical_journal_digest, historical_journal_anchor_digest(raw))
            self.assertEqual(evidence.source_journal_tail_record_digest, source_state["journal_record_digest"])
            self.assertEqual(evidence.source_interpretation_digest, source_state["interpretation_digest"])
            # Framing: moving a byte across a row boundary or renumbering changes the digest.
            first_generation, first_payload = raw[0]
            self.assertNotEqual(
                historical_journal_anchor_digest([(first_generation + 1, first_payload), *raw[1:]]),
                evidence.historical_journal_digest,
            )
            self.assertNotEqual(
                historical_journal_anchor_digest([(first_generation, first_payload + b" "), *raw[1:]]),
                evidence.historical_journal_digest,
            )


class EnvelopeIdentityAnchorTests(unittest.TestCase):
    def test_phase5_refuses_changed_preserved_identity_with_consistent_rebuild(self):
        def profile(connection: sqlite3.Connection) -> None:
            state = _state(connection)
            state["profile"]["profile_version"] = "9.9.9"
            raw = state["profile"]
            rebuilt = RuntimeProfile(
                runtime_version=raw["runtime_version"],
                profile_id=raw["profile_id"],
                profile_version=raw["profile_version"],
                bindings=tuple(CapabilityBinding(**binding) for binding in raw["bindings"]),
            )
            # Journal + envelope are rebuilt consistently around the changed profile.
            digest = rebuilt.interpretation_digest
            _rebuild_candidate_tail(
                connection,
                edit_final=lambda final: final.update(interpretation_digest=digest),
                edit_state=lambda s: s.update(profile=state["profile"]),
            )

        def interpretation(connection: sqlite3.Connection) -> None:
            _rebuild_candidate_tail(
                connection, edit_final=lambda final: final.update(interpretation_digest="sha256:" + "a" * 64)
            )

        def substrate_identity(connection: sqlite3.Connection) -> None:
            def edit(state: dict) -> None:
                state["substrate_identity"] = {**state["substrate_identity"], "sqlite_version": "0.0.0"}

            _rebuild_candidate_tail(connection, edit_state=edit)

        for change, reason in (
            (profile, "candidate_runtime_profile_identity_mismatch"),
            (interpretation, "candidate_interpretation_digest_mismatch"),
            (substrate_identity, "candidate_substrate_identity_mismatch"),
        ):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                _, _, preflight = _fresh_preflight(Path(temp))
                transactional_recommit_candidate_v2(preflight)
                _mutate(Path(preflight.evidence.snapshot_database), change)
                with self.assertRaises(CandidateMigrationError) as caught:
                    qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
                self.assertEqual(caught.exception.reason, reason)

    def test_phase4_rechecks_envelope_identity_inside_transaction(self):
        def profile(state: dict) -> None:
            state["profile"]["profile_version"] = "9.9.9"

        def interpretation(state: dict) -> None:
            state["interpretation_digest"] = "sha256:" + "a" * 64

        def substrate_identity(state: dict) -> None:
            state["substrate_identity"] = {**state["substrate_identity"], "sqlite_version": "0.0.0"}

        for edit, reason in (
            (profile, "source_runtime_profile_identity_mismatch"),
            (interpretation, "source_interpretation_digest_mismatch"),
            (substrate_identity, "source_substrate_identity_mismatch"),
        ):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                _, _, preflight = _fresh_preflight(Path(temp))
                candidate_db = Path(preflight.evidence.snapshot_database)

                def apply(connection: sqlite3.Connection) -> None:
                    state = _state(connection)
                    edit(state)
                    _write_state(connection, state, v2=False)

                _mutate(candidate_db, apply)
                before = _database_hash(candidate_db)
                with mock.patch.object(transaction_module, "_reverify_old_copy", lambda preflight: None):
                    with self.assertRaises(CandidateMigrationError) as caught:
                        transactional_recommit_candidate_v2(preflight)
                self.assertEqual(caught.exception.reason, reason)
                self.assertEqual(_database_hash(candidate_db), before)


class ExactShapeTests(unittest.TestCase):
    def test_candidate_envelope_rejects_extra_and_missing_keys(self):
        for label, edit in (
            ("extra_authority_grant", lambda s: s.update(authority_grant={"scope": "all"})),
            ("missing_substrate_identity", lambda s: s.pop("substrate_identity")),
        ):
            with self.subTest(label), tempfile.TemporaryDirectory() as temp:
                _, _, preflight = _fresh_preflight(Path(temp))
                transactional_recommit_candidate_v2(preflight)
                _mutate(
                    Path(preflight.evidence.snapshot_database),
                    lambda c: _rebuild_candidate_tail(c, edit_state=edit),
                )
                with self.assertRaises(CandidateMigrationError) as caught:
                    qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
                self.assertEqual(caught.exception.reason, "candidate_runtime_state_shape_invalid")

    def test_candidate_journal_rejects_extra_and_missing_keys(self):
        for label, edit, extra in (
            ("extra_authority_grant", lambda f: f.update(authority_grant="tenant-acme:admin"), ("authority_grant",)),
            ("missing_provenance_digest", lambda f: f.pop("migration_provenance_digest"), ()),
        ):
            with self.subTest(label), tempfile.TemporaryDirectory() as temp:
                _, _, preflight = _fresh_preflight(Path(temp))
                transactional_recommit_candidate_v2(preflight)
                # Integrity material (record digest + envelope binding) is rebuilt
                # around the injected field so only the shape rule can refuse it.
                _mutate(
                    Path(preflight.evidence.snapshot_database),
                    lambda c: _rebuild_candidate_tail(c, edit_final=edit, extra_material=extra),
                )
                with self.assertRaises(CandidateMigrationError) as caught:
                    qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
                self.assertEqual(caught.exception.reason, "candidate_journal_shape_invalid")

    def test_frozen_fixture_field_sets_match_verifier(self):
        # Amendment-1 makes the base contract's required sets exact; it adds no field.
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
        for section in ("candidate_runtime_state", "candidate_journal"):
            self.assertTrue(amendment[section]["exact_fields_equal_base_required_fields"])
        self.assertEqual(set(fixture["candidate_runtime_state"]["required_fields"]), set(CANDIDATE_RUNTIME_STATE_FIELDS))
        self.assertEqual(set(fixture["candidate_journal"]["required_fields"]), set(CANDIDATE_JOURNAL_FIELDS))
        self.assertEqual(
            list(fixture["candidate_journal"]["record_digest_material_fields"]), list(CANDIDATE_JOURNAL_MATERIAL_FIELDS)
        )


class ContractAmendmentProvenanceTests(unittest.TestCase):
    REPO_ROOT = ROOT.parent

    def _validate(self, amendment: dict | None = None, base: bytes | None = None) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            amendment_path = Path(temp) / "amendment.json"
            base_path = Path(temp) / "base.json"
            amendment_path.write_text(json.dumps(amendment or json.loads(AMENDMENT.read_text(encoding="utf-8"))))
            base_path.write_bytes(FIXTURE.read_bytes() if base is None else base)
            return contract.validate_amendment(amendment_path, base_path, self.REPO_ROOT)

    def _amended(self, edit) -> dict:
        value = json.loads(AMENDMENT.read_text(encoding="utf-8"))
        edit(value)
        return value

    def test_base_fixture_is_byte_identical_to_first_frozen_form(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), contract.BASE_FIXTURE_SHA256)
        amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
        self.assertEqual(amendment["amends"]["file_sha256"], contract.BASE_FIXTURE_SHA256)
        self.assertEqual(amendment["amends"]["frozen_at_commit"], contract.BASE_FIXTURE_FROZEN_AT)
        report = self._validate()
        self.assertTrue(report["narrowing_only"])

    def test_effective_contract_is_superset_of_base(self):
        base = json.loads(FIXTURE.read_text(encoding="utf-8"))
        amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
        effective_refusals = set(base["adversarial_refusals"]) | set(amendment["additional_adversarial_refusals"])
        effective_invariants = set(base["success_invariants"]) | set(amendment["additional_success_invariants"])
        self.assertTrue(set(base["adversarial_refusals"]) < effective_refusals)
        self.assertTrue(set(base["success_invariants"]) < effective_invariants)
        self.assertFalse(set(amendment) & (set(base) - contract.AMENDMENT_KEYS))

    def test_amendment_cannot_relax_override_or_repoint_base(self):
        cases = {
            "rewritten_base_bytes": dict(base=FIXTURE.read_bytes() + b"\n"),
            "claims_relaxation": dict(amendment=self._amended(lambda a: a.update(relaxes_or_replaces_base_requirement=True))),
            "redefines_base_refusals": dict(amendment=self._amended(lambda a: a.update(adversarial_refusals=[]))),
            "overrides_base_required_fields": dict(
                amendment=self._amended(lambda a: a["candidate_journal"].update(required_fields=["schema_version"]))
            ),
            "re_adds_base_refusal": dict(
                amendment=self._amended(lambda a: a["additional_adversarial_refusals"].append("migration_provenance_tamper"))
            ),
            "claims_preimplementation_freeze": dict(
                amendment=self._amended(
                    lambda a: a.update(status="FROZEN_PREIMPLEMENTATION_TRANSACTION_QUALIFICATION_CONTRACT")
                )
            ),
            "wrong_base_identity": dict(amendment=self._amended(lambda a: a["amends"].update(file_sha256="0" * 64))),
        }
        for label, kwargs in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                self._validate(**kwargs)


class JournalGenerationColumnTests(unittest.TestCase):
    def test_sql_generation_must_equal_payload_generation(self):
        for label in ("final_candidate_record", "historical_record"):
            with self.subTest(label), tempfile.TemporaryDirectory() as temp:
                _, _, preflight = _fresh_preflight(Path(temp))
                transactional_recommit_candidate_v2(preflight)

                def renumber(connection: sqlite3.Connection) -> None:
                    rows = _journal(connection)
                    generation = rows[-1][0] if label == "final_candidate_record" else rows[0][0]
                    target = rows[-1][0] + 10 if label == "final_candidate_record" else 0
                    connection.execute(
                        "UPDATE runtime_journal SET generation = ? WHERE generation = ?", (target, generation)
                    )

                _mutate(Path(preflight.evidence.snapshot_database), renumber)
                with self.assertRaises(CandidateMigrationError) as caught:
                    qualify_candidate_v2_restart(preflight, prove_production_refusal=False)
                self.assertEqual(caught.exception.reason, "candidate_journal_generation_column_mismatch")


class ProductionRecoveryRouteTests(unittest.TestCase):
    def test_low_level_verifier_has_no_production_recovery_route(self):
        low_level = transaction_module.qualify_candidate_v2_restart
        self.assertNotIn("prove_production_refusal", inspect.signature(low_level).parameters)
        source = inspect.getsource(transaction_module)
        self.assertNotIn("SQLiteRestartSafeRuntime", source)
        self.assertNotIn(".recover(", source)

    def test_refusal_proof_records_expected_reason(self):
        with tempfile.TemporaryDirectory() as temp:
            _, _, preflight = _fresh_preflight(Path(temp))
            transactional_recommit_candidate_v2(preflight)
            evidence = prove_production_runtime_refusal(preflight)
            self.assertEqual(evidence.refusal_reason, EXPECTED_PRODUCTION_REFUSAL_REASON)
            self.assertEqual(evidence.refusal_reason, "unsupported SQLite runtime state schema")
            self.assertEqual(evidence.refusal_type, "RuntimeRecoveryError")

    def test_unrelated_recovery_errors_do_not_count_as_refusal_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            _, _, preflight = _fresh_preflight(Path(temp))
            transactional_recommit_candidate_v2(preflight)
            candidate_db = Path(preflight.evidence.snapshot_database)
            before = _database_hash(candidate_db)

            # Missing disposable file: recovery fails for a reason other than the schema.
            with mock.patch.object(restart_module, "_backup_read_only", lambda source, destination: None):
                with self.assertRaises(CandidateMigrationError) as caught:
                    prove_production_runtime_refusal(preflight)
            self.assertEqual(caught.exception.reason, "production_recovery_refused_for_unexpected_reason")

            for message in (
                "SQLite durability profile changed",
                "SQLite runtime interpretation digest mismatch",
                "SQLite canonical substrate digest mismatch",
            ):
                with self.subTest(message=message):
                    with mock.patch.object(
                        SQLiteRestartSafeRuntime, "recover", side_effect=RuntimeRecoveryError(message)
                    ):
                        with self.assertRaises(CandidateMigrationError) as caught:
                            qualify_candidate_v2_restart(preflight)
                    self.assertEqual(caught.exception.reason, "production_recovery_refused_for_unexpected_reason")
            self.assertEqual(_database_hash(candidate_db), before)


if __name__ == "__main__":
    unittest.main()
