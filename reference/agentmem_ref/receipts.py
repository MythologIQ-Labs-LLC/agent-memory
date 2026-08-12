"""Schema-conformant decision and audit artifacts.

Stdlib apart from jsonschema, which is a pinned reference-validation dependency.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from . import policy

NO_ACTION = "no_action"
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate(schema_name: str, document: dict) -> None:
    errors = sorted(_validator(schema_name).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "$"
        raise ValueError(f"{schema_name} at {location}: {errors[0].message}")


def enforce_selection(permitted_actions: tuple[str, ...], selected_action: str) -> None:
    if selected_action not in permitted_actions:
        raise ValueError(f"selected action {selected_action!r} is outside the permitted set {permitted_actions!r}")


def enforce_decision_consistency(
    outcome: str,
    requested_action: str,
    permitted_actions: tuple[str, ...],
    prohibited_actions: tuple[str, ...],
    selected_action: str,
) -> None:
    """Hold the authority envelope and selected consequence internally consistent."""
    overlap = set(permitted_actions) & set(prohibited_actions)
    if overlap:
        raise ValueError(f"actions appear in both permitted and prohibited sets: {sorted(overlap)!r}")
    if outcome in (policy.REQUIRE_REVIEW, policy.REQUIRE_EXTERNAL_VERIFICATION, policy.BLOCK):
        if requested_action not in prohibited_actions:
            raise ValueError(f"{outcome} must prohibit requested action {requested_action!r}")
    if selected_action != NO_ACTION:
        enforce_selection(permitted_actions, selected_action)


def build_audit_event(
    event_id: str,
    event_type: str,
    timestamp: str,
    component: str,
    memory_id: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    policy_version: str | None = None,
    authority: dict | None = None,
    receipt_ref: str | None = None,
) -> dict:
    document = {
        "schema_version": "1.0.0",
        "event_id": event_id,
        "event_type": event_type,
        "event_version": "1.0.0",
        "timestamp": timestamp,
        "component": component,
    }
    if memory_id:
        document["memory_id"] = memory_id
    if correlation_id:
        document["correlation_id"] = correlation_id
    if causation_id:
        document["causation_id"] = causation_id
    if policy_version:
        document["policy_version"] = policy_version
    if authority is not None:
        document["authority"] = authority
    if receipt_ref:
        document["receipt_ref"] = receipt_ref
    validate("memory-audit-event.schema.json", document)
    return document


def build_pama_decision(
    proposal: policy.Proposal,
    decision: policy.Decision,
    selected_action: str,
    selection_mode: str | None,
    receipt_ref: str,
) -> dict:
    # PAMA decision 1.1.0 introduces the closed-enum `decision_overwrite`
    # operation. Existing operations continue to emit 1.0.0 so historical
    # consumers are not told their older contract changed retroactively.
    schema_version = "1.1.0" if proposal.operation == "decision_overwrite" else "1.0.0"
    document = {
        "schema_version": schema_version,
        "proposal_id": proposal.proposal_id,
        "proposing_actor": {"id": proposal.actor_id, "charter_version": proposal.charter_version},
        "target": {
            "reference": proposal.target_reference,
            "class": proposal.target_class,
            "scope": proposal.scope,
        },
        "mutation": {
            "operation": proposal.operation,
            "current_strength": proposal.current_strength,
            "proposed_strength": proposal.proposed_strength,
            "downstream_authority": proposal.downstream_authority,
            "reversibility": proposal.reversibility,
            "risk_class": proposal.risk_class,
        },
        "basis": {"evidence_refs": list(proposal.evidence_refs)},
        "policy": {"policy_version": decision.policy_version},
        "decision": {
            "outcome": decision.outcome,
            "permitted_actions": list(decision.permitted_actions),
            "prohibited_actions": list(decision.prohibited_actions),
            "selected_action": None if selected_action == NO_ACTION else selected_action,
            "selection_mode": selection_mode,
            "decision_receipt_ref": receipt_ref,
        },
    }
    if proposal.tenant_ref:
        document["target"]["tenant_ref"] = proposal.tenant_ref
    if proposal.purpose:
        document["target"]["purpose"] = proposal.purpose
    _attach_estimates(document["basis"], proposal)
    validate("pama-decision.schema.json", document)
    return document


def _attach_estimates(basis: dict, proposal: policy.Proposal) -> None:
    if proposal.estimator_refs:
        basis["estimator_refs"] = list(proposal.estimator_refs)
    if proposal.estimator_versions:
        basis["estimator_versions"] = list(proposal.estimator_versions)
    if proposal.confidence is not None:
        basis["confidence"] = proposal.confidence


def build_receipt(
    receipt_id: str,
    proposal: policy.Proposal,
    decision: policy.Decision,
    selected_action: str,
    selection_mode: str,
    timestamp: str,
    before_state: str,
    after_state: str,
    rollback_ref: str | None = None,
) -> dict:
    enforce_decision_consistency(
        decision.outcome,
        proposal.operation,
        decision.permitted_actions,
        decision.prohibited_actions,
        selected_action,
    )
    document = {
        "schema_version": "1.1.0",
        "receipt_id": receipt_id,
        "decision_ref": proposal.proposal_id,
        "decision_outcome": decision.outcome,
        "memory_id": proposal.target_reference,
        "requested_action": proposal.operation,
        "policy_version": decision.policy_version,
        "authority_refs": list(proposal.approval_refs),
        "permitted_actions": list(decision.permitted_actions),
        "prohibited_actions": list(decision.prohibited_actions),
        "selected_action": selected_action,
        "selection_mode": selection_mode,
        "before_state": before_state,
        "after_state": after_state,
        "evidence_refs": list(proposal.evidence_refs),
        "timestamp": timestamp,
    }
    if proposal.state_snapshot:
        document["state_snapshot"] = proposal.state_snapshot
    if proposal.estimator_refs:
        document["estimate_refs"] = list(proposal.estimator_refs)
    if rollback_ref:
        document["rollback_or_recovery_ref"] = rollback_ref
    validate("decision-receipt.schema.json", document)
    return document


def verify_receipt_decision_pair(receipt: dict, pama_decision: dict) -> None:
    """Verify the bidirectional decision <-> receipt authority binding."""
    decision = pama_decision["decision"]
    if receipt.get("decision_ref") != pama_decision.get("proposal_id"):
        raise ValueError("receipt decision_ref does not match PAMA proposal_id")
    if receipt.get("decision_outcome") != decision.get("outcome"):
        raise ValueError("receipt decision_outcome does not match PAMA decision outcome")
    if decision.get("decision_receipt_ref") != receipt.get("receipt_id"):
        raise ValueError("PAMA decision receipt backlink does not match receipt_id")
    if receipt.get("policy_version") != pama_decision.get("policy", {}).get("policy_version"):
        raise ValueError("receipt policy_version does not match PAMA decision")
    if receipt.get("permitted_actions") != decision.get("permitted_actions"):
        raise ValueError("receipt permitted_actions do not match PAMA decision")
    if receipt.get("prohibited_actions") != decision.get("prohibited_actions"):
        raise ValueError("receipt prohibited_actions do not match PAMA decision")

    selected = receipt.get("selected_action")
    pama_selected = decision.get("selected_action")
    if selected == NO_ACTION:
        if pama_selected is not None:
            raise ValueError("receipt no_action contradicts a selected PAMA action")
    elif selected != pama_selected:
        raise ValueError("receipt selected_action does not match PAMA decision")

    enforce_decision_consistency(
        decision["outcome"],
        receipt["requested_action"],
        tuple(decision["permitted_actions"]),
        tuple(decision["prohibited_actions"]),
        selected,
    )
