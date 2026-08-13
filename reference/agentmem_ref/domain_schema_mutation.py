"""Version and compatibility helpers for governed domain-schema mutation."""

from __future__ import annotations

from . import policy, receipts

DOMAIN_SCHEMA_MUTATION = "domain_schema_mutation"
PAMA_SCHEMA_VERSION = "1.2.0"


def required_outcome_for_risk(risk_class: str) -> str:
    """Return the explicit minimum PAMA posture for a domain-schema mutation."""
    if risk_class in ("low", "medium"):
        return policy.REQUIRE_REVIEW
    if risk_class in ("high", "critical"):
        return policy.REQUIRE_EXTERNAL_VERIFICATION
    raise ValueError(f"unsupported risk class {risk_class!r}")


def enforce_scope_floor(decision: policy.Decision, proposal: policy.Proposal) -> policy.Decision:
    """Preserve the existing scope-expansion floor when ontology change widens scope."""
    if not proposal.requested_scope_change:
        return decision
    scope_proposal = policy.Proposal(
        proposal_id=proposal.proposal_id,
        actor_id=proposal.actor_id,
        charter_version=proposal.charter_version,
        target_reference=proposal.target_reference,
        target_class=proposal.target_class,
        scope=proposal.scope,
        operation="scope_expansion",
        current_strength=proposal.current_strength,
        proposed_strength=proposal.proposed_strength,
        downstream_authority=proposal.downstream_authority,
        reversibility=proposal.reversibility,
        risk_class=proposal.risk_class,
        evidence_refs=proposal.evidence_refs,
        estimator_refs=proposal.estimator_refs,
        estimator_versions=proposal.estimator_versions,
        confidence=proposal.confidence,
        actor_authority_resolved=proposal.actor_authority_resolved,
        approves_own_authority=proposal.approves_own_authority,
        approval_refs=proposal.approval_refs,
        review_satisfied=proposal.review_satisfied,
        state_snapshot=proposal.state_snapshot,
        tenant_ref=proposal.tenant_ref,
        purpose=proposal.purpose,
        isolation_domain_refs=proposal.isolation_domain_refs,
        required_isolation_domain_refs=proposal.required_isolation_domain_refs,
        project_ref=proposal.project_ref,
        task_ref=proposal.task_ref,
    )
    scope_decision = policy.evaluate(scope_proposal)
    order = {
        policy.ALLOW: 0,
        policy.ALLOW_WITH_LEDGER: 1,
        policy.REQUIRE_REVIEW: 2,
        policy.REQUIRE_EXTERNAL_VERIFICATION: 3,
        policy.BLOCK: 4,
    }
    if order[scope_decision.outcome] <= order[decision.outcome]:
        return decision
    permitted, prohibited = _envelope(scope_decision.outcome, proposal.operation)
    return policy.Decision(
        outcome=scope_decision.outcome,
        permitted_actions=permitted,
        prohibited_actions=prohibited,
        reasons=decision.reasons + ("scope-expansion floor preserved",),
        policy_version=decision.policy_version,
    )


def evaluate(proposal: policy.Proposal) -> policy.Decision:
    """Evaluate the new operation without letting estimator output weaken its floor."""
    if proposal.operation != DOMAIN_SCHEMA_MUTATION:
        raise ValueError("domain-schema evaluator requires domain_schema_mutation")
    decision = policy.evaluate(proposal)
    minimum = required_outcome_for_risk(proposal.risk_class)
    order = {
        policy.ALLOW: 0,
        policy.ALLOW_WITH_LEDGER: 1,
        policy.REQUIRE_REVIEW: 2,
        policy.REQUIRE_EXTERNAL_VERIFICATION: 3,
        policy.BLOCK: 4,
    }
    if order[decision.outcome] < order[minimum]:
        permitted, prohibited = _envelope(minimum, proposal.operation)
        decision = policy.Decision(
            outcome=minimum,
            permitted_actions=permitted,
            prohibited_actions=prohibited,
            reasons=decision.reasons + ("domain-schema mutation minimum",),
            policy_version=decision.policy_version,
        )
    return enforce_scope_floor(decision, proposal)


def _envelope(outcome: str, operation: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if outcome == policy.REQUIRE_REVIEW:
        return ("enter_pending_verification", "collect_more_evidence", "defer"), (operation,)
    if outcome == policy.REQUIRE_EXTERNAL_VERIFICATION:
        return ("request_external_verification", "collect_more_evidence", "defer"), (operation,)
    if outcome == policy.BLOCK:
        return (), (operation, "enter_pending_verification", "request_external_verification")
    if outcome in (policy.ALLOW, policy.ALLOW_WITH_LEDGER):
        return (operation, "collect_more_evidence", "defer"), ()
    raise ValueError(f"unsupported outcome {outcome!r}")


def build_pama_decision(
    proposal: policy.Proposal,
    decision: policy.Decision,
    *,
    selected_action: str,
    selection_mode: str | None,
    receipt_ref: str,
) -> dict:
    """Build a canonical 1.2.0 PAMA decision for domain-schema mutation."""
    document = receipts.build_pama_decision(
        proposal,
        decision,
        selected_action=selected_action,
        selection_mode=selection_mode,
        receipt_ref=receipt_ref,
    )
    document["schema_version"] = PAMA_SCHEMA_VERSION
    receipts.validate("pama-decision.schema.json", document)
    return document
