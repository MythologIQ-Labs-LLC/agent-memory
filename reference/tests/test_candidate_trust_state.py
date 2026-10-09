"""#757 T01-T14: opaque independent compound-state regression candidates.

No protected R6/#732 case data, no inference/provider, no runtime mutation.
A positive local candidate is NEVER semantic identity or trust authority.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from hashlib import sha256
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentmem_ref.evaluation.candidate_trust_state import (
    MAX_PAGE_EVENTS, CandidateTrustState, TrustStateError,
    verify_trust_pages,
)
from agentmem_ref.evaluation.candidate_composition import (
    qualify_candidate_at_trust_state, recheck_candidate_head,
)
from agentmem_ref.evaluation.source_actor_witnesses import (
    WitnessExpectation, WitnessInput, sign_write_witness,
)
from agentmem_ref.memory.temporal_trust import public_key_digest
from tests.test_issuer_policy import IssuerPolicyTests


class SingleStateCandidateTests(unittest.TestCase):
    def setUp(self):
        parent = IssuerPolicyTests("test_exact_grant_is_mechanically_qualified_only")
        parent.setUp()
        self.publisher_key = parent.key
        self.signed_registry = parent.signed
        self.policy = parent.snapshot
        self.proposal = replace(
            parent.proposal,
            newer=replace(
                parent.proposal.newer,
                property_ref=parent.proposal.older.property_ref,
            ),
        )
        self.signers = tuple(
            Ed25519PrivateKey.from_private_bytes(bytes([i] * 32))
            for i in (0x71, 0x72, 0x74, 0x75)
        )
        self.ledger = CandidateTrustState("ledger:opaque-757", self.policy)

    def inputs_for(self, proposal=None):
        proposal = proposal or self.proposal
        witnesses = []
        for i, (side, role) in enumerate((
            ("older", "actor"), ("older", "source"),
            ("newer", "actor"), ("newer", "source"),
        )):
            obs = getattr(proposal, side)
            key = self.signers[i]
            principal = obs.actor_ref if role == "actor" else obs.source_ref
            key_ref = f"witness:{i}"
            signed = sign_write_witness(
                obs, side=side, role=role, claimed_principal_ref=principal,
                key_ref=key_ref, private_key=key,
            )
            pin = WitnessExpectation(
                side=side, role=role, expected_principal_ref=principal,
                expected_key_ref=key_ref,
                pinned_public_key_digest=public_key_digest(key.public_key()),
            )
            witnesses.append(WitnessInput(signed, key.public_key(), pin))
        return tuple(witnesses)

    def qualify(self, *, ledger=None, proposal=None, witnesses=None,
                head=None, sequence=None, registry=None):
        target = ledger or self.ledger
        p = proposal or self.proposal
        view = target.view().checkpoint
        return qualify_candidate_at_trust_state(
            target, p, registry or self.signed_registry,
            registry_public_key=self.publisher_key.public_key(),
            witnesses=witnesses if witnesses is not None else self.inputs_for(p),
            expected_current_head=head if head is not None else view.current_head,
            expected_sequence=sequence if sequence is not None else view.sequence,
        )

    def no_authority(self, result):
        self.assertFalse(result.issuer_authorized)
        self.assertFalse(result.principal_authenticated)
        self.assertFalse(result.origin_independence_verified)
        self.assertFalse(result.identity_verified)
        self.assertFalse(result.can_supersede)
        self.assertFalse(result.mutates_memory)
        self.assertEqual(result.authority_effect, "none")
        self.assertEqual(result.currentness, "not_established")

    def test_t01_same_head_baseline_is_mechanical_only(self):
        result = self.qualify()
        self.assertEqual(result.status, "mechanical_candidate")
        self.assertEqual(result.structural_status, "structurally_plausible_unverified")
        self.assertEqual(result.registry_status, "schema_candidate")
        self.assertEqual(result.policy_status, "policy_matched_candidate")
        self.assertEqual(result.witness_status, "cryptographic_witness_candidate")
        self.assertIn("current_anchor_authentication_not_established",
                      result.reason_codes)
        self.no_authority(result)

    def test_t01_old_snapshot_and_old_pin_cannot_qualify_at_new_head(self):
        original = self.ledger.view().checkpoint
        self.ledger.revoke_key(
            tenant_ref=self.proposal.older.tenant_ref,
            key_digest=public_key_digest(self.publisher_key.public_key()),
            expected_head=original.current_head,
        )
        stale = self.qualify(head=original.current_head, sequence=0)
        current = self.qualify()
        self.assertEqual(stale.status, "refused")
        self.assertIn("expected_current_trust_checkpoint_mismatch",
                      stale.reason_codes)
        self.assertEqual(current.status, "refused")
        self.assertIn("signing_key_revoked_at_checkpoint", current.reason_codes)
        self.no_authority(stale)
        self.no_authority(current)

    def test_t02_revocation_of_each_witness_key_and_schema_issuer_denies(self):
        keys = (self.publisher_key,) + self.signers
        for index, key in enumerate(keys):
            state = CandidateTrustState(f"ledger:each-{index}", self.policy)
            initial = state.view().checkpoint
            state.revoke_key(
                tenant_ref=self.proposal.older.tenant_ref,
                key_digest=public_key_digest(key.public_key()),
                expected_head=initial.current_head,
            )
            result = self.qualify(ledger=state)
            self.assertEqual(result.status, "refused", msg=index)
            self.assertIn("signing_key_revoked_at_checkpoint", result.reason_codes)
            self.no_authority(result)

    def test_t03_revoked_key_beats_unmapped_property_abstention(self):
        old = self.ledger.view().checkpoint
        self.ledger.revoke_key(
            tenant_ref=self.proposal.older.tenant_ref,
            key_digest=public_key_digest(self.signers[2].public_key()),
            expected_head=old.current_head,
        )
        variant = replace(
            self.proposal, newer=replace(
                self.proposal.newer, property_ref="field:unmapped-757",
            ),
        )
        result = self.qualify(proposal=variant)
        self.assertEqual(result.status, "refused")
        self.assertIn("signing_key_revoked_at_checkpoint", result.reason_codes)
        self.no_authority(result)

    def test_t04_digest_binds_proposal_and_signed_witnesses(self):
        initial = self.qualify()
        self.assertEqual(initial, self.qualify())
        alt = replace(self.proposal, newer=replace(
            self.proposal.newer, value_ref="opaque:different-revision",
        ))
        changed = self.qualify(proposal=alt)
        self.assertNotEqual(initial.proposal_digest, changed.proposal_digest)
        self.assertNotEqual(initial.record_digest, changed.record_digest)
        witnesses = self.inputs_for()
        altered = replace(witnesses[0].signed, signature_b64="AAAA")
        modified = self.qualify(witnesses=(
            replace(witnesses[0], signed=altered),
        ) + witnesses[1:])
        self.assertNotEqual(initial.evidence_digest, modified.evidence_digest)
        self.assertNotEqual(initial.record_digest, modified.record_digest)
        self.assertEqual(modified.status, "refused")
        self.no_authority(modified)

    def test_t05_different_subject_or_property_remains_underdetermined(self):
        for field, value in (
            ("property_ref", "field:current-phase"),
            ("subject_ref", "subject:other-alias"),
            ("source_ref", "source:other-origin"),
        ):
            variant = replace(self.proposal, newer=replace(
                self.proposal.newer, **{field: value},
            ))
            result = self.qualify(proposal=variant)
            self.assertEqual(result.status, "abstain", msg=field)
            self.assertEqual(result.structural_status, "underdetermined")
            self.assertIn("structural_preflight_underdetermined",
                          result.reason_codes)
            self.no_authority(result)

    def test_t06_distinct_active_property_refused_unknown_label_abstains(self):
        different = replace(self.proposal, newer=replace(
            self.proposal.newer, property_ref="field:priority",
        ))
        v = self.qualify(proposal=different)
        self.assertEqual(v.status, "refused")
        self.assertIn("explicit_distinct_property_refusal", v.reason_codes)
        unknown = replace(self.proposal, newer=replace(
            self.proposal.newer, property_ref="field:truly-unknown",
        ))
        u = self.qualify(proposal=unknown)
        self.assertEqual(u.status, "abstain")
        self.no_authority(v)
        self.no_authority(u)

    def test_t07_structural_denial_dominates_all_signatures(self):
        p = replace(self.proposal, newer=replace(
            self.proposal.newer, tenant_ref="tenant:outside",
        ))
        v = self.qualify(proposal=p)
        self.assertEqual(v.status, "refused")
        self.assertIn("structural_preflight_refused", v.reason_codes)
        self.no_authority(v)

    def test_t08_ninety_denials_cross_bounded_pages_and_replay(self):
        original = self.ledger.view().checkpoint
        head = original.current_head
        for i in range(90):
            key = "sha256:" + sha256(f"synthetic-key-{i}".encode()).hexdigest()
            event = self.ledger.revoke_key(
                tenant_ref=self.proposal.older.tenant_ref,
                key_digest=key, expected_head=head,
            )
            head = event.head_digest
        report = self.ledger.view().checkpoint
        self.assertEqual(report.sequence, 90)
        self.assertEqual(report.denied_key_count, 90)
        self.assertEqual(report.page_count, 6)
        pages = self.ledger.pages()
        self.assertEqual(tuple(len(p.events) for p in pages),
                         (16, 16, 16, 16, 16, 10))
        verification = verify_trust_pages(
            "ledger:opaque-757", self.policy, pages,
            expected_current_head=report.current_head, expected_sequence=90,
        )
        self.assertEqual(verification.status, "mechanical_match")
        self.assertFalse(verification.externally_authenticated)
        self.assertFalse(verification.mutates_memory)
        self.assertEqual(self.qualify().status, "mechanical_candidate")

    def test_t09_page_tampering_reorder_and_bad_pin_fail_closed(self):
        head = self.ledger.view().checkpoint.current_head
        for i in range(18):
            event = self.ledger.revoke_key(
                tenant_ref="tenant:isolated",
                key_digest="sha256:" + sha256(f"synthetic:{i}".encode()).hexdigest(),
                expected_head=head,
            )
            head = event.head_digest
        pages = self.ledger.pages()
        current = self.ledger.view().checkpoint
        bad = (
            tuple(reversed(pages)),
            pages[:-1],
            (replace(pages[0], end_head=current.genesis_head), pages[1]),
        )
        for parts in bad:
            check = verify_trust_pages(
                "ledger:opaque-757", self.policy, parts,
                expected_current_head=current.current_head,
                expected_sequence=current.sequence,
            )
            self.assertNotEqual(check.status, "mechanical_match")
        stale = verify_trust_pages(
            "ledger:opaque-757", self.policy, pages,
            expected_current_head=current.genesis_head,
            expected_sequence=current.sequence,
        )
        self.assertEqual(stale.status, "pin_mismatch")

    def test_t10_candidate_recheck_invalidated_by_new_checkpoint(self):
        v = self.qualify()
        origin = self.ledger.view().checkpoint
        still = recheck_candidate_head(
            v, self.ledger, expected_current_head=origin.current_head,
        )
        self.assertEqual(still.status, "same_local_checkpoint")
        self.ledger.invalidate_schema_revision(
            tenant_ref="tenant:isolated",
            schema_ref="schema:unrelated", registry_revision_ref="revision:unrelated",
            expected_head=origin.current_head,
        )
        stale = recheck_candidate_head(
            v, self.ledger,
            expected_current_head=self.ledger.view().checkpoint.current_head,
        )
        self.assertEqual(stale.status, "stale_receipt")
        current = self.qualify()
        self.assertNotEqual(current.trust_checkpoint, v.trust_checkpoint)
        self.no_authority(current)

    def test_t11_alternate_history_own_pins_remains_untrusted(self):
        alt = CandidateTrustState("ledger:attacker-owned", self.policy)
        initial = alt.view().checkpoint
        alt.revoke_key(
            tenant_ref="tenant:isolated",
            key_digest="sha256:" + sha256(b"attacker-marker").hexdigest(),
            expected_head=initial.current_head,
        )
        checkpoint = alt.view().checkpoint
        result = verify_trust_pages(
            "ledger:attacker-owned", self.policy, alt.pages(),
            expected_current_head=checkpoint.current_head,
            expected_sequence=checkpoint.sequence,
        )
        self.assertEqual(result.status, "mechanical_match")
        self.assertFalse(result.externally_authenticated)

    def test_t14_concurrent_head_conflict_allows_one_append(self):
        origin = self.ledger.view().checkpoint
        def write_one(index):
            key = "sha256:" + sha256(f"concurrent-{index}".encode()).hexdigest()
            try:
                self.ledger.revoke_key(
                    tenant_ref="tenant:isolated", key_digest=key,
                    expected_head=origin.current_head,
                )
                return "appended"
            except TrustStateError:
                return "stale"
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(write_one, range(8)))
        self.assertEqual(results.count("appended"), 1)
        self.assertEqual(results.count("stale"), 7)

    def test_t14_mutable_report_alias_cannot_rewrite_internal_state(self):
        baseline = self.ledger.view()
        pages_before = self.ledger.pages()
        object.__setattr__(baseline.policy_snapshot, "policy_ref", "policy:forged")
        current = self.ledger.view()
        self.assertEqual(current.policy_snapshot.policy_ref, "policy:domain-owner")
        self.assertEqual(current.checkpoint, baseline.checkpoint)
        self.assertEqual(self.ledger.pages(), pages_before)

    def test_policy_publishing_does_not_preserve_old_local_candidate(self):
        before = self.ledger.view().checkpoint
        updated = replace(self.policy, revision_ref="policy-revision:11")
        self.ledger.publish_policy(updated, expected_head=before.current_head)
        self.assertEqual(
            self.qualify(head=before.current_head, sequence=0).status, "refused"
        )
        self.assertEqual(self.qualify().status, "mechanical_candidate")
        checkpoint = self.ledger.view().checkpoint
        with self.assertRaises(TrustStateError):
            self.ledger.publish_policy(self.policy, expected_head=checkpoint.current_head)

    def test_schema_revocation_overrides_missing_mapping(self):
        initial = self.ledger.view().checkpoint
        self.ledger.invalidate_schema_revision(
            tenant_ref="tenant:isolated",
            schema_ref="schema:owner-vocabulary",
            registry_revision_ref="revision:schema-17",
            expected_head=initial.current_head,
        )
        result = self.qualify()
        self.assertEqual(result.status, "refused")
        self.assertIn("schema_revision_invalidated_at_checkpoint", result.reason_codes)
        self.no_authority(result)


if __name__ == "__main__":
    unittest.main()
