"""Governed shared-domain membership mutation for issue #364.

Shared-domain membership controls who may recall memory from a shared isolation
domain. Changing that set is therefore an ``authority_change`` consequence, not
ordinary runtime configuration.

The embedding host remains responsible for authenticating ``principal_ref`` on
recall. This module governs mutation of Agent Memory's recorded membership state;
it does not introduce a local identity provider.

A5 governance changes have a deliberately different shape from ordinary memory
mutations. PAMA records the requirement for external verification; it does not
turn that requirement into an ordinary ``allow`` outcome. A bound external
verification may satisfy the authority requirement for this exact consequence,
but the canonical PAMA decision remains ``require_external_verification``.

``bootstrap_shared_domain_members`` is deliberately named as a fixture/bootstrap
seam. Production/reference runtime mutation belongs through
``commit_shared_domain_membership_change``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..core import policy, receipts
from ..runtime.adapter import GovernedMemoryAdapter

SLOT = "shared_domain_membership_authority"
OPERATION = "authority_change"
CHANGE_KINDS = frozenset({"add", "remove", "replace"})
REQUEST_EXTERNAL = "request_external_verification"
ENTER_PENDING = "enter_pending_verification"


@dataclass(frozen=True)
class SharedDomainMembershipChange:
    """One exact requested membership transition."""

    change_id: str
    domain_ref: str
    change_kind: str
    before_members: tuple[str, ...]
    after_members: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.change_id or not self.domain_ref:
            raise ValueError("membership change requires change_id and domain_ref")
        if self.change_kind not in CHANGE_KINDS:
            raise ValueError(f"unsupported membership change kind: {self.change_kind}")
        before = _members(self.before_members)
        after = _members(self.after_members)
        if before == after:
            raise ValueError("membership change must change the member set")
        before_set, after_set = set(before), set(after)
        if self.change_kind == "add" and not (before_set < after_set):
            raise ValueError("add must strictly add members without removing existing members")
        if self.change_kind == "remove" and not (after_set < before_set):
            raise ValueError("remove must strictly remove members without adding new members")


@dataclass(frozen=True)
class SharedDomainMembershipResult:
    change: SharedDomainMembershipChange
    decision: policy.Decision
    pama_decision: dict
    receipt: dict
    before_members: tuple[str, ...]
    after_members: tuple[str, ...]
    committed: bool
    refusal: str | None = None
    external_authority_ref: str | None = None


def _members(values) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def current_shared_domain_members(memory: GovernedMemoryAdapter, domain_ref: str) -> tuple[str, ...]:
    """Return current recorded membership without granting or changing authority."""
    if not domain_ref:
        raise ValueError("shared domain requires a stable domain ref")
    raw = getattr(memory, "_shared_domain_members", None)
    if not isinstance(raw, dict):
        raise TypeError("adapter does not expose shared-domain membership state")
    return _members(raw.get(domain_ref, ()))


def bootstrap_shared_domain_members(
    memory: GovernedMemoryAdapter,
    domain_ref: str,
    members: tuple[str, ...],
) -> None:
    """Seed fixture/bootstrap state without claiming a governed authority change.

    This function exists for deterministic test/bootstrap construction only. A
    runtime membership change after initialization must use
    ``commit_shared_domain_membership_change``.
    """
    memory.set_shared_domain_members(domain_ref, _members(members))


def _load_state(memory: GovernedMemoryAdapter) -> dict[str, Any]:
    raw = memory.extension_state.get(SLOT)
    if raw is None:
        return {"versions": {}, "changes": {}, "proposals": {}}
    if not isinstance(raw, Mapping):
        raise ValueError("shared-domain membership authority state is malformed")
    try:
        versions = {str(key): int(value) for key, value in dict(raw["versions"]).items()}
        changes = dict(raw["changes"])
        proposals = {str(key): str(value) for key, value in dict(raw["proposals"]).items()}
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError("shared-domain membership authority state is malformed") from exc
    return {"versions": versions, "changes": changes, "proposals": proposals}


def _store_state(memory: GovernedMemoryAdapter, state: Mapping[str, Any]) -> None:
    memory.extension_state[SLOT] = {
        "versions": dict(sorted(dict(state["versions"]).items())),
        "changes": {key: dict(value) for key, value in sorted(dict(state["changes"]).items())},
        "proposals": dict(sorted(dict(state["proposals"]).items())),
    }


def _validate_binding(
    memory: GovernedMemoryAdapter,
    change: SharedDomainMembershipChange,
    proposal: policy.Proposal,
    state: Mapping[str, Any],
) -> tuple[tuple[str, ...], str, str | None]:
    if proposal.operation != OPERATION:
        return (), "", "membership_change_requires_authority_change"
    if proposal.target_reference != change.domain_ref:
        return (), "", "membership_domain_binding_mismatch"
    if proposal.target_class != policy.M5:
        return (), "", "membership_change_requires_M5_target_class"
    if proposal.downstream_authority != policy.A5:
        return (), "", "membership_change_requires_A5_governance_authority"

    current = current_shared_domain_members(memory, change.domain_ref)
    versions = dict(state["versions"])
    current_version = f"v{versions.get(change.domain_ref, 0)}"

    # Replay is a stronger diagnosis than the inevitable before-state mismatch
    # after a successful prior mutation, so detect it first.
    if change.change_id in state["changes"]:
        return current, current_version, "membership_change_replay"
    if proposal.proposal_id in state["proposals"]:
        return current, current_version, "membership_proposal_replay"

    expected = _members(change.before_members)
    if current != expected:
        return current, current_version, "stale_membership_binding"
    if not proposal.state_snapshot:
        return current, current_version, "membership_change_requires_state_snapshot"
    if proposal.state_snapshot != current_version:
        return current, current_version, "stale_authorization"
    return current, current_version, None


def _blocked_decision(proposal: policy.Proposal, reason: str) -> policy.Decision:
    return policy.Decision(
        outcome=policy.BLOCK,
        permitted_actions=(),
        prohibited_actions=(proposal.operation,),
        reasons=(reason,),
        constraints=("risk_cell", f"target_floor:{policy.M5}", f"authority_floor:{policy.A5}"),
    )


def _selection_for(decision: policy.Decision) -> tuple[str, str | None]:
    """Select only a remediation action from the canonical PAMA envelope."""
    if REQUEST_EXTERNAL in decision.permitted_actions:
        return REQUEST_EXTERNAL, "deterministic"
    if ENTER_PENDING in decision.permitted_actions:
        return ENTER_PENDING, "deterministic"
    return receipts.NO_ACTION, None


def _ledger(
    memory: GovernedMemoryAdapter,
    proposal: policy.Proposal,
    decision: policy.Decision,
    *,
    before_state: str,
) -> tuple[dict, dict, str]:
    """Record the canonical PAMA requirement before any authority consequence.

    For A5, a valid PAMA record never selects ``authority_change`` itself. It
    selects the remediation route (normally ``request_external_verification``),
    while the separately validated external authority binds the durable change.
    """
    selected, selection_mode = _selection_for(decision)
    receipt_id = memory.mint_id()
    pama_decision = receipts.build_pama_decision(
        proposal,
        decision,
        selected,
        selection_mode,
        receipt_id,
    )
    receipt = receipts.build_receipt(
        receipt_id=receipt_id,
        proposal=proposal,
        decision=decision,
        selected_action=selected,
        selection_mode="none" if selected == receipts.NO_ACTION else "deterministic",
        timestamp=memory.now(),
        before_state=before_state,
        after_state=before_state,
    )
    receipts.verify_receipt_decision_pair(receipt, pama_decision)
    return pama_decision, receipt, receipt_id


def _authority_ref(proposal: policy.Proposal, attestation: policy.ExternalVerification) -> str:
    return f"external-verification:{proposal.proposal_id}:{attestation.verifier_principal_id}"


def _external_authority_refusal(
    proposal: policy.Proposal,
    decision: policy.Decision,
    attestation: policy.ExternalVerification | None,
) -> str | None:
    if decision.outcome != policy.REQUIRE_EXTERNAL_VERIFICATION:
        return f"membership_change_not_external_verification:{decision.outcome}"
    if attestation is None:
        return "external_verification_required"
    return policy.attestation_refusal(proposal, attestation)


def commit_shared_domain_membership_change(
    memory: GovernedMemoryAdapter,
    change: SharedDomainMembershipChange,
    proposal: policy.Proposal,
    *,
    evidence=None,
    attestation: policy.ExternalVerification | None = None,
) -> SharedDomainMembershipResult:
    """Evaluate, ledger, and commit one exact shared-domain authority change.

    The durable consequence is bound to the exact domain, previous member set,
    resulting member set, proposal id, state snapshot, canonical PAMA requirement,
    and a separately validated external authority record.

    The A5 boundary is intentional: PAMA remains
    ``require_external_verification`` even when a valid attestation is present.
    The attestation satisfies the external authority requirement for this exact
    consequence; it does not rewrite PAMA's decision into ``allow``.
    """
    state = _load_state(memory)
    current, before_state, binding_refusal = _validate_binding(memory, change, proposal, state)

    if binding_refusal:
        decision = _blocked_decision(proposal, binding_refusal)
        pama_decision, receipt, _ = _ledger(
            memory,
            proposal,
            decision,
            before_state=before_state or proposal.state_snapshot or "unknown",
        )
        return SharedDomainMembershipResult(
            change=change,
            decision=decision,
            pama_decision=pama_decision,
            receipt=receipt,
            before_members=current,
            after_members=current,
            committed=False,
            refusal=binding_refusal,
        )

    # Evidence may qualify the proposition under review, but it cannot lower the
    # A5 authority floor. Deliberately omit the attestation from PAMA evaluation:
    # the canonical A5 decision remains the external-verification requirement.
    decision = memory.evaluate_proposal(proposal, evidence=evidence)
    pama_decision, receipt, receipt_id = _ledger(
        memory,
        proposal,
        decision,
        before_state=before_state,
    )

    correlation = memory.mint_id()
    propose_event = memory.record_event("memory.shared_membership.propose", change.domain_ref, correlation)
    authorize_event = memory.record_event(
        "memory.shared_membership.authorize",
        change.domain_ref,
        correlation,
        causation_id=propose_event["event_id"],
        policy_version=decision.policy_version,
        authority={
            "permitted_actions": list(decision.permitted_actions),
            "prohibited_actions": list(decision.prohibited_actions),
            "selection_mode": "deterministic" if _selection_for(decision)[0] != receipts.NO_ACTION else "none",
        },
    )

    authority_refusal = _external_authority_refusal(proposal, decision, attestation)
    if authority_refusal is not None:
        return SharedDomainMembershipResult(
            change=change,
            decision=decision,
            pama_decision=pama_decision,
            receipt=receipt,
            before_members=current,
            after_members=current,
            committed=False,
            refusal=authority_refusal,
        )

    assert attestation is not None
    external_authority_ref = _authority_ref(proposal, attestation)

    # This is the single governed production/reference mutation point. The
    # adapter-owned map remains part of #363's persistence-contract cleanup; the
    # current restart profile already snapshots/restores it and extension_state.
    after_members = _members(change.after_members)
    memory._shared_domain_members[change.domain_ref] = set(after_members)
    version = state["versions"].get(change.domain_ref, 0) + 1
    state["versions"][change.domain_ref] = version
    record = {
        "change_id": change.change_id,
        "change_kind": change.change_kind,
        "domain_ref": change.domain_ref,
        "proposal_id": proposal.proposal_id,
        "pama_receipt_id": receipt_id,
        "pama_decision_ref": receipts.decision_ref_for(proposal.proposal_id),
        "pama_outcome": decision.outcome,
        "policy_version": decision.policy_version,
        "external_authority_ref": external_authority_ref,
        "external_verification": {
            "bound_proposal_id": attestation.bound_proposal_id,
            "verifier_principal_id": attestation.verifier_principal_id,
            "authority_kind": attestation.authority_kind,
            "max_risk_class": attestation.max_risk_class,
        },
        "before_members": list(current),
        "after_members": list(after_members),
        "before_state": before_state,
        "after_state": f"v{version}",
    }
    state["changes"][change.change_id] = record
    state["proposals"][proposal.proposal_id] = change.change_id
    _store_state(memory, state)
    memory.record_event(
        "memory.shared_membership.commit",
        change.domain_ref,
        correlation,
        causation_id=authorize_event["event_id"],
        policy_version=decision.policy_version,
        receipt_ref=receipt_id,
    )

    return SharedDomainMembershipResult(
        change=change,
        decision=decision,
        pama_decision=pama_decision,
        receipt=receipt,
        before_members=current,
        after_members=after_members,
        committed=True,
        refusal=None,
        external_authority_ref=external_authority_ref,
    )


__all__ = [
    "SLOT",
    "OPERATION",
    "REQUEST_EXTERNAL",
    "SharedDomainMembershipChange",
    "SharedDomainMembershipResult",
    "bootstrap_shared_domain_members",
    "current_shared_domain_members",
    "commit_shared_domain_membership_change",
]
