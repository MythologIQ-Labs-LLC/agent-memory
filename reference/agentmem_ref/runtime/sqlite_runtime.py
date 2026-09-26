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

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .configured_restart import (
    ConfigBindingStore,
    ConfigBoundRecoveryEvidence,
    ConfigBoundRestartRuntime,
    _assert_visibility_matches_plan,
    _profile_from_plan,
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
from ..state.sqlite_substrate import SQLiteTemporalGraph, SQLITE_SUBSTRATE_PROFILE


SQLITE_RUNTIME_SCHEMA_VERSION = "1.0.0"
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
        runtime = cls(
            root=root_path,
            substrate=substrate,
            profile=profile,
            adapter=adapter,
            observed_generation=0,
            verifier_registry=verifier_registry,
        )
        runtime.recovery_evidence = runtime.checkpoint()
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
            if state.get("schema_version") != SQLITE_RUNTIME_SCHEMA_VERSION:
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

            governance = state.get("governance")
            if not isinstance(governance, dict):
                raise RuntimeRecoveryError("SQLite governance state is missing")
            if _digest(governance) != state.get("governance_digest"):
                raise RuntimeRecoveryError("SQLite governance state digest mismatch")
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

        governance = self._governance_snapshot()
        governance_digest = _digest(governance)
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
            "schema_version": SQLITE_RUNTIME_SCHEMA_VERSION,
            "durability_profile": SQLITE_DURABILITY_PROFILE,
            "transaction_protocol": SQLITE_TRANSACTION_PROTOCOL,
            "generation": generation,
            "profile": self.profile.to_dict(),
            "interpretation_digest": self.profile.interpretation_digest,
            "substrate_digest": substrate_digest,
            "governance_digest": governance_digest,
            "governance": governance,
            "substrate_identity": self.substrate.operational_identity(),
            "journal_record_digest": record["record_digest"],
        }
        self.substrate.write_runtime_state(state)
        self.substrate.append_runtime_journal(generation, record)
        return SQLiteRecoveryEvidence(
            generation=generation,
            durability_profile=SQLITE_DURABILITY_PROFILE,
            substrate_digest=substrate_digest,
            governance_digest=governance_digest,
            interpretation_digest=self.profile.interpretation_digest,
            recovered_visibility_operations=tuple(sorted(self.visibility_snapshots)),
            sqlite_version=self.substrate.sqlite_version,
            recovery_posture="committed_atomic_sqlite_generation",
        )

    def checkpoint(self) -> SQLiteRecoveryEvidence:
        with self.substrate.transaction():
            evidence = self._persist_unlocked()
        self._observed_generation = evidence.generation
        self.recovery_evidence = evidence
        return evidence

    def _restore_governance_after_rollback(self) -> None:
        state = self.substrate.read_runtime_state()
        if state is None:
            return
        governance = state.get("governance", {})
        if not isinstance(governance, dict):
            raise RuntimeRecoveryError("cannot restore governance after SQLite rollback")
        adapter_raw = governance.get("adapter")
        visibility = governance.get("visibility_snapshots", {})
        if not isinstance(adapter_raw, dict) or not isinstance(visibility, dict):
            raise RuntimeRecoveryError("cannot restore governance after SQLite rollback")
        self.adapter.restore_checkpoint_state(adapter_raw)
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
        try:
            with self.substrate.transaction():
                binding = self.substrate.read_runtime_binding()
                generation = 0 if binding is None else binding[0]
                if generation != self._observed_generation:
                    raise RuntimeCheckpointConflict(
                        "SQLite generation conflict: "
                        f"observed {self._observed_generation}, current {generation}"
                    )
                result = operation()
                evidence = self._persist_unlocked()
        except Exception:
            self._restore_governance_after_rollback()
            raise
        self._observed_generation = evidence.generation
        self.recovery_evidence = evidence
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
    ):
        return self._transactional_operation(
            lambda: self.adapter.commit_proposal(
                proposal,
                fact_text,
                episode,
                evidence=evidence,
                attestation=attestation,
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
        previous = dict(self.visibility_snapshots)
        self.visibility_snapshots[operation_id] = snapshot
        try:
            return self.checkpoint()
        except Exception:
            self.visibility_snapshots = previous
            raise

    def backup_to(self, destination: str | Path) -> None:
        self.substrate.backup_to(destination)


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
        profile = _profile_from_plan(plan)
        base = SQLiteRestartSafeRuntime.create(
            root,
            tenant=tenant,
            profile=profile,
            verifier_registry=verifier_registry,
        )
        binding_store = ConfigBindingStore(root)
        evidence = binding_store.checkpoint(plan=plan, base_evidence=base.recovery_evidence)
        return cls(base=base, plan=plan, binding_store=binding_store, recovery_evidence=evidence)

    @classmethod
    def recover(
        cls,
        root: str | Path,
        *,
        plan: RuntimeConfigurationPlan,
        provider_failures=(),
        verifier_registry=None,
    ) -> "SQLiteConfigBoundRestartRuntime":
        profile = _profile_from_plan(plan)
        base = SQLiteRestartSafeRuntime.recover(
            root,
            profile=profile,
            verifier_registry=verifier_registry,
        )
        _assert_visibility_matches_plan(base.visibility_snapshots, plan)
        binding_store = ConfigBindingStore(root)
        evidence = binding_store.recover(
            plan=plan,
            base_evidence=base.recovery_evidence,
            provider_failures=provider_failures,
        )
        return cls(base=base, plan=plan, binding_store=binding_store, recovery_evidence=evidence)

    def _bind_current_base(self) -> ConfigBoundRecoveryEvidence:
        self.recovery_evidence = self.binding_store.checkpoint(
            plan=self.plan,
            base_evidence=self.base.recovery_evidence,
        )
        return self.recovery_evidence

    def checkpoint(self) -> ConfigBoundRecoveryEvidence:
        self.base.checkpoint()
        return self._bind_current_base()

    def run_governed_read(self, operation):
        result = self.base.run_governed_read(operation)
        self._bind_current_base()
        return result

    def governed_recall(self, query, context=None):
        return self.run_governed_read(
            lambda: self.adapter.governed_recall(query, context)
        )

    def commit_proposal(self, proposal, fact_text: str, episode=None, *, evidence=None, attestation=None):
        result = self.base.commit_proposal(
            proposal,
            fact_text,
            episode,
            evidence=evidence,
            attestation=attestation,
        )
        self._bind_current_base()
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
        self._bind_current_base()
        return result

    def persist_visibility_snapshot(self, operation_id: str, snapshot: dict) -> ConfigBoundRecoveryEvidence:
        _assert_visibility_matches_plan({operation_id: snapshot}, self.plan)
        self.base.persist_visibility_snapshot(operation_id, snapshot)
        return self._bind_current_base()
