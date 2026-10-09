"""#757 J73-J88: proposal-only exact source/actor write-revision witnesses.

Signatures and caller-supplied pins show mechanical commitment to bytes, NOT
verified organizational principals, independent issuance or semantic identity.
No lifecycle, memory, PAMA, currentness or runtime mutation is possible.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import base64
import binascii
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)

from ..memory.temporal_commitment import canonical_json
from ..memory.temporal_trust import public_key_digest
from .identity_link_journal import _digest, _identifier
from .proposition_link_preflight import (
    ObservedWrite, ProposedIdentityLink, preflight,
)

PROFILE = "agent-memory/write-revision-origin-witness"
VERSION = "0.1.0"
ALGORITHM = "Ed25519"
MAX_TRANSCRIPT_BYTES = 8192
MAX_WITNESSES = 4
MAX_SIGNATURE_B64 = 128
SIDES = frozenset(("older", "newer"))
ROLES = frozenset(("actor", "source"))
EXPECTED_POSITIONS = frozenset(
    (side, role) for side in SIDES for role in ROLES
)


class WitnessError(ValueError):
    """A proposed witness has an invalid bounded shape or contents."""


@dataclass(frozen=True)
class SignedWriteWitness:
    profile: str
    version: str
    algorithm: str
    side: Literal["older", "newer"]
    role: Literal["actor", "source"]
    claimed_principal_ref: str
    key_ref: str
    observed: ObservedWrite
    signature_b64: str


@dataclass(frozen=True)
class WitnessExpectation:
    side: Literal["older", "newer"]
    role: Literal["actor", "source"]
    expected_principal_ref: str
    expected_key_ref: str
    pinned_public_key_digest: str

    def __post_init__(self) -> None:
        if type(self.side) is not str or self.side not in SIDES:
            raise WitnessError("invalid expected observation side")
        if type(self.role) is not str or self.role not in ROLES:
            raise WitnessError("invalid expected principal role")
        _identifier(self.expected_principal_ref, "expected_principal_ref")
        _identifier(self.expected_key_ref, "expected_key_ref")
        _digest(self.pinned_public_key_digest, "pinned_public_key_digest")


@dataclass(frozen=True)
class WitnessInput:
    signed: SignedWriteWitness
    public_key: Ed25519PublicKey
    expected: WitnessExpectation


@dataclass(frozen=True)
class WitnessQualification:
    status: Literal["cryptographic_witness_candidate", "abstain", "refused"]
    reason_codes: tuple[str, ...]
    signature_matches: int
    pin_matches: int
    required_positions: int
    observed_positions: int
    preflight_status: Literal["refused", "underdetermined", "structurally_plausible_unverified"]
    preflight_reason_codes: tuple[str, ...]
    principal_authenticated: Literal[False] = False
    origin_independence_verified: Literal[False] = False
    issuer_authorized: Literal[False] = False
    identity_verified: Literal[False] = False
    can_supersede: Literal[False] = False
    authority_effect: Literal["none"] = "none"
    mutates_memory: Literal[False] = False
    currentness: Literal["not_established"] = "not_established"
    integration_state: Literal["evaluation_only"] = "evaluation_only"


def _validate_shape(signed: SignedWriteWitness) -> None:
    if type(signed) is not SignedWriteWitness:
        raise WitnessError("witness must be exact SignedWriteWitness")
    if (signed.profile != PROFILE or signed.version != VERSION
            or signed.algorithm != ALGORITHM):
        raise WitnessError("unsupported witness signing contract")
    if type(signed.side) is not str or signed.side not in SIDES:
        raise WitnessError("invalid witness side")
    if type(signed.role) is not str or signed.role not in ROLES:
        raise WitnessError("invalid witness role")
    _identifier(signed.claimed_principal_ref, "claimed_principal_ref")
    _identifier(signed.key_ref, "key_ref")
    if type(signed.observed) is not ObservedWrite:
        raise WitnessError("witness observation must be exact ObservedWrite")
    # Revalidate field typing after any unsafe object.__setattr__ mutation.
    obs = signed.observed
    ObservedWrite(**asdict(obs))
    if (type(signed.signature_b64) is not str
            or len(signed.signature_b64) > MAX_SIGNATURE_B64):
        raise WitnessError("invalid bounded signature")


def _transcript(signed: SignedWriteWitness) -> bytes:
    _validate_shape(signed)
    payload = canonical_json({
        "profile": signed.profile,
        "version": signed.version,
        "algorithm": signed.algorithm,
        "side": signed.side,
        "role": signed.role,
        "claimed_principal_ref": signed.claimed_principal_ref,
        "key_ref": signed.key_ref,
        "observed": asdict(signed.observed),
    })
    if len(payload) > MAX_TRANSCRIPT_BYTES:
        raise WitnessError("witness transcript is oversized")
    return payload


def sign_write_witness(
    observed: ObservedWrite,
    *,
    side: Literal["older", "newer"],
    role: Literal["actor", "source"],
    claimed_principal_ref: str,
    key_ref: str,
    private_key: Ed25519PrivateKey,
) -> SignedWriteWitness:
    """Create a signer claim, never a validated provenance credential."""
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("private_key must be Ed25519PrivateKey")
    blank = SignedWriteWitness(
        PROFILE, VERSION, ALGORITHM, side, role, claimed_principal_ref,
        key_ref, observed, "",
    )
    signature = private_key.sign(_transcript(blank))
    return SignedWriteWitness(
        PROFILE, VERSION, ALGORITHM, side, role, claimed_principal_ref,
        key_ref, observed, base64.b64encode(signature).decode("ascii"),
    )


def _verify_one(
    supplied: WitnessInput,
    observed: ObservedWrite,
) -> tuple[bool, bool, set[str]]:
    reasons: set[str] = set()
    if type(supplied) is not WitnessInput:
        return False, False, {"invalid_witness_input_shape"}
    if (type(supplied.signed) is not SignedWriteWitness
            or type(supplied.expected) is not WitnessExpectation
            or not isinstance(supplied.public_key, Ed25519PublicKey)):
        return False, False, {"invalid_witness_material"}
    signed, expected, key = supplied.signed, supplied.expected, supplied.public_key
    pin_ok = (public_key_digest(key) == expected.pinned_public_key_digest)
    if not pin_ok:
        reasons.add("witness_key_material_pin_mismatch")
    if ((signed.side, signed.role) != (expected.side, expected.role)
            or signed.key_ref != expected.expected_key_ref):
        reasons.add("witness_role_or_key_reference_mismatch")
    principal = (observed.actor_ref if expected.role == "actor"
                 else observed.source_ref)
    if (signed.claimed_principal_ref != expected.expected_principal_ref
            or signed.claimed_principal_ref != principal):
        reasons.add("witness_principal_binding_mismatch")
    # D4: compare exact field bytes, never user-defined __eq__ dispatch.
    if (type(observed) is not ObservedWrite
            or type(signed.observed) is not ObservedWrite
            or asdict(signed.observed) != asdict(observed)):
        reasons.add("witness_observation_revision_mismatch")
    sig_ok = False
    try:
        data = _transcript(signed)
        raw = base64.b64decode(signed.signature_b64, validate=True)
        if len(raw) != 64 or base64.b64encode(raw).decode("ascii") != signed.signature_b64:
            raise WitnessError("noncanonical signature encoding")
        key.verify(raw, data)
        sig_ok = True
    except (WitnessError, ValueError, TypeError, binascii.Error, InvalidSignature,
            UnicodeError):
        reasons.add("witness_signature_or_contract_invalid")
    return sig_ok, pin_ok, reasons


def qualify_write_origins(
    proposal: ProposedIdentityLink,
    witnesses: tuple[WitnessInput, ...],
) -> WitnessQualification:
    """Mechanical matching only; out-of-band anchor authenticity is unknown.

    A positive result is a **candidate** even when distinct keys and apparently
    independent principals are present. This code does not inspect registries,
    authorize issuers or infer property equivalence.
    """
    if type(proposal) is not ProposedIdentityLink:
        raise TypeError("proposal must be exact ProposedIdentityLink")
    if type(witnesses) is not tuple:
        raise TypeError("witnesses must be a tuple")
    reasons: set[str] = set()
    base = preflight(proposal)
    # D4: a dataclass subclass can override equality without changing fields.
    # It must never be accepted as a signed observation.
    if (type(proposal.older) is not ObservedWrite
            or type(proposal.newer) is not ObservedWrite):
        reasons.add("noncanonical_proposed_observation_type")
    if base.status == "refused":
        reasons.add("structural_preflight_refused")
    elif base.status == "underdetermined":
        reasons.add("structural_preflight_underdetermined")
    if len(witnesses) > MAX_WITNESSES:
        reasons.add("unexpected_witness_count")
    positions: set[tuple[str, str]] = set()
    signatures = 0
    pins = 0
    for item in witnesses:
        if type(item) is not WitnessInput or type(item.expected) is not WitnessExpectation:
            reasons.add("invalid_witness_input_shape")
            continue
        pos = (item.expected.side, item.expected.role)
        if pos not in EXPECTED_POSITIONS or pos in positions:
            reasons.add("duplicate_or_unknown_witness_position")
            continue
        positions.add(pos)
        observed = proposal.older if pos[0] == "older" else proposal.newer
        sig_ok, pin_ok, one = _verify_one(item, observed)
        signatures += int(sig_ok)
        pins += int(pin_ok)
        reasons.update(one)
    if not reasons and positions != EXPECTED_POSITIONS:
        reasons.add("missing_witness_position")
    if not reasons:
        reasons.update((
            "witness_anchor_origin_and_delegation_not_authenticated",
            "claimed_principals_not_independently_verified",
        ))
        status: Literal["cryptographic_witness_candidate", "abstain", "refused"] = (
            "cryptographic_witness_candidate"
        )
    elif reasons <= {"missing_witness_position",
                     "structural_preflight_underdetermined"}:
        # D5: provenance signatures cannot prove subject/property equivalence.
        status = "abstain"
    else:
        status = "refused"
    return WitnessQualification(
        status=status,
        reason_codes=tuple(sorted(reasons)),
        signature_matches=signatures,
        pin_matches=pins,
        required_positions=MAX_WITNESSES,
        observed_positions=len(positions),
        preflight_status=base.status,
        preflight_reason_codes=base.reasons,
    )
