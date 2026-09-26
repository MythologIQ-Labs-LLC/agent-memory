"""Governed shared-domain membership authority evidence for issue #364."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import policy  # noqa: E402
from agentmem_ref.adapter import GovernedMemoryAdapter, RecallContext  # noqa: E402
from agentmem_ref.shared_revocation import (  # noqa: E402
    REQUEST_EXTERNAL,
    SLOT,
    SharedDomainMembershipChange,
    bootstrap_shared_domain_members,
    commit_shared_domain_membership_change,
    current_shared_domain_members,
)
from agentmem_ref.restart_runtime import (  # noqa: E402
    CapabilityBinding,
    RestartSafeRuntime,
    RuntimeProfile,
)
from agentmem_ref.substrate import InMemoryTemporalGraph  # noqa: E402

from tests.prefilter_bypass import admission_only  # noqa: E402


TENANT = "tenant-a"
SHARED = "domain:shared-security"
OTHER = "domain:other"
ALICE = "user:alice"
BOB = "user:bob"
CAROL = "user:carol"
PROFILE = RuntimeProfile(
    runtime_version="0.1.0-reference",
    profile_id="shared-membership-governance",
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


def _membership_proposal(
    proposal_id: str,
    *,
    target: str = SHARED,
    snapshot: str = "v0",
    actor: str = "agent:membership-admin",
    target_class: str = policy.M5,
    authority: str = policy.A5,
    operation: str = "authority_change",
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id=actor,
        charter_version="charter:shared-membership-v1",
        target_reference=target,
        target_class=target_class,
        scope=TENANT,
        operation=operation,
        current_strength="promoted",
        proposed_strength="promoted",
        downstream_authority=authority,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=("evidence:membership-authority",),
        state_snapshot=snapshot,
        tenant_ref=TENANT,
        purpose="shared-memory-administration",
        isolation_domain_refs=(SHARED,),
        required_isolation_domain_refs=(SHARED,),
    )


def _attestation(proposal_id: str, *, verifier: str = "principal:security-admin") -> policy.ExternalVerification:
    return policy.ExternalVerification(
        bound_proposal_id=proposal_id,
        verifier_principal_id=verifier,
        authority_kind=policy.DELEGATED_POLICY,
        max_risk_class="critical",
    )


def _remove_alice(change_id: str = "change:remove-alice") -> SharedDomainMembershipChange:
    return SharedDomainMembershipChange(
        change_id=change_id,
        domain_ref=SHARED,
        change_kind="remove",
        before_members=(ALICE, BOB),
        after_members=(BOB,),
    )


def _shared_fact(memory: GovernedMemoryAdapter) -> str:
    proposal = policy.Proposal(
        proposal_id="proposal:shared-memory",
        actor_id="agent:planner",
        charter_version="charter-1",
        target_reference="mem:shared-security-procedure",
        target_class=policy.M2,
        scope=TENANT,
        operation="promotion",
        current_strength="reinforced",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=("evidence:shared-source",),
        tenant_ref=TENANT,
        purpose="security-review",
        isolation_domain_refs=(SHARED,),
    )
    committed = memory.commit_proposal(proposal, "shared credential rotation guidance")
    if not committed.committed or not committed.fact_uuid:
        raise RuntimeError("shared membership fixture failed to commit")
    return committed.fact_uuid


class SharedMembershipGovernance(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = GovernedMemoryAdapter(InMemoryTemporalGraph(), tenant=TENANT)
        bootstrap_shared_domain_members(self.memory, SHARED, (ALICE, BOB))

    def test_authority_change_requests_external_verification_without_mutation(self):
        proposal = _membership_proposal("proposal:membership:1")
        result = commit_shared_domain_membership_change(self.memory, _remove_alice(), proposal)

        self.assertFalse(result.committed)
        self.assertEqual(result.decision.outcome, policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertEqual(result.receipt["selected_action"], REQUEST_EXTERNAL)
        self.assertEqual(result.pama_decision["decision"]["outcome"], policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertEqual(result.refusal, "external_verification_required")
        self.assertEqual(current_shared_domain_members(self.memory, SHARED), (ALICE, BOB))

    @admission_only()  # exercises full admission's own domain refusal (#548)

    def test_bound_external_verification_commits_without_rewriting_pama_to_allow(self):
        fact_uuid = _shared_fact(self.memory)
        before = self.memory.governed_recall(
            "shared credential rotation guidance",
            RecallContext(target_domain_refs=(SHARED,), principal_ref=ALICE, purpose="security-review"),
        )
        self.assertIn(fact_uuid, before.admitted)

        proposal = _membership_proposal("proposal:membership:2")
        result = commit_shared_domain_membership_change(
            self.memory,
            _remove_alice(),
            proposal,
            attestation=_attestation(proposal.proposal_id),
        )

        self.assertTrue(result.committed)
        self.assertEqual(result.decision.outcome, policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertEqual(result.receipt["selected_action"], REQUEST_EXTERNAL)
        self.assertEqual(result.pama_decision["decision"]["outcome"], policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertIsNotNone(result.external_authority_ref)
        self.assertEqual(current_shared_domain_members(self.memory, SHARED), (BOB,))
        after = self.memory.governed_recall(
            "shared credential rotation guidance",
            RecallContext(target_domain_refs=(SHARED,), principal_ref=ALICE, purpose="security-review"),
        )
        self.assertNotIn(fact_uuid, after.admitted)
        self.assertEqual(after.refusals[fact_uuid], "shared_space_non_member")
        record = self.memory.extension_state[SLOT]["changes"]["change:remove-alice"]
        self.assertEqual(record["pama_outcome"], policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertEqual(record["external_verification"]["verifier_principal_id"], "principal:security-admin")

    def test_self_verification_cannot_change_membership(self):
        proposal = _membership_proposal("proposal:membership:self", actor="principal:security-admin")
        result = commit_shared_domain_membership_change(
            self.memory,
            _remove_alice(),
            proposal,
            attestation=_attestation(proposal.proposal_id, verifier="principal:security-admin"),
        )
        self.assertFalse(result.committed)
        self.assertEqual(result.decision.outcome, policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertEqual(result.refusal, "attestation_self_verified")
        self.assertEqual(current_shared_domain_members(self.memory, SHARED), (ALICE, BOB))

    def test_weaker_target_or_authority_class_is_refused_before_mutation(self):
        weak_target = _membership_proposal("proposal:membership:weak-target", target_class=policy.M2)
        target_result = commit_shared_domain_membership_change(
            self.memory,
            _remove_alice("change:weak-target"),
            weak_target,
            attestation=_attestation(weak_target.proposal_id),
        )
        self.assertFalse(target_result.committed)
        self.assertEqual(target_result.refusal, "membership_change_requires_M5_target_class")

        weak_authority = _membership_proposal("proposal:membership:weak-authority", authority=policy.A1)
        authority_result = commit_shared_domain_membership_change(
            self.memory,
            _remove_alice("change:weak-authority"),
            weak_authority,
            attestation=_attestation(weak_authority.proposal_id),
        )
        self.assertFalse(authority_result.committed)
        self.assertEqual(authority_result.refusal, "membership_change_requires_A5_governance_authority")
        self.assertEqual(current_shared_domain_members(self.memory, SHARED), (ALICE, BOB))

    def test_domain_and_before_state_are_bound(self):
        wrong_domain = _membership_proposal("proposal:membership:wrong-domain", target=OTHER)
        domain_result = commit_shared_domain_membership_change(
            self.memory,
            _remove_alice("change:wrong-domain"),
            wrong_domain,
            attestation=_attestation(wrong_domain.proposal_id),
        )
        self.assertFalse(domain_result.committed)
        self.assertEqual(domain_result.refusal, "membership_domain_binding_mismatch")

        stale_change = SharedDomainMembershipChange(
            change_id="change:stale-members",
            domain_ref=SHARED,
            change_kind="remove",
            before_members=(ALICE, BOB, CAROL),
            after_members=(BOB, CAROL),
        )
        stale = _membership_proposal("proposal:membership:stale-members")
        stale_result = commit_shared_domain_membership_change(
            self.memory,
            stale_change,
            stale,
            attestation=_attestation(stale.proposal_id),
        )
        self.assertFalse(stale_result.committed)
        self.assertEqual(stale_result.refusal, "stale_membership_binding")
        self.assertEqual(current_shared_domain_members(self.memory, SHARED), (ALICE, BOB))

    def test_committed_change_and_replay_guard_survive_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = RestartSafeRuntime.create(tmp, tenant=TENANT, profile=PROFILE)
            bootstrap_shared_domain_members(runtime.adapter, SHARED, (ALICE, BOB))
            runtime.checkpoint()

            proposal = _membership_proposal("proposal:membership:restart")
            change = _remove_alice("change:restart")
            result = commit_shared_domain_membership_change(
                runtime.adapter,
                change,
                proposal,
                attestation=_attestation(proposal.proposal_id),
            )
            self.assertTrue(result.committed)
            runtime.checkpoint()

            restored = RestartSafeRuntime.recover(tmp, profile=PROFILE)
            self.assertEqual(current_shared_domain_members(restored.adapter, SHARED), (BOB,))
            self.assertIn("change:restart", restored.adapter.extension_state[SLOT]["changes"])

            replay = commit_shared_domain_membership_change(
                restored.adapter,
                change,
                proposal,
                attestation=_attestation(proposal.proposal_id),
            )
            self.assertFalse(replay.committed)
            self.assertEqual(replay.refusal, "membership_change_replay")
            self.assertEqual(current_shared_domain_members(restored.adapter, SHARED), (BOB,))


if __name__ == "__main__":
    unittest.main()
