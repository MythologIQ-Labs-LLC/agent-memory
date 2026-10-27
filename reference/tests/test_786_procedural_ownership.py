"""#786 candidate (isolated, opt-in, pending review): creator-principal skill ownership.

Adversarial owner / non-owner / delegation cases. Ownership is recorded in canonical
scope metadata only when the host composes ``ProceduralMemoryRuntime`` with
``ownership="creator_principal_v1"``; the creator is the host-bound principal, never a
caller-supplied actor id; and the canonical adapter enforces it, so going around the
procedural runtime to the adapter does not bypass it. Revocation may be delegated only
through a governed A5 authority change bound to an external verification.
"""
from __future__ import annotations

import unittest

from agentmem_ref import policy
from agentmem_ref.adapter import Clock, RecallContext
from agentmem_ref.capabilities import ComponentRegistry
from agentmem_ref.procedural_memory import ProceduralMemoryRuntime, SkillArtifact, reference_procedural_component
from agentmem_ref.runtime.adapter import OWNERSHIP_CREATOR_PRINCIPAL
from agentmem_ref.runtime.restart_runtime import CheckpointableGovernedMemoryAdapter
from agentmem_ref.runtime.revocation_delegation import RevocationDelegationChange, commit_revocation_delegation
from agentmem_ref.substrate import InMemoryTemporalGraph

from tests.qualified_fixtures import corpus_for, registry_for, rule

TENANT = "tenant:ownership"
PROJECT = "project:ownership"
PURPOSE = "release_planning"
OWNER = "agent:owner"
PEER = "agent:peer"
SKILL = "skill:release-workflow"


def _context(principal: str) -> RecallContext:
    return RecallContext(target_domain_refs=(TENANT, PROJECT), principal_ref=principal,
                         project_ref=PROJECT, purpose=PURPOSE)


def _artifact(version: int) -> SkillArtifact:
    return SkillArtifact(
        skill_id="release-workflow", version=version, purpose=PURPOSE, scope=TENANT,
        isolation_domain_refs=(TENANT, PROJECT), required_isolation_domain_refs=(TENANT, PROJECT),
        procedure_markdown=f"# Release workflow v{version}\n- Run release checks.",
        provenance_refs=(f"episode:release-{version}",), validation_refs=(f"validation:release-{version}",),
    )


