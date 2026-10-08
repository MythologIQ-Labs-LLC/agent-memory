"""#757 J01-J14: hash-chain consistency without semantic-identity authority.

Tests only opaque typed evidence claims, not frozen #732/MESA phrases, gold
labels, a provider, production runtime, or a real trust-root verifier.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from unittest import TestCase
from unittest.mock import patch

from agentmem_ref.evaluation.identity_link_journal import (
    CONTRACT,
    JournalError,
    LinkEvidenceJournal,
    MAX_EVENTS,
    _append_event,
    _event_hash,
    _hash,
    _json_bytes,
    _load_proposal,
    genesis,
    proposal_payload,
    replay,
    PROPOSAL_DOMAIN,
)
from tests.test_proposition_link_preflight import proposed, claims, write


class IdentityLinkJournalTests(TestCase):
    def setUp(self):
        self.stream = "stream:tenant-A/case-9"
        self.journal = LinkEvidenceJournal(self.stream)

    def _proposal(self, suffix="2"):
        return proposed(
            newer=write(
                revision=f"revision:new-{suffix}",
                fact=f"fact:new-{suffix}", value=f"value:revision-{suffix}"
            )
        )

    def _append(self, proposal=None):
        return self.journal.propose(
            proposal or self._proposal(),
            expected_head=self.journal.inspect().head_digest,
        )

    def assert_non_authority(self, report):
        self.assertEqual(report.authority_effect, "none")
        self.assertFalse(report.identity_verified)
        self.assertFalse(report.can_supersede)
        self.assertFalse(report.mutates_memory)
        self.assertEqual(report.integration_state, "evaluation_only")

    def test_genesis_and_one_event_are_stable_across_instances(self):
        self.assertEqual(self.journal.inspect().head_digest, genesis(self.stream))
        self.assertNotEqual(genesis(self.stream), genesis("stream:another"))
        event = self._append()
        snapshot = self.journal.inspect()
        self.assertEqual(len(snapshot.events), 1)
        self.assertEqual(event.previous_digest, genesis(self.stream))
        self.assertEqual(event.sequence, 1)
        self.assertEqual(event.kind, "proposed")
        self.assertEqual(event.proposal_digest,
                         _hash(PROPOSAL_DOMAIN, event.proposal_payload.encode("ascii")))
        self.assertEqual(snapshot.proposal_states, ((event.proposal_digest, "under_review"),))
        self.assertEqual(snapshot, replay(self.stream, snapshot.events))
        self.assert_non_authority(snapshot)

    def test_serialized_replay_is_equal_and_preserves_claims(self):
        p = self._proposal()
        e = self._append(p)
        stored = json.loads(e.proposal_payload)
        self.assertEqual(stored["contract"], CONTRACT)
        self.assertEqual(stored["proposal"]["older"]["revision_ref"], p.older.revision_ref)
        self.assertEqual(stored["proposal"]["newer"]["revision_ref"], p.newer.revision_ref)
        self.assertEqual(len(stored["proposal"]["claims"]), len(p.claims))
        self.assertEqual(proposal_payload(_load_proposal(e.proposal_payload)), e.proposal_payload)
        self.assertEqual(replay(self.stream, (e,)), self.journal.inspect())

    def test_withdraw_does_not_erase_proposal_or_create_approval(self):
        e = self._append()
        r = self.journal.resolve(
            e.proposal_digest, kind="withdrawn",
            reason="independent review failed", expected_head=e.event_digest
        )
        report = self.journal.inspect()
        self.assertEqual([x.kind for x in report.events], ["proposed", "withdrawn"])
        self.assertIsNotNone(report.events[0].proposal_payload)
        self.assertEqual(r.proposal_payload, None)
        self.assertEqual(report.proposal_states, ((e.proposal_digest, "withdrawn"),))
        self.assert_non_authority(report)
        self.assertEqual(report, replay(self.stream, report.events))

    def test_dispute_is_recorded_as_uncertain_not_accepted(self):
        e = self._append()
        self.journal.resolve(e.proposal_digest, kind="disputed", reason="conflicting source",
                             expected_head=e.event_digest)
        state = self.journal.inspect()
        self.assertEqual(state.proposal_states, ((e.proposal_digest, "disputed"),))
        self.assert_non_authority(state)
        with self.assertRaises(JournalError):
            self.journal.resolve(e.proposal_digest, kind="withdrawn", reason="again",
                                 expected_head=state.head_digest)

    def test_stale_head_does_not_append_and_does_not_overwrite_first_writer(self):
        initial = genesis(self.stream)
        first = self.journal.propose(self._proposal("2"), expected_head=initial)
        before = self.journal.inspect()
        with self.assertRaises(JournalError):
            self.journal.propose(self._proposal("3"), expected_head=initial)
        self.assertEqual(self.journal.inspect(), before)
        second = self.journal.propose(self._proposal("3"), expected_head=first.event_digest)
        self.assertEqual(second.previous_digest, first.event_digest)
        self.assertEqual(self.journal.inspect().head_digest, second.event_digest)

    def test_concurrent_same_head_accepts_exactly_one_distinct_proposal(self):
        expected = genesis(self.stream)
        def run(suffix):
            try:
                return self.journal.propose(self._proposal(suffix), expected_head=expected)
            except JournalError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, ("31", "32")))
        self.assertEqual(sum(e is not None for e in results), 1)
        self.assertEqual(len(self.journal.inspect().events), 1)
        self.assert_non_authority(self.journal.inspect())

    def test_duplicate_proposal_digest_refused_even_at_new_head(self):
        p = self._proposal()
        self._append(p)
        before = self.journal.inspect()
        with self.assertRaises(JournalError):
            self.journal.propose(p, expected_head=before.head_digest)
        self.assertEqual(self.journal.inspect(), before)

    def test_unknown_and_duplicate_resolutions_are_refused(self):
        before = self.journal.inspect()
        with self.assertRaises(JournalError):
            self.journal.resolve(
                "sha256:"+"0"*64, kind="disputed",
                reason="nonexistent", expected_head=before.head_digest
            )
        self.assertEqual(before, self.journal.inspect())
        e = self._append()
        with self.assertRaises(JournalError):
            self.journal.resolve(e.proposal_digest, kind="approved",
                                 reason="not a valid mode", expected_head=e.event_digest)
        with self.assertRaises(JournalError):
            self.journal.resolve(e.proposal_digest, kind="withdrawn",
                                 reason="", expected_head=e.event_digest)
        self.assertEqual(self.journal.inspect().events, (e,))

    def test_preflight_rejections_do_not_write_to_journal(self):
        base = self._proposal()
        refused = [
            replace(base, newer=replace(base.newer, tenant_ref="tenant:other")),
            replace(base, newer=replace(base.newer, scope_ref="scope:other")),
            replace(base, newer=replace(base.newer, cardinality="multi")),
            replace(base, newer=replace(base.newer, value_ref=base.older.value_ref)),
            replace(base, observed_head_ref="old-stale-source-head"),
            replace(base, older=replace(base.older, lifecycle_state="disputed")),
        ]
        prior = self.journal.inspect()
        for p in refused:
            with self.assertRaises(JournalError):
                self.journal.propose(p, expected_head=prior.head_digest)
            self.assertEqual(self.journal.inspect(), prior)

    def test_underdetermined_different_property_is_still_unverified(self):
        p = replace(self._proposal(), newer=replace(self._proposal().newer,
                                                   property_ref="property:alt"))
        e = self._append(p)
        self.assertIn("property_identity_requires_independent_crosswalk",
                      json.loads(e.proposal_payload)["preflight"]["reasons"])
        self.assert_non_authority(self.journal.inspect())

    def test_single_model_origin_does_not_become_independent_trust(self):
        c = claims()[0]
        p = replace(self._proposal(), claims=(c, replace(c, evidence_ref="evidence:2")))
        e = self._append(p)
        body = json.loads(e.proposal_payload)
        self.assertIn("identity_evidence_has_single_claimed_origin",
                      body["preflight"]["reasons"])
        self.assert_non_authority(self.journal.inspect())

    def test_content_digest_binds_every_semantically_relevant_claimed_field(self):
        p = self._proposal()
        original = proposal_payload(p)
        variants = [
            replace(p, older=replace(p.older, property_ref="property:other")),
            replace(p, newer=replace(p.newer, actor_ref="actor:other")),
            replace(p, newer=replace(p.newer, source_ref="source:other")),
            replace(p, newer=replace(p.newer, value_ref="new:value")),
            replace(p, older=replace(p.older, subject_ref="subject:other")),
            replace(p, older=replace(p.older, purpose_ref="purpose:other")),
            replace(p, newer=replace(p.newer, revision_ref="revision:v3")),
            replace(p, claims=(replace(claims()[0], evidence_ref="evidence:new"), claims()[1])),
            replace(p, expected_head_ref="source-revision:new"),
        ]
        for variant in variants:
            if variant.newer.value_ref == variant.older.value_ref:
                continue
            self.assertNotEqual(proposal_payload(variant), original)
            self.assertNotEqual(
                _hash(PROPOSAL_DOMAIN, proposal_payload(variant).encode("ascii")),
                _hash(PROPOSAL_DOMAIN, original.encode("ascii")),
            )

    def test_truncation_order_stream_and_sequence_are_rejected(self):
        first = self._append(self._proposal("2"))
        second = self._append(self._proposal("3"))
        events = self.journal.inspect().events
        self.assertEqual(events, (first, second))
        with self.assertRaises(JournalError):
            replay("stream:different", events)
        with self.assertRaises(JournalError):
            replay(self.stream, events[::-1])
        with self.assertRaises(JournalError):
            replay(self.stream, (second,))
        with self.assertRaises(JournalError):
            replay(self.stream, (replace(first, sequence=2),))
        self.assertNotEqual(replay(self.stream, (first,)).head_digest,
                            self.journal.inspect().head_digest)

    def test_tampered_event_content_and_claims_fail_without_hash_rewrite(self):
        e = self._append()
        cases = (
            replace(e, kind="withdrawn"),
            replace(e, proposal_digest="sha256:"+"e"*64),
            replace(e, previous_digest="sha256:"+"0"*64),
            replace(e, event_digest="sha256:"+"0"*64),
            replace(e, stream_ref="stream:other"),
            replace(e, proposal_payload=e.proposal_payload.replace("source:owner", "source:alien")),
        )
        for tampered in cases:
            with self.assertRaises(JournalError):
                replay(self.stream, (tampered,))

    def test_full_rehash_of_forged_history_is_not_external_authenticity(self):
        # Anyone holding an untrusted chain can rewrite and recompute receipts.
        # This demonstrates exactly WHY there is no provenance/truth claim.
        p = self._proposal()
        e = self._append(p)
        different = replace(p, newer=replace(p.newer, value_ref="different"))
        alternate_payload = proposal_payload(different)
        forged = _append_event(
            self.stream, 1, genesis(self.stream), "proposed",
            _hash(PROPOSAL_DOMAIN, alternate_payload.encode("ascii")),
            alternate_payload, None,
        )
        self.assertNotEqual(e.event_digest, forged.event_digest)
        result = replay(self.stream, (forged,))
        self.assert_non_authority(result)
        self.assertNotEqual(self.journal.inspect().head_digest, result.head_digest)

    def test_unknown_kind_and_noncanonical_payload_fail_even_if_rehashed(self):
        e = self._append()
        bad = _append_event(
            self.stream, 1, genesis(self.stream), "accepted",
            e.proposal_digest, e.proposal_payload, None,
        )
        with self.assertRaises(JournalError):
            replay(self.stream, (bad,))
        serialized = json.loads(e.proposal_payload)
        changed = json.dumps(serialized, indent=2) + "\n"
        noncanonical = _append_event(
            self.stream, 1, genesis(self.stream), "proposed",
            e.proposal_digest, changed, None,
        )
        with self.assertRaises(JournalError):
            replay(self.stream, (noncanonical,))

    def test_event_and_inspection_receipts_immutable(self):
        event = self._append()
        report = self.journal.inspect()
        with self.assertRaises(FrozenInstanceError):
            event.kind = "accepted"
        with self.assertRaises(FrozenInstanceError):
            report.can_supersede = True
        self.assertIs(type(report.events), tuple)

    def test_load_existing_history_preserves_head_and_proposal_status(self):
        e = self._append()
        self.journal.resolve(e.proposal_digest, kind="disputed", reason="semantic doubt",
                             expected_head=e.event_digest)
        events = self.journal.inspect().events
        another = LinkEvidenceJournal(self.stream, events)
        self.assertEqual(another.inspect(), self.journal.inspect())
        with self.assertRaises(JournalError):
            another.resolve(e.proposal_digest, kind="withdrawn", reason="double",
                            expected_head=another.inspect().head_digest)

    def test_invalid_shapes_and_size_guard_reject_untrusted_inputs(self):
        with self.assertRaises(JournalError):
            LinkEvidenceJournal("\n")
        with self.assertRaises(JournalError):
            replay(self.stream, [])
        with self.assertRaises(JournalError):
            replay(self.stream, tuple([object()]))
        with self.assertRaises(JournalError):
            replay(self.stream, tuple([object()]*129))
        e = self._append()
        with self.assertRaises(JournalError):
            replay(self.stream, (replace(e, sequence=True),))
        with self.assertRaises(JournalError):
            _load_proposal('{"contract":"bad"}')
        with self.assertRaises(JournalError):
            _load_proposal(e.proposal_payload + "{}")
        with self.assertRaises(JournalError):
            _load_proposal(e.proposal_payload + (" " * 16500))

    def test_journal_cap_is_bounded_without_removing_old_evidence(self):
        e = self._append()
        with patch("agentmem_ref.evaluation.identity_link_journal.MAX_EVENTS", 1):
            before = self.journal.inspect()
            with self.assertRaises(JournalError):
                self.journal.resolve(e.proposal_digest, kind="withdrawn", reason="full",
                                     expected_head=before.head_digest)
            self.assertEqual(before, self.journal.inspect())


if __name__ == "__main__":
    import unittest
    unittest.main()
