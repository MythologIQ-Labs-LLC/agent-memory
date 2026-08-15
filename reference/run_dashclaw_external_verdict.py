#!/usr/bin/env python3
"""Execute the #279 provider-side governed durable-memory proof.

This is a deterministic provider/workload harness. It proves the Agent Memory
side of the frozen DashClaw v1 contract and the ordinary governed mutation path.
It does not claim a live public-HTTPS DashClaw deployment or process-restart
durability.
"""

from __future__ import annotations

import json

from agentmem_ref import policy
from agentmem_ref.adapter import GovernedMemoryAdapter, RecallContext
from agentmem_ref.dashclaw_external_verdict import (
    ACTION_MUTATION,
    StaticAuthorityGrant,
    StaticAuthorityResolver,
    commit_bound_mutation,
    evaluate_request,
    parse_mutation_request,
    sha256_text,
)
from agentmem_ref.substrate import InMemoryTemporalGraph

ORG = "fixture-org"
AGENT = "release-agent"
HUMAN = "operator-kevin"
PROJECT = "project:fixture"
OTHER_PROJECT = "project:other"
MEMORY_ID = "repo:fixture:release-branch"

AUTHORITY = StaticAuthorityResolver(
    (
        StaticAuthorityGrant(
            org_id=ORG,
            agent_id=AGENT,
            isolation_domain_refs=(PROJECT,),
            evidence_ref="authority-grant:fixture-release-agent",
        ),
    )
)


def _request(
    *,
    suffix: str,
    value: str,
    operation: str,
    risk: str,
    state_snapshot: str,
    target_class: str = policy.M2,
    downstream_authority: str = policy.A1,
    project_ref: str = PROJECT,
    requested_scope_change: str = "",
) -> dict:
    proposal = {
        "proposal_id": f"proposal-{suffix}",
        "charter_version": "fixture-charter-v1",
        "target_reference": MEMORY_ID,
        "target_class": target_class,
        "scope": project_ref,
        "operation": operation,
        "current_strength": "observed" if state_snapshot == "v0" else "promoted",
        "proposed_strength": "promoted",
        "downstream_authority": downstream_authority,
        "reversibility": "reversible",
        "risk_class": risk,
        "state_snapshot": state_snapshot,
        "purpose": "release planning",
        "isolation_domain_refs": [project_ref],
        "required_isolation_domain_refs": [project_ref],
        "project_ref": project_ref,
        "evidence_refs": [f"fixture:{suffix}:authoritative-statement"],
        "content_sha256": sha256_text(value),
    }
    if requested_scope_change:
        proposal["requested_scope_change"] = requested_scope_change
    return {
        "request_id": f"evr-{suffix}",
        "org_id": ORG,
        "agent_id": AGENT,
        "action_type": ACTION_MUTATION,
        "declared_goal": "retain the repository release branch for future planning",
        "act": {
            "kind": ACTION_MUTATION,
            "memory_value": value,
            "proposal": proposal,
        },
        # DashClaw owns this digest. The provider must echo it, not recompute it.
        "input_identity": f"sha256:dashclaw-{suffix}",
    }


