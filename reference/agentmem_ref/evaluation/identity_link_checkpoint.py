"""#757 evaluation-only Ed25519 binding of a replayed identity-link journal head.

A verified signature establishes possession of a signing key for particular
bytes, NOT semantic property identity, event truth, issuer authorization,
trusted time, currentness, or a lifecycle/recall permission.

The caller must supply stream, count, head and key pin OUTSIDE the attestation.
This module does not authenticate that independent channel and never verifies
issuer authority. It is NOT a runtime checkpoint or trusted storage service.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from ..memory.temporal_commitment import canonical_json
from ..memory.temporal_trust import public_key_digest
from .identity_link_journal import (
    JournalError, JournalReport, LinkEvent, MAX_EVENTS, _digest,
    _identifier, replay,
)

CHECKPOINT_PROFILE = "agent-memory/identity-link-checkpoint"
CHECKPOINT_VERSION = "0.1.0"
ALGORITHM = "Ed25519"
_MAX_B64 = 128


@dataclass(frozen=True)
class JournalHeadCheckpoint:
    profile: str
    version: str
    stream_ref: str
    event_count: int
    head_digest: str
    key_ref: str
    algorithm: str
    signature_b64: str


@dataclass(frozen=True)
class CheckpointVerification:
    cryptographic_status: Literal["valid", "invalid"]
    head_binding_status: Literal["match", "mismatch", "invalid_history"]
    key_pin_status: Literal["match", "mismatch"]
    key_ref_status: Literal["match", "mismatch"]
    reason_codes: tuple[str, ...]
    authenticated_issuer: Literal[False] = False
    semantic_identity_verified: Literal[False] = False
    trusted_time: Literal["not_established"] = "not_established"
    currentness: Literal["not_established"] = "not_established"
    authority_effect: Literal["none"] = "none"
    can_supersede: Literal[False] = False
    mutates_memory: Literal[False] = False
    integration_state: Literal["evaluation_only"] = "evaluation_only"


def _fields(checkpoint: JournalHeadCheckpoint) -> dict[str, object]:
    return {
        "profile": checkpoint.profile,
        "version": checkpoint.version,
        "stream_ref": checkpoint.stream_ref,
        "event_count": checkpoint.event_count,
        "head_digest": checkpoint.head_digest,
        "key_ref": checkpoint.key_ref,
        "algorithm": checkpoint.algorithm,
    }


def _validate(checkpoint: JournalHeadCheckpoint) -> None:
    if type(checkpoint) is not JournalHeadCheckpoint:
        raise ValueError("checkpoint must have the exact checkpoint shape")
    if checkpoint.profile != CHECKPOINT_PROFILE or checkpoint.version != CHECKPOINT_VERSION:
        raise ValueError("unsupported checkpoint contract")
    _identifier(checkpoint.stream_ref, "stream_ref")
    if type(checkpoint.event_count) is not int or not 0 <= checkpoint.event_count <= MAX_EVENTS:
        raise ValueError("invalid checkpoint event_count")
    _digest(checkpoint.head_digest, "checkpoint.head_digest")
    _identifier(checkpoint.key_ref, "key_ref")
    if checkpoint.algorithm != ALGORITHM:
        raise ValueError("unsupported checkpoint algorithm")
    if type(checkpoint.signature_b64) is not str or len(checkpoint.signature_b64) > _MAX_B64:
        raise ValueError("invalid signature encoding")


def _transcript(checkpoint: JournalHeadCheckpoint) -> bytes:
    # Canonical bytes supplied by the existing native temporal-commitment
    # evidence mechanism, bound to a DISTINCT domain/profile/version.
    return canonical_json(_fields(checkpoint))


def sign_journal_head(report: JournalReport, *, private_key: Ed25519PrivateKey,
                      key_ref: str) -> JournalHeadCheckpoint:
    """Produce an untrusted signer-origin claim over the exact replayed head."""
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("private_key must be an Ed25519PrivateKey")
    if type(report) is not JournalReport:
        raise TypeError("report must be a JournalReport")
    checked = replay(report.stream_ref, report.events)
    if checked != report:
        raise JournalError("report differs from recomputed history")
    _identifier(key_ref, "key_ref")
    unsigned = JournalHeadCheckpoint(
        profile=CHECKPOINT_PROFILE, version=CHECKPOINT_VERSION,
        stream_ref=report.stream_ref, event_count=len(report.events),
        head_digest=report.head_digest, key_ref=key_ref, algorithm=ALGORITHM,
        signature_b64="",
    )
    signature = private_key.sign(_transcript(unsigned))
    return JournalHeadCheckpoint(
        **{**_fields(unsigned), "signature_b64": base64.b64encode(signature).decode("ascii")}
    )


def verify_journal_head(
    events: tuple[LinkEvent, ...],
    checkpoint: JournalHeadCheckpoint,
    *,
    public_key: Ed25519PublicKey,
    expected_stream_ref: str,
    expected_head_digest: str,
    expected_event_count: int,
    expected_key_ref: str,
    pinned_public_key_digest: str,
) -> CheckpointVerification:
    """Check three distinct facts: cryptographic, key pin, and history binding.

    The expected values must come from a separately established channel.
    This function does not authenticate that channel; even all MATCH states
    cannot grant any property-identity, recall or lifecycle authority.
    """
    if not isinstance(public_key, Ed25519PublicKey):
        raise TypeError("public_key must be an Ed25519PublicKey")
    _identifier(expected_stream_ref, "expected_stream_ref")
    _digest(expected_head_digest, "expected_head_digest")
    if type(expected_event_count) is not int or not 0 <= expected_event_count <= MAX_EVENTS:
        raise ValueError("invalid expected_event_count")
    _identifier(expected_key_ref, "expected_key_ref")
    _digest(pinned_public_key_digest, "pinned_public_key_digest")

    reasons: set[str] = set()
    key_match = public_key_digest(public_key) == pinned_public_key_digest
    if not key_match:
        reasons.add("public_key_pin_mismatch")

    try:
        _validate(checkpoint)
        key_ref_match = checkpoint.key_ref == expected_key_ref
        if not key_ref_match:
            reasons.add("signer_key_ref_mismatch")
        signature = base64.b64decode(checkpoint.signature_b64, validate=True)
        if len(signature) != 64 or base64.b64encode(signature).decode("ascii") != checkpoint.signature_b64:
            raise ValueError("noncanonical signature")
        public_key.verify(signature, _transcript(checkpoint))
        crypto = "valid"
    except (ValueError, JournalError, binascii.Error, InvalidSignature, TypeError, UnicodeError):
        # Intentionally do not use a malformed checkpoint's key_ref as trust.
        crypto = "invalid"
        key_ref_match = (type(checkpoint) is JournalHeadCheckpoint
                         and checkpoint.key_ref == expected_key_ref)
        reasons.add("checkpoint_signature_or_contract_invalid")

    try:
        actual = replay(expected_stream_ref, events)
        head_match = all((
            type(checkpoint) is JournalHeadCheckpoint,
            checkpoint.stream_ref == expected_stream_ref,
            checkpoint.head_digest == expected_head_digest,
            checkpoint.event_count == expected_event_count,
            actual.head_digest == expected_head_digest,
            len(actual.events) == expected_event_count,
        ))
        binding = "match" if head_match else "mismatch"
        if not head_match:
            reasons.add("independent_head_binding_mismatch")
    except (JournalError, ValueError, TypeError):
        binding = "invalid_history"
        reasons.add("journal_replay_invalid")

    return CheckpointVerification(
        cryptographic_status=crypto,
        head_binding_status=binding,
        key_pin_status="match" if key_match else "mismatch",
        key_ref_status="match" if key_ref_match else "mismatch",
        reason_codes=tuple(sorted(reasons)),
    )
