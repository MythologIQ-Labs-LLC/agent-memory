"""#757 J57-J72: independent opaque policy-lineage falsification fixtures.

No #732/R6 benchmark inputs, model calls, production memory writes or claims
that a valid local hash chain is a trustworthy historical authority.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentmem_ref.evaluation.issuer_policy import (
    IssuerGrant, IssuerPolicySnapshot,
)
from agentmem_ref.evaluation.issuer_policy_lineage import (
    MAX_TRANSITIONS, PolicyLineage, PolicyLineageError,
    genesis_head, replay_policy_lineage, verify_policy_lineage,
)
from agentmem_ref.memory.temporal_trust import public_key_digest


class PolicyLineageTests(unittest.TestCase):
    def setUp(self):
        self.first_key = Ed25519PrivateKey.from_private_bytes(bytes([0x51] * 32))
        self.second_key = Ed25519PrivateKey.from_private_bytes(bytes([0x52] * 32))
        self.first_digest = public_key_digest(self.first_key.public_key())
        self.second_digest = public_key_digest(self.second_key.public_key())
        self.grant = IssuerGrant(
            schema_ref="schema:opaque-4", registry_revision_ref="registry-rev:7",
            tenant_ref="tenant:one", scope_ref="scope:isolated",
            purpose_ref="purpose:trace", issuer_key_ref="issuer:key-1",
            public_key_digest=self.first_digest,
        )
        self.start = IssuerPolicySnapshot(
            policy_ref="policy:opaque",
            revision_ref="policy-rev:1",
            grants=(self.grant,),
        )
        self.timeline = PolicyLineage(self.start)

    def revised(self, revision="policy-rev:2", **kw):
        return replace(self.start, revision_ref=revision, **kw)

    def deny_all(self, revision="policy-rev:2"):
        return self.revised(
            revision,
            grants=(replace(self.grant, state="revoked"),),
            revoked_key_digests=(self.first_digest,),
            invalidated_registry_revisions=(("schema:opaque-4", "registry-rev:7"),),
        )

    def assert_denied_authority(self, obj):
        self.assertFalse(obj.issuer_authorized)
        self.assertFalse(obj.identity_verified)
        self.assertFalse(obj.can_supersede)
        self.assertFalse(obj.mutates_memory)
        self.assertEqual(obj.authority_effect, "none")
        self.assertEqual(obj.integration_state, "evaluation_only")
        self.assertEqual(obj.currentness, "not_established")

    def test_genesis_replay_and_independent_pins_match_mechanically_only(self):
        orig = self.timeline.report()
        event = self.timeline.append(self.deny_all(), expected_head=orig.head_digest)
        report = self.timeline.report()
        self.assertEqual(report.genesis_head, orig.head_digest)
        self.assertEqual(report.head_digest, event.head_digest)
        self.assertEqual(replay_policy_lineage(self.start, report.events), report)
        match = verify_policy_lineage(
            self.start, report.events, expected_genesis_head=orig.genesis_head,
            expected_current_head=report.head_digest, expected_event_count=1,
        )
        self.assertEqual(match.status, "mechanical_match")
        self.assertIn("lineage_pin_provenance_and_freshness_unauthenticated",
                      match.reason_codes)
        self.assert_denied_authority(match)
        self.assert_denied_authority(report)

    def test_old_consistent_prefix_fails_fresh_expected_head(self):
        orig = self.timeline.report()
        self.timeline.append(self.deny_all(), expected_head=orig.head_digest)
        current = self.timeline.report()
        old = verify_policy_lineage(
            self.start, (), expected_genesis_head=orig.genesis_head,
            expected_current_head=current.head_digest, expected_event_count=1,
        )
        self.assertEqual(old.status, "pin_mismatch")
        self.assertFalse(old.head_matches)
        self.assertFalse(old.count_matches)
        self.assert_denied_authority(old)

    def test_stale_competing_append_fails_without_state_change(self):
        origin = self.timeline.report()
        first = self.revised()
        self.timeline.append(first, expected_head=origin.head_digest)
        checkpoint = self.timeline.report()
        with self.assertRaises(PolicyLineageError):
            self.timeline.append(self.deny_all(), expected_head=origin.head_digest)
        self.assertEqual(self.timeline.report(), checkpoint)

    def test_two_concurrent_writers_contend_for_one_head(self):
        base = self.timeline.report()
        def contender(i):
            try:
                self.timeline.append(self.revised(f"policy-rev:{i}"),
                                     expected_head=base.head_digest)
                return "appended"
            except PolicyLineageError:
                return "stale"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(contender, (2, 3)))
        self.assertEqual(sorted(outcomes), ["appended", "stale"])
        self.assertEqual(len(self.timeline.report().events), 1)

    def test_unchanged_revision_and_cross_policy_refuse(self):
        original = self.timeline.report()
        for bad in (
            self.start,
            replace(self.revised(), policy_ref="policy:other"),
        ):
            with self.assertRaises(PolicyLineageError):
                self.timeline.append(bad, expected_head=original.head_digest)
            self.assertEqual(self.timeline.report(), original)

    def test_revoked_key_cannot_disappear_from_later_policy(self):
        original = self.timeline.report()
        self.timeline.append(self.deny_all(), expected_head=original.head_digest)
        before = self.timeline.report()
        without_key = replace(self.deny_all("policy-rev:3"), revoked_key_digests=())
        with self.assertRaisesRegex(PolicyLineageError, "revocation cannot be removed"):
            self.timeline.append(without_key, expected_head=before.head_digest)
        self.assertEqual(self.timeline.report(), before)

    def test_invalidated_registry_revision_cannot_disappear(self):
        original = self.timeline.report()
        self.timeline.append(self.deny_all(), expected_head=original.head_digest)
        before = self.timeline.report()
        without_revocation = replace(
            self.deny_all("policy-rev:3"), invalidated_registry_revisions=(),
        )
        with self.assertRaisesRegex(PolicyLineageError, "invalidation cannot be removed"):
            self.timeline.append(without_revocation, expected_head=before.head_digest)
        self.assertEqual(self.timeline.report(), before)

    def test_revoked_grant_cannot_be_resurrected_or_rewritten(self):
        old = self.timeline.report()
        self.timeline.append(
            self.revised(grants=(replace(self.grant, state="revoked"),)),
            expected_head=old.head_digest,
        )
        before = self.timeline.report()
        for bad_grant in (
            self.grant, replace(self.grant, state="revoked",
                                public_key_digest=self.second_digest),
        ):
            with self.assertRaises(PolicyLineageError):
                self.timeline.append(
                    replace(self.revised("policy-rev:3"), grants=(bad_grant,)),
                    expected_head=before.head_digest,
                )
            self.assertEqual(self.timeline.report(), before)

    def test_removing_scope_without_explicit_tombstone_refused(self):
        first = self.timeline.report()
        with self.assertRaisesRegex(PolicyLineageError, "silently removed"):
            self.timeline.append(self.revised(grants=()), expected_head=first.head_digest)
        self.assertEqual(self.timeline.report(), first)

    def test_key_rotation_requires_retiring_old_key_material(self):
        start = self.timeline.report()
        rotated_grant = replace(
            self.grant, issuer_key_ref="issuer:key-2",
            public_key_digest=self.second_digest,
        )
        changed = self.revised(grants=(rotated_grant,))
        with self.assertRaisesRegex(PolicyLineageError, "rotation requires"):
            self.timeline.append(changed, expected_head=start.head_digest)
        self.assertEqual(self.timeline.report(), start)
        explicit = replace(changed, revoked_key_digests=(self.first_digest,))
        event = self.timeline.append(explicit, expected_head=start.head_digest)
        self.assertEqual(event.sequence, 1)
        self.assertEqual(self.timeline.report().events[0].snapshot, explicit)
        self.assert_denied_authority(self.timeline.report())

    def test_key_ref_swap_with_same_key_material_refused(self):
        before = self.timeline.report()
        changed = self.revised(grants=(replace(
            self.grant, issuer_key_ref="issuer:renamed",
        ),), revoked_key_digests=(self.first_digest,))
        with self.assertRaisesRegex(PolicyLineageError, "rotation requires"):
            self.timeline.append(changed, expected_head=before.head_digest)

    def test_grant_tombstone_preserves_original_issuer(self):
        old = self.timeline.report()
        changed = self.revised(grants=(replace(
            self.grant, state="revoked", issuer_key_ref="issuer:replacement",
        ),))
        with self.assertRaisesRegex(PolicyLineageError, "tombstone"):
            self.timeline.append(changed, expected_head=old.head_digest)

    def test_tamper_digest_payload_or_previous_head_fails_replay(self):
        old = self.timeline.report()
        self.timeline.append(self.deny_all(), expected_head=old.head_digest)
        event = self.timeline.report().events[0]
        alternate = self.deny_all("policy-rev:other")
        for corrupt in (
            replace(event, sequence=2),
            replace(event, snapshot=alternate),
            replace(event, snapshot_digest=old.genesis_head),
            replace(event, previous_head=event.head_digest),
            replace(event, head_digest=old.genesis_head),
        ):
            with self.assertRaises(PolicyLineageError):
                replay_policy_lineage(self.start, (corrupt,))
            check = verify_policy_lineage(
                self.start, (corrupt,), expected_genesis_head=old.genesis_head,
                expected_current_head=event.head_digest, expected_event_count=1,
            )
            self.assertEqual(check.status, "invalid_history")
            self.assert_denied_authority(check)

    def test_event_order_duplication_and_truncation(self):
        first = self.timeline.report()
        self.timeline.append(self.revised(), expected_head=first.head_digest)
        halfway = self.timeline.report()
        self.timeline.append(self.deny_all("policy-rev:3"),
                             expected_head=halfway.head_digest)
        final = self.timeline.report()
        with self.assertRaises(PolicyLineageError):
            replay_policy_lineage(self.start, tuple(reversed(final.events)))
        with self.assertRaises(PolicyLineageError):
            replay_policy_lineage(self.start, (final.events[0], final.events[0]))
        truncated = verify_policy_lineage(
            self.start, (final.events[0],), expected_genesis_head=first.genesis_head,
            expected_current_head=final.head_digest, expected_event_count=2,
        )
        self.assertEqual(truncated.status, "pin_mismatch")
        self.assert_denied_authority(truncated)

    def test_substituted_genesis_refuses_independently_pinned_genesis(self):
        start = self.timeline.report()
        forged_genesis = replace(self.start, policy_ref="policy:forged")
        verdict = verify_policy_lineage(
            forged_genesis, (), expected_genesis_head=start.genesis_head,
            expected_current_head=start.head_digest, expected_event_count=0,
        )
        self.assertEqual(verdict.status, "pin_mismatch")
        self.assertFalse(verdict.genesis_matches)
        self.assert_denied_authority(verdict)

    def test_attacker_rehashes_all_history_and_supplies_own_pins(self):
        fake = replace(self.start, policy_ref="policy:attacker")
        timeline = PolicyLineage(fake)
        initial = timeline.report()
        timeline.append(replace(fake, revision_ref="policy-rev:forged"),
                        expected_head=initial.head_digest)
        fabricated = timeline.report()
        verified = verify_policy_lineage(
            fake, fabricated.events,
            expected_genesis_head=fabricated.genesis_head,
            expected_current_head=fabricated.head_digest,
            expected_event_count=len(fabricated.events),
        )
        self.assertEqual(verified.status, "mechanical_match")
        self.assert_denied_authority(verified)

    def test_wrong_count_and_malformed_events_fail_closed(self):
        start = self.timeline.report()
        bad_count = verify_policy_lineage(
            self.start, (), expected_genesis_head=start.genesis_head,
            expected_current_head=start.head_digest, expected_event_count=1,
        )
        self.assertEqual(bad_count.status, "pin_mismatch")
        self.assertFalse(bad_count.count_matches)
        for raw in ([], (object(),)):
            with self.assertRaises(PolicyLineageError):
                replay_policy_lineage(self.start, raw)
        with self.assertRaises(ValueError):
            verify_policy_lineage(
                self.start, (), expected_genesis_head=start.genesis_head,
                expected_current_head=start.head_digest, expected_event_count=True,
            )
        self.assert_denied_authority(bad_count)

    def test_bounded_transitions_and_no_mutation_after_limit(self):
        head = self.timeline.report().head_digest
        for sequence in range(MAX_TRANSITIONS):
            snap = self.revised(f"policy-rev:bounded-{sequence}")
            event = self.timeline.append(snap, expected_head=head)
            head = event.head_digest
        before = self.timeline.report()
        self.assertEqual(len(before.events), MAX_TRANSITIONS)
        self.assertEqual(replay_policy_lineage(self.start, before.events), before)
        with self.assertRaisesRegex(PolicyLineageError, "limit"):
            self.timeline.append(self.revised("policy-rev:overflow"),
                                 expected_head=head)
        self.assertEqual(self.timeline.report(), before)

    def test_immutable_event_and_report(self):
        start = self.timeline.report()
        event = self.timeline.append(self.revised(), expected_head=start.head_digest)
        report = self.timeline.report()
        with self.assertRaises(FrozenInstanceError):
            event.sequence = 100
        with self.assertRaises(FrozenInstanceError):
            report.head_digest = start.head_digest
        self.assert_denied_authority(report)


if __name__ == "__main__":
    unittest.main()
