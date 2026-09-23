"""Issue #424: atomic auxiliary state composition with restart generations."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref.auxiliary_checkpoint import (
    AUXILIARY_CUSTODY_KEY,
    ComposedRestartSafeRuntime,
)
from agentmem_ref.memory.telemetry import TelemetryProjector
from agentmem_ref.memory.telemetry_retention import TelemetryStore
from agentmem_ref.restart_runtime import (
    CapabilityBinding,
    RestartSafeRuntime,
    RuntimeCheckpointConflict,
    RuntimeProfile,
    RuntimeRecoveryError,
)
from agentmem_ref.state.projections import (
    CanonicalView,
    DERIVED_CONTENT,
    DETERMINISTIC,
    Projection,
    ProjectionStore,
    REPRODUCIBLE,
    RESIDUAL,
)
from agentmem_ref.write_claims import (
    ACQUIRED,
    INVALIDATED,
    SharedWriteCoordinator,
    WriteClaim,
)


class ManualClock:
    def __init__(self, value: str = "2026-09-23T06:15:00Z") -> None:
        self.value = value

    def now(self) -> str:
        return self.value


def profile() -> RuntimeProfile:
    binding = CapabilityBinding(
        component_id="reference-governed-memory",
        component_version="1.0.0",
        capability_id="governed-memory-core",
        capability_version="1.0.0",
        maturity="reference_qualified",
        evidence_ref="evidence:reference-runtime-core-v1",
    )
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="reference-project-memory",
        profile_version="1.0.0",
        bindings=(binding,),
    )


def telemetry_event(event_id: str, memory_id: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "event_id": event_id,
        "event_type": "memory.recalled",
        "event_version": "1.0.0",
        "timestamp": "2026-09-23T06:15:00Z",
        "memory_id": memory_id,
        "component": "runtime-memory",
        "correlation_id": f"workflow:{event_id}",
        "payload": {"content": f"SECRET:{memory_id}"},
    }


class AuxiliaryCheckpointCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile = profile()
        self.clock = ManualClock()
        self.old_projector = TelemetryProjector(
            b"old-telemetry-key-material-0001",
            key_id="telemetry-2026-08",
        )
        self.factories = {
            "projection-store": lambda _adapter: ProjectionStore(),
            "shared-write-coordinator": lambda adapter: SharedWriteCoordinator(
                adapter,
                authority_resolver=lambda claim: claim.authority_ref == "authority:shared-write",
                now=self.clock.now,
            ),
            "telemetry-store": lambda _adapter: TelemetryStore(),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _create(self) -> ComposedRestartSafeRuntime:
        return ComposedRestartSafeRuntime.create(
            self.root,
            tenant="tenant-acme",
            profile=self.profile,
            auxiliary_factories=self.factories,
        )

    def _recover(self, factories=None) -> ComposedRestartSafeRuntime:
        return ComposedRestartSafeRuntime.recover(
            self.root,
            profile=self.profile,
            auxiliary_factories=self.factories if factories is None else factories,
        )

    def _claim(self, runtime, claim_id: str = "claim:a") -> WriteClaim:
        return WriteClaim(
            claim_id=claim_id,
            actor_id="agent:a",
            task_id="task:shared",
            scope="tenant-acme",
            target_reference="memory:shared",
            mutation_class="promotion",
            authority_ref="authority:shared-write",
            state_snapshot=f"v{runtime.adapter.state_version('memory:shared')}",
            issued_at="2026-09-23T06:00:00Z",
            expires_at="2026-09-23T07:00:00Z",
        )

    def test_one_generation_restores_all_composed_state_with_owner_semantics(self):
        runtime = self._create()
        projections = runtime.auxiliary("projection-store")
        claims = runtime.auxiliary("shared-write-coordinator")
        telemetry = runtime.auxiliary("telemetry-store")

        projections.declare(
            Projection(
                projection_id="projection:summary",
                basis=(("memory:a", 1),),
                transform=DETERMINISTIC,
                content_class=DERIVED_CONTENT,
                rebuild=REPRODUCIBLE,
                scope="tenant-acme",
            )
        )
        acquired = claims.acquire(self._claim(runtime))
        self.assertEqual(acquired.status, ACQUIRED)
        telemetry.append(
            self.old_projector.project(telemetry_event("evt-old", "memory:a")),
            expires_at="2026-10-01T00:00:00Z",
        )

        committed = runtime.checkpoint()
        self.assertEqual(committed.generation, 2)
        self.assertEqual(
            {item.component_id for item in runtime.auxiliary_evidence()},
            set(self.factories),
        )

        recovered = self._recover()
        self.assertEqual(recovered.recovery_evidence.generation, committed.generation)

        restored_projection = recovered.auxiliary("projection-store").get("projection:summary")
        self.assertIsNotNone(restored_projection)
        deleted_view = CanonicalView(
            versions={"memory:a": 1},
            tombstoned={"memory:a"},
            purged=set(),
        )
        self.assertEqual(
            recovered.auxiliary("projection-store").freshness(
                restored_projection, deleted_view
            ),
            RESIDUAL,
        )

        restored_claim = recovered.auxiliary("shared-write-coordinator").record("claim:a")
        self.assertIsNotNone(restored_claim)
        self.assertEqual(restored_claim.status, INVALIDATED)
        self.assertIsNone(
            recovered.auxiliary("shared-write-coordinator").active_claim_id(
                "tenant-acme", "memory:shared"
            )
        )

        purge = recovered.auxiliary("telemetry-store").purge_memory(
            "memory:a", projectors={}
        )
        self.assertFalse(purge.complete)
        self.assertEqual(purge.unresolved_key_ids, (self.old_projector.key_id,))
        self.assertEqual(purge.removed_count, 0)

    def test_stale_writer_cannot_partially_publish_newer_auxiliary_state(self):
        self._create()
        writer_a = self._recover()
        writer_b = self._recover()

        writer_a.auxiliary("projection-store").declare(
            Projection(
                projection_id="projection:a",
                basis=(("memory:a", 1),),
                transform=DETERMINISTIC,
                content_class=DERIVED_CONTENT,
                rebuild=REPRODUCIBLE,
                scope="tenant-acme",
            )
        )
        writer_a.checkpoint()

        writer_b.auxiliary("telemetry-store").append(
            self.old_projector.project(telemetry_event("evt-stale", "memory:b")),
            expires_at="2026-10-01T00:00:00Z",
        )
        with self.assertRaises(RuntimeCheckpointConflict):
            writer_b.checkpoint()

        recovered = self._recover()
        self.assertIsNotNone(
            recovered.auxiliary("projection-store").get("projection:a")
        )
        self.assertEqual(recovered.auxiliary("telemetry-store").records(), ())

    def test_mixed_generation_governance_payload_fails_closed(self):
        runtime = self._create()
        old_governance = json.loads((self.root / "governance.json").read_text())

        runtime.auxiliary("telemetry-store").append(
            self.old_projector.project(telemetry_event("evt-new", "memory:a")),
            expires_at="2026-10-01T00:00:00Z",
        )
        runtime.checkpoint()
        (self.root / "governance.json").write_text(
            json.dumps(old_governance, sort_keys=True), encoding="utf-8"
        )

        with self.assertRaisesRegex(RuntimeRecoveryError, "governance checkpoint digest mismatch"):
            self._recover()

    def test_composition_drift_refuses_instead_of_fabricating_state(self):
        self._create()
        missing_telemetry = {
            key: value for key, value in self.factories.items() if key != "telemetry-store"
        }
        with self.assertRaisesRegex(RuntimeRecoveryError, "composition changed"):
            self._recover(missing_telemetry)

    def test_legacy_checkpoint_cannot_be_promoted_to_composed_state_implicitly(self):
        RestartSafeRuntime.create(
            self.root,
            tenant="tenant-acme",
            profile=self.profile,
        )
        with self.assertRaisesRegex(RuntimeRecoveryError, "explicit migration is required"):
            self._recover()

    def test_uncomposed_runtime_makes_no_auxiliary_durability_claim(self):
        runtime = RestartSafeRuntime.create(
            self.root,
            tenant="tenant-acme",
            profile=self.profile,
        )
        self.assertNotIn(AUXILIARY_CUSTODY_KEY, runtime.adapter.extension_state)
        recovered = RestartSafeRuntime.recover(self.root, profile=self.profile)
        self.assertNotIn(AUXILIARY_CUSTODY_KEY, recovered.adapter.extension_state)

    def test_per_component_digest_is_validated_after_governance_integrity(self):
        base = RestartSafeRuntime.create(
            self.root,
            tenant="tenant-acme",
            profile=self.profile,
        )
        projection_snapshot = ProjectionStore().export_checkpoint_state()
        base.adapter.extension_state[AUXILIARY_CUSTODY_KEY] = {
            "schema_version": "1.0.0",
            "components": {
                "projection-store": {
                    "checkpoint_digest": "sha256:" + "0" * 64,
                    "snapshot": projection_snapshot,
                }
            },
        }
        base.checkpoint()

        with self.assertRaisesRegex(RuntimeRecoveryError, "auxiliary checkpoint digest mismatch"):
            ComposedRestartSafeRuntime.recover(
                self.root,
                profile=self.profile,
                auxiliary_factories={
                    "projection-store": lambda _adapter: ProjectionStore(),
                },
            )


if __name__ == "__main__":
    unittest.main()
