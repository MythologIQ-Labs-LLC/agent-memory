"""Explicit reusable-grant proposal, ratification, and evaluation for issue #250.

Historical precedent may motivate a proposal. Only a separately evidenced,
verified ratification can create a reusable grant, and that grant may discharge
only an otherwise-required human review inside its exact bound conditions.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from typing import Iterable

import rfc8785

from . import policy, receipts
from .precedent_applicability import REDUCE_REVIEW, evaluate_projection

VERSION = "0.1.0"
_RELEVANT_RELATIONSHIPS = {"exact", "material_match"}


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _digest(value: dict) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _canonical(value) -> bytes:
    return rfc8785.dumps(value)


def _eligible_human_precedents(projection: dict) -> list[dict]:
    by_source: dict[str, dict] = {}
    for precedent in projection["precedents"]:
        provenance = precedent["provenance"]
        if (
            precedent["polarity"] == "supportive"
            and precedent["relationship"] in _RELEVANT_RELATIONSHIPS
            and precedent["validity"]["status"] == "current"
            and provenance["source_type"] == "human_adjudication"
            and provenance.get("independent_adjudication") is True
        ):
            by_source.setdefault(provenance["source_ref"], precedent)
    return list(by_source.values())


def _material_conditions(precedents: Iterable[dict]) -> tuple[list[dict], list[str]]:
    values: dict[str, object] = {}
    reasons: list[str] = []
    seen = False
    for precedent in precedents:
        for condition in precedent["material_conditions"]:
            seen = True
            if condition["comparison"] != "match":
                reasons.append(f"condition_not_matched:{condition['name']}")
                continue
            name = condition["name"]
            current = condition.get("current_value")
            if name in values and _canonical(values[name]) != _canonical(current):
                reasons.append(f"inconsistent_current_value:{name}")
            else:
                values[name] = current
    if not seen:
        reasons.append("no_material_conditions")
    return ([{"name": name, "value": values[name]} for name in sorted(values)], list(dict.fromkeys(reasons)))


def _current_relevant_support(projection: dict) -> list[dict]:
    return [
        precedent
        for precedent in projection["precedents"]
        if precedent["polarity"] == "supportive"
        and precedent["relationship"] in _RELEVANT_RELATIONSHIPS
        and precedent["validity"]["status"] == "current"
    ]


def propose_reusable_grant(
    projection: dict,
    applicability: dict,
    *,
    requested_operation: str,
    policy_version_ref: str,
    generated_at: str,
    requested_valid_until: str,
    revocation_mechanism_ref: str,
    minimum_independent_human_evidence: int = 2,
) -> dict:
    """Create a non-authoritative proposal from deterministic precedent evidence."""

    receipts.validate("governance-context-projection.schema.json", projection)
    receipts.validate("precedent-applicability-result.schema.json", applicability)
    if applicability["projection_id"] != projection["projection_id"]:
        raise ValueError("applicability result does not belong to projection")
    for name, value in (
        ("requested_operation", requested_operation),
        ("policy_version_ref", policy_version_ref),
        ("generated_at", generated_at),
        ("requested_valid_until", requested_valid_until),
        ("revocation_mechanism_ref", revocation_mechanism_ref),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")
    if minimum_independent_human_evidence < 2:
        raise ValueError("minimum independent human evidence must be at least 2")
    generated = _parse_time(generated_at)
    valid_until = _parse_time(requested_valid_until)
    if valid_until <= generated:
        raise ValueError("requested_valid_until must follow generated_at")

    reasons: list[str] = []
    if projection["derivation"]["mode"] not in {"exact_identity", "deterministic_condition_match"}:
        reasons.append("non_deterministic_projection")
    if projection["scope"]["relationship"] != "same":
        reasons.append(f"scope_relationship:{projection['scope']['relationship']}")
    if applicability["recommended_handling"] != REDUCE_REVIEW:
        reasons.append(f"handling:{applicability['recommended_handling']}")
    if applicability["authority_effect"] != "none" or applicability["can_authorize_execution"] is not False:
        reasons.append("precedent_result_claims_authority")
    if applicability["incident_or_negative_evidence_present"]:
        reasons.append("relevant_negative_precedent")
    if applicability["material_differences"]:
        reasons.append("material_differences_present")
    if applicability["unknown_conditions"]:
        reasons.append("unknown_material_conditions")
    if applicability["stale_or_invalid_reasons"]:
        reasons.append("stale_or_invalid_precedent")

    human_precedents = _eligible_human_precedents(projection)
    human_source_refs = [p["provenance"]["source_ref"] for p in human_precedents]
    human_memory_refs = [p["memory_ref"] for p in human_precedents]
    unique_human_count = len(human_source_refs)
    if unique_human_count < minimum_independent_human_evidence:
        reasons.append("insufficient_independent_human_evidence")
    if applicability["independent_human_evidence_count"] < unique_human_count:
        reasons.append("applicability_human_count_understates_projection")

    source_policy_versions = {
        p["validity"].get("policy_version_ref")
        for p in human_precedents
        if p["validity"].get("policy_version_ref")
    }
    if source_policy_versions and source_policy_versions != {policy_version_ref}:
        reasons.append("policy_version_mismatch")

    conditions, condition_reasons = _material_conditions(human_precedents)
    reasons.extend(condition_reasons)
    reasons = list(dict.fromkeys(reasons))

    body = {
        "source_projection_id": projection["projection_id"],
        "source_applicability": applicability["applicability"],
        "requested_operation": requested_operation,
        "scope_refs": list(projection["scope"]["domain_refs"]),
        "material_conditions": conditions,
        "policy_version_ref": policy_version_ref,
        "generated_at": generated_at,
        "requested_valid_until": requested_valid_until,
        "revocation_mechanism_ref": revocation_mechanism_ref,
        "supporting_precedent_refs": human_memory_refs,
        "supporting_human_decision_refs": human_source_refs,
        "independent_human_evidence_count": unique_human_count,
        "minimum_independent_human_evidence": minimum_independent_human_evidence,
    }
    document = {
        "schema_version": VERSION,
        "proposal_id": f"grant-proposal:{_digest(body)}",
        "status": "proposed" if not reasons else "not_proposed",
        **body,
        "reasons": reasons,
        "authority_effect": "none",
        "can_authorize_execution": False,
        "can_self_ratify": False,
        "can_create_autonomy_policy": False,
    }
    receipts.validate("reusable-grant-proposal.schema.json", document)
    return document


def ratify_reusable_grant(
    proposal: dict,
    *,
    ratification_ref: str,
    ratifying_principal_ref: str,
    ratifier_authority_evidence_ref: str,
    ratifier_authority_verified: bool,
    approved_operation: str,
    approved_scope_refs: tuple[str, ...],
    approved_material_conditions: tuple[dict, ...],
    policy_version_ref: str,
    issued_at: str,
    expires_at: str,
    revocation_mechanism_ref: str,
    evidence_refs: tuple[str, ...] = (),
) -> dict:
    """Create reusable authority only from a separate, verified ratification."""

    receipts.validate("reusable-grant-proposal.schema.json", proposal)
    if proposal["status"] != "proposed":
        raise ValueError("only an eligible proposal can be ratified")
    if ratifier_authority_verified is not True:
        raise ValueError("ratifier authority must be independently verified")
    for name, value in (
        ("ratification_ref", ratification_ref),
        ("ratifying_principal_ref", ratifying_principal_ref),
        ("ratifier_authority_evidence_ref", ratifier_authority_evidence_ref),
        ("approved_operation", approved_operation),
        ("policy_version_ref", policy_version_ref),
        ("issued_at", issued_at),
        ("expires_at", expires_at),
        ("revocation_mechanism_ref", revocation_mechanism_ref),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")
    historical_refs = set(proposal["supporting_human_decision_refs"]) | set(proposal["supporting_precedent_refs"])
    if ratification_ref in historical_refs:
        raise ValueError("ratification must be a separate authority transition, not reused history")
    if approved_operation != proposal["requested_operation"]:
        raise ValueError("ratification cannot widen or change requested operation")
    if list(approved_scope_refs) != proposal["scope_refs"]:
        raise ValueError("ratification scope must exactly match proposal scope")
    if _canonical(list(approved_material_conditions)) != _canonical(proposal["material_conditions"]):
        raise ValueError("ratification material conditions must exactly match proposal")
    if policy_version_ref != proposal["policy_version_ref"]:
        raise ValueError("ratification policy version must exactly match proposal")
    if revocation_mechanism_ref != proposal["revocation_mechanism_ref"]:
        raise ValueError("ratification revocation mechanism must exactly match proposal")
    issued = _parse_time(issued_at)
    expires = _parse_time(expires_at)
    requested_until = _parse_time(proposal["requested_valid_until"])
    if expires <= issued:
        raise ValueError("grant expiry must follow issuance")
    if expires > requested_until:
        raise ValueError("ratification cannot extend beyond proposed validity")

    body = {
        "proposal_id": proposal["proposal_id"],
        "ratification_ref": ratification_ref,
        "ratifying_principal_ref": ratifying_principal_ref,
        "ratifier_authority_evidence_ref": ratifier_authority_evidence_ref,
        "ratifier_authority_verified": True,
        "operation": approved_operation,
        "scope_refs": list(approved_scope_refs),
        "material_conditions": list(approved_material_conditions),
        "policy_version_ref": policy_version_ref,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "revocation_mechanism_ref": revocation_mechanism_ref,
        "evidence_refs": list(dict.fromkeys((ratification_ref, ratifier_authority_evidence_ref, *evidence_refs))),
    }
    grant = {
        "schema_version": VERSION,
        "grant_id": f"reusable-grant:{_digest(body)}",
        **body,
        "source_class": "explicit_ratification",
        "reusable_authority": True,
        "authority_effect": "scoped_reusable_review_grant",
        "can_widen_pama": False,
        "can_widen_scope": False,
        "can_create_autonomy_policy": False,
    }
    receipts.validate("reusable-grant.schema.json", grant)
    return grant


def revoke_reusable_grant(
    grant: dict,
    *,
    revocation_ref: str,
    revoking_principal_ref: str,
    revoker_authority_evidence_ref: str,
    revoker_authority_verified: bool,
    revoked_at: str,
    evidence_refs: tuple[str, ...] = (),
) -> dict:
    receipts.validate("reusable-grant.schema.json", grant)
    if revoker_authority_verified is not True:
        raise ValueError("revoker authority must be independently verified")
    if _parse_time(revoked_at) < _parse_time(grant["issued_at"]):
        raise ValueError("revocation cannot precede grant issuance")
    body = {
        "grant_id": grant["grant_id"],
        "revocation_ref": revocation_ref,
        "revoking_principal_ref": revoking_principal_ref,
        "revoker_authority_evidence_ref": revoker_authority_evidence_ref,
        "revoker_authority_verified": True,
        "revoked_at": revoked_at,
        "evidence_refs": list(dict.fromkeys((revocation_ref, revoker_authority_evidence_ref, *evidence_refs))),
    }
    document = {"schema_version": VERSION, **body}
    receipts.validate("reusable-grant-revocation.schema.json", document)
    return document


def evaluate_reusable_grant(
    grant: dict,
    projection: dict,
    *,
    expected_operation: str,
    current_policy_version_ref: str,
    observed_at: str,
    ratification_evidence_present: bool,
    revocation: dict | None = None,
) -> dict:
    """Revalidate a ratified grant against current deterministic context."""

    receipts.validate("reusable-grant.schema.json", grant)
    receipts.validate("governance-context-projection.schema.json", projection)
    if revocation is not None:
        receipts.validate("reusable-grant-revocation.schema.json", revocation)
    observed = _parse_time(observed_at)
    applicability = evaluate_projection(projection)
    reasons: list[str] = []
    status = "current"

    if revocation is not None:
        if revocation["grant_id"] != grant["grant_id"]:
            status = "invalid"
            reasons.append("revocation_grant_mismatch")
        elif _parse_time(revocation["revoked_at"]) <= observed:
            status = "revoked"
            reasons.append("grant_revoked")
    if status == "current" and observed < _parse_time(grant["issued_at"]):
        status = "invalid"
        reasons.append("grant_not_yet_issued")
    if status == "current" and observed > _parse_time(grant["expires_at"]):
        status = "stale"
        reasons.append("grant_expired")
    if status == "current" and current_policy_version_ref != grant["policy_version_ref"]:
        status = "stale"
        reasons.append("policy_version_drift")
    if status == "current" and ratification_evidence_present is not True:
        status = "invalid"
        reasons.append("ratification_evidence_missing")
    if status == "current" and expected_operation != grant["operation"]:
        status = "not_applicable"
        reasons.append("operation_mismatch")
    if status == "current" and (
        projection["scope"]["relationship"] != "same"
        or projection["scope"]["domain_refs"] != grant["scope_refs"]
    ):
        status = "not_applicable"
        reasons.append("scope_mismatch")
    if status == "current" and applicability["recommended_handling"] != REDUCE_REVIEW:
        status = "not_applicable"
        reasons.append(f"precedent_handling:{applicability['recommended_handling']}")
    if status == "current" and applicability["incident_or_negative_evidence_present"]:
        status = "not_applicable"
        reasons.append("relevant_negative_precedent")

    conditions, condition_reasons = _material_conditions(_current_relevant_support(projection))
    if status == "current" and condition_reasons:
        status = "not_applicable"
        reasons.extend(condition_reasons)
    if status == "current" and _canonical(conditions) != _canonical(grant["material_conditions"]):
        status = "not_applicable"
        reasons.append("material_condition_mismatch")

    satisfied = status == "current"
    result = {
        "schema_version": VERSION,
        "grant_id": grant["grant_id"],
        "proposal_id": grant["proposal_id"],
        "projection_id": projection["projection_id"],
        "operation": expected_operation,
        "scope_refs": list(grant["scope_refs"]),
        "status": status,
        "satisfies_reusable_approval": satisfied,
        "approval_ref": grant["grant_id"],
        "reasons": list(dict.fromkeys(reasons)),
        "source_class": "ratified_reusable_grant",
        "counts_as_independent_human_adjudication": False,
        "can_widen_pama": False,
        "can_widen_scope": False,
        "can_create_autonomy_policy": False,
    }
    receipts.validate("reusable-grant-evaluation.schema.json", result)
    return result


def evaluate_pama_with_reusable_grant(proposal: policy.Proposal, grant_evaluation: dict) -> policy.Decision:
    """Use a current grant only to discharge ordinary PAMA review.

    External verification and blocks remain absorbing for this profile.
    """

    receipts.validate("reusable-grant-evaluation.schema.json", grant_evaluation)
    baseline = policy.evaluate(replace(proposal, review_satisfied=False, approval_refs=()))
    if not grant_evaluation["satisfies_reusable_approval"]:
        return baseline
    if baseline.outcome != policy.REQUIRE_REVIEW:
        return baseline
    if proposal.operation != grant_evaluation["operation"]:
        return baseline
    if proposal.scope not in grant_evaluation["scope_refs"]:
        return baseline
    return policy.evaluate(
        replace(
            proposal,
            review_satisfied=True,
            approval_refs=(grant_evaluation["approval_ref"],),
        )
    )


def grant_execution_provenance(grant: dict, *, execution_ref: str) -> dict:
    """Classify reuse as derived policy outcome, never a new human adjudication."""

    receipts.validate("reusable-grant.schema.json", grant)
    if not execution_ref:
        raise ValueError("execution_ref must be non-empty")
    return {
        "source_type": "policy_outcome",
        "source_ref": execution_ref,
        "authority_ref": grant["grant_id"],
        "independent_adjudication": False,
    }
