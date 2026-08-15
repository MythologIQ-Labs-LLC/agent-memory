"""Stateful commit seam for DashClaw-governed Agent Memory mutations.

The pure external-verdict adapter can resolve authority over the *requested*
scope, but a correction also needs authority over the scope already bound to the
logical target. ``GovernedMemoryAdapter`` intentionally keeps that scope metadata
private to its current reference runtime, so this #279 integration seam records
the scope of successful mutations it commits and fails closed when an existing
target cannot be reconstructed.

This registry is process-local by design in the current slice. Its restart-safe
persistence/reconstruction becomes part of #282 rather than being mistaken for
durable governance merely because the underlying memory substrate persists.
"""

from __future__ import annotations

from dataclasses import dataclass

from .adapter import GovernedMemoryAdapter
from .dashclaw_external_verdict import (
    AuthorityRequest,
    AuthorityResolver,
    BoundCommitResult,
    BoundMutation,
    commit_bound_mutation,
)


@dataclass(frozen=True)
class TargetScopeBinding:
    memory_id: str
    authority_request: AuthorityRequest
    authority_evidence_ref: str


class DashClawGovernedCommitter:
    """Revalidate requested and current-target scope before ordinary commit."""

    def __init__(self, memory: GovernedMemoryAdapter, authority_resolver: AuthorityResolver) -> None:
        self._memory = memory
        self._authority_resolver = authority_resolver
        self._target_scopes: dict[str, TargetScopeBinding] = {}

    def _request_for_mutation(self, mutation: BoundMutation) -> AuthorityRequest:
        proposal = mutation.proposal
        return AuthorityRequest(
            org_id=mutation.org_id,
            agent_id=mutation.agent_id,
            scope=proposal.scope,
            project_ref=proposal.project_ref,
            task_ref=proposal.task_ref,
            isolation_domain_refs=tuple(proposal.isolation_domain_refs),
            target_reference=proposal.target_reference,
        )

    @staticmethod
    def _same_scope(left: AuthorityRequest, right: AuthorityRequest) -> bool:
        return (
            left.org_id == right.org_id
            and left.scope == right.scope
            and left.project_ref == right.project_ref
            and left.task_ref == right.task_ref
            and set(left.isolation_domain_refs) == set(right.isolation_domain_refs)
            and left.target_reference == right.target_reference
        )

    def _refusal(self, mutation: BoundMutation, code: str) -> BoundCommitResult:
        return BoundCommitResult(
            committed=False,
            refusal=code,
            input_identity=mutation.input_identity,
            proposal_digest=mutation.proposal_digest,
        )

    def commit(
        self,
        mutation: BoundMutation,
        *,
        approval_ref: str | None = None,
        approval_actor_id: str | None = None,
        approved_input_identity: str | None = None,
    ) -> BoundCommitResult:
        requested = self._request_for_mutation(mutation)
        requested_resolution = self._authority_resolver(requested)
        if not requested_resolution.authorized or not requested_resolution.evidence_ref:
            return self._refusal(mutation, "requested_scope_authority_unresolved")

        memory_id = mutation.proposal.target_reference
        current_uuid = self._memory.current_fact_uuid(memory_id)
        current_binding = self._target_scopes.get(memory_id)

        if current_uuid is not None and current_binding is None:
            # Existing governed state without a reconstructable target-scope
            # binding must not be corrected merely because the new requested
            # scope is authorized. #282 will make this state durable/replayable.
            return self._refusal(mutation, "target_scope_unresolved")

        if current_binding is not None:
            current_resolution = self._authority_resolver(current_binding.authority_request)
            if not current_resolution.authorized or not current_resolution.evidence_ref:
                return self._refusal(mutation, "target_scope_authority_unresolved")

            if mutation.proposal.operation != "scope_expansion" and not self._same_scope(
                current_binding.authority_request,
                requested,
            ):
                return self._refusal(mutation, "target_scope_mismatch")

        result = commit_bound_mutation(
            self._memory,
            mutation,
            approval_ref=approval_ref,
            approval_actor_id=approval_actor_id,
            approved_input_identity=approved_input_identity,
        )
        if result.committed:
            self._target_scopes[memory_id] = TargetScopeBinding(
                memory_id=memory_id,
                authority_request=requested,
                authority_evidence_ref=requested_resolution.evidence_ref,
            )
        return result

    def target_scope_binding(self, memory_id: str) -> TargetScopeBinding | None:
        """Return the current process-local binding for evidence/tests only."""
        return self._target_scopes.get(memory_id)
