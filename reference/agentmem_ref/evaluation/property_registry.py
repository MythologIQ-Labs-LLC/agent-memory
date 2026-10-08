"""#757: Schema-declared cross-write property candidate, NOT verified semantic truth.

This eval-only mechanism can recognize explicit property-label crosswalks from
a *separately pinned*, signed, versioned registry. Signatures prove only key
possession; the caller's pins and schema ownership are NOT authenticated here.
There is no inferred synonym mapping, memory mutation, recall or approval.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
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
from .proposition_link_preflight import ProposedIdentityLink, preflight

PROFILE = "agent-memory/property-registry-qualification"
VERSION = "1.0.0"
ALGORITHM = "Ed25519"
MAX_PROPERTIES = 32
MAX_ALIASES = 12
MAX_SIGNATURE_B64 = 128
_ALLOWED_STATES = frozenset({"active", "disputed", "retired", "revoked"})


class RegistryError(ValueError):
    """Invalid bounded registry or signature shape."""


@dataclass(frozen=True)
class PropertyDefinition:
    property_ref: str
    label_refs: tuple[str, ...]
    state: Literal["active", "disputed", "retired", "revoked"] = "active"

    def __post_init__(self) -> None:
        _identifier(self.property_ref, "property_ref")
        if type(self.label_refs) is not tuple or not 1 <= len(self.label_refs) <= MAX_ALIASES:
            raise RegistryError("property labels must be a bounded tuple")
        for label in self.label_refs:
            _identifier(label, "label_ref")
        if tuple(sorted(set(self.label_refs))) != self.label_refs:
            raise RegistryError("property labels must be unique and canonically ordered")
        if self.state not in _ALLOWED_STATES:
            raise RegistryError("unrecognized property lifecycle state")


@dataclass(frozen=True)
class PropertyRegistry:
    schema_ref: str
    revision_ref: str
    tenant_ref: str
    scope_ref: str
    purpose_ref: str
    issuer_key_ref: str
    properties: tuple[PropertyDefinition, ...]

    def __post_init__(self) -> None:
        for name in (
            "schema_ref", "revision_ref", "tenant_ref", "scope_ref",
            "purpose_ref", "issuer_key_ref",
        ):
            _identifier(getattr(self, name), name)
        if type(self.properties) is not tuple or not 1 <= len(self.properties) <= MAX_PROPERTIES:
            raise RegistryError("properties must be a bounded tuple")
        if not all(type(p) is PropertyDefinition for p in self.properties):
            raise RegistryError("property definition type mismatch")
        if tuple(sorted(self.properties, key=lambda p: p.property_ref)) != self.properties:
            raise RegistryError("properties must have canonical ordering")
        prop_refs = [p.property_ref for p in self.properties]
        if len(prop_refs) != len(set(prop_refs)):
            raise RegistryError("duplicate canonical property reference")
        aliases = [alias for prop in self.properties for alias in prop.label_refs]
        if len(aliases) != len(set(aliases)):
            raise RegistryError("one label cannot identify multiple canonical properties")


@dataclass(frozen=True)
class SignedPropertyRegistry:
    profile: str
    version: str
    algorithm: str
    registry: PropertyRegistry
    signature_b64: str


@dataclass(frozen=True)
class PropertyLinkQualification:
    status: Literal["schema_candidate", "abstain", "refused"]
    reason_codes: tuple[str, ...]
    declared_property_ref: str | None
    signature_valid: bool
    key_pin_matches: bool
    pinned_context_matches: bool
    issuer_authorized: Literal[False] = False
    identity_verified: Literal[False] = False
    can_supersede: Literal[False] = False
    authority_effect: Literal["none"] = "none"
    mutates_memory: Literal[False] = False
    integration_state: Literal["evaluation_only"] = "evaluation_only"


def _transcript(registry: PropertyRegistry) -> bytes:
    if type(registry) is not PropertyRegistry:
        raise RegistryError("expected a typed registry")
    # Payload includes complete versioned ontology, scope, revisions and
    # issuer key ref. Domain-separated from temporal/journal attestations.
    return canonical_json({
        "profile": PROFILE,
        "version": VERSION,
        "algorithm": ALGORITHM,
        "registry": asdict(registry),
    })


def sign_registry(registry: PropertyRegistry, *,
                  private_key: Ed25519PrivateKey) -> SignedPropertyRegistry:
    if type(registry) is not PropertyRegistry:
        raise TypeError("registry must be PropertyRegistry")
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("private_key must be Ed25519PrivateKey")
    signature = private_key.sign(_transcript(registry))
    return SignedPropertyRegistry(PROFILE, VERSION, ALGORITHM, registry,
                                  base64.b64encode(signature).decode("ascii"))


def _verify(signed: SignedPropertyRegistry, *, public_key: Ed25519PublicKey,
            expected_public_key_digest: str, expected_issuer_key_ref: str,
            expected_schema_ref: str, expected_revision_ref: str,
            expected_tenant_ref: str, expected_scope_ref: str,
            expected_purpose_ref: str) -> tuple[bool, bool, bool, tuple[str, ...]]:
    if not isinstance(public_key, Ed25519PublicKey):
        raise TypeError("public_key must be Ed25519PublicKey")
    _digest(expected_public_key_digest, "expected_public_key_digest")
    expectations = {
        "issuer_key_ref": expected_issuer_key_ref,
        "schema_ref": expected_schema_ref,
        "revision_ref": expected_revision_ref,
        "tenant_ref": expected_tenant_ref,
        "scope_ref": expected_scope_ref,
        "purpose_ref": expected_purpose_ref,
    }
    for name, value in expectations.items():
        _identifier(value, name)
    pin_ok = public_key_digest(public_key) == expected_public_key_digest
    reasons: set[str] = set()
    if not pin_ok:
        reasons.add("independent_key_pin_mismatch")

    sig_ok = False
    ctx_ok = False
    if type(signed) is not SignedPropertyRegistry:
        reasons.add("invalid_signed_registry_shape")
    else:
        reg = signed.registry
        if type(reg) is PropertyRegistry:
            ctx_ok = all(getattr(reg, key) == value
                         for key, value in expectations.items())
        if not ctx_ok:
            reasons.add("independent_schema_context_mismatch")
        try:
            if (signed.profile != PROFILE or signed.version != VERSION
                    or signed.algorithm != ALGORITHM or type(reg) is not PropertyRegistry
                    or type(signed.signature_b64) is not str
                    or len(signed.signature_b64) > MAX_SIGNATURE_B64):
                raise RegistryError("unsupported signature contract")
            # Revalidate the manifest to defend against post-construction
            # dataclass/mutable subclass tampering.
            rebuilt = tuple(PropertyDefinition(item.property_ref, item.label_refs, item.state)
                            for item in reg.properties)
            PropertyRegistry(
                schema_ref=reg.schema_ref, revision_ref=reg.revision_ref,
                tenant_ref=reg.tenant_ref, scope_ref=reg.scope_ref,
                purpose_ref=reg.purpose_ref, issuer_key_ref=reg.issuer_key_ref,
                properties=rebuilt,
            )
            raw = base64.b64decode(signed.signature_b64, validate=True)
            if len(raw) != 64 or base64.b64encode(raw).decode("ascii") != signed.signature_b64:
                raise RegistryError("invalid or noncanonical signature")
            public_key.verify(raw, _transcript(reg))
            sig_ok = True
        except (RegistryError, ValueError, TypeError, InvalidSignature, binascii.Error):
            reasons.add("signature_invalid_or_registry_malformed")
    return sig_ok, pin_ok, ctx_ok, tuple(sorted(reasons))


def qualify_property_link(
    proposal: ProposedIdentityLink,
    signed_registry: SignedPropertyRegistry,
    *,
    public_key: Ed25519PublicKey,
    pinned_public_key_digest: str,
    expected_issuer_key_ref: str,
    expected_schema_ref: str,
    expected_revision_ref: str,
    expected_tenant_ref: str,
    expected_scope_ref: str,
    expected_purpose_ref: str,
) -> PropertyLinkQualification:
    """Candidate only for an exact, active, schema-declared shared property.

    This cannot authenticate the registry publisher or establish semantic
    truth. It cannot promote an alias into authoritative lifecycle state.
    """
    verdict = preflight(proposal)
    sig_ok, pin_ok, ctx_ok, trust_reasons = _verify(
        signed_registry, public_key=public_key,
        expected_public_key_digest=pinned_public_key_digest,
        expected_issuer_key_ref=expected_issuer_key_ref,
        expected_schema_ref=expected_schema_ref,
        expected_revision_ref=expected_revision_ref,
        expected_tenant_ref=expected_tenant_ref,
        expected_scope_ref=expected_scope_ref,
        expected_purpose_ref=expected_purpose_ref,
    )
    problems = set(trust_reasons)
    if verdict.status == "refused":
        problems.add("structural_preflight_refused")
    a, b = proposal.older, proposal.newer
    if a.subject_ref != b.subject_ref:
        problems.add("subject_identity_not_proven")
    if (a.tenant_ref != expected_tenant_ref or b.tenant_ref != expected_tenant_ref
            or a.scope_ref != expected_scope_ref or b.scope_ref != expected_scope_ref
            or a.purpose_ref != expected_purpose_ref or b.purpose_ref != expected_purpose_ref):
        problems.add("proposal_outside_registry_scope")
    if problems:
        return PropertyLinkQualification("refused", tuple(sorted(problems)), None,
                                         sig_ok, pin_ok, ctx_ok)

    mapping: dict[str, tuple[str, str]] = {
        label: (item.property_ref, item.state)
        for item in signed_registry.registry.properties
        for label in item.label_refs
    }
    left = mapping.get(a.property_ref)
    right = mapping.get(b.property_ref)
    if left is None or right is None:
        problems.add("schema_label_unmapped")
    elif left[1] != "active" or right[1] != "active":
        problems.add("property_not_active")
    elif left[0] != right[0]:
        problems.add("schema_declares_different_properties")
    if problems:
        return PropertyLinkQualification("abstain", tuple(sorted(problems)), None,
                                         sig_ok, pin_ok, ctx_ok)
    # Schema mapping is an independently authored declaration relative to
    # extractor text, but its real-world truth, publisher authority and
    # source/actor provenance remain UNVERIFIED.
    problems.add("registry_issuer_authority_not_established")
    if a.actor_ref != b.actor_ref or a.source_ref != b.source_ref:
        problems.add("cross_origin_provenance_not_established")
    return PropertyLinkQualification(
        "schema_candidate", tuple(sorted(problems)), left[0],
        sig_ok, pin_ok, ctx_ok,
    )
