"""Public transaction-support seam for governed checkpoint consumers.

This module is intentionally narrow. It exposes semantic operations needed by
higher layers that must coordinate with the reference checkpoint store without
learning the store's private lock, journal, observation, serialization, or
component-reconstruction implementation details.

It does not own migration policy, structural authority, or transformation
semantics. Those remain in the memory layer.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Mapping

from . import restart_runtime as _rr

# Recovery must remain able to restore the pre-transaction bundle when a test or
# injected failure replaces the normal publication writer. Capture the proven
# primitive at module import rather than consulting a possibly fault-injected
# publication symbol during recovery.
_RECOVERY_ATOMIC_JSON_WRITE = _rr._atomic_json_write
_RECOVERY_FSYNC_DIRECTORY = _rr._fsync_directory


@dataclass(frozen=True)
class CheckpointPreview:
    """A complete not-yet-published checkpoint generation."""

    manifest: dict
    substrate: dict
    governance: dict


@dataclass(frozen=True)
class CommittedCheckpointBundle:
    """One validated committed checkpoint plus its local journal witness."""

    manifest: dict
    substrate: dict
    governance: dict
    journal_present: bool
    journal_records: tuple[dict, ...]

    @property
    def generation(self) -> int:
        return int(self.manifest["generation"])


class CheckpointTransactionSession:
    """Operations valid only while the checkpoint store lock is held."""

    def __init__(self, support: "CheckpointTransactionSupport") -> None:
        self._support = support

    @property
    def root(self):
        return self._support.root

    def read_manifest(self) -> dict | None:
        path = self._support._store.manifest_path
        return _rr._read_json(path) if path.exists() else None

    def current_bundle(self) -> CommittedCheckpointBundle:
        return self._support._bundle_unlocked()

    def try_current_bundle(self) -> CommittedCheckpointBundle | None:
        try:
            return self.current_bundle()
        except _rr.RuntimeRecoveryError:
            return None

    def require_current(
        self,
        *,
        expected_generation: int | None = None,
        expected_manifest_digest: str | None = None,
        require_store_observation: bool = False,
    ) -> CommittedCheckpointBundle:
        bundle = self.current_bundle()
        current_digest = _rr._digest(bundle.manifest)
        if expected_generation is not None and bundle.generation != expected_generation:
            raise _rr.RuntimeCheckpointConflict(
                "checkpoint generation conflict: "
                f"expected {expected_generation}, current {bundle.generation}"
            )
        if (
            expected_manifest_digest is not None
            and current_digest != expected_manifest_digest
        ):
            raise _rr.RuntimeCheckpointConflict(
                "checkpoint manifest changed without the expected generation view"
            )
        if require_store_observation:
            store = self._support._store
            if store._observed_generation != bundle.generation:
                raise _rr.RuntimeCheckpointConflict(
                    "checkpoint store has not observed the current generation"
                )
            if store._observed_manifest_digest != current_digest:
                raise _rr.RuntimeCheckpointConflict(
                    "checkpoint store observed manifest no longer matches current commit"
                )
        return bundle

    def is_fully_committed(self, manifest: Mapping[str, object]) -> bool:
        bundle = self.try_current_bundle()
        return (
            bundle is not None
            and _rr._digest(bundle.manifest) == _rr._digest(dict(manifest))
        )

    def restore_bundle(self, bundle: CommittedCheckpointBundle) -> None:
        self._support._restore_bundle_unlocked(bundle)


class CheckpointTransactionSupport:
    """Narrow public coordination surface around ``JsonRuntimeStateStore``.

    Callers may inspect or restore complete validated bundles and may reserve a
    serialized inspection/recovery window. They cannot mint authority, bypass
    generation CAS, or publish a new canonical generation except through the
    store's normal ``checkpoint`` method.
    """

    def __init__(self, store: _rr.JsonRuntimeStateStore) -> None:
        if not isinstance(store, _rr.JsonRuntimeStateStore):
            raise TypeError("checkpoint transaction support requires JsonRuntimeStateStore")
        self._store = store

    @property
    def root(self):
        return self._store.root

    @staticmethod
    def digest(value: object) -> str:
        return _rr._digest(value)

    def preview(
        self,
        adapter,
        *,
        profile: _rr.RuntimeProfile,
        visibility_snapshots: dict[str, dict],
        generation: int,
    ) -> CheckpointPreview:
        """Render the exact payloads/manifest a later checkpoint would publish."""
        if generation < 1:
            raise _rr.RuntimeRecoveryError("checkpoint preview generation must be positive")
        substrate_reader = getattr(adapter, "checkpoint_substrate", None)
        if not callable(substrate_reader):
            raise _rr.RuntimeRecoveryError(
                "governed adapter does not declare checkpoint capability"
            )
        substrate = _rr._snapshot_substrate(substrate_reader())
        governance = _rr._snapshot_governance(
            adapter,
            profile=profile,
            visibility_snapshots=visibility_snapshots,
        )
        manifest = {
            "schema_version": _rr.SCHEMA_VERSION,
            "durability_profile": _rr.DURABILITY_PROFILE,
            "transaction_protocol": _rr.TRANSACTION_PROTOCOL,
            "generation": generation,
            "substrate_digest": _rr._digest(substrate),
            "governance_digest": _rr._digest(governance),
            "interpretation_digest": profile.interpretation_digest,
        }
        return CheckpointPreview(
            manifest=manifest,
            substrate=substrate,
            governance=governance,
        )

    def reconstruct(
        self,
        *,
        substrate_snapshot: dict,
        governance_snapshot: dict,
        verifier_registry=None,
    ):
        """Reconstruct checkpoint-capable state through owner-declared contracts."""
        substrate = _rr._restore_substrate(substrate_snapshot)
        return _rr._restore_adapter(
            substrate,
            governance_snapshot,
            verifier_registry=verifier_registry,
        )

    def _bundle_unlocked(self) -> CommittedCheckpointBundle:
        manifest, _latest = self._store._current_manifest_and_journal()
        if manifest is None:
            raise _rr.RuntimeRecoveryError(
                "required runtime state missing: runtime-manifest.json"
            )
        substrate = _rr._read_json(self._store.substrate_path)
        governance = _rr._read_json(self._store.governance_path)
        if _rr._digest(substrate) != manifest.get("substrate_digest"):
            raise _rr.RuntimeRecoveryError(
                "substrate checkpoint digest mismatch; recovery fails closed"
            )
        if _rr._digest(governance) != manifest.get("governance_digest"):
            raise _rr.RuntimeRecoveryError(
                "governance checkpoint digest mismatch; recovery fails closed"
            )
        records = _rr._read_generation_journal(self._store.journal_path)
        if records:
            validated_latest = _rr._validate_generation_journal(records)
            if validated_latest is None:
                raise _rr.RuntimeRecoveryError("checkpoint generation journal is empty")
            _rr._assert_manifest_matches_journal(manifest, validated_latest)
        elif manifest.get("transaction_protocol") == _rr.TRANSACTION_PROTOCOL:
            raise _rr.RuntimeRecoveryError(
                "transactional runtime manifest is missing its generation journal"
            )
        return CommittedCheckpointBundle(
            manifest=dict(manifest),
            substrate=substrate,
            governance=governance,
            journal_present=self._store.journal_path.exists(),
            journal_records=tuple(dict(record) for record in records),
        )

    @contextmanager
    def serialized(self) -> Iterator[CheckpointTransactionSession]:
        """Hold the checkpoint lock even when the current bundle may be torn."""
        with _rr._exclusive_checkpoint_lock(self._store.lock_path):
            yield CheckpointTransactionSession(self)

    @contextmanager
    def serialized_current(
        self,
        *,
        expected_generation: int | None = None,
        expected_manifest_digest: str | None = None,
        require_store_observation: bool = False,
    ) -> Iterator[CommittedCheckpointBundle]:
        """Yield one validated current bundle while holding the checkpoint lock."""
        with self.serialized() as session:
            yield session.require_current(
                expected_generation=expected_generation,
                expected_manifest_digest=expected_manifest_digest,
                require_store_observation=require_store_observation,
            )

    def current_bundle(self) -> CommittedCheckpointBundle:
        with self.serialized() as session:
            return session.current_bundle()

    def try_current_bundle(self) -> CommittedCheckpointBundle | None:
        with self.serialized() as session:
            return session.try_current_bundle()

    def is_fully_committed(self, manifest: Mapping[str, object]) -> bool:
        with self.serialized() as session:
            return session.is_fully_committed(manifest)

    def restore_bundle(self, bundle: CommittedCheckpointBundle) -> None:
        with self.serialized() as session:
            session.restore_bundle(bundle)

    def _restore_bundle_unlocked(self, bundle: CommittedCheckpointBundle) -> None:
        """Internal implementation for exact crash-recovery restoration."""
        if not isinstance(bundle, CommittedCheckpointBundle):
            raise TypeError("restore_bundle requires CommittedCheckpointBundle")
        _RECOVERY_ATOMIC_JSON_WRITE(self._store.substrate_path, bundle.substrate)
        _RECOVERY_ATOMIC_JSON_WRITE(self._store.governance_path, bundle.governance)
        _RECOVERY_ATOMIC_JSON_WRITE(self._store.manifest_path, bundle.manifest)
        if bundle.journal_present:
            self._atomic_journal_write(bundle.journal_records)
        elif self._store.journal_path.exists():
            self._store.journal_path.unlink()
            _RECOVERY_FSYNC_DIRECTORY(self._store.root)

        restored = self._bundle_unlocked()
        if _rr._digest(restored.manifest) != _rr._digest(bundle.manifest):
            raise _rr.RuntimeRecoveryError("checkpoint bundle restore verification failed")
        self._store._observed_generation = restored.generation
        self._store._observed_manifest_digest = _rr._digest(restored.manifest)

    def _atomic_journal_write(self, records: tuple[dict, ...]) -> None:
        path = self._store.journal_path
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        payload = b"".join(
            _rr._canonical_bytes(dict(record)) + b"\n" for record in records
        )
        with tmp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            _rr.os.fsync(handle.fileno())
        _rr.os.replace(tmp, path)
        _RECOVERY_FSYNC_DIRECTORY(path.parent)