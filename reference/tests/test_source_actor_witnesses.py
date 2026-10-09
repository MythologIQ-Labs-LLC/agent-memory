"""#757 J73-J88: synthetic actor/source observation witness adversarial cases.

These are not general semantic or origin-trust benchmarks. No provider calls,
production mutation, frozen #732/R6 inputs or claim of independent issuers.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentmem_ref.evaluation.source_actor_witnesses import (
    ALGORITHM, PROFILE, VERSION,
    MAX_WITNESSES, SignedWriteWitness, WitnessExpectation, WitnessInput,
    WitnessError, qualify_write_origins, sign_write_witness,
)
from agentmem_ref.memory.temporal_trust import public_key_digest
from tests.test_proposition_link_preflight import proposed, write


class WriteWitnessTests(unittest.TestCase):
    def setUp(self):
        self.proposal = proposed(
            older=write(fact="fact:w1", revision="revision:r1",
                        prop="property:unspecifiedA", value="opaque:x1"),
            newer=write(fact="fact:w2", revision="revision:r2",
                        prop="attribute:unspecifiedB", value="opaque:x2"),
        )
        self.keys = (
            Ed25519PrivateKey.from_private_bytes(bytes([0x61] * 32)),
            Ed25519PrivateKey.from_private_bytes(bytes([0x62] * 32)),
            Ed25519PrivateKey.from_private_bytes(bytes([0x63] * 32)),
            Ed25519PrivateKey.from_private_bytes(bytes([0x64] * 32)),
        )
        self.inputs = tuple(
            self.witness(side, role, self.keys[i])
            for i, (side, role) in enumerate((
                ("older", "actor"), ("older", "source"),
                ("newer", "actor"), ("newer", "source"),
            ))
        )

    def witness(self, side, role, key, *, observed=None,
                principal=None, key_ref=None, expected=None):
        obs = observed or getattr(self.proposal, side)
        name = principal or (obs.actor_ref if role == "actor" else obs.source_ref)
        ref = key_ref or f"witness-key:{side}:{role}"
        signed = sign_write_witness(
            obs, side=side, role=role, claimed_principal_ref=name,
            key_ref=ref, private_key=key,
        )
        anchor = expected or WitnessExpectation(
            side=side, role=role, expected_principal_ref=name,
            expected_key_ref=ref,
            pinned_public_key_digest=public_key_digest(key.public_key()),
        )
        return WitnessInput(signed, key.public_key(), anchor)

    def no_authority(self, receipt):
        self.assertFalse(receipt.principal_authenticated)
        self.assertFalse(receipt.origin_independence_verified)
        self.assertFalse(receipt.issuer_authorized)
        self.assertFalse(receipt.identity_verified)
        self.assertFalse(receipt.can_supersede)
        self.assertFalse(receipt.mutates_memory)
        self.assertEqual(receipt.authority_effect, "none")
        self.assertEqual(receipt.currentness, "not_established")
        self.assertEqual(receipt.integration_state, "evaluation_only")

    def test_four_complete_signed_roles_are_only_provenance_candidates(self):
        v = qualify_write_origins(self.proposal, self.inputs)
        self.assertEqual(v.status, "cryptographic_witness_candidate")
        self.assertEqual(v.signature_matches, 4)
        self.assertEqual(v.pin_matches, 4)
        self.assertEqual(v.observed_positions, 4)
        self.assertIn("witness_anchor_origin_and_delegation_not_authenticated",
                      v.reason_codes)
        self.no_authority(v)

    def test_missing_witness_abstains_even_when_three_are_valid(self):
        v = qualify_write_origins(self.proposal, self.inputs[:-1])
        self.assertEqual(v.status, "abstain")
        self.assertIn("missing_witness_position", v.reason_codes)
        self.assertEqual(v.signature_matches, 3)
        self.no_authority(v)
        self.assertEqual(qualify_write_origins(self.proposal, ()).status, "abstain")

    def test_duplicate_and_fifth_witness_are_refused(self):
        for data in (self.inputs + (self.inputs[0],),
                     self.inputs[:3] + (self.inputs[0],)):
            v = qualify_write_origins(self.proposal, data)
            self.assertEqual(v.status, "refused")
            self.assertIn("duplicate_or_unknown_witness_position", v.reason_codes)
            self.no_authority(v)

    def test_permutation_is_deterministic(self):
        a = qualify_write_origins(self.proposal, self.inputs)
        b = qualify_write_origins(self.proposal, tuple(reversed(self.inputs)))
        c = qualify_write_origins(self.proposal, self.inputs)
        self.assertEqual(a, b)
        self.assertEqual(b, c)
        self.no_authority(a)

    def test_wrong_key_material_even_with_correct_role_refuses(self):
        other = self.keys[2].public_key()
        changed = replace(self.inputs[0], public_key=other)
        v = qualify_write_origins(self.proposal, (changed,) + self.inputs[1:])
        self.assertEqual(v.status, "refused")
        self.assertIn("witness_key_material_pin_mismatch", v.reason_codes)
        self.assertIn("witness_signature_or_contract_invalid", v.reason_codes)
        self.no_authority(v)

    def test_attacker_controlled_key_and_anchor_pin_is_still_untrusted(self):
        attacker = Ed25519PrivateKey.from_private_bytes(bytes([0x31] * 32))
        forged = tuple(
            self.witness(side, role, attacker)
            for side, role in (("older", "actor"), ("older", "source"),
                               ("newer", "actor"), ("newer", "source"))
        )
        v = qualify_write_origins(self.proposal, forged)
        self.assertEqual(v.status, "cryptographic_witness_candidate")
        self.no_authority(v)

    def test_four_distinct_keys_are_not_proof_of_independent_issuers(self):
        v = qualify_write_origins(self.proposal, self.inputs)
        self.assertEqual(v.status, "cryptographic_witness_candidate")
        self.assertFalse(v.origin_independence_verified)
        self.no_authority(v)

    def test_role_swap_and_side_swap_are_refused(self):
        one = self.inputs[0]
        changes = (
            replace(one.signed, role="source"),
            replace(one.signed, side="newer"),
            replace(one.signed, key_ref="witness-key:forged"),
            replace(one.signed, claimed_principal_ref="actor:unauthorized"),
        )
        for signed in changes:
            modified = (replace(one, signed=signed),) + self.inputs[1:]
            v = qualify_write_origins(self.proposal, modified)
            self.assertEqual(v.status, "refused")
            self.no_authority(v)

    def test_changed_expected_principal_and_key_ref_refuse(self):
        one = self.inputs[0]
        for changes in (
            {"expected_principal_ref": "actor:unknown"},
            {"expected_key_ref": "witness-key:other"},
            {"side": "newer"},
            {"role": "source"},
        ):
            expectation = replace(one.expected, **changes)
            v = qualify_write_origins(
                self.proposal,
                (replace(one, expected=expectation),) + self.inputs[1:],
            )
            self.assertEqual(v.status, "refused")
            self.no_authority(v)

    def test_exact_observation_payload_bound_against_mutation(self):
        one = self.inputs[0]
        for name, value in (
            ("fact_ref", "fact:other"),
            ("revision_ref", "revision:other"),
            ("subject_ref", "subject:other"),
            ("property_ref", "property:other"),
            ("value_ref", "opaque:other"),
            ("actor_ref", "actor:other"),
            ("source_ref", "source:other"),
            ("tenant_ref", "tenant:other"),
            ("scope_ref", "scope:other"),
            ("purpose_ref", "purpose:other"),
            ("cardinality", "multi"),
            ("lifecycle_state", "disputed"),
            ("coexistent", True),
        ):
            wrong_obs = replace(one.signed.observed, **{name:value})
            witness = replace(one.signed, observed=wrong_obs)
            v = qualify_write_origins(self.proposal, (
                replace(one, signed=witness),) + self.inputs[1:],
            )
            self.assertEqual(v.status, "refused", msg=name)
            self.assertIn("witness_observation_revision_mismatch", v.reason_codes)
            self.no_authority(v)

    def test_witnesses_from_prior_revision_cannot_be_replayed_for_new_one(self):
        p = replace(self.proposal, newer=replace(
            self.proposal.newer, revision_ref="revision:r3",
        ))
        v = qualify_write_origins(p, self.inputs)
        self.assertEqual(v.status, "refused")
        self.assertIn("witness_observation_revision_mismatch", v.reason_codes)
        self.no_authority(v)

    def test_noncanonical_and_corrupt_signature_refuse(self):
        one = self.inputs[0]
        for bad in ("@@", "AA==", one.signed.signature_b64 + "==", ""):
            v = qualify_write_origins(self.proposal, (
                replace(one, signed=replace(one.signed, signature_b64=bad)),
            ) + self.inputs[1:])
            self.assertEqual(v.status, "refused")
            self.assertIn("witness_signature_or_contract_invalid", v.reason_codes)
            self.no_authority(v)

    def test_unsupported_profile_version_and_algorithm_refuse(self):
        one = self.inputs[0]
        for updates in (
            {"profile": "agent-memory/other"},
            {"version": "2.0.0"},
            {"algorithm": "RSA"},
        ):
            v = qualify_write_origins(self.proposal, (
                replace(one, signed=replace(one.signed, **updates)),
            ) + self.inputs[1:])
            self.assertEqual(v.status, "refused")
            self.assertIn("witness_signature_or_contract_invalid", v.reason_codes)
            self.no_authority(v)

    def test_structural_refusals_dominate_even_four_signed_roles(self):
        variants = (
            {"value_ref": self.proposal.older.value_ref},
            {"cardinality": "multi"},
            {"coexistent": True},
            {"lifecycle_state": "retracted"},
            {"tenant_ref": "tenant:other"},
            {"scope_ref": "scope:other"},
            {"purpose_ref": "purpose:other"},
        )
        for changed in variants:
            p = replace(self.proposal, newer=replace(self.proposal.newer, **changed))
            fresh = tuple(
                self.witness(side, role, self.keys[i],
                             observed=getattr(p, side))
                for i, (side,role) in enumerate((
                    ("older","actor"), ("older","source"),
                    ("newer","actor"), ("newer","source")
                ))
            )
            v = qualify_write_origins(p, fresh)
            self.assertEqual(v.status, "refused")
            self.assertIn("structural_preflight_refused", v.reason_codes)
            self.no_authority(v)

    def test_stale_head_refused_with_all_valid_signed_roles(self):
        p = replace(self.proposal, observed_head_ref="head:new")
        v = qualify_write_origins(p, self.inputs)
        self.assertEqual(v.status, "refused")
        self.assertIn("structural_preflight_refused", v.reason_codes)
        self.no_authority(v)

    def test_bounded_exact_input_types_and_invalid_roles(self):
        with self.assertRaises(WitnessError):
            WitnessExpectation(
                side="other", role="actor",
                expected_principal_ref="actor:owner",
                expected_key_ref="key:any",
                pinned_public_key_digest=public_key_digest(self.keys[0].public_key()),
            )
        with self.assertRaises(ValueError):
            sign_write_witness(
                self.proposal.older, side="older", role="actor",
                claimed_principal_ref="principal:a",
                key_ref="a" * 257, private_key=self.keys[0],
            )
        with self.assertRaises(TypeError):
            qualify_write_origins(self.proposal, list(self.inputs))
        self.assertEqual(MAX_WITNESSES, 4)

    def test_same_actor_and_source_across_writes_does_not_establish_independence(self):
        single_key = self.keys[0]
        inputs = tuple(
            self.witness(side, role, single_key)
            for side,role in (("older","actor"), ("older","source"),
                              ("newer","actor"), ("newer","source"))
        )
        v = qualify_write_origins(self.proposal, inputs)
        self.assertEqual(v.status, "cryptographic_witness_candidate")
        self.assertFalse(v.origin_independence_verified)
        self.no_authority(v)

    def test_witness_receipts_and_inputs_are_immutable(self):
        result = qualify_write_origins(self.proposal, self.inputs)
        with self.assertRaises(FrozenInstanceError):
            result.status = "refused"
        with self.assertRaises(FrozenInstanceError):
            self.inputs[0].signed.side = "newer"
        self.no_authority(result)


if __name__ == "__main__":
    unittest.main()
