"""Governed shared-domain membership authority transitions.

Shared-memory membership is authority state: changing it changes who may admit
memory from a shared domain. It therefore cannot be treated as ordinary
configuration after bootstrap.

The embedding host remains responsible for authenticating principals and for
initial domain bootstrap. Runtime membership changes are evaluated as PAMA
``authority_change`` operations with an A5 authority floor, independent
qualified evidence, exact before-state binding, and a proposal-bound external
attestation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..core import policy
from ..core.evidence_qualification import (
    ASSERTED,
    REPRODUCIBLE_PROCEDURE,
    VERIFIED,
    EvidenceItem,
    qualify,
)

SLOT = "shared_membership_authority"
CRITERION = "shared-membership-authority"


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
    """Canonical membership state used by adjudication evidence and receipts."""
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


def _evidence_refusal(adapter, proposal: policy.Proposal, change: SharedMembershipChange,
                      evidence: Sequence[EvidenceItem]) -> str | None:
    """Require qualified evidence for this exact before/after transition.

    R3 permits several evidence classes in general. This authority profile is
    intentionally narrower: shared-membership changes require a reproducible
    adjudication whose inputs name the exact domain, canonical current member
    set, and canonical proposed member set. A strong piece of evidence about a
    *different* transition must not be reusable here.
    """
    before = membership_state(change.expected_members)
    after = membership_state(change.resulting_members)
    expected_inputs = f"{change.domain_ref}@{before}->{after}"
    required_binding = policy.strength_ladder_for(proposal.risk_class)["binding_status"]
    verifiers = adapter._verifier_registry.as_mapping()

    saw_direct = False
    saw_bound = False
    for item in evidence:
        qualified = qualify(item, verifiers=verifiers)
        if qualified.qualification_class != REPRODUCIBLE_PROCEDURE:
            continue
        saw_direct = True
        if item.inputs != expected_inputs or item.result != "admitted":
            continue
        saw_bound = True
        if required_binding == VERIFIED and qualified.binding_status == VERIFIED:
            return None
        if required_binding == ASSERTED and qualified.binding_status in (ASSERTED, VERIFIED):
            return None

    if saw_bound:
        return "membership_evidence_binding_insufficient"
    if saw_direct:
        return "membership_evidence_transition_mismatch"
    return "membership_evidence_class_insufficient"


def change_shared_domain_membership(
    adapter,
    change: SharedMembershipChange,
    proposal: policy.Proposal,
    *,
    evidence: Sequence[EvidenceItem],
    attestation: policy.ExternalVerification | None,
) -> SharedMembershipResult:
    """Apply one exact membership transition through independent evidence + authority.

    Evidence answers whether the requested transition is justified. The
    proposal-bound external attestation answers who may authorize an A5
    authority change. Neither substitutes for the other.

    The adapter's verifier registry is host-owned and intentionally not exposed
    as a per-call parameter. A proposing caller therefore cannot register the
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

    evidence_refusal = _evidence_refusal(adapter, proposal, change, evidence)
    if evidence_refusal is not None:
        return _refuse(proposal, change.domain_ref, current, evidence_refusal)

    # A5 is a governance/security authority boundary. The ordinary evaluator
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
        "criterion": CRITERION,
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
