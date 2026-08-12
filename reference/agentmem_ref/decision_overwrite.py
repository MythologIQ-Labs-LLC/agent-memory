"""Reference authority boundary for durable decision overwrite.

This module exercises ADR-025 without turning decision memory into a second
policy engine. Durable decisions are immutable episodes. An overwrite proposal
may be retained as audit evidence without changing current decision state.
Only a proposal whose exact authority grant remains valid is evaluated through
PAMA, and only a permitted PAMA consequence appends supersession evidence.

The central distinctions are:

proposal != approval != committed supersession
historical approval != reusable authority
agent consensus != human confirmation

Stdlib apart from the canonical schema validation reached through ``receipts``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from . import policy, receipts

PENDING = "pending"
REJECTED = "rejected"
COMMITTED = "committed"

HUMAN_CONFIRMATION = "human_confirmation"
DELEGATED_POLICY = "delegated_policy"
AGENT_CONSENSUS = "agent_consensus"

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass(frozen=True)
class DurableDecision:
    decision_id: str
    decision_statement: str
    rationale: str
    decision_scope: str
    owner: str
    approval_refs: tuple[str, ...]
    decided_at: str
    status_at_creation: str = "active"
    supersedes: str | None = None
    human_confirmed: bool = False


@dataclass(frozen=True)
class OverwriteProposal:
    proposal_id: str
    proposing_actor: str
    target_decision_id: str
    replacement: DurableDecision
    scope: str
    rationale: str
    evidence_refs: tuple[str, ...]
    conflict_notes: tuple[str, ...]
    state_snapshot: str
    risk_class: str
    target_class: str = policy.M4
    downstream_authority: str = policy.A3
    reversibility: str = "reversible"


@dataclass(frozen=True)
class AuthorityGrant:
    grant_id: str
    authority_kind: str
    principal_id: str
    proposal_id: str
    target_decision_id: str
    scope: str
    mutation_class: str
    issued_at: str
    expires_at: str
    max_risk_class: str
    authorized_actor_ids: tuple[str, ...]
    revoked: bool = False


@dataclass
class OverwriteResult:
    proposal: OverwriteProposal
    status: str
    reason: str | None = None
    grant: AuthorityGrant | None = None
    decision: policy.Decision | None = None
    pama_decision: dict | None = None
    receipt: dict | None = None
    events: list[dict] = field(default_factory=list)
    supersession_evidence: dict | None = None


class DurableDecisionRegistry:
    """Append-oriented reference registry for ADR-025 evidence.

    Decision objects are never mutated after registration. Current/superseded
    status is derived from the append-only supersession journal. This registry
    demonstrates the authority boundary, not a production decision database.
    """

    def __init__(self, now: Callable[[], str]) -> None:
        self._now = now
        self._decisions: dict[str, DurableDecision] = {}
        self._superseded_by: dict[str, str] = {}
        self._versions: dict[str, int] = {}
        self._proposals: dict[str, OverwriteResult] = {}
        self.supersession_journal: list[dict] = []
        self.events: list[dict] = []
        self._event_counter = 0
        self._receipt_counter = 0

    def register(self, decision: DurableDecision) -> None:
        self._validate_decision(decision)
        if decision.decision_id in self._decisions:
            raise ValueError(f"decision already exists: {decision.decision_id}")
        if decision.supersedes is not None:
            raise ValueError("initial registration cannot silently supersede another decision")
        self._decisions[decision.decision_id] = decision
        self._versions[decision.decision_id] = 0

    def propose(self, proposal: OverwriteProposal) -> OverwriteResult:
        if proposal.proposal_id in self._proposals:
            raise ValueError(f"overwrite proposal already exists: {proposal.proposal_id}")
        self._validate_proposal_shape(proposal)
        event = self._event(
            "memory.decision_overwrite_proposed",
            proposal,
            self._now(),
            status=PENDING,
        )
        result = OverwriteResult(proposal=proposal, status=PENDING, events=[event])
        self._proposals[proposal.proposal_id] = result
        self.events.append(event)
        return result

    def commit(self, proposal_id: str, grant: AuthorityGrant | None) -> OverwriteResult:
        result = self._proposals.get(proposal_id)
        if result is None:
            raise ValueError(f"unknown overwrite proposal: {proposal_id}")
        if result.status != PENDING:
            return result

        proposal = result.proposal
        now = self._now()
        refusal = self._precommit_refusal(proposal, grant, now)
        if refusal:
            return self._reject(result, grant, now, refusal)

        assert grant is not None  # proved by _precommit_refusal
        pama_proposal = policy.Proposal(
            proposal_id=proposal.proposal_id,
            actor_id=proposal.proposing_actor,
            charter_version="decision-overwrite-reference",
            target_reference=proposal.target_decision_id,
            target_class=proposal.target_class,
            scope=proposal.scope,
            operation="decision_overwrite",
            current_strength="durable_decision",
            proposed_strength="superseded",
            downstream_authority=proposal.downstream_authority,
            reversibility=proposal.reversibility,
            risk_class=proposal.risk_class,
            evidence_refs=proposal.evidence_refs,
            actor_authority_resolved=True,
            approves_own_authority=grant.principal_id == proposal.proposing_actor,
            approval_refs=(grant.grant_id,),
            review_satisfied=True,
            state_snapshot=proposal.state_snapshot,
            purpose="durable-decision-overwrite",
        )
        decision = policy.evaluate(pama_proposal)
        selected_action = (
            pama_proposal.operation
            if pama_proposal.operation in decision.permitted_actions
            else receipts.NO_ACTION
        )

        before_state = proposal.state_snapshot
        after_state = before_state
        self._receipt_counter += 1
        receipt_id = f"decision-overwrite-receipt:{self._receipt_counter}"

        if selected_action == receipts.NO_ACTION:
            receipt = receipts.build_receipt(
                receipt_id=receipt_id,
                proposal=pama_proposal,
                decision=decision,
                selected_action=receipts.NO_ACTION,
                selection_mode="none",
                timestamp=now,
                before_state=before_state,
                after_state=after_state,
            )
            pama_decision = receipts.build_pama_decision(
                pama_proposal,
                decision,
                receipts.NO_ACTION,
                None,
                receipt_id,
            )
            result.grant = grant
            result.decision = decision
            result.receipt = receipt
            result.pama_decision = pama_decision
            return self._reject(result, grant, now, "pama_not_permitted", receipt_ref=receipt_id)

        new_version = self._versions[proposal.target_decision_id] + 1
        after_state = f"v{new_version}"
        receipt = receipts.build_receipt(
            receipt_id=receipt_id,
            proposal=pama_proposal,
            decision=decision,
            selected_action=selected_action,
            selection_mode="human" if grant.authority_kind == HUMAN_CONFIRMATION else "external",
            timestamp=now,
            before_state=before_state,
            after_state=after_state,
            rollback_ref=f"decision-recovery:{proposal.target_decision_id}:{before_state}",
        )
        pama_decision = receipts.build_pama_decision(
            pama_proposal,
            decision,
            selected_action,
            "human" if grant.authority_kind == HUMAN_CONFIRMATION else "external",
            receipt_id,
        )
        receipts.verify_receipt_decision_pair(receipt, pama_decision)

        replacement = proposal.replacement
        self._decisions[replacement.decision_id] = replacement
        self._versions[proposal.target_decision_id] = new_version
        self._superseded_by[proposal.target_decision_id] = replacement.decision_id
        evidence = {
            "supersession_id": f"supersession:{proposal.proposal_id}",
            "prior_decision_id": proposal.target_decision_id,
            "replacement_decision_id": replacement.decision_id,
            "proposal_id": proposal.proposal_id,
            "authority_grant_ref": grant.grant_id,
            "authority_kind": grant.authority_kind,
            "receipt_ref": receipt_id,
            "state_before": before_state,
            "state_after": after_state,
            "timestamp": now,
        }
        self.supersession_journal.append(evidence)

        event = self._event(
            "memory.decision_overwrite_committed",
            proposal,
            now,
            status=COMMITTED,
            grant=grant,
            receipt_ref=receipt_id,
            extra_payload={"replacement_decision_id": replacement.decision_id},
        )
        result.status = COMMITTED
        result.reason = None
        result.grant = grant
        result.decision = decision
        result.receipt = receipt
        result.pama_decision = pama_decision
        result.supersession_evidence = evidence
        result.events.append(event)
        self.events.append(event)
        return result

    def decision(self, decision_id: str) -> DurableDecision | None:
        return self._decisions.get(decision_id)

    def decision_status(self, decision_id: str) -> str | None:
        if decision_id not in self._decisions:
            return None
        if decision_id in self._superseded_by:
            return "superseded"
        return self._decisions[decision_id].status_at_creation

    def superseded_by(self, decision_id: str) -> str | None:
        return self._superseded_by.get(decision_id)

    def state_snapshot(self, decision_id: str) -> str:
        if decision_id not in self._decisions:
            raise ValueError(f"unknown decision: {decision_id}")
        return f"v{self._versions[decision_id]}"

    def record_external_state_change(self, decision_id: str) -> str:
        """Advance current state to exercise stale-proposal rejection."""
        if decision_id not in self._decisions:
            raise ValueError(f"unknown decision: {decision_id}")
        self._versions[decision_id] += 1
        return self.state_snapshot(decision_id)

    def _precommit_refusal(
        self,
        proposal: OverwriteProposal,
        grant: AuthorityGrant | None,
        now: str,
    ) -> str | None:
        target = self._decisions.get(proposal.target_decision_id)
        if target is None:
            return "unknown_target_decision"
        if proposal.target_decision_id in self._superseded_by:
            return "target_not_current"
        if proposal.state_snapshot != self.state_snapshot(proposal.target_decision_id):
            return "stale_overwrite_proposal"
        if proposal.replacement.decision_id in self._decisions:
            return "replacement_decision_already_exists"
        if proposal.replacement.supersedes != proposal.target_decision_id:
            return "replacement_supersession_mismatch"
        if proposal.replacement.decision_scope != proposal.scope or target.decision_scope != proposal.scope:
            return "decision_scope_mismatch"
        if grant is None:
            return "authority_required"

        grant_refusal = self._grant_refusal(proposal, target, grant, now)
        if grant_refusal:
            return grant_refusal
        return None

    def _grant_refusal(
        self,
        proposal: OverwriteProposal,
        target: DurableDecision,
        grant: AuthorityGrant,
        now: str,
    ) -> str | None:
        if grant.revoked:
            return "authority_grant_revoked"
        if self._is_expired(grant, now):
            return "authority_grant_expired"
        if grant.proposal_id != proposal.proposal_id:
            return "authority_proposal_mismatch"
        if grant.target_decision_id != proposal.target_decision_id:
            return "authority_target_mismatch"
        if grant.scope != proposal.scope:
            return "authority_scope_mismatch"
        if grant.mutation_class != "decision_overwrite":
            return "authority_mutation_mismatch"
        if proposal.proposing_actor not in grant.authorized_actor_ids:
            return "actor_not_delegated"
        if grant.principal_id == proposal.proposing_actor:
            return "self_approval_prohibited"
        if grant.max_risk_class not in _RISK_ORDER:
            return "invalid_authority_risk_ceiling"
        if _RISK_ORDER[proposal.risk_class] > _RISK_ORDER[grant.max_risk_class]:
            return "authority_risk_ceiling_exceeded"

        human_required = target.human_confirmed or proposal.risk_class in ("high", "critical")
        if human_required and grant.authority_kind != HUMAN_CONFIRMATION:
            return "human_confirmation_required"
        if grant.authority_kind not in (HUMAN_CONFIRMATION, DELEGATED_POLICY):
            return "unsupported_authority_kind"
        if grant.authority_kind == DELEGATED_POLICY and proposal.risk_class not in ("low", "medium"):
            return "delegation_not_permitted_for_risk"
        return None

    def _reject(
        self,
        result: OverwriteResult,
        grant: AuthorityGrant | None,
        timestamp: str,
        reason: str,
        *,
        receipt_ref: str | None = None,
    ) -> OverwriteResult:
        result.status = REJECTED
        result.reason = reason
        if grant is not None:
            result.grant = grant
        event = self._event(
            "memory.decision_overwrite_rejected",
            result.proposal,
            timestamp,
            status=REJECTED,
            reason=reason,
            grant=grant,
            receipt_ref=receipt_ref,
        )
        result.events.append(event)
        self.events.append(event)
        return result

    @staticmethod
    def _validate_decision(decision: DurableDecision) -> None:
        for name in ("decision_id", "decision_statement", "rationale", "decision_scope", "owner", "decided_at"):
            if not getattr(decision, name):
                raise ValueError(f"decision field {name} must be non-empty")
        if decision.status_at_creation != "active":
            raise ValueError("reference registry accepts only active decision episodes")
        DurableDecisionRegistry._parse_time(decision.decided_at)

    @staticmethod
    def _validate_proposal_shape(proposal: OverwriteProposal) -> None:
        for name in ("proposal_id", "proposing_actor", "target_decision_id", "scope", "rationale", "state_snapshot"):
            if not getattr(proposal, name):
                raise ValueError(f"overwrite proposal field {name} must be non-empty")
        if not proposal.evidence_refs:
            raise ValueError("overwrite proposal requires evidence refs")
        if proposal.risk_class not in _RISK_ORDER:
            raise ValueError(f"invalid overwrite risk class: {proposal.risk_class}")
        DurableDecisionRegistry._validate_decision(proposal.replacement)

    @staticmethod
    def _parse_time(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid timestamp: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @classmethod
    def _is_expired(cls, grant: AuthorityGrant, now: str) -> bool:
        return cls._parse_time(now) >= cls._parse_time(grant.expires_at)

    def _event(
        self,
        event_type: str,
        proposal: OverwriteProposal,
        timestamp: str,
        *,
        status: str,
        reason: str | None = None,
        grant: AuthorityGrant | None = None,
        receipt_ref: str | None = None,
        extra_payload: dict | None = None,
    ) -> dict:
        self._event_counter += 1
        payload = {
            "proposal_id": proposal.proposal_id,
            "target_decision_id": proposal.target_decision_id,
            "replacement_decision_id": proposal.replacement.decision_id,
            "scope": proposal.scope,
            "mutation_class": "decision_overwrite",
            "risk_class": proposal.risk_class,
            "state_snapshot": proposal.state_snapshot,
            "status": status,
            "evidence_refs": list(proposal.evidence_refs),
            "conflict_notes": list(proposal.conflict_notes),
        }
        if reason:
            payload["reason"] = reason
        if grant is not None:
            payload["authority_kind"] = grant.authority_kind
            payload["authority_grant_ref"] = grant.grant_id
        if extra_payload:
            payload.update(extra_payload)
        document = {
            "schema_version": "1.0.0",
            "event_id": f"decision-overwrite-event:{self._event_counter}",
            "event_type": event_type,
            "event_version": "1.0.0",
            "timestamp": timestamp,
            "component": "durable-decision-registry",
            "memory_id": proposal.target_decision_id,
            "actor": proposal.proposing_actor,
            "correlation_id": proposal.proposal_id,
            "payload": payload,
        }
        if grant is not None:
            document["authority"] = {"authority_refs": [grant.grant_id]}
        if receipt_ref:
            document["receipt_ref"] = receipt_ref
        receipts.validate("memory-audit-event.schema.json", document)
        return document
