"""Authority tests for governed shared-domain membership mutation (#364)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import policy  # noqa: E402
from agentmem_ref.adapter import Clock, GovernedMemoryAdapter  # noqa: E402
from agentmem_ref.runtime.shared_membership import (  # noqa: E402
    SLOT,
    SharedMembershipChange,
    change_shared_domain_membership,
    membership_state,
)
from agentmem_ref.substrate import InMemoryTemporalGraph  # noqa: E402
from tests.qualified_fixtures import attestation_for, corpus_for, registry_for, rule  # noqa: E402

DOMAIN = "domain:shared-security"


def _corpus(to_members: tuple[str, ...] = ("user:alice",)):
    return corpus_for(
        rule(
            rule_id="rule:shared-membership-revocation",
            target=DOMAIN,
            criterion="shared-membership-authority",
            from_state=membership_state(("user:alice", "user:bob")),
            to_values=(membership_state(to_members),),
        )
    )


def _proposal(**overrides) -> policy.Proposal:
    base = dict(
        proposal_id="membership-change-1",
        actor_id="agent:security-admin",
        charter_version="charter-1",
        target_reference=DOMAIN,
        target_class=policy.M5,
        scope="tenant-a",
        operation="authority_change",
        current_strength="promoted",
        proposed_strength="promoted",
        downstream_authority=policy.A5,
        reversibility="reversible",
        risk_class="high",
        evidence_refs=("evidence:shared-membership-rule",),
        tenant_ref="tenant-a",
        purpose="shared-domain-revocation",
        state_snapshot="v0",
    )
    base.update(overrides)
    return policy.Proposal(**base)


def _change(**overrides) -> SharedMembershipChange:
    base = dict(
        domain_ref=DOMAIN,
        expected_members=("user:alice", "user:bob"),
        resulting_members=("user:alice",),
        reason="revoke user:bob from the shared security domain",
    )
    base.update(overrides)
    return SharedMembershipChange(**base)


class SharedMembershipAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = _corpus()
        self.adapter = GovernedMemoryAdapter(
            InMemoryTemporalGraph(),
            tenant="tenant-a",
            clock=Clock(),
            verifier_registry=registry_for(self.corpus),
        )
        # Bootstrap belongs to the embedding host. Runtime replacement is what
        # this authority path governs.
        self.adapter.set_shared_domain_members(DOMAIN, ("user:alice", "user:bob"))

    def _evidence(self, *, proposed: tuple[str, ...] = ("user:alice",)):
        return self.corpus.evidence_for(
            target_reference=DOMAIN,
            criterion="shared-membership-authority",
            pre_state=membership_state(("user:alice", "user:bob")),
            proposed_value=membership_state(proposed),
        )

    def _commit(self, proposal=None, change=None, evidence=None, attestation=None):
        proposal = proposal or _proposal()
        if evidence is None:
            evidence = self._evidence()
        if attestation is None:
            attestation = attestation_for(proposal, principal="human:security-owner")
        return change_shared_domain_membership(
            self.adapter,
            change or _change(),
            proposal,
            evidence=evidence,
            attestation=attestation,
        )

    def test_verified_evidence_plus_external_authority_commits_exact_membership(self):
        result = self._commit()

        self.assertTrue(result.committed)
        self.assertEqual(result.decision.outcome, policy.ALLOW_WITH_LEDGER)
        self.assertEqual(result.before_members, ("user:alice", "user:bob"))
        self.assertEqual(result.after_members, ("user:alice",))
        self.assertEqual(self.adapter._shared_domain_members[DOMAIN], {"user:alice"})

        slot = self.adapter.extension_state[SLOT]
        self.assertEqual(slot["versions"][DOMAIN], 1)
        event_id = slot["proposals"]["membership-change-1"]
        record = slot["transitions"][event_id]
        self.assertEqual(record["before_state"], "v0")
        self.assertEqual(record["after_state"], "v1")
        self.assertEqual(record["verifier_principal_id"], "human:security-owner")
        self.assertEqual(record["authority_kind"], policy.HUMAN_CONFIRMATION)

    def test_attestation_is_required_independently_of_good_evidence(self):
        proposal = _proposal()
        result = change_shared_domain_membership(
            self.adapter,
            _change(),
            proposal,
            evidence=self._evidence(),
            attestation=None,
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.decision.outcome, policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertEqual(self.adapter._shared_domain_members[DOMAIN], {"user:alice", "user:bob"})

    def test_evidence_is_required_independently_of_good_attestation(self):
        proposal = _proposal()
        result = change_shared_domain_membership(
            self.adapter,
            _change(),
            proposal,
            evidence=(),
            attestation=attestation_for(proposal, principal="human:security-owner"),
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "membership_evidence_class_insufficient")
        self.assertEqual(self.adapter._shared_domain_members[DOMAIN], {"user:alice", "user:bob"})

    def test_caller_authored_or_mismatched_transition_does_not_become_evidence(self):
        result = self._commit(
            change=_change(resulting_members=("user:mallory",)),
            evidence=self._evidence(proposed=("user:alice",)),
        )

        self.assertFalse(result.committed)
        self.assertEqual(self.adapter._shared_domain_members[DOMAIN], {"user:alice", "user:bob"})

    def test_exact_prior_membership_is_an_optimistic_concurrency_guard(self):
        result = self._commit(
            change=_change(expected_members=("user:alice",)),
        )

        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "stale_membership_binding")
        self.assertNotIn(SLOT, self.adapter.extension_state)

    def test_membership_proposal_requires_authority_change_a5_and_domain_binding(self):
        wrong_operation = self._commit(proposal=_proposal(operation="scope_expansion"))
        self.assertFalse(wrong_operation.committed)
        self.assertEqual(wrong_operation.refusal, "membership_requires_authority_change")

        wrong_authority = self._commit(proposal=_proposal(downstream_authority=policy.A4))
        self.assertFalse(wrong_authority.committed)
        self.assertEqual(wrong_authority.refusal, "membership_requires_a5_authority")

        wrong_target_proposal = _proposal(target_reference="domain:elsewhere")
        wrong_target = change_shared_domain_membership(
            self.adapter,
            _change(),
            wrong_target_proposal,
            evidence=self._evidence(),
            attestation=attestation_for(wrong_target_proposal),
        )
        self.assertFalse(wrong_target.committed)
        self.assertEqual(wrong_target.refusal, "membership_target_binding_mismatch")

    def test_state_snapshot_and_proposal_are_single_use(self):
        first = self._commit()
        self.assertTrue(first.committed)

        replay_proposal = _proposal()
        replay = change_shared_domain_membership(
            self.adapter,
            SharedMembershipChange(
                domain_ref=DOMAIN,
                expected_members=("user:alice",),
                resulting_members=("user:alice", "user:carol"),
                reason="attempt replay",
            ),
            replay_proposal,
            evidence=(),
            attestation=attestation_for(replay_proposal),
        )
        self.assertFalse(replay.committed)
        self.assertEqual(replay.refusal, "membership_authority_replay")
        self.assertEqual(self.adapter._shared_domain_members[DOMAIN], {"user:alice"})

        fresh_proposal = _proposal(
            proposal_id="membership-change-2",
            state_snapshot="v0",
        )
        stale = change_shared_domain_membership(
            self.adapter,
            SharedMembershipChange(
                domain_ref=DOMAIN,
                expected_members=("user:alice",),
                resulting_members=("user:alice", "user:carol"),
                reason="stale snapshot",
            ),
            fresh_proposal,
            evidence=(),
            attestation=attestation_for(fresh_proposal),
        )
        self.assertFalse(stale.committed)
        self.assertEqual(stale.refusal, "stale_authorization")


if __name__ == "__main__":
    unittest.main()
