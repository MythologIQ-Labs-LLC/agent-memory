"""Governed durable-state migration for issue #417.

Structural governance decides whether a schema/profile transition is authorized.
This module does not re-decide that authority. It binds an authorized ADR-032
structural lifecycle to an exact committed checkpoint generation, applies a
named deterministic transformer, validates that migration did not launder away
governance state, and publishes the transformed state through the existing
checkpoint CAS protocol.

The reference file profile uses a migration guard: before any migration write,
it stores the exact source payloads/manifest/journal plus an intent describing
the expected target manifest. If the process dies mid-publication,
``recover_interrupted_migration`` deterministically recognizes a completed
target, a superseding writer, or restores the last committed source generation.

This is deliberately a memory-layer module. It consumes structural authority
from ``structural_mutation`` and the earlier runtime checkpoint contract; the
runtime layer must not import memory-layer governance back upward.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import json
import os
from pathlib import Path
from typing import Callable, Mapping

from .structural_mutation import (
    ACTIVE,
    AUTHORIZED,
    S2,
    S3,
    SchemaLifecycle,
    StructuralImpact,
    StructuralMutationError,
    rollback as structural_rollback,
)
from ..runtime.restart_runtime import (
    CheckpointableGovernedMemoryAdapter,
    DURABILITY_PROFILE,
    JOURNAL_SCHEMA_VERSION,
    SCHEMA_VERSION,
    TRANSACTION_PROTOCOL,
    RestartSafeRuntime,
    RuntimeCheckpointConflict,
    RuntimeProfile,
    RuntimeRecoveryError,
    _assert_manifest_matches_journal,
    _atomic_json_write,
    _canonical_bytes,
    _digest,
    _exclusive_checkpoint_lock,
    _fsync_directory,
    _read_generation_journal,
    _read_json,
    _restore_adapter,
    _restore_substrate,
    _snapshot_governance,
    _snapshot_substrate,
    _validate_generation_journal,
)


MIGRATION_SCHEMA_VERSION = "1.0.0"
MIGRATION_PROTOCOL = "governed_checkpoint_migration_v1"


class CheckpointMigrationError(RuntimeRecoveryError):
    """A durable migration cannot be proven or completed safely."""


@dataclass(frozen=True)
class MigrationState:
    """Component-owned checkpoint state presented to a deterministic transformer."""

    substrate: dict
    adapter: dict
    visibility_snapshots: dict[str, dict]

    def detached_copy(self) -> "MigrationState":
        return MigrationState(
            substrate=copy.deepcopy(self.substrate),
            adapter=copy.deepcopy(self.adapter),
            visibility_snapshots=copy.deepcopy(self.visibility_snapshots),
        )


@dataclass(frozen=True)
class MigrationPlan:
    migration_id: str
    source_generation: int
    source_schema_id: str
    source_schema_version: str
    target_schema_id: str
    target_schema_version: str
    structural_impact_digest: str
    authorization_ref: str
    approval_refs: tuple[str, ...]
    source_substrate_digest: str
    source_governance_digest: str
    source_interpretation_digest: str
    target_interpretation_digest: str
    transformer_id: str
    transformer_version: str
    compatibility_evidence_refs: tuple[str, ...]
    validation_refs: tuple[str, ...]
    rollback_ref: str
    semantic_changes: tuple[str, ...]
    lossy_fields: tuple[str, ...] = ()
    direction: str = "forward"

    def to_dict(self) -> dict:
        value = asdict(self)
        value["approval_refs"] = list(self.approval_refs)
        value["compatibility_evidence_refs"] = list(self.compatibility_evidence_refs)
        value["validation_refs"] = list(self.validation_refs)
        value["semantic_changes"] = list(self.semantic_changes)
        value["lossy_fields"] = list(self.lossy_fields)
        return {"schema_version": MIGRATION_SCHEMA_VERSION, **value}

    @property
    def plan_digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class MigrationExecution:
    migration_id: str
    plan_digest: str
    source_generation: int
    target_generation: int
    source_profile_digest: str
    target_profile_digest: str
    source_manifest_digest: str
    target_manifest_digest: str
    authorization_ref: str
    rollback_ref: str
    backup_ref: str
    record_ref: str
    status: str = "committed"

    def to_dict(self) -> dict:
        return {
            "schema_version": MIGRATION_SCHEMA_VERSION,
            "record_type": "migration_execution",
            **asdict(self),
        }


@dataclass(frozen=True)
class RollbackExecution:
    migration_id: str
    source_generation: int
    rollback_generation: int
    rollback_ref: str
    execution_ref: str
    record_ref: str
    status: str = "committed"


_PROTECTED_ADAPTER_FIELDS = (
    "checkpoint_owner",
    "selector_mode",
    "clock_tick",
    "id_counter",
    "state_version",
    "disputed",
    "tombstones",
    "fact_scope",
    "fact_memory",
    "shared_domain_members",
    "current_fact_by_memory",
    "rejected_values",
    "rejected_values_descriptor",
    "containment_violations",
    "events",
    "extension_state",
)

_MATURITY = {
    "declared": 0,
    "implemented": 1,
    "runtime_wired": 2,
    "evidence_proven": 3,
    "reference_qualified": 4,
}


def build_migration_plan(
    runtime: RestartSafeRuntime,
    *,
    target_profile: RuntimeProfile,
    impact: StructuralImpact,
    lifecycle: SchemaLifecycle,
    migration_id: str,
    transformer_id: str,
    transformer_version: str,
    compatibility_evidence_refs: tuple[str, ...] = (),
    validation_refs: tuple[str, ...] = (),
    lossy_fields: tuple[str, ...] = (),
) -> MigrationPlan:
    """Bind a plan to exact durable state and already-authorized structure."""
    evidence = runtime.recovery_evidence
    if evidence is None:
        raise CheckpointMigrationError("migration requires recovered checkpoint evidence")
    proposal = impact.proposal
    plan = MigrationPlan(
        migration_id=migration_id,
        source_generation=evidence.generation,
        source_schema_id=proposal.current_schema.schema_id,
        source_schema_version=proposal.current_schema.schema_version,
        target_schema_id=proposal.proposed_schema.schema_id,
        target_schema_version=proposal.proposed_schema.schema_version,
        structural_impact_digest=impact.impact_digest,
        authorization_ref=lifecycle.authorization_ref,
        approval_refs=lifecycle.approval_refs,
        source_substrate_digest=evidence.substrate_digest,
        source_governance_digest=evidence.governance_digest,
        source_interpretation_digest=runtime.profile.interpretation_digest,
        target_interpretation_digest=target_profile.interpretation_digest,
        transformer_id=transformer_id,
        transformer_version=transformer_version,
        compatibility_evidence_refs=tuple(compatibility_evidence_refs),
        validation_refs=tuple(validation_refs),
        rollback_ref=lifecycle.rollback_ref,
        semantic_changes=proposal.semantic_diff,
        lossy_fields=tuple(lossy_fields),
    )
    _validate_plan(plan)
    _validate_structural_binding(plan, impact, lifecycle)
    _validate_profile_transition(runtime.profile, target_profile, plan)
    return plan


def execute_migration(
    runtime: RestartSafeRuntime,
    *,
    target_profile: RuntimeProfile,
    impact: StructuralImpact,
    lifecycle: SchemaLifecycle,
    plan: MigrationPlan,
    transformer_id: str,
    transformer_version: str,
    transform: Callable[[MigrationState], MigrationState],
) -> tuple[RestartSafeRuntime, MigrationExecution]:
    """Execute one authorized deterministic migration as one new generation."""
    _validate_plan(plan)
    _validate_structural_binding(plan, impact, lifecycle)
    _validate_profile_transition(runtime.profile, target_profile, plan)
    _assert_runtime_matches_plan(runtime, plan)
    if transformer_id != plan.transformer_id or transformer_version != plan.transformer_version:
        raise CheckpointMigrationError("migration transformer identity/version does not match plan")
    if plan.lossy_fields:
        raise CheckpointMigrationError(
            "reference checkpoint migration refuses lossy transformation; use a stricter explicit profile"
        )

    source_state = _migration_state(runtime)
    try:
        target_state = transform(source_state.detached_copy())
    except Exception as exc:
        raise CheckpointMigrationError("deterministic migration transformer failed") from exc
    if not isinstance(target_state, MigrationState):
        raise CheckpointMigrationError("migration transformer must return MigrationState")
    _validate_migration_state(source_state, target_state)

    target_adapter = _adapter_from_state(runtime, target_state)
    expected_manifest = _expected_target_manifest(
        runtime,
        target_adapter=target_adapter,
        target_profile=target_profile,
        target_visibility=target_state.visibility_snapshots,
    )
    guard = _prepare_guard(
        runtime,
        operation_id=plan.migration_id,
        operation_digest=plan.plan_digest,
        operation_kind="migration",
        expected_target_manifest=expected_manifest,
    )
    try:
        result = runtime.store.checkpoint(
            target_adapter,
            profile=target_profile,
            visibility_snapshots=target_state.visibility_snapshots,
        )
    except Exception:
        recover_interrupted_migration(runtime.store.root)
        raise

    if result.generation != plan.source_generation + 1:
        recover_interrupted_migration(runtime.store.root)
        raise CheckpointMigrationError("migration did not publish exactly one new generation")

    execution = _finalize_guard(
        runtime.store.root,
        guard,
        migration_id=plan.migration_id,
        plan_digest=plan.plan_digest,
        authorization_ref=plan.authorization_ref,
        rollback_ref=plan.rollback_ref,
        source_profile_digest=runtime.profile.interpretation_digest,
        target_profile_digest=target_profile.interpretation_digest,
    )
    migrated = RestartSafeRuntime.recover(runtime.store.root, profile=target_profile)
    return migrated, execution


def recover_interrupted_migration(root: str | Path) -> dict | None:
    """Resolve a prepared migration after process failure.

    Returns a small recovery record. No intent means no migration recovery work.
    A fully committed target is finalized. A different *valid committed* newer
    generation is preserved as a superseding writer. Every torn/uncommitted
    state restores the exact source bundle captured before migration writes.
    """
    root = Path(root)
    intent_path = root / "runtime-migration-intent.json"
    if not intent_path.exists():
        return None
    lock_path = root / ".runtime-checkpoint.lock"
    with _exclusive_checkpoint_lock(lock_path):
        intent = _read_json(intent_path)
        _validate_intent(intent)
        backup_path = root / intent["backup_ref"]
        backup_envelope = _read_json(backup_path)
        backup = _validated_backup(backup_envelope, intent)

        manifest_path = root / "runtime-manifest.json"
        current_manifest = _read_json(manifest_path) if manifest_path.exists() else None
        current_digest = _digest(current_manifest) if current_manifest is not None else ""
        target_digest = intent["target_manifest_digest"]
        source_digest = intent["source_manifest_digest"]

        if current_manifest is not None and current_digest == target_digest:
            if _target_is_fully_committed(root, current_manifest):
                record = _recovery_record(intent, "target_committed")
                _write_recovery_record(root, intent, record)
                _remove_intent(root, intent_path)
                return record
            _restore_backup(root, backup)
            record = _recovery_record(intent, "source_restored_from_torn_target")
            _write_recovery_record(root, intent, record)
            _remove_intent(root, intent_path)
            return record

        valid_current = _try_valid_current_commit(root, current_manifest)
        if valid_current is not None:
            current_generation = int(valid_current["generation"])
            source_generation = int(intent["source_generation"])
            if current_generation > source_generation and current_digest not in {source_digest, target_digest}:
                record = _recovery_record(intent, "superseded_by_other_committed_writer")
                _write_recovery_record(root, intent, record)
                _remove_intent(root, intent_path)
                return record

        _restore_backup(root, backup)
        record = _recovery_record(intent, "source_restored")
        _write_recovery_record(root, intent, record)
        _remove_intent(root, intent_path)
        return record


def recover_migration_aware_runtime(
    root: str | Path,
    *,
    profile: RuntimeProfile,
    available_bindings=None,
    verifier_registry=None,
) -> RestartSafeRuntime:
    """Resolve any interrupted migration before normal restart recovery."""
    recover_interrupted_migration(root)
    return RestartSafeRuntime.recover(
        root,
        profile=profile,
        available_bindings=available_bindings,
        verifier_registry=verifier_registry,
    )


def rollback_migration(
    runtime: RestartSafeRuntime,
    *,
    source_profile: RuntimeProfile,
    lifecycle: SchemaLifecycle,
    execution: MigrationExecution,
) -> tuple[RestartSafeRuntime, SchemaLifecycle, RollbackExecution]:
    """Publish the exact pre-migration checkpoint as a *new* generation.

    Raw rollback is allowed only while the migration generation is still the
    current generation. If any correction, deletion, or ordinary checkpoint has
    advanced state since migration, rollback refuses rather than resurrecting
    older durable state. A later rollback must be a new governed migration or
    compensation over the current generation.
    """
    current = runtime.recovery_evidence
    if current is None:
        raise CheckpointMigrationError("rollback requires recovered checkpoint evidence")
    if current.generation != execution.target_generation:
        raise CheckpointMigrationError(
            "rollback target is stale; later durable state exists and must not be resurrected"
        )
    if runtime.profile.interpretation_digest != execution.target_profile_digest:
        raise CheckpointMigrationError("rollback runtime profile does not match migration target")
    if lifecycle.lifecycle_state not in {AUTHORIZED, ACTIVE}:
        raise CheckpointMigrationError("rollback requires authorized or active schema lifecycle")
    if lifecycle.rollback_ref != execution.rollback_ref:
        raise CheckpointMigrationError("rollback reference does not match migration execution")

    backup_path = runtime.store.root / execution.backup_ref
    envelope = _read_json(backup_path)
    backup = _validated_backup(envelope, None)
    source_governance = backup["governance"]
    if source_governance.get("profile") != source_profile.to_dict():
        raise CheckpointMigrationError("rollback source profile does not match migration backup")
    source_substrate = _restore_substrate(backup["substrate"])
    source_adapter, source_visibility = _restore_adapter(source_substrate, source_governance)

    expected_manifest = _expected_target_manifest(
        runtime,
        target_adapter=source_adapter,
        target_profile=source_profile,
        target_visibility=source_visibility,
    )
    rollback_id = f"rollback:{execution.migration_id}:{current.generation}"
    guard = _prepare_guard(
        runtime,
        operation_id=rollback_id,
        operation_digest=execution.plan_digest,
        operation_kind="rollback",
        expected_target_manifest=expected_manifest,
    )
    try:
        result = runtime.store.checkpoint(
            source_adapter,
            profile=source_profile,
            visibility_snapshots=source_visibility,
        )
    except Exception:
        recover_interrupted_migration(runtime.store.root)
        raise

    rollback_execution_ref = f"migration-rollback:{_digest({'id': rollback_id, 'generation': result.generation})}"
    rolled_lifecycle = structural_rollback(
        lifecycle,
        rollback_ref=execution.rollback_ref,
        execution_ref=rollback_execution_ref,
    )
    rollback_record = _finalize_rollback_guard(
        runtime.store.root,
        guard,
        migration_id=execution.migration_id,
        rollback_ref=execution.rollback_ref,
        execution_ref=rollback_execution_ref,
        source_generation=execution.target_generation,
        rollback_generation=result.generation,
    )
    recovered = RestartSafeRuntime.recover(runtime.store.root, profile=source_profile)
    return recovered, rolled_lifecycle, rollback_record


def _validate_plan(plan: MigrationPlan) -> None:
    strings = (
        plan.migration_id,
        plan.source_schema_id,
        plan.source_schema_version,
        plan.target_schema_id,
        plan.target_schema_version,
        plan.structural_impact_digest,
        plan.authorization_ref,
        plan.source_substrate_digest,
        plan.source_governance_digest,
        plan.source_interpretation_digest,
        plan.target_interpretation_digest,
        plan.transformer_id,
        plan.transformer_version,
        plan.rollback_ref,
    )
    if any(not value for value in strings):
        raise CheckpointMigrationError("migration plan requires stable non-empty identifiers")
    if plan.source_generation < 1:
        raise CheckpointMigrationError("migration source generation must be positive")
    if plan.direction != "forward":
        raise CheckpointMigrationError("direct downgrade/rollback plans are unsupported; use governed rollback")
    for name in (
        "structural_impact_digest",
        "source_substrate_digest",
        "source_governance_digest",
        "source_interpretation_digest",
        "target_interpretation_digest",
    ):
        value = getattr(plan, name)
        if not value.startswith("sha256:") or len(value) != 71:
            raise CheckpointMigrationError(f"migration plan {name} must be sha256:<64 hex>")
    if not plan.approval_refs:
        raise CheckpointMigrationError("durable migration requires explicit approval references")
    if not plan.validation_refs:
        raise CheckpointMigrationError("durable migration requires validation evidence")
    if not plan.semantic_changes:
        raise CheckpointMigrationError("durable migration requires explicit semantic-change record")


def _validate_structural_binding(
    plan: MigrationPlan,
    impact: StructuralImpact,
    lifecycle: SchemaLifecycle,
) -> None:
    proposal = impact.proposal
    if lifecycle.lifecycle_state != AUTHORIZED:
        raise CheckpointMigrationError(
            "migration execution requires authorized structural lifecycle before activation"
        )
    if lifecycle.structural_class not in {S2, S3}:
        raise CheckpointMigrationError("durable migration requires S2/S3 structural authority")
    if not proposal.migration_required:
        raise CheckpointMigrationError("structural proposal does not require durable migration")
    if impact.impact_digest != plan.structural_impact_digest or lifecycle.impact_digest != plan.structural_impact_digest:
        raise CheckpointMigrationError("migration plan is not bound to the authorized structural impact")
    if lifecycle.authorization_ref != plan.authorization_ref:
        raise CheckpointMigrationError("migration authorization reference does not match lifecycle")
    if tuple(lifecycle.approval_refs) != tuple(plan.approval_refs):
        raise CheckpointMigrationError("migration approval references do not match lifecycle")
    if lifecycle.rollback_ref != plan.rollback_ref:
        raise CheckpointMigrationError("migration rollback reference does not match lifecycle")
    if (
        proposal.current_schema.schema_id != plan.source_schema_id
        or proposal.current_schema.schema_version != plan.source_schema_version
        or proposal.proposed_schema.schema_id != plan.target_schema_id
        or proposal.proposed_schema.schema_version != plan.target_schema_version
    ):
        raise CheckpointMigrationError("migration schema transition does not match structural proposal")
    if tuple(proposal.semantic_diff) != tuple(plan.semantic_changes):
        raise CheckpointMigrationError("migration semantic changes do not match structural proposal")
    if lifecycle.state_digest != proposal.state_digest or lifecycle.dependency_digest != proposal.dependency_digest:
        raise CheckpointMigrationError("authorized lifecycle no longer matches structural snapshots")


def _validate_profile_transition(
    source: RuntimeProfile,
    target: RuntimeProfile,
    plan: MigrationPlan,
) -> None:
    if source.interpretation_digest != plan.source_interpretation_digest:
        raise CheckpointMigrationError("source runtime interpretation does not match migration plan")
    if target.interpretation_digest != plan.target_interpretation_digest:
        raise CheckpointMigrationError("target runtime interpretation does not match migration plan")
    if source.profile_id != target.profile_id:
        raise CheckpointMigrationError("reference migration cannot change runtime profile identity")
    if source.to_dict() == target.to_dict():
        return
    if not plan.compatibility_evidence_refs:
        raise CheckpointMigrationError(
            "runtime interpretation change requires explicit compatibility evidence"
        )

    source_by_cap = {binding.capability_id: binding for binding in source.bindings}
    target_by_cap = {binding.capability_id: binding for binding in target.bindings}
    if set(source_by_cap) != set(target_by_cap):
        raise CheckpointMigrationError(
            "reference migration cannot add/remove capabilities; use a separately qualified composition migration"
        )
    for capability_id, target_binding in target_by_cap.items():
        source_binding = source_by_cap[capability_id]
        if source_binding == target_binding:
            continue
        source_rank = _MATURITY.get(source_binding.maturity)
        target_rank = _MATURITY.get(target_binding.maturity)
        if source_rank is None or target_rank is None:
            raise CheckpointMigrationError("migration encountered unknown capability maturity")
        if target_rank != source_rank and target_binding.evidence_ref == source_binding.evidence_ref:
            raise CheckpointMigrationError(
                f"capability {capability_id} maturity changed without distinct qualification evidence"
            )


def _assert_runtime_matches_plan(runtime: RestartSafeRuntime, plan: MigrationPlan) -> None:
    evidence = runtime.recovery_evidence
    if evidence is None:
        raise CheckpointMigrationError("migration requires recovered checkpoint evidence")
    if evidence.generation != plan.source_generation:
        raise RuntimeCheckpointConflict(
            f"migration plan is stale: source generation {plan.source_generation}, current {evidence.generation}"
        )
    if evidence.substrate_digest != plan.source_substrate_digest:
        raise CheckpointMigrationError("migration source substrate digest changed")
    if evidence.governance_digest != plan.source_governance_digest:
        raise CheckpointMigrationError("migration source governance digest changed")
    if runtime.profile.interpretation_digest != plan.source_interpretation_digest:
        raise CheckpointMigrationError("migration source profile interpretation changed")


def _migration_state(runtime: RestartSafeRuntime) -> MigrationState:
    adapter = runtime.adapter
    substrate_reader = getattr(adapter, "checkpoint_substrate", None)
    exporter = getattr(adapter, "export_checkpoint_state", None)
    if not callable(substrate_reader) or not callable(exporter):
        raise CheckpointMigrationError("runtime adapter does not declare checkpoint migration capability")
    return MigrationState(
        substrate=_snapshot_substrate(substrate_reader()),
        adapter=copy.deepcopy(exporter()),
        visibility_snapshots=copy.deepcopy(runtime.visibility_snapshots),
    )


def _validate_migration_state(source: MigrationState, target: MigrationState) -> None:
    if target.visibility_snapshots != source.visibility_snapshots:
        raise CheckpointMigrationError(
            "migration cannot erase or reinterpret pending visibility obligations"
        )
    for field in _PROTECTED_ADAPTER_FIELDS:
        if target.adapter.get(field) != source.adapter.get(field):
            raise CheckpointMigrationError(
                f"migration cannot alter protected governance checkpoint field {field}"
            )

    if target.substrate.get("schema_version") != source.substrate.get("schema_version"):
        raise CheckpointMigrationError(
            "reference migration cannot change physical checkpoint schema; provider migration required"
        )
    if target.substrate.get("checkpoint_owner") != source.substrate.get("checkpoint_owner"):
        raise CheckpointMigrationError("migration cannot change checkpoint state owner")
    if target.substrate.get("id_counter") != source.substrate.get("id_counter"):
        raise CheckpointMigrationError("migration cannot rewind or advance identifier state")
    if target.substrate.get("episodes") != source.substrate.get("episodes"):
        raise CheckpointMigrationError("migration cannot rewrite raw source episodes")
    if target.substrate.get("write_log") != source.substrate.get("write_log"):
        raise CheckpointMigrationError("migration cannot rewrite substrate mutation history")

    source_facts = {row["uuid"]: row for row in source.substrate.get("facts", ())}
    target_facts = {row["uuid"]: row for row in target.substrate.get("facts", ())}
    if set(source_facts) != set(target_facts):
        raise CheckpointMigrationError("migration cannot add or remove durable fact identities")
    protected_fact_fields = (
        "uuid",
        "group_id",
        "episode_uuids",
        "valid_at",
        "invalid_at",
        "created_at",
        "expired_at",
    )
    for fact_id, source_fact in source_facts.items():
        target_fact = target_facts[fact_id]
        for field in protected_fact_fields:
            if target_fact.get(field) != source_fact.get(field):
                raise CheckpointMigrationError(
                    f"migration cannot alter fact authority/currentness field {field} for {fact_id}"
                )
        if source_fact.get("fact_text") and not target_fact.get("fact_text"):
            raise CheckpointMigrationError("migration cannot erase durable fact content")


def _adapter_from_state(runtime: RestartSafeRuntime, state: MigrationState):
    substrate = _restore_substrate(state.substrate)
    tenant_reader = getattr(runtime.adapter, "checkpoint_tenant", None)
    if not callable(tenant_reader):
        raise CheckpointMigrationError("runtime adapter has no checkpoint tenant binding")
    adapter = CheckpointableGovernedMemoryAdapter(substrate, tenant=tenant_reader())
    try:
        adapter.restore_checkpoint_state(state.adapter)
    except (TypeError, ValueError) as exc:
        raise CheckpointMigrationError("transformed governance state cannot be reconstructed") from exc
    return adapter


def _expected_target_manifest(
    runtime: RestartSafeRuntime,
    *,
    target_adapter,
    target_profile: RuntimeProfile,
    target_visibility: dict[str, dict],
) -> dict:
    substrate = _snapshot_substrate(target_adapter.checkpoint_substrate())
    governance = _snapshot_governance(
        target_adapter,
        profile=target_profile,
        visibility_snapshots=target_visibility,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "durability_profile": DURABILITY_PROFILE,
        "transaction_protocol": TRANSACTION_PROTOCOL,
        "generation": runtime.recovery_evidence.generation + 1,
        "substrate_digest": _digest(substrate),
        "governance_digest": _digest(governance),
        "interpretation_digest": target_profile.interpretation_digest,
    }


def _prepare_guard(
    runtime: RestartSafeRuntime,
    *,
    operation_id: str,
    operation_digest: str,
    operation_kind: str,
    expected_target_manifest: dict,
) -> dict:
    store = runtime.store
    root = store.root
    with _exclusive_checkpoint_lock(store.lock_path):
        current_manifest, _latest = store._current_manifest_and_journal()
        if current_manifest is None:
            raise CheckpointMigrationError("migration source manifest is missing")
        source_evidence = runtime.recovery_evidence
        current_generation = int(current_manifest.get("generation", 0))
        if source_evidence is None or current_generation != source_evidence.generation:
            raise RuntimeCheckpointConflict("migration source generation advanced before prepare")
        if _digest(current_manifest) != store._observed_manifest_digest:
            raise RuntimeCheckpointConflict("migration source manifest changed before prepare")
        substrate = _read_json(store.substrate_path)
        governance = _read_json(store.governance_path)
        if _digest(substrate) != current_manifest.get("substrate_digest"):
            raise CheckpointMigrationError("migration source substrate failed integrity validation")
        if _digest(governance) != current_manifest.get("governance_digest"):
            raise CheckpointMigrationError("migration source governance failed integrity validation")
        journal_records = _read_generation_journal(store.journal_path)
        if journal_records:
            latest = _validate_generation_journal(journal_records)
            _assert_manifest_matches_journal(current_manifest, latest)

        archive_dir = root / "migrations"
        archive_dir.mkdir(parents=True, exist_ok=True)
        token = operation_digest.removeprefix("sha256:")
        backup_rel = f"migrations/{token}.source.json"
        record_rel = f"migrations/{token}.record.json"
        backup = {
            "schema_version": MIGRATION_SCHEMA_VERSION,
            "operation_id": operation_id,
            "operation_kind": operation_kind,
            "source_manifest": current_manifest,
            "substrate": substrate,
            "governance": governance,
            "journal_present": store.journal_path.exists(),
            "journal_records": journal_records,
        }
        backup_envelope = {
            "backup": backup,
            "backup_digest": _digest(backup),
        }
        _atomic_json_write(root / backup_rel, backup_envelope)
        intent = {
            "schema_version": MIGRATION_SCHEMA_VERSION,
            "protocol": MIGRATION_PROTOCOL,
            "operation_id": operation_id,
            "operation_kind": operation_kind,
            "operation_digest": operation_digest,
            "source_generation": current_generation,
            "source_manifest_digest": _digest(current_manifest),
            "target_generation": int(expected_target_manifest["generation"]),
            "target_manifest_digest": _digest(expected_target_manifest),
            "backup_ref": backup_rel,
            "backup_digest": backup_envelope["backup_digest"],
            "record_ref": record_rel,
        }
        _atomic_json_write(root / "runtime-migration-intent.json", intent)
        return intent


def _finalize_guard(
    root: Path,
    guard: dict,
    *,
    migration_id: str,
    plan_digest: str,
    authorization_ref: str,
    rollback_ref: str,
    source_profile_digest: str,
    target_profile_digest: str,
) -> MigrationExecution:
    root = Path(root)
    with _exclusive_checkpoint_lock(root / ".runtime-checkpoint.lock"):
        intent = _read_json(root / "runtime-migration-intent.json")
        if intent != guard:
            raise CheckpointMigrationError("migration intent changed before finalization")
        manifest = _read_json(root / "runtime-manifest.json")
        if _digest(manifest) != guard["target_manifest_digest"]:
            raise CheckpointMigrationError("committed migration manifest does not match prepared target")
        if not _target_is_fully_committed(root, manifest):
            raise CheckpointMigrationError("migration target is not fully committed")
        execution = MigrationExecution(
            migration_id=migration_id,
            plan_digest=plan_digest,
            source_generation=int(guard["source_generation"]),
            target_generation=int(guard["target_generation"]),
            source_profile_digest=source_profile_digest,
            target_profile_digest=target_profile_digest,
            source_manifest_digest=guard["source_manifest_digest"],
            target_manifest_digest=guard["target_manifest_digest"],
            authorization_ref=authorization_ref,
            rollback_ref=rollback_ref,
            backup_ref=guard["backup_ref"],
            record_ref=guard["record_ref"],
        )
        _atomic_json_write(root / guard["record_ref"], execution.to_dict())
        _remove_intent(root, root / "runtime-migration-intent.json")
        return execution


def _finalize_rollback_guard(
    root: Path,
    guard: dict,
    *,
    migration_id: str,
    rollback_ref: str,
    execution_ref: str,
    source_generation: int,
    rollback_generation: int,
) -> RollbackExecution:
    root = Path(root)
    with _exclusive_checkpoint_lock(root / ".runtime-checkpoint.lock"):
        intent = _read_json(root / "runtime-migration-intent.json")
        if intent != guard:
            raise CheckpointMigrationError("rollback intent changed before finalization")
        manifest = _read_json(root / "runtime-manifest.json")
        if _digest(manifest) != guard["target_manifest_digest"] or not _target_is_fully_committed(root, manifest):
            raise CheckpointMigrationError("rollback target is not fully committed")
        record_ref = guard["record_ref"]
        value = {
            "schema_version": MIGRATION_SCHEMA_VERSION,
            "record_type": "migration_rollback",
            "migration_id": migration_id,
            "source_generation": source_generation,
            "rollback_generation": rollback_generation,
            "rollback_ref": rollback_ref,
            "execution_ref": execution_ref,
            "status": "committed",
        }
        _atomic_json_write(root / record_ref, value)
        _remove_intent(root, root / "runtime-migration-intent.json")
        return RollbackExecution(
            migration_id=migration_id,
            source_generation=source_generation,
            rollback_generation=rollback_generation,
            rollback_ref=rollback_ref,
            execution_ref=execution_ref,
            record_ref=record_ref,
        )


def _validate_intent(intent: Mapping[str, object]) -> None:
    if intent.get("schema_version") != MIGRATION_SCHEMA_VERSION or intent.get("protocol") != MIGRATION_PROTOCOL:
        raise CheckpointMigrationError("unsupported migration intent")
    for key in (
        "operation_id",
        "operation_kind",
        "operation_digest",
        "source_manifest_digest",
        "target_manifest_digest",
        "backup_ref",
        "backup_digest",
        "record_ref",
    ):
        if not intent.get(key):
            raise CheckpointMigrationError(f"migration intent missing {key}")


def _validated_backup(envelope: Mapping[str, object], intent: Mapping[str, object] | None) -> dict:
    backup = envelope.get("backup")
    digest = envelope.get("backup_digest")
    if not isinstance(backup, dict) or digest != _digest(backup):
        raise CheckpointMigrationError("migration backup digest mismatch")
    if intent is not None and digest != intent.get("backup_digest"):
        raise CheckpointMigrationError("migration intent does not bind the source backup")
    return backup


def _target_is_fully_committed(root: Path, manifest: Mapping[str, object]) -> bool:
    try:
        journal = _read_generation_journal(root / "runtime-generation-journal.jsonl")
        latest = _validate_generation_journal(journal)
        if latest is None:
            return False
        _assert_manifest_matches_journal(manifest, latest)
        substrate = _read_json(root / "substrate.json")
        governance = _read_json(root / "governance.json")
        return (
            _digest(substrate) == manifest.get("substrate_digest")
            and _digest(governance) == manifest.get("governance_digest")
        )
    except RuntimeRecoveryError:
        return False


def _try_valid_current_commit(root: Path, manifest: Mapping[str, object] | None) -> dict | None:
    if manifest is None:
        return None
    try:
        if not _target_is_fully_committed(root, manifest):
            return None
        return dict(manifest)
    except RuntimeRecoveryError:
        return None


def _restore_backup(root: Path, backup: Mapping[str, object]) -> None:
    source_manifest = backup.get("source_manifest")
    substrate = backup.get("substrate")
    governance = backup.get("governance")
    journal_records = backup.get("journal_records", [])
    if not isinstance(source_manifest, dict) or not isinstance(substrate, dict) or not isinstance(governance, dict):
        raise CheckpointMigrationError("migration source backup is malformed")
    _atomic_json_write(root / "substrate.json", substrate)
    _atomic_json_write(root / "governance.json", governance)
    _atomic_json_write(root / "runtime-manifest.json", source_manifest)
    journal_path = root / "runtime-generation-journal.jsonl"
    if backup.get("journal_present"):
        _atomic_journal_write(journal_path, journal_records)
    elif journal_path.exists():
        journal_path.unlink()
        _fsync_directory(root)

    if _digest(_read_json(root / "runtime-manifest.json")) != _digest(source_manifest):
        raise CheckpointMigrationError("source manifest restore verification failed")
    if _digest(_read_json(root / "substrate.json")) != source_manifest.get("substrate_digest"):
        raise CheckpointMigrationError("source substrate restore verification failed")
    if _digest(_read_json(root / "governance.json")) != source_manifest.get("governance_digest"):
        raise CheckpointMigrationError("source governance restore verification failed")
    if backup.get("journal_present"):
        latest = _validate_generation_journal(_read_generation_journal(journal_path))
        _assert_manifest_matches_journal(source_manifest, latest)


def _atomic_journal_write(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    payload = b"".join(_canonical_bytes(dict(record)) + b"\n" for record in records)
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_directory(path.parent)


def _recovery_record(intent: Mapping[str, object], outcome: str) -> dict:
    return {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "record_type": "migration_recovery",
        "operation_id": intent["operation_id"],
        "operation_kind": intent["operation_kind"],
        "operation_digest": intent["operation_digest"],
        "source_generation": intent["source_generation"],
        "target_generation": intent["target_generation"],
        "outcome": outcome,
        "backup_ref": intent["backup_ref"],
    }


def _write_recovery_record(root: Path, intent: Mapping[str, object], record: dict) -> None:
    token = str(intent["operation_digest"]).removeprefix("sha256:")
    _atomic_json_write(root / "migrations" / f"{token}.recovery.json", record)


def _remove_intent(root: Path, intent_path: Path) -> None:
    try:
        intent_path.unlink()
    except FileNotFoundError:
        return
    _fsync_directory(root)
