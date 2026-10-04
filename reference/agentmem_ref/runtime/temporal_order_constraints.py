"""Bounded pairwise temporal-order constraints for explicit-current recall (#584).

This module does not retrieve, admit, refuse, supersede, or mutate memories.  It
operates only on candidates that have already crossed canonical governed recall
admission.  Its purpose is deliberately narrower than a global temporal tier:

* only explicit ``current`` intent activates the profile;
* only persisted #550 exclusive same-slot relation evidence can create a dominance
  edge;
* only an affirmatively applicable candidate may dominate an unknown-temporal-basis
  competitor;
* unknown remains admitted and remains labelled unknown;
* coexistence, hierarchy, unresolved cardinality, untrusted change evidence, and
  unrelated propositions create no edge;
* contradictory/cyclic edges refuse the whole #584 constraint set;
* the caller supplies the ordinary base ranking and unconstrained order is preserved
  as far as possible by promoting winners rather than globally tiering losers.

The helpers are provider-neutral and authority-neutral.  They are separated from the
ranking policy so the constrained-order contract can be falsified independently before
policy 3.1.2 integrates it.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping, Sequence

from .proposition_semantics import (
    CONFLICT,
    STATE_CHANGE_CANDIDATE,
    WRITE_SEMANTICS_KEY,
)
from .temporal_intent import (
    CALLER_DECLARED,
    CURRENT,
    EXPLICIT,
    QUERY_LANGUAGE_EXPLICIT,
    TemporalIntent,
)

UNKNOWN_TEMPORAL_BASIS = "unknown_temporal_basis"
APPLICABLE = "applicable"

_ALLOWED_INTENT_BASES = frozenset({CALLER_DECLARED, QUERY_LANGUAGE_EXPLICIT})
_EXCLUSIVE_RELATION_CLASSES = frozenset({STATE_CHANGE_CANDIDATE, CONFLICT})


@dataclass(frozen=True)
class TemporalConstraintEdge:
    """One authority-neutral ordering constraint between two admitted fact UUIDs."""

    winner: str
    loser: str
    slot: str
    classification: str
    basis: str
    winner_temporal_applicability: str
    loser_temporal_applicability: str
    winner_applicability_basis: str | None = None
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner": self.winner,
            "loser": self.loser,
            "competition_slot": self.slot,
            "competition_classification": self.classification,
            "competition_basis": self.basis,
            "winner_temporal_applicability": self.winner_temporal_applicability,
            "loser_temporal_applicability": self.loser_temporal_applicability,
            "winner_applicability_basis": self.winner_applicability_basis,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class ConstrainedOrderResult:
    """Inspectable result of applying a bounded #584 constraint set."""

    ordered: tuple[str, ...]
    edges: tuple[TemporalConstraintEdge, ...]
    constraint_applied: bool
    constraint_refusal_reason: str | None
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ordered": list(self.ordered),
            "edges": [edge.to_dict() for edge in self.edges],
            "constraint_applied": self.constraint_applied,
            "constraint_refusal_reason": self.constraint_refusal_reason,
            "authority_effect": self.authority_effect,
        }


def explicit_current_profile(intent: TemporalIntent) -> bool:
    """True only for the first #584 activation profile.

    High-confidence inferred current intent remains outside this profile even though it
    may order temporally under the older ranking policy.
    """

    return (
        intent.mode == CURRENT
        and intent.posture == EXPLICIT
        and intent.intent_basis in _ALLOWED_INTENT_BASES
    )


