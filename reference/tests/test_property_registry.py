"""#757 J27-J41 independent typed cross-write ontology qualification.

These are domain-neutral, opaque property ID tests, NOT #732 or MESA
benchmarks; a schema declaration remains a NON-AUTHORITATIVE candidate.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentmem_ref.evaluation.property_registry import (
    ALGORITHM, PROFILE, VERSION, PropertyDefinition, PropertyRegistry,
    RegistryError, SignedPropertyRegistry, qualify_property_link, sign_registry,
)
from agentmem_ref.memory.temporal_trust import public_key_digest
from tests.test_proposition_link_preflight import proposed, write


def registry(*, state="active") -> PropertyRegistry:
    return PropertyRegistry(
        schema_ref="schema:owner-vocabulary",
        revision_ref="revision:schema-17",
        tenant_ref="tenant:isolated",
        scope_ref="scope:program",
        purpose_ref="purpose:task",
        issuer_key_ref="key:owner-publisher",
        properties=(
            PropertyDefinition(
                "canonical:phase", ("field:current-phase", "property:status-7"), state
            ),
            PropertyDefinition(
                "canonical:priority", ("field:priority",), "active"
            ),
        ),
    )


class PropertyRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = Ed25519PrivateKey.from_private_bytes(bytes([0x73] * 32))
        cls.other = Ed25519PrivateKey.from_private_bytes(bytes([0x42] * 32))

    def setUp(self):
        self.manifest = registry()
        self.signed = sign_registry(self.manifest, private_key=self.key)
        self.oldnew = proposed(
            older=write(
                revision="revision:old", fact="fact:old",
                prop="property:status-7", value="opaque:v1"
            ),
            newer=write(
                revision="revision:new", fact="fact:new",
                prop="field:current-phase", value="opaque:v2"
            ),
        )

    def qualify(self, *, proposal=None, signed=None, key=None, pin=None, **expected):
        public = (key or self.key).public_key()
        expected_args = {
            "expected_issuer_key_ref": "key:owner-publisher",
            "expected_schema_ref": "schema:owner-vocabulary",
            "expected_revision_ref": "revision:schema-17",
            "expected_tenant_ref": "tenant:isolated",
            "expected_scope_ref": "scope:program",
            "expected_purpose_ref": "purpose:task",
        }
        expected_args.update(expected)
        return qualify_property_link(
            self.oldnew if proposal is None else proposal,
            self.signed if signed is None else signed,
            public_key=public,
            pinned_public_key_digest=public_key_digest(public) if pin is None else pin,
            **expected_args,
        )

    def assert_no_authority(self, result):
        self.assertFalse(result.issuer_authorized)
        self.assertFalse(result.identity_verified)
        self.assertFalse(result.can_supersede)
        self.assertFalse(result.mutates_memory)
        self.assertEqual(result.authority_effect, "none")
        self.assertEqual(result.integration_state, "evaluation_only")

    def test_distinct_labels_shared_explicit_property_gives_candidate_not_identity(self):
        verdict = self.qualify()
        self.assertEqual(verdict.status, "schema_candidate")
        self.assertEqual(verdict.declared_property_ref, "canonical:phase")
        self.assertTrue(verdict.signature_valid)
        self.assertTrue(verdict.key_pin_matches)
        self.assertTrue(verdict.pinned_context_matches)
        self.assertIn("registry_issuer_authority_not_established", verdict.reason_codes)
        self.assert_no_authority(verdict)

    def test_exact_same_label_also_not_final_semantic_identity(self):
        p = replace(self.oldnew, newer=replace(self.oldnew.newer,
                                               property_ref="property:status-7"))
        result = self.qualify(proposal=p)
        self.assertEqual(result.status, "schema_candidate")
        self.assert_no_authority(result)

    def test_k01_declared_distinct_active_properties_refuse(self):
        p = replace(self.oldnew, newer=replace(self.oldnew.newer,
                                               property_ref="field:priority"))
        v = self.qualify(proposal=p)
        self.assertEqual(v.status, "refused")
        self.assertIn("schema_declares_different_properties", v.reason_codes)
        self.assertIsNone(v.declared_property_ref)
        self.assertTrue(v.signature_valid)
        self.assertTrue(v.key_pin_matches)
        self.assert_no_authority(v)

    def test_k02_unknown_label_remains_underdetermined(self):
        p = replace(self.oldnew, newer=replace(self.oldnew.newer,
                                               property_ref="field:unknown"))
        v = self.qualify(proposal=p)
        self.assertEqual(v.status, "abstain")
        self.assertIn("schema_label_unmapped", v.reason_codes)
        self.assertNotIn("schema_declares_different_properties", v.reason_codes)
        self.assert_no_authority(v)

    def test_unknown_property_label_never_uses_fuzzy_match(self):
        for label in (
            "Field:current-phase", "field:current-phases", "current phase",
            "field:currént-phase", "field:current-phase ",
        ):
            if label.endswith(" "):
                with self.assertRaises(ValueError):
                    replace(self.oldnew.newer, property_ref=label)
                continue
            p = replace(self.oldnew, newer=replace(self.oldnew.newer, property_ref=label))
            v = self.qualify(proposal=p)
            self.assertEqual(v.status, "abstain")
            self.assertIn("schema_label_unmapped", v.reason_codes)
            self.assert_no_authority(v)

    def test_same_low_entropy_value_does_not_become_state_change(self):
        p = replace(self.oldnew, newer=replace(self.oldnew.newer,
                                               value_ref=self.oldnew.older.value_ref))
        v = self.qualify(proposal=p)
        self.assertEqual(v.status, "refused")
        self.assertIn("structural_preflight_refused", v.reason_codes)
        self.assert_no_authority(v)

    def test_different_subject_prevents_candidate_even_with_same_label_map(self):
        p = replace(self.oldnew, newer=replace(self.oldnew.newer,
                                               subject_ref="subject:another"))
        v = self.qualify(proposal=p)
        self.assertEqual(v.status, "refused")
        self.assertIn("subject_identity_not_proven", v.reason_codes)
        self.assert_no_authority(v)

    def test_scoped_tenant_purpose_and_cross_scope_reject(self):
        for field, value in (
            ("tenant_ref", "tenant:another"),
            ("scope_ref", "scope:another"),
            ("purpose_ref", "purpose:other"),
        ):
            p = replace(self.oldnew, newer=replace(self.oldnew.newer, **{field: value}))
            v = self.qualify(proposal=p)
            self.assertEqual(v.status, "refused")
            self.assertIn("proposal_outside_registry_scope", v.reason_codes)
            self.assert_no_authority(v)

    def test_cross_actor_and_source_does_not_confer_authority(self):
        p = replace(self.oldnew, newer=replace(self.oldnew.newer,
            actor_ref="actor:other", source_ref="source:other"))
        v = self.qualify(proposal=p)
        self.assertEqual(v.status, "schema_candidate")
        self.assertIn("cross_origin_provenance_not_established", v.reason_codes)
        self.assert_no_authority(v)

    def test_revoked_disputed_and_retired_property_not_eligible(self):
        for status in ("revoked", "disputed", "retired"):
            current = registry(state=status)
            signed = sign_registry(current, private_key=self.key)
            v = self.qualify(signed=signed)
            self.assertEqual(v.status, "abstain")
            self.assertIn("property_not_active", v.reason_codes)
            self.assert_no_authority(v)

    def test_unknown_cardinality_coexistence_and_lifecycle_refuse(self):
        for changed in (
            {"cardinality": "multi"},
            {"cardinality": "unknown"},
            {"coexistent": True},
            {"lifecycle_state": "disputed"},
            {"lifecycle_state": "retracted"},
        ):
            p = replace(self.oldnew, newer=replace(self.oldnew.newer, **changed))
            v = self.qualify(proposal=p)
            self.assertEqual(v.status, "refused")
            self.assertIn("structural_preflight_refused", v.reason_codes)
            self.assert_no_authority(v)

    def test_wrong_expected_manifest_boundaries_refused(self):
        for field, value in (
            ("expected_schema_ref", "schema:another"),
            ("expected_revision_ref", "revision:outdated"),
            ("expected_tenant_ref", "tenant:other"),
            ("expected_scope_ref", "scope:outside"),
            ("expected_purpose_ref", "purpose:unknown"),
            ("expected_issuer_key_ref", "key:untrusted"),
        ):
            v = self.qualify(**{field: value})
            self.assertEqual(v.status, "refused")
            self.assertIn("independent_schema_context_mismatch", v.reason_codes)
            self.assert_no_authority(v)

    def test_wrong_public_key_pin_and_key_substitution_do_not_link(self):
        old_pin = public_key_digest(self.key.public_key())
        v = self.qualify(key=self.other, pin=old_pin)
        self.assertEqual(v.status, "refused")
        self.assertFalse(v.signature_valid)
        self.assertFalse(v.key_pin_matches)
        self.assert_no_authority(v)
        v = self.qualify(pin=public_key_digest(self.other.public_key()))
        self.assertEqual(v.status, "refused")
        self.assertTrue(v.signature_valid)
        self.assertFalse(v.key_pin_matches)
        self.assert_no_authority(v)

    def test_changed_content_invalidates_signature(self):
        broken = replace(self.signed, registry=replace(
            self.manifest, revision_ref="revision:changed"
        ))
        v = self.qualify(signed=broken)
        self.assertEqual(v.status, "refused")
        self.assertFalse(v.signature_valid)
        self.assert_no_authority(v)

    def test_changed_aliases_and_binding_invalidate_signature(self):
        changed = replace(
            self.manifest,
            properties=(
                replace(self.manifest.properties[0],
                        label_refs=("field:alternate", "property:status-7")),
                self.manifest.properties[1],
            )
        )
        v = self.qualify(signed=replace(self.signed, registry=changed))
        self.assertEqual(v.status, "refused")
        self.assertFalse(v.signature_valid)

    def test_signature_contract_version_and_encoding_refused(self):
        for changed in (
            replace(self.signed, version="2.0.0"),
            replace(self.signed, profile="different/profile"),
            replace(self.signed, algorithm="RSA"),
            replace(self.signed, signature_b64="@@bad"),
            replace(self.signed, signature_b64="AA=="),
        ):
            v = self.qualify(signed=changed)
            self.assertEqual(v.status, "refused")
            self.assertFalse(v.signature_valid)
            self.assert_no_authority(v)

    def test_ambiguous_alias_and_duplicate_canonical_property_rejected(self):
        base = self.manifest.properties
        with self.assertRaises(RegistryError):
            replace(self.manifest, properties=base+(
                PropertyDefinition("canonical:z", ("field:current-phase",)),
            ))
        with self.assertRaises(RegistryError):
            replace(self.manifest, properties=base+(
                PropertyDefinition("canonical:phase", ("field:unknown",)),
            ))

    def test_duplicate_labels_bad_order_and_missing_labels_fail(self):
        with self.assertRaises(RegistryError):
            PropertyDefinition("canonical:x", ("x", "x"))
        with self.assertRaises(RegistryError):
            PropertyDefinition("canonical:x", ("z", "a"))
        with self.assertRaises(RegistryError):
            PropertyDefinition("canonical:x", ())
        with self.assertRaises(RegistryError):
            PropertyDefinition("canonical:x", ("x",), "unknown")

    def test_malformed_registry_and_counts_fail_closed(self):
        with self.assertRaises(RegistryError):
            PropertyRegistry(**{**self.manifest.__dict__, "properties": []})
        with self.assertRaises(RegistryError):
            PropertyRegistry(**{**self.manifest.__dict__, "properties":
                (PropertyDefinition("canonical:A", ("field:a",)),)*33})
        with self.assertRaises(RegistryError):
            PropertyDefinition("canonical:z", tuple(f"v:{x}" for x in range(13)))
        with self.assertRaises(TypeError):
            sign_registry("not-registry", private_key=self.key)

    def test_self_issued_registry_and_attacker_supplied_pin_still_not_authoritative(self):
        false_registry = PropertyRegistry(
            schema_ref=self.manifest.schema_ref,
            revision_ref=self.manifest.revision_ref,
            tenant_ref=self.manifest.tenant_ref,
            scope_ref=self.manifest.scope_ref,
            purpose_ref=self.manifest.purpose_ref,
            issuer_key_ref=self.manifest.issuer_key_ref,
            properties=(
                PropertyDefinition("canonical:made-up",
                                   ("field:current-phase", "property:status-7")),
            ),
        )
        forged_signed = sign_registry(false_registry, private_key=self.other)
        v = self.qualify(signed=forged_signed, key=self.other)
        self.assertEqual(v.status, "schema_candidate")
        self.assertTrue(v.signature_valid)
        self.assertTrue(v.key_pin_matches)
        self.assertIn("registry_issuer_authority_not_established", v.reason_codes)
        self.assert_no_authority(v)

    def test_no_side_effects_and_determinism(self):
        old = self.manifest
        signed = self.signed
        observed = self.oldnew
        first = self.qualify()
        for _ in range(6):
            self.assertEqual(self.qualify(), first)
        self.assertEqual(old, self.manifest)
        self.assertEqual(signed, self.signed)
        self.assertEqual(observed, self.oldnew)
        with self.assertRaises(FrozenInstanceError):
            first.can_supersede = True
        with self.assertRaises(FrozenInstanceError):
            signed.registry = old

    def test_unknown_expected_pin_and_shape_fail_closed(self):
        with self.assertRaises(ValueError):
            self.qualify(pin="unknown")
        with self.assertRaises(ValueError):
            self.qualify(expected_scope_ref="")
        v = self.qualify(signed={})
        self.assertEqual(v.status, "refused")
        self.assert_no_authority(v)


if __name__ == "__main__":
    unittest.main()
