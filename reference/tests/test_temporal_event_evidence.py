import copy
import hashlib
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentmem_ref.temporal_event_commitment import (
    build_temporal_commitment,
    evaluate_uor_temporal_compatibility,
    sign_temporal_commitment,
    temporal_content_ref,
    verify_temporal_chain,
    verify_temporal_commitment,
)


def fake_address(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


class TemporalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.fields = {
            "event_type": "agent.action",
            "payload_digest": "sha256:" + "11" * 32,
            "event_time": "2026-08-13T21:00:00Z",
            "observed_at": "2026-08-13T21:00:01Z",
            "scope_ref": "scope:alpha",
            "stream_id": "stream:alpha",
            "sequence": 1,
            "source_schema_ref": "schema:v1",
            "source_schema_digest": "sha256:" + "22" * 32,
        }

    def signed(self, **changes):
        data = {**self.fields, **changes}
        return sign_temporal_commitment(build_temporal_commitment(**data), private_key=self.key, key_id="key:a:1")

    def test_temporal_mutation_changes_identity(self):
        base = temporal_content_ref(build_temporal_commitment(**self.fields))
        for field, value in [
            ("event_time", "2026-08-13T21:00:02Z"),
            ("observed_at", "2026-08-13T21:00:03Z"),
            ("scope_ref", "scope:beta"),
            ("stream_id", "stream:beta"),
            ("payload_digest", "sha256:" + "33" * 32),
            ("source_schema_digest", "sha256:" + "44" * 32),
        ]:
            self.assertNotEqual(base, temporal_content_ref(build_temporal_commitment(**{**self.fields, field: value})))

    def test_tampered_temporal_claim_fails(self):
        document = self.signed()
        document["commitment"]["event_time"] = "2026-08-13T22:00:00Z"
        result = verify_temporal_commitment(document)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("content_reference_mismatch", result["reason_codes"])

    def test_different_verifier_key_fails(self):
        document = self.signed()
        other_key = Ed25519PrivateKey.generate()
        other = sign_temporal_commitment(document["commitment"], private_key=other_key, key_id="key:b:1")
        document["signature"]["public_key_base64"] = other["signature"]["public_key_base64"]
        self.assertEqual(verify_temporal_commitment(document)["status"], "invalid")

    def test_signer_identifier_is_bound(self):
        document = self.signed()
        document["signature"]["key_id"] = "key:other:1"
        result = verify_temporal_commitment(document)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("signature_invalid", result["reason_codes"])

    def test_unwitnessed_time_is_not_trusted_time_or_authority(self):
        result = verify_temporal_commitment(self.signed())
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["trusted_time_status"], "unwitnessed")
        self.assertFalse(result["signature_proves_trusted_wall_clock"])
        self.assertFalse(result["can_create_lifecycle_currentness"])
        self.assertFalse(result["can_satisfy_pama_mutation_authority"])

    def test_witness_binds_exact_signer_evidence(self):
        first = self.signed()
        witness = {
            "kind": "rfc3161",
            "subject_ref": first["signature"]["signature_ref"],
            "witnessed_at": "2026-08-13T21:00:05Z",
            "witness_ref": "witness:1",
            "verified": True,
            "evidence_refs": ["evidence:witness:1"],
        }
        witnessed = sign_temporal_commitment(first["commitment"], private_key=self.key, key_id="key:a:1", trusted_time_witness=witness)
        self.assertEqual(witnessed["trusted_time"]["status"], "verified")
        self.assertEqual(witnessed["trusted_time"]["authority_effect"], "none")

    def test_chain_detects_order_and_scope_changes(self):
        first = self.signed()
        second = sign_temporal_commitment(
            build_temporal_commitment(**{
                **self.fields,
                "sequence": 2,
                "previous_event_ref": first["commitment_ref"],
                "event_time": "2026-08-13T21:01:00Z",
                "observed_at": "2026-08-13T21:01:01Z",
            }),
            private_key=self.key,
            key_id="key:a:1",
        )
        self.assertEqual(verify_temporal_chain([first, second])["status"], "verified")
        tampered = copy.deepcopy(second)
        tampered["commitment"]["previous_event_ref"] = "sha256:" + "55" * 32
        self.assertEqual(verify_temporal_chain([first, tampered])["status"], "invalid")

    def test_chain_never_claims_completeness(self):
        result = verify_temporal_chain([self.signed()])
        self.assertFalse(result["proves_complete_history"])
        self.assertFalse(result["proves_deletion_completeness"])
        self.assertEqual(result["authority_effect"], "none")

    def test_uor_identity_remains_optional_and_non_authoritative(self):
        evidence = evaluate_uor_temporal_compatibility(self.signed(), address_fn=fake_address, binding_name="fixture", binding_version="0")
        self.assertEqual(evidence["status"], "verified")
        self.assertEqual(evidence["authority_effect"], "none")
        self.assertFalse(evidence["ordinary_agent_memory_requires_uor_runtime"])


if __name__ == "__main__":
    unittest.main()