def content_identity_digest(fact: Any) -> str:
    """Stable, time-neutral exact-content identity for a true residual tie.

    The digest intentionally does not use candidate/fact UUID because runtime UUIDs are
    counter allocated and therefore encode write order.  Only deterministic presentation
    differences in case and whitespace are normalized; punctuation and word order remain
    significant, so this helper does not pretend to be semantic equivalence.
    """

    text = getattr(fact, "fact_text", "") or ""
    normalized = " ".join(str(text).casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def explicit_current_residual_key(candidate_ref: str, fact: Any, intent: TemporalIntent) -> tuple[str, str] | None:
    """Time-neutral residual key for the explicit-current profile.

    Candidate ref is only the second component.  It can distinguish truly identical
    content, where either order is semantically equivalent, but cannot choose between
    distinguishable memories merely because one was written later.
    """

    if not explicit_current_profile(intent):
        return None
    return content_identity_digest(fact), hashlib.sha256(candidate_ref.encode("utf-8")).hexdigest()


def _persisted_semantics(fact: Any) -> Mapping[str, Any]:
    attributes = getattr(fact, "attributes", None) or {}
    if not isinstance(attributes, Mapping):
        return {}
    semantics = attributes.get(WRITE_SEMANTICS_KEY) or {}
    return semantics if isinstance(semantics, Mapping) else {}


def _exclusive_relation(classification: str, basis: str) -> bool:
    """Accept only #550 relation forms that positively establish exclusivity.

    Classification is necessary but the basis is also pinned so a future classifier
    cannot silently widen #584 by reusing a class name for a weaker relation.
    """

    if classification not in _EXCLUSIVE_RELATION_CLASSES:
        return False
    if classification == CONFLICT:
        return basis == "single_valued_without_change_evidence"
    return basis == "single_valued_replacement_marker" or basis.startswith("explicit_termination:")


def build_explicit_current_constraints(
    facts: Mapping[str, Any],
    ranking_evidence: Mapping[str, Mapping[str, Any]],
    intent: TemporalIntent,
) -> tuple[TemporalConstraintEdge, ...]:
    """Build bounded applicable-over-unknown edges from persisted #550 evidence only."""

    if not explicit_current_profile(intent):
        return ()

    dedup: dict[tuple[str, str], TemporalConstraintEdge] = {}
    admitted = set(facts)
    for source_ref in sorted(facts):
        semantics = _persisted_semantics(facts[source_ref])
        relations = semantics.get("relations") or ()
        if not isinstance(relations, (list, tuple)):
            continue
        for relation in relations:
            if not isinstance(relation, Mapping):
                continue
            other_ref = str(relation.get("other_fact_uuid") or "")
            if not other_ref or other_ref == source_ref or other_ref not in admitted:
                continue
            classification = str(relation.get("classification") or "")
            basis = str(relation.get("basis") or "")
            if not _exclusive_relation(classification, basis):
                continue

            source_evidence = ranking_evidence.get(source_ref) or {}
            other_evidence = ranking_evidence.get(other_ref) or {}
            source_app = str(source_evidence.get("temporal_applicability") or "")
            other_app = str(other_evidence.get("temporal_applicability") or "")
            source_basis = source_evidence.get("temporal_applicability_basis")
            other_basis = other_evidence.get("temporal_applicability_basis")

            if source_app == APPLICABLE and other_app == UNKNOWN_TEMPORAL_BASIS:
                winner, loser = source_ref, other_ref
                winner_basis = str(source_basis) if source_basis is not None else None
            elif other_app == APPLICABLE and source_app == UNKNOWN_TEMPORAL_BASIS:
                winner, loser = other_ref, source_ref
                winner_basis = str(other_basis) if other_basis is not None else None
            else:
                continue

            edge = TemporalConstraintEdge(
                winner=winner,
                loser=loser,
                slot=str(relation.get("slot") or ""),
                classification=classification,
                basis=basis,
                winner_temporal_applicability=APPLICABLE,
                loser_temporal_applicability=UNKNOWN_TEMPORAL_BASIS,
                winner_applicability_basis=winner_basis,
            )
            key = (winner, loser)
            previous = dedup.get(key)
            if previous is None or (edge.classification, edge.basis, edge.slot) < (
                previous.classification,
                previous.basis,
                previous.slot,
            ):
                dedup[key] = edge

    return tuple(dedup[key] for key in sorted(dedup))


def _has_cycle(nodes: Sequence[str], edges: Sequence[TemporalConstraintEdge]) -> bool:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    indegree = dict.fromkeys(nodes, 0)
    for edge in edges:
        if edge.winner not in adjacency or edge.loser not in adjacency:
            continue
        if edge.loser in adjacency[edge.winner]:
            continue
        adjacency[edge.winner].add(edge.loser)
        indegree[edge.loser] += 1
    ready = [node for node in nodes if indegree[node] == 0]
    seen = 0
    while ready:
        node = ready.pop()
        seen += 1
        for target in adjacency[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return seen != len(nodes)


def apply_pairwise_constraints(
    base_order: Iterable[str],
    edges: Sequence[TemporalConstraintEdge],
) -> ConstrainedOrderResult:
    """Apply acyclic edges while preserving base order by promoting winners.

    Unlike a global applicability tier, this algorithm never demotes every unknown
    candidate.  When a required winner currently trails its paired loser, only the
    winner is moved to immediately precede that loser.  Unrelated candidates therefore
    retain the base order unless a winner must cross them to satisfy an explicit edge.
    """

    ordered = list(dict.fromkeys(base_order))
    active = tuple(
        edge for edge in edges
        if edge.winner in ordered and edge.loser in ordered and edge.winner != edge.loser
    )
    if not active:
        return ConstrainedOrderResult(tuple(ordered), (), False, "no_eligible_exclusive_competition")
    if _has_cycle(ordered, active):
        return ConstrainedOrderResult(
            tuple(ordered), active, False, "cyclic_or_contradictory_competition_evidence"
        )

    # A DAG converges under repeated winner promotion.  Sort the edge scan by original
    # base positions for deterministic minimal disturbance; repeat because promoting one
    # winner may expose another previously satisfied dependency in a chain.
    base_position = {ref: index for index, ref in enumerate(ordered)}
    scan = sorted(active, key=lambda edge: (
        base_position[edge.loser],
        base_position[edge.winner],
        edge.winner,
        edge.loser,
    ))
    limit = max(1, len(ordered) * len(scan) + 1)
    for _ in range(limit):
        changed = False
        for edge in scan:
            winner_index = ordered.index(edge.winner)
            loser_index = ordered.index(edge.loser)
            if winner_index < loser_index:
                continue
            winner = ordered.pop(winner_index)
            loser_index = ordered.index(edge.loser)
            ordered.insert(loser_index, winner)
            changed = True
        if not changed:
            return ConstrainedOrderResult(tuple(ordered), active, True, None)

    # Defensive refusal.  The explicit cycle check above should make this unreachable,
    # but preserving the base order is safer than inventing a recency/identifier escape.
    return ConstrainedOrderResult(
        tuple(dict.fromkeys(base_order)),
        active,
        False,
        "constraint_application_did_not_converge",
    )


__all__ = [
    "APPLICABLE",
    "ConstrainedOrderResult",
    "TemporalConstraintEdge",
    "UNKNOWN_TEMPORAL_BASIS",
    "apply_pairwise_constraints",
    "build_explicit_current_constraints",
    "content_identity_digest",
    "explicit_current_profile",
    "explicit_current_residual_key",
]
