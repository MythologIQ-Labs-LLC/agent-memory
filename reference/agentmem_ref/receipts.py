"""Construction and validation of governance evidence.

Emits three artifacts, each conforming to a schema already canonical in this
repository rather than to a shape invented here:

- a PAMA decision record   (`schemas/pama-decision.schema.json`)
- a decision receipt       (`schemas/decision-receipt.schema.json`)
- audit events             (`schemas/memory-audit-event.schema.json`)

The substrate under evaluation persists none of this, which is precisely why
the adapter must.

`jsonschema` is required here, matching the validator dependency policy in
CONTRIBUTING: fixture and link validation stay standard-library, schema
validation may use it.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import jsonschema

from . import policy

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

#: Sentinel recorded when governance permitted no action at all.
NO_ACTION = "none"


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> jsonschema.Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)


def validate(schema_name: str, document: dict) -> None:
    """Raise if the document does not satisfy its canonical schema."""
    errors = sorted(_validator(schema_name).iter_errors(document), key=lambda e: list(e.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise ValueError(f"{schema_name} at {location}: {errors[0].message}")


def enforce_selection(permitted: tuple[str, ...], selected: str) -> None:
    """Selected action must come from the permitted set.

    JSON Schema cannot portably express this membership across sibling
    properties, so the receipt schema delegates it to consumers. This is that
    enforcement. `NO_ACTION` is legal only when nothing was permitted.
    """
    if selected == NO_ACTION:
        if permitted:
            raise ValueError("no action recorded although governance permitted actions")
        return
    if selected not in permitted:
        raise ValueError(f"selected action {selected!r} is not in the permitted set {list(permitted)}")


def build_pama_decision(
    proposal: policy.Proposal,
    decision: policy.Decision,
    selected_action: str,
    selection_mode: str | None,
    receipt_ref: str,
) -> dict:
    document = {
        "schema_version": "1.0.0",
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
    enforce_selection(decision.permitted_actions, selected_action)
    document = {
        "schema_version": "1.0.0",
        "receipt_id": receipt_id,
        "memory_id": proposal.target_reference,
        "actor": proposal.actor_id,
        "requested_action": proposal.operation,
        "state_snapshot": proposal.state_snapshot,
        "policy_version": decision.policy_version,
        "permitted_actions": list(decision.permitted_actions),
        "prohibited_actions": list(decision.prohibited_actions),
        "selected_action": selected_action,
        "selection_mode": selection_mode,
        "before_state": before_state,
        "after_state": after_state,
        "evidence_refs": list(proposal.evidence_refs),
        "timestamp": timestamp,
    }
    if proposal.estimator_refs:
        document["estimate_refs"] = list(proposal.estimator_refs)
    if proposal.estimator_versions:
        document["estimator_versions"] = {
            ref: version
            for ref, version in zip(proposal.estimator_refs, proposal.estimator_versions)
        }
    if rollback_ref:
        document["rollback_or_recovery_ref"] = rollback_ref
    validate("decision-receipt.schema.json", document)
    return document


def build_audit_event(
    event_id: str,
    event_type: str,
    timestamp: str,
    component: str,
    memory_id: str,
    correlation_id: str,
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
        "memory_id": memory_id,
        "correlation_id": correlation_id,
    }
    for key, value in (
        ("causation_id", causation_id),
        ("policy_version", policy_version),
        ("authority", authority),
        ("receipt_ref", receipt_ref),
    ):
        if value is not None:
            document[key] = value
    validate("memory-audit-event.schema.json", document)
    return document