class OwnershipFixture(unittest.TestCase):
    ownership = OWNERSHIP_CREATOR_PRINCIPAL

    def setUp(self) -> None:
        self.substrate = InMemoryTemporalGraph()
        self.corpus = corpus = corpus_for(rule(rule_id="rule:skill-version-advance", target=SKILL,
                                               criterion="skill-version-advance", from_state="v1", to_values=("v2",)))
        self.adapter = CheckpointableGovernedMemoryAdapter(
            self.substrate, tenant=TENANT, clock=Clock(), verifier_registry=registry_for(corpus))
        self.registry = ComponentRegistry()
        self.registry.register(reference_procedural_component())
        self.owner = self.runtime_for(OWNER)
        saved = self.owner.commit_skill(self.owner.propose_skill(_artifact(1), actor_id=OWNER))
        self.assertTrue(saved.commit.committed, saved.commit)
        self.fact = saved.commit.fact_uuid

    def runtime_for(self, principal: str, ownership=OWNERSHIP_CREATOR_PRINCIPAL) -> ProceduralMemoryRuntime:
        return ProceduralMemoryRuntime(substrate=self.substrate, adapter=self.adapter, registry=self.registry,
                                       revocation_context=_context(principal), ownership=ownership)

    def assert_intact(self) -> None:
        self.assertEqual(self.adapter.current_fact_uuid(SKILL), self.fact)
        self.assertIsNone(self.adapter.tombstone(self.fact))

    def revoke(self, principal: str):
        return self.runtime_for(principal).revoke_skill("release-workflow", actor_id=principal,
                                                        evidence_refs=(f"evidence:{principal}",))

    def direct_proposal(self, actor: str, operation: str, **extra) -> policy.Proposal:
        fields = dict(
            proposal_id=f"proposal:direct:{actor}:{operation}", actor_id=actor, charter_version="procedural-memory-v1",
            target_reference=SKILL, target_class=policy.M3, scope=TENANT, operation=operation,
            current_strength="promoted", proposed_strength="archived", downstream_authority=policy.A1,
            reversibility="reversible", risk_class="low", evidence_refs=("evidence:direct",),
            state_snapshot=f"v{self.adapter.state_version(SKILL)}", tenant_ref=TENANT, purpose=PURPOSE,
            isolation_domain_refs=(TENANT, PROJECT), required_isolation_domain_refs=(TENANT, PROJECT),
            project_ref=PROJECT,
        )
        fields.update(extra)
        return policy.Proposal(**fields)

    def delegation(self, actor: str, change_id: str, before, after, *, attest=True, kind="add"):
        state = self.adapter.extension_state.get("revocation_delegation_authority") or {}
        version = f"v{dict(state.get('versions', {})).get(SKILL, 0)}"
        proposal = policy.Proposal(
            proposal_id=f"proposal:delegate:{change_id}", actor_id=actor, charter_version="procedural-memory-v1",
            target_reference=SKILL, target_class=policy.M5, scope=TENANT, operation="authority_change",
            current_strength="promoted", proposed_strength="promoted", downstream_authority=policy.A5,
            reversibility="reversible", risk_class="high", evidence_refs=(f"evidence:delegate:{change_id}",),
            state_snapshot=version, tenant_ref=TENANT, purpose=PURPOSE,
            isolation_domain_refs=(TENANT, PROJECT), required_isolation_domain_refs=(TENANT, PROJECT),
            project_ref=PROJECT,
        )
        attestation = policy.ExternalVerification(
            bound_proposal_id=proposal.proposal_id, verifier_principal_id="principal:security-officer",
            authority_kind=policy.HUMAN_CONFIRMATION, max_risk_class="high",
        ) if attest else None
        change = RevocationDelegationChange(change_id=change_id, memory_ref=SKILL, change_kind=kind,
                                            before_delegates=tuple(before), after_delegates=tuple(after))
        return commit_revocation_delegation(self.adapter, change, proposal, attestation=attestation)


