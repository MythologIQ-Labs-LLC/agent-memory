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

import hashlib
import json
from functools import lru_cache
from importlib import resources
from pathlib import Path

import jsonschema

from . import policy
from .._paths import REPO_ROOT, PACKAGE_NAME

_SOURCE_SCHEMAS = REPO_ROOT / "schemas"


def _packaged_schemas() -> Path:
    return Path(str(resources.files(PACKAGE_NAME) / "_schemas"))


def schema_dir() -> Path:
    """Canonical schemas: source tree when present, packaged copy when installed."""
    if _SOURCE_SCHEMAS.is_dir():
        return _SOURCE_SCHEMAS
    packaged = _packaged_schemas()
    if packaged.is_dir():
        return packaged
    raise FileNotFoundError(
        "canonical schemas are unavailable; install the distribution with its packaged schema data"
    )

#: Sentinel recorded when governance permitted no action at all.
NO_ACTION = "none"

_DEFERRED_OUTCOMES = {
    "require_review",
    "require_external_verification",
    "abstain",
    "quarantine",
    "collect_more_evidence",
}

_CONTEXTUAL_RECALL_SCHEMA = "contextual-recall-admission.schema.json"
# #572: the fast path below is valid only for this exact canonical schema blob.
# If the schema changes, validation automatically falls back to jsonschema until
# the optimized validator is reviewed against the new contract.
_CONTEXTUAL_RECALL_SCHEMA_BLOB_SHA = "b9663c491e576608f89ee3df56e1d9f46d5e6c4a"
_CONTEXTUAL_RECALL_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "profile_version",
        "decision_id",
        "candidate_ref",
        "policy",
        "context",
        "outcome",
        "reason_code",
        "evidence_refs",
        "evaluated_at",
        "interpretation",
    }
)
_CONTEXTUAL_RECALL_POLICY_KEYS = frozenset(
    {"policy_ref", "policy_version", "status", "selection_mode"}
)
_CONTEXTUAL_RECALL_CONTEXT_KEYS = frozenset(
    {
        "target_domain_refs",
        "principal_ref",
        "project_ref",
        "task_ref",
        "purpose",
        "destination_ref",
    }
)
_CONTEXTUAL_RECALL_INTERPRETATION = {
    "authority_effect": "current_recall_only",
    "prior_admission_authority": "none",
    "memory_mutation": "not_performed",
    "relevance_authority": "none",
    "risk_signal_authority": "none",
}
_CONTEXTUAL_RECALL_OUTCOMES = {
    "admit",
    "admit_with_warning",
    "require_verification",
    "require_review",
    "quarantine",
    "block",
}
_CONTEXTUAL_RECALL_POLICY_STATUSES = {"evaluated", "unavailable", "error", "invalid"}


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> jsonschema.Draft202012Validator:
    schema = json.loads((schema_dir() / schema_name).read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)


