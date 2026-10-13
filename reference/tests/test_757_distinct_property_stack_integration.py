"""#757/#766: original-registry negative identity through the stacked trust state.

These tests are authored BEFORE the #766 source is applied to the #767 stack.
All identities, keys and values are synthetic. No lifecycle or memory API is called.
"""
from __future__ import annotations

from dataclasses import replace
import unittest

from agentmem_ref.evaluation.property_registry import (
    qualify_property_link, sign_registry,
)
from agentmem_ref.memory.temporal_trust import public_key_digest
from tests.test_candidate_trust_state import SingleStateCandidateTests
from tests.test_issuer_policy import IssuerPolicyTests


class DistinctPropertyStackIntegration(unittest.TestCase):
    def setUp(self):
        issuer = IssuerPolicyTests("test_exact_grant_is_mechanically_qualified_only")
        issuer.setUp()
        self.issuer = issuer
        stack = SingleStateCandidateTests("test_t01_same_head_baseline_is_mechanical_only")
        stack.setUp()
        self.stack = stack

    def issuer_variant(self, label):
        return replace(
            self.issuer.proposal,
            newer=replace(self.issuer.proposal.newer, property_ref=label),
        )

    def composite_variant(self, label):
        return replace(
            self.stack.proposal,
            newer=replace(self.stack.proposal.newer, property_ref=label),
        )

    def registry_check(self, proposal, *, signed=None):
        reg = self.issuer.registry
        key = self.issuer.key.public_key()
        return qualify_property_link(
            proposal, self.issuer.signed if signed is None else signed,
            public_key=key, pinned_public_key_digest=public_key_digest(key),
            expected_issuer_key_ref=reg.issuer_key_ref,
            expected_schema_ref=reg.schema_ref,
            expected_revision_ref=reg.revision_ref,
            expected_tenant_ref=reg.tenant_ref,
            expected_scope_ref=reg.scope_ref,
            expected_purpose_ref=reg.purpose_ref,
        )

    def no_authority(self, verdict):
        for field in ("issuer_authorized", "identity_verified", "can_supersede",
                      "mutates_memory"):
            self.assertIs(getattr(verdict, field), False, field)
        self.assertEqual(verdict.authority_effect, "none")

    def test_distinct_active_mapped_property_is_refusal_at_all_three_layers(self):
        proposed = self.issuer_variant("field:priority")
        registry = self.registry_check(proposed)
        policy = self.issuer.check(proposal=proposed)
        composite = self.stack.qualify(
            proposal=self.composite_variant("field:priority"),
        )
        self.assertEqual(registry.status, "refused")
        self.assertEqual(policy.status, "refused")
        self.assertEqual(policy.registry_status, "refused")
        self.assertEqual(composite.status, "refused")
        self.assertEqual(composite.registry_status, "refused")
        self.assertEqual(composite.policy_status, "refused")
        self.assertIn("schema_declares_different_properties", registry.reason_codes)
        self.assertIn("schema_declares_different_properties", policy.reason_codes)
        self.assertIn("explicit_distinct_property_refusal", composite.reason_codes)
        self.assertTrue(registry.signature_valid)
        self.assertTrue(registry.key_pin_matches)
        self.assertTrue(policy.policy_pin_matches)
        for result in (registry, policy, composite):
            self.no_authority(result)

    def test_truly_unknown_property_abstains_through_every_layer(self):
        label = "field:unseen-novel-property"
        registry = self.registry_check(self.issuer_variant(label))
        policy = self.issuer.check(proposal=self.issuer_variant(label))
        composite = self.stack.qualify(proposal=self.composite_variant(label))
        self.assertEqual(registry.status, "abstain")
        self.assertEqual(policy.status, "abstain")
        self.assertEqual(composite.status, "abstain")
        self.assertIn("schema_label_unmapped", registry.reason_codes)
        self.assertNotIn("explicit_distinct_property_refusal", composite.reason_codes)
        for result in (registry, policy, composite):
            self.no_authority(result)

    def test_exact_active_shared_property_is_candidate_only_not_truth(self):
        registry = self.registry_check(self.issuer.proposal)
        policy = self.issuer.check()
        composite = self.stack.qualify()
        self.assertEqual(registry.status, "schema_candidate")
        self.assertEqual(policy.status, "policy_matched_candidate")
        self.assertEqual(composite.status, "mechanical_candidate")
        self.assertIn(
            "current_anchor_authentication_not_established",
            composite.reason_codes,
        )
        for result in (registry, policy, composite):
            self.no_authority(result)

    def test_inactive_property_is_not_misreported_as_distinct_active(self):
        reg = replace(
            self.issuer.registry,
            properties=(
                replace(self.issuer.registry.properties[0], state="retired"),
                self.issuer.registry.properties[1],
            ),
        )
        signed = sign_registry(reg, private_key=self.issuer.key)
        proposal = self.issuer_variant("field:priority")
        verdict = self.registry_check(proposal, signed=signed)
        policy = self.issuer.check(proposal=proposal, signed=signed)
        self.assertEqual(verdict.status, "abstain")
        self.assertEqual(policy.status, "abstain")
        self.assertIn("property_not_active", verdict.reason_codes)
        self.assertNotIn("schema_declares_different_properties", verdict.reason_codes)
        self.no_authority(verdict)
        self.no_authority(policy)

    def test_revoked_witness_key_still_refuses_with_distinct_schema(self):
        proposed = self.composite_variant("field:priority")
        initial = self.stack.ledger.view().checkpoint
        key = self.stack.signers[0].public_key()
        self.stack.ledger.revoke_key(
            tenant_ref=proposed.older.tenant_ref,
            key_digest=public_key_digest(key),
            expected_head=initial.current_head,
        )
        result = self.stack.qualify(proposal=proposed)
        self.assertEqual(result.status, "refused")
        self.assertIn("signing_key_revoked_at_checkpoint", result.reason_codes)
        self.assertIn("explicit_distinct_property_refusal", result.reason_codes)
        self.no_authority(result)

    def test_same_scope_structural_refusal_is_not_downgraded(self):
        proposed = replace(
            self.issuer_variant("field:priority"),
            newer=replace(
                self.issuer_variant("field:priority").newer,
                tenant_ref="tenant:other",
            ),
        )
        result = self.issuer.check(proposal=proposed)
        self.assertEqual(result.status, "refused")
        self.assertIn("registry_or_structural_refusal", result.reason_codes)
        self.no_authority(result)


if __name__ == "__main__":
    unittest.main()
