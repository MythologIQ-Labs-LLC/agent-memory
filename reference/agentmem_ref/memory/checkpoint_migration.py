"""Governed durable-state migration for issue #417 / #419.

Structural governance decides whether a schema/profile transition is authorized.
This module does not re-decide that authority. It binds an authorized ADR-032
structural lifecycle to an exact committed checkpoint generation, applies a
named deterministic transformer, validates that migration did not launder away
governance state, and publishes through the checkpoint CAS protocol.

Issue #419 narrows the implementation boundary: migration now consumes the
public checkpoint transaction-support seam. Locking, journal validation,
store-observation state, checkpoint preview construction, and exact bundle
restoration remain runtime persistence responsibilities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import hashlib
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
    rollback as structural_rollback,
)
from ..runtime.checkpoint_transactions import (
    CheckpointTransactionSupport,
    CommittedCheckpointBundle,
)
from ..runtime.restart_runtime import (
    JsonRuntimeStateStore,
    RestartSafeRuntime,
    RuntimeCheckpointConflict,
    RuntimeProfile,
    RuntimeRecoveryError,
    SCHEMA_VERSION,
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
        for field in (
            "approval_refs",
            "compatibility_evidence_refs",
            "validation_refs",
            "semantic_changes",
            "lossy_fields",
        ):
            value[field] = list(value[field])
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


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _read_json(path: Path) -> dict:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise CheckpointMigrationError(f"required migration state missing: {path.name}") from exc
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckpointMigrationError(f"migration state is corrupt: {path.name}") from exc
    if not isinstance(value, dict):
        raise CheckpointMigrationError(f"migration state must be an object: {path.name}")
    return value


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json_write(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    payload = _canonical_bytes(dict(value)) + b"\n"
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_directory(path.parent)


def _support(runtime: RestartSafeRuntime) -> CheckpointTransactionSupport:
    return CheckpointTransactionSupport(runtime.store)


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
        runtime,
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
    """Resolve a prepared migration while preserving any valid newer writer."""
    root = Path(root)
    intent_path = root / "runtime-migration-intent.json"
    if not intent_path.exists():
        return None

    store = JsonRuntimeStateStore(root)
    support = CheckpointTransactionSupport(store)
    with support.serialized() as transaction:
        intent = _read_json(intent_path)
        _validate_intent(intent)
        backup = _validated_backup(_read_json(root / str(intent["backup_ref"])), intent)
        backup_bundle = _bundle_from_backup(backup)

        current_manifest = transaction.read_manifest()
        current_digest = _digest(current_manifest) if current_manifest is not None else ""
        target_digest = str(intent["target_manifest_digest"])
        source_digest = str(intent["source_manifest_digest"])

        if current_manifest is not None and current_digest == target_digest:
            if transaction.is_fully_committed(current_manifest):
                record = _recovery_record(intent, "target_committed")
                _write_recovery_record(root, intent, record)
                _remove_intent(root, intent_path)
                return record
            transaction.restore_bundle(backup_bundle)
            record = _recovery_record(intent, "source_restored_from_torn_target")
            _write_recovery_record(root, intent, record)
            _remove_intent(root, intent_path)
            return record

        valid_current = transaction.try_current_bundle()
        if valid_current is not None:
            source_generation = int(intent["source_generation"])
            if (
                valid_current.generation > source_generation
                and current_digest not in {source_digest, target_digest}
            ):
                record = _recovery_record(intent, "superseded_by_other_committed_writer")
                _write_recovery_record(root, intent, record)
                _remove_intent(root, intent_path)
                return record

        transaction.restore_bundle(backup_bundle)
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
    """Publish the exact pre-migration state as a new generation."""
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

    backup = _validated_backup(
        _read_json(runtime.store.root / execution.backup_ref),
        None,
    )
    source_governance = backup["governance"]
    if source_governance.get("profile") != source_profile.to_dict():
        raise CheckpointMigrationError("rollback source profile does not match migration backup")
    source_adapter, source_visibility = _support(runtime).reconstruct(
        substrate_snapshot=backup["substrate"],
        governance_snapshot=source_governance,
    )

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

    rollback_execution_ref = (
        "migration-rollback:"
        + _digest({"id": rollback_id, "generation": result.generation})
    )
    rolled_lifecycle = structural_rollback(
        lifecycle,
        rollback_ref=execution.rollback_ref,
        execution_ref=rollback_execution_ref,
    )
    rollback_record = _finalize_rollback_guard(
        runtime,
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
        raise CheckpointMigrationError(
            "direct downgrade/rollback plans are unsupported; use governed rollback"
        )
    for name in (
        "structural_impact_digest",
        "source_substrate_digest",
        "source_governance_digest",
        "source_interpretation_digest",
        "target_interpretation_digest",
    ):
        value = getattr(plan, name)
        if not value.startswith("sha256:") or len(value) != 71:
            raise CheckpointMigrationError(
                f"migration plan {name} must be sha256:<64 hex>"
            )
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
    if (
        impact.impact_digest != plan.structural_impact_digest
        or lifecycle.impact_digest != plan.structural_impact_digest
    ):
        raise CheckpointMigrationError(
            "migration plan is not bound to the authorized structural impact"
        )
    if lifecycle.authorization_ref != plan.authorization_ref:
        raise CheckpointMigrationError(
            "migration authorization reference does not match lifecycle"
        )
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
        raise CheckpointMigrationError(
            "migration schema transition does not match structural proposal"
        )
    if tuple(proposal.semantic_diff) != tuple(plan.semantic_changes):
        raise CheckpointMigrationError(
            "migration semantic changes do not match structural proposal"
        )
    if (
        lifecycle.state_digest != proposal.state_digest
        or lifecycle.dependency_digest != proposal.dependency_digest
    ):
        raise CheckpointMigrationError(
            "authorized lifecycle no longer matches structural snapshots"
        )


def _validate_profile_transition(
    source: RuntimeProfile,
    target: RuntimeProfile,
    plan: MigrationPlan,
) -> None:
    if source.interpretation_digest != plan.source_interpretation_digest:
        raise CheckpointMigrationError(
            "source runtime interpretation does not match migration plan"
        )
    if target.interpretation_digest != plan.target_interpretation_digest:
        raise CheckpointMigrationError(
            "target runtime interpretation does not match migration plan"
        )
    if source.profile_id != target.profile_id:
        raise CheckpointMigrationError(
            "reference migration cannot change runtime profile identity"
        )
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
            raise CheckpointMigrationError(
                "migration encountered unknown capability maturity"
            )
        if (
            target_rank != source_rank
            and target_binding.evidence_ref == source_binding.evidence_ref
        ):
            raise CheckpointMigrationError(
                f"capability {capability_id} maturity changed without distinct qualification evidence"
            )


def _assert_runtime_matches_plan(
    runtime: RestartSafeRuntime, plan: MigrationPlan
) -> None:
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
        raise CheckpointMigrationError(
            "migration source profile interpretation changed"
        )


def _migration_state(runtime: RestartSafeRuntime) -> MigrationState:
    evidence = runtime.recovery_evidence
    if evidence is None:
        raise CheckpointMigrationError("migration requires recovered checkpoint evidence")
    preview = _support(runtime).preview(
        runtime.adapter,
        profile=runtime.profile,
        visibility_snapshots=runtime.visibility_snapshots,
        generation=evidence.generation,
    )
    adapter_state = preview.governance.get("adapter")
    if not isinstance(adapter_state, dict):
        raise CheckpointMigrationError("runtime governance checkpoint has no adapter state")
    return MigrationState(
        substrate=copy.deepcopy(preview.substrate),
        adapter=copy.deepcopy(adapter_state),
        visibility_snapshots=copy.deepcopy(runtime.visibility_snapshots),
    )


def _validate_migration_state(
    source: MigrationState, target: MigrationState
) -> None:
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
        raise CheckpointMigrationError(
            "migration cannot rewind or advance identifier state"
        )
    if target.substrate.get("episodes") != source.substrate.get("episodes"):
        raise CheckpointMigrationError("migration cannot rewrite raw source episodes")
    if target.substrate.get("write_log") != source.substrate.get("write_log"):
        raise CheckpointMigrationError(
            "migration cannot rewrite substrate mutation history"
        )

    source_facts = {row["uuid"]: row for row in source.substrate.get("facts", ())}
    target_facts = {row["uuid"]: row for row in target.substrate.get("facts", ())}
    if set(source_facts) != set(target_facts):
        raise CheckpointMigrationError(
            "migration cannot add or remove durable fact identities"
        )
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
    tenant_reader = getattr(runtime.adapter, "checkpoint_tenant", None)
    if not callable(tenant_reader):
        raise CheckpointMigrationError(
            "runtime adapter has no checkpoint tenant binding"
        )
    governance = {
        "schema_version": SCHEMA_VERSION,
        "tenant": tenant_reader(),
        "profile": runtime.profile.to_dict(),
        "interpretation_digest": runtime.profile.interpretation_digest,
        "adapter": copy.deepcopy(state.adapter),
        "visibility_snapshots": copy.deepcopy(state.visibility_snapshots),
    }
    try:
        adapter, _visibility = _support(runtime).reconstruct(
            substrate_snapshot=state.substrate,
            governance_snapshot=governance,
        )
    except RuntimeRecoveryError as exc:
        raise CheckpointMigrationError(
            "transformed governance state cannot be reconstructed"
        ) from exc
    return adapter


def _expected_target_manifest(
    runtime: RestartSafeRuntime,
    *,
    target_adapter,
    target_profile: RuntimeProfile,
    target_visibility: dict[str, dict],
) -> dict:
    evidence = runtime.recovery_evidence
    if evidence is None:
        raise CheckpointMigrationError("migration requires recovered checkpoint evidence")
    return _support(runtime).preview(
        target_adapter,
        profile=target_profile,
        visibility_snapshots=target_visibility,
        generation=evidence.generation + 1,
    ).manifest


def _prepare_guard(
    runtime: RestartSafeRuntime,
    *,
    operation_id: str,
    operation_digest: str,
    operation_kind: str,
    expected_target_manifest: dict,
) -> dict:
    evidence = runtime.recovery_evidence
    if evidence is None:
        raise CheckpointMigrationError("migration source evidence is missing")
    support = _support(runtime)
    with support.serialized() as transaction:
        try:
            bundle = transaction.require_current(
                expected_generation=evidence.generation,
                require_store_observation=True,
            )
        except RuntimeCheckpointConflict as exc:
            raise RuntimeCheckpointConflict(
                "migration source generation or manifest advanced before prepare"
            ) from exc

        archive_dir = support.root / "migrations"
        archive_dir.mkdir(parents=True, exist_ok=True)
        token = operation_digest.removeprefix("sha256:")
        backup_rel = f"migrations/{token}.source.json"
        record_rel = f"migrations/{token}.record.json"
        backup = _backup_from_bundle(
            bundle,
            operation_id=operation_id,
            operation_kind=operation_kind,
        )
        backup_envelope = {
            "backup": backup,
            "backup_digest": _digest(backup),
        }
        _atomic_json_write(support.root / backup_rel, backup_envelope)
        intent = {
            "schema_version": MIGRATION_SCHEMA_VERSION,
            "protocol": MIGRATION_PROTOCOL,
            "operation_id": operation_id,
            "operation_kind": operation_kind,
            "operation_digest": operation_digest,
            "source_generation": bundle.generation,
            "source_manifest_digest": _digest(bundle.manifest),
            "target_generation": int(expected_target_manifest["generation"]),
            "target_manifest_digest": _digest(expected_target_manifest),
            "backup_ref": backup_rel,
            "backup_digest": backup_envelope["backup_digest"],
            "record_ref": record_rel,
        }
        _atomic_json_write(
            support.root / "runtime-migration-intent.json",
            intent,
        )
        return intent


def _finalize_guard(
    runtime: RestartSafeRuntime,
    guard: dict,
    *,
    migration_id: str,
    plan_digest: str,
    authorization_ref: str,
    rollback_ref: str,
    source_profile_digest: str,
    target_profile_digest: str,
) -> MigrationExecution:
    support = _support(runtime)
    intent_path = support.root / "runtime-migration-intent.json"
    with support.serialized() as transaction:
        intent = _read_json(intent_path)
        if intent != guard:
            raise CheckpointMigrationError(
                "migration intent changed before finalization"
            )
        try:
            transaction.require_current(
                expected_generation=int(guard["target_generation"]),
                expected_manifest_digest=str(guard["target_manifest_digest"]),
                require_store_observation=True,
            )
        except (RuntimeRecoveryError, RuntimeCheckpointConflict) as exc:
            raise CheckpointMigrationError(
                "migration target is not fully committed"
            ) from exc
        execution = MigrationExecution(
            migration_id=migration_id,
            plan_digest=plan_digest,
            source_generation=int(guard["source_generation"]),
            target_generation=int(guard["target_generation"]),
            source_profile_digest=source_profile_digest,
            target_profile_digest=target_profile_digest,
            source_manifest_digest=str(guard["source_manifest_digest"]),
            target_manifest_digest=str(guard["target_manifest_digest"]),
            authorization_ref=authorization_ref,
            rollback_ref=rollback_ref,
            backup_ref=str(guard["backup_ref"]),
            record_ref=str(guard["record_ref"]),
        )
        _atomic_json_write(support.root / execution.record_ref, execution.to_dict())
        _remove_intent(support.root, intent_path)
        return execution


def _finalize_rollback_guard(
    runtime: RestartSafeRuntime,
    guard: dict,
    *,
    migration_id: str,
    rollback_ref: str,
    execution_ref: str,
    source_generation: int,
    rollback_generation: int,
) -> RollbackExecution:
    support = _support(runtime)
    intent_path = support.root / "runtime-migration-intent.json"
    with support.serialized() as transaction:
        intent = _read_json(intent_path)
        if intent != guard:
            raise CheckpointMigrationError("rollback intent changed before finalization")
        try:
            transaction.require_current(
                expected_generation=int(guard["target_generation"]),
                expected_manifest_digest=str(guard["target_manifest_digest"]),
                require_store_observation=True,
            )
        except (RuntimeRecoveryError, RuntimeCheckpointConflict) as exc:
            raise CheckpointMigrationError(
                "rollback target is not fully committed"
            ) from exc
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
        record_ref = str(guard["record_ref"])
        _atomic_json_write(support.root / record_ref, value)
        _remove_intent(support.root, intent_path)
        return RollbackExecution(
            migration_id=migration_id,
            source_generation=source_generation,
            rollback_generation=rollback_generation,
            rollback_ref=rollback_ref,
            execution_ref=execution_ref,
            record_ref=record_ref,
        )


def _validate_intent(intent: Mapping[str, object]) -> None:
    if (
        intent.get("schema_version") != MIGRATION_SCHEMA_VERSION
        or intent.get("protocol") != MIGRATION_PROTOCOL
    ):
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


def _backup_from_bundle(
    bundle: CommittedCheckpointBundle,
    *,
    operation_id: str,
    operation_kind: str,
) -> dict:
    return {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "operation_id": operation_id,
        "operation_kind": operation_kind,
        "source_manifest": copy.deepcopy(bundle.manifest),
        "substrate": copy.deepcopy(bundle.substrate),
        "governance": copy.deepcopy(bundle.governance),
        "journal_present": bundle.journal_present,
        "journal_records": [copy.deepcopy(row) for row in bundle.journal_records],
    }


def _bundle_from_backup(backup: Mapping[str, object]) -> CommittedCheckpointBundle:
    manifest = backup.get("source_manifest")
    substrate = backup.get("substrate")
    governance = backup.get("governance")
    records = backup.get("journal_records", [])
    if (
        not isinstance(manifest, dict)
        or not isinstance(substrate, dict)
        or not isinstance(governance, dict)
        or not isinstance(records, list)
    ):
        raise CheckpointMigrationError("migration source backup is malformed")
    return CommittedCheckpointBundle(
        manifest=copy.deepcopy(manifest),
        substrate=copy.deepcopy(substrate),
        governance=copy.deepcopy(governance),
        journal_present=bool(backup.get("journal_present")),
        journal_records=tuple(copy.deepcopy(row) for row in records),
    )


def _validated_backup(
    envelope: Mapping[str, object],
    intent: Mapping[str, object] | None,
) -> dict:
    backup = envelope.get("backup")
    digest = envelope.get("backup_digest")
    if not isinstance(backup, dict) or digest != _digest(backup):
        raise CheckpointMigrationError("migration backup digest mismatch")
    if intent is not None and digest != intent.get("backup_digest"):
        raise CheckpointMigrationError(
            "migration intent does not bind the source backup"
        )
    # Construction validates the backup shape without mutating it.
    _bundle_from_backup(backup)
    return backup


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


def _write_recovery_record(
    root: Path, intent: Mapping[str, object], record: dict
) -> None:
    token = str(intent["operation_digest"]).removeprefix("sha256:")
    _atomic_json_write(root / "migrations" / f"{token}.recovery.json", record)


def _remove_intent(root: Path, intent_path: Path) -> None:
    try:
        intent_path.unlink()
    except FileNotFoundError:
        return
    _fsync_directory(root)
