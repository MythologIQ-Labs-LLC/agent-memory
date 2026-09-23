"""Atomic auxiliary-state composition for issue #424.

The #414 reference checkpoint already publishes the governed adapter envelope as
one CAS-protected generation. The adapter's ``extension_state`` is the declared
custody seam for correctness/evidence state owned by later layers. This module
uses that seam to bind explicitly composed auxiliary checkpoint owners to the
same generation without teaching the runtime layer projection, telemetry, or
other higher-layer semantics.

The host supplies factories explicitly. Nothing discovers global stores and
nothing absent from the declared composition gains a durability claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from .checkpoint_transactions import CheckpointTransactionSupport
from .restart_runtime import (
    CapabilityBinding,
    CheckpointableGovernedMemoryAdapter,
    GovernedMemoryAdapter,
    InMemoryTemporalGraph,
    JsonRuntimeStateStore,
    RecoveryEvidence,
    RestartSafeRuntime,
    RuntimeProfile,
    RuntimeRecoveryError,
)

AUXILIARY_CHECKPOINT_SCHEMA_VERSION = "1.0.0"
AUXILIARY_CUSTODY_KEY = "runtime_auxiliary_checkpoint_v1"

AuxiliaryFactory = Callable[[GovernedMemoryAdapter], object]


@dataclass(frozen=True)
class AuxiliaryComponentEvidence:
    component_id: str
    checkpoint_digest: str


class ComposedRestartSafeRuntime(RestartSafeRuntime):
    """Restart-safe runtime with an explicit set of auxiliary state owners.

    Each auxiliary object must expose ``export_checkpoint_state()`` and
    ``restore_checkpoint_state(snapshot)``. The runtime never inspects the
    owner's private state and never infers composition from process globals.
    """

    def __init__(
        self,
        *,
        store: JsonRuntimeStateStore,
        profile: RuntimeProfile,
        adapter: GovernedMemoryAdapter,
        auxiliary_state: Mapping[str, object],
        visibility_snapshots: dict[str, dict] | None = None,
        recovery_evidence: RecoveryEvidence | None = None,
    ) -> None:
        super().__init__(
            store=store,
            profile=profile,
            adapter=adapter,
            visibility_snapshots=visibility_snapshots,
            recovery_evidence=recovery_evidence,
        )
        self._auxiliary_state = dict(auxiliary_state)
        self._validate_component_ids(self._auxiliary_state)

    @classmethod
    def create(
        cls,
        root,
        *,
        tenant: str,
        profile: RuntimeProfile,
        auxiliary_factories: Mapping[str, AuxiliaryFactory],
        verifier_registry=None,
    ) -> "ComposedRestartSafeRuntime":
        store = JsonRuntimeStateStore(root)
        if store.exists():
            raise RuntimeRecoveryError("runtime state already exists; use recover()")
        adapter = CheckpointableGovernedMemoryAdapter(
            InMemoryTemporalGraph(), tenant=tenant, verifier_registry=verifier_registry
        )
        auxiliary = cls._instantiate_auxiliary(adapter, auxiliary_factories)
        runtime = cls(
            store=store,
            profile=profile,
            adapter=adapter,
            auxiliary_state=auxiliary,
        )
        runtime.recovery_evidence = runtime.checkpoint()
        return runtime

    @classmethod
    def recover(
        cls,
        root,
        *,
        profile: RuntimeProfile,
        auxiliary_factories: Mapping[str, AuxiliaryFactory],
        available_bindings: Iterable[CapabilityBinding] | None = None,
        verifier_registry=None,
    ) -> "ComposedRestartSafeRuntime":
        available = tuple(
            available_bindings if available_bindings is not None else profile.bindings
        )
        store = JsonRuntimeStateStore(root)
        adapter, visibility, evidence = store.recover(
            expected_profile=profile,
            available_bindings=available,
            verifier_registry=verifier_registry,
        )
        auxiliary = cls._restore_auxiliary(adapter, auxiliary_factories)
        return cls(
            store=store,
            profile=profile,
            adapter=adapter,
            auxiliary_state=auxiliary,
            visibility_snapshots=visibility,
            recovery_evidence=evidence,
        )

    @property
    def auxiliary_components(self) -> tuple[str, ...]:
        return tuple(sorted(self._auxiliary_state))

    def auxiliary(self, component_id: str):
        try:
            return self._auxiliary_state[component_id]
        except KeyError as exc:
            raise KeyError(f"auxiliary component is not composed: {component_id}") from exc

    def checkpoint(self) -> RecoveryEvidence:
        self._stage_auxiliary_state()
        return super().checkpoint()

    def auxiliary_evidence(self) -> tuple[AuxiliaryComponentEvidence, ...]:
        envelope = self.adapter.extension_state.get(AUXILIARY_CUSTODY_KEY)
        if not isinstance(envelope, Mapping):
            return ()
        raw = envelope.get("components", {})
        if not isinstance(raw, Mapping):
            return ()
        evidence: list[AuxiliaryComponentEvidence] = []
        for component_id in sorted(raw):
            entry = raw[component_id]
            if isinstance(entry, Mapping):
                evidence.append(
                    AuxiliaryComponentEvidence(
                        component_id=component_id,
                        checkpoint_digest=str(entry.get("checkpoint_digest", "")),
                    )
                )
        return tuple(evidence)

    def _stage_auxiliary_state(self) -> None:
        components: dict[str, dict] = {}
        for component_id in sorted(self._auxiliary_state):
            owner = self._auxiliary_state[component_id]
            exporter = getattr(owner, "export_checkpoint_state", None)
            if not callable(exporter):
                raise RuntimeRecoveryError(
                    f"auxiliary component does not declare checkpoint export: {component_id}"
                )
            try:
                snapshot = exporter()
            except (TypeError, ValueError) as exc:
                raise RuntimeRecoveryError(
                    f"auxiliary checkpoint export failed: {component_id}"
                ) from exc
            if not isinstance(snapshot, dict):
                raise RuntimeRecoveryError(
                    f"auxiliary checkpoint export must be a mapping: {component_id}"
                )
            components[component_id] = {
                "checkpoint_digest": CheckpointTransactionSupport.digest(snapshot),
                "snapshot": snapshot,
            }
        self.adapter.extension_state[AUXILIARY_CUSTODY_KEY] = {
            "schema_version": AUXILIARY_CHECKPOINT_SCHEMA_VERSION,
            "components": components,
        }

    @classmethod
    def _restore_auxiliary(
        cls,
        adapter: GovernedMemoryAdapter,
        factories: Mapping[str, AuxiliaryFactory],
    ) -> dict[str, object]:
        cls._validate_component_ids(factories)
        envelope = adapter.extension_state.get(AUXILIARY_CUSTODY_KEY)
        if envelope is None:
            if factories:
                raise RuntimeRecoveryError(
                    "runtime checkpoint predates declared auxiliary composition; explicit migration is required"
                )
            return {}
        if not isinstance(envelope, Mapping):
            raise RuntimeRecoveryError("auxiliary checkpoint envelope is malformed")
        if envelope.get("schema_version") != AUXILIARY_CHECKPOINT_SCHEMA_VERSION:
            raise RuntimeRecoveryError("unsupported auxiliary checkpoint schema")
        raw_components = envelope.get("components")
        if not isinstance(raw_components, Mapping):
            raise RuntimeRecoveryError("auxiliary checkpoint components are malformed")

        persisted_ids = set(raw_components)
        declared_ids = set(factories)
        if persisted_ids != declared_ids:
            missing = sorted(persisted_ids - declared_ids)
            added = sorted(declared_ids - persisted_ids)
            raise RuntimeRecoveryError(
                "auxiliary runtime composition changed; explicit migration is required "
                f"(missing factories={missing}, new factories={added})"
            )

        owners = cls._instantiate_auxiliary(adapter, factories)
        for component_id in sorted(persisted_ids):
            entry = raw_components[component_id]
            if not isinstance(entry, Mapping):
                raise RuntimeRecoveryError(
                    f"auxiliary checkpoint entry is malformed: {component_id}"
                )
            snapshot = entry.get("snapshot")
            digest = entry.get("checkpoint_digest")
            if not isinstance(snapshot, dict) or not isinstance(digest, str):
                raise RuntimeRecoveryError(
                    f"auxiliary checkpoint entry is incomplete: {component_id}"
                )
            if CheckpointTransactionSupport.digest(snapshot) != digest:
                raise RuntimeRecoveryError(
                    f"auxiliary checkpoint digest mismatch: {component_id}"
                )
            restorer = getattr(owners[component_id], "restore_checkpoint_state", None)
            if not callable(restorer):
                raise RuntimeRecoveryError(
                    f"auxiliary component does not declare checkpoint restore: {component_id}"
                )
            try:
                restorer(snapshot)
            except (TypeError, ValueError) as exc:
                raise RuntimeRecoveryError(
                    f"auxiliary checkpoint cannot be reconstructed: {component_id}"
                ) from exc
        return owners

    @staticmethod
    def _instantiate_auxiliary(
        adapter: GovernedMemoryAdapter,
        factories: Mapping[str, AuxiliaryFactory],
    ) -> dict[str, object]:
        ComposedRestartSafeRuntime._validate_component_ids(factories)
        owners: dict[str, object] = {}
        for component_id in sorted(factories):
            factory = factories[component_id]
            if not callable(factory):
                raise RuntimeRecoveryError(
                    f"auxiliary component factory is not callable: {component_id}"
                )
            try:
                owner = factory(adapter)
            except Exception as exc:
                raise RuntimeRecoveryError(
                    f"auxiliary component factory failed: {component_id}"
                ) from exc
            exporter = getattr(owner, "export_checkpoint_state", None)
            restorer = getattr(owner, "restore_checkpoint_state", None)
            if not callable(exporter) or not callable(restorer):
                raise RuntimeRecoveryError(
                    f"auxiliary component lacks owner checkpoint contract: {component_id}"
                )
            owners[component_id] = owner
        return owners

    @staticmethod
    def _validate_component_ids(values: Mapping[str, object]) -> None:
        for component_id in values:
            if not isinstance(component_id, str) or not component_id:
                raise RuntimeRecoveryError(
                    "auxiliary component ids must be stable non-empty strings"
                )
            if component_id == AUXILIARY_CUSTODY_KEY:
                raise RuntimeRecoveryError("auxiliary component id collides with custody key")
