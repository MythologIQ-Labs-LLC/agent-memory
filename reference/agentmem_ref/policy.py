"""PAMA authority evaluation.

A reference projection of the operation/risk decision data in
`docs/33-pama-decision-table.md`, layered over the foundational target-class
and downstream-authority floors in `docs/pama/README.md`.

The evaluation is deterministic: for a fixed proposal and policy version it
returns the same authority envelope. Estimator confidence is an *input to
evidence quality only* and has no path to the outcome, which is the property
the negative-path tests exist to hold in place.

Enumerated values mirror `schemas/pama-decision.schema.json` exactly.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

POLICY_VERSION = "ref-p1"

# Outcomes, ordered by strictness.
ALLOW = "allow"
ALLOW_WITH_LEDGER = "allow_with_ledger"
REQUIRE_REVIEW = "require_review"
REQUIRE_EXTERNAL_VERIFICATION = "require_external_verification"
BLOCK = "block"

_STRICTNESS = {
    ALLOW: 0,
    ALLOW_WITH_LEDGER: 1,
    REQUIRE_REVIEW: 2,
    REQUIRE_EXTERNAL_VERIFICATION: 3,
    BLOCK: 4,
}

M0 = "M0_EXECUTION_LOCAL_CONTEXT"
M1 = "M1_LOW_RISK_PERSONAL_PREFERENCE"
M2 = "M2_OPERATIONAL_ASSOCIATION"
M3 = "M3_REUSABLE_PROCEDURE_OR_CAPABILITY"
M4 = "M4_SHARED_OR_IDENTITY_BEARING_STATE"
M5 = "M5_GOVERNANCE_SECURITY_OR_AUTONOMOUS_AUTHORITY"

A0 = "A0_RETRIEVAL_ONLY"
A1 = "A1_RECOMMENDATION_INFLUENCE"
A2 = "A2_DRAFT_GENERATION"
A3 = "A3_LOCAL_WORKFLOW_MUTATION"
A4 = "A4_EXTERNAL_ACTION"
A5 = "A5_GOVERNANCE_CHANGE"

# Base cells from the decision table, for the operations this reference exercises.
_BASE_TABLE: dict[tuple[str, str], str] = {
    ("runtime_assembly", "low"): ALLOW_WITH_LEDGER,
    ("runtime_assembly", "medium"): ALLOW_WITH_LEDGER,
    ("runtime_assembly", "high"): REQUIRE_REVIEW,
    ("runtime_assembly", "critical"): REQUIRE_REVIEW,
    # GAP-ARCH-09: transcribed from docs/33-pama-decision-table.md:80-93.
    # Previously absent, so all twelve fell through _base_outcome's
    # REQUIRE_REVIEW default -- weaker than doctrine at
    # score_adjustment/critical (block) and link_deletion/critical
    # (require_external_verification), stricter than doctrine at five others.
    ("score_adjustment", "low"): ALLOW_WITH_LEDGER,
    ("score_adjustment", "medium"): ALLOW_WITH_LEDGER,
    ("score_adjustment", "high"): REQUIRE_REVIEW,
    ("score_adjustment", "critical"): BLOCK,
    ("link_creation", "low"): ALLOW_WITH_LEDGER,
    ("link_creation", "medium"): ALLOW_WITH_LEDGER,
    ("link_creation", "high"): REQUIRE_REVIEW,
    ("link_creation", "critical"): REQUIRE_REVIEW,
    ("link_deletion", "low"): ALLOW_WITH_LEDGER,
    ("link_deletion", "medium"): REQUIRE_REVIEW,
    ("link_deletion", "high"): REQUIRE_REVIEW,
    ("link_deletion", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
    ("correction", "low"): REQUIRE_REVIEW,
    ("correction", "medium"): REQUIRE_REVIEW,
    ("correction", "high"): REQUIRE_REVIEW,
    ("correction", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
    ("decision_overwrite", "low"): REQUIRE_REVIEW,
    ("decision_overwrite", "medium"): REQUIRE_REVIEW,
    ("decision_overwrite", "high"): REQUIRE_EXTERNAL_VERIFICATION,
    ("decision_overwrite", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
    ("domain_schema_mutation", "low"): REQUIRE_REVIEW,
    ("domain_schema_mutation", "medium"): REQUIRE_REVIEW,
    ("domain_schema_mutation", "high"): REQUIRE_EXTERNAL_VERIFICATION,
    ("domain_schema_mutation", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
    ("promotion", "low"): ALLOW_WITH_LEDGER,
    ("promotion", "medium"): REQUIRE_REVIEW,
    ("promotion", "high"): REQUIRE_REVIEW,
    ("promotion", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
    ("crystallization", "low"): REQUIRE_REVIEW,
    ("crystallization", "medium"): REQUIRE_REVIEW,
    ("crystallization", "high"): REQUIRE_EXTERNAL_VERIFICATION,
    ("crystallization", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
    ("pruning", "low"): ALLOW_WITH_LEDGER,
    ("pruning", "medium"): ALLOW_WITH_LEDGER,
    ("pruning", "high"): REQUIRE_REVIEW,
    ("pruning", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
    ("permanent_deletion", "low"): REQUIRE_REVIEW,
    ("permanent_deletion", "medium"): REQUIRE_REVIEW,
    ("permanent_deletion", "high"): REQUIRE_EXTERNAL_VERIFICATION,
    ("permanent_deletion", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
    ("scope_expansion", "low"): REQUIRE_REVIEW,
    ("scope_expansion", "medium"): REQUIRE_REVIEW,
    ("scope_expansion", "high"): REQUIRE_EXTERNAL_VERIFICATION,
    ("scope_expansion", "critical"): BLOCK,
    ("policy_mutation", "low"): REQUIRE_REVIEW,
    ("policy_mutation", "medium"): REQUIRE_EXTERNAL_VERIFICATION,
    ("policy_mutation", "high"): REQUIRE_EXTERNAL_VERIFICATION,
    ("policy_mutation", "critical"): REQUIRE_EXTERNAL_VERIFICATION,
}

# Foundational class floors. A base cell may never resolve weaker than these.
_TARGET_FLOOR = {M4: REQUIRE_REVIEW, M5: REQUIRE_REVIEW}
_AUTHORITY_FLOOR = {A4: REQUIRE_REVIEW, A5: REQUIRE_EXTERNAL_VERIFICATION}

_DEFERRALS = ("collect_more_evidence", "defer")


@dataclass(frozen=True)
class Proposal:
    """The adaptive mutation contract, reduced to what this reference needs."""

    proposal_id: str
    actor_id: str
    charter_version: str
    target_reference: str
    target_class: str
    scope: str
    operation: str
    current_strength: str
    proposed_strength: str
    downstream_authority: str
    reversibility: str
    risk_class: str
    evidence_refs: tuple[str, ...]
    estimator_refs: tuple[str, ...] = ()
    estimator_versions: tuple[str, ...] = ()
    confidence: float | None = None
    actor_authority_resolved: bool = True
    approves_own_authority: bool = False
    approval_refs: tuple[str, ...] = ()
    review_satisfied: bool = False
    requested_scope_change: str = ""
    state_snapshot: str = ""
    tenant_ref: str = ""
    purpose: str = ""
    isolation_domain_refs: tuple[str, ...] = ()
    required_isolation_domain_refs: tuple[str, ...] = ()
    project_ref: str = ""
    task_ref: str = ""


@dataclass(frozen=True)
class ExternalVerification:
    """Attestation that an external authority verified this specific proposal.

    GAP-ARCH-04. Deliberately NOT a `verified: bool` on Proposal -- that would be
    a fourth caller-asserted boolean, the pattern removed from
    `approves_own_authority` and `ratification_evidence_present`, and it would
    let "i-said-so" become "i-said-so" plus verified=True.

    It carries facts policy cross-checks *relationally against the proposal*:
    the binding stops an attestation being replayed on a different proposal, and
    the verifier principal is compared to the actor so self-verification is
    derived rather than trusted.

    Honest limit: this is still constructed by the caller, so an actor who can
    build a Proposal can build one. What changes is that the assertion path is
    closed entirely -- ordinary `evaluate` can no longer discharge external
    verification at all. Making the attestation unforgeable means applying the
    RatificationRegistry pattern to attestations: written by the verifier,
    resolved rather than trusted. That is a further cycle and is not claimed here.
    """

    bound_proposal_id: str
    verifier_principal_id: str
    authority_kind: str
    max_risk_class: str


@dataclass(frozen=True)
class Decision:
    outcome: str
    permitted_actions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    reasons: tuple[str, ...] = field(default_factory=tuple)
    policy_version: str = POLICY_VERSION
    # GAP-ARCH-04 (LD3): what a review discharge rested on. "asserted" means the
    # caller set review_satisfied and supplied approval refs that nothing
    # verified. "verified" is reserved for the evidence-bound discharge and is
    # not produced by this cycle. Generalizes enforcement_evidence's
    # unverified/verified distinction, which policy had no equivalent of.
    review_discharge: str = ""


def _strictest(*outcomes: str) -> str:
    return max(outcomes, key=lambda outcome: _STRICTNESS[outcome])


def _base_outcome(proposal: Proposal) -> str:
    return _BASE_TABLE.get((proposal.operation, proposal.risk_class), REQUIRE_REVIEW)


def _apply_floors(outcome: str, proposal: Proposal) -> tuple[str, list[str]]:
    reasons: list[str] = []
    target_floor = _TARGET_FLOOR.get(proposal.target_class)
    if target_floor and _STRICTNESS[target_floor] > _STRICTNESS[outcome]:
        outcome = target_floor
        reasons.append(f"target-class floor {proposal.target_class}")
    authority_floor = _AUTHORITY_FLOOR.get(proposal.downstream_authority)
    if authority_floor and _STRICTNESS[authority_floor] > _STRICTNESS[outcome]:
        outcome = authority_floor
        reasons.append(f"authority floor {proposal.downstream_authority}")
    return outcome, reasons


def _apply_modifiers(outcome: str, proposal: Proposal) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not proposal.actor_authority_resolved:
        return BLOCK, ["M-AUTH: actor authority could not be reconstructed"]
    # GAP-ARCH-04 (LD1, LD2): derive self-approval from identity rather than
    # trusting the proposer's boolean. Generalizes decision_overwrite.py:171,
    # which already computes this (grant.principal_id == proposal.proposing_actor).
    # Placed here, beside the asserted flag, so derived and asserted have
    # identical reach -- _apply_review runs only for review-requiring outcomes,
    # so deriving there would leave a self-approving allow_with_ledger proposal
    # permitted when derived and blocked when asserted.
    # Exact match on the whole ref: `any(actor_id in ref ...)` would let
    # actor_id="a" self-approve against ("grant:human",).
    approval_refs = {str(ref).strip() for ref in proposal.approval_refs}
    derived_self_approval = str(proposal.actor_id).strip() in approval_refs
    if proposal.approves_own_authority or derived_self_approval:
        return BLOCK, ["invariant 4: an actor may not approve its own authority expansion"]
    required_domains = set(proposal.required_isolation_domain_refs)
    bound_domains = set(proposal.isolation_domain_refs)
    if required_domains and not required_domains.issubset(bound_domains):
        return BLOCK, ["required isolation domains must be bound to the memory scope"]
    if proposal.operation == "domain_schema_mutation" and proposal.requested_scope_change:
        scope_floor = _BASE_TABLE[("scope_expansion", proposal.risk_class)]
        escalated = _strictest(outcome, scope_floor)
        if escalated != outcome:
            reasons.append("M-SCOPE: domain-schema mutation also requests scope expansion")
        outcome = escalated
    if proposal.reversibility == "irreversible":
        escalated = _strictest(outcome, REQUIRE_REVIEW)
        if proposal.risk_class in ("high", "critical"):
            escalated = _strictest(escalated, REQUIRE_EXTERNAL_VERIFICATION)
        if escalated != outcome:
            reasons.append("M-IRREV: irreversible mutation")
        outcome = escalated
    if not proposal.evidence_refs:
        outcome = _strictest(outcome, REQUIRE_REVIEW)
        reasons.append("M-EVID: no evidence references supplied")
    return outcome, reasons


def _apply_review(outcome: str, proposal: Proposal) -> tuple[str, list[str]]:
    """Discharge a review requirement that an external authority has satisfied.

    Review is satisfied by an approver, never by the proposer. `block` stays
    absorbing, and a proposal that would expand its own authority cannot buy
    its way past review by asserting that review happened.
    """
    if outcome not in (REQUIRE_REVIEW, REQUIRE_EXTERNAL_VERIFICATION):
        return outcome, []
    if not proposal.review_satisfied:
        return outcome, []
    if not proposal.approval_refs or proposal.approves_own_authority:
        return outcome, ["review claimed without an external approval record"]
    if outcome == REQUIRE_EXTERNAL_VERIFICATION:
        # GAP-ARCH-04 (LD1): an asserted boolean cannot discharge external
        # verification. Before this, review_satisfied plus the literal string
        # "i-said-so" collapsed policy_mutation/critical to allow_with_ledger,
        # making require_review and require_external_verification the same thing
        # under assertion. Use evaluate_with_external_verification instead.
        return outcome, ["external_verification_requires_attestation"]
    return ALLOW_WITH_LEDGER, [f"review discharged by {list(proposal.approval_refs)}"]


def _envelope(outcome: str, proposal: Proposal) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Permitted and prohibited sets. Prohibited actions are absent from permitted."""
    operation = proposal.operation
    if outcome in (ALLOW, ALLOW_WITH_LEDGER):
        return (operation,) + _DEFERRALS, ()
    if outcome == REQUIRE_REVIEW:
        return ("enter_pending_verification",) + _DEFERRALS, (operation,)
    if outcome == REQUIRE_EXTERNAL_VERIFICATION:
        return ("request_external_verification",) + _DEFERRALS, (operation,)
    return (), (operation, "enter_pending_verification", "request_external_verification")