def run() -> dict:
    substrate = InMemoryTemporalGraph()
    memory = GovernedMemoryAdapter(substrate=substrate, tenant=ORG)
    context = RecallContext(
        target_domain_refs=(f"org:{ORG}", PROJECT),
        principal_ref=AGENT,
        project_ref=PROJECT,
        purpose="release planning",
    )

    initial_request = _request(
        suffix="release-v1",
        value="release branch release",
        operation="promotion",
        risk="low",
        state_snapshot="v0",
    )
    unresolved_identity_only = evaluate_request(initial_request)
    initial_verdict = evaluate_request(initial_request, AUTHORITY)
    initial_mutation = parse_mutation_request(initial_request, AUTHORITY)
    initial_commit = commit_bound_mutation(memory, initial_mutation)
    recall_v1 = memory.governed_recall("release branch", context)

    correction_request = _request(
        suffix="release-v2",
        value="release branch main",
        operation="correction",
        risk="medium",
        state_snapshot="v1",
    )
    correction_verdict = evaluate_request(correction_request, AUTHORITY)
    correction_mutation = parse_mutation_request(correction_request, AUTHORITY)

    unapproved_correction = commit_bound_mutation(memory, correction_mutation)
    wrong_identity_approval = commit_bound_mutation(
        memory,
        correction_mutation,
        approval_ref="dashclaw-approval:wrong-identity",
        approval_actor_id=HUMAN,
        approved_input_identity="sha256:different-act",
    )
    self_approval = commit_bound_mutation(
        memory,
        correction_mutation,
        approval_ref="dashclaw-approval:self",
        approval_actor_id=AGENT,
        approved_input_identity=correction_mutation.input_identity,
    )
    correction_commit = commit_bound_mutation(
        memory,
        correction_mutation,
        approval_ref="dashclaw-approval:release-v2",
        approval_actor_id=HUMAN,
        approved_input_identity=correction_mutation.input_identity,
    )
    recall_v2 = memory.governed_recall("release branch", context)

    stale_replay = commit_bound_mutation(
        memory,
        correction_mutation,
        approval_ref="dashclaw-approval:release-v2",
        approval_actor_id=HUMAN,
        approved_input_identity=correction_mutation.input_identity,
    )

    attack_request = _request(
        suffix="org-scope-attack",
        value="release branch main for every project",
        operation="scope_expansion",
        risk="critical",
        state_snapshot="v2",
        target_class=policy.M5,
        downstream_authority=policy.A5,
        requested_scope_change="organization",
    )
    attack_verdict = evaluate_request(attack_request, AUTHORITY)
    attack_mutation = parse_mutation_request(attack_request, AUTHORITY)
    writes_before_attack = tuple(substrate.write_log)
    attack_commit = commit_bound_mutation(memory, attack_mutation)
    writes_after_attack = tuple(substrate.write_log)

    unauthorized_request = _request(
        suffix="unauthorized-project",
        value="release branch main",
        operation="promotion",
        risk="low",
        state_snapshot="v2",
        project_ref=OTHER_PROJECT,
    )
    unauthorized_verdict = evaluate_request(unauthorized_request, AUTHORITY)
    unauthorized_mutation = parse_mutation_request(unauthorized_request, AUTHORITY)
    writes_before_unauthorized = tuple(substrate.write_log)
    unauthorized_commit = commit_bound_mutation(memory, unauthorized_mutation)
    writes_after_unauthorized = tuple(substrate.write_log)

    cross_project = memory.governed_recall(
        "release branch",
        RecallContext(
            target_domain_refs=(f"org:{ORG}", OTHER_PROJECT),
            principal_ref="other-agent",
            project_ref=OTHER_PROJECT,
            purpose="release planning",
        ),
    )

    current_uuid = memory.current_fact_uuid(MEMORY_ID)
    current_fact = substrate.get_fact(current_uuid) if current_uuid else None
    v1_fact = substrate.get_fact(initial_commit.adapter_result.fact_uuid) if initial_commit.adapter_result else None

    report = {
        "schema_version": "1.0.0",
        "dashclaw_contract": "external-verdict-v1@v5.24.0",
        "provider_scope": [ACTION_MUTATION],
        "cross_session_not_restart": True,
        "authority_boundary": {
            "identity_only_decision": unresolved_identity_only["decision"],
            "identity_only_authority_resolved": unresolved_identity_only["evidence"]["authority_resolved"],
            "resolved_authority_evidence": initial_verdict["evidence"]["authority_evidence_ref"],
        },
        "initial": {
            "provider_decision": initial_verdict["decision"],
            "provider_identity_echo": initial_verdict["input_identity"] == initial_request["input_identity"],
            "provider_execution_evidence": initial_verdict["evidence"]["execution_evidence"],
            "committed": initial_commit.committed,
            "receipt_id": initial_commit.adapter_result.receipt["receipt_id"] if initial_commit.adapter_result else None,
            "recall_admitted": list(recall_v1.admitted),
        },
        "correction": {
            "provider_decision": correction_verdict["decision"],
            "unapproved_refusal": unapproved_correction.refusal,
            "wrong_identity_refusal": wrong_identity_approval.refusal,
            "self_approval_refusal": self_approval.refusal,
            "committed": correction_commit.committed,
            "receipt_id": correction_commit.adapter_result.receipt["receipt_id"] if correction_commit.adapter_result else None,
            "state_version": memory.state_version(MEMORY_ID),
            "current_value": current_fact.fact_text if current_fact else None,
            "old_value_event_invalid": bool(v1_fact and v1_fact.is_event_invalid),
            "recall_admitted": list(recall_v2.admitted),
            "recall_refusals": dict(recall_v2.refusals),
        },
        "stale_replay": {
            "committed": stale_replay.committed,
            "refusal": stale_replay.refusal,
        },
        "scope_attack": {
            "provider_decision": attack_verdict["decision"],
            "committed": attack_commit.committed,
            "refusal": attack_commit.refusal,
            "substrate_untouched": writes_before_attack == writes_after_attack,
        },
        "unauthorized_project": {
            "provider_decision": unauthorized_verdict["decision"],
            "authority_resolved": unauthorized_verdict["evidence"]["authority_resolved"],
            "authority_reason": unauthorized_verdict["evidence"]["authority_reason"],
            "committed": unauthorized_commit.committed,
            "refusal": unauthorized_commit.refusal,
            "substrate_untouched": writes_before_unauthorized == writes_after_unauthorized,
        },
        "cross_project_recall": {
            "candidate_count": len(cross_project.candidates),
            "admitted": list(cross_project.admitted),
            "refusals": dict(cross_project.refusals),
        },
    }

    assert report["authority_boundary"]["identity_only_decision"] == "deny"
    assert report["authority_boundary"]["identity_only_authority_resolved"] is False
    assert report["authority_boundary"]["resolved_authority_evidence"] == "authority-grant:fixture-release-agent"

    assert report["initial"]["provider_decision"] == "allow"
    assert report["initial"]["provider_identity_echo"] is True
    assert report["initial"]["provider_execution_evidence"] is False
    assert report["initial"]["committed"] is True
    assert report["initial"]["recall_admitted"]

    assert report["correction"]["provider_decision"] == "escalate"
    assert report["correction"]["unapproved_refusal"] == "approval_required"
    assert report["correction"]["wrong_identity_refusal"] == "approval_identity_mismatch"
    assert report["correction"]["self_approval_refusal"] == "self_approval_forbidden"
    assert report["correction"]["committed"] is True
    assert report["correction"]["state_version"] == 2
    assert report["correction"]["current_value"] == "release branch main"
    assert report["correction"]["old_value_event_invalid"] is True
    assert current_uuid in report["correction"]["recall_admitted"]
    assert initial_commit.adapter_result.fact_uuid in report["correction"]["recall_refusals"]

    assert report["stale_replay"] == {"committed": False, "refusal": "stale_authorization"}
    assert report["scope_attack"]["provider_decision"] == "deny"
    assert report["scope_attack"]["committed"] is False
    assert report["scope_attack"]["refusal"] == "pama_blocked"
    assert report["scope_attack"]["substrate_untouched"] is True

    assert report["unauthorized_project"]["provider_decision"] == "deny"
    assert report["unauthorized_project"]["authority_resolved"] is False
    assert report["unauthorized_project"]["authority_reason"] == "authority_grant_not_found"
    assert report["unauthorized_project"]["committed"] is False
    assert report["unauthorized_project"]["refusal"] == "pama_blocked"
    assert report["unauthorized_project"]["substrate_untouched"] is True

    assert report["cross_project_recall"]["candidate_count"] >= 1
    assert report["cross_project_recall"]["admitted"] == []

    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
