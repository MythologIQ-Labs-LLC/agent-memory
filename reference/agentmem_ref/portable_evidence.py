"""Portable Agent Memory governance evidence, P4.5a reference profile.

This module projects a canonical Agent Memory decision receipt into a content-free,
portable evidence object.  The canonical receipt remains authoritative; the
portable object only binds that receipt to governance, authority, domain, runtime,
and lifecycle references so another process can verify what happened without
receiving raw memory content.

The first executable trust profile deliberately uses HMAC-SHA256 from the Python
standard library.  It is a symmetric trust-domain profile, not a public-key or
non-repudiation scheme.  The evidence format names the algorithm explicitly so a
later asymmetric profile can replace it without changing the semantic boundary.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

EVIDENCE_TYPE = "agent-memory-governance-evidence"
EVIDENCE_VERSION = "1.0.0"
ALGORITHM = "HMAC-SHA256"

INTEGRITY_VALID = "valid"
INTEGRITY_INVALID = "invalid"
INTEGRITY_UNVERIFIABLE = "unverifiable"

GOVERNANCE_VALUES = {
    "permitted",
    "denied",
    "deferred",
    "review_required",
    "committed",
}
LIFECYCLE_VALUES = {
    "satisfied",
    "residual",
    "incomplete",
    "unverifiable",
    "not_applicable",
}


def canonical_json(value: object) -> bytes:
    """Return the v1 canonical JSON byte representation.

    v1 is UTF-8 JSON with sorted object keys, no insignificant whitespace, and
    non-ASCII characters preserved.  Floats are intentionally unsupported in
    the evidence contract because cross-runtime float canonicalization is a
    larger problem than this reference profile needs to invent.
    """
    _reject_floats(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _reject_floats(value: object) -> None:
    if isinstance(value, float):
        raise TypeError("portable evidence v1 does not permit floating-point values")
    if isinstance(value, dict):
        for item in value.values():
            _reject_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_floats(item)


def sha256_ref(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class TrustKey:
    """One configured symmetric trust anchor for the reference profile."""

    issuer_id: str
    key_id: str
    secret: bytes
    valid_from: str
    valid_until: str | None = None
    revoked_at: str | None = None

    def usable_at(self, timestamp: str) -> bool:
        point = _parse_time(timestamp)
        if point < _parse_time(self.valid_from):
            return False
        if self.valid_until and point > _parse_time(self.valid_until):
            return False
        if self.revoked_at and point >= _parse_time(self.revoked_at):
            return False
        return True


@dataclass(frozen=True)
class RuntimeObservation:
    """Optional execution-time facts supplied independently by a verifier."""

    action_ref: str | None = None
    execution_time: str | None = None
    policy_ref: str | None = None
    authority_state_ref: str | None = None
    source_domain_ref: str | None = None
    destination_domain_ref: str | None = None
    authority_valid_at_execution: bool | None = None


def issue_evidence(
    canonical_receipt: Mapping[str, object],
    *,
    issuer_id: str,
    key: TrustKey,
    issued_at: str,
    action_ref: str,
    memory_action: str,
    governance_disposition: str,
    policy_ref: str,
    authority_state_ref: str,
    decision_time: str,
    scope_ref: str,
    before_state_ref: str,
    after_state_ref: str,
    lifecycle_result: str = "not_applicable",
    source_domain_ref: str | None = None,
    destination_domain_ref: str | None = None,
    domain_authorization_state_ref: str | None = None,
) -> dict:
    """Create and authenticate a portable projection of a canonical receipt."""
    if issuer_id != key.issuer_id:
        raise ValueError("issuer_id must match the configured trust key")
    if governance_disposition not in GOVERNANCE_VALUES:
        raise ValueError(f"unsupported governance disposition: {governance_disposition}")
    if lifecycle_result not in LIFECYCLE_VALUES:
        raise ValueError(f"unsupported lifecycle result: {lifecycle_result}")
    if not key.usable_at(issued_at):
        raise ValueError("trust key is not valid at evidence issuance time")

    scope = {"scope_ref": scope_ref}
    for name, value in (
        ("source_domain_ref", source_domain_ref),
        ("destination_domain_ref", destination_domain_ref),
        ("domain_authorization_state_ref", domain_authorization_state_ref),
    ):
        if value is not None:
            scope[name] = value

    evidence = {
        "evidence_type": EVIDENCE_TYPE,
        "version": EVIDENCE_VERSION,
        "canonicalization": "agent-memory-canonical-json-v1",
        "issuer": {
            "id": issuer_id,
            "key_id": key.key_id,
            "algorithm": ALGORITHM,
        },
        "issued_at": issued_at,
        "action_ref": action_ref,
        "memory_action": memory_action,
        "canonical_receipt_ref": sha256_ref(dict(canonical_receipt)),
        "governance": {
            "disposition": governance_disposition,
            "policy_ref": policy_ref,
            "authority_state_ref": authority_state_ref,
            "decision_time": decision_time,
        },
        "scope": scope,
        "state": {
            "before_ref": before_state_ref,
            "after_ref": after_state_ref,
        },
        "lifecycle_result": lifecycle_result,
    }
    evidence["authentication"] = {
        "algorithm": ALGORITHM,
        "key_id": key.key_id,
        "value": _mac(evidence, key.secret),
    }
    return evidence


def _signable(evidence: Mapping[str, object]) -> dict:
    payload = copy.deepcopy(dict(evidence))
    payload.pop("authentication", None)
    return payload


def _mac(evidence: Mapping[str, object], secret: bytes) -> str:
    return hmac.new(secret, canonical_json(_signable(evidence)), hashlib.sha256).hexdigest()


def verify_evidence(
    evidence: Mapping[str, object],
    trust_keys: Mapping[tuple[str, str], TrustKey],
    *,
    canonical_receipt: Mapping[str, object] | None = None,
    runtime: RuntimeObservation | None = None,
) -> dict:
    """Verify evidence while keeping semantic outcome dimensions separate.

    A cryptographically authentic denial is still a denial.  Likewise, a valid
    authorized delete with residual derived state remains a lifecycle failure.
    """
    runtime = runtime or RuntimeObservation()
    failures: list[str] = []

    if evidence.get("evidence_type") != EVIDENCE_TYPE or evidence.get("version") != EVIDENCE_VERSION:
        return _result(INTEGRITY_INVALID, ["unsupported_evidence_profile"], evidence, "unresolved", runtime)

    issuer = evidence.get("issuer")
    auth = evidence.get("authentication")
    if not isinstance(issuer, dict) or not isinstance(auth, dict):
        return _result(INTEGRITY_INVALID, ["missing_authentication_metadata"], evidence, "unresolved", runtime)

    issuer_id = issuer.get("id")
    key_id = issuer.get("key_id")
    if issuer.get("algorithm") != ALGORITHM or auth.get("algorithm") != ALGORITHM or auth.get("key_id") != key_id:
        return _result(INTEGRITY_INVALID, ["algorithm_or_key_binding_mismatch"], evidence, "unresolved", runtime)

    key = trust_keys.get((str(issuer_id), str(key_id)))
    if key is None:
        return _result(INTEGRITY_UNVERIFIABLE, ["unknown_or_untrusted_issuer_key"], evidence, "unresolved", runtime)

    issued_at = evidence.get("issued_at")
    if not isinstance(issued_at, str) or not key.usable_at(issued_at):
        return _result(INTEGRITY_UNVERIFIABLE, ["issuer_key_not_valid_at_issuance"], evidence, "unresolved", runtime)

    expected_mac = _mac(evidence, key.secret)
    if not hmac.compare_digest(str(auth.get("value", "")), expected_mac):
        return _result(INTEGRITY_INVALID, ["authentication_failed"], evidence, "unresolved", runtime)

    receipt_resolution = "detached"
    if canonical_receipt is not None:
        if sha256_ref(dict(canonical_receipt)) != evidence.get("canonical_receipt_ref"):
            failures.append("canonical_receipt_hash_mismatch")
            receipt_resolution = "mismatch"
        else:
            receipt_resolution = "resolved"

    governance = evidence.get("governance") if isinstance(evidence.get("governance"), dict) else {}
    scope = evidence.get("scope") if isinstance(evidence.get("scope"), dict) else {}

    for observed, signed, failure in (
        (runtime.action_ref, evidence.get("action_ref"), "wrong_action_ref"),
        (runtime.policy_ref, governance.get("policy_ref"), "stale_or_wrong_policy_ref"),
        (runtime.authority_state_ref, governance.get("authority_state_ref"), "stale_or_wrong_authority_state_ref"),
        (runtime.source_domain_ref, scope.get("source_domain_ref"), "wrong_source_domain"),
        (runtime.destination_domain_ref, scope.get("destination_domain_ref"), "wrong_destination_domain"),
    ):
        if observed is not None and observed != signed:
            failures.append(failure)

    integrity = INTEGRITY_VALID if not failures else INTEGRITY_INVALID
    return _result(integrity, failures, evidence, receipt_resolution, runtime)


def _result(
    integrity: str,
    failures: list[str],
    evidence: Mapping[str, object],
    receipt_resolution: str,
    runtime: RuntimeObservation,
) -> dict:
    governance = evidence.get("governance") if isinstance(evidence.get("governance"), dict) else {}
    disposition = governance.get("disposition", "unverifiable")
    lifecycle = evidence.get("lifecycle_result", "unverifiable")

    if runtime.action_ref is None:
        execution = "not_executed"
    elif "wrong_action_ref" in failures:
        execution = "execution_mismatch"
    elif disposition in {"denied", "deferred", "review_required"}:
        execution = "unauthorized_execution"
    elif runtime.authority_valid_at_execution is False:
        execution = "unauthorized_execution"
    elif runtime.authority_valid_at_execution is None and runtime.execution_time is not None:
        execution = "unverifiable"
    elif integrity == INTEGRITY_VALID:
        execution = "executed_as_authorized"
    else:
        execution = "unverifiable"

    return {
        "evidence_integrity": integrity,
        "binding_failures": failures,
        "receipt_resolution": receipt_resolution,
        "governance_disposition": disposition,
        "runtime_execution": execution,
        "lifecycle_satisfaction": lifecycle,
    }
