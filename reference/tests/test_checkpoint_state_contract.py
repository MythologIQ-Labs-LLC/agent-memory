"""Issue #363 phase 1/2: declared checkpoint ownership and fail-closed support."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import policy, restart_runtime
from agentmem_ref.core.readmission import RejectedValueRegistry
from agentmem_ref.restart_runtime import (
    ADAPTER_CHECKPOINT_OWNER,
    CapabilityBinding,
    CheckpointableGovernedMemoryAdapter,
    JsonRuntimeStateStore,
    RuntimeProfile,
    RuntimeRecoveryError,
)
from agentmem_ref.substrate import Episode, Fact, InMemoryTemporalGraph

TENANT = "tenant:checkpoint"
PROFILE = RuntimeProfile(
    runtime_version="0.1.0-reference",
    profile_id="checkpoint-contract",
    profile_version="1.0.0",
    bindings=(
        CapabilityBinding(
            component_id="reference-governed-memory",
            component_version="1.0.0",
            capability_id="governed-memory-core",
            capability_version="1.0.0",
            maturity="reference_qualified",
            evidence_ref="evidence:reference-runtime-core-v1",
        ),
    ),
)


def _proposal(pid: str, target: str = "memory:checkpoint") -> policy.Proposal:
    return policy.Proposal(
        proposal_id=pid,
        actor_id="agent:checkpoint",
        charter_version="charter:v1",
        target_reference=target,
        target_class=policy.M1,
        scope=TENANT,
        operation="runtime_assembly",
        current_strength="observed",
        proposed_strength="tentative",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=("evidence:checkpoint",),
        tenant_ref=TENANT,
        isolation_domain_refs=(TENANT,),
    )


class NonCheckpointingSubstrate:
    """Valid enough for ordinary adapter use; deliberately no checkpoint seam."""

    def __init__(self) -> None:
        self.facts: dict[str, Fact] = {}

    def add_episode(self, episode: Episode) -> None:
        return None

    def write_fact(self, fact: Fact) -> None:
        self.facts[fact.uuid] = fact

    def invalidate_fact(self, uuid: str, invalid_at: str, expired_at: str) -> None:
        return None

    def get_fact(self, uuid: str) -> Fact | None:
        return self.facts.get(uuid)

    def delete_fact(self, uuid: str) -> None:
        self.facts.pop(uuid, None)

    def search(self, query: str, group_ids=None):
        return []


class SubstrateCheckpointContractTests(unittest.TestCase):
    def test_inmemory_provider_owns_roundtrip_and_identifier_progress(self):
        substrate = InMemoryTemporalGraph()
        substrate.add_episode(
            Episode(
                uuid="episode:1",
                content="source",
                source_description="fixture",
                valid_at="2026-09-22T00:00:00Z",
                group_id=TENANT,
            )
        )
        first_id = substrate.next_id()
        substrate.write_fact(
            Fact(
                uuid=first_id,
                fact_text="checkpoint fact",
                group_id=TENANT,
                episode_uuids=("episode:1",),
                created_at="2026-09-22T00:00:01Z",
            )
        )

        snapshot = restart_runtime._snapshot_substrate(substrate)
        self.assertEqual(snapshot["checkpoint_owner"], "in_memory_temporal_graph")
        restored = restart_runtime._restore_substrate(snapshot)
        self.assertEqual(restored.get_fact(first_id).fact_text, "checkpoint fact")
        self.assertEqual(restored.get_episode("episode:1").content, "source")
        self.assertGreater(restored.next_id(), first_id)

    def test_provider_without_declared_checkpoint_capability_fails_closed(self):
        adapter = CheckpointableGovernedMemoryAdapter(
            NonCheckpointingSubstrate(), tenant=TENANT
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonRuntimeStateStore(Path(tmp))
            with self.assertRaisesRegex(
                RuntimeRecoveryError, "substrate does not declare checkpoint capability"
            ):
                store.checkpoint(adapter, profile=PROFILE, visibility_snapshots={})


class RejectedValueCheckpointContractTests(unittest.TestCase):
    def test_registry_roundtrip_preserves_readmission_authority_metadata(self):
        registry = RejectedValueRegistry()
        registry.reject(
            memory_id="memory:branch",
            value="release",
            superseded_fact_uuid="fact:release",
            correction_proposal_id="proposal:main",
            evidence_refs=("evidence:correction",),
            authority_refs=("authority:review",),
            scope=TENANT,
            rejected_at="2026-09-22T00:00:00Z",
        )
        registry.readmit(
            memory_id="memory:branch",
            value="release",
            proposal_id="proposal:release-again",
            readmitted_at="2026-09-22T00:01:00Z",
            verifier_principal_id="principal:operator",
            authority_kind="human_confirmation",
        )

        rows = registry.export_checkpoint_rows()
        restored = RejectedValueRegistry.restore_checkpoint_rows(rows)
        self.assertEqual(restored.export_checkpoint_rows(), rows)
        descriptor = restored.checkpoint_descriptor()
        self.assertEqual(descriptor["checkpoint_owner"], "rejected_value_registry")
        self.assertEqual(descriptor["record_count"], 1)

    def test_tampered_rejection_identity_fails_closed(self):
        registry = RejectedValueRegistry()
        registry.reject(
            memory_id="memory:branch",
            value="release",
            superseded_fact_uuid="fact:release",
            correction_proposal_id="proposal:main",
            evidence_refs=("evidence:correction",),
            scope=TENANT,
            rejected_at="2026-09-22T00:00:00Z",
        )
        rows = registry.export_checkpoint_rows()
        rows[0]["rejection_id"] = "rejection:sha256:tampered"
        with self.assertRaisesRegex(ValueError, "cannot be reconstructed"):
            RejectedValueRegistry.restore_checkpoint_rows(rows)


class GovernanceCheckpointContractTests(unittest.TestCase):
    def test_adapter_export_is_explicit_and_runtime_envelope_stays_v1(self):
        adapter = CheckpointableGovernedMemoryAdapter(
            InMemoryTemporalGraph(), tenant=TENANT
        )
        committed = adapter.commit_proposal(_proposal("proposal:1"), "checkpoint state")
        self.assertTrue(committed.committed)

        snapshot = restart_runtime._snapshot_governance(
            adapter, profile=PROFILE, visibility_snapshots={}
        )
        self.assertEqual(snapshot["schema_version"], "1.0.0")
        self.assertEqual(snapshot["tenant"], TENANT)
        self.assertEqual(snapshot["adapter"]["checkpoint_owner"], ADAPTER_CHECKPOINT_OWNER)
        self.assertEqual(
            snapshot["adapter"]["rejected_values_descriptor"]["checkpoint_owner"],
            "rejected_value_registry",
        )
        self.assertEqual(restart_runtime.DURABILITY_PROFILE, "reference_file_checkpoint_v1")

    def test_legacy_v1_owner_metadata_is_optional_but_state_is_not_invented(self):
        substrate = InMemoryTemporalGraph()
        adapter = CheckpointableGovernedMemoryAdapter(substrate, tenant=TENANT)
        committed = adapter.commit_proposal(_proposal("proposal:legacy"), "legacy v1 state")
        governance = restart_runtime._snapshot_governance(
            adapter, profile=PROFILE, visibility_snapshots={}
        )
        substrate_snapshot = restart_runtime._snapshot_substrate(substrate)

        governance["adapter"].pop("checkpoint_owner")
        governance["adapter"].pop("rejected_values_descriptor")
        substrate_snapshot.pop("checkpoint_owner")
        substrate_snapshot.pop("id_counter")

        restored_substrate = restart_runtime._restore_substrate(substrate_snapshot)
        restored, _ = restart_runtime._restore_adapter(restored_substrate, governance)
        self.assertEqual(restored.current_fact_uuid("memory:checkpoint"), committed.fact_uuid)
        self.assertIsNotNone(restored_substrate.get_fact(committed.fact_uuid))
        self.assertGreater(restored_substrate.identifier_checkpoint(), 0)

    def test_corrupt_owner_identity_fails_closed(self):
        adapter = CheckpointableGovernedMemoryAdapter(
            InMemoryTemporalGraph(), tenant=TENANT
        )
        snapshot = restart_runtime._snapshot_governance(
            adapter, profile=PROFILE, visibility_snapshots={}
        )
        snapshot["adapter"]["checkpoint_owner"] = "some_other_component"
        with self.assertRaisesRegex(RuntimeRecoveryError, "cannot be reconstructed"):
            restart_runtime._restore_adapter(InMemoryTemporalGraph(), snapshot)


if __name__ == "__main__":
    unittest.main()