class CreatorOwnershipTests(OwnershipFixture):
    def test_creator_is_recorded_from_host_binding(self):
        self.assertEqual(self.adapter.lineage_owner(SKILL), OWNER)

    def test_caller_supplied_author_is_refused(self):
        spoofing = self.runtime_for(PEER)
        with self.assertRaisesRegex(ValueError, "host-bound principal"):
            spoofing.propose_skill(_artifact(2), actor_id=OWNER)
        proposal = self.owner.propose_skill(_artifact(2), actor_id=OWNER)
        with self.assertRaisesRegex(ValueError, "host-bound principal"):
            spoofing.commit_skill(proposal)
        self.assert_intact()

    def test_owner_revokes(self):
        result = self.revoke(OWNER)
        self.assertTrue(result.commit.committed, result.commit)
        self.assertIsNotNone(self.adapter.tombstone(self.fact))

    def test_same_project_non_owner_cannot_revoke(self):
        result = self.revoke(PEER)
        self.assertFalse(result.commit.committed)
        self.assertEqual(result.commit.decision.outcome, policy.BLOCK)
        self.assertEqual(result.commit.receipt["selected_action"], "none")
        self.assert_intact()

    def test_non_owner_cannot_spoof_the_owner_at_the_procedural_boundary(self):
        with self.assertRaisesRegex(ValueError, "host-bound principal"):
            self.runtime_for(PEER).revoke_skill("release-workflow", actor_id=OWNER, evidence_refs=("evidence:x",))
        self.assert_intact()

    def test_direct_canonical_delete_by_non_owner_is_refused(self):
        for operation in ("pruning", "permanent_deletion"):
            with self.subTest(operation=operation):
                result = self.adapter.governed_delete(
                    self.direct_proposal(PEER, operation, reversibility="irreversible" if operation != "pruning"
                                         else "reversible"), self.fact)
                self.assertFalse(result.committed)
                self.assertEqual(result.refusal, "write_target_unavailable")
                self.assert_intact()

    def takeover(self, actor: str):
        # Qualified evidence for the v1 -> v2 transition: without the ownership gate
        # this correction would commit, so a refusal here is ownership, not review.
        return self.adapter.commit_proposal(
            self.direct_proposal(actor, "correction", proposed_strength="promoted", risk_class="medium",
                                 proposal_id=f"proposal:takeover:{actor}"),
            "# Release workflow\n- Push straight to main.",
            evidence=self.corpus.evidence_for(target_reference=SKILL, criterion="skill-version-advance",
                                              pre_state="v1", proposed_value="v2"))

    def test_owner_takeover_control_commits_with_the_same_evidence(self):
        self.assertTrue(self.takeover(OWNER).committed)
        self.assertEqual(self.adapter.lineage_owner(SKILL), OWNER)

    def test_non_owner_cannot_take_over_by_correction(self):
        takeover = self.takeover(PEER)
        self.assertFalse(takeover.committed)
        self.assertEqual(takeover.refusal, "write_target_unavailable")
        self.assert_intact()
        self.assertEqual(self.adapter.lineage_owner(SKILL), OWNER)

    def test_owner_correction_carries_ownership_forward(self):
        approved = self.owner.approve_skill_proposal(self.owner.propose_skill(_artifact(2), actor_id=OWNER),
                                                     approval_ref="approval:release-v2")
        v2 = self.owner.commit_skill(approved, evidence=self.corpus.evidence_for(
            target_reference=SKILL, criterion="skill-version-advance", pre_state="v1", proposed_value="v2"))
        self.assertTrue(v2.commit.committed, v2.commit)
        self.assertEqual(self.adapter.lineage_owner(SKILL), OWNER)
        self.assertFalse(self.revoke(PEER).commit.committed)
        self.assertTrue(self.revoke(OWNER).commit.committed)

    def test_ownership_survives_checkpoint_restore(self):
        state = self.adapter.export_checkpoint_state()
        restored = CheckpointableGovernedMemoryAdapter(self.substrate, tenant=TENANT, clock=Clock())
        restored.restore_checkpoint_state(state)
        self.assertEqual(restored.lineage_owner(SKILL), OWNER)
        self.adapter = restored
        self.assertFalse(self.revoke(PEER).commit.committed)
        self.assert_intact()


