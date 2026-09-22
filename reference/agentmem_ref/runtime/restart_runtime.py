"""Bounded restart-safe Agent Memory runtime for issue #282 / #363.

This module is intentionally conservative. It persists the reference substrate
and governance envelope as separate payloads, then binds both to a manifest by
SHA-256 digest. Recovery refuses missing, corrupt, torn, or interpretation-
ambiguous state.

Issue #363 tightens the ownership boundary without changing the base durability
profile: the substrate exports/restores its own durable state, rejected-value
history exports/restores itself, and the governed adapter durability
specialization exports/restores governance state. This module orchestrates those
contracts instead of scraping implementation-private dictionaries.

The file-backed store remains the first executable durability profile, not
canonical storage doctrine. A production implementation may use a database,
WAL, object store, or another transactional substrate while preserving the same
recovery obligations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Mapping

from .adapter import Clock, GovernedMemoryAdapter
from ..core.readmission import RejectedValueRegistry
from ..state.substrate import (
    CheckpointableTemporalGraphPort,
    InMemoryTemporalGraph,
)


SCHEMA_VERSION = "1.0.0"
DURABILITY_PROFILE = "reference_file_checkpoint_v1"
ADAPTER_CHECKPOINT_OWNER = "governed_memory_adapter"


class RuntimeRecoveryError(RuntimeError):
    """Durable runtime state cannot be reconstructed safely."""


@dataclass(frozen=True)
class CapabilityBinding:
    """Exact component interpretation required to recover a runtime safely."""

    component_id: str
    component_version: str
    capability_id: str
    capability_version: str
    maturity: str
    evidence_ref: str
    source_rights_posture: str = "runtime_allowed"

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not value:
                raise ValueError(f"capability binding requires {name}")
        if self.source_rights_posture != "runtime_allowed":
            raise ValueError("restart runtime requires runtime-allowed source rights")

    @property
    def key(self) -> str:
        return f"{self.capability_id}@{self.capability_version}"


@dataclass(frozen=True)
class RuntimeProfile:
    runtime_version: str
    profile_id: str
    profile_version: str
    bindings: tuple[CapabilityBinding, ...]

    def __post_init__(self) -> None:
        if not self.runtime_version or not self.profile_id or not self.profile_version:
            raise ValueError("runtime/profile identity is required")
        keys = [binding.key for binding in self.bindings]
        if len(keys) != len(set(keys)):
            raise ValueError("runtime profile capability bindings must be unique")

    def to_dict(self) -> dict:
        return {
            "runtime_version": self.runtime_version,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "bindings": [asdict(binding) for binding in self.bindings],
        }

    @property
    def interpretation_digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class RecoveryEvidence:
    generation: int
    durability_profile: str
    substrate_digest: str
    governance_digest: str
    interpretation_digest: str
    recovered_visibility_operations: tuple[str, ...]
    recovery_posture: str = "recovered_exact_interpretation"

    def to_dict(self) -> dict:
        return asdict(self)


class CheckpointableGovernedMemoryAdapter(GovernedMemoryAdapter):
    """Reference governed adapter with a declared durability state-provider seam.

    ``GovernedMemoryAdapter`` remains usable without claiming persistence. This
    specialization is what the restart-safe profile instantiates. Its methods
    own access to adapter-private state; the checkpoint orchestrator never
    reaches into those fields directly.

    Keeping this as a specialization also avoids silently declaring every
    external adapter implementation restart-safe merely because it satisfies the
    ordinary governed runtime contract.
    """

    checkpoint_owner = ADAPTER_CHECKPOINT_OWNER

    def checkpoint_substrate(self):
        """Return the substrate collaborator for its own checkpoint contract."""
        return self._substrate

    def checkpoint_tenant(self) -> str:
        return self._tenant

    def export_checkpoint_state(self) -> dict:
        """Export adapter-owned governance state in the existing v1 wire shape."""
        selector_mode = getattr(self._selector, "mode", "unknown")
        if selector_mode != "deterministic":
            raise ValueError(
                "reference durability profile currently supports only deterministic selector recovery"
            )
        identifier_checkpoint = getattr(self._substrate, "identifier_checkpoint", None)
        if not callable(identifier_checkpoint):
            raise ValueError("substrate does not declare identifier checkpoint capability")
        return {
            "checkpoint_owner": self.checkpoint_owner,
            "selector_mode": selector_mode,
            "clock_tick": self._clock._t,
            # Legacy v1 location retained for compatibility. The value is read
            # through the substrate-owned contract rather than from `_ids._n`.
            "id_counter": int(identifier_checkpoint()),
            "state_version": dict(sorted(self._state_version.items())),
            "disputed": sorted(self._disputed),
            "tombstones": self._tombstones,
            "fact_scope": self._fact_scope,
            "fact_memory": dict(sorted(self._fact_memory.items())),
            "shared_domain_members": {
                key: sorted(value) for key, value in sorted(self._shared_domain_members.items())
            },
            "current_fact_by_memory": dict(sorted(self._current_fact_by_memory.items())),
            "rejected_values": self._rejected_values.export_checkpoint_rows(),
            "rejected_values_descriptor": self._rejected_values.checkpoint_descriptor(),
            "containment_violations": list(self.containment_violations),
            "events": list(self.events),
            "extension_state": {
                key: self.extension_state[key] for key in sorted(self.extension_state)
            },
        }

    def restore_checkpoint_state(self, raw: Mapping[str, object]) -> None:
        """Restore adapter-owned governance state fail-closed.

        The input accepts pre-#363 v1 snapshots that lack owner/descriptor
        metadata, but does not infer missing correctness state. Identifier
        progress is restored through the substrate-owned seam and is never
        allowed to rewind.
        """
        owner = raw.get("checkpoint_owner")
        if owner not in (None, self.checkpoint_owner):
            raise ValueError("governance checkpoint owner mismatch")
        if raw.get("selector_mode") != "deterministic":
            raise ValueError("selector recovery is unsupported or ambiguous")

        def mapping(name: str) -> Mapping:
            value = raw.get(name, {})
            if not isinstance(value, Mapping):
                raise ValueError(f"governance checkpoint {name} is not a mapping")
            return value

        try:
            self._clock = Clock(start=int(raw.get("clock_tick", 0)))

            restore_identifier = getattr(self._substrate, "restore_identifier_checkpoint", None)
            current_identifier = getattr(self._substrate, "identifier_checkpoint", None)
            if not callable(restore_identifier) or not callable(current_identifier):
                raise ValueError("substrate does not declare identifier checkpoint capability")
            legacy_identifier = int(raw.get("id_counter", 0))
            restore_identifier(max(int(current_identifier()), legacy_identifier))

            self._state_version = {
                str(key): int(value) for key, value in mapping("state_version").items()
            }
            disputed = raw.get("disputed", ())
            if not isinstance(disputed, (list, tuple, set)):
                raise ValueError("governance checkpoint disputed state is malformed")
            self._disputed = {str(value) for value in disputed}
            self._tombstones = {str(key): dict(value) for key, value in mapping("tombstones").items()}

            fact_scope = {}
            for key, value in mapping("fact_scope").items():
                if not isinstance(value, Mapping):
                    raise ValueError("governance fact scope is malformed")
                restored = dict(value)
                restored["domain_refs"] = tuple(restored.get("domain_refs", ()))
                restored["required_domain_refs"] = tuple(restored.get("required_domain_refs", ()))
                fact_scope[str(key)] = restored
            self._fact_scope = fact_scope

            self._fact_memory = {
                str(key): str(value) for key, value in mapping("fact_memory").items()
            }
            self._shared_domain_members = {
                str(key): {str(member) for member in value}
                for key, value in mapping("shared_domain_members").items()
            }
            self._current_fact_by_memory = {
                str(key): str(value)
                for key, value in mapping("current_fact_by_memory").items()
            }

            rejected_rows = raw.get("rejected_values", ())
            if not isinstance(rejected_rows, (list, tuple)):
                raise ValueError("rejected-value checkpoint rows are malformed")
            self._rejected_values = RejectedValueRegistry.restore_checkpoint_rows(rejected_rows)

            containment = raw.get("containment_violations", ())
            events = raw.get("events", ())
            if not isinstance(containment, (list, tuple)) or not isinstance(events, (list, tuple)):
                raise ValueError("governance audit state is malformed")
            self.containment_violations = [str(value) for value in containment]
            self.events = [dict(value) for value in events]

            extension_state = raw.get("extension_state", {})
            if not isinstance(extension_state, Mapping):
                raise ValueError("extension state is not a mapping")
            self.extension_state = {
                str(key): dict(value) for key, value in extension_state.items()
            }
        except (TypeError, ValueError) as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError("governance adapter state cannot be reconstructed") from exc


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _read_json(path: Path) -> dict:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise RuntimeRecoveryError(f"required runtime state missing: {path.name}") from exc
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeRecoveryError(f"runtime state is corrupt: {path.name}") from exc
    if not isinstance(value, dict):
        raise RuntimeRecoveryError(f"runtime state must be a JSON object: {path.name}")
    return value


def _atomic_json_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    payload = _canonical_bytes(value) + b"\n"
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _snapshot_substrate(substrate) -> dict:
    """Snapshot only a provider that explicitly declares checkpoint capability."""
    if not isinstance(substrate, CheckpointableTemporalGraphPort):
        raise RuntimeRecoveryError("substrate does not declare checkpoint capability")
    try:
        snapshot = substrate.export_checkpoint_state()
    except (TypeError, ValueError) as exc:
        raise RuntimeRecoveryError("substrate checkpoint export failed") from exc
    if not isinstance(snapshot, dict):
        raise RuntimeRecoveryError("substrate checkpoint export must be a mapping")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeRecoveryError("unsupported substrate state schema")
    return snapshot


def _restore_substrate(snapshot: dict) -> InMemoryTemporalGraph:
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeRecoveryError("unsupported substrate state schema")
    substrate = InMemoryTemporalGraph()
    try:
        substrate.restore_checkpoint_state(snapshot)
    except (TypeError, ValueError) as exc:
        raise RuntimeRecoveryError("substrate state cannot be reconstructed") from exc
    return substrate


def _snapshot_rejections(registry: RejectedValueRegistry) -> list[dict]:
    """Compatibility helper delegated to the registry owner."""
    return registry.export_checkpoint_rows()


def _restore_rejections(rows: Iterable[Mapping[str, object]]) -> RejectedValueRegistry:
    """Compatibility helper delegated to the registry owner."""
    try:
        return RejectedValueRegistry.restore_checkpoint_rows(rows)
    except (TypeError, ValueError) as exc:
        raise RuntimeRecoveryError("rejected-value state cannot be reconstructed") from exc


def _snapshot_governance(
    adapter: GovernedMemoryAdapter,
    *,
    profile: RuntimeProfile,
    visibility_snapshots: dict[str, dict],
) -> dict:
    """Compose the runtime envelope from an adapter-owned checkpoint export."""
    exporter = getattr(adapter, "export_checkpoint_state", None)
    tenant_reader = getattr(adapter, "checkpoint_tenant", None)
    if not callable(exporter) or not callable(tenant_reader):
        raise RuntimeRecoveryError("governed adapter does not declare checkpoint capability")
    try:
        raw = exporter()
        tenant = tenant_reader()
    except (TypeError, ValueError) as exc:
        raise RuntimeRecoveryError("governance checkpoint export failed") from exc
    if not isinstance(raw, dict):
        raise RuntimeRecoveryError("governance checkpoint export must be a mapping")
    if not isinstance(tenant, str) or not tenant:
        raise RuntimeRecoveryError("governance state has no tenant identity")
    return {
        "schema_version": SCHEMA_VERSION,
        "tenant": tenant,
        "profile": profile.to_dict(),
        "interpretation_digest": profile.interpretation_digest,
        "adapter": raw,
        "visibility_snapshots": visibility_snapshots,
    }


def _restore_adapter(
    substrate: InMemoryTemporalGraph,
    snapshot: dict,
    verifier_registry=None,
) -> tuple[GovernedMemoryAdapter, dict[str, dict]]:
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeRecoveryError("unsupported governance state schema")
    tenant = snapshot.get("tenant")
    if not isinstance(tenant, str) or not tenant:
        raise RuntimeRecoveryError("governance state has no tenant identity")
    raw = snapshot.get("adapter")
    if not isinstance(raw, dict):
        raise RuntimeRecoveryError("governance adapter state is missing")

    adapter = CheckpointableGovernedMemoryAdapter(
        substrate, tenant=tenant, verifier_registry=verifier_registry
    )
    try:
        adapter.restore_checkpoint_state(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeRecoveryError("governance adapter state cannot be reconstructed") from exc

    visibility = snapshot.get("visibility_snapshots", {})
    if not isinstance(visibility, dict):
        raise RuntimeRecoveryError("visibility snapshot state is malformed")
    return adapter, visibility


def _profile_from_dict(raw: dict) -> RuntimeProfile:
    try:
        return RuntimeProfile(
            runtime_version=raw["runtime_version"],
            profile_id=raw["profile_id"],
            profile_version=raw["profile_version"],
            bindings=tuple(CapabilityBinding(**binding) for binding in raw.get("bindings", ())),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeRecoveryError("persisted runtime profile is malformed") from exc


def _assert_profile_compatible(
    persisted: RuntimeProfile,
    expected: RuntimeProfile,
    available_bindings: Iterable[CapabilityBinding],
) -> None:
    if persisted.to_dict() != expected.to_dict():
        raise RuntimeRecoveryError(
            "runtime profile/component interpretation changed; explicit compatibility evidence or migration is required"
        )
    available = {binding.key: binding for binding in available_bindings}
    for required in persisted.bindings:
        candidate = available.get(required.key)
        if candidate is None:
            raise RuntimeRecoveryError(f"required capability unavailable after restart: {required.key}")
        if candidate != required:
            raise RuntimeRecoveryError(
                f"required capability interpretation changed after restart: {required.key}"
            )


class JsonRuntimeStateStore:
    """Atomic-manifest checkpoint store with separate substrate/governance payloads."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.substrate_path = self.root / "substrate.json"
        self.governance_path = self.root / "governance.json"
        self.manifest_path = self.root / "runtime-manifest.json"

    def exists(self) -> bool:
        return self.manifest_path.exists()

    def checkpoint(
        self,
        adapter: GovernedMemoryAdapter,
        *,
        profile: RuntimeProfile,
        visibility_snapshots: dict[str, dict],
    ) -> RecoveryEvidence:
        previous_generation = 0
        if self.manifest_path.exists():
            previous = _read_json(self.manifest_path)
            previous_generation = int(previous.get("generation", 0))

        substrate_reader = getattr(adapter, "checkpoint_substrate", None)
        if not callable(substrate_reader):
            raise RuntimeRecoveryError("governed adapter does not declare checkpoint capability")
        substrate = _snapshot_substrate(substrate_reader())
        governance = _snapshot_governance(
            adapter,
            profile=profile,
            visibility_snapshots=visibility_snapshots,
        )
        substrate_digest = _digest(substrate)
        governance_digest = _digest(governance)
        generation = previous_generation + 1

        _atomic_json_write(self.substrate_path, substrate)
        _atomic_json_write(self.governance_path, governance)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "durability_profile": DURABILITY_PROFILE,
            "generation": generation,
            "substrate_digest": substrate_digest,
            "governance_digest": governance_digest,
            "interpretation_digest": profile.interpretation_digest,
        }
        # The manifest is replaced last. A crash before this point leaves a
        # digest mismatch that recovery treats as a torn checkpoint.
        _atomic_json_write(self.manifest_path, manifest)
        return RecoveryEvidence(
            generation=generation,
            durability_profile=DURABILITY_PROFILE,
            substrate_digest=substrate_digest,
            governance_digest=governance_digest,
            interpretation_digest=profile.interpretation_digest,
            recovered_visibility_operations=tuple(sorted(visibility_snapshots)),
        )

    def recover(
        self,
        *,
        expected_profile: RuntimeProfile,
        available_bindings: Iterable[CapabilityBinding],
        verifier_registry=None,
    ) -> tuple[GovernedMemoryAdapter, dict[str, dict], RecoveryEvidence]:
        manifest = _read_json(self.manifest_path)
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeRecoveryError("unsupported runtime manifest schema")
        if manifest.get("durability_profile") != DURABILITY_PROFILE:
            raise RuntimeRecoveryError("runtime durability profile changed")

        substrate_raw = _read_json(self.substrate_path)
        governance_raw = _read_json(self.governance_path)
        substrate_digest = _digest(substrate_raw)
        governance_digest = _digest(governance_raw)
        if substrate_digest != manifest.get("substrate_digest"):
            raise RuntimeRecoveryError("substrate checkpoint digest mismatch; recovery fails closed")
        if governance_digest != manifest.get("governance_digest"):
            raise RuntimeRecoveryError("governance checkpoint digest mismatch; recovery fails closed")

        persisted_profile_raw = governance_raw.get("profile")
        if not isinstance(persisted_profile_raw, dict):
            raise RuntimeRecoveryError("persisted runtime profile is missing")
        persisted_profile = _profile_from_dict(persisted_profile_raw)
        if persisted_profile.interpretation_digest != manifest.get("interpretation_digest"):
            raise RuntimeRecoveryError("runtime interpretation digest mismatch")
        _assert_profile_compatible(persisted_profile, expected_profile, available_bindings)

        substrate = _restore_substrate(substrate_raw)
        adapter, visibility = _restore_adapter(
            substrate, governance_raw, verifier_registry=verifier_registry
        )
        evidence = RecoveryEvidence(
            generation=int(manifest.get("generation", 0)),
            durability_profile=DURABILITY_PROFILE,
            substrate_digest=substrate_digest,
            governance_digest=governance_digest,
            interpretation_digest=persisted_profile.interpretation_digest,
            recovered_visibility_operations=tuple(sorted(visibility)),
        )
        return adapter, visibility, evidence


