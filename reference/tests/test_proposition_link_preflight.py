"""#757 structural identity-link falsifiers; independent of #732 text corpora.

No training examples, no gold semantic equivalence, no runtime integration,
no provider credentials, no scorer and no claim about population prevalence.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import random
import unittest

from agentmem_ref.evaluation.proposition_link_preflight import (
    ClaimOfIdentity,
    IdentityPreflight,
    ObservedWrite,
    ProposedIdentityLink,
    preflight,
)


def write(*, revision: str, fact: str, value: str = "opaque:value-v1",
          subject: str = "subject:stable-23", prop: str = "property:status-7",
          **updates) -> ObservedWrite:
    base = dict(
        fact_ref=fact, revision_ref=revision, tenant_ref="tenant:isolated",
        scope_ref="scope:program", purpose_ref="purpose:task",
        actor_ref="actor:owner", source_ref="source:owner",
        subject_ref=subject, property_ref=prop, value_ref=value,
        cardinality="single", lifecycle_state="active", coexistent=False,
    )
    base.update(updates)
    return ObservedWrite(**base)


def claims() -> tuple[ClaimOfIdentity, ...]:
    return (
        ClaimOfIdentity("evidence:one", "invocation:1", "source:one", "schema_claim"),
        ClaimOfIdentity("evidence:two", "invocation:2", "source:two", "signature_claim"),
    )


def proposed(**updates) -> ProposedIdentityLink:
    default = dict(
        older=write(revision="revision:old", fact="fact:old"),
        newer=write(revision="revision:new", fact="fact:new",
                    value="opaque:value-v2"),
        expected_head_ref="head:old", observed_head_ref="head:old",
        claims=claims(),
    )
    default.update(updates)
    return ProposedIdentityLink(**default)


class PropositionLinkSafetyTests(unittest.TestCase):
    def assert_no_authority(self, outcome: IdentityPreflight) -> None:
        self.assertEqual(outcome.authority_effect, "none")
        self.assertFalse(outcome.identity_verified)
        self.assertFalse(outcome.can_supersede)
        self.assertFalse(outcome.mutates_memory)
        self.assertIsNone(outcome.canonical_identity_ref)
        self.assertEqual(outcome.integration_state, "evaluation_only")

    def test_matching_claimed_keys_and_two_claimed_origins_are_still_unverified(self):
        result = preflight(proposed())
        self.assertEqual(result.status, "structurally_plausible_unverified")
        self.assertIn("claimed_issuers_and_receipts_not_independently_verified",
                      result.reasons)
        self.assert_no_authority(result)

    def test_different_labels_might_name_same_property_but_cannot_auto_merge(self):
        p = proposed(newer=write(revision="revision:new", fact="fact:new",
                                  value="opaque:value-v2", prop="field:status-A"))
        result = preflight(p)
        self.assertEqual(result.status, "underdetermined")
        self.assertIn("property_identity_requires_independent_crosswalk", result.reasons)
        self.assert_no_authority(result)

    def test_different_subject_anchors_never_become_identity_by_value(self):
        p = proposed(newer=write(revision="revision:new", fact="fact:new",
                                  value="opaque:value-v2", subject="subject:unknown-alias"))
        result = preflight(p)
        self.assertEqual(result.status, "underdetermined")
        self.assertIn("subject_identity_requires_independent_proof", result.reasons)
        self.assert_no_authority(result)

    def test_actor_source_differences_require_independence_proof(self):
        for field, replacement in (("actor_ref", "actor:another"), ("source_ref", "source:external")):
            new = replace(proposed().newer, **{field: replacement})
            result = preflight(proposed(newer=new))
            self.assertEqual(result.status, "underdetermined")
            self.assertIn("cross_origin_requires_scope_and_issuer_verification", result.reasons)
            self.assert_no_authority(result)

    def test_tenant_scope_and_purpose_isolation_are_hard_refusals(self):
        for key, value in (("tenant_ref", "tenant:outsider"),
                           ("scope_ref", "scope:outside"),
                           ("purpose_ref", "purpose:unrelated")):
            newer = replace(proposed().newer, **{key: value})
            result = preflight(proposed(newer=newer))
            self.assertEqual(result.status, "refused")
            self.assertIn(f"{key}_incompatible", result.reasons)
            self.assert_no_authority(result)

    def test_stale_claimed_head_refused_even_with_signed_claims(self):
        result = preflight(proposed(observed_head_ref="head:changed"))
        self.assertEqual(result.status, "refused")
        self.assertIn("stale_claimed_head", result.reasons)
        self.assert_no_authority(result)

    def test_same_fact_or_revision_never_produces_two_write_state_change(self):
        base = proposed()
        for newer in (
            replace(base.newer, fact_ref=base.older.fact_ref),
            replace(base.newer, revision_ref=base.older.revision_ref),
        ):
            result = preflight(replace(base, newer=newer))
            self.assertEqual(result.status, "refused")
            self.assertIn("not_two_independent_fact_revisions", result.reasons)

    def test_lifecycle_refusals_before_any_semantic_claim(self):
        base = proposed()
        for status in ("disputed", "retracted", "tombstoned"):
            for side in ("older", "newer"):
                changed = replace(base, **{
                    side: replace(getattr(base, side), lifecycle_state=status),
                })
                result = preflight(changed)
                self.assertEqual(result.status, "refused")
                self.assertIn("inactive_or_disputed_revision", result.reasons)
                self.assert_no_authority(result)

    def test_cardinality_unknown_multi_and_coexistence_refuse_exclusive_update(self):
        base = proposed()
        for side in ("older", "newer"):
            for card in ("unknown", "multi"):
                p = replace(base, **{
                    side: replace(getattr(base, side), cardinality=card)
                })
                result = preflight(p)
                self.assertEqual(result.status, "refused")
                self.assertIn("exclusive_update_not_licensed_by_cardinality", result.reasons)
                self.assert_no_authority(result)
            p = replace(base, **{
                side: replace(getattr(base, side), coexistent=True)
            })
            self.assertEqual(preflight(p).status, "refused")

    def test_identical_value_is_not_exclusive_state_change(self):
        p = proposed(newer=replace(proposed().newer, value_ref="opaque:value-v1"))
        result = preflight(p)
        self.assertEqual(result.status, "refused")
        self.assertIn("identical_value_is_not_a_state_change", result.reasons)
        self.assert_no_authority(result)

    def test_claims_from_single_model_invocation_are_circular(self):
        one = claims()[0]
        doubled = (
            one,
            replace(one, evidence_ref="evidence:other-inside-same-call"),
        )
        outcome = preflight(proposed(claims=doubled))
        self.assertEqual(outcome.status, "underdetermined")
        self.assertIn("identity_evidence_has_single_claimed_origin", outcome.reasons)
        self.assert_no_authority(outcome)

    def test_duplicate_evidence_does_not_multiply_independence(self):
        c = claims()
        dup = replace(c[0], origin_invocation_ref="invocation:3",
                      origin_source_ref="source:third")
        result = preflight(proposed(claims=c+(dup,)))
        self.assertIn("identity_evidence_refs_reused", result.reasons)
        self.assertEqual(result.status, "underdetermined")
        self.assert_no_authority(result)

    def test_no_claims_is_not_evidence_of_equivalence(self):
        result = preflight(proposed(claims=()))
        self.assertEqual(result.status, "underdetermined")
        self.assertIn("no_identity_evidence_claimed", result.reasons)
        self.assert_no_authority(result)

    def test_claimed_signature_and_schema_are_never_issuer_verification(self):
        for kind in ("extractor_claim", "caller_claim", "schema_claim", "signature_claim"):
            a, b = claims()
            result = preflight(proposed(claims=(replace(a, claimed_kind=kind),
                                                replace(b, claimed_kind=kind))))
            self.assertIn("claimed_issuers_and_receipts_not_independently_verified",
                          result.reasons)
            self.assert_no_authority(result)

    def test_evidence_order_and_duplicate_claims_do_not_grant_authority(self):
        p = proposed()
        result = preflight(p)
        reverse = preflight(replace(p, claims=tuple(reversed(p.claims))))
        self.assertEqual(result, reverse)
        for new_claim in (
            replace(p.claims[0], evidence_ref="evidence:three"),
            replace(p.claims[1], evidence_ref="evidence:three"),
        ):
            candidate = preflight(replace(p, claims=p.claims+(new_claim,)))
            self.assert_no_authority(candidate)

    def test_no_value_identifier_can_make_the_claim_semantically_verified(self):
        p = proposed()
        values = ("0", "false", "32", "rgb:000000", "sha256:abc",
                  "shared", "unrelated", "value:⚙")
        for a_value in values:
            for b_value in values:
                old = replace(p.older, value_ref=a_value)
                new = replace(p.newer, value_ref=b_value)
                result = preflight(replace(p, older=old, newer=new))
                self.assert_no_authority(result)
                if a_value == b_value:
                    self.assertEqual(result.status, "refused")
                else:
                    self.assertNotEqual(result.status, "refused")

    def test_unrelated_semantic_domains_same_surface_property_never_authorized(self):
        # Deliberate "negative" category: two subjects happen to share the
        # same human-display property and value. The probe cannot know truth.
        left = write(revision="old", fact="fact:X", subject="entity:X",
                     prop="location", value="building:A")
        right = write(revision="new", fact="fact:Y", subject="entity:Y",
                      prop="location", value="building:B")
        r = preflight(proposed(older=left, newer=right))
        self.assertEqual(r.status, "underdetermined")
        self.assert_no_authority(r)

    def test_metamorphic_opaque_randomized_variants_are_deterministic(self):
        gen = random.Random(7572026)
        p = proposed()
        for i in range(120):
            a = replace(p.older, value_ref=f"v:{gen.randrange(100)}")
            b = replace(p.newer, value_ref=f"v:{gen.randrange(100)}",
                        property_ref=f"property:{gen.randrange(5)}",
                        subject_ref=f"entity:{gen.randrange(5)}")
            variant = replace(p, older=a, newer=b)
            before = repr(variant)
            one = preflight(variant)
            two = preflight(variant)
            self.assertEqual(one, two)
            self.assertEqual(repr(variant), before)
            self.assert_no_authority(one)
            if a.value_ref == b.value_ref:
                self.assertEqual(one.status, "refused")

    def test_bounded_shape_refuses_invalid_evidence_and_input(self):
        with self.assertRaises(ValueError):
            proposed(claims=(claims()[0],)*9)
        with self.assertRaises(ValueError):
            write(fact="\n", revision="r")
        with self.assertRaises(ValueError):
            write(fact="f", revision="r", cardinality="unbounded")
        with self.assertRaises(ValueError):
            write(fact="f", revision="r", lifecycle_state="forgotten")
        with self.assertRaises(ValueError):
            write(fact="f", revision="r", coexistent="yes")
        with self.assertRaises(TypeError):
            preflight({})
        with self.assertRaises(TypeError):
            proposed(claims=["claimed"])

    def test_immutable_receipts_cannot_be_rewritten_into_acceptance(self):
        result = preflight(proposed())
        with self.assertRaises(FrozenInstanceError):
            result.can_supersede = True
        with self.assertRaises(FrozenInstanceError):
            result.status = "verified_same_property"


if __name__ == "__main__":
    unittest.main()
