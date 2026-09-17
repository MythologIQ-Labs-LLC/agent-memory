"""Governed shared-domain membership authority transitions.

Shared-memory membership is authority state: changing it changes who may admit
memory from a shared domain.  It therefore cannot be treated as ordinary
configuration after bootstrap.

The embedding host remains responsible for authenticating principals and for
initial domain bootstrap.  Runtime membership changes are evaluated as PAMA
``authority_change`` operations with an A5 authority floor, independent
qualified evidence, exact before-state binding, and a proposal-bound external
attestation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..core import policy
from ..core.evidence_qualification import EvidenceItem, group_by_dependence

SLOT = "shared_membership_authority"


@dataclass(frozen=True)
class SharedMembershipChange:
    domain_ref: str
    expected_members: tuple[str, ...]
    resulting_members: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class SharedMembershipResult:
    decision: policy.Decision
    domain_ref: str
    before_members: tuple[str, ...]
    after_members: tuple[str, ...]
    committed: bool
    event: dict | None = None
    refusal: str | None = None


def membership_state(members: Sequence[str]) -> str:
    """Canonical membership state used by adjudication fixtures and receipts."""
    return ",".join(sorted(set(members)))


def _slot(adapter) -> dict:
    slot = adapter.extension_state.setdefault(
        SLOT,
        {"versions": {}, "transitions": {}, "proposals": {}},
    )
    if not isinstance(slot, dict):
        raise ValueError("shared membership authority state is malformed")
    for key in ("versions", "transitions", "proposals"):
        if not isinstance(slot.get(key), dict):
            raise ValueError(f"shared membership authority {key} state is malformed")
    return slot


def _refuse(
    proposal: policy.Proposal,
    domain_ref: str,
    before: tuple[str, ...],
    reason: str,
    *,
    decision: policy.Decision | None = None,
) -> SharedMembershipResult:
    if decision is None:
        decision = policy.Decision(
            outcome=policy.BLOCK,
            permitted_actions=(),
            prohibited_actions=(proposal.operation, "authority_change"),
            reasons=(reason,),
        )
    return SharedMembershipResult(
        decision=decision,
        domain_ref=domain_ref,
        before_members=before,
        after_members=before,
        committed=False,
        refusal=reason,
    )


def change_shared_domain_membership(
    adapter,
    change: SharedMembershipChange,
    proposal: policy.Proposal,
    *,
    evidence: Sequence[EvidenceItem],
    attestation: policy.ExternalVerification | None,
) -> SharedMembershipResult:
    """Apply one exact membership transition through independent evidence + authority.

    Evidence answers whether the requested transition is justified.  The
    proposal-bound external attestation answers who may authorize an A5
    authority change.  Neither substitutes for the other.

    The adapter's verifier registry is host-owned and intentionally not exposed
    as a per-call parameter.  A proposing caller therefore cannot register the
    verifier that certifies its own evidence.
    """
    if not change.domain_ref:
        raise ValueError("shared membership change requires a stable domain ref")
    if not change.reason:
        raise ValueError("shared membership change requires a reason")
    if any(not member for member in change.resulting_members):
        raise ValueError("shared membership cannot contain an empty principal ref")

    current = tuple(sorted(adapter._shared_domain_members.get(change.domain_ref, set())))
    expected = tuple(sorted(set(change.expected_members)))
    resulting = tuple(sorted(set(change.resulting_members)))

    if proposal.operation != "authority_change":
        return _refuse(proposal, change.domain_ref, current, "membership_requires_authority_change")
    if proposal.target_reference != change.domain_ref:
        return _refuse(proposal, change.domain_ref, current, "membership_target_binding_mismatch")
    if proposal.downstream_authority != policy.A5:
        return _refuse(proposal, change.domain_ref, current, "membership_requires_a5_authority")
    if current != expected:
        return _refuse(proposal, change.domain_ref, current, "stale_membership_binding")
    if current == resulting:
        return _refuse(proposal, change.domain_ref, current, "membership_change_has_no_effect")

    slot = _slot(adapter)
    versions = slot["versions"]
    transitions = slot["transitions"]
    proposals = slot["proposals"]
    if proposal.proposal_id in proposals:
        return _refuse(proposal, change.domain_ref, current, "membership_authority_replay")

    current_version = int(versions.get(change.domain_ref, 0))
    if proposal.state_snapshot and proposal.state_snapshot != f"v{current_version}":
        return _refuse(proposal, change.domain_ref, current, "stale_authorization")

    # Evidence quality is independent from authority.  Reuse the shared R5
    # ladder and dependence grouping rather than inventing a membership-specific
    # threshold.  For high/critical risk this therefore requires verified
    # evidence; lower risk retains the existing asserted binding floor.
    analysis = group_by_dependence(
        evidence,
        verifiers=adapter._verifier_registry.as_mapping(),
    )
    required_binding = policy.strength_ladder_for(proposal.risk_class)["binding_status"]
    if not analysis.qualifying_group_count(status=required_binding):
        asserted = analysis.qualifying_group_count(status="asserted")
        reason = (
            "membership_evidence_binding_insufficient"
            if asserted
            else "membership_evidence_class_insufficient"
        )
        return _refuse(proposal, change.domain_ref, current, reason)

    # A5 is a governance/security authority boundary.  The ordinary evaluator
    # raises the fallback review outcome to external verification; only the
    # shared external-verification evaluator may discharge that state.
    decision = (
        policy.evaluate(proposal)
        if attestation is None
        else policy.evaluate_with_external_verification(proposal, attestation)
    )
    if decision.outcome not in (policy.ALLOW, policy.ALLOW_WITH_LEDGER):
        return _refuse(
            proposal,
            change.domain_ref,
            current,
            f"membership_authority_not_granted:{decision.outcome}",
            decision=decision,
        )

    adapter._shared_domain_members[change.domain_ref] = set(resulting)
    versions[change.domain_ref] = current_version + 1

    correlation = adapter.mint_id()
    event = adapter.record_event(
        "memory.shared_membership_change",
        change.domain_ref,
        correlation,
        policy_version=decision.policy_version,
        authority={
            "operation": "authority_change",
            "downstream_authority": policy.A5,
            "verifier_principal_id": (
                attestation.verifier_principal_id if attestation is not None else ""
            ),
            "authority_kind": attestation.authority_kind if attestation is not None else "",
        },
    )
    record = {
        "proposal_id": proposal.proposal_id,
        "domain_ref": change.domain_ref,
        "reason": change.reason,
        "before_members": list(current),
        "after_members": list(resulting),
        "before_state": f"v{current_version}",
        "after_state": f"v{current_version + 1}",
        "evidence_refs": list(proposal.evidence_refs),
        "verifier_principal_id": (
            attestation.verifier_principal_id if attestation is not None else ""
        ),
        "authority_kind": attestation.authority_kind if attestation is not None else "",
        "policy_version": decision.policy_version,
        "event_id": event["event_id"],
        "committed_at": event["timestamp"],
    }
    transitions[event["event_id"]] = record
    proposals[proposal.proposal_id] = event["event_id"]

    return SharedMembershipResult(
        decision=decision,
        domain_ref=change.domain_ref,
        before_members=current,
        after_members=resulting,
        committed=True,
        event=event,
    )
