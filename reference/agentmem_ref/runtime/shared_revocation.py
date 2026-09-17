"""Shared-memory membership revocation propagation.

A shared-space membership change is current authority state, not a command to
mutate every downstream store. This reference seam first governs the membership
transition, then recomputes authority inherited by derived state only when the
membership change actually commits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..core import policy
from ..core.evidence_qualification import EvidenceItem
from .scope_governance import DerivedScope, ScopeReconciliation, SourceScope, reconcile_derived_scope
from .shared_membership import (
    SharedMembershipChange,
    SharedMembershipResult,
    change_shared_domain_membership,
)


@dataclass(frozen=True)
class SharedRevocationResult:
    domain_ref: str
    revoked_principal: str
    affected_source_refs: tuple[str, ...]
    reconciliation: ScopeReconciliation | None
    membership_change: SharedMembershipResult

    @property
    def committed(self) -> bool:
        return self.membership_change.committed

    @property
    def refusal(self) -> str | None:
        return self.membership_change.refusal


def propagate_shared_membership_revocation(
    adapter,
    *,
    domain_ref: str,
    revoked_principal: str,
    expected_members: tuple[str, ...],
    remaining_members: tuple[str, ...],
    current_derived_scope: DerivedScope,
    source_scopes: tuple[SourceScope, ...],
    proposal: policy.Proposal,
    evidence: Sequence[EvidenceItem],
    attestation: policy.ExternalVerification | None,
) -> SharedRevocationResult:
    """Govern membership revocation, then recompute downstream derived authority.

    Only sources actually bound to ``domain_ref`` lose the revoked principal
    from their allowed audience. Other source authority remains unchanged.
    The result reports whether the existing derived scope is still current; it
    does not silently rewrite, delete, or re-authorize the downstream object.

    If the A5 authority transition does not commit, no membership or derived
    authority consequence is applied. This prevents revocation propagation from
    remaining an unguarded alternate path around #364's membership boundary.
    """
    if not domain_ref or not revoked_principal:
        raise ValueError("shared revocation requires a domain and principal")
    if revoked_principal in remaining_members:
        raise ValueError("revoked principal cannot remain a member")
    if revoked_principal not in expected_members:
        raise ValueError("revoked principal must exist in the expected member set")

    membership = change_shared_domain_membership(
        adapter,
        SharedMembershipChange(
            domain_ref=domain_ref,
            expected_members=expected_members,
            resulting_members=remaining_members,
            reason=f"revoke {revoked_principal} from {domain_ref}",
        ),
        proposal,
        evidence=evidence,
        attestation=attestation,
    )
    if not membership.committed:
        return SharedRevocationResult(
            domain_ref=domain_ref,
            revoked_principal=revoked_principal,
            affected_source_refs=(),
            reconciliation=None,
            membership_change=membership,
        )

    updated: list[SourceScope] = []
    affected: list[str] = []
    for source in source_scopes:
        if domain_ref not in source.domain_refs:
            updated.append(source)
            continue
        affected.append(source.source_ref)
        updated.append(
            SourceScope(
                source_ref=source.source_ref,
                domain_refs=source.domain_refs,
                allowed_audiences=frozenset(
                    audience for audience in source.allowed_audiences if audience != revoked_principal
                ),
                allowed_purposes=source.allowed_purposes,
                restrictions=source.restrictions,
            )
        )

    reconciliation = reconcile_derived_scope(current_derived_scope, tuple(updated))
    return SharedRevocationResult(
        domain_ref=domain_ref,
        revoked_principal=revoked_principal,
        affected_source_refs=tuple(affected),
        reconciliation=reconciliation,
        membership_change=membership,
    )
