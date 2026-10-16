"""Transactional SQLite restart profile for Agent Memory RC1.

Unlike the reference file-checkpoint profile, this runtime keeps canonical
substrate state and the governed runtime envelope in one SQLite database and
publishes them through one SQLite transaction. The database is therefore the
durable source of truth for this profile rather than a serialized substrate
snapshot.

The profile is deliberately single-host. SQLite provides transactional local
durability; it does not provide distributed consensus or network-partition
semantics.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
from typing import Iterable

from .configured_restart import (
    ConfigBindingStore,
    ConfigBoundRecoveryEvidence,
    ConfigBoundRestartRuntime,
    _assert_visibility_matches_plan,
    _profile_from_plan,
    binding_record,
    checkpoint_evidence,
    plan_digest,
    verify_binding_record,
)
from .restart_runtime import (
    CapabilityBinding,
    CheckpointableGovernedMemoryAdapter,
    RuntimeCheckpointConflict,
    RuntimeProfile,
    RuntimeRecoveryError,
    _assert_profile_compatible,
)
from .runtime_config import RuntimeConfigurationPlan
from ..state.sqlite_substrate import (
    GOVERNANCE_SCHEME,
    GovernanceIntegrityError,
    SQLiteTemporalGraph,
    SQLITE_SUBSTRATE_PROFILE,
)


# Journal records keep schema 1.0.0: their material is unchanged, and the governance
# digest they bind is self-describing ("sha256:" = full-json-v1, "gsect-v1:" = #562).
SQLITE_RUNTIME_SCHEMA_VERSION = "1.0.0"
# Runtime-state envelope versions. 1.0.0 embeds the whole governance snapshot and binds
# its full-JSON digest (full-json-v1). 1.1.0 persists governance as sections and binds
# the gsect-v1 root; the envelope no longer carries the snapshot (#562).
LEGACY_RUNTIME_STATE_SCHEMA_VERSION = "1.0.0"
SQLITE_RUNTIME_STATE_SCHEMA_VERSION = "1.1.0"
# Test and qualification aid: after every publication, re-read the governance rows and
# require them to equal a full export of the in-memory governance state.
GOVERNANCE_SELF_CHECK_ENV = "AGENT_MEMORY_GOVERNANCE_SELF_CHECK"
SQLITE_DURABILITY_PROFILE = "sqlite_transactional_runtime_v1"
SQLITE_TRANSACTION_PROTOCOL = "sqlite_begin_immediate_generation_v1"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class SQLiteRecoveryEvidence:
    generation: int
    durability_profile: str
    substrate_digest: str
    governance_digest: str
    interpretation_digest: str
    recovered_visibility_operations: tuple[str, ...]
    sqlite_version: str
    substrate_profile: str = SQLITE_SUBSTRATE_PROFILE
    recovery_posture: str = "recovered_exact_sqlite_transaction"

    def to_dict(self) -> dict:
        return asdict(self)


def _journal_record(
    *,
    generation: int,
    substrate_digest: str,
    governance_digest: str,
    interpretation_digest: str,
    previous_record_digest: str,
) -> dict:
    material = {
        "schema_version": SQLITE_RUNTIME_SCHEMA_VERSION,
        "transaction_protocol": SQLITE_TRANSACTION_PROTOCOL,
        "generation": int(generation),
        "substrate_digest": substrate_digest,
        "governance_digest": governance_digest,
        "interpretation_digest": interpretation_digest,
        "previous_record_digest": previous_record_digest,
    }
    return {**material, "record_digest": _digest(material)}


_JOURNAL_MATERIAL_FIELDS = (
    "schema_version",
    "transaction_protocol",
    "generation",
    "substrate_digest",
    "governance_digest",
    "interpretation_digest",
    "previous_record_digest",
)


def _validate_record(raw: dict, expected_generation: int) -> None:
    if raw.get("schema_version") != SQLITE_RUNTIME_SCHEMA_VERSION:
        raise RuntimeRecoveryError("unsupported SQLite runtime journal schema")
    if raw.get("transaction_protocol") != SQLITE_TRANSACTION_PROTOCOL:
        raise RuntimeRecoveryError("SQLite runtime transaction protocol changed")
    try:
        generation = int(raw["generation"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeRecoveryError("SQLite runtime journal generation is malformed") from exc
    if generation != expected_generation:
        raise RuntimeRecoveryError("SQLite runtime journal is not contiguous")
    try:
        material = {key: raw[key] for key in _JOURNAL_MATERIAL_FIELDS}
    except KeyError as exc:
        raise RuntimeRecoveryError("SQLite runtime journal record is incomplete") from exc
    if raw.get("record_digest") != _digest(material):
        raise RuntimeRecoveryError("SQLite runtime journal record digest mismatch")


def _validate_journal(rows: Iterable[dict]) -> dict | None:
    """Recovery-time full chain verification."""

    previous: dict | None = None
    for index, raw in enumerate(rows, start=1):
        previous_digest = "" if previous is None else str(previous["record_digest"])
        if raw.get("previous_record_digest") != previous_digest:
            raise RuntimeRecoveryError("SQLite runtime journal chain is broken")
        _validate_record(raw, index)
        previous = dict(raw)
    return previous


def _validate_journal_tail(
    tail: dict | None, generation: int, bound_record_digest: str | None
) -> dict | None:
    """Commit-time operation integrity (#522): verify only the record being extended.

    The full chain was verified when this handle recovered it, and every later record
    was appended by a committed transaction that passed this same check. Here the tail
    must be self-consistent, sit at the current generation, and be the record the
    runtime state binds.
    """

    if generation == 0:
        if tail is not None:
            raise RuntimeRecoveryError("SQLite runtime journal exists without runtime state")
        return None
    if tail is None:
        raise RuntimeRecoveryError("SQLite runtime journal is missing")
    _validate_record(tail, generation)
    if tail.get("record_digest") != bound_record_digest:
        raise RuntimeRecoveryError("SQLite runtime state does not bind the journal tail")
    return tail


def _assemble_governance(loaded: dict) -> dict:
    """The v1-shaped governance snapshot from verified gsect-v1 sections."""

    residual = loaded["residual"]
    adapter = residual.get("adapter")
    if not isinstance(adapter, dict):
        raise RuntimeRecoveryError("SQLite governance residual state is malformed")
    maps = loaded["maps"]
    return {
        "tenant": residual.get("tenant"),
        "adapter": {
            **adapter,
            "state_version": maps["state_version"],
            "tombstones": maps["tombstones"],
            "fact_scope": maps["fact_scope"],
            "fact_memory": maps["fact_memory"],
            "current_fact_by_memory": maps["current_fact_by_memory"],
            "events": loaded["logs"]["events"],
        },
        "visibility_snapshots": residual.get("visibility_snapshots", {}),
    }


def _verified_governance(substrate: SQLiteTemporalGraph, state: dict, state_schema) -> tuple[dict, bool]:
    """Recovery-time full verification of the committed governance state.

    Returns ``(governance, legacy)``. A 1.0.0 envelope must embed the snapshot and bind
    its full-JSON digest (full-json-v1); a 1.1.0 envelope must name gsect-v1, carry no
    embedded snapshot, and bind a root that the stored sections reproduce exactly.
    Mixing the two is refused rather than reinterpreted.
    """

    digest = str(state.get("governance_digest", ""))
    if state_schema == LEGACY_RUNTIME_STATE_SCHEMA_VERSION:
        governance = state.get("governance")
        if "governance_scheme" in state or not digest.startswith("sha256:"):
            raise RuntimeRecoveryError("SQLite governance scheme does not match the runtime state schema")
        if not isinstance(governance, dict):
            raise RuntimeRecoveryError("SQLite governance state is missing")
        if _digest(governance) != digest:
            raise RuntimeRecoveryError("SQLite governance state digest mismatch")
        return governance, True
    if state.get("governance_scheme") != GOVERNANCE_SCHEME or "governance" in state:
        raise RuntimeRecoveryError("SQLite governance scheme does not match the runtime state schema")
    try:
        loaded = substrate.governance.load_verified(digest)
    except GovernanceIntegrityError as exc:
        raise RuntimeRecoveryError(f"SQLite governance state digest mismatch: {exc}") from exc
    except (ValueError, TypeError) as exc:
        raise RuntimeRecoveryError("SQLite governance state is malformed") from exc
    return _assemble_governance(loaded), False


class SQLiteRestartSafeRuntime:
    """Governed runtime whose canonical and governance state commit atomically."""

    def __init__(
        self,
        *,
        root: str | Path,
        substrate: SQLiteTemporalGraph,
        profile: RuntimeProfile,
        adapter: CheckpointableGovernedMemoryAdapter,
        visibility_snapshots: dict[str, dict] | None = None,
        recovery_evidence: SQLiteRecoveryEvidence | None = None,
        observed_generation: int = 0,
        verifier_registry=None,
    ) -> None:
        self.root = Path(root)
        self.substrate = substrate
        self.profile = profile
        self.adapter = adapter
        self.visibility_snapshots = dict(visibility_snapshots or {})
        self.recovery_evidence = recovery_evidence
        self._observed_generation = int(observed_generation)
        self._verifier_registry = verifier_registry
        # Runtime-owned serialization boundary (#530). One reentrant lock covers the
        # SQLite connection, observed generation (CAS), adapter governance state,
        # visibility snapshots, and journal publication. Operations still commit as
        # single-writer SQLite generations; they simply never interleave.
        self._serialization_lock = threading.RLock()
        # #816: the database is the durable source of truth only for what a generation
        # published, so from here on a governed act runs only inside ``_transactional_operation``
        # (a direct adapter call on this handle is refused before anything moves, not half-applied).
        self._generation_capability = substrate.require_runtime_generations()
        adapter.require_generation_for_durable_effects(substrate.require_generation)
        self._generation_binder = None
        self._on_generation_published = None

    def bind_generations(self, binder) -> None:
        """Run ``binder(substrate, evidence, journal_record, tenant)`` inside every generation
        this runtime publishes, after its journal row and before COMMIT (#821).

        Whatever the binder writes commits or rolls back with the generation; if it raises, the
        generation is not published. This is how an owner binds a generation durably."""

        self._generation_binder = binder

    def on_generation_published(self, callback) -> None:
        """Run ``callback`` after every generation this runtime publishes (#816), however the
        governed act reached it. It runs after COMMIT, so it must only update in-memory state;
        durable binding belongs in ``bind_generations`` (#821)."""

        self._on_generation_published = callback

    def _published(self, evidence: SQLiteRecoveryEvidence) -> None:
        self._observed_generation = evidence.generation
        self.recovery_evidence = evidence
        if self._on_generation_published is not None:
            self._on_generation_published()

    @property
    def serialization_lock(self) -> threading.RLock:
        return self._serialization_lock

    @property
    def database_path(self) -> Path:
        return self.substrate.path

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        tenant: str,
        profile: RuntimeProfile,
        verifier_registry=None,
        generation_binder=None,
    ) -> "SQLiteRestartSafeRuntime":
        root_path = Path(root)
        root_path.mkdir(parents=True, exist_ok=True)
        substrate = SQLiteTemporalGraph(root_path / "agent-memory.sqlite3")
        if substrate.read_runtime_state() is not None:
            substrate.close()
            raise RuntimeRecoveryError("SQLite runtime state already exists; use recover()")
        adapter = CheckpointableGovernedMemoryAdapter(
            substrate,
            tenant=tenant,
            verifier_registry=verifier_registry,
        )
        adapter.track_governance_changes()
        runtime = cls(
            root=root_path,
            substrate=substrate,
            profile=profile,
            adapter=adapter,
            observed_generation=0,
            verifier_registry=verifier_registry,
        )
        # #821: generation 1 commits together with its owner's binding, or not at all.
        runtime.bind_generations(generation_binder)
        try:
            runtime.recovery_evidence = runtime.checkpoint()
        except BaseException:
            substrate.close()
            raise
        return runtime

    @classmethod
    def recover(
        cls,
        root: str | Path,
        *,
        profile: RuntimeProfile,
        available_bindings: Iterable[CapabilityBinding] | None = None,
        verifier_registry=None,
    ) -> "SQLiteRestartSafeRuntime":
        root_path = Path(root)
        substrate = SQLiteTemporalGraph(root_path / "agent-memory.sqlite3")
        try:
            substrate.integrity_check()
            state = substrate.read_runtime_state()
            if state is None:
                raise RuntimeRecoveryError("required SQLite runtime state is missing")
            state_schema = state.get("schema_version")
            if state_schema not in (LEGACY_RUNTIME_STATE_SCHEMA_VERSION, SQLITE_RUNTIME_STATE_SCHEMA_VERSION):
                raise RuntimeRecoveryError("unsupported SQLite runtime state schema")
            if state.get("durability_profile") != SQLITE_DURABILITY_PROFILE:
                raise RuntimeRecoveryError("SQLite durability profile changed")
            if state.get("transaction_protocol") != SQLITE_TRANSACTION_PROTOCOL:
                raise RuntimeRecoveryError("SQLite transaction protocol changed")

            persisted_profile_raw = state.get("profile")
            if not isinstance(persisted_profile_raw, dict):
                raise RuntimeRecoveryError("persisted SQLite runtime profile is missing")
            try:
                persisted_profile = RuntimeProfile(
                    runtime_version=persisted_profile_raw["runtime_version"],
                    profile_id=persisted_profile_raw["profile_id"],
                    profile_version=persisted_profile_raw["profile_version"],
                    bindings=tuple(
                        CapabilityBinding(**binding)
                        for binding in persisted_profile_raw.get("bindings", ())
                    ),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeRecoveryError("persisted SQLite runtime profile is malformed") from exc
            available = tuple(
                available_bindings if available_bindings is not None else profile.bindings
            )
            _assert_profile_compatible(persisted_profile, profile, available)
            if state.get("interpretation_digest") != profile.interpretation_digest:
                raise RuntimeRecoveryError("SQLite runtime interpretation digest mismatch")

            governance, legacy_governance = _verified_governance(substrate, state, state_schema)
            if not substrate.verify_recorded_state_digest(str(state.get("substrate_digest", ""))):
                raise RuntimeRecoveryError("SQLite canonical substrate digest mismatch")

            latest = _validate_journal(substrate.read_runtime_journal())
            if latest is None:
                raise RuntimeRecoveryError("SQLite runtime journal is missing")
            generation = int(state.get("generation", 0))
            if generation < 1 or int(latest["generation"]) != generation:
                raise RuntimeRecoveryError("SQLite runtime generation/journal mismatch")
            for field in ("substrate_digest", "governance_digest", "interpretation_digest"):
                if latest.get(field) != state.get(field):
                    raise RuntimeRecoveryError("SQLite runtime journal does not bind current state")
            if latest.get("record_digest") != state.get("journal_record_digest"):
                raise RuntimeRecoveryError("SQLite runtime state does not bind the journal tail")

            tenant = governance.get("tenant")
            adapter_raw = governance.get("adapter")
            visibility = governance.get("visibility_snapshots", {})
            if not isinstance(tenant, str) or not tenant:
                raise RuntimeRecoveryError("SQLite governance state has no tenant")
            if not isinstance(adapter_raw, dict) or not isinstance(visibility, dict):
                raise RuntimeRecoveryError("SQLite governance state is malformed")
            adapter = CheckpointableGovernedMemoryAdapter(
                substrate,
                tenant=tenant,
                verifier_registry=verifier_registry,
            )
            try:
                adapter.restore_checkpoint_state(adapter_raw)
            except (TypeError, ValueError) as exc:
                raise RuntimeRecoveryError("SQLite governance state cannot be reconstructed") from exc
            adapter.track_governance_changes()
            if legacy_governance:
                # full-json-v1 store: the next generation migrates it to gsect-v1 atomically.
                substrate.governance.invalidate()

            evidence = SQLiteRecoveryEvidence(
                generation=generation,
                durability_profile=SQLITE_DURABILITY_PROFILE,
                substrate_digest=str(state["substrate_digest"]),
                governance_digest=str(state["governance_digest"]),
                interpretation_digest=profile.interpretation_digest,
                recovered_visibility_operations=tuple(sorted(visibility)),
                sqlite_version=substrate.sqlite_version,
            )
            return cls(
                root=root_path,
                substrate=substrate,
                profile=profile,
                adapter=adapter,
                visibility_snapshots=visibility,
                recovery_evidence=evidence,
                observed_generation=generation,
                verifier_registry=verifier_registry,
            )
        except Exception:
            substrate.close()
            raise

    def close(self) -> None:
        with self._serialization_lock:
            self.substrate.close()

    def _governance_snapshot(self) -> dict:
        try:
            adapter_state = self.adapter.export_checkpoint_state()
            tenant = self.adapter.checkpoint_tenant()
        except (TypeError, ValueError) as exc:
            raise RuntimeRecoveryError("SQLite governance checkpoint export failed") from exc
        if not isinstance(adapter_state, dict) or not isinstance(tenant, str) or not tenant:
            raise RuntimeRecoveryError("SQLite governance checkpoint is malformed")
        return {
            "tenant": tenant,
            "adapter": adapter_state,
            "visibility_snapshots": self.visibility_snapshots,
        }

    def _persist_unlocked(self) -> SQLiteRecoveryEvidence:
        binding = self.substrate.read_runtime_binding()
        current_generation = 0 if binding is None else binding[0]
        if current_generation != self._observed_generation:
            raise RuntimeCheckpointConflict(
                "SQLite generation conflict: "
                f"observed {self._observed_generation}, current {current_generation}"
            )

        governance_digest = self._publish_governance()
        substrate_digest = self.substrate.incremental_state_digest()
        generation = current_generation + 1
        previous = _validate_journal_tail(
            self.substrate.read_runtime_journal_tail(),
            current_generation,
            None if binding is None else binding[1],
        )
        previous_digest = "" if previous is None else str(previous["record_digest"])
        record = _journal_record(
            generation=generation,
            substrate_digest=substrate_digest,
            governance_digest=governance_digest,
            interpretation_digest=self.profile.interpretation_digest,
            previous_record_digest=previous_digest,
        )
        state = {
            "schema_version": SQLITE_RUNTIME_STATE_SCHEMA_VERSION,
            "durability_profile": SQLITE_DURABILITY_PROFILE,
            "transaction_protocol": SQLITE_TRANSACTION_PROTOCOL,
            "generation": generation,
            "profile": self.profile.to_dict(),
            "interpretation_digest": self.profile.interpretation_digest,
            "substrate_digest": substrate_digest,
            "governance_scheme": GOVERNANCE_SCHEME,
            "governance_digest": governance_digest,
            "substrate_identity": self.substrate.operational_identity(),
            "journal_record_digest": record["record_digest"],
        }
        self.substrate.write_runtime_state(state)
        self.substrate.append_runtime_journal(generation, record)
        evidence = SQLiteRecoveryEvidence(
            generation=generation,
            durability_profile=SQLITE_DURABILITY_PROFILE,
            substrate_digest=substrate_digest,
            governance_digest=governance_digest,
            interpretation_digest=self.profile.interpretation_digest,
            recovered_visibility_operations=tuple(sorted(self.visibility_snapshots)),
            sqlite_version=self.substrate.sqlite_version,
            recovery_posture="committed_atomic_sqlite_generation",
        )
        if self._generation_binder is not None:
            self._generation_binder(self.substrate, evidence, record, self.adapter.checkpoint_tenant())
        if os.environ.get(GOVERNANCE_SELF_CHECK_ENV) == "1":
            self._self_check_governance(governance_digest)
        self.adapter.mark_governance_published()
        return evidence

    def _governance_residual(self) -> dict:
        try:
            adapter_residual = self.adapter.export_governance_residual()
            tenant = self.adapter.checkpoint_tenant()
        except (TypeError, ValueError) as exc:
            raise RuntimeRecoveryError("SQLite governance checkpoint export failed") from exc
        if not isinstance(tenant, str) or not tenant:
            raise RuntimeRecoveryError("SQLite governance checkpoint is malformed")
        return {"tenant": tenant, "adapter": adapter_residual, "visibility_snapshots": self.visibility_snapshots}

    def _publish_governance(self) -> str:
        """Write this generation's governance changes inside the open transaction (#562).

        Publishes only changed entries and appended log records when the maintained
        commitment is trusted and every section is expressible as a change set;
        otherwise (creation, legacy migration, an untrusted index, or a non-append
        edit) it publishes the whole state once. Either way the result is the same root.
        """
        store = self.substrate.governance
        residual = self._governance_residual()
        changes = self.adapter.export_governance_changes() if store.trusted else None
        try:
            if changes is None:
                maps, logs = self.adapter.export_governance_sections()
                return store.write_full(maps, logs, residual)
            maps, deleted, logs = changes
            return store.apply(maps, deleted, logs, residual)
        except (TypeError, ValueError) as exc:
            raise RuntimeRecoveryError("SQLite governance publication failed") from exc

    def _self_check_governance(self, root: str) -> None:
        store = self.substrate.governance
        snapshot = store.cache_snapshot()
        try:
            loaded = store.load_verified(root)
        except GovernanceIntegrityError as exc:
            raise RuntimeRecoveryError(f"SQLite governance self-check failed: {exc}") from exc
        finally:
            store.restore_cache(snapshot)
        if _digest(_assemble_governance(loaded)) != _digest(self._governance_snapshot()):
            raise RuntimeRecoveryError("SQLite governance rows diverged from in-memory governance state")

    @contextmanager
    def _generation(self):
        """One SQLite transaction that this runtime publishes as a generation (#816)."""

        with self.substrate.transaction(), self.substrate.generation_opened(self._generation_capability):
            yield

    def checkpoint(self) -> SQLiteRecoveryEvidence:
        with self._serialization_lock:
            with self._generation():
                evidence = self._persist_unlocked()
            self._published(evidence)
            return evidence

    def _restore_governance_after_rollback(self) -> None:
        state = self.substrate.read_runtime_state()
        if state is None:
            return
        try:
            governance, _ = _verified_governance(self.substrate, state, state.get("schema_version"))
        except RuntimeRecoveryError as exc:
            raise RuntimeRecoveryError("cannot restore governance after SQLite rollback") from exc
        adapter_raw = governance.get("adapter")
        visibility = governance.get("visibility_snapshots", {})
        if not isinstance(adapter_raw, dict) or not isinstance(visibility, dict):
            raise RuntimeRecoveryError("cannot restore governance after SQLite rollback")
        self.adapter.restore_checkpoint_state(adapter_raw)
        self.adapter.track_governance_changes()
        self.visibility_snapshots = dict(visibility)

    def _transactional_operation(self, operation):
        """Publish canonical or governance side effects as one SQLite generation.

        Governed recall is memory-content read-only, but it allocates decision,
        event, and correlation identifiers and appends audit evidence. Those
        effects are governance state and must commit atomically just like a
        canonical mutation. Keeping them inside this seam prevents a read from
        advancing durable identifier state without advancing the bound runtime
        generation.
        """
        with self._serialization_lock:
            try:
                with self._generation():
                    binding = self.substrate.read_runtime_binding()
                    generation = 0 if binding is None else binding[0]
                    if generation != self._observed_generation:
                        raise RuntimeCheckpointConflict(
                            "SQLite generation conflict: "
                            f"observed {self._observed_generation}, current {generation}"
                        )
                    result = operation()
                    evidence = self._persist_unlocked()
            except BaseException:
                self._restore_governance_after_rollback()
                raise
            self._published(evidence)
            return result

    def run_governed_read(self, operation):
        return self._transactional_operation(operation)

    def governed_recall(self, query, context=None):
        return self.run_governed_read(
            lambda: self.adapter.governed_recall(query, context)
        )

    def commit_proposal(
        self,
        proposal,
        fact_text: str,
        episode=None,
        *,
        evidence=None,
        attestation=None,
        temporal=None,
        replacement_kind="error_correction",
        source_ref=None,
        typed_write=None,
    ):
        return self._transactional_operation(
            lambda: self.adapter.commit_proposal(
                proposal,
                fact_text,
                episode,
                evidence=evidence,
                attestation=attestation,
                temporal=temporal,
                replacement_kind=replacement_kind,
                source_ref=source_ref,
                typed_write=typed_write,
            )
        )

    def governed_delete(
        self,
        proposal,
        fact_uuid: str,
        derived_refs: tuple[str, ...] = (),
        external_verification=None,
        evidence=None,
    ):
        return self._transactional_operation(
            lambda: self.adapter.governed_delete(
                proposal,
                fact_uuid,
                derived_refs,
                external_verification,
                evidence,
            )
        )

    def persist_visibility_snapshot(
        self,
        operation_id: str,
        snapshot: dict,
    ) -> SQLiteRecoveryEvidence:
        if not operation_id:
            raise ValueError("visibility operation id is required")
        if not isinstance(snapshot, dict):
            raise ValueError("visibility snapshot must be a mapping")
        with self._serialization_lock:
            previous = dict(self.visibility_snapshots)
            generation = self._observed_generation
            self.visibility_snapshots[operation_id] = snapshot
            try:
                return self.checkpoint()
            except BaseException:  # an interrupt rolls the generation back too (review N2)
                # Undo only what did not commit: a failure after the generation committed (the
                # owner's binding hook, #816 review F3) must not drop a committed snapshot.
                if self._observed_generation == generation:
                    self.visibility_snapshots = previous
                raise

    def backup_to(self, destination: str | Path) -> None:
        with self._serialization_lock:
            self.substrate.backup_to(destination)


# #821: the configuration binding of a SQLite store is a row its generation's own transaction
# commits; the file written after COMMIT is read only for stores bound before this protocol.
SQLITE_CONFIG_BINDING_PROTOCOL = "sqlite_same_transaction_config_binding_v1"
SQLITE_TRANSACTION_BINDING = "sqlite_transaction"
LEGACY_FILE_BINDING = "legacy_file"
GENERATION_WITNESS_NAME = "generation-witness.json"
GENERATION_WITNESS_SCHEMA = "agent-memory-sqlite-generation-witness/1"


def _verified_binding_row(
    current: tuple[int, str],
    *,
    plan: RuntimeConfigurationPlan,
    base_evidence,
    tenant: str,
    journal_record_digest: str | None,
    provider_failures=(),
) -> ConfigBoundRecoveryEvidence:
    """Verify one binding row against a generation whose base identity is already verified."""

    column, payload = current
    try:
        record = json.loads(payload)
    except (TypeError, ValueError) as exc:
        raise RuntimeRecoveryError("SQLite configuration binding is corrupt: not JSON") from exc
    if not isinstance(record, dict):
        raise RuntimeRecoveryError("SQLite configuration binding is corrupt: not an object")
    if record.get("binding_protocol") != SQLITE_CONFIG_BINDING_PROTOCOL:
        raise RuntimeRecoveryError("SQLite configuration binding protocol is unsupported")
    material = {key: value for key, value in record.items() if key != "record_digest"}
    if record.get("record_digest") != _digest(material):
        raise RuntimeRecoveryError("SQLite configuration binding is corrupt: record digest mismatch")
    base = record.get("base")
    if not isinstance(base, dict) or base.get("generation") != column:
        raise RuntimeRecoveryError("SQLite configuration binding is corrupt: its row and record disagree")
    if record.get("tenant") != tenant:
        raise RuntimeRecoveryError("SQLite configuration binding belongs to another tenant")
    if base.get("generation") != base_evidence.generation:
        raise RuntimeRecoveryError(
            "SQLite configuration binding is stale or replayed: it binds generation "
            f"{base.get('generation')!r}, the store committed generation {base_evidence.generation}"
        )
    if journal_record_digest is None or base.get("journal_record_digest") != journal_record_digest:
        raise RuntimeRecoveryError(
            "configuration binding does not match recovered base checkpoint: journal_record_digest"
        )
    return verify_binding_record(
        record, plan=plan, base_evidence=base_evidence, provider_failures=provider_failures
    )


class SQLiteConfigBindingStore:
    """The configuration binding as a row each generation commits with itself (#821).

    ``publish`` runs inside the generation (``SQLiteRestartSafeRuntime.bind_generations``), so the
    generation and its binding are one SQLite transaction: there is no state in which one is
    durable without the other. ``recover`` verifies the row and never repairs it. Only a store
    without the table is a pre-#821 store; it is verified through its legacy file exactly as before.
    The record digest is an unkeyed checksum: it detects corruption, not a forger with write access.
    """

    def __init__(self, root: str | Path) -> None:
        self.legacy = ConfigBindingStore(root)

    @staticmethod
    def _read(substrate: SQLiteTemporalGraph) -> tuple[int, str] | None:
        try:
            return substrate.read_runtime_configuration_binding()
        except (ValueError, sqlite3.DatabaseError) as exc:
            raise RuntimeRecoveryError(f"SQLite configuration binding is corrupt: {exc}") from exc

    def publish(
        self,
        substrate: SQLiteTemporalGraph,
        *,
        plan: RuntimeConfigurationPlan,
        base_evidence: SQLiteRecoveryEvidence,
        journal_record: dict,
        tenant: str,
        previous_evidence: SQLiteRecoveryEvidence | None,
        legacy_generation: int | None,
    ) -> None:
        """Write generation G's binding inside G's open transaction.

        Continuity: the row being replaced must verify, exactly as recovery would, as the binding of
        this handle's previous generation (``previous_evidence``, with the journal tail G extends).
        It may be absent only when G is 1, or when G-1 is the generation this handle verified
        through a pre-#821 file (``legacy_generation``). The generation CAS already excludes another
        writer; this refuses a row that changed under the handle."""

        generation = int(base_evidence.generation)
        try:
            current = self._read(substrate)
            if current is None:
                if generation != 1 and generation - 1 != legacy_generation:
                    raise RuntimeRecoveryError(
                        f"configuration binding for generation {generation - 1} is missing"
                    )
            elif previous_evidence is None:
                raise RuntimeRecoveryError("a configuration binding exists before the first generation")
            else:
                _verified_binding_row(
                    current,
                    plan=plan,
                    base_evidence=previous_evidence,
                    tenant=tenant,
                    journal_record_digest=journal_record.get("previous_record_digest"),
                )
        except RuntimeRecoveryError as exc:
            raise RuntimeCheckpointConflict(
                f"configuration binding changed under this handle; refusing to bind generation {generation}: {exc}"
            ) from exc
        record = binding_record(plan=plan, base_evidence=base_evidence)
        record["base"]["journal_record_digest"] = journal_record["record_digest"]
        record.update(binding_protocol=SQLITE_CONFIG_BINDING_PROTOCOL, tenant=tenant)
        substrate.write_runtime_configuration_binding(generation, {**record, "record_digest": _digest(record)})

    def recover(
        self,
        substrate: SQLiteTemporalGraph,
        *,
        plan: RuntimeConfigurationPlan,
        base_evidence: SQLiteRecoveryEvidence,
        tenant: str,
        provider_failures=(),
        require_row: bool = False,
    ) -> tuple[ConfigBoundRecoveryEvidence, str]:
        current = self._read(substrate)
        if current is None and require_row:
            raise RuntimeRecoveryError(
                "SQLite configuration binding is missing although this store's generation witness "
                "shows its generations were bound in the database"
            )
        if current is None:
            evidence = self.legacy.recover(
                plan=plan, base_evidence=base_evidence, provider_failures=provider_failures
            )
            return evidence, LEGACY_FILE_BINDING
        recorded = substrate.read_runtime_binding()
        evidence = _verified_binding_row(
            current,
            plan=plan,
            base_evidence=base_evidence,
            tenant=tenant,
            journal_record_digest=None if recorded is None else recorded[1],
            provider_failures=provider_failures,
        )
        return evidence, SQLITE_TRANSACTION_BINDING


class GenerationWitness:
    """Advisory high-water mark of the last generation a #821 runtime committed (#821 amendment 1).

    ``{schema, generation, journal_record_digest}`` beside the database. It is written only after
    the COMMIT it names (and with generation 0 inside generation 1, once the database file exists),
    so it may lag the database but never lead it, and a lagging witness is accepted. It can only
    refuse: a database behind it, a database whose verified journal disagrees with it, a witness
    that cannot be read, or a witness with no database. Recovery reads it before reading the
    database, so a writer that commits in between can only make it lag (review N1). It is not a
    keyed or remote anchor; a store without one (pre-#821, or deleted) is not refused.
    """

    RESTORE_HINT = (
        "explicit operator action is required (if this database was restored deliberately, remove "
        f"{GENERATION_WITNESS_NAME} to accept it)"
    )
    UNREADABLE_HINT = (
        "explicit operator action is required (if the database is this store's own, remove "
        f"{GENERATION_WITNESS_NAME} to accept it)"
    )

    def __init__(self, root: str | Path) -> None:
        self.path = Path(root) / GENERATION_WITNESS_NAME

    def exists(self) -> bool:
        return self.path.exists()

    def record(self, generation: int, journal_record_digest: str) -> None:
        payload = _canonical_bytes({
            "schema": GENERATION_WITNESS_SCHEMA,
            "generation": int(generation),
            "journal_record_digest": journal_record_digest,
        }) + b"\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary, descriptor = self._exclusive_temporary()
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        directory = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _exclusive_temporary(self) -> tuple[Path, int]:
        """A temporary only this writer can have opened (review R-1). With one shared name, a second
        writer process truncated the inode the first was about to rename, and a crash or ENOSPC in
        between published an empty witness that refused every open. The mode stays ``0o666`` less
        the umask, as ``open("wb")`` created it."""

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        for _ in range(8):
            temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp")
            try:
                return temporary, os.open(temporary, flags, 0o666)
            except FileExistsError:
                continue
        raise FileExistsError(f"no unused temporary name for {self.path.name}")

    def read(self) -> tuple[int, str] | None:
        """``(generation, journal_record_digest)``, or None when there is no witness."""

        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise RuntimeRecoveryError(
                f"SQLite generation witness is unreadable: {exc}; {self.UNREADABLE_HINT}") from exc
        try:
            witness = json.loads(raw)
            if not isinstance(witness, dict) or witness.get("schema") != GENERATION_WITNESS_SCHEMA:
                raise ValueError("unsupported schema")
            witnessed = witness["generation"]
            digest = witness["journal_record_digest"]
            if type(witnessed) is not int or witnessed < 0 or not isinstance(digest, str):
                raise ValueError("malformed fields")
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeRecoveryError(
                f"SQLite generation witness is unreadable: {exc}; {self.UNREADABLE_HINT}") from exc
        return witnessed, digest

    @classmethod
    def check(cls, witnessed: tuple[int, str] | None, substrate: SQLiteTemporalGraph, generation: int) -> None:
        """Refuse a recovered database that a witness read before it shows is not this store's latest."""

        if witnessed is None:
            return
        witnessed, digest = witnessed
        if witnessed > generation:
            raise RuntimeRecoveryError(
                f"SQLite database is behind this store's generation witness ({generation} < {witnessed}): "
                f"it was rolled back or replaced; {cls.RESTORE_HINT}"
            )
        if witnessed == 0:
            return
        try:
            journal = substrate.read_runtime_journal_record(witnessed)
        except ValueError as exc:
            raise RuntimeRecoveryError("SQLite runtime journal row is malformed") from exc
        if journal is None or journal.get("record_digest") != digest:
            raise RuntimeRecoveryError(
                f"SQLite database does not continue the history this store witnessed at generation {witnessed}: "
                f"it was replaced; {cls.RESTORE_HINT}"
            )


def configuration_binding_row_present(database: str | Path) -> bool:
    """Whether a database file has a binding table, read-only (diagnostics; verifies nothing)."""

    try:
        connection = sqlite3.connect(f"file:{Path(database)}?mode=ro", uri=True)
        try:
            return connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'runtime_configuration_binding'"
            ).fetchone() is not None
        finally:
            connection.close()
    except sqlite3.DatabaseError:
        return False


def _refuse_witness_without_database(root: Path) -> None:
    if GenerationWitness(root).exists() and not (root / "agent-memory.sqlite3").exists():
        raise RuntimeRecoveryError(
            "incomplete durable state: generation witness exists without SQLite runtime database"
        )


class SQLiteConfigBoundRestartRuntime(ConfigBoundRestartRuntime):
    """Validated runtime plan composed with the transactional SQLite profile."""

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        tenant: str,
        plan: RuntimeConfigurationPlan,
        verifier_registry=None,
    ) -> "SQLiteConfigBoundRestartRuntime":
        root_path = Path(root)
        _refuse_witness_without_database(root_path)
        profile = _profile_from_plan(plan)
        binding_store = SQLiteConfigBindingStore(root_path)

        def bind_first(substrate, evidence, journal_record, generation_tenant):
            # The database file exists now; from here on a lost database is refused, never
            # re-created (amendment 1, F1; review N2). If generation 1 rolls back, the database
            # without runtime state is refused anyway (preregistration section 8).
            GenerationWitness(root_path).record(0, "")
            binding_store.publish(
                substrate, plan=plan, base_evidence=evidence, journal_record=journal_record,
                tenant=generation_tenant, previous_evidence=None, legacy_generation=None,
            )

        base = SQLiteRestartSafeRuntime.create(
            root_path,
            tenant=tenant,
            profile=profile,
            verifier_registry=verifier_registry,
            generation_binder=bind_first,
        )
        evidence = checkpoint_evidence(plan=plan, base_evidence=base.recovery_evidence)
        runtime = cls(base=base, plan=plan, binding_store=binding_store, recovery_evidence=evidence)
        runtime._record_witness()
        return runtime

    @classmethod
    def recover(
        cls,
        root: str | Path,
        *,
        plan: RuntimeConfigurationPlan,
        provider_failures=(),
        verifier_registry=None,
    ) -> "SQLiteConfigBoundRestartRuntime":
        root_path = Path(root)
        _refuse_witness_without_database(root_path)
        # Read the witness before the database (review N1): it only advances after a COMMIT, so a
        # writer that commits in between can only make this reading lag, never lead.
        witnessed = GenerationWitness(root_path).read()
        profile = _profile_from_plan(plan)
        base = SQLiteRestartSafeRuntime.recover(
            root_path,
            profile=profile,
            verifier_registry=verifier_registry,
        )
        try:
            GenerationWitness.check(witnessed, base.substrate, base.recovery_evidence.generation)
            _assert_visibility_matches_plan(base.visibility_snapshots, plan)
            binding_store = SQLiteConfigBindingStore(root_path)
            evidence, scheme = binding_store.recover(
                base.substrate,
                plan=plan,
                base_evidence=base.recovery_evidence,
                tenant=base.adapter.checkpoint_tenant(),
                provider_failures=provider_failures,
                # A witnessed generation was bound in a row; a missing table is not a pre-#821
                # store (review N4).
                require_row=witnessed is not None and witnessed[0] >= 1,
            )
        except BaseException:
            base.close()
            raise
        return cls(base=base, plan=plan, binding_store=binding_store, recovery_evidence=evidence,
                   binding_scheme=scheme)

    def __init__(self, *, binding_scheme: str = SQLITE_TRANSACTION_BINDING, **kwargs) -> None:
        super().__init__(**kwargs)
        # Which binding the last verified or published generation carries: a pre-#821 file until
        # this handle's first generation commits its row.
        self.binding_scheme = binding_scheme
        # The generation a pre-#821 file verified; only the next one may be the first with a row.
        self._legacy_generation = (
            self.recovery_evidence.base_generation if binding_scheme == LEGACY_FILE_BINDING else None
        )
        self.witness = GenerationWitness(self.base.root)
        # False while the witness lags a committed generation (a failed post-commit write).
        self.generation_witness_current = True
        # #821: every base generation, however the governed act reached it, commits its binding
        # in its own transaction; after COMMIT only the in-memory evidence and the witness follow.
        self.base.bind_generations(self._publish_binding)
        self.base.on_generation_published(self._binding_published)

    def _publish_binding(self, substrate, evidence, journal_record, tenant) -> None:
        # A generation whose visibility obligations this plan does not require would commit and
        # then be refused at recovery; refuse it here so it rolls back (amendment 1, A11).
        _assert_visibility_matches_plan(self.base.visibility_snapshots, self.plan)
        self.binding_store.publish(
            substrate,
            plan=self.plan,
            base_evidence=evidence,
            journal_record=journal_record,
            tenant=tenant,
            previous_evidence=self.base.recovery_evidence,
            legacy_generation=self._legacy_generation,
        )

    def _binding_published(self) -> None:
        self.binding_scheme = SQLITE_TRANSACTION_BINDING
        self._legacy_generation = None
        self.recovery_evidence = checkpoint_evidence(plan=self.plan, base_evidence=self.base.recovery_evidence)
        self._record_witness()

    def _record_witness(self) -> None:
        """Advance the witness to the committed generation. Best effort by construction: a witness
        that lags is accepted, so an ``OSError`` here leaves the generation committed and is
        retried by the next generation (``generation_witness_current`` reports it)."""

        binding = self.base.substrate.read_runtime_binding()
        self.generation_witness_current = False  # until the write below completes (review N3)
        try:
            self.witness.record(binding[0], binding[1])
        except OSError:
            self.generation_witness_current = False
        else:
            self.generation_witness_current = True

    def checkpoint(self) -> ConfigBoundRecoveryEvidence:
        self.base.checkpoint()
        return self.recovery_evidence

    def run_governed_read(self, operation):
        return self.base.run_governed_read(operation)

    def governed_recall(self, query, context=None):
        return self.run_governed_read(
            lambda: self.adapter.governed_recall(query, context)
        )

    def commit_proposal(self, proposal, fact_text: str, episode=None, *, evidence=None, attestation=None, temporal=None, replacement_kind="error_correction", source_ref=None, typed_write=None):
        result = self.base.commit_proposal(
            proposal,
            fact_text,
            episode,
            evidence=evidence,
            attestation=attestation,
            temporal=temporal,
            replacement_kind=replacement_kind,
            source_ref=source_ref,
            typed_write=typed_write,
        )
        return result

    def governed_delete(
        self,
        proposal,
        fact_uuid: str,
        derived_refs: tuple[str, ...] = (),
        external_verification=None,
        evidence=None,
    ):
        result = self.base.governed_delete(
            proposal,
            fact_uuid,
            derived_refs,
            external_verification,
            evidence,
        )
        return result

    def persist_visibility_snapshot(self, operation_id: str, snapshot: dict) -> ConfigBoundRecoveryEvidence:
        _assert_visibility_matches_plan({operation_id: snapshot}, self.plan)
        self.base.persist_visibility_snapshot(operation_id, snapshot)
        return self.recovery_evidence
