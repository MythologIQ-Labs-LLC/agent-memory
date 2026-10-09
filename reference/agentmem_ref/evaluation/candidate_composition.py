"""#757 C01-C14: one checkpoint for proposal, registry, issuer and witnesses.

This composes *evaluation-only* mechanical observations. It cannot establish
real-world source authority, semantic identity, currentness or memory mutation.
The external expected head is caller-supplied and may be attacker-controlled.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ..memory.temporal_commitment import canonical_json
from ..memory.temporal_trust import public_key_digest
from .candidate_trust_state import CandidateTrustState, TrustCheckpoint
from .issuer_policy import qualify_issuer_policy
from .property_registry import PropertyRegistry, SignedPropertyRegistry
from .proposition_link_preflight import (
    ClaimOfIdentity, ObservedWrite, ProposedIdentityLink, preflight,
)
from .source_actor_witnesses import WitnessInput, qualify_write_origins

RECEIPT_DOMAIN = b"am-revocable-link-candidate-v1\x00"
MAX_RECEIPT_TRANSCRIPT = 262144


@dataclass(frozen=True)
class CompositeCandidate:
    status: Literal["mechanical_candidate", "abstain", "refused"]
    reason_codes: tuple[str, ...]
    trust_checkpoint: TrustCheckpoint
    structural_status: str
    structural_reasons: tuple[str, ...]
    registry_status: str
    policy_status: str
    witness_status: str
    proposal_digest: str | None
    evidence_digest: str | None
    dependency_key_digests: tuple[str, ...]
    record_digest: str
    issuer_authorized: Literal[False] = False
    principal_authenticated: Literal[False] = False
    origin_independence_verified: Literal[False] = False
    identity_verified: Literal[False] = False
    can_supersede: Literal[False] = False
    authority_effect: Literal["none"] = "none"
    mutates_memory: Literal[False] = False
    currentness: Literal["not_established"] = "not_established"
    integration_state: Literal["evaluation_only"] = "evaluation_only"


@dataclass(frozen=True)
class CandidateFreshness:
    status: Literal["same_local_checkpoint", "stale_receipt"]
    reason_codes: tuple[str, ...]
    authority_effect: Literal["none"] = "none"
    currentness: Literal["not_established"] = "not_established"
    can_supersede: Literal[False] = False
    mutates_memory: Literal[False] = False


def _digest(label: bytes, payload: object) -> str:
    blob = canonical_json(payload)
    if len(blob) > MAX_RECEIPT_TRANSCRIPT:
        raise ValueError("candidate evidence exceeds transcript bound")
    return "sha256:" + sha256(label + blob).hexdigest()


def _canonical_evidence(
    proposal: ProposedIdentityLink, signed_registry: SignedPropertyRegistry,
    public_key: Ed25519PublicKey, witnesses: tuple[WitnessInput, ...],
) -> tuple[str, str, tuple[str, ...]]:
    if (type(proposal) is not ProposedIdentityLink
            or type(proposal.older) is not ObservedWrite
            or type(proposal.newer) is not ObservedWrite
            or type(proposal.claims) is not tuple
            or not all(type(c) is ClaimOfIdentity for c in proposal.claims)):
        raise ValueError("noncanonical exact proposal")
    if (type(signed_registry) is not SignedPropertyRegistry
            or type(witnesses) is not tuple
            or not isinstance(public_key, Ed25519PublicKey)):
        raise ValueError("noncanonical evidence envelope")
    p = _digest(b"am-composite-proposal-v1\x00", asdict(proposal))
    witness_rows = []
    key_digests = [public_key_digest(public_key)]
    for item in witnesses:
        if (type(item) is not WitnessInput
                or not isinstance(item.public_key, Ed25519PublicKey)):
            raise ValueError("malformed witness input envelope")
        key = public_key_digest(item.public_key)
        key_digests.append(key)
        witness_rows.append({
            "witness": asdict(item.signed),
            "expectation": asdict(item.expected),
            "public_key_digest": key,
        })
    # Witness order cannot change evidence identity. Duplicate positions are
    # still rejected by the lower witness evaluator.
    witness_rows.sort(key=lambda x: canonical_json(x))
    evidence = _digest(b"am-composite-evidence-v1\x00", {
        "signed_registry": asdict(signed_registry),
        "public_key_digest": key_digests[0],
        "witnesses": witness_rows,
    })
    return p, evidence, tuple(sorted(set(key_digests)))


def qualify_candidate_at_trust_state(
    trust_state: CandidateTrustState,
    proposal: ProposedIdentityLink,
    signed_registry: SignedPropertyRegistry,
    *,
    registry_public_key: Ed25519PublicKey,
    witnesses: tuple[WitnessInput, ...],
    expected_current_head: str,
    expected_sequence: int,
) -> CompositeCandidate:
    """Qualify a read-only *mechanical* candidate against one local view.

    A caller able to forge this state and the expected head can manufacture a
    mechanical match. External authority and reliable freshness are UNSOLVED.
    """
    if type(trust_state) is not CandidateTrustState:
        raise TypeError("trust_state must be exact CandidateTrustState")
    view = trust_state.view()
    checkpoint = view.checkpoint
    reasons: set[str] = {"current_anchor_authentication_not_established"}
    structural_status = "not_evaluated"
    structural_reasons: tuple[str, ...] = ()
    registry_status = "not_evaluated"
    policy_status = "not_evaluated"
    witness_status = "not_evaluated"
    proposal_hash = None
    evidence_hash = None
    dependencies: tuple[str, ...] = ()
    denied = False
    incomplete = False

    if type(expected_current_head) is not str or type(expected_sequence) is not int:
        reasons.add("invalid_expected_checkpoint")
    elif (expected_current_head != checkpoint.current_head
          or expected_sequence != checkpoint.sequence):
        reasons.add("expected_current_trust_checkpoint_mismatch")

    try:
        proposal_hash, evidence_hash, dependencies = _canonical_evidence(
            proposal, signed_registry, registry_public_key, witnesses,
        )
        baseline = preflight(proposal)
        structural_status = baseline.status
        structural_reasons = baseline.reasons
        reasons.update("preflight:" + reason for reason in baseline.reasons)
        if baseline.status == "refused":
            reasons.add("structural_preflight_refused")
        elif baseline.status == "underdetermined":
            reasons.add("structural_preflight_underdetermined")
            incomplete = True

        reg = signed_registry.registry
        if type(reg) is not PropertyRegistry:
            raise ValueError("noncanonical signed registry content")
        tenant = proposal.older.tenant_ref
        if any((tenant, key) in view.denied_keys for key in dependencies):
            reasons.add("signing_key_revoked_at_checkpoint")
            denied = True
        if (tenant, reg.schema_ref, reg.revision_ref) in view.denied_schema_revisions:
            reasons.add("schema_revision_invalidated_at_checkpoint")
            denied = True

        policy = qualify_issuer_policy(
            proposal, signed_registry, public_key=registry_public_key,
            snapshot=view.policy_snapshot,
            expected_policy_digest=checkpoint.policy_digest,
            expected_policy_ref=view.policy_snapshot.policy_ref,
            expected_policy_revision_ref=view.policy_snapshot.revision_ref,
            expected_issuer_key_ref=reg.issuer_key_ref,
            expected_schema_ref=reg.schema_ref,
            expected_revision_ref=reg.revision_ref,
            expected_tenant_ref=proposal.older.tenant_ref,
            expected_scope_ref=proposal.older.scope_ref,
            expected_purpose_ref=proposal.older.purpose_ref,
        )
        policy_status = policy.status
        registry_status = policy.registry_status
        reasons.update("policy:" + r for r in policy.reason_codes)
        if policy.status == "abstain":
            incomplete = True
        if "schema_declares_different_properties" in policy.reason_codes:
            reasons.add("explicit_distinct_property_refusal")
            denied = True

        witness = qualify_write_origins(proposal, witnesses)
        witness_status = witness.status
        reasons.update("witness:" + r for r in witness.reason_codes)
        reasons.update("preflight:" + r for r in witness.preflight_reason_codes)
        if witness.status == "abstain":
            incomplete = True
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError) as exc:
        # Inputs that cannot be canonicalized or validated cannot qualify.
        reasons.add("malformed_or_unverifiable_composition_input")
        reasons.add("composition_exception:" + type(exc).__name__)
        denied = True

    if trust_state.view().checkpoint.current_head != checkpoint.current_head:
        reasons.add("trust_state_advanced_during_qualification")
        denied = True

    if (denied or "expected_current_trust_checkpoint_mismatch" in reasons
            or "invalid_expected_checkpoint" in reasons
            or structural_status == "refused"
            or registry_status == "refused"
            or policy_status == "refused"
            or witness_status == "refused"
            or "explicit_distinct_property_refusal" in reasons):
        status: Literal["mechanical_candidate", "abstain", "refused"] = "refused"
    elif (incomplete or structural_status != "structurally_plausible_unverified"
          or registry_status != "schema_candidate"
          or policy_status != "policy_matched_candidate"
          or witness_status != "cryptographic_witness_candidate"):
        status = "abstain"
    else:
        status = "mechanical_candidate"

    stable_reasons = tuple(sorted(reasons))
    receipt_content = {
        "status": status, "reasons": stable_reasons,
        "checkpoint": asdict(checkpoint), "structural_status": structural_status,
        "structural_reasons": structural_reasons,
        "registry_status": registry_status, "policy_status": policy_status,
        "witness_status": witness_status, "proposal_digest": proposal_hash,
        "evidence_digest": evidence_hash, "dependency_key_digests": dependencies,
    }
    record_digest = _digest(RECEIPT_DOMAIN, receipt_content)
    return CompositeCandidate(
        status=status, reason_codes=stable_reasons,
        trust_checkpoint=checkpoint, structural_status=structural_status,
        structural_reasons=structural_reasons, registry_status=registry_status,
        policy_status=policy_status, witness_status=witness_status,
        proposal_digest=proposal_hash, evidence_digest=evidence_hash,
        dependency_key_digests=dependencies, record_digest=record_digest,
    )


def recheck_candidate_head(
    candidate: CompositeCandidate, trust_state: CandidateTrustState,
    *, expected_current_head: str,
) -> CandidateFreshness:
    """A same-head result is NOT an authorization or independent requalification."""
    if type(candidate) is not CompositeCandidate or type(trust_state) is not CandidateTrustState:
        raise TypeError("typed candidate and trust state required")
    current = trust_state.view().checkpoint
    if (current.current_head == expected_current_head
            and current == candidate.trust_checkpoint):
        return CandidateFreshness(
            "same_local_checkpoint", ("local_head_unchanged_but_not_authenticated",),
        )
    return CandidateFreshness("stale_receipt", ("candidate_checkpoint_no_longer_current",))
