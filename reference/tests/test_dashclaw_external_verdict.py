from __future__ import annotations

import json
import unittest

from agentmem_ref import policy
from agentmem_ref.adapter import GovernedMemoryAdapter
from agentmem_ref.dashclaw_external_verdict import (
    ACTION_CONNECTION_TEST,
    ACTION_MUTATION,
    DashClawRequestError,
    commit_bound_mutation,
    evaluate_request,
    parse_mutation_request,
    sha256_text,
)
from agentmem_ref.substrate import InMemoryTemporalGraph


ORG = "fixture-org"
AGENT = "release-agent"
PROJECT = "project:fixture"


def mutation_request(
    *,
    value: str = "release branch release",
    operation: str = "promotion",
    risk: str = "low",
    state_snapshot: str = "v0",
    input_identity: str = "sha256:dashclaw-fixture",
    target_class: str = policy.M2,
    downstream_authority: str = policy.A1,
) -> dict:
    return {
        "request_id": "evr-fixture",
        "org_id": ORG,
        "agent_id": AGENT,
        "action_type": ACTION_MUTATION,
        "declared_goal": "retain release branch memory",
        "act": {
            "kind": ACTION_MUTATION,
            "memory_value": value,
            "proposal": {
                "proposal_id": "proposal-fixture",
                "charter_version": "fixture-charter-v1",
                "target_reference": "repo:fixture:release-branch",
                "target_class": target_class,
                "scope": PROJECT,
                "operation": operation,
                "current_strength": "session",
                "proposed_strength": "durable",
                "downstream_authority": downstream_authority,
                "reversibility": "reversible",
                "risk_class": risk,
                "state_snapshot": state_snapshot,
                "purpose": "release planning",
                "isolation_domain_refs": [PROJECT],
                "required_isolation_domain_refs": [PROJECT],
                "project_ref": PROJECT,
                "evidence_refs": ["fixture:user-statement"],
                "content_sha256": sha256_text(value),
            },
        },
        "input_identity": input_identity,
    }