def evaluate_with_base_outcome(
    proposal: Proposal,
    *,
    base_outcome: str,
    allow_review_discharge: bool = True,
) -> Decision:
    """Apply the common PAMA floors/modifiers to an explicitly versioned base cell.

    This is intentionally narrow. A caller may supply a different base outcome
    only when another accepted, versioned policy owns that base cell. All
    target-class, downstream-authority, scope, isolation, reversibility,
    evidence, self-approval, and actor-authority constraints remain controlling.
    """
    if base_outcome not in _STRICTNESS:
        raise ValueError(f"unsupported PAMA base outcome {base_outcome!r}")
    outcome, floor_reasons = _apply_floors(base_outcome, proposal)
    outcome, modifier_reasons = _apply_modifiers(outcome, proposal)
    review_reasons: list[str] = []
    review_discharge = ""
    if allow_review_discharge:
        before_review = outcome
        outcome, review_reasons = _apply_review(outcome, proposal)
        # LD3: detected from what _apply_review already returns rather than by
        # re-deriving its condition or widening its signature. The refusal path
        # also returns a non-empty reason list, but leaves the outcome unchanged,
        # so it cannot be mistaken for a discharge.
        if outcome != before_review and outcome == ALLOW_WITH_LEDGER and review_reasons:
            review_discharge = "asserted"
    permitted, prohibited = _envelope(outcome, proposal)
    return Decision(
        outcome=outcome,
        permitted_actions=permitted,
        prohibited_actions=prohibited,
        reasons=tuple(floor_reasons + modifier_reasons + review_reasons),
        review_discharge=review_discharge,
    )


