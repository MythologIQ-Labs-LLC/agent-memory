"""#757 J42-J56: independently pinned issuer policy, evaluation-only.

A digest-matching *caller supplied* policy does NOT authenticate its origin.
This module never grants issuer/semantic/lifecycle authority and cannot apply
a cross-write identity relation. Revocation has deny precedence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ..memory.temporal_commitment import canonical_json
from ..memory.temporal_trust import public_key_digest
from .identity_link_journal import _digest, _identifier
from .property_registry import (
    PropertyLinkQualification, SignedPropertyRegistry, qualify_property_link,
)
from .proposition_link_preflight import ProposedIdentityLink

POLICY_PROFILE = "agent-memory/issuer-policy-qualification"
POLICY_VERSION = "0.1.0"
POLICY_DOMAIN = b"am-evaluation-issuer-policy-v1\x00"
MAX_GRANTS = 32
MAX_REVOKED = 32
MAX_BYTES = 16384
_GRANT_STATES = frozenset({"active", "revoked"})


class IssuerPolicyError(ValueError):
    """Refusal of an invalid policy snapshot or trust pin."""


@dataclass(frozen=True)
class IssuerGrant:
    schema_ref: str
    registry_revision_ref: str
    tenant_ref: str
    scope_ref: str
    purpose_ref: str
    issuer_key_ref: str
    public_key_digest: str
    state: Literal["active", "revoked"] = "active"

    def __post_init__(self) -> None:
        for field in (
            "schema_ref", "registry_revision_ref", "tenant_ref", "scope_ref",
            "purpose_ref", "issuer_key_ref",
        ):
            _identifier(getattr(self, field), field)
        _digest(self.public_key_digest, "public_key_digest")
        if type(self.state) is not str or self.state not in _GRANT_STATES:
            raise IssuerPolicyError("unknown grant state")

    @property
    def scope_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.schema_ref, self.registry_revision_ref,
            self.tenant_ref, self.scope_ref, self.purpose_ref,
        )


@dataclass(frozen=True)
class IssuerPolicySnapshot:
    policy_ref: str
    revision_ref: str
    grants: tuple[IssuerGrant, ...]
    revoked_key_digests: tuple[str, ...] = ()
    invalidated_registry_revisions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.policy_ref, "policy_ref")
        _identifier(self.revision_ref, "policy_revision_ref")
        if (type(self.grants) is not tuple or len(self.grants) > MAX_GRANTS
                or not all(type(x) is IssuerGrant for x in self.grants)):
            raise IssuerPolicyError("grants must be a bounded tuple of exact IssuerGrant")
        if tuple(sorted(self.grants, key=lambda x: x.scope_key)) != self.grants:
            raise IssuerPolicyError("grants must be sorted by exact scope")
        keys = tuple(x.scope_key for x in self.grants)
        if len(keys) != len(set(keys)):
            raise IssuerPolicyError("multiple issuers for one exact grant scope")
        if (type(self.revoked_key_digests) is not tuple
                or len(self.revoked_key_digests) > MAX_REVOKED):
            raise IssuerPolicyError("revoked keys must be a bounded tuple")
        for item in self.revoked_key_digests:
            _digest(item, "revoked_key_digest")
        if tuple(sorted(set(self.revoked_key_digests))) != self.revoked_key_digests:
            raise IssuerPolicyError("revoked key digests must be unique and sorted")
        if (type(self.invalidated_registry_revisions) is not tuple
                or len(self.invalidated_registry_revisions) > MAX_REVOKED):
            raise IssuerPolicyError("invalidated revisions must be a bounded tuple")
        for pair in self.invalidated_registry_revisions:
            if type(pair) is not tuple or len(pair) != 2:
                raise IssuerPolicyError("invalidated revision must be an exact pair")
            _identifier(pair[0], "invalidated_schema_ref")
            _identifier(pair[1], "invalidated_revision_ref")
        if (tuple(sorted(set(self.invalidated_registry_revisions)))
                != self.invalidated_registry_revisions):
            raise IssuerPolicyError("invalidated revision pairs must be unique and sorted")
        if len(_canonical_policy_payload(self)) > MAX_BYTES:
            raise IssuerPolicyError("policy exceeds canonical size bound")


@dataclass(frozen=True)
class IssuerPolicyQualification:
    status: Literal["policy_matched_candidate", "abstain", "refused"]
    reason_codes: tuple[str, ...]
    declared_property_ref: str | None
    registry_status: Literal["schema_candidate", "abstain", "refused"]
    policy_pin_matches: bool
    policy_context_matches: bool
    grant_matched: bool
    issuer_authorized: Literal[False] = False
    identity_verified: Literal[False] = False
    can_supersede: Literal[False] = False
    authority_effect: Literal["none"] = "none"
    mutates_memory: Literal[False] = False
    integration_state: Literal["evaluation_only"] = "evaluation_only"


def _canonical_policy_payload(snapshot: IssuerPolicySnapshot) -> bytes:
    """Exact bounded policy transcript. Shared by construction and hashing."""
    return canonical_json({
        "profile": POLICY_PROFILE,
        "version": POLICY_VERSION,
        "policy": {
            "policy_ref": snapshot.policy_ref,
            "revision_ref": snapshot.revision_ref,
            "grants": [asdict(item) for item in snapshot.grants],
            "revoked_key_digests": list(snapshot.revoked_key_digests),
            "invalidated_registry_revisions": [
                list(pair) for pair in snapshot.invalidated_registry_revisions
            ],
        },
    })


def policy_digest(snapshot: IssuerPolicySnapshot) -> str:
    """Canonical digest for comparison to an OUT-OF-BAND pin (not authentication)."""
    if type(snapshot) is not IssuerPolicySnapshot:
        raise TypeError("snapshot must be IssuerPolicySnapshot")
    # Revalidation defends against mutated dataclasses from unsafe callers.
    rebuilt = IssuerPolicySnapshot(
        policy_ref=snapshot.policy_ref,
        revision_ref=snapshot.revision_ref,
        grants=tuple(IssuerGrant(**asdict(x)) for x in snapshot.grants),
        revoked_key_digests=snapshot.revoked_key_digests,
        invalidated_registry_revisions=snapshot.invalidated_registry_revisions,
    )
    payload = _canonical_policy_payload(rebuilt)
    return "sha256:" + sha256(POLICY_DOMAIN + payload).hexdigest()


def qualify_issuer_policy(
    proposal: ProposedIdentityLink,
    signed_registry: SignedPropertyRegistry,
    *,
    public_key: Ed25519PublicKey,
    snapshot: IssuerPolicySnapshot,
    expected_policy_digest: str,
    expected_policy_ref: str,
    expected_policy_revision_ref: str,
    expected_issuer_key_ref: str,
    expected_schema_ref: str,
    expected_revision_ref: str,
    expected_tenant_ref: str,
    expected_scope_ref: str,
    expected_purpose_ref: str,
) -> IssuerPolicyQualification:
    """Validate an exact policy grant for an already-safe schema candidate.

    All pins and the policy are supplied by the caller. Even a full positive
    mechanical match is NOT evidence of legitimate trust-root distribution,
    currentness, original source/actor authority or real property equivalence.
    """
    if not isinstance(public_key, Ed25519PublicKey):
        raise TypeError("public_key must be Ed25519PublicKey")
    _digest(expected_policy_digest, "expected_policy_digest")
    _identifier(expected_policy_ref, "expected_policy_ref")
    _identifier(expected_policy_revision_ref, "expected_policy_revision_ref")
    if type(snapshot) is not IssuerPolicySnapshot:
        raise TypeError("snapshot must be IssuerPolicySnapshot")
    # Always preserve the existing independent structural/registry gates.
    registry: PropertyLinkQualification = qualify_property_link(
        proposal, signed_registry,
        public_key=public_key,
        pinned_public_key_digest=public_key_digest(public_key),
        expected_issuer_key_ref=expected_issuer_key_ref,
        expected_schema_ref=expected_schema_ref,
        expected_revision_ref=expected_revision_ref,
        expected_tenant_ref=expected_tenant_ref,
        expected_scope_ref=expected_scope_ref,
        expected_purpose_ref=expected_purpose_ref,
    )
    actual_digest = policy_digest(snapshot)
    pin_ok = actual_digest == expected_policy_digest
    ctx_ok = (snapshot.policy_ref == expected_policy_ref
              and snapshot.revision_ref == expected_policy_revision_ref)
    reasons = set(registry.reason_codes)
    if not pin_ok:
        reasons.add("independent_policy_digest_mismatch")
    if not ctx_ok:
        reasons.add("independent_policy_context_mismatch")
    if registry.status == "refused":
        reasons.add("registry_or_structural_refusal")
    def result(status: Literal["policy_matched_candidate", "abstain", "refused"],
               matched: bool = False) -> IssuerPolicyQualification:
        return IssuerPolicyQualification(
            status=status, reason_codes=tuple(sorted(reasons)),
            declared_property_ref=(
                registry.declared_property_ref if status == "policy_matched_candidate"
                else None
            ),
            registry_status=registry.status,
            policy_pin_matches=pin_ok,
            policy_context_matches=ctx_ok,
            grant_matched=matched,
        )

    # D1: negative authority evidence must be evaluated BEFORE any
    # lower-layer abstention, so explicit denial can never be downgraded.
    actual_key_digest = public_key_digest(public_key)
    revision_pair = (expected_schema_ref, expected_revision_ref)
    if actual_key_digest in snapshot.revoked_key_digests:
        reasons.add("issuer_key_revoked")
    if revision_pair in snapshot.invalidated_registry_revisions:
        reasons.add("registry_revision_invalidated")
    if (not pin_ok or not ctx_ok or registry.status == "refused"
            or "issuer_key_revoked" in reasons
            or "registry_revision_invalidated" in reasons):
        return result("refused")
    if registry.status == "abstain":
        reasons.add("schema_candidate_not_established")
        return result("abstain")

    key = (
        expected_schema_ref, expected_revision_ref, expected_tenant_ref,
        expected_scope_ref, expected_purpose_ref,
    )
    grant = next((x for x in snapshot.grants if x.scope_key == key), None)
    if grant is None:
        reasons.add("no_exact_issuer_grant")
        return result("abstain")
    matched = (
        grant.issuer_key_ref == expected_issuer_key_ref
        and grant.public_key_digest == actual_key_digest
    )
    if not matched:
        reasons.add("grant_key_or_issuer_mismatch")
        return result("refused")
    if grant.state != "active":
        reasons.add("issuer_grant_revoked")
        return result("refused", True)

    reasons.add("policy_distribution_and_issuer_legitimacy_not_authenticated")
    return result("policy_matched_candidate", True)
