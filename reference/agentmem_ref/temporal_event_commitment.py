"""Cryptographically committed temporal event evidence for #263 / ADR-031.

Temporal meaning is part of the content-addressed commitment. Signer evidence,
trusted-time witnesses, currentness, and authority remain separate layers.
"""
from __future__ import annotations

import base64
import hashlib
import unicodedata
from datetime import datetime
from typing import Any, Callable, Mapping

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from . import receipts
from .uor_content_reference import evaluate_json_content_reference

PROFILE_ID = "agent-memory/temporal-event-commitment"
PROFILE_VERSION = "0.1.0"
CANONICALIZATION = "uax15-nfc+rfc8785-jcs"
HASH_ALGORITHM = "sha256"
SIGNATURE_DOMAIN = b"agent-memory-temporal-event-v1\0"
SIGNATURE_ALGORITHM = "ed25519"
AUTHORITY_EFFECT = "none"
UOR_PROFILE_ID = "agent-memory/uor-addr-json-content-reference"


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _time(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    _nonempty(value, field)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return value


def _digest(value: str, field: str) -> str:
    _nonempty(value, field)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be sha256:<64hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be sha256:<64hex>") from exc
    if value[7:] != value[7:].lower():
        raise ValueError(f"{field} must use lowercase hex")
    return value


def _normalize_nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("temporal commitment object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in output:
                raise ValueError("Unicode NFC normalization creates a duplicate object key")
            output[normalized_key] = _normalize_nfc(item)
        return output
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise ValueError(f"unsupported temporal commitment value type: {type(value).__name__}")


def canonical_temporal_bytes(commitment: Mapping[str, Any]) -> bytes:
    if not isinstance(commitment, Mapping):
        raise ValueError("commitment must be an object")
    try:
        return rfc8785.dumps(_normalize_nfc(dict(commitment)))
    except Exception as exc:
        raise ValueError(f"temporal commitment cannot be canonicalized: {exc}") from exc


def temporal_content_ref(commitment: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_temporal_bytes(commitment)).hexdigest()


def _signature_message(commitment_ref: str, key_id: str) -> bytes:
    binding = {
        "commitment_ref": _digest(commitment_ref, "commitment_ref"),
        "key_id": _nonempty(key_id, "key_id"),
    }
    return SIGNATURE_DOMAIN + rfc8785.dumps(binding)


def _signature_ref(signature_bytes: bytes) -> str:
    return "sha256:" + hashlib.sha256(signature_bytes).hexdigest()


def build_temporal_commitment(*, event_type: str, payload_digest: str, event_time: str,
    observed_at: str, scope_ref: str, stream_id: str, sequence: int,
    source_schema_ref: str, source_schema_digest: str,
    previous_event_ref: str | None = None, valid_from: str | None = None,
    valid_to: str | None = None, projection_profile: str | None = None,
    projection_version: str | None = None) -> dict[str, Any]:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ValueError("sequence must be a positive integer")
    event_time = _time(event_time, "event_time")
    observed_at = _time(observed_at, "observed_at")
    valid_from = _time(valid_from, "valid_from")
    valid_to = _time(valid_to, "valid_to")
    if valid_from and valid_to:
        if datetime.fromisoformat(valid_to.replace("Z", "+00:00")) < datetime.fromisoformat(valid_from.replace("Z", "+00:00")):
            raise ValueError("valid_to cannot precede valid_from")
    if sequence == 1 and previous_event_ref is not None:
        raise ValueError("sequence 1 must not declare previous_event_ref")
    if sequence > 1 and previous_event_ref is None:
        raise ValueError("sequence > 1 requires previous_event_ref")
    if previous_event_ref is not None:
        previous_event_ref = _digest(previous_event_ref, "previous_event_ref")
    if (projection_profile is None) != (projection_version is None):
        raise ValueError("projection_profile and projection_version must be supplied together")
    commitment: dict[str, Any] = {
        "profile_id": PROFILE_ID,
        "profile_version": PROFILE_VERSION,
        "event_type": _nonempty(event_type, "event_type"),
        "payload_digest": _digest(payload_digest, "payload_digest"),
        "event_time": event_time,
        "observed_at": observed_at,
        "scope_ref": _nonempty(scope_ref, "scope_ref"),
        "stream_id": _nonempty(stream_id, "stream_id"),
        "sequence": sequence,
        "source_schema_ref": _nonempty(source_schema_ref, "source_schema_ref"),
        "source_schema_digest": _digest(source_schema_digest, "source_schema_digest"),
    }
    if previous_event_ref is not None:
        commitment["previous_event_ref"] = previous_event_ref
    if valid_from is not None:
        commitment["valid_from"] = valid_from
    if valid_to is not None:
        commitment["valid_to"] = valid_to
    if projection_profile is not None:
        commitment["projection_profile"] = _nonempty(projection_profile, "projection_profile")
        commitment["projection_version"] = _nonempty(projection_version, "projection_version")
    return _normalize_nfc(commitment)


def sign_temporal_commitment(commitment: Mapping[str, Any], *, private_key: Ed25519PrivateKey,
    key_id: str, trusted_time_witness: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("private_key must be Ed25519PrivateKey")
    commitment_norm = _normalize_nfc(dict(commitment))
    commitment_ref = temporal_content_ref(commitment_norm)
    key_id = _nonempty(key_id, "key_id")
    signature_bytes = private_key.sign(_signature_message(commitment_ref, key_id))
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    signature = {
        "algorithm": SIGNATURE_ALGORITHM,
        "domain": SIGNATURE_DOMAIN[:-1].decode("ascii"),
        "key_id": key_id,
        "public_key_base64": base64.b64encode(public_key).decode("ascii"),
        "signature_base64": base64.b64encode(signature_bytes).decode("ascii"),
        "signature_ref": _signature_ref(signature_bytes),
    }
    document: dict[str, Any] = {
        "schema_version": "1.0.0", "profile_id": PROFILE_ID,
        "profile_version": PROFILE_VERSION, "canonicalization": CANONICALIZATION,
        "hash_algorithm": HASH_ALGORITHM, "commitment_ref": commitment_ref,
        "commitment": commitment_norm, "signature": signature,
        "trusted_time": {"status": "unwitnessed", "claim": "signer_commitment_only", "authority_effect": AUTHORITY_EFFECT},
        "interpretation": _interpretation(),
    }
    if trusted_time_witness is not None:
        document["trusted_time"] = _normalize_witness(trusted_time_witness, signature["signature_ref"])
    receipts.validate("temporal-event-commitment.schema.json", document)
    return document


def _normalize_witness(value: Mapping[str, Any], expected_subject_ref: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("trusted_time_witness must be an object")
    kind = _nonempty(value.get("kind"), "trusted_time_witness.kind")
    if kind not in {"rfc3161", "transparency_log", "other"}:
        raise ValueError("trusted_time_witness.kind is unsupported")
    subject_ref = _digest(value.get("subject_ref"), "trusted_time_witness.subject_ref")
    if subject_ref != expected_subject_ref:
        raise ValueError("trusted_time_witness.subject_ref must bind the exact signature_ref")
    witnessed_at = _time(value.get("witnessed_at"), "trusted_time_witness.witnessed_at")
    verified = value.get("verified")
    if not isinstance(verified, bool):
        raise ValueError("trusted_time_witness.verified must be boolean")
    evidence_refs = value.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or not all(isinstance(item, str) and item for item in evidence_refs):
        raise ValueError("trusted_time_witness.evidence_refs must be non-empty strings")
    if verified and not evidence_refs:
        raise ValueError("verified trusted-time witness requires evidence_refs")
    return {
        "status": "verified" if verified else "unverified", "kind": kind,
        "subject_ref": subject_ref, "witnessed_at": witnessed_at,
        "witness_ref": _nonempty(value.get("witness_ref"), "trusted_time_witness.witness_ref"),
        "verified": verified, "evidence_refs": list(dict.fromkeys(evidence_refs)),
        "claim": "independent_time_evidence" if verified else "unverified_time_evidence",
        "authority_effect": AUTHORITY_EFFECT,
    }


def _interpretation() -> dict[str, Any]:
    return {
        "authority_effect": AUTHORITY_EFFECT, "content_identity_only": True,
        "signature_proves": "signer_commitment_to_exact_temporal_object",
        "signature_proves_trusted_wall_clock": False,
        "chain_proves_complete_history": False, "chain_proves_deletion_completeness": False,
        "can_create_lifecycle_currentness": False, "can_satisfy_pama_mutation_authority": False,
        "can_create_reusable_authority": False,
    }


def verify_temporal_commitment(document: Mapping[str, Any]) -> dict[str, Any]:
    receipts.validate("temporal-event-commitment.schema.json", dict(document))
    reasons: list[str] = []
    if temporal_content_ref(document["commitment"]) != document["commitment_ref"]:
        reasons.append("content_reference_mismatch")
    signature = document["signature"]
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(signature["public_key_base64"], validate=True))
        signature_bytes = base64.b64decode(signature["signature_base64"], validate=True)
        public_key.verify(signature_bytes, _signature_message(document["commitment_ref"], signature["key_id"]))
        if _signature_ref(signature_bytes) != signature["signature_ref"]:
            reasons.append("signature_reference_mismatch")
    except (ValueError, InvalidSignature):
        reasons.append("signature_invalid")
    return {
        "status": "verified" if not reasons else "invalid",
        "commitment_ref": document["commitment_ref"],
        "signature_valid": "signature_invalid" not in reasons and "signature_reference_mismatch" not in reasons,
        "content_identity_valid": "content_reference_mismatch" not in reasons,
        "trusted_time_status": document["trusted_time"]["status"], "reason_codes": reasons,
        **_interpretation(),
    }


def verify_temporal_chain(documents: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not documents:
        raise ValueError("temporal chain must contain at least one event")
    reasons: list[str] = []
    expected_stream = documents[0]["commitment"]["stream_id"]
    expected_scope = documents[0]["commitment"]["scope_ref"]
    previous_ref: str | None = None
    for index, document in enumerate(documents, start=1):
        if verify_temporal_commitment(document)["status"] != "verified":
            reasons.append(f"event_{index}_cryptographic_verification_failed")
        commitment = document["commitment"]
        if commitment["sequence"] != index:
            reasons.append(f"event_{index}_sequence_mismatch")
        if commitment["stream_id"] != expected_stream:
            reasons.append(f"event_{index}_stream_mismatch")
        if commitment["scope_ref"] != expected_scope:
            reasons.append(f"event_{index}_scope_mismatch")
        actual_previous = commitment.get("previous_event_ref")
        if index == 1 and actual_previous is not None:
            reasons.append("event_1_unexpected_previous_ref")
        elif index > 1 and actual_previous != previous_ref:
            reasons.append(f"event_{index}_previous_ref_mismatch")
        previous_ref = document["commitment_ref"]
    return {
        "status": "verified" if not reasons else "invalid", "event_count": len(documents),
        "stream_id": expected_stream, "scope_ref": expected_scope, "reason_codes": reasons,
        "proves_complete_history": False, "proves_deletion_completeness": False,
        "authority_effect": AUTHORITY_EFFECT,
    }


def evaluate_uor_temporal_compatibility(document: Mapping[str, Any], *, address_fn: Callable[[bytes], str],
    binding_name: str, binding_version: str) -> dict[str, Any]:
    receipts.validate("temporal-event-commitment.schema.json", dict(document))
    evidence = evaluate_json_content_reference(
        canonical_temporal_bytes(document["commitment"]), address_fn=address_fn,
        binding_name=binding_name, binding_version=binding_version,
        claimed_label=document["commitment_ref"])
    return {
        "status": evidence["status"], "commitment_ref": document["commitment_ref"],
        "uor_profile_id": UOR_PROFILE_ID, "uor_evidence": evidence,
        "authority_effect": AUTHORITY_EFFECT, "ordinary_agent_memory_requires_uor_runtime": False,
    }
