"""Governed revocation delegation for owned memory lineages (#786 candidate, pending review).

A lineage committed with ``ownership="creator_principal_v1"`` records its creator in
canonical scope metadata, and the canonical write and delete gates allow only that
owner to replace or revoke it. This module is the only way to let another principal
*revoke* an owned lineage: an exact, owner-proposed delegation change.

Who may revoke a memory is an authority change (A5), with the same shape as governed
shared-domain membership: PAMA records ``require_external_verification``, a bound
external verification satisfies the consequence, and the decision is never rewritten
into ``allow``. A delegate may revoke; it may never replace the head, and it cannot
delegate further. The embedding host remains responsible for authenticating the
principal it binds to each proposal.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core import policy, receipts
from .adapter import REVOCATION_DELEGATIONS_KEY, GovernedMemoryAdapter
from .shared_revocation import _authority_ref, _external_authority_refusal, _ledger, _members, _selection_for

OPERATION = "authority_change"
CHANGE_KINDS = frozenset({"add", "remove"})


@dataclass(frozen=True)
class RevocationDelegationChange:
    """One exact requested change to who may revoke one owned lineage."""

    change_id: str
    memory_ref: str
    change_kind: str
    before_delegates: tuple[str, ...]
    after_delegates: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.change_id or not self.memory_ref:
            raise ValueError("delegation change requires change_id and memory_ref")
        if self.change_kind not in CHANGE_KINDS:
            raise ValueError(f"unsupported delegation change kind: {self.change_kind}")
        before, after = set(_members(self.before_delegates)), set(_members(self.after_delegates))
        if self.change_kind == "add" and not before < after:
            raise ValueError("add must strictly add delegates")
        if self.change_kind == "remove" and not after < before:
            raise ValueError("remove must strictly remove delegates")


@dataclass(frozen=True)
class RevocationDelegationResult:
    change: RevocationDelegationChange
    decision: policy.Decision
    pama_decision: dict
    receipt: dict
    before_delegates: tuple[str, ...]
    after_delegates: tuple[str, ...]
    committed: bool
    refusal: str | None
    external_authority_ref: str | None = None


def _load_state(memory: GovernedMemoryAdapter) -> dict:
    raw = memory.extension_state.get(REVOCATION_DELEGATIONS_KEY) or {}
    return {
        "delegates": {key: list(value) for key, value in dict(raw.get("delegates", {})).items()},
        "versions": {key: int(value) for key, value in dict(raw.get("versions", {})).items()},
        "changes": dict(raw.get("changes", {})),
        "proposals": dict(raw.get("proposals", {})),
    }


def _store_state(memory: GovernedMemoryAdapter, state: dict) -> None:
    # Whole-value replacement keeps the incremental checkpoint publication exact.
    memory.extension_state[REVOCATION_DELEGATIONS_KEY] = {
        "delegates": {key: list(value) for key, value in sorted(state["delegates"].items()) if value},
        "versions": dict(sorted(state["versions"].items())),
        "changes": {key: dict(value) for key, value in sorted(state["changes"].items())},
        "proposals": dict(sorted(state["proposals"].items())),
    }


def _binding_refusal(memory, change, proposal, state, current, version) -> str | None:
    if proposal.operation != OPERATION:
        return "delegation_requires_authority_change"
    if proposal.target_reference != change.memory_ref:
        return "delegation_memory_binding_mismatch"
    if proposal.target_class != policy.M5 or proposal.downstream_authority != policy.A5:
        return "delegation_requires_M5_A5_governance"
    owner = memory.lineage_owner(change.memory_ref)
    # Unknown, unowned and foreign lineages are indistinguishable to a non-owner.
    if owner is None or proposal.actor_id != owner:
        return "owner_required"
    if change.change_id in state["changes"]:
        return "delegation_change_replay"
    if proposal.proposal_id in state["proposals"]:
        return "delegation_proposal_replay"
    if owner in _members(change.after_delegates):
        return "owner_cannot_be_delegate"
    if current != _members(change.before_delegates):
        return "stale_delegation_binding"
    if proposal.state_snapshot != version:
        return "stale_authorization"
    return None


def commit_revocation_delegation(
    memory: GovernedMemoryAdapter,
    change: RevocationDelegationChange,
    proposal: policy.Proposal,
    *,
    evidence=None,
    attestation: policy.ExternalVerification | None = None,
) -> RevocationDelegationResult:
    """Evaluate, ledger and (only with bound external authority) commit one delegation change."""
    state = _load_state(memory)
    current = _members(state["delegates"].get(change.memory_ref, ()))
    version = f"v{state['versions'].get(change.memory_ref, 0)}"
    refusal = _binding_refusal(memory, change, proposal, state, current, version)
    if refusal is not None:
        decision = policy.Decision(
            outcome=policy.BLOCK,
            permitted_actions=(),
            prohibited_actions=(proposal.operation,),
            reasons=(refusal,),
            constraints=("risk_cell", f"target_floor:{policy.M5}", f"authority_floor:{policy.A5}"),
        )
        pama_decision, receipt, _ = _ledger(memory, proposal, decision, before_state=version)
        return RevocationDelegationResult(change, decision, pama_decision, receipt, current, current, False, refusal)

    # Evidence may support the proposition; it cannot lower the A5 authority floor.
    decision = memory.evaluate_proposal(proposal, evidence=evidence)
    pama_decision, receipt, receipt_id = _ledger(memory, proposal, decision, before_state=version)
    correlation = memory.mint_id()
    propose_event = memory.record_event("memory.revocation_delegation.propose", change.memory_ref, correlation)
    authorize_event = memory.record_event(
        "memory.revocation_delegation.authorize",
        change.memory_ref,
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
        return RevocationDelegationResult(
            change, decision, pama_decision, receipt, current, current, False, authority_refusal,
        )

    assert attestation is not None
    after = _members(change.after_delegates)
    next_version = state["versions"].get(change.memory_ref, 0) + 1
    state["delegates"][change.memory_ref] = list(after)
    state["versions"][change.memory_ref] = next_version
    state["changes"][change.change_id] = {
        "change_id": change.change_id,
        "change_kind": change.change_kind,
        "memory_ref": change.memory_ref,
        "owner_principal_ref": proposal.actor_id,
        "proposal_id": proposal.proposal_id,
        "pama_receipt_id": receipt_id,
        "pama_outcome": decision.outcome,
        "policy_version": decision.policy_version,
        "external_authority_ref": _authority_ref(proposal, attestation),
        "before_delegates": list(current),
        "after_delegates": list(after),
        "before_state": version,
        "after_state": f"v{next_version}",
    }
    state["proposals"][proposal.proposal_id] = change.change_id
    _store_state(memory, state)
    memory.record_event(
        "memory.revocation_delegation.commit",
        change.memory_ref,
        correlation,
        causation_id=authorize_event["event_id"],
        policy_version=decision.policy_version,
        receipt_ref=receipt_id,
    )
    return RevocationDelegationResult(
        change, decision, pama_decision, receipt, current, after, True, None,
        external_authority_ref=_authority_ref(proposal, attestation),
    )
