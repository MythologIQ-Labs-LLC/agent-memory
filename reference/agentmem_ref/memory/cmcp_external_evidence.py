"""cMCP external-evidence adapter into Agent Memory's generic evidence seam.

The historical/default binding remains cMCP v0.4.0 because already-produced
qualification evidence must not be rewritten as though it came from a newer peer.
Version-exact qualification paths may supply a different source binding explicitly.

The adapter deliberately splits one cMCP GatewayClaim into separate evidence
records for enforcement/configuration posture and runtime attestation posture.
A global cMCP verification result is not collapsed into one boolean because a
claim can verify policy, signature, and audit facts while remaining explicitly
unverified for hardware attestation.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import rfc8785

from .external_evidence import (
    EvidenceContext,
    REVOCATION_NOT_REVOKED,
    VERIFIED,
    VERIFICATION_FAILED,
    VERIFICATION_UNKNOWN,
    normalize_external_evidence,
)

CMCP_PEER = "cMCP"
CMCP_VERSION = "cmcp-runtime==0.4.0"
CMCP_RELEASE = "a2e95151356c9ae6c545330c900f3d4af0e447c1"
CMCP_VERIFIER_ID = "cmcp-verify==0.4.0"
ADAPTER_ID = "agent-memory-cmcp-external-evidence"
ADAPTER_VERSION = "0.2.0"

_CRITICAL_ENFORCEMENT_FAILURES = {
    "SIGNATURE_INVALID",
    "PUBLIC_KEY_NOT_BOUND",
    "POLICY_HASH_MISMATCH",
    "CATALOG_HASH_MISMATCH",
    "CHAIN_BROKEN",
    "CHAIN_ROOT_NOT_BOUND",
    "CLAIM_MALFORMED",
    "AGENT_MANIFEST_MISMATCH",
}
_ATTESTATION_FAILURES = {
    "HARDWARE_ATTESTATION_FAILED",
    "PUBLIC_KEY_NOT_BOUND",
}
_REQUIRED_ENFORCEMENT_FIELDS = {
    "schema",
    "signature",
    "policy_bundle.hash",
    "tool_catalog.hash",
    "audit_chain",
}


def _iso_from_epoch(value: int) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("cMCP timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _attestation_expiry(gateway: Mapping[str, Any]) -> str:
    generated = _parse_time(str(gateway["attestation_generated_at"]))
    validity = int(gateway["attestation_validity_seconds"])
    if validity < 1:
        raise ValueError("cMCP attestation_validity_seconds must be positive")
    return (generated + timedelta(seconds=validity)).isoformat().replace("+00:00", "Z")


def _sha256_jcs(document: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(dict(document))).hexdigest()


def _verification_projection(result: Mapping[str, Any]) -> tuple[set[str], set[str], str | None]:
    verified = set(str(item) for item in result.get("verified_fields", []))
    unverified = set(str(item) for item in result.get("unverified_fields", []))
    failure = result.get("failure_reason")
    return verified, unverified, str(failure) if failure else None


def _enforcement_verification_status(result: Mapping[str, Any]) -> str:
    verified, _, failure = _verification_projection(result)
    if failure in _CRITICAL_ENFORCEMENT_FAILURES:
        return VERIFICATION_FAILED
    signer_bound = "public_key_binding" in verified or "trusted_public_key" in verified
    if _REQUIRED_ENFORCEMENT_FIELDS.issubset(verified) and signer_bound:
        return VERIFIED
    return VERIFICATION_UNKNOWN


def _attestation_verification_status(result: Mapping[str, Any]) -> str:
    verified, _, failure = _verification_projection(result)
    if "hardware_attestation" in verified:
        return VERIFIED
    if failure in _ATTESTATION_FAILURES:
        return VERIFICATION_FAILED
    return VERIFICATION_UNKNOWN


def _common_adapter_fields(claim: Mapping[str, Any]) -> dict[str, Any]:
    trace = claim["trace"]
    gateway = claim["gateway"]
    cnf = trace.get("cnf", {}).get("jwk", {})
    session_id = str(gateway["session_id"])
    sequence = int(gateway["sequence_number"])
    digest = _sha256_jcs(claim)
    audit = gateway["audit_chain"]
    catalog = gateway["catalog"]
    policy = trace["policy"]
    evidence_refs = [
        f"cmcp:claim:{digest}",
        f"cmcp:audit-root:{audit['root']}",
        f"cmcp:audit-tip:{audit['tip']}",
        f"cmcp:catalog:{catalog['hash']}",
        f"cmcp:policy-bundle:{policy['bundle_hash']}",
    ]
    agent_identity = gateway.get("agent_identity")
    if isinstance(agent_identity, Mapping) and agent_identity.get("manifest_id"):
        evidence_refs.append(f"agent-manifest:{agent_identity['manifest_id']}")
    return {
        "parse_status": "parsed",
        "source_peer": CMCP_PEER,
        "source_version": CMCP_VERSION,
        "source_release_ref": CMCP_RELEASE,
        "record_ref": f"cmcp:gateway-claim:{session_id}:{sequence}:{digest}",
        "evidence_digest": digest,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "issuer_id": str(trace["subject"]),
        "signer_id": str(cnf.get("kid") or trace["subject"]),
        "verifier_id": CMCP_VERIFIER_ID,
        "verification_method": "cmcp_verify.verify_trace_claim",
        "claim_scope": f"cmcp-session:{session_id}",
        "subject_ref": str(trace["subject"]),
        "issued_at": _iso_from_epoch(int(trace["iat"])),
        "revocation_status": REVOCATION_NOT_REVOKED,
        "policy_ref": str(policy["bundle_hash"]),
        "configuration_ref": (
            f"cmcp:gateway:{gateway['gateway_version']}:catalog:{catalog['hash']}:"
            f"policy-version:{policy.get('version', 'unknown')}"
        ),
        "evidence_refs": evidence_refs,
    }


def build_cmcp_adapter_results(
    claim: Mapping[str, Any],
    verifier_result: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build separate enforcement and attestation adapter results from one claim."""
    trace = claim.get("trace")
    gateway = claim.get("gateway")
    if not isinstance(trace, Mapping) or not isinstance(gateway, Mapping):
        raise ValueError("cMCP claim requires trace and gateway objects")
    policy = trace.get("policy")
    runtime = trace.get("runtime")
    if not isinstance(policy, Mapping) or not isinstance(runtime, Mapping):
        raise ValueError("cMCP claim requires trace.policy and trace.runtime")

    mode = str(policy.get("enforcement_mode", ""))
    if mode not in {"enforce", "advisory", "silent"}:
        raise ValueError(f"unsupported cMCP enforcement mode {mode!r}")
    platform = str(runtime.get("platform", ""))
    measurement = str(runtime.get("measurement", ""))
    if not platform or not measurement:
        raise ValueError("cMCP runtime platform and measurement are required")

    common = _common_adapter_fields(claim)
    global_status = str(verifier_result.get("status", "unknown"))
    failure = verifier_result.get("failure_reason")
    verified, unverified, _ = _verification_projection(verifier_result)

    enforcement_limitations = [
        "policy_enforcement_posture_is_not_execution_evidence",
        "gateway_decision_is_not_agent_memory_authority",
        "audit_chain_integrity_is_not_lifecycle_satisfaction",
        f"cmcp_global_verification_status:{global_status}",
    ]
    if failure:
        enforcement_limitations.append(f"cmcp_verifier_failure:{failure}")
    if "hardware_attestation" in unverified:
        enforcement_limitations.append("hardware_attestation_not_established_by_this_claim")

    attestation_status = _attestation_verification_status(verifier_result)
    if "hardware_attestation" in verified:
        attestation_mode = f"hardware_verified:{platform}"
    elif platform == "software-only":
        attestation_mode = "software_only_unverified"
    else:
        attestation_mode = f"hardware_unverified:{platform}"

    attestation_limitations = [
        "runtime_attestation_does_not_create_agent_memory_authority",
        "runtime_measurement_does_not_establish_semantic_correctness",
        f"cmcp_global_verification_status:{global_status}",
    ]
    if failure:
        attestation_limitations.append(f"cmcp_verifier_failure:{failure}")
    if attestation_status != VERIFIED:
        attestation_limitations.append("hardware_attestation_not_verified")

    enforcement = {
        **common,
        "verification_status": _enforcement_verification_status(verifier_result),
        "claim_type": "enforcement",
        "enforcement_posture": mode,
        "runtime_ref": f"cmcp-runtime:{platform}:{measurement}",
        "limitations": enforcement_limitations,
    }

    attestation = {
        **common,
        "issued_at": str(gateway["attestation_generated_at"]),
        "expires_at": _attestation_expiry(gateway),
        "verification_status": attestation_status,
        "claim_type": "attestation",
        "runtime_ref": f"cmcp-runtime:{platform}:{measurement}",
        "attestation_mode": attestation_mode,
        "limitations": attestation_limitations,
    }
    return enforcement, attestation