def _validate_with_jsonschema(schema_name: str, document: dict) -> None:
    """Canonical JSON Schema validation oracle."""
    errors = sorted(_validator(schema_name).iter_errors(document), key=lambda e: list(e.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise ValueError(f"{schema_name} at {location}: {errors[0].message}")


@lru_cache(maxsize=1)
def _builtin_recall_fastpath_enabled() -> bool:
    """Use the optimized validator only while the canonical schema is byte-identical.

    This is deliberately a Git-blob identity rather than a semantic guess. A
    schema edit disables the fast path and restores the canonical jsonschema
    validator automatically, so performance code cannot silently outlive the
    evidence contract it was reviewed against.
    """

    raw = (schema_dir() / _CONTEXTUAL_RECALL_SCHEMA).read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    observed = hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()
    return observed == _CONTEXTUAL_RECALL_SCHEMA_BLOB_SHA


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _string_list_is_unique_and_nonempty(value: object) -> bool:
    if not isinstance(value, list):
        return False
    if not all(_nonempty_string(item) for item in value):
        return False
    return len(value) == len(set(value))


def _fast_validation_error(path: str, message: str) -> ValueError:
    location = path or "<root>"
    return ValueError(f"{_CONTEXTUAL_RECALL_SCHEMA} at {location}: {message}")


def _is_builtin_recall_fastpath_candidate(document: object) -> bool:
    """Return whether a document belongs to the fixed built-in recall-decision shape.

    Contextual policy decisions and decisions carrying optional risk evidence
    stay on canonical jsonschema. The optimized path exists only for the hot
    built-in admission record emitted by GovernedMemoryAdapter._recall_decision.
    """

    if not isinstance(document, dict) or "risk_evidence" in document:
        return False
    policy_document = document.get("policy")
    return (
        isinstance(policy_document, dict)
        and policy_document.get("policy_ref") == "contextual-recall-policy:none"
        and policy_document.get("status") == "unavailable"
    )


def _validate_builtin_recall_decision(document: dict) -> None:
    """Schema-equivalent validator for the fixed built-in recall decision.

    The schema is intentionally simple and self-contained. This validator checks
    every constraint exercised by the canonical Draft 2020-12 schema for the
    no-risk-evidence built-in shape: object closure, required keys, const/enum
    values, string types/minLength, array item types/uniqueness, and nested
    object closure. `evaluated_at` remains a string check because the canonical
    jsonschema validator is instantiated without a FormatChecker, so `format:
    date-time` is annotation-only in the current contract.
    """

    if frozenset(document) != _CONTEXTUAL_RECALL_TOP_LEVEL_KEYS:
        raise _fast_validation_error("<root>", "unexpected or missing top-level properties")
    if document.get("schema_version") != "1.0.0":
        raise _fast_validation_error("schema_version", "must be '1.0.0'")
    if document.get("profile_version") != "0.1.0":
        raise _fast_validation_error("profile_version", "must be '0.1.0'")
    if not _nonempty_string(document.get("decision_id")):
        raise _fast_validation_error("decision_id", "must be a non-empty string")
    if not _nonempty_string(document.get("candidate_ref")):
        raise _fast_validation_error("candidate_ref", "must be a non-empty string")

    policy_document = document.get("policy")
    if not isinstance(policy_document, dict) or frozenset(policy_document) != _CONTEXTUAL_RECALL_POLICY_KEYS:
        raise _fast_validation_error("policy", "must contain exactly the canonical policy properties")
    if not _nonempty_string(policy_document.get("policy_ref")):
        raise _fast_validation_error("policy.policy_ref", "must be a non-empty string")
    if not _nonempty_string(policy_document.get("policy_version")):
        raise _fast_validation_error("policy.policy_version", "must be a non-empty string")
    if policy_document.get("status") not in _CONTEXTUAL_RECALL_POLICY_STATUSES:
        raise _fast_validation_error("policy.status", "is not a supported status")
    if policy_document.get("selection_mode") != "deterministic":
        raise _fast_validation_error("policy.selection_mode", "must be 'deterministic'")

    context = document.get("context")
    if not isinstance(context, dict) or frozenset(context) != _CONTEXTUAL_RECALL_CONTEXT_KEYS:
        raise _fast_validation_error("context", "must contain exactly the canonical context properties")
    if not _string_list_is_unique_and_nonempty(context.get("target_domain_refs")):
        raise _fast_validation_error(
            "context.target_domain_refs",
            "must be a unique array of non-empty strings",
        )
    for field_name in ("principal_ref", "project_ref", "task_ref", "purpose", "destination_ref"):
        if not isinstance(context.get(field_name), str):
            raise _fast_validation_error(f"context.{field_name}", "must be a string")

    if document.get("outcome") not in _CONTEXTUAL_RECALL_OUTCOMES:
        raise _fast_validation_error("outcome", "is not a supported outcome")
    if not _nonempty_string(document.get("reason_code")):
        raise _fast_validation_error("reason_code", "must be a non-empty string")
    if not _string_list_is_unique_and_nonempty(document.get("evidence_refs")) and document.get("evidence_refs") != []:
        raise _fast_validation_error("evidence_refs", "must be a unique array of non-empty strings")
    if not isinstance(document.get("evaluated_at"), str):
        raise _fast_validation_error("evaluated_at", "must be a string")

    interpretation = document.get("interpretation")
    if not isinstance(interpretation, dict) or interpretation != _CONTEXTUAL_RECALL_INTERPRETATION:
        raise _fast_validation_error(
            "interpretation",
            "must contain exactly the canonical authority interpretation",
        )


def validate(schema_name: str, document: dict) -> None:
    """Raise if the document does not satisfy its canonical schema.

    #572 keeps the built-in recall decision at the same per-record validation
    boundary but avoids full jsonschema traversal for its fixed, internally
    constructed shape. The fast validator is enabled only while the exact
    canonical schema blob matches the reviewed revision. All other documents,
    including contextual-policy decisions and any future schema revision, use
    the canonical jsonschema oracle unchanged.
    """

    if (
        schema_name == _CONTEXTUAL_RECALL_SCHEMA
        and _builtin_recall_fastpath_enabled()
        and _is_builtin_recall_fastpath_candidate(document)
    ):
        _validate_builtin_recall_decision(document)
        return
    _validate_with_jsonschema(schema_name, document)


def decision_ref_for(proposal_id: str) -> str:
    """Stable logical reference for the PAMA decision produced for a proposal.

    The PAMA decision already carries ``proposal_id`` as its stable identity
    anchor. This names that artifact without introducing a second, cyclic
    content identity merely to link it back from the receipt.
    """
    if not proposal_id:
        raise ValueError("decision reference requires a proposal id")
    return f"pama-decision:{proposal_id}"


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


def enforce_decision_consistency(
    outcome: str,
    requested_action: str,
    permitted: tuple[str, ...],
    prohibited: tuple[str, ...],
) -> None:
    """Reject authority outcomes that contradict their action envelope.

    This intentionally enforces only invariants that are stable across the
    current decision vocabulary. It does not invent one universal policy table.
    """
    overlap = set(permitted) & set(prohibited)
    if overlap:
        raise ValueError(f"actions cannot be both permitted and prohibited: {sorted(overlap)}")

    if outcome in ("allow", "allow_with_ledger"):
        if requested_action not in permitted:
            raise ValueError(f"{outcome} must permit the requested action {requested_action!r}")
        if requested_action in prohibited:
            raise ValueError(f"{outcome} cannot prohibit the requested action {requested_action!r}")
        return

    if outcome == "block":
        if permitted:
            raise ValueError("block outcome cannot expose permitted actions")
        if requested_action not in prohibited:
            raise ValueError("block outcome must prohibit the requested action")
        return

    if outcome in _DEFERRED_OUTCOMES:
        if requested_action in permitted:
            raise ValueError(f"{outcome} cannot directly permit the requested action")
        if requested_action not in prohibited:
            raise ValueError(f"{outcome} must keep the requested action prohibited pending resolution")
        return

    raise ValueError(f"unknown decision outcome {outcome!r}")


def build_pama_decision(
    proposal: policy.Proposal,
    decision: policy.Decision,
    selected_action: str,
    selection_mode: str | None,
    receipt_ref: str,
) -> dict:
    # PAMA decision 1.1.0 adds the closed-enum `decision_overwrite` operation.
    # Existing operations remain 1.0.0 so older decision artifacts and closed
    # consumers do not acquire a new semantic contract retroactively.
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
    )
    enforce_selection(decision.permitted_actions, selected_action)
    document = {
        "schema_version": "1.1.0",
        "receipt_id": receipt_id,
        "decision_ref": decision_ref_for(proposal.proposal_id),
        "decision_outcome": decision.outcome,
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


def verify_receipt_decision_pair(receipt: dict, pama_decision: dict) -> None:
    """Verify that a receipt and PAMA decision describe the same authority event."""
    validate("decision-receipt.schema.json", receipt)
    validate("pama-decision.schema.json", pama_decision)

    expected_ref = decision_ref_for(pama_decision["proposal_id"])
    if receipt.get("decision_ref") != expected_ref:
        raise ValueError(
            f"receipt decision_ref {receipt.get('decision_ref')!r} does not match {expected_ref!r}"
        )

    decision = pama_decision["decision"]
    comparisons = {
        "decision_outcome": decision["outcome"],
        "permitted_actions": decision["permitted_actions"],
        "prohibited_actions": decision["prohibited_actions"],
        "policy_version": pama_decision["policy"]["policy_version"],
    }
    for receipt_field, decision_value in comparisons.items():
        if receipt.get(receipt_field) != decision_value:
            raise ValueError(
                f"receipt {receipt_field} does not match referenced decision: "
                f"receipt={receipt.get(receipt_field)!r} decision={decision_value!r}"
            )

    receipt_selected = receipt["selected_action"]
    decision_selected = decision.get("selected_action")
    normalized_decision_selected = NO_ACTION if decision_selected is None else decision_selected
    if receipt_selected != normalized_decision_selected:
        raise ValueError(
            "receipt selected_action does not match referenced decision: "
            f"receipt={receipt_selected!r} decision={normalized_decision_selected!r}"
        )

    if decision.get("decision_receipt_ref") != receipt["receipt_id"]:
        raise ValueError("referenced decision does not point back to this receipt")

    enforce_decision_consistency(
        receipt["decision_outcome"],
        receipt["requested_action"],
        tuple(receipt["permitted_actions"]),
        tuple(receipt.get("prohibited_actions") or ()),
    )
    enforce_selection(tuple(receipt["permitted_actions"]), receipt_selected)


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
