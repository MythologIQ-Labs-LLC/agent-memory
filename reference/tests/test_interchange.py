"""Executable P7 governed memory interchange evidence."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import policy  # noqa: E402
from agentmem_ref.crossing import CrossingRequest, evaluate_crossing  # noqa: E402
from agentmem_ref.interchange import build_export_bundle, import_bundle  # noqa: E402


def memory_unit() -> dict:
    return {
        "schema_version": "1.0.0",
        "id": "mem:portable-decision",
        "type": "decision",
        "state": "crystallized",
        "scope": {
            "owner_principal": "user:alice",
            "tenant": "tenant-a",
            "project": "project-a",
            "purpose": "security-review",
            "isolation_domain_refs": ["domain:project-a"],
            "primary_isolation_domain_ref": "domain:project-a",
        },
        "sensitivity": {"labels": ["internal"]},
        "provenance": {
            "origin": "system-a",
            "observer": "agent:planner",
            "method": "governed decision",
            "timestamp": "2026-08-11T20:00:00Z",
            "source_refs": ["evidence:decision-source"],
        },
        "evidence": [
            {
                "id": "evidence:decision-source",
                "kind": "decision_record",
                "ref": "local://decision/42",
                "confidence": 1.0,
            }
        ],
        "saturation": {
            "sigma": 0.95,
            "calibrated": True,
            "durability_dimensions": ["certified_decision"],
        },
        "authority": {
            "pama_outcome": "allow_with_ledger",
            "risk_class": "medium",
            "policy_version": "sender-policy-7",
            "authority_refs": ["authority:sender"],
            "permitted_actions": ["retain"],
            "prohibited_actions": [],
            "selection_mode": "deterministic",
        },
        "created_at": "2026-08-11T20:00:00Z",
    }


def crossing(*, reviewed: bool) -> dict:
    request = CrossingRequest(
        operation="export",
        source_domain_refs=("domain:project-a",),
        destination_domain_refs=("domain:system-b-import",),
        actor="agent:planner",
        principal="user:alice",
        purpose="security-review",
        representation_kind="canonical_memory",
        source_refs=("mem:portable-decision",),
        authority_refs=("authority:sender",),
        policy_refs=("policy:sender-export",),
        provenance_refs=("evidence:decision-source",),
        before_scope_refs=("domain:project-a",),
        after_scope_refs=("domain:system-b-import",),
    )
    proposal = policy.Proposal(
        proposal_id="sender-export",
        actor_id="agent:planner",
        charter_version="charter-a",
        target_reference="mem:portable-decision",
        target_class=policy.M4,
        scope="tenant-a",
        operation="scope_expansion",
        current_strength="crystallized",
        proposed_strength="crystallized",
        downstream_authority=policy.A2,
        reversibility="reversible",
        risk_class="medium",
        evidence_refs=("evidence:decision-source",),
        review_satisfied=reviewed,
        approval_refs=("approval:sender-security-owner",) if reviewed else (),
    )
    return evaluate_crossing(
        request,
        proposal,
        receipt_id="crossing:sender-export",
        timestamp="2026-08-11T20:01:00Z",
        decision_receipt_ref="decision:sender-export",
        ledger_ref="ledger:sender-export",
    ).receipt


def receiver_proposal(*, reviewed: bool = True, owner_conflict: bool = False) -> policy.Proposal:
    return policy.Proposal(
        proposal_id="receiver-import",
        actor_id="agent:receiver",
        charter_version="charter-b",
        target_reference="mem:portable-decision",
        target_class=policy.M4,
        scope="tenant-b",
        operation="scope_expansion",
        current_strength="crystallized",
        proposed_strength="crystallized",
        downstream_authority=policy.A2,
        reversibility="reversible",
        risk_class="medium",
        evidence_refs=("crossing:sender-export",),
        review_satisfied=reviewed,
        approval_refs=("approval:receiver-security-owner",) if reviewed else (),
        actor_authority_resolved=not owner_conflict,
    )


class InterchangeTests(unittest.TestCase):
    def test_export_requires_committed_sender_crossing(self):
        with self.assertRaises(ValueError):
            build_export_bundle(
                memory_unit(),
                sender_system="system-a",
                receiver_system="system-b",
                crossing_receipt=crossing(reviewed=False),
            )

    def test_receiver_does_not_inherit_sender_allow(self):
        bundle = build_export_bundle(
            memory_unit(),
            sender_system="system-a",
            receiver_system="system-b",
            crossing_receipt=crossing(reviewed=True),
        )
        result = import_bundle(
            bundle,
            receiver_domain_ref="domain:system-b-import",
            receiver_proposal=receiver_proposal(reviewed=False),
            expected_owner_principal="user:alice",
        )
        self.assertFalse(result.admitted)
        self.assertEqual(result.decision.outcome, policy.REQUIRE_REVIEW)
        self.assertIsNone(result.memory)

    def test_ownership_conflict_fails_closed(self):
        bundle = build_export_bundle(
            memory_unit(),
            sender_system="system-a",
            receiver_system="system-b",
            crossing_receipt=crossing(reviewed=True),
        )
        result = import_bundle(
            bundle,
            receiver_domain_ref="domain:system-b-import",
            receiver_proposal=receiver_proposal(),
            expected_owner_principal="user:bob",
        )
        self.assertFalse(result.admitted)
        self.assertEqual(result.decision.outcome, policy.BLOCK)
        self.assertEqual(result.refusal, "ownership_conflict")

    def test_successful_import_preserves_semantics_and_rebinds_local_scope(self):
        original = memory_unit()
        bundle = build_export_bundle(
            original,
            sender_system="system-a",
            receiver_system="system-b",
            crossing_receipt=crossing(reviewed=True),
        )
        result = import_bundle(
            bundle,
            receiver_domain_ref="domain:system-b-import",
            receiver_proposal=receiver_proposal(),
            expected_owner_principal="user:alice",
        )

        self.assertTrue(result.admitted)
        imported = result.memory
        assert imported is not None
        self.assertEqual(imported["id"], original["id"])
        self.assertEqual(imported["state"], original["state"])
        self.assertEqual(imported["provenance"], original["provenance"])
        self.assertEqual(imported["sensitivity"], original["sensitivity"])
        self.assertEqual(imported["scope"]["owner_principal"], "user:alice")
        self.assertEqual(imported["scope"]["isolation_domain_refs"], ["domain:system-b-import"])
        self.assertEqual(imported["scope"]["source_isolation_domain_refs"], ["domain:project-a"])
        self.assertEqual(imported["authority"]["authority_refs"], ["approval:receiver-security-owner"])
        self.assertNotIn("authority:sender", imported["authority"]["authority_refs"])
        self.assertEqual(bundle.sender_authority_evidence[-1], "crossing:sender-export")


if __name__ == "__main__":
    unittest.main()