class RestartSafeRuntime:
    """Smallest durable runtime wrapper around the governed reference adapter."""

    def __init__(
        self,
        *,
        store: JsonRuntimeStateStore,
        profile: RuntimeProfile,
        adapter: GovernedMemoryAdapter,
        visibility_snapshots: dict[str, dict] | None = None,
        recovery_evidence: RecoveryEvidence | None = None,
    ) -> None:
        self.store = store
        self.profile = profile
        self.adapter = adapter
        self.visibility_snapshots = dict(visibility_snapshots or {})
        self.recovery_evidence = recovery_evidence

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        tenant: str,
        profile: RuntimeProfile,
        verifier_registry=None,
    ) -> "RestartSafeRuntime":
        """ADR-037 step 4b-2, DoD 20: the host configures verifier trust here."""
        store = JsonRuntimeStateStore(root)
        if store.exists():
            raise RuntimeRecoveryError("runtime state already exists; use recover()")
        adapter = CheckpointableGovernedMemoryAdapter(
            InMemoryTemporalGraph(), tenant=tenant, verifier_registry=verifier_registry
        )
        runtime = cls(store=store, profile=profile, adapter=adapter)
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
    ) -> "RestartSafeRuntime":
        """ADR-037 step 4b-2, DoD 20: a recovered runtime carries host-configured
        verifier trust too, so restart is not a way to lose the channel."""
        available = tuple(
            available_bindings if available_bindings is not None else profile.bindings
        )
        store = JsonRuntimeStateStore(root)
        adapter, visibility, evidence = store.recover(
            expected_profile=profile,
            available_bindings=available,
            verifier_registry=verifier_registry,
        )
        return cls(
            store=store,
            profile=profile,
            adapter=adapter,
            visibility_snapshots=visibility,
            recovery_evidence=evidence,
        )

    def checkpoint(self) -> RecoveryEvidence:
        evidence = self.store.checkpoint(
            self.adapter,
            profile=self.profile,
            visibility_snapshots=self.visibility_snapshots,
        )
        self.recovery_evidence = evidence
        return evidence

    def commit_proposal(
        self,
        proposal,
        fact_text: str,
        episode=None,
        *,
        evidence=None,
        attestation=None,
    ):
        """Forward the governed commit, including the qualified-evidence channel.

        ADR-037 step 4b-2, DoD 20: a wrapper that dropped `evidence` would leave
        the capability present underneath and unreachable from here -- a path
        that neither forwards nor parks honestly. It forwards; it does **not**
        become an alternate trust authority. Verifier trust stays with the
        adapter's evaluator-owned registry, and there is deliberately no
        `verifiers=` parameter here either.
        """
        result = self.adapter.commit_proposal(
            proposal, fact_text, episode, evidence=evidence, attestation=attestation
        )
        self.checkpoint()
        return result

    def governed_delete(
        self,
        proposal,
        fact_uuid: str,
        derived_refs: tuple[str, ...] = (),
        external_verification=None,
        evidence=None,
    ):
        """Forwards the deletion channels too (ADR-037 step 4b-2, DoD 20)."""
        result = self.adapter.governed_delete(
            proposal, fact_uuid, derived_refs, external_verification, evidence
        )
        self.checkpoint()
        return result

    def persist_visibility_snapshot(
        self, operation_id: str, snapshot: dict
    ) -> RecoveryEvidence:
        if not operation_id:
            raise ValueError("visibility operation id is required")
        if not isinstance(snapshot, dict):
            raise ValueError("visibility snapshot must be a mapping")
        self.visibility_snapshots[operation_id] = snapshot
        return self.checkpoint()
