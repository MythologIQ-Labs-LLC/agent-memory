"""Governed isolation-domain boundary crossings.

Executable evidence toward proposed ADR-022. The operation that moves or makes
memory influential across a logical boundary is recorded separately from the
PAMA consequence class used to authorize the broadening.

A valid receipt reconstructs a decision made under bound policy/state. It does
not grant permanent permission for future crossings after membership,
delegation, purpose, policy, or revocation state changes.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core import policy, receipts

CROSSING_OPERATIONS = frozenset(
    {
        "share",
        "export",
        "import",
        "copy",
        "promote_scope",
        "summarize_for",
        "derive_for",
        "inherit",
        "publish",
    }
)


@dataclass(frozen=True)
class CrossingRequest:
    operation: str
    source_domain_refs: tuple[str, ...]
    destination_domain_refs: tuple[str, ...]
    actor: str
    principal: str
    purpose: str
    representation_kind: str
    source_refs: tuple[str, ...]
    sensitivity_labels: tuple[str, ...] = ()
    consent_ref: str = ""
    delegation_ref: str = ""
    membership_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    policy_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    valid_until: str = ""
    revocation_refs: tuple[str, ...] = ()
    before_scope_refs: tuple[str, ...] = ()
    after_scope_refs: tuple[str, ...] = ()
    privacy_minimized: bool = False
    redaction_ref: str = ""


@dataclass(frozen=True)
class CrossingResult:
    decision: policy.Decision
    receipt: dict
    committed: bool
    refusal: str | None = None


@dataclass(frozen=True)
class BoundCrossingResult:
    """A crossing decision bound to one concrete fact-scope consequence.

    ``crossing.committed`` means PAMA authorized the crossing operation.
    ``mutated`` means that authorization also passed the state-binding checks
    and changed the governed adapter's scope state. Keeping the two explicit
    prevents an abstract allow decision from being mistaken for a durable
    mutation when the bound fact, proposal, receipt, or state has gone stale.
    """

    crossing: CrossingResult
    fact_uuid: str
    before_scope_refs: tuple[str, ...]
    after_scope_refs: tuple[str, ...]
    mutated: bool
    refusal: str | None = None


def _outcome_for(decision: policy.Decision) -> tuple[str, bool]:
    if decision.outcome in (policy.ALLOW, policy.ALLOW_WITH_LEDGER):
        return "committed", True
    if decision.outcome == policy.REQUIRE_REVIEW:
        return "review_required", False
    if decision.outcome == policy.REQUIRE_EXTERNAL_VERIFICATION:
        return "verification_required", False
    return "blocked", False


def _evaluate(proposal, evidence, attestation, verifier_registry):
    """Route through the qualified path when evidence is supplied."""
    if evidence:
        from ..core.evidence_qualification import group_by_dependence

        return policy.evaluate_with_qualified_evidence(
            proposal,
            group_by_dependence(
                evidence,
                verifiers=(verifier_registry.as_mapping() if verifier_registry else None),
            ),
            attestation=attestation,
        )
    return policy.evaluate(proposal)


def _result_for_decision(
    request: CrossingRequest,
    decision: policy.Decision,
    *,
    receipt_id: str,
    timestamp: str,
    decision_receipt_ref: str = "",
    ledger_ref: str = "",
    refusal: str | None = None,
) -> CrossingResult:
    outcome, committed = _outcome_for(decision)
    representation = {
        "kind": request.representation_kind,
        "privacy_minimized": request.privacy_minimized,
    }
    if request.redaction_ref:
        representation["redaction_ref"] = request.redaction_ref

    document = {
        "schema_version": "1.0.0",
        "receipt_id": receipt_id,
        "operation": request.operation,
        "source_domain_refs": list(request.source_domain_refs),
        "destination_domain_refs": list(request.destination_domain_refs),
        "actor": request.actor,
        "principal": request.principal,
        "purpose": request.purpose,
        "representation": representation,
        "source_refs": list(request.source_refs),
        "requested_consequence": "scope_expansion",
        "pama_disposition": decision.outcome,
        "policy_version": decision.policy_version,
        "outcome": outcome,
        "timestamp": timestamp,
    }

    optional_lists = (
        ("membership_refs", request.membership_refs),
        ("authority_refs", request.authority_refs),
        ("policy_refs", request.policy_refs),
        ("provenance_refs", request.provenance_refs),
        ("revocation_refs", request.revocation_refs),
        ("before_scope_refs", request.before_scope_refs),
        ("after_scope_refs", request.after_scope_refs),
    )
    for key, values in optional_lists:
        if values:
            document[key] = list(values)
    if request.sensitivity_labels:
        document["sensitivity"] = {"labels": list(request.sensitivity_labels)}
    if request.consent_ref:
        document["consent_ref"] = request.consent_ref
    if request.delegation_ref:
        document["delegation_ref"] = request.delegation_ref
    if request.valid_until:
        document["valid_until"] = request.valid_until
    if decision_receipt_ref:
        document["decision_receipt_ref"] = decision_receipt_ref
    if ledger_ref:
        document["ledger_ref"] = ledger_ref

    receipts.validate("boundary-crossing-receipt.schema.json", document)
    resolved_refusal = refusal
    if resolved_refusal is None and not committed:
        resolved_refusal = f"crossing not committed: {decision.outcome}"
    return CrossingResult(
        decision=decision,
        receipt=document,
        committed=committed,
        refusal=resolved_refusal,
    )


def _binding_block(
    request: CrossingRequest,
    proposal: policy.Proposal,
    *,
    receipt_id: str,
    timestamp: str,
    reason: str,
    decision_receipt_ref: str = "",
    ledger_ref: str = "",
) -> CrossingResult:
    """Build a schema-backed blocked receipt for a failed consequence binding."""
    decision = policy.Decision(
        outcome=policy.BLOCK,
        permitted_actions=(),
        prohibited_actions=(proposal.operation, "scope_expansion"),
        reasons=(reason,),
    )
    return _result_for_decision(
        request,
        decision,
        receipt_id=receipt_id,
        timestamp=timestamp,
        decision_receipt_ref=decision_receipt_ref,
        ledger_ref=ledger_ref,
        refusal=reason,
    )


def evaluate_crossing(
    request: CrossingRequest,
    proposal: policy.Proposal,
    *,
    receipt_id: str,
    timestamp: str,
    decision_receipt_ref: str = "",
    ledger_ref: str = "",
    evidence=None,
    attestation: policy.ExternalVerification | None = None,
    verifier_registry=None,
) -> CrossingResult:
    """Evaluate and receipt one requested memory-boundary crossing.

    `request.operation` describes the concrete transfer or influence operation.
    `proposal.operation` must be `scope_expansion` because crossing to a broader
    authority domain is the PAMA consequence under evaluation. This prevents a
    caller from obtaining a weaker envelope by describing an export as a copy
    or summary operation.

    SCOPE ADDITION, disclosed (ADR-037 step 4b-2, entry #24). The flip removed
    the asserted discharge for `require_review`, and this entry point evaluated
    the proposal directly -- leaving every crossing caller refused with no
    reachable remediation. `evidence` defaults to None, so a caller supplying
    none behaves exactly as before and simply parks where it used to discharge
    on assertion. Same reasoning and same shape as the adapter's addition.
    """
    if request.operation not in CROSSING_OPERATIONS:
        raise ValueError(f"unsupported crossing operation: {request.operation}")
    if not request.source_domain_refs or not request.destination_domain_refs:
        raise ValueError("crossing requires explicit source and destination domains")
    if not request.source_refs:
        raise ValueError("crossing requires at least one source memory or derivation ref")
    if proposal.operation != "scope_expansion":
        decision = policy.Decision(
            outcome=policy.BLOCK,
            permitted_actions=(),
            prohibited_actions=(proposal.operation, "scope_expansion"),
            reasons=("boundary crossing must be evaluated as scope_expansion",),
        )
    else:
        decision = _evaluate(proposal, evidence, attestation, verifier_registry)

    return _result_for_decision(
        request,
        decision,
        receipt_id=receipt_id,
        timestamp=timestamp,
        decision_receipt_ref=decision_receipt_ref,
        ledger_ref=ledger_ref,
    )


def commit_crossing(
    adapter,
    fact_uuid: str,
    request: CrossingRequest,
    proposal: policy.Proposal,
    *,
    receipt_id: str,
    timestamp: str,
    decision_receipt_ref: str = "",
    ledger_ref: str = "",
    evidence=None,
    attestation: policy.ExternalVerification | None = None,
    verifier_registry=None,
) -> BoundCrossingResult:
    """Authorize and apply one scope expansion to one exact governed fact.

    This is the write-side closure for GAP-SEC-02 / issue #364. Previously the
    crossing evaluator could authorize and receipt ``scope_expansion`` while
    the durable adapter scope remained unchanged, forcing callers to widen
    ``_fact_scope`` separately and therefore outside the decision that was
    supposed to authorize it.

    The memory layer owns this orchestration because it sits above the runtime
    adapter in the package dependency order. The adapter's current private maps
    remain a known production-state coupling tracked by #363; this function
    does not pretend that persistence problem is solved. It does, however,
    ensure the consequence is bound to the exact fact, memory, current scope,
    proposal snapshot, proposal id, and receipt id before mutation occurs.
    """
    if not fact_uuid:
        raise ValueError("crossing commit requires a fact uuid")

    fact_scope = getattr(adapter, "_fact_scope", None)
    fact_memory = getattr(adapter, "_fact_memory", None)
    state_version = getattr(adapter, "_state_version", None)
    extension_state = getattr(adapter, "extension_state", None)
    if not isinstance(fact_scope, dict) or not isinstance(fact_memory, dict):
        raise TypeError("adapter does not expose governed fact-scope state")
    if not isinstance(state_version, dict) or not isinstance(extension_state, dict):
        raise TypeError("adapter does not expose governed state versioning")

    scope = fact_scope.get(fact_uuid)
    memory_ref = fact_memory.get(fact_uuid)
    current_scope = tuple(scope.get("domain_refs", ())) if isinstance(scope, dict) else ()

    crossing_state = extension_state.setdefault("scope_crossings", {})
    receipts_seen = crossing_state.setdefault("receipts", {})
    proposals_seen = crossing_state.setdefault("proposals", {})

    def blocked(reason: str) -> BoundCrossingResult:
        crossing = _binding_block(
            request,
            proposal,
            receipt_id=receipt_id,
            timestamp=timestamp,
            reason=reason,
            decision_receipt_ref=decision_receipt_ref,
            ledger_ref=ledger_ref,
        )
        return BoundCrossingResult(
            crossing=crossing,
            fact_uuid=fact_uuid,
            before_scope_refs=current_scope,
            after_scope_refs=current_scope,
            mutated=False,
            refusal=reason,
        )

    if scope is None:
        return blocked("unknown_fact_scope")
    if memory_ref != proposal.target_reference:
        return blocked("fact_memory_binding_mismatch")
    if receipt_id in receipts_seen or proposal.proposal_id in proposals_seen:
        return blocked("scope_crossing_replay")
    if proposal.target_reference not in request.source_refs and fact_uuid not in request.source_refs:
        return blocked("crossing_source_binding_mismatch")

    expected_before = tuple(request.before_scope_refs) or tuple(request.source_domain_refs)
    if set(current_scope) != set(expected_before):
        return blocked("stale_scope_binding")
    if not set(request.source_domain_refs).issubset(set(current_scope)):
        return blocked("crossing_source_domain_mismatch")

    current_version = f"v{state_version.get(proposal.target_reference, 0)}"
    if proposal.state_snapshot and proposal.state_snapshot != current_version:
        return blocked("stale_authorization")

    authorized_destinations = tuple(
        dict.fromkeys(request.after_scope_refs or request.destination_domain_refs)
    )
    if not set(request.destination_domain_refs).issubset(set(authorized_destinations)):
        return blocked("crossing_destination_binding_mismatch")
    if not authorized_destinations or set(authorized_destinations).issubset(set(current_scope)):
        return blocked("scope_expansion_has_no_new_domain")

    crossing = evaluate_crossing(
        request,
        proposal,
        receipt_id=receipt_id,
        timestamp=timestamp,
        decision_receipt_ref=decision_receipt_ref,
        ledger_ref=ledger_ref,
        evidence=evidence,
        attestation=attestation,
        verifier_registry=verifier_registry,
    )
    if not crossing.committed:
        return BoundCrossingResult(
            crossing=crossing,
            fact_uuid=fact_uuid,
            before_scope_refs=current_scope,
            after_scope_refs=current_scope,
            mutated=False,
            refusal=crossing.refusal,
        )

    resulting_scope = tuple(dict.fromkeys((*current_scope, *authorized_destinations)))
    updated_scope = dict(scope)
    updated_scope["domain_refs"] = resulting_scope
    fact_scope[fact_uuid] = updated_scope
    state_version[proposal.target_reference] = state_version.get(proposal.target_reference, 0) + 1

    record = {
        "fact_uuid": fact_uuid,
        "memory_ref": proposal.target_reference,
        "proposal_id": proposal.proposal_id,
        "receipt_id": receipt_id,
        "policy_version": crossing.decision.policy_version,
        "before_scope_refs": list(current_scope),
        "after_scope_refs": list(resulting_scope),
        "destination_domain_refs": list(request.destination_domain_refs),
        "committed_at": timestamp,
    }
    receipts_seen[receipt_id] = record
    proposals_seen[proposal.proposal_id] = receipt_id

    return BoundCrossingResult(
        crossing=crossing,
        fact_uuid=fact_uuid,
        before_scope_refs=current_scope,
        after_scope_refs=resulting_scope,
        mutated=True,
        refusal=None,
    )
