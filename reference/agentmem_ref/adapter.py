"""The governed adapter.

Implements the end-to-end path the runtime-evidence program requires:

```text
evidence -> proposal -> authority envelope -> permitted action set
         -> selected action -> substrate mutation -> decision receipt
         -> retrieval candidate -> governed admission -> active context
```

Everything the mapped substrate cannot supply is supplied here: enforced scope
filtering, an authority gate in front of every write, lifecycle state,
tombstones, and receipts. The substrate stores; it never decides.

Stdlib only apart from the schema validation reached through `receipts`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import policy, receipts
from .substrate import DeterministicIds, Episode, Fact, TemporalGraphPort


class Clock:
    """Deterministic clock, so runs are reproducible."""

    def __init__(self, start: int = 0) -> None:
        self._t = start

    def now(self) -> str:
        self._t += 1
        return f"2026-01-01T00:00:{self._t:02d}Z"


class DeterministicSelector:
    """Prefers the requested operation when permitted, else the first permitted action."""

    mode = "deterministic"

    def select(self, permitted: tuple[str, ...], preferred: str | None) -> str:
        if not permitted:
            return receipts.NO_ACTION
        if preferred in permitted:
            return preferred
        return permitted[0]


class StochasticSelector:
    """Samples uniformly from the permitted set.

    Doctrine permits stochastic action selection *inside* an authority
    envelope. It is the adapter, not this selector, that guarantees the choice
    stays inside: a selector is untrusted by construction, so whatever it
    returns is re-checked against the permitted set before use.
    """

    mode = "stochastic"

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def select(self, permitted: tuple[str, ...], preferred: str | None) -> str:
        if not permitted:
            return receipts.NO_ACTION
        return self._rng.choice(list(permitted))


@dataclass
class CommitResult:
    decision: policy.Decision
    pama_decision: dict
    receipt: dict
    events: list[dict] = field(default_factory=list)
    committed: bool = False
    fact_uuid: str | None = None
    refusal: str | None = None


@dataclass
class AdmissionResult:
    candidates: list[str] = field(default_factory=list)
    admitted: list[str] = field(default_factory=list)
    refusals: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RecallContext:
    """Authority context for one governed recall request.

    Domain refs are logical authority boundaries. They are not storage
    partitions and their tuple order does not imply hierarchy.
    """

    target_domain_refs: tuple[str, ...]
    principal_ref: str = ""
    project_ref: str = ""
    task_ref: str = ""
    purpose: str = ""


class GovernedMemoryAdapter:
    """Wraps a permissive substrate in the governance it does not provide."""

    def __init__(
        self,
        substrate: TemporalGraphPort,
        tenant: str,
        clock: Clock | None = None,
        selector=None,
    ) -> None:
        self._substrate = substrate
        self._tenant = tenant
        self._clock = clock or Clock()
        self._selector = selector or DeterministicSelector()
        self._ids = DeterministicIds("ref")
        self.containment_violations: list[str] = []
        self._state_version: dict[str, int] = {}
        self._disputed: set[str] = set()
        self._tombstones: dict[str, dict] = {}
        self._fact_scope: dict[str, dict] = {}
        self._shared_domain_members: dict[str, set[str]] = {}
        self.events: list[dict] = []

    # -- isolation-domain administration -------------------------------

    def set_shared_domain_members(self, domain_ref: str, members: tuple[str, ...]) -> None:
        """Replace current membership for a governed shared-memory domain.

        This is a narrow reference seam, not a complete membership service.
        Recall always consults the current set so revocation affects subsequent
        admission without rewriting the retained memory itself.
        """
        if not domain_ref:
            raise ValueError("shared domain requires a stable domain ref")
        self._shared_domain_members[domain_ref] = set(members)

    # -- write path -----------------------------------------------------

    def commit_proposal(self, proposal: policy.Proposal, fact_text: str, episode: Episode | None = None) -> CommitResult:
        correlation = self._ids.next()
        if episode is not None:
            self._substrate.add_episode(episode)
        propose_event = self._event("memory.propose", proposal.target_reference, correlation)

        decision = policy.evaluate(proposal)
        authorize_event = self._event(
            "memory.authorize",
            proposal.target_reference,
            correlation,
            causation_id=propose_event["event_id"],
            policy_version=decision.policy_version,
            authority={
                "permitted_actions": list(decision.permitted_actions),
                "prohibited_actions": list(decision.prohibited_actions),
                "selection_mode": "none",
            },
        )
        events = [propose_event, authorize_event]

        stale = self._is_stale(proposal)
        selected = self._select_action(decision, proposal, blocked_by_stale=stale)
        commits = selected == proposal.operation
        before_state = f"v{self._state_version.get(proposal.target_reference, 0)}"

        fact_uuid = None
        if commits:
            fact_uuid = self._write(proposal, fact_text)
            events.append(
                self._event(
                    "memory.commit",
                    proposal.target_reference,
                    correlation,
                    causation_id=authorize_event["event_id"],
                    policy_version=decision.policy_version,
                )
            )
        after_state = f"v{self._state_version.get(proposal.target_reference, 0)}"

        receipt_id = self._ids.next()
        receipt = receipts.build_receipt(
            receipt_id=receipt_id,
            proposal=proposal,
            decision=decision,
            selected_action=selected,
            selection_mode=self._selector.mode if selected != receipts.NO_ACTION else "none",
            timestamp=self._clock.now(),
            before_state=before_state,
            after_state=after_state,
            rollback_ref=f"recovery:{proposal.target_reference}:{before_state}" if commits else None,
        )
        pama_decision = receipts.build_pama_decision(
            proposal,
            decision,
            selected,
            self._selector.mode if selected != receipts.NO_ACTION else None,
            receipt_id,
        )
        events.append(
            self._event(
                "memory.receipt",
                proposal.target_reference,
                correlation,
                causation_id=events[-1]["event_id"],
                receipt_ref=receipt_id,
            )
        )
        self.events.extend(events)
        return CommitResult(
            decision=decision,
            pama_decision=pama_decision,
            receipt=receipt,
            events=events,
            committed=commits,
            fact_uuid=fact_uuid,
            refusal="stale_authorization" if stale else None,
        )

    def _is_stale(self, proposal: policy.Proposal) -> bool:
        """Authority binds to the state it was resolved against."""
        if not proposal.state_snapshot:
            return False
        current = f"v{self._state_version.get(proposal.target_reference, 0)}"
        return proposal.state_snapshot != current

    def _select_action(self, decision: policy.Decision, proposal: policy.Proposal, blocked_by_stale: bool) -> str:
        permitted = decision.permitted_actions
        if not permitted:
            return receipts.NO_ACTION
        if blocked_by_stale:
            return "defer" if "defer" in permitted else permitted[0]

        choice = self._selector.select(permitted, proposal.operation)
        return self._contain(permitted, choice)

    def _contain(self, permitted: tuple[str, ...], choice: str) -> str:
        """Re-check any selector's output against the envelope.

        A selector is untrusted: deterministic, stochastic, or learned, it
        proposes and does not authorize. A choice outside the permitted set is
        a containment violation, recorded and failed closed to a deferral
        rather than executed. Randomness does not create permission.
        """
        try:
            receipts.enforce_selection(permitted, choice)
        except ValueError as exc:
            self.containment_violations.append(str(exc))
            return "defer" if "defer" in permitted else permitted[0]
        return choice

    def _write(self, proposal: policy.Proposal, fact_text: str) -> str:
        uuid = self._ids.next()
        self._substrate.write_fact(
            Fact(
                uuid=uuid,
                fact_text=fact_text,
                group_id=self._tenant,
                episode_uuids=tuple(proposal.evidence_refs),
                valid_at=self._clock.now(),
                created_at=self._clock.now(),
            )
        )
        domain_refs = tuple(proposal.isolation_domain_refs) or ((proposal.scope,) if proposal.scope else (self._tenant,))
        self._fact_scope[uuid] = {
            "domain_refs": domain_refs,
            "project_ref": proposal.project_ref,
            "task_ref": proposal.task_ref,
            "purpose": proposal.purpose,
        }
        self._state_version[proposal.target_reference] = self._state_version.get(proposal.target_reference, 0) + 1
        return uuid

    # -- read path ------------------------------------------------------

    def governed_recall(self, query: str, context: RecallContext | None = None) -> AdmissionResult:
        """Retrieve candidates, then admit only what current authority allows.

        Tenant partitioning is enforced before retrieval. Logical isolation
        domains, shared-space membership, project, and task are evaluated at
        admission because the in-memory substrate is trusted to return
        same-tenant candidates for policy evaluation. Candidate presence and
        shared-space membership remain distinct from admission authority.
        """
        context = context or RecallContext(target_domain_refs=(self._tenant,))
        result = AdmissionResult()
        for fact, _score in self._substrate.search(query, group_ids=[self._tenant]):
            result.candidates.append(fact.uuid)
            refusal = self._admission_refusal(fact, context)
            if refusal:
                result.refusals[fact.uuid] = refusal
            else:
                result.admitted.append(fact.uuid)
        return result

    def _admission_refusal(self, fact: Fact, context: RecallContext) -> str | None:
        if fact.group_id != self._tenant:
            return "out_of_scope"
        if fact.uuid in self._tombstones:
            return "tombstoned"
        if fact.is_event_invalid:
            return "superseded_not_current"
        if fact.uuid in self._disputed:
            return "disputed"

        scope = self._fact_scope.get(fact.uuid)
        if scope is None:
            return None

        memory_domains = set(scope["domain_refs"])
        target_domains = set(context.target_domain_refs)
        matching_domains = memory_domains.intersection(target_domains)
        if not target_domains or not matching_domains:
            return "isolation_domain_mismatch"

        # A shared domain is still an isolation boundary. If all matching
        # routes are governed shared spaces, at least one must currently admit
        # the requesting principal as a member. Membership is necessary but
        # not sufficient; project/task/purpose gates continue below.
        shared_matches = {domain for domain in matching_domains if domain in self._shared_domain_members}
        if shared_matches == matching_domains:
            if not context.principal_ref:
                return "shared_space_membership_unresolved"
            if not any(context.principal_ref in self._shared_domain_members[domain] for domain in shared_matches):
                return "shared_space_non_member"

        memory_project = scope.get("project_ref", "")
        if memory_project and context.project_ref != memory_project:
            return "project_scope_mismatch"

        memory_task = scope.get("task_ref", "")
        if memory_task and context.task_ref != memory_task:
            return "task_scope_mismatch"

        return None

    def mark_disputed(self, fact_uuid: str) -> None:
        self._disputed.add(fact_uuid)

    # -- canonical state accessors --------------------------------------

    def state_version(self, memory_id: str) -> int:
        return self._state_version.get(memory_id, 0)

    def tombstoned_ids(self) -> set[str]:
        return {record["memory_id"] for record in self._tombstones.values()}

    def record_correction(self, memory_id: str) -> int:
        """A correction advances canonical version; dependents become stale by relation."""
        self._state_version[memory_id] = self._state_version.get(memory_id, 0) + 1
        return self._state_version[memory_id]

    # -- deletion -------------------------------------------------------

    def governed_delete(self, proposal: policy.Proposal, fact_uuid: str, derived_refs: tuple[str, ...] = ()) -> CommitResult:
        """Delete through the authority gate, leaving a tombstone the substrate cannot."""
        correlation = self._ids.next()
        decision = policy.evaluate(proposal)
        selected = self._select_action(decision, proposal, blocked_by_stale=False)
        committed = selected == proposal.operation
        before_state = f"v{self._state_version.get(proposal.target_reference, 0)}"

        if committed:
            self._tombstones[fact_uuid] = {
                "memory_id": proposal.target_reference,
                "fact_uuid": fact_uuid,
                "deleted_at": self._clock.now(),
                "declared_derived_refs": list(derived_refs),
                "mode": proposal.operation,
                "reversible": proposal.operation != "permanent_deletion",
            }
            # Pruning removes from active recall and keeps the content recoverable;
            # only permanent deletion reaches the substrate's physical delete.
            if proposal.operation == "permanent_deletion":
                self._substrate.delete_fact(fact_uuid)
            self._state_version[proposal.target_reference] = self._state_version.get(proposal.target_reference, 0) + 1

        receipt_id = self._ids.next()
        receipt = receipts.build_receipt(
            receipt_id=receipt_id,
            proposal=proposal,
            decision=decision,
            selected_action=selected,
            selection_mode=self._selector.mode if selected != receipts.NO_ACTION else "none",
            timestamp=self._clock.now(),
            before_state=before_state,
            after_state=f"v{self._state_version.get(proposal.target_reference, 0)}",
        )
        pama_decision = receipts.build_pama_decision(
            proposal, decision, selected, self._selector.mode if selected != receipts.NO_ACTION else None, receipt_id
        )
        event = self._event("memory.delete", proposal.target_reference, correlation, receipt_ref=receipt_id)
        self.events.append(event)
        return CommitResult(
            decision=decision,
            pama_decision=pama_decision,
            receipt=receipt,
            events=[event],
            committed=committed,
            fact_uuid=fact_uuid if committed else None,
        )

    def undeclared_residue(self, fact_uuid: str) -> list[str]:
        """Substrate remnants referencing a tombstoned fact that were not declared."""
        tombstone = self._tombstones.get(fact_uuid)
        if tombstone is None:
            return []
        declared = set(tombstone["declared_derived_refs"])
        remnants = [
            candidate.uuid
            for candidate in getattr(self._substrate, "all_facts", tuple)()
            if fact_uuid in candidate.episode_uuids and candidate.uuid not in declared
        ]
        return remnants

    def tombstone(self, fact_uuid: str) -> dict | None:
        return self._tombstones.get(fact_uuid)

    # -- helpers --------------------------------------------------------

    def _event(self, event_type: str, memory_id: str, correlation: str, **extra) -> dict:
        return receipts.build_audit_event(
            event_id=self._ids.next(),
            event_type=event_type,
            timestamp=self._clock.now(),
            component="governed-adapter",
            memory_id=memory_id,
            correlation_id=correlation,
            **extra,
        )
