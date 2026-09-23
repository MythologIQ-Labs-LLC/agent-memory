"""Issue #422: owner-level restart contracts for auxiliary correctness state."""

from __future__ import annotations

import copy
import unittest

from agentmem_ref.core import policy
from agentmem_ref.memory.telemetry import TelemetryProjector
from agentmem_ref.memory.telemetry_retention import TelemetryStore
from agentmem_ref.runtime.adapter import Clock, GovernedMemoryAdapter
from agentmem_ref.runtime.write_claims import (
    ACQUIRED,
    COMMITTED,
    INVALIDATED,
    RESTART_INVALIDATION_REASON,
    SharedWriteCoordinator,
    WriteClaim,
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
from agentmem_ref.state.substrate import InMemoryTemporalGraph


class ManualClock:
    def __init__(self, value: str = "2026-09-23T06:00:00Z") -> None:
        self.value = value

    def now(self) -> str:
        return self.value


def telemetry_event(event_id: str, memory_id: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "event_id": event_id,
        "event_type": "memory.recalled",
        "event_version": "1.0.0",
        "timestamp": "2026-09-23T06:00:00Z",
        "memory_id": memory_id,
        "component": "runtime-memory",
        "correlation_id": f"workflow:{event_id}",
        "payload": {"content": f"SECRET:{memory_id}"},
    }


class ProjectionCheckpointTests(unittest.TestCase):
    def test_round_trip_preserves_supersession_and_residual_semantics(self):
        store = ProjectionStore()
        store.declare(
            Projection(
                projection_id="projection:summary",
                basis=(("memory:a", 1),),
                transform=DETERMINISTIC,
                content_class=DERIVED_CONTENT,
                rebuild=REPRODUCIBLE,
                scope="tenant:a",
            )
        )
        store.supersede("projection:summary", (("memory:a", 2),))

        snapshot = store.export_checkpoint_state()
        restored = ProjectionStore()
        restored.restore_checkpoint_state(snapshot)

        live = restored.get("projection:summary")
        self.assertIsNotNone(live)
        self.assertEqual(live.version, 2)
        self.assertEqual(live.basis, (("memory:a", 2),))
        superseded = restored.superseded("projection:summary")
        self.assertEqual(len(superseded), 1)
        self.assertEqual(superseded[0].version, 1)
        self.assertEqual(superseded[0].superseded_by, "projection:summary@v2")

        deleted_view = CanonicalView(
            versions={"memory:a": 2},
            tombstoned={"memory:a"},
            purged=set(),
        )
        self.assertEqual(restored.freshness(live, deleted_view), RESIDUAL)

    def test_incompatible_projection_checkpoint_refuses(self):
        store = ProjectionStore()
        snapshot = store.export_checkpoint_state()
        snapshot["schema_version"] = "999.0.0"
        with self.assertRaisesRegex(ValueError, "unsupported projection checkpoint schema"):
            ProjectionStore().restore_checkpoint_state(snapshot)


class TelemetryCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.old = TelemetryProjector(
            b"old-telemetry-key-material-0001", key_id="telemetry-2026-08"
        )
        self.new = TelemetryProjector(
            b"new-telemetry-key-material-0002", key_id="telemetry-2026-09"
        )

    def test_round_trip_preserves_records_expiry_and_missing_key_uncertainty(self):
        store = TelemetryStore()
        store.append(
            self.old.project(telemetry_event("evt-old", "memory:a")),
            expires_at="2026-10-01T00:00:00Z",
        )
        store.append(
            self.new.project(telemetry_event("evt-new", "memory:a")),
            expires_at="2026-10-02T00:00:00Z",
        )

        snapshot = store.export_checkpoint_state()
        restored = TelemetryStore()
        restored.restore_checkpoint_state(snapshot)

        self.assertEqual(restored.records(), store.records())
        result = restored.purge_memory(
            "memory:a",
            projectors={self.new.key_id: self.new},
        )
        self.assertFalse(result.complete)
        self.assertEqual(result.removed_count, 1)
        self.assertEqual(result.unresolved_key_ids, (self.old.key_id,))
        self.assertEqual(restored.records()[0].expires_at, "2026-10-01T00:00:00Z")

    def test_incompatible_telemetry_checkpoint_refuses_without_partial_restore(self):
        store = TelemetryStore()
        store.append(
            self.new.project(telemetry_event("evt-existing", "memory:a")),
            expires_at="2026-10-02T00:00:00Z",
        )
        before = store.records()
        incompatible = copy.deepcopy(store.export_checkpoint_state())
        incompatible["checkpoint_owner"] = "not-telemetry"
        with self.assertRaisesRegex(ValueError, "telemetry checkpoint owner mismatch"):
            store.restore_checkpoint_state(incompatible)
        self.assertEqual(store.records(), before)


class WriteClaimCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.substrate = InMemoryTemporalGraph()
        self.adapter = GovernedMemoryAdapter(
            self.substrate,
            tenant="shared:test",
            clock=Clock(),
        )
        self.claim_clock = ManualClock()

    def coordinator(self) -> SharedWriteCoordinator:
        return SharedWriteCoordinator(
            self.adapter,
            authority_resolver=lambda claim: claim.authority_ref == "authority:shared-write",
            now=self.claim_clock.now,
        )

    def claim(self, claim_id: str = "claim:a") -> WriteClaim:
        return WriteClaim(
            claim_id=claim_id,
            actor_id="agent:a",
            task_id="task:shared",
            scope="shared:test",
            target_reference="memory:shared",
            mutation_class="promotion",
            authority_ref="authority:shared-write",
            state_snapshot=f"v{self.adapter.state_version('memory:shared')}",
            issued_at="2026-09-23T05:00:00Z",
            expires_at="2026-09-23T07:00:00Z",
        )

    def proposal(self) -> policy.Proposal:
        return policy.Proposal(
            proposal_id="proposal:shared",
            actor_id="agent:a",
            charter_version="charter:1",
            target_reference="memory:shared",
            target_class=policy.M2,
            scope="shared:test",
            operation="promotion",
            current_strength="reinforced",
            proposed_strength="promoted",
            downstream_authority=policy.A1,
            reversibility="reversible",
            risk_class="low",
            evidence_refs=("evidence:shared",),
            state_snapshot=f"v{self.adapter.state_version('memory:shared')}",
            tenant_ref="shared:test",
            purpose="shared-write-test",
            task_ref="task:shared",
        )

    def test_active_claim_is_invalidated_not_resurrected_after_restart(self):
        original = self.coordinator()
        acquired = original.acquire(self.claim())
        self.assertEqual(acquired.status, ACQUIRED)

        restored = self.coordinator()
        restored.restore_checkpoint_state(original.export_checkpoint_state())

        record = restored.record("claim:a")
        self.assertIsNotNone(record)
        self.assertEqual(record.status, INVALIDATED)
        self.assertEqual(record.reason, RESTART_INVALIDATION_REASON)
        self.assertIsNone(restored.active_claim_id("shared:test", "memory:shared"))
        self.assertEqual(record.events[-1]["event_type"], "memory.write_claim_invalidated")
        self.assertEqual(record.events[-1]["payload"]["reason"], RESTART_INVALIDATION_REASON)

        fresh = restored.acquire(self.claim("claim:b"))
        self.assertEqual(fresh.status, ACQUIRED)
        self.assertEqual(restored.active_claim_id("shared:test", "memory:shared"), "claim:b")

    def test_terminal_claim_and_audit_evidence_round_trip(self):
        original = self.coordinator()
        original.acquire(self.claim())
        committed = original.commit("claim:a", self.proposal(), "shared fact")
        self.assertEqual(committed.status, COMMITTED)
        receipt_ref = committed.commit_result.receipt["receipt_id"]

        restored = self.coordinator()
        restored.restore_checkpoint_state(original.export_checkpoint_state())
        record = restored.record("claim:a")

        self.assertIsNotNone(record)
        self.assertEqual(record.status, COMMITTED)
        self.assertEqual(record.commit_receipt_ref, receipt_ref)
        self.assertIsNone(record.commit_result)
        self.assertEqual(record.events, committed.events)
        self.assertEqual(restored.events, original.events)
        self.assertIsNone(restored.active_claim_id("shared:test", "memory:shared"))

    def test_incompatible_write_claim_checkpoint_refuses(self):
        coordinator = self.coordinator()
        snapshot = coordinator.export_checkpoint_state()
        snapshot["schema_version"] = "2.0.0"
        with self.assertRaisesRegex(ValueError, "unsupported write-claim checkpoint schema"):
            self.coordinator().restore_checkpoint_state(snapshot)


if __name__ == "__main__":
    unittest.main()
