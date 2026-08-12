"""Vendor-neutral enforcement evidence for issue #152 Phase 3.

This module keeps configured governance, decision delivery, enforcement-point
observation, and action execution/prevention as distinct evidence states.
A decision receipt is never upgraded to execution proof by inference.
"""

from __future__ import annotations

import hashlib

import rfc8785

from . import receipts

WITNESS_VERSION = "0.1.0"
POSTURE_VERSION = "0.1.0"

ENFORCEMENT_MODES = {"mechanical", "cooperative", "unknown"}
DELIVERY_STATUSES = {"delivered", "failed", "not_observed"}
POINT_STATUSES = {"reached", "unavailable", "not_observed"}
ACTION_STATUSES = {"executed", "prevented", "refused", "unknown", "not_observed"}
LIVENESS_STATUSES = {"healthy", "degraded", "unavailable", "unknown"}
WITNESS_COVERAGE = {"available", "partial", "absent"}


def _sha256_ref(value: dict) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _alignment(effective_decision: str, action_status: str, enforcement_point_status: str) -> str:
    if enforcement_point_status != "reached" or action_status in {"unknown", "not_observed"}:
        return "unverifiable"

    if effective_decision == "deny":
        return "violation" if action_status == "executed" else "consistent"

    if effective_decision in {"allow", "warn"}:
        if action_status == "executed":
            return "consistent"
        if action_status in {"prevented", "refused"}:
            return "stricter_than_decision"
        return "unverifiable"

    # ``require_approval`` cannot be upgraded to authorized execution merely
    # because a witness sees execution. Approval validity is a separate check.
    if effective_decision == "require_approval":
        if action_status in {"prevented", "refused"}:
            return "consistent"
        return "unverifiable"

    return "unverifiable"


def build_execution_witness(
    composition: dict,
    *,
    action_ref: str,
    witness_ref: str,
    enforcement_mode: str,
    delivery_status: str,
    enforcement_point_status: str,
    action_status: str,
    liveness_status: str,
    observed_at: str,
    observed_input_identity: str | None = None,
    approval_evidence_ref: str | None = None,
    evidence_refs: tuple[str, ...] = (),
) -> dict:
    """Bind an observed enforcement/execution event to a composed decision.

    The witness may record a policy violation rather than rejecting the event.
    That distinction matters: evidence that an action executed despite ``deny``
    is valuable negative evidence, not malformed evidence.
    """

    receipts.validate("decision-composition-receipt.schema.json", composition)
    if not action_ref or not witness_ref or not observed_at:
        raise ValueError("execution witness requires action_ref, witness_ref, and observed_at")
    if enforcement_mode not in ENFORCEMENT_MODES:
        raise ValueError(f"invalid enforcement_mode {enforcement_mode!r}")
    if delivery_status not in DELIVERY_STATUSES:
        raise ValueError(f"invalid delivery_status {delivery_status!r}")
    if enforcement_point_status not in POINT_STATUSES:
        raise ValueError(f"invalid enforcement_point_status {enforcement_point_status!r}")
    if action_status not in ACTION_STATUSES:
        raise ValueError(f"invalid action_status {action_status!r}")
    if liveness_status not in LIVENESS_STATUSES:
        raise ValueError(f"invalid liveness_status {liveness_status!r}")

    identity = composition["input_identity"]
    if observed_input_identity is not None and observed_input_identity != identity:
        raise ValueError("execution witness input identity does not match composed decision")

    if enforcement_point_status == "reached" and delivery_status != "delivered":
        raise ValueError("reached enforcement point requires delivered decision evidence")
    if enforcement_point_status != "reached" and action_status in {"executed", "prevented", "refused"}:
        raise ValueError("action outcome cannot be claimed without observing the enforcement point")

    body = {
        "input_identity": identity,
        "composition_id": composition["composition_id"],
        "action_ref": action_ref,
        "witness_ref": witness_ref,
        "effective_decision": composition["effective_decision"],
        "enforcement_mode": enforcement_mode,
        "delivery_status": delivery_status,
        "enforcement_point_status": enforcement_point_status,
        "action_status": action_status,
        "decision_alignment": _alignment(
            composition["effective_decision"], action_status, enforcement_point_status
        ),
        "liveness_status": liveness_status,
        "observed_at": observed_at,
        "evidence_refs": list(dict.fromkeys(evidence_refs)),
        "non_claims": [
            "lifecycle_satisfaction_not_established",
            "execution_witness_does_not_create_memory_authority",
        ],
    }
    if approval_evidence_ref:
        body["approval_evidence_ref"] = approval_evidence_ref

    witness = {
        "schema_version": "1.0.0",
        "witness_version": WITNESS_VERSION,
        "witness_id": f"execution-witness:{_sha256_ref(body)}",
        **body,
    }
    receipts.validate("execution-witness.schema.json", witness)
    return witness


def build_posture_report(
    *,
    policy_context_ref: str,
    configured_governance: bool,
    memory_write: str,
    recall_admission: str,
    background_maintenance: str,
    external_import: str,
    execution_witness: str,
    observed_witness_count: int,
    liveness_status: str,
    generated_at: str,
    evidence_refs: tuple[str, ...] = (),
) -> dict:
    """Describe configured enforcement separately from what was actually seen."""

    if not policy_context_ref or not generated_at:
        raise ValueError("posture report requires policy_context_ref and generated_at")
    surfaces = {
        "memory_write": memory_write,
        "recall_admission": recall_admission,
        "background_maintenance": background_maintenance,
        "external_import": external_import,
    }
    invalid = {name: value for name, value in surfaces.items() if value not in ENFORCEMENT_MODES}
    if invalid:
        raise ValueError(f"invalid enforcement surface modes: {invalid}")
    if execution_witness not in WITNESS_COVERAGE:
        raise ValueError(f"invalid execution_witness coverage {execution_witness!r}")
    if liveness_status not in LIVENESS_STATUSES:
        raise ValueError(f"invalid liveness_status {liveness_status!r}")
    if observed_witness_count < 0:
        raise ValueError("observed_witness_count cannot be negative")
    if execution_witness == "absent" and observed_witness_count:
        raise ValueError("absent execution witness capability cannot have observed witnesses")

    if observed_witness_count > 0:
        evidence_scope = "observed_enforcement"
    elif execution_witness in {"available", "partial"}:
        evidence_scope = "witness_capability_only"
    else:
        evidence_scope = "configuration_only"

    body = {
        "policy_context_ref": policy_context_ref,
        "configured_governance": configured_governance,
        "surfaces": surfaces,
        "execution_witness": execution_witness,
        "observed_witness_count": observed_witness_count,
        "liveness_status": liveness_status,
        "evidence_scope": evidence_scope,
        "generated_at": generated_at,
        "evidence_refs": list(dict.fromkeys(evidence_refs)),
    }
    report = {
        "schema_version": "1.0.0",
        "posture_version": POSTURE_VERSION,
        "report_id": f"enforcement-posture:{_sha256_ref(body)}",
        **body,
    }
    receipts.validate("enforcement-posture-report.schema.json", report)
    return report
