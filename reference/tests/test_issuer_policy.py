"""#757 J42-J56: independent synthetic issuer-policy adversarial controls.

No textual benchmark data, no runtime writes, no provider calls, no asserted
population score. Passing policy checks never implies trusted identity authority.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentmem_ref.evaluation.issuer_policy import (
    IssuerGrant, IssuerPolicyError, IssuerPolicySnapshot,
    policy_digest, qualify_issuer_policy,
)
from agentmem_ref.evaluation.property_registry import sign_registry
from agentmem_ref.memory.temporal_trust import public_key_digest
from tests.test_property_registry import registry
from tests.test_proposition_link_preflight import proposed, write


class IssuerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.from_private_bytes(bytes([0x73] * 32))
        self.attacker = Ed25519PrivateKey.from_private_bytes(bytes([0x21] * 32))
        self.registry = registry()
        self.signed = sign_registry(self.registry, private_key=self.key)
        self.proposal = proposed(
            older=write(fact="fact:old", revision="revision:old",
                        prop="property:status-7", value="opaque:alpha"),
            newer=write(fact="fact:new", revision="revision:new",
                        prop="field:current-phase", value="opaque:beta"),
        )
        self.grant = IssuerGrant(
            schema_ref="schema:owner-vocabulary",
            registry_revision_ref="revision:schema-17",
            tenant_ref="tenant:isolated",
            scope_ref="scope:program",
            purpose_ref="purpose:task",
            issuer_key_ref="key:owner-publisher",
            public_key_digest=public_key_digest(self.key.public_key()),
        )
        self.snapshot = IssuerPolicySnapshot(
            policy_ref="policy:domain-owner",
            revision_ref="policy-revision:10",
            grants=(self.grant,),
        )

    def check(self, *, snapshot=None, pin=None, public_key=None,
              proposal=None, signed=None, **expectations):
        snap = snapshot if snapshot is not None else self.snapshot
        key = public_key if public_key is not None else self.key.public_key()
        kwargs = dict(
            expected_policy_ref="policy:domain-owner",
            expected_policy_revision_ref="policy-revision:10",
            expected_issuer_key_ref="key:owner-publisher",
            expected_schema_ref="schema:owner-vocabulary",
            expected_revision_ref="revision:schema-17",
            expected_tenant_ref="tenant:isolated",
            expected_scope_ref="scope:program",
            expected_purpose_ref="purpose:task",
        )
        kwargs.update(expectations)
        return qualify_issuer_policy(
            self.proposal if proposal is None else proposal,
            self.signed if signed is None else signed,
            public_key=key,
            snapshot=snap,
            expected_policy_digest=policy_digest(snap) if pin is None else pin,
            **kwargs,
        )

    def no_authority(self, result):
        self.assertFalse(result.issuer_authorized)
        self.assertFalse(result.identity_verified)
        self.assertFalse(result.can_supersede)
        self.assertFalse(result.mutates_memory)
        self.assertEqual(result.authority_effect, "none")
        self.assertEqual(result.integration_state, "evaluation_only")

    def test_exact_grant_is_mechanically_qualified_only(self):
        r = self.check()
        self.assertEqual(r.status, "policy_matched_candidate")
        self.assertEqual(r.registry_status, "schema_candidate")
        self.assertTrue(r.policy_pin_matches)
        self.assertTrue(r.policy_context_matches)
        self.assertTrue(r.grant_matched)
        self.assertEqual(r.declared_property_ref, "canonical:phase")
        self.assertIn("policy_distribution_and_issuer_legitimacy_not_authenticated",
                      r.reason_codes)
        self.no_authority(r)

    def test_missing_grant_abstains_without_fallback(self):
        empty = replace(self.snapshot, grants=())
        r = self.check(snapshot=empty)
        self.assertEqual(r.status, "abstain")
        self.assertIn("no_exact_issuer_grant", r.reason_codes)
        self.no_authority(r)

    def test_grant_wrong_issuer_and_key_refused(self):
        for changes in (
            {"issuer_key_ref": "key:other"},
            {"public_key_digest": public_key_digest(self.attacker.public_key())},
        ):
            modified = replace(self.grant, **changes)
            r = self.check(snapshot=replace(self.snapshot, grants=(modified,)))
            self.assertEqual(r.status, "refused")
            self.assertIn("grant_key_or_issuer_mismatch", r.reason_codes)
            self.no_authority(r)

    def test_revoked_grant_always_refuses(self):
        snap = replace(self.snapshot, grants=(replace(self.grant, state="revoked"),))
        r = self.check(snapshot=snap)
        self.assertEqual(r.status, "refused")
        self.assertIn("issuer_grant_revoked", r.reason_codes)
        self.assertTrue(r.grant_matched)
        self.no_authority(r)

    def test_revoked_key_overrides_active_matching_grant(self):
        snap = replace(self.snapshot, revoked_key_digests=(self.grant.public_key_digest,))
        r = self.check(snapshot=snap)
        self.assertEqual(r.status, "refused")
        self.assertIn("issuer_key_revoked", r.reason_codes)
        self.no_authority(r)

    def test_invalidated_registry_revision_overrides_valid_signed_registry(self):
        snap = replace(self.snapshot, invalidated_registry_revisions=(
            ("schema:owner-vocabulary", "revision:schema-17"),
        ))
        r = self.check(snapshot=snap)
        self.assertEqual(r.status, "refused")
        self.assertIn("registry_revision_invalidated", r.reason_codes)
        self.no_authority(r)

    def test_stale_out_of_band_pin_refuses_changed_revocation(self):
        old_pin = policy_digest(self.snapshot)
        snap = replace(self.snapshot, revision_ref="policy-revision:11",
                       revoked_key_digests=(self.grant.public_key_digest,))
        r = self.check(snapshot=snap, pin=old_pin)
        self.assertEqual(r.status, "refused")
        self.assertIn("independent_policy_digest_mismatch", r.reason_codes)
        self.assertIn("independent_policy_context_mismatch", r.reason_codes)
        self.no_authority(r)

    def test_policy_identity_revision_or_digest_mismatch_refused(self):
        for expected in (
            {"expected_policy_ref": "policy:fake"},
            {"expected_policy_revision_ref": "policy-revision:9"},
        ):
            r = self.check(**expected)
            self.assertEqual(r.status, "refused")
            self.no_authority(r)
        r = self.check(pin=policy_digest(replace(self.snapshot, policy_ref="policy:other")))
        self.assertEqual(r.status, "refused")
        self.assertFalse(r.policy_pin_matches)
        self.no_authority(r)

    def test_attacker_controls_signed_registry_policy_and_pin(self):
        # A self-issued and self-pinned forged configuration remains untrusted
        # EVEN when all local cryptographic and policy checks match.
        forged = replace(self.registry, issuer_key_ref="key:owner-publisher")
        attacker_grant = replace(
            self.grant, public_key_digest=public_key_digest(self.attacker.public_key())
        )
        attacker_policy = replace(self.snapshot, grants=(attacker_grant,))
        r = self.check(snapshot=attacker_policy,
                       signed=sign_registry(forged, private_key=self.attacker),
                       public_key=self.attacker.public_key())
        self.assertEqual(r.status, "policy_matched_candidate")
        self.no_authority(r)

    def test_wrong_signed_key_refuses_through_registry_gate(self):
        r = self.check(public_key=self.attacker.public_key())
        self.assertEqual(r.status, "refused")
        self.assertIn("registry_or_structural_refusal", r.reason_codes)
        self.no_authority(r)

    def test_cross_tenant_and_subject_and_cardinality_cannot_pass(self):
        for changed in (
            {"tenant_ref": "tenant:other"},
            {"scope_ref": "scope:other"},
            {"purpose_ref": "purpose:other"},
            {"subject_ref": "subject:other"},
            {"cardinality": "multi"},
            {"coexistent": True},
        ):
            changed_proposal = replace(
                self.proposal,
                newer=replace(self.proposal.newer, **changed),
            )
            r = self.check(proposal=changed_proposal)
            self.assertEqual(r.status, "refused")
            self.no_authority(r)

    def test_same_value_never_becomes_a_new_state(self):
        p = replace(self.proposal, newer=replace(
            self.proposal.newer, value_ref=self.proposal.older.value_ref
        ))
        r = self.check(proposal=p)
        self.assertEqual(r.status, "refused")
        self.no_authority(r)

    def test_registry_unmapped_label_does_not_use_policy_to_guess(self):
        p = replace(self.proposal, newer=replace(
            self.proposal.newer, property_ref="field:near-miss"
        ))
        r = self.check(proposal=p)
        self.assertEqual(r.status, "abstain")
        self.assertIn("schema_candidate_not_established", r.reason_codes)
        self.no_authority(r)

    def test_scope_grants_must_be_exact_unique_sorted(self):
        with self.assertRaises(IssuerPolicyError):
            replace(self.snapshot, grants=(self.grant, self.grant))
        second = replace(self.grant, schema_ref="schema:zz")
        with self.assertRaises(IssuerPolicyError):
            replace(self.snapshot, grants=(second, self.grant))
        with self.assertRaises(IssuerPolicyError):
            replace(self.snapshot, revoked_key_digests=(
                self.grant.public_key_digest, self.grant.public_key_digest,
            ))
        with self.assertRaises(IssuerPolicyError):
            replace(self.snapshot, invalidated_registry_revisions=(
                ("schema:a", "revision:z"), ("schema:a", "revision:z"),
            ))

    def test_digest_is_stable_and_binds_all_revocations_and_keys(self):
        first = policy_digest(self.snapshot)
        self.assertEqual(first, policy_digest(self.snapshot))
        changes = (
            replace(self.snapshot, policy_ref="policy:other"),
            replace(self.snapshot, revision_ref="policy-revision:11"),
            replace(self.snapshot, grants=(replace(self.grant, state="revoked"),)),
            replace(self.snapshot, grants=(replace(self.grant,
                public_key_digest=public_key_digest(self.attacker.public_key())),)),
            replace(self.snapshot,
                invalidated_registry_revisions=(("schema:a", "revision:1"),)),
            replace(self.snapshot,
                revoked_key_digests=(self.grant.public_key_digest,)),
        )
        for changed in changes:
            self.assertNotEqual(first, policy_digest(changed))

    def test_immutable_receipt_and_policy_shape(self):
        r = self.check()
        with self.assertRaises(FrozenInstanceError):
            r.status = "refused"
        with self.assertRaises(FrozenInstanceError):
            self.snapshot.policy_ref = "policy:other"
        self.no_authority(self.check())


    def test_d1_revoked_key_denies_even_when_schema_layer_abstains(self):
        unmapped = replace(self.proposal, newer=replace(
            self.proposal.newer, property_ref="field:unmapped-q757"
        ))
        denied = replace(
            self.snapshot,
            revoked_key_digests=(self.grant.public_key_digest,),
        )
        result = self.check(snapshot=denied, proposal=unmapped)
        self.assertEqual(result.registry_status, "abstain")
        self.assertEqual(result.status, "refused")
        self.assertIn("issuer_key_revoked", result.reason_codes)
        self.no_authority(result)

    def test_d1_invalidated_schema_denies_even_when_registry_abstains(self):
        unmapped = replace(self.proposal, newer=replace(
            self.proposal.newer, property_ref="field:unmapped-q757"
        ))
        denied = replace(self.snapshot, invalidated_registry_revisions=(
            ("schema:owner-vocabulary", "revision:schema-17"),
        ))
        result = self.check(snapshot=denied, proposal=unmapped)
        self.assertEqual(result.registry_status, "abstain")
        self.assertEqual(result.status, "refused")
        self.assertIn("registry_revision_invalidated", result.reason_codes)
        self.no_authority(result)

    def test_d8_policy_size_bound_enforced_at_construction(self):
        # Individually valid, sorted, distinct scopes still exceed 16 KiB.
        grants = tuple(replace(
            self.grant,
            schema_ref="schema:" + "s" * 190,
            registry_revision_ref="revision:" + "r" * 180,
            tenant_ref="tenant:" + "t" * 190,
            scope_ref=f"scope:{i:03d}:" + "c" * 180,
            purpose_ref="purpose:" + "p" * 190,
            issuer_key_ref="issuer:" + "i" * 190,
        ) for i in range(32))
        with self.assertRaisesRegex(IssuerPolicyError, "size bound"):
            replace(self.snapshot, grants=grants)



if __name__ == "__main__":
    unittest.main()
