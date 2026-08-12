"""Vendor-neutral transformation evidence for issue #202.

A transformation may create useful derived evidence, but it cannot replace the
source basis with transformer reputation, turn confidence into authority, widen
scope, create certification, or silently remain current after its source basis
is invalidated.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

import rfc8785

from . import receipts

PROFILE_VERSION = "0.1.0"
TRANSFORMATION_TYPES = {"summary", "consolidation", "extraction", "projection", "other"}
MODES = {"deterministic", "probabilistic"}
STATUSES = {"complete", "partial", "failed"}
SOURCE_STATES = {"current", "disputed", "revoked", "superseded", "tombstoned", "deleted", "unknown"}
EVIDENCE_CLASSES = {"ordinary", "negative", "adversarial", "correction", "incident"}
SCOPE_RELATIONS = {"preserved", "narrowed"}


def _ref(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _refs(name: str, value: object, *, required: bool = False) -> list[str]:
    if value is None:
        if required:
            raise ValueError(f"{name} must contain at least one reference")
        return []
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{name} must be a list of non-empty strings")
    result = list(dict.fromkeys(value))
    if required and not result:
        raise ValueError(f"{name} must contain at least one reference")
    return result


def _digest(name: str, value: object) -> str:
    text = _ref(name, value)
    if len(text) != 71 or not text.startswith("sha256:") or any(ch not in "0123456789abcdef" for ch in text[7:]):
        raise ValueError(f"{name} must be a lowercase sha256 digest reference")
    return text


def _sha256_ref(value: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _optional_ref(target: dict[str, Any], field: str, value: object) -> None:
    if value is not None:
        target[field] = _ref(field, value)


def _normalize_source(source: object, index: int) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise ValueError(f"sources[{index}] must be an object")
    state = source.get("state")
    if state not in SOURCE_STATES:
        raise ValueError(f"sources[{index}].state is invalid")
    evidence_class = source.get("evidence_class")
    if evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"sources[{index}].evidence_class is invalid")
    normalized: dict[str, Any] = {
        "source_ref": _ref(f"sources[{index}].source_ref", source.get("source_ref")),
        "evidence_refs": _refs(f"sources[{index}].evidence_refs", source.get("evidence_refs"), required=True),
        "scope_ref": _ref(f"sources[{index}].scope_ref", source.get("scope_ref")),
        "state": state,
        "evidence_class": evidence_class,
    }
    _optional_ref(normalized, "tenant_ref", source.get("tenant_ref"))
    _optional_ref(normalized, "project_ref", source.get("project_ref"))
    return normalized


def _normalize_uncertainty(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("uncertainty must be an object")
    signal_value = value.get("signal_value")
    if isinstance(signal_value, bool) or not isinstance(signal_value, (int, float)):
        raise ValueError("uncertainty.signal_value must be numeric")
    result = {
        "signal_semantics": _ref("uncertainty.signal_semantics", value.get("signal_semantics")),
        "estimator_ref": _ref("uncertainty.estimator_ref", value.get("estimator_ref")),
        "estimator_version": _ref("uncertainty.estimator_version", value.get("estimator_version")),
        "signal_value": signal_value,
    }
    _optional_ref(result, "uncertainty_summary", value.get("uncertainty_summary"))
    return result


def _scope_binding(
    sources: list[dict[str, Any]],
    derived_scope: dict[str, Any],
    relation: str,
    basis_refs: list[str],
) -> tuple[str, str, list[str]]:
    """Return relation, binding status, and reasons.

    V0.1 does not infer a scope hierarchy from strings. Exact scope preservation
    is directly provable. A narrower scope must be explicitly declared and
    carry one or more basis references while retaining any source tenant/project
    boundaries. Anything else is a mismatch and therefore invalid for current
    derived use.
    """
    reasons: list[str] = []
    derived_tenant = derived_scope.get("tenant_ref")
    derived_project = derived_scope.get("project_ref")

    source_tenants = {item.get("tenant_ref") for item in sources if item.get("tenant_ref")}
    source_projects = {item.get("project_ref") for item in sources if item.get("project_ref")}
    source_scopes = {item["scope_ref"] for item in sources}

    if len(source_tenants) > 1:
        reasons.append("source_tenant_conflict")
    if len(source_projects) > 1:
        reasons.append("source_project_conflict")
    if source_tenants and derived_tenant not in source_tenants:
        reasons.append("tenant_widening_or_mismatch")
    if source_projects and derived_project not in source_projects:
        reasons.append("project_widening_or_mismatch")

    if relation == "preserved":
        if len(source_scopes) != 1 or derived_scope["scope_ref"] not in source_scopes:
            reasons.append("scope_not_preserved")
        status = "exact"
    elif relation == "narrowed":
        if not basis_refs:
            reasons.append("scope_narrowing_basis_missing")
        if derived_scope["scope_ref"] in source_scopes:
            reasons.append("narrowed_scope_must_differ_from_source_scope")
        status = "narrowed"
    else:
        raise ValueError(f"invalid scope_relation {relation!r}")

    if reasons:
        return "mismatch", "mismatch", reasons
    return relation, status, []


def _currentness(sources: list[dict[str, Any]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    unknown = False
    for source in sources:
        state = source["state"]
        if state == "current":
            continue
        if state == "unknown":
            unknown = True
            reasons.append(f"source_state_unknown:{source['source_ref']}")
        else:
            reasons.append(f"source_{state}:{source['source_ref']}")
    if reasons and not all(item.startswith("source_state_unknown:") for item in reasons):
        return "revalidation_required", reasons
    if unknown:
        return "unknown", reasons
    return "current", []


def _evidence_character(sources: list[dict[str, Any]]) -> str:
    classes = {item["evidence_class"] for item in sources}
    if classes.intersection({"negative", "adversarial"}):
        return "negative_or_adversarial"
    if classes.intersection({"correction", "incident"}):
        return "correction_or_incident"
    return "ordinary"


def normalize_transformation_evidence(
    transformation: dict[str, Any],
    *,
    parent_records: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    """Normalize one transformation into bounded derived evidence.

    `parent_records` are already-normalized transformation records. They are used
    only to extend lineage. Transformer-provided authority-like fields are never
    copied because the output is built from an explicit allowlist.
    """
    if not isinstance(transformation, dict):
        raise ValueError("transformation must be an object")

    transformation_type = transformation.get("transformation_type")
    if transformation_type not in TRANSFORMATION_TYPES:
        raise ValueError(f"invalid transformation_type {transformation_type!r}")
    mode = transformation.get("mode")
    if mode not in MODES:
        raise ValueError(f"invalid mode {mode!r}")
    status = transformation.get("status")
    if status not in STATUSES:
        raise ValueError(f"invalid status {status!r}")

    raw_sources = transformation.get("sources")
    if not isinstance(raw_sources, (list, tuple)) or not raw_sources:
        raise ValueError("sources must contain at least one source object")
    sources = [_normalize_source(item, index) for index, item in enumerate(raw_sources)]

    for index, parent in enumerate(parent_records):
        if not isinstance(parent, dict) or parent.get("schema_version") != "1.0.0" or "lineage" not in parent:
            raise ValueError(f"parent_records[{index}] is not a normalized transformation record")

    transformer = {
        "transformer_ref": _ref("transformer_ref", transformation.get("transformer_ref")),
        "transformer_version": _ref("transformer_version", transformation.get("transformer_version")),
        "trust_evidence_refs": _refs("transformer_trust_evidence_refs", transformation.get("transformer_trust_evidence_refs")),
    }

    direct_source_refs = list(dict.fromkeys(item["source_ref"] for item in sources))
    parent_transformation_refs = list(
        dict.fromkeys(parent["transformation_id"] for parent in parent_records)
    )
    original_source_refs = list(direct_source_refs)
    for parent in parent_records:
        for source_ref in parent["lineage"]["original_source_refs"]:
            if source_ref not in original_source_refs:
                original_source_refs.append(source_ref)

    scope_ref = _ref("derived_scope_ref", transformation.get("derived_scope_ref"))
    derived_scope: dict[str, Any] = {"scope_ref": scope_ref}
    _optional_ref(derived_scope, "tenant_ref", transformation.get("derived_tenant_ref"))
    _optional_ref(derived_scope, "project_ref", transformation.get("derived_project_ref"))
    relation = transformation.get("scope_relation", "preserved")
    basis_refs = _refs("scope_basis_refs", transformation.get("scope_basis_refs"))
    relation_out, binding_status, binding_reasons = _scope_binding(sources, derived_scope, relation, basis_refs)
    derived_scope.update(
        {
            "relation": relation_out,
            "basis_refs": basis_refs,
            "binding_status": binding_status,
        }
    )

    currentness_status, currentness_reasons = _currentness(sources)
    uncertainty = _normalize_uncertainty(transformation.get("uncertainty"))

    derived: dict[str, Any] = {
        "derived_ref": _ref("derived_ref", transformation.get("derived_ref")),
        "derived_evidence_ref": _ref("derived_evidence_ref", transformation.get("derived_evidence_ref")),
        "derived_evidence_digest": _digest("derived_evidence_digest", transformation.get("derived_evidence_digest")),
        "evidence_character": _evidence_character(sources),
    }
    if uncertainty is not None:
        derived["uncertainty"] = uncertainty

    applicability_reasons = list(binding_reasons)
    if status != "complete":
        applicability_reasons.append(f"transformation_{status}")
    applicability_reasons.extend(currentness_reasons)

    if binding_status == "mismatch":
        applicability_status = "invalid"
    elif status != "complete":
        applicability_status = "incomplete"
    elif currentness_status != "current":
        applicability_status = "revalidation_required"
    else:
        applicability_status = "current"

    body: dict[str, Any] = {
        "transformation_id": _ref("transformation_id", transformation.get("transformation_id")),
        "transformation_type": transformation_type,
        "mode": mode,
        "status": status,
        "transformer": transformer,
        "sources": sources,
        "lineage": {
            "direct_source_refs": direct_source_refs,
            "original_source_refs": original_source_refs,
            "parent_transformation_refs": parent_transformation_refs,
        },
        "derived": derived,
        "scope": derived_scope,
        "source_currentness": {
            "status": currentness_status,
            "reasons": currentness_reasons,
        },
        "applicability": {
            "status": applicability_status,
            "reasons": list(dict.fromkeys(applicability_reasons)),
        },
        "created_at": _ref("created_at", transformation.get("created_at")),
        "interpretation": {
            "transformation_authority_effect": "none",
            "transformer_trust_is_source_trust": False,
            "derived_confidence_authority": "none",
            "certification_claim": "none",
            "standing_policy_effect": "none",
            "memory_admission": "not_established",
        },
    }

    identity_body = deepcopy(body)
    body["identity_digest"] = _sha256_ref(identity_body)
    document = {
        "schema_version": "1.0.0",
        "profile_version": PROFILE_VERSION,
        **body,
    }
    receipts.validate("transformation-evidence.schema.json", document)
    return document


def reevaluate_source_currentness(
    record: dict[str, Any],
    source_states: dict[str, str],
) -> dict[str, Any]:
    """Re-evaluate a normalized derived record against current source states.

    This returns a new normalized record-like object and never rewrites source
    history. It is deliberately conservative: an unknown or changed source
    state can remove current applicability but cannot manufacture a stronger
    derived status.
    """
    if not isinstance(record, dict) or record.get("schema_version") != "1.0.0":
        raise ValueError("record must be normalized transformation evidence")
    if not isinstance(source_states, dict):
        raise ValueError("source_states must be an object")

    updated = deepcopy(record)
    reasons: list[str] = []
    unknown = False
    for source in updated["sources"]:
        state = source_states.get(source["source_ref"], source["state"])
        if state not in SOURCE_STATES:
            raise ValueError(f"invalid current source state {state!r}")
        source["state"] = state
        if state == "current":
            continue
        if state == "unknown":
            unknown = True
            reasons.append(f"source_state_unknown:{source['source_ref']}")
        else:
            reasons.append(f"source_{state}:{source['source_ref']}")

    if reasons and not all(item.startswith("source_state_unknown:") for item in reasons):
        currentness_status = "revalidation_required"
    elif unknown:
        currentness_status = "unknown"
    else:
        currentness_status = "current"

    updated["source_currentness"] = {"status": currentness_status, "reasons": reasons}
    prior_binding_reasons = [
        reason for reason in updated["applicability"]["reasons"]
        if not reason.startswith("source_")
    ]
    combined_reasons = list(dict.fromkeys(prior_binding_reasons + reasons))
    if updated["scope"]["binding_status"] == "mismatch":
        applicability_status = "invalid"
    elif updated["status"] != "complete":
        applicability_status = "incomplete"
    elif currentness_status != "current":
        applicability_status = "revalidation_required"
    else:
        applicability_status = "current"
    updated["applicability"] = {"status": applicability_status, "reasons": combined_reasons}

    identity_body = {
        key: value for key, value in updated.items()
        if key not in {"schema_version", "profile_version", "identity_digest"}
    }
    updated["identity_digest"] = _sha256_ref(identity_body)
    receipts.validate("transformation-evidence.schema.json", updated)
    return updated
