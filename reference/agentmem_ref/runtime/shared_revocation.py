"""Shared-memory membership revocation propagation.

A shared-space membership change is current authority state, not a command to
mutate every downstream store. Membership authority must already have been
changed through ``memory.shared_membership`` before this projection helper runs.
This seam then recomputes the authority inherited by derived state.
"""

from __future__ import annotations

from dataclasses import dataclass

from .scope_governance import DerivedScope, ScopeReconciliation, SourceScope, reconcile_derived_scope


@dataclass(frozen=True)
class SharedRevocationResult:
    domain_ref: str
    revoked_principal: str
    affected_source_refs: tuple[str, ...]
    reconciliation: ScopeReconciliation


def propagate_shared_membership_revocation(
    adapter,
    *,
    domain_ref: str,
    revoked_principal: str,
    remaining_members: tuple[str, ...],
    current_derived_scope: DerivedScope,
    source_scopes: tuple[SourceScope, ...],
) -> SharedRevocationResult:
    """Recompute downstream derived authority after a governed revocation.

    This function deliberately does **not** mutate shared-domain membership.
    The membership change is an ``authority_change`` consequence owned by
    ``memory.shared_membership.commit_shared_domain_membership_change``.

    The current adapter membership must already equal ``remaining_members``;
    otherwise this helper refuses instead of making an ungoverned correction.
    Only sources actually bound to ``domain_ref`` lose the revoked principal
    from their allowed audience. Other source authority remains unchanged. The
    result reports whether the existing derived scope is still current; it does
    not silently rewrite, delete, or re-authorize the downstream object.
    """
    if not domain_ref or not revoked_principal:
        raise ValueError("shared revocation requires a domain and principal")
    if revoked_principal in remaining_members:
        raise ValueError("revoked principal cannot remain a member")

    raw_members = getattr(adapter, "_shared_domain_members", None)
    if not isinstance(raw_members, dict):
        raise TypeError("adapter does not expose shared-domain membership state")
    current_members = tuple(sorted(raw_members.get(domain_ref, ())))
    expected_members = tuple(sorted(set(remaining_members)))
    if current_members != expected_members:
        raise ValueError("shared membership authority change must be committed before propagation")

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
    )