class DashClawExternalVerdictTests(unittest.TestCase):
    def test_connection_test_is_side_effect_free_contract_allow(self) -> None:
        request = {
            "request_id": "evr-test",
            "org_id": ORG,
            "agent_id": "dashclaw-connection-test",
            "action_type": ACTION_CONNECTION_TEST,
            "declared_goal": "DashClaw provider connection test (synthetic act — no real action follows)",
            "act": {"synthetic": True, "source": "dashclaw-policies-panel"},
            "input_identity": "sha256:dashclaw-connection-test",
        }
        response = evaluate_request(request)
        self.assertEqual(response["decision"], "allow")
        self.assertEqual(response["reason"], "connection_test_ok")
        self.assertEqual(response["input_identity"], request["input_identity"])
        self.assertEqual(response["evidence"], {"connection_test": True, "accepted": True})

    def test_input_identity_is_echoed_verbatim(self) -> None:
        request = mutation_request(input_identity="opaque:not-a-provider-digest")
        response = evaluate_request(request)
        self.assertEqual(response["input_identity"], "opaque:not-a-provider-digest")

    def test_low_risk_promotion_maps_allow_with_ledger_to_allow(self) -> None:
        response = evaluate_request(mutation_request())
        self.assertEqual(response["decision"], "allow")
        self.assertEqual(response["reason"], "pama_allow_with_ledger")
        self.assertEqual(response["evidence"]["pama_outcome"], policy.ALLOW_WITH_LEDGER)
        self.assertFalse(response["evidence"]["execution_evidence"])

    def test_correction_maps_review_to_escalate(self) -> None:
        response = evaluate_request(mutation_request(operation="correction", risk="medium", state_snapshot="v1"))
        self.assertEqual(response["decision"], "escalate")
        self.assertEqual(response["reason"], "pama_require_review")

    def test_critical_authority_scope_expansion_maps_to_deny(self) -> None:
        request = mutation_request(
            value="release branch main for every project",
            operation="scope_expansion",
            risk="critical",
            state_snapshot="v2",
            target_class=policy.M5,
            downstream_authority=policy.A5,
        )
        response = evaluate_request(request)
        self.assertEqual(response["decision"], "deny")
        self.assertEqual(response["reason"], "pama_block")

    def test_unsupported_action_fails_conservatively(self) -> None:
        request = mutation_request()
        request["action_type"] = "shell"
        response = evaluate_request(request)
        self.assertEqual(response["decision"], "deny")
        self.assertEqual(response["reason"], "unsupported_action_type")

    def test_content_drift_is_denied_before_pama(self) -> None:
        request = mutation_request()
        request["act"]["memory_value"] = "release branch main"
        response = evaluate_request(request)
        self.assertEqual(response["decision"], "deny")
        self.assertEqual(response["reason"], "content_binding_mismatch")

    def test_act_cannot_inject_actor_tenant_or_review_authority(self) -> None:
        for field, value in (
            ("actor_id", "different-agent"),
            ("tenant_ref", "other-org"),
            ("approval_refs", ["fake-approval"]),
            ("review_satisfied", True),
        ):
            with self.subTest(field=field):
                request = mutation_request()
                request["act"]["proposal"][field] = value
                response = evaluate_request(request)
                self.assertEqual(response["decision"], "deny")
                self.assertEqual(response["reason"], "authority_injection_attempt")

    def test_conflicting_org_isolation_binding_is_denied(self) -> None:
        request = mutation_request()
        request["act"]["proposal"]["isolation_domain_refs"].append("org:other-org")
        response = evaluate_request(request)
        self.assertEqual(response["decision"], "deny")
        self.assertEqual(response["reason"], "conflicting_trusted_binding")

    def test_missing_input_identity_cannot_fake_contract_verdict(self) -> None:
        request = mutation_request()
        del request["input_identity"]
        with self.assertRaises(DashClawRequestError):
            evaluate_request(request)

    def test_provider_evidence_is_bounded(self) -> None:
        response = evaluate_request(mutation_request())
        serialized = json.dumps(response["evidence"], sort_keys=True, separators=(",", ":"))
        self.assertLessEqual(len(serialized), 4096)

    def test_review_commit_requires_exact_approval_identity_and_external_actor(self) -> None:
        memory = GovernedMemoryAdapter(InMemoryTemporalGraph(), tenant=ORG)
        mutation = parse_mutation_request(
            mutation_request(operation="correction", risk="medium", state_snapshot="v0")
        )

        missing = commit_bound_mutation(memory, mutation)
        wrong_identity = commit_bound_mutation(
            memory,
            mutation,
            approval_ref="approval:1",
            approval_actor_id="operator",
            approved_input_identity="different",
        )
        self_approval = commit_bound_mutation(
            memory,
            mutation,
            approval_ref="approval:2",
            approval_actor_id=AGENT,
            approved_input_identity=mutation.input_identity,
        )

        self.assertEqual(missing.refusal, "approval_required")
        self.assertEqual(wrong_identity.refusal, "approval_identity_mismatch")
        self.assertEqual(self_approval.refusal, "self_approval_forbidden")
        self.assertEqual(memory.state_version(mutation.proposal.target_reference), 0)

    def test_blocked_provider_result_cannot_reach_substrate_via_bound_commit(self) -> None:
        substrate = InMemoryTemporalGraph()
        memory = GovernedMemoryAdapter(substrate, tenant=ORG)
        request = mutation_request(
            value="release branch main for every project",
            operation="scope_expansion",
            risk="critical",
            target_class=policy.M5,
            downstream_authority=policy.A5,
        )
        mutation = parse_mutation_request(request)
        before = tuple(substrate.write_log)
        result = commit_bound_mutation(memory, mutation)
        self.assertFalse(result.committed)
        self.assertEqual(result.refusal, "pama_blocked")
        self.assertEqual(tuple(substrate.write_log), before)


if __name__ == "__main__":
    unittest.main()
