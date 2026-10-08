"""#757: evaluation-only necessary-condition probe for cross-write identity links.

This code **never establishes semantic equivalence**, authenticated issuance,
currentness, recall eligibility, or permission to replace a memory. It does not
import a runtime, create a persistent relation, score benchmarks or inspect text
phrases. Its inputs are untrusted *descriptive assertions*, including any
claimed verification or external evidence references.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MAX_EVIDENCE = 8
MAX_TEXT = 256
_RETAINED = {"active", "disputed", "retracted", "tombstoned"}
_CARDINALITY = {"single", "multi", "unknown"}
_EVIDENCE_KIND = {"extractor_claim", "caller_claim", "schema_claim", "signature_claim"}
Status = Literal["refused", "underdetermined", "structurally_plausible_unverified"]


def _id(value: str, name: str) -> None:
    if type(value) is not str or not value or len(value) > MAX_TEXT or value != value.strip():
        raise ValueError(f"{name}: expected nonempty trimmed string of <= {MAX_TEXT} chars")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f"{name}: control characters not allowed")


@dataclass(frozen=True)
class ObservedWrite:
    """Claimed descriptors. No trust/authoritative status follows from fields."""

    fact_ref: str
    revision_ref: str
    tenant_ref: str
    scope_ref: str
    purpose_ref: str
    actor_ref: str
    source_ref: str
    subject_ref: str
    property_ref: str
    value_ref: str
    cardinality: Literal["single", "multi", "unknown"] = "unknown"
    lifecycle_state: Literal["active", "disputed", "retracted", "tombstoned"] = "active"
    coexistent: bool = False

    def __post_init__(self) -> None:
        for name in (
            "fact_ref", "revision_ref", "tenant_ref", "scope_ref", "purpose_ref",
            "actor_ref", "source_ref", "subject_ref", "property_ref", "value_ref",
        ):
            _id(getattr(self, name), name)
        if self.cardinality not in _CARDINALITY:
            raise ValueError("invalid cardinality")
        if self.lifecycle_state not in _RETAINED:
            raise ValueError("invalid lifecycle state")
        if type(self.coexistent) is not bool:
            raise ValueError("coexistent must be bool")


@dataclass(frozen=True)
class ClaimOfIdentity:
    """An assertion about identity evidence, NOT independently verified proof."""

    evidence_ref: str
    origin_invocation_ref: str
    origin_source_ref: str
    claimed_kind: Literal[
        "extractor_claim", "caller_claim", "schema_claim", "signature_claim"
    ]

    def __post_init__(self) -> None:
        for name in ("evidence_ref", "origin_invocation_ref", "origin_source_ref"):
            _id(getattr(self, name), name)
        if self.claimed_kind not in _EVIDENCE_KIND:
            raise ValueError("unrecognized identity evidence kind")


@dataclass(frozen=True)
class ProposedIdentityLink:
    """Explicit prior/current head assertions do not constitute live CAS."""

    older: ObservedWrite
    newer: ObservedWrite
    expected_head_ref: str
    observed_head_ref: str
    claims: tuple[ClaimOfIdentity, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.older, ObservedWrite) or not isinstance(self.newer, ObservedWrite):
            raise TypeError("older/newer must be ObservedWrite")
        _id(self.expected_head_ref, "expected_head_ref")
        _id(self.observed_head_ref, "observed_head_ref")
        if type(self.claims) is not tuple or len(self.claims) > MAX_EVIDENCE:
            raise ValueError(f"claims must be a tuple of at most {MAX_EVIDENCE} items")
        if not all(isinstance(x, ClaimOfIdentity) for x in self.claims):
            raise TypeError("claims must be typed claims")


@dataclass(frozen=True)
class IdentityPreflight:
    """Diagnostic only, with no positive semantic verdict."""

    status: Status
    reasons: tuple[str, ...]
    claimed_evidence_refs: tuple[str, ...]
    authority_effect: Literal["none"] = "none"
    identity_verified: Literal[False] = False
    can_supersede: Literal[False] = False
    mutates_memory: Literal[False] = False
    canonical_identity_ref: None = None
    integration_state: Literal["evaluation_only"] = "evaluation_only"


def preflight(proposal: ProposedIdentityLink) -> IdentityPreflight:
    """Check necessary structural conditions for a proposed exclusive update.

    'Structurally plausible' never means 'same property'; it signals that
    no configured structural falsifier fired and that an *independent* trusted
    semantic/evidence verification contract is still required.
    """
    if not isinstance(proposal, ProposedIdentityLink):
        raise TypeError("proposal must be ProposedIdentityLink")
    a, b = proposal.older, proposal.newer
    refusals: set[str] = set()
    unknowns: set[str] = set()

    for field in ("tenant_ref", "scope_ref", "purpose_ref"):
        if getattr(a, field) != getattr(b, field):
            refusals.add(f"{field}_incompatible")

    if a.fact_ref == b.fact_ref or a.revision_ref == b.revision_ref:
        refusals.add("not_two_independent_fact_revisions")
    if proposal.expected_head_ref != proposal.observed_head_ref:
        refusals.add("stale_claimed_head")
    if a.lifecycle_state != "active" or b.lifecycle_state != "active":
        refusals.add("inactive_or_disputed_revision")
    if a.cardinality != "single" or b.cardinality != "single" or a.coexistent or b.coexistent:
        refusals.add("exclusive_update_not_licensed_by_cardinality")
    if a.value_ref == b.value_ref:
        refusals.add("identical_value_is_not_a_state_change")

    if a.actor_ref != b.actor_ref or a.source_ref != b.source_ref:
        unknowns.add("cross_origin_requires_scope_and_issuer_verification")
    if a.subject_ref != b.subject_ref:
        unknowns.add("subject_identity_requires_independent_proof")
    if a.property_ref != b.property_ref:
        unknowns.add("property_identity_requires_independent_crosswalk")

    if not proposal.claims:
        unknowns.add("no_identity_evidence_claimed")
    else:
        # These are claimed origins, NOT verifier-established independent sources.
        # One extractor invocation can produce arbitrarily many apparent claims.
        origins = {(c.origin_invocation_ref, c.origin_source_ref) for c in proposal.claims}
        if len(origins) < 2:
            unknowns.add("identity_evidence_has_single_claimed_origin")
        if len({c.evidence_ref for c in proposal.claims}) != len(proposal.claims):
            unknowns.add("identity_evidence_refs_reused")
        unknowns.add("claimed_issuers_and_receipts_not_independently_verified")

    # No true semantic equivalence verdict is possible here even if every
    # syntactic precondition is met. This evaluator NEVER consults trust roots.
    if refusals:
        status: Status = "refused"
        reasons = refusals | unknowns
    elif unknowns - {"claimed_issuers_and_receipts_not_independently_verified"}:
        status = "underdetermined"
        reasons = unknowns
    else:
        status = "structurally_plausible_unverified"
        reasons = unknowns
    return IdentityPreflight(
        status=status,
        reasons=tuple(sorted(reasons)),
        claimed_evidence_refs=tuple(sorted({c.evidence_ref for c in proposal.claims})),
    )
