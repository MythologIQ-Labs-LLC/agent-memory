"""Adversarial tests for cryptographically committed temporal events (#263)."""

from __future__ import annotations

import copy
import hashlib
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentmem_ref.temporal_event_commitment import (
    build_temporal_commitment,
    canonical_temporal_bytes,
    evaluate_uor_temporal_compatibility,
    sign_temporal_commitment,
    temporal_content_ref,
    verify_temporal_chain,
    verify_temporal_commitment,
)


def fake_uor_address(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


class TemporalEventCommitmentTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.base = dict(
            event_type="agent.action",
            payload_digest="sha256:" + "11" * 32,
            event_time="2026-08-13T21:00:00Z",
            observed_at="2026-08-13T21:00:01Z",
            scope_ref="scope:project:alpha",
            stream_id="stream:agent-a:alpha",
            sequence=1,
            source_schema_ref="domain-schema:v3",
            source_schema_digest="sha256:" + "22" * 32,
            valid_from="2026-08-13T21:00:00Z",
            valid_to="2026-08-14T21:00:00Z",
        )

    def _signed(self, **changes):
        fields = {**self.base, **changes}
        return sign_temporal_commitment(
            build_temporal_commitment(**fields),
            private_key=self.key,
            key_id="key:agent-a:1",
        )

    def test_temporal_fields_are_inside_content_identity(self):
        baseline = build_temporal_commitment(**self.base)
        baseline_ref = temporal_content_ref(baseline)
        for field, value in (
            ("event_time", "2026-08-13T21:00:02Z"),
            ("observed_at", "2026-08-13T21:00:03Z"),
            ("valid_from", "2026-08-13T21:00:04Z"),
            ("valid_to", "2026-08-15T21:00:00Z"),
            ("scope_ref", "scope:project:beta"),
            ("stream_id", "stream:agent-a:beta"),
            ("source_schema_digest", "sha256:" + "33" * 32),
            ("payload_digest", "sha256:" + "44" * 32),
        ):
            with self.subTest(field=field):
                changed = {**self.base, field: value}
                self.assertNotEqual(baseline_ref, temporal_content_ref(build_temporal_commitment(**changed)))

    def test_signature_breaks_when_committed_temporal_claim_is_tampered(self):
        document = self._signed()
        tampered = copy.deepcopy(document)
        tampered["commitment"]["event_time"] = "2026-08-13T22:00:00Z"
        result = verify_temporal_commitment(tampered)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("content_reference_mismatch", result["reason_codes"])

    def test_wrong_key_signature_is_rejected(self):
        document = self._signed()
        other = self._signed(event_time="2026-08-13T21:00:02Z")
        document["signature"]["public_key_base64"] = other["signature"]["public_key_base64"]
        result = verify_temporal_commitment(document)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("signature_invalid", result["reason_codes"])

    def test_unwitnessed_signature_does_not_claim_trusted_wall_clock(self):
        document = self._signed()
        result = verify_temporal_commitment(document)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["trusted_time_status"], "unwitnessed")
        self.assertFalse(result["signature_proves_trusted_wall_clock"])
        self.assertEqual(result["authority_effect"], "none")
        self.assertFalse(result["can_create_lifecycle_currentness"])
        self.assertFalse(result["can_satisfy_pama_mutation_authority"])

    def test_verified_witness_binds_exact_signature_but_not_authority(self):
        first = self._signed()
        witness = {
            "kind": "rfc3161",
            "subject_ref": first["signature"]["signature_ref"],
            "witnessed_at": "2026-08-13T21:00:05Z",
            "witness_ref": "tsa:receipt:1",
            "verified": True,
            "evidence_refs": ["evidence:tsa:1"],
        }
        document = sign_temporal_commitment(
            first["commitment"], private_key=self.key, key_id="key:agent-a:1", trusted_time_witness=witness
        )
        self.assertEqual(document["trusted_time"]["status"], "verified")
        self.assertEqual(document["trusted_time"]["authority_effect"], "none")
        with self.assertRaisesRegex(ValueError, "exact signature_ref"):
            bad = dict(witness)
            bad["subject_ref"] = "sha256:" + "55" * 32
            sign_temporal_commitment(first["commitment"], private_key=self.key, key_id="key:agent-a:1", trusted_time_witness=bad)

    def test_chain_detects_previous_reference_sequence_and_scope_substitution(self):
        first = self._signed()
        second_fields = {**self.base, "sequence": 2, "previous_event_ref": first["commitment_ref"], "event_time": "2026-08-13T21:01:00Z", "observed_at": "2026-08-13T21:01:01Z"}
        second = sign_temporal_commitment(build_temporal_commitment(**second_fields), private_key=self.key, key_id="key:agent-a:1")
        self.assertEqual(verify_temporal_chain([first, second])["status"], "verified")

        bad_previous = copy.deepcopy(second)
        bad_previous["commitment"]["previous_event_ref"] = "sha256:" + "66" * 32
        self.assertEqual(verify_temporal_chain([first, bad_previous])["status"], "invalid")

        wrong_scope_fields = {**second_fields, "scope_ref": "scope:project:other"}
        wrong_scope = sign_temporal_commitment(build_temporal_commitment(**wrong_scope_fields), private_key=self.key, key_id="key:agent-a:1")
        result = verify_temporal_chain([first, wrong_scope])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("event_2_scope_mismatch", result["reason_codes"])

        wrong_sequence_fields = {**self.base, "sequence": 3, "previous_event_ref": first["commitment_ref"], "event_time": "2026-08-13T21:01:00Z", "observed_at": "2026-08-13T21:01:01Z"}
        wrong_sequence = sign_temporal_commitment(build_temporal_commitment(**wrong_sequence_fields), private_key=self.key, key_id="key:agent-a:1")
        result = verify_temporal_chain([first, wrong_sequence])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("event_2_sequence_mismatch", result["reason_codes"])

    def test_chain_never_claims_complete_history_or_deletion_completeness(self):
        result = verify_temporal_chain([self._signed()])
        self.assertFalse(result["proves_complete_history"])
        self.assertFalse(result["proves_deletion_completeness"])
        self.assertEqual(result["authority_effect"], "none")

    def test_uor_profile_can_verify_same_canonical_temporal_identity_without_authority(self):
        document = self._signed()
        evidence = evaluate_uor_temporal_compatibility(
            document, address_fn=fake_uor_address, binding_name="fixture", binding_version="0"
        )
        self.assertEqual(evidence["status"], "verified")
        self.assertEqual(evidence["authority_effect"], "none")
        self.assertFalse(evidence["ordinary_agent_memory_requires_uor_runtime"])
        self.assertTrue(evidence["uor_evidence"]["content_identity_only"])

    def test_unicode_nfc_is_part_of_temporal_realization(self):
        composed = build_temporal_commitment(**{**self.base, "event_type": "caf\u00e9"})
        decomposed = build_temporal_commitment(**{**self.base, "event_type": "cafe\u0301"})
        self.assertEqual(canonical_temporal_bytes(composed), canonical_temporal_bytes(decomposed))
        self.assertEqual(temporal_content_ref(composed), temporal_content_ref(decomposed))

    def test_sequence_contract_rejects_ambiguous_chain_roots(self):
        with self.assertRaisesRegex(ValueError, "sequence 1"):
            build_temporal_commitment(**{**self.base, "previous_event_ref": "sha256:" + "77" * 32})
        with self.assertRaisesRegex(ValueError, "requires previous_event_ref"):
            build_temporal_commitment(**{**self.base, "sequence": 2})


if __name__ == "__main__":
    unittest.main()