def _rebind_source(
    records: tuple[dict[str, Any], dict[str, Any]],
    *,
    source_version: str,
    source_release_ref: str,
    verifier_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind newly executed peer evidence to the exact peer that produced it.

    Historical/default v0.4.0 constants remain untouched. This helper exists so a
    qualification run cannot accidentally execute cMCP 0.5.0 while labeling the
    evidence as 0.4.0, which would be a pleasantly green but useless lie.
    """
    if not source_version or not source_release_ref or not verifier_id:
        raise ValueError("exact cMCP source version, release ref, and verifier id are required")
    rebound = []
    for record in records:
        row = dict(record)
        row["source_version"] = source_version
        row["source_release_ref"] = source_release_ref
        row["verifier_id"] = verifier_id
        rebound.append(row)
    return rebound[0], rebound[1]


def build_cmcp_adapter_results_for_source(
    claim: Mapping[str, Any],
    verifier_result: Mapping[str, Any],
    *,
    source_version: str,
    source_release_ref: str,
    verifier_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build records bound to an explicitly qualified cMCP peer revision."""
    return _rebind_source(
        build_cmcp_adapter_results(claim, verifier_result),
        source_version=source_version,
        source_release_ref=source_release_ref,
        verifier_id=verifier_id,
    )


def normalize_cmcp_claim(
    claim: Mapping[str, Any],
    verifier_result: Mapping[str, Any],
    *,
    observed_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize cMCP enforcement and attestation evidence under exact session context."""
    enforcement_adapter, attestation_adapter = build_cmcp_adapter_results(claim, verifier_result)
    context = EvidenceContext(
        subject_ref=enforcement_adapter["subject_ref"],
        scope=enforcement_adapter["claim_scope"],
    )
    return (
        normalize_external_evidence(
            enforcement_adapter,
            context=context,
            observed_at=observed_at,
        ),
        normalize_external_evidence(
            attestation_adapter,
            context=context,
            observed_at=observed_at,
        ),
    )


def normalize_cmcp_claim_for_source(
    claim: Mapping[str, Any],
    verifier_result: Mapping[str, Any],
    *,
    observed_at: str,
    source_version: str,
    source_release_ref: str,
    verifier_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize evidence from a non-default cMCP peer under exact source binding."""
    enforcement_adapter, attestation_adapter = build_cmcp_adapter_results_for_source(
        claim,
        verifier_result,
        source_version=source_version,
        source_release_ref=source_release_ref,
        verifier_id=verifier_id,
    )
    context = EvidenceContext(
        subject_ref=enforcement_adapter["subject_ref"],
        scope=enforcement_adapter["claim_scope"],
    )
    return (
        normalize_external_evidence(
            enforcement_adapter,
            context=context,
            observed_at=observed_at,
        ),
        normalize_external_evidence(
            attestation_adapter,
            context=context,
            observed_at=observed_at,
        ),
    )