_HIGH_RISK = ("high", "critical")
_RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
HUMAN_CONFIRMATION = "human_confirmation"


def attestation_refusal(
    proposal: Proposal, attestation: ExternalVerification
) -> str | None:
    """Cross-check an attestation against the proposal it claims to verify.

    GAP-ARCH-04 (LD3). Each check is relational: none of them can be satisfied
    by the attestation alone.
    """
    if attestation.bound_proposal_id != proposal.proposal_id:
        # Stops an attestation being replayed on a different proposal.
        return "attestation_not_bound_to_proposal"
    if attestation.verifier_principal_id == proposal.actor_id:
        # Self-verification derived from identity, as Loop 5 did for approval.
        return "attestation_self_verified"
    if (
        proposal.risk_class in _HIGH_RISK
        and attestation.authority_kind != HUMAN_CONFIRMATION
    ):
        return "human_confirmation_required"
    if attestation.max_risk_class not in _RISK_RANK:
        return "attestation_invalid_risk_ceiling"
    if _RISK_RANK[proposal.risk_class] > _RISK_RANK[attestation.max_risk_class]:
        return "attestation_risk_ceiling_exceeded"
    return None


def evaluate_with_external_verification(
    proposal: Proposal,
    attestation: ExternalVerification,
    *,
    base_outcome: str | None = None,
) -> Decision:
    """Evaluate with an attested external verification available to discharge.

    Mirrors `reusable_grants.evaluate_pama_with_reusable_grant`, which is
    already this repository's pattern for evidence-gated discharge through a
    dedicated entry point. Ordinary `evaluate` cannot reach this path.
    """
    base = _base_outcome(proposal) if base_outcome is None else base_outcome
    decision = evaluate_with_base_outcome(proposal, base_outcome=base)
    if decision.outcome != REQUIRE_EXTERNAL_VERIFICATION:
        return decision
    refusal = attestation_refusal(proposal, attestation)
    if refusal is not None:
        return replace(decision, reasons=decision.reasons + (refusal,))
    permitted, prohibited = _envelope(ALLOW_WITH_LEDGER, proposal)
    return Decision(
        outcome=ALLOW_WITH_LEDGER,
        permitted_actions=permitted,
        prohibited_actions=prohibited,
        reasons=decision.reasons
        + (f"external verification attested by {attestation.verifier_principal_id}",),
        review_discharge="verified",
    )


def evaluate(proposal: Proposal) -> Decision:
    """Resolve a proposal into a deterministic authority envelope."""
    return evaluate_with_base_outcome(proposal, base_outcome=_base_outcome(proposal))
