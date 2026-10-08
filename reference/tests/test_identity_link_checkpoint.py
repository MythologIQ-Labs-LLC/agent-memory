"""J15–J26: independently pinned head binding, never semantic proof.

Opaque typed evaluation inputs only. No scored #732/MESA cases, provider calls,
trust store, runtime baseline change, or issuer authorization is introduced.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentmem_ref.evaluation.identity_link_journal import (
    JournalError, LinkEvidenceJournal, _append_event, _hash, genesis,
    proposal_payload, PROPOSAL_DOMAIN,
)
from agentmem_ref.evaluation.identity_link_checkpoint import (
    CHECKPOINT_PROFILE, CHECKPOINT_VERSION, JournalHeadCheckpoint,
    sign_journal_head, verify_journal_head,
)
from agentmem_ref.memory.temporal_trust import public_key_digest
from tests.test_identity_link_journal import IdentityLinkJournalTests


class JournalCheckpointTests(TestCase):
    def setUp(self):
        self.stream = "stream:example-tenant-42"
        self.key = Ed25519PrivateKey.from_private_bytes(bytes([0x47] * 32))
        self.other_key = Ed25519PrivateKey.from_private_bytes(bytes([0x29] * 32))
        self.pub = self.key.public_key()
        self.pin = public_key_digest(self.pub)
        self.journal = LinkEvidenceJournal(self.stream)
        self.helper = IdentityLinkJournalTests()
        p = self.helper._proposal("v2")
        self.event = self.journal.propose(p, expected_head=genesis(self.stream))
        self.head_report = self.journal.inspect()
        self.checkpoint = sign_journal_head(self.head_report, private_key=self.key,
                                            key_ref="keys:independently-registered")

    def verify(self, *, events=None, checkpoint=None, public_key=None, pin=None,
               stream=None, head=None, count=None, key_ref=None):
        return verify_journal_head(
            self.head_report.events if events is None else events,
            self.checkpoint if checkpoint is None else checkpoint,
            public_key=self.pub if public_key is None else public_key,
            expected_stream_ref=self.stream if stream is None else stream,
            expected_head_digest=self.head_report.head_digest if head is None else head,
            expected_event_count=len(self.head_report.events) if count is None else count,
            expected_key_ref="keys:independently-registered" if key_ref is None else key_ref,
            pinned_public_key_digest=self.pin if pin is None else pin,
        )

    def no_authority(self, result):
        self.assertFalse(result.authenticated_issuer)
        self.assertFalse(result.semantic_identity_verified)
        self.assertEqual(result.trusted_time, "not_established")
        self.assertEqual(result.currentness, "not_established")
        self.assertEqual(result.authority_effect, "none")
        self.assertFalse(result.can_supersede)
        self.assertFalse(result.mutates_memory)
        self.assertEqual(result.integration_state, "evaluation_only")

    def test_valid_signature_pin_head_and_history_still_not_identity_proof(self):
        result = self.verify()
        self.assertEqual(result.cryptographic_status, "valid")
        self.assertEqual(result.head_binding_status, "match")
        self.assertEqual(result.key_pin_status, "match")
        self.assertEqual(result.key_ref_status, "match")
        self.assertEqual(result.reason_codes, ())
        self.no_authority(result)
        self.assertEqual(self.checkpoint.profile, CHECKPOINT_PROFILE)
        self.assertEqual(self.checkpoint.version, CHECKPOINT_VERSION)

    def test_signing_is_deterministic_and_never_writes_a_journal_event(self):
        old = self.journal.inspect()
        duplicate = sign_journal_head(old, private_key=self.key,
                                      key_ref="keys:independently-registered")
        self.assertEqual(duplicate, self.checkpoint)
        self.assertEqual(self.journal.inspect(), old)
        self.no_authority(self.verify())

    def test_external_head_and_event_count_mismatch_fail_binding(self):
        for kwargs in (
            {"head": genesis(self.stream)},
            {"count": 0},
            {"count": 2},
        ):
            result = self.verify(**kwargs)
            self.assertEqual(result.cryptographic_status, "valid")
            self.assertEqual(result.head_binding_status, "mismatch")
            self.no_authority(result)

    def test_truncated_valid_chain_cannot_match_pinned_later_checkpoint(self):
        result = self.verify(events=())
        self.assertEqual(result.cryptographic_status, "valid")
        self.assertEqual(result.head_binding_status, "mismatch")
        self.no_authority(result)

    def test_rehashed_alternate_history_fails_independent_head_binding(self):
        old = self.event
        p = self.helper._proposal("alternate")
        payload = proposal_payload(p)
        forged = _append_event(
            self.stream, 1, genesis(self.stream), "proposed",
            _hash(PROPOSAL_DOMAIN, payload.encode("ascii")), payload, None,
        )
        self.assertNotEqual(forged.event_digest, old.event_digest)
        outcome = self.verify(events=(forged,))
        self.assertEqual(outcome.cryptographic_status, "valid")
        self.assertEqual(outcome.head_binding_status, "mismatch")
        self.no_authority(outcome)

    def test_signed_forged_history_is_still_only_claimed_pinned_history(self):
        payload = proposal_payload(self.helper._proposal("forged"))
        forged = _append_event(self.stream, 1, genesis(self.stream), "proposed",
                               _hash(PROPOSAL_DOMAIN, payload.encode("ascii")), payload, None)
        forged_report = LinkEvidenceJournal(self.stream, (forged,)).inspect()
        signed_forgery = sign_journal_head(
            forged_report, private_key=self.other_key, key_ref="keys:other"
        )
        result = self.verify(
            events=(forged,), checkpoint=signed_forgery,
            public_key=self.other_key.public_key(),
        )
        self.assertEqual(result.cryptographic_status, "valid")
        self.assertEqual(result.head_binding_status, "mismatch")
        self.assertEqual(result.key_pin_status, "mismatch")
        self.assertEqual(result.key_ref_status, "mismatch")
        self.no_authority(result)

    def test_signer_spoofed_key_ref_and_wrong_public_key_are_rejected(self):
        result = self.verify(checkpoint=replace(self.checkpoint, key_ref="keys:stolen"))
        self.assertEqual(result.cryptographic_status, "invalid")
        self.assertEqual(result.key_ref_status, "mismatch")
        result = self.verify(public_key=self.other_key.public_key())
        self.assertEqual(result.cryptographic_status, "invalid")
        self.assertEqual(result.key_pin_status, "mismatch")
        self.no_authority(result)

    def test_correct_signature_but_wrong_independent_key_pin_does_not_authenticate(self):
        result = self.verify(pin=public_key_digest(self.other_key.public_key()))
        self.assertEqual(result.cryptographic_status, "valid")
        self.assertEqual(result.key_pin_status, "mismatch")
        self.no_authority(result)
        result = self.verify(key_ref="keys:other")
        self.assertEqual(result.cryptographic_status, "valid")
        self.assertEqual(result.key_ref_status, "mismatch")
        self.no_authority(result)

    def test_stream_substitution_never_rebinds_a_signature(self):
        wrong_stream = "stream:another-tenant"
        outcome = self.verify(stream=wrong_stream)
        self.assertEqual(outcome.head_binding_status, "invalid_history")
        self.assertEqual(outcome.cryptographic_status, "valid")
        self.no_authority(outcome)
        tampered = replace(self.checkpoint, stream_ref=wrong_stream)
        outcome = self.verify(checkpoint=tampered)
        self.assertEqual(outcome.cryptographic_status, "invalid")
        self.assertEqual(outcome.head_binding_status, "mismatch")
        self.no_authority(outcome)

    def test_contract_algorithm_and_count_changes_invalidate_signature(self):
        for changed in (
            replace(self.checkpoint, version="2.0.0"),
            replace(self.checkpoint, profile="agent-memory/another-contract"),
            replace(self.checkpoint, algorithm="RSA"),
            replace(self.checkpoint, event_count=2),
            replace(self.checkpoint, head_digest=genesis(self.stream)),
        ):
            outcome = self.verify(checkpoint=changed)
            self.assertEqual(outcome.cryptographic_status, "invalid")
            self.no_authority(outcome)

    def test_corrupt_signature_and_invalid_checkpoint_shape(self):
        for changed in (
            replace(self.checkpoint, signature_b64="????"),
            replace(self.checkpoint, signature_b64="AA=="),
            replace(self.checkpoint, signature_b64=""),
        ):
            result = self.verify(checkpoint=changed)
            self.assertEqual(result.cryptographic_status, "invalid")
            self.no_authority(result)
        result = self.verify(checkpoint={})
        self.assertEqual(result.cryptographic_status, "invalid")
        self.assertEqual(result.head_binding_status, "mismatch")
        self.no_authority(result)

    def test_corrupt_chain_is_invalid_even_with_valid_attestation(self):
        tampered = replace(self.event, sequence=2)
        result = self.verify(events=(tampered,))
        self.assertEqual(result.cryptographic_status, "valid")
        self.assertEqual(result.head_binding_status, "invalid_history")
        self.no_authority(result)

    def test_historical_signed_checkpoint_is_not_proof_of_latest_event(self):
        old = self.journal.inspect()
        self.journal.resolve(self.event.proposal_digest, kind="withdrawn",
                             reason="safely withdrawn", expected_head=old.head_digest)
        new = self.journal.inspect()
        # Existing old receipt is still a valid signature on its OLD head.
        old_result = self.verify(events=old.events)
        self.assertEqual(old_result.cryptographic_status, "valid")
        self.assertEqual(old_result.head_binding_status, "match")
        self.no_authority(old_result)
        # It cannot pass a separately pinned NEW count/head.
        new_result = self.verify(events=new.events, head=new.head_digest,
                                 count=len(new.events))
        self.assertEqual(new_result.cryptographic_status, "valid")
        self.assertEqual(new_result.head_binding_status, "mismatch")
        self.no_authority(new_result)

    def test_signed_resolution_binds_withdrawal_event_and_history(self):
        self.journal.resolve(self.event.proposal_digest, kind="disputed",
                             reason="unverified cross-origin facts",
                             expected_head=self.journal.inspect().head_digest)
        state = self.journal.inspect()
        fresh = sign_journal_head(state, private_key=self.key,
                                 key_ref="keys:independently-registered")
        good = self.verify(events=state.events, checkpoint=fresh,
                           head=state.head_digest, count=len(state.events))
        self.assertEqual(good.cryptographic_status, "valid")
        self.assertEqual(good.head_binding_status, "match")
        self.no_authority(good)

    def test_self_issued_key_pinning_can_be_consistent_without_trusted_root(self):
        # If the caller lets the signer replace BOTH public key and pin,
        # all byte-level checks pass. This explicitly proves the missing
        # independent root-of-trust is NOT supplied by the verifier.
        other_pub = self.other_key.public_key()
        other_att = sign_journal_head(
            self.head_report, private_key=self.other_key,
            key_ref="keys:self-issued",
        )
        result = self.verify(checkpoint=other_att, public_key=other_pub,
                             pin=public_key_digest(other_pub),
                             key_ref="keys:self-issued")
        self.assertEqual(result.cryptographic_status, "valid")
        self.assertEqual(result.head_binding_status, "match")
        self.assertEqual(result.key_pin_status, "match")
        self.no_authority(result)

    def test_fail_closed_expected_parameters_and_signing_inputs(self):
        for args in (
            {"count": True}, {"pin": "garbage"}, {"head": "sha256:bad"},
            {"stream": ""}, {"key_ref": ""},
        ):
            with self.assertRaises((ValueError, JournalError)):
                self.verify(**args)
        with self.assertRaises(TypeError):
            sign_journal_head(self.head_report, private_key="not-a-key",
                              key_ref="keys:test")
        altered_report = replace(self.head_report, head_digest=genesis(self.stream))
        with self.assertRaises(JournalError):
            sign_journal_head(altered_report, private_key=self.key, key_ref="keys:test")

    def test_receipts_are_immutable(self):
        report = self.verify()
        with self.assertRaises(FrozenInstanceError):
            report.semantic_identity_verified = True
        with self.assertRaises(FrozenInstanceError):
            self.checkpoint.head_digest = "something"


if __name__ == "__main__":
    import unittest
    unittest.main()