class DelegationTests(OwnershipFixture):
    def test_governed_delegation_lets_delegate_revoke(self):
        granted = self.delegation(OWNER, "grant-peer", (), (PEER,))
        self.assertTrue(granted.committed, granted.refusal)
        self.assertEqual(granted.decision.outcome, policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertTrue(self.revoke(PEER).commit.committed)

    def test_delegation_without_external_verification_is_not_committed(self):
        refused = self.delegation(OWNER, "grant-unverified", (), (PEER,), attest=False)
        self.assertFalse(refused.committed)
        self.assertEqual(refused.refusal, "external_verification_required")
        self.assertFalse(self.revoke(PEER).commit.committed)
        self.assert_intact()

    def test_non_owner_cannot_grant_itself(self):
        refused = self.delegation(PEER, "self-grant", (), (PEER,))
        self.assertFalse(refused.committed)
        self.assertEqual(refused.refusal, "owner_required")
        self.assertFalse(self.revoke(PEER).commit.committed)

    def test_delegate_can_revoke_but_not_replace_the_head(self):
        self.assertTrue(self.delegation(OWNER, "grant-peer", (), (PEER,)).committed)
        takeover = CreatorOwnershipTests.takeover(self, PEER)
        self.assertFalse(takeover.committed)
        self.assertEqual(takeover.refusal, "write_target_unavailable")
        self.assert_intact()
        self.assertEqual(self.adapter.lineage_owner(SKILL), OWNER)

    def test_removed_delegate_is_refused_again(self):
        self.assertTrue(self.delegation(OWNER, "grant-peer", (), (PEER,)).committed)
        removed = self.delegation(OWNER, "remove-peer", (PEER,), (), kind="remove")
        self.assertTrue(removed.committed, removed.refusal)
        self.assertFalse(self.revoke(PEER).commit.committed)
        self.assert_intact()

    def test_replay_and_stale_delegation_bindings_are_refused(self):
        self.assertTrue(self.delegation(OWNER, "grant-peer", (), (PEER,)).committed)
        self.assertEqual(self.delegation(OWNER, "grant-peer", (PEER,), (PEER, "agent:third")).refusal,
                         "delegation_change_replay")
        self.assertEqual(self.delegation(OWNER, "grant-stale", (), ("agent:third",)).refusal,
                         "stale_delegation_binding")

    def test_delegation_survives_checkpoint_restore(self):
        self.assertTrue(self.delegation(OWNER, "grant-peer", (), (PEER,)).committed)
        restored = CheckpointableGovernedMemoryAdapter(self.substrate, tenant=TENANT, clock=Clock())
        restored.restore_checkpoint_state(self.adapter.export_checkpoint_state())
        self.adapter = restored
        self.assertTrue(self.revoke(PEER).commit.committed)


class OptInIsolationTests(unittest.TestCase):
    def test_default_runtime_records_no_owner_and_keeps_domain_authority(self):
        substrate = InMemoryTemporalGraph()
        corpus = corpus_for(rule(rule_id="rule:skill-version-advance", target=SKILL,
                                 criterion="skill-version-advance", from_state="v1", to_values=("v2",)))
        adapter = CheckpointableGovernedMemoryAdapter(substrate, tenant=TENANT, clock=Clock(),
                                                      verifier_registry=registry_for(corpus))
        registry = ComponentRegistry()
        registry.register(reference_procedural_component())
        owner = ProceduralMemoryRuntime(substrate=substrate, adapter=adapter, registry=registry,
                                        revocation_context=_context(OWNER))
        self.assertTrue(owner.commit_skill(owner.propose_skill(_artifact(1), actor_id=OWNER)).commit.committed)
        self.assertIsNone(adapter.lineage_owner(SKILL))
        peer = ProceduralMemoryRuntime(substrate=substrate, adapter=adapter, registry=registry,
                                       revocation_context=_context(PEER))
        # Pre-candidate contract, unchanged: project/task/domain authority only.
        self.assertTrue(peer.revoke_skill("release-workflow", actor_id=PEER,
                                          evidence_refs=("evidence:peer",)).commit.committed)

    def test_ownership_requires_a_host_principal(self):
        with self.assertRaisesRegex(ValueError, "host-bound principal"):
            ProceduralMemoryRuntime(substrate=InMemoryTemporalGraph(), adapter=None, registry=ComponentRegistry(),
                                    ownership=OWNERSHIP_CREATOR_PRINCIPAL)

    def test_unowned_lineage_is_never_claimed_by_a_later_version(self):
        substrate = InMemoryTemporalGraph()
        corpus = corpus_for(rule(rule_id="rule:skill-version-advance", target=SKILL,
                                 criterion="skill-version-advance", from_state="v1", to_values=("v2",)))
        adapter = CheckpointableGovernedMemoryAdapter(substrate, tenant=TENANT, clock=Clock(),
                                                      verifier_registry=registry_for(corpus))
        registry = ComponentRegistry()
        registry.register(reference_procedural_component())
        legacy = ProceduralMemoryRuntime(substrate=substrate, adapter=adapter, registry=registry,
                                         revocation_context=_context(OWNER))
        self.assertTrue(legacy.commit_skill(legacy.propose_skill(_artifact(1), actor_id=OWNER)).commit.committed)
        claimant = ProceduralMemoryRuntime(substrate=substrate, adapter=adapter, registry=registry,
                                           revocation_context=_context(PEER), ownership=OWNERSHIP_CREATOR_PRINCIPAL)
        approved = claimant.approve_skill_proposal(claimant.propose_skill(_artifact(2), actor_id=PEER),
                                                   approval_ref="approval:claim")
        claimed = claimant.commit_skill(approved, evidence=corpus.evidence_for(
            target_reference=SKILL, criterion="skill-version-advance", pre_state="v1", proposed_value="v2"))
        self.assertTrue(claimed.commit.committed, claimed.commit)  # the write is legitimate...
        self.assertIsNone(adapter.lineage_owner(SKILL))  # ...but cannot claim an unowned lineage


if __name__ == "__main__":
    unittest.main()
