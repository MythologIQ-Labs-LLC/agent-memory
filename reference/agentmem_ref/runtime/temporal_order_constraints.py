"""Bounded pairwise temporal-order constraints for explicit-current recall (#584).

This module does not retrieve, admit, refuse, supersede, or mutate memories. It
operates only on candidates that have already crossed canonical governed recall
admission. Its purpose is deliberately narrower than a global temporal tier:

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
  by a stable topological sort rather than a global temporal tier.

``ExplicitCurrentConstrainedRankingPolicy`` is policy 3.1.2's drop-in extension of
the 3.1.1 post-admission ranker. It deliberately remains a frozen dataclass so the
repository's benchmark variant machinery can continue using ``dataclasses.replace``
across every active planner.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
from typing import Any, Callable, Iterable, Mapping, Sequence

from .proposition_semantics import (
    CONFLICT,
    STATE_CHANGE_CANDIDATE,
    WRITE_SEMANTICS_KEY,
)
from .cross_fact_currentness import CROSS_FACT_BASIS, CROSS_FACT_LABEL
from .ranking_policy import PostAdmissionRankingPolicy, temporal_applicability, typed_temporal_evidence
from .temporal_intent import (
    CALLER_DECLARED,
    CURRENT,
    EXPLICIT,
    QUERY_LANGUAGE_EXPLICIT,
    TemporalIntent,
)

UNKNOWN_TEMPORAL_BASIS = "unknown_temporal_basis"
APPLICABLE = "applicable"
# The active multi-route policy version (identity.ranking.active_policy_version): 3.3.0 adds
# #671 read-path cross-fact currentness; 3.4.0 (#732 R4) admits typed-proposition relations
# to that evidence under assertion filter 6.1.0. The 3.2.0 class keeps its own constant, so an
# instance constructed without cross-fact evidence still reports 3.2.0.
CONSTRAINED_POLICY_VERSION = "3.2.0"
POLICY_VERSION = "3.4.0"
UNKNOWN_BASIS_POLICY = "explicit_current_exclusive_pairwise_v1"
CROSS_FACT_POLICY = "explicit_current_interpreted_cross_fact_v1"

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
    counter allocated and therefore encode write order. Only deterministic presentation
    differences in case and whitespace are normalized; punctuation and word order remain
    significant, so this helper does not pretend to be semantic equivalence.
    """

    text = getattr(fact, "fact_text", "") or ""
    normalized = " ".join(str(text).casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def explicit_current_residual_key(candidate_ref: str, fact: Any, intent: TemporalIntent) -> tuple[str, str] | None:
    """Time-neutral residual key for the explicit-current profile.

    Candidate ref is only the second component. It can distinguish truly identical
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


def apply_pairwise_constraints(
    base_order: Iterable[str],
    edges: Sequence[TemporalConstraintEdge],
) -> ConstrainedOrderResult:
    """Apply acyclic edges with a stable topological sort over the base ranking.

    The base ranking is the priority order for every candidate not currently blocked by
    a #584 edge. A loser is delayed only until its required winner has been emitted;
    unrelated candidates that were already ahead of that winner remain ahead. This is
    the minimal-order-disturbance interpretation of a pairwise constraint and avoids
    turning one exclusive competition into a global temporal tier.
    """

    base = list(dict.fromkeys(base_order))
    active = tuple(
        edge for edge in edges
        if edge.winner in base and edge.loser in base and edge.winner != edge.loser
    )
    if not active:
        return ConstrainedOrderResult(tuple(base), (), False, "no_eligible_exclusive_competition")

    position = {ref: index for index, ref in enumerate(base)}
    adjacency: dict[str, set[str]] = {ref: set() for ref in base}
    indegree = dict.fromkeys(base, 0)
    for edge in active:
        if edge.loser in adjacency[edge.winner]:
            continue
        adjacency[edge.winner].add(edge.loser)
        indegree[edge.loser] += 1

    ready = [ref for ref in base if indegree[ref] == 0]
    ordered: list[str] = []
    while ready:
        ready.sort(key=lambda ref: position[ref])
        ref = ready.pop(0)
        ordered.append(ref)
        for target in sorted(adjacency[ref], key=lambda item: position[item]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)

    if len(ordered) != len(base):
        return ConstrainedOrderResult(
            tuple(base), active, False, "cyclic_or_contradictory_competition_evidence"
        )
    return ConstrainedOrderResult(tuple(ordered), active, True, None)


@dataclass(frozen=True)
class ExplicitCurrentConstrainedRankingPolicy(PostAdmissionRankingPolicy):
    """Policy 3.2.0: 3.1.1 ranking plus bounded explicit-current constraints.

    3.2.0 (#669) adds ordering-subordinate routes (``subordinate_routes``): they add
    candidates but order only after every temporal stage, and admitted-set lexical
    statistics exclude candidates found only by them. With no subordinate route hit the
    ordering is exactly 3.1.2's.

    Outside the explicit-current profile this class delegates entirely to the existing
    post-admission ranker. Inside the profile it performs two post-order operations:

    1. within groups tied on every pre-temporal stage, replace only the positions occupied
       by unknown-temporal-basis candidates with a stable content-identity order so the
       runtime transaction clock cannot decide unknown-vs-unknown currentness;
    2. apply persisted typed exclusive same-slot applicable-over-unknown edges using the
       stable topological policy above.

    Neither operation changes admission, truth, lifecycle state, or authority.
    """

    version: str = CONSTRAINED_POLICY_VERSION
    unknown_basis_policy: str = UNKNOWN_BASIS_POLICY

    def stage_names(self) -> list[str]:
        return [
            *super().stage_names(),
            "explicit_current_unknown_tie_content_identity",
            "explicit_current_exclusive_pairwise_constraints",
        ]

    def identity(self) -> dict[str, Any]:
        identity = super().identity()
        identity.update(
            unknown_basis_policy=self.unknown_basis_policy,
            explicit_current_constraint_profile="caller_declared_or_query_language_explicit",
            exclusive_competition_evidence=(
                "persisted_state_change_candidate",
                "persisted_conflict",
            ),
            global_applicable_over_unknown_tier=False,
            authority_effect="none",
        )
        return identity

    def _pre_temporal_key(self, record: Mapping[str, Any], intent: TemporalIntent) -> tuple[Any, ...]:
        """Return all ordinary stages before temporal tie ordering/fallback."""

        values: list[Any] = []
        for name, value in super().keyed_stages(record, intent):
            if name in {"temporal_order_within_query_regime", "temporal_evidence:newer_first"}:
                break
            if name in {"candidate_ref_neutral_digest", "candidate_ref_asc"}:
                break
            if name.startswith("route_score_desc_subordinate:"):
                break
            values.append(value)
        return tuple(values)

    def _neutralize_unknown_ties(
        self,
        ordered: Sequence[str],
        evidence: Mapping[str, Mapping[str, Any]],
        facts: Mapping[str, Any],
        intent: TemporalIntent,
    ) -> tuple[list[str], set[str]]:
        """Remove hidden write-clock preference only among genuine relevance ties."""

        neutral = list(ordered)
        groups: dict[tuple[Any, ...], list[str]] = {}
        for ref in ordered:
            groups.setdefault(self._pre_temporal_key(evidence[ref], intent), []).append(ref)

        affected: set[str] = set()
        for refs in groups.values():
            unknown = [
                ref for ref in refs
                if evidence[ref].get("temporal_applicability") == UNKNOWN_TEMPORAL_BASIS
            ]
            if len(unknown) < 2:
                continue
            positions = sorted(neutral.index(ref) for ref in unknown)
            stable = sorted(
                unknown,
                key=lambda ref: explicit_current_residual_key(ref, facts[ref], intent),
            )
            before = [neutral[position] for position in positions]
            for position, ref in zip(positions, stable):
                neutral[position] = ref
            if before != stable:
                affected.update(unknown)
        return neutral, affected

    @staticmethod
    def _edge_map(edges: Sequence[TemporalConstraintEdge]) -> dict[str, list[TemporalConstraintEdge]]:
        by_ref: dict[str, list[TemporalConstraintEdge]] = {}
        for edge in edges:
            by_ref.setdefault(edge.winner, []).append(edge)
            by_ref.setdefault(edge.loser, []).append(edge)
        return by_ref

    def rank(
        self,
        admitted: Iterable[str],
        hits_by_candidate: Mapping[str, Sequence[Any]],
        fact_lookup: Callable[[str], Any],
        query: str = "",
        intent: TemporalIntent | None = None,
    ) -> tuple[list[str], dict[str, dict[str, Any]]]:
        intent = intent or TemporalIntent()
        admitted = list(admitted)
        base_order, evidence = super().rank(
            admitted,
            hits_by_candidate,
            fact_lookup,
            query=query,
            intent=intent,
        )
        if not explicit_current_profile(intent):
            return base_order, evidence

        facts = {ref: fact_lookup(ref) for ref in admitted}
        base_position = {ref: index + 1 for index, ref in enumerate(base_order)}
        base_next = {
            ref: base_order[index + 1] if index + 1 < len(base_order) else None
            for index, ref in enumerate(base_order)
        }
        base_reason = {
            ref: evidence[ref].get("ordered_before_next_by")
            for ref in base_order
        }

        neutral_order, neutralized_refs = self._neutralize_unknown_ties(
            base_order, evidence, facts, intent
        )
        edges = build_explicit_current_constraints(facts, evidence, intent)
        constrained = apply_pairwise_constraints(neutral_order, edges)
        final_order = list(constrained.ordered)
        edge_by_ref = self._edge_map(edges)
        direct_edges = {(edge.winner, edge.loser) for edge in edges}

        for position, ref in enumerate(final_order, start=1):
            record = evidence[ref]
            record["base_rank_position"] = base_position[ref]
            record["rank_position"] = position
            record["unknown_basis_policy"] = self.unknown_basis_policy
            record["query_intent_basis"] = intent.intent_basis
            record["explicit_current_unknown_tie_fallback"] = (
                "stable_content_digest" if ref in neutralized_refs else "not_exercised"
            )
            record["constraint_applied"] = bool(
                constrained.constraint_applied and edge_by_ref.get(ref)
            )
            record["constraint_refusal_reason"] = (
                constrained.constraint_refusal_reason
                if not constrained.constraint_applied and edges
                else None if edge_by_ref.get(ref)
                else "not_in_exclusive_competition"
            )
            record["constraint_edges"] = [edge.to_dict() for edge in edge_by_ref.get(ref, ())]
            if edge_by_ref.get(ref):
                first = edge_by_ref[ref][0]
                record["competition_slot"] = first.slot
                record["competition_basis"] = first.basis
                record["winner_temporal_applicability"] = first.winner_temporal_applicability
                record["loser_temporal_applicability"] = first.loser_temporal_applicability
                record["winner_applicability_basis"] = first.winner_applicability_basis
            record["authority_effect"] = "none"
            record.pop("ordered_before_next_by", None)

        for index, ref in enumerate(final_order[:-1]):
            successor = final_order[index + 1]
            record = evidence[ref]
            if (ref, successor) in direct_edges and constrained.constraint_applied:
                reason = "explicit_current_exclusive_pairwise_constraint"
            elif ref in neutralized_refs or successor in neutralized_refs:
                reason = "explicit_current_unknown_tie_content_identity"
            elif base_next.get(ref) == successor:
                reason = base_reason.get(ref) or "base_ranking_preserved"
            else:
                reason = "stable_constraint_topology"
            record["ordered_before_next_by"] = reason

        return final_order, evidence


_CROSS_FACT_DECISIONS: ContextVar[dict[str, dict[str, Any]] | None] = ContextVar("cross_fact_decisions", default=None)


@dataclass(frozen=True)
class ExplicitCurrentCrossFactRankingPolicy(ExplicitCurrentConstrainedRankingPolicy):
    """Policy 3.4.0 (#671 Option A; #732 R4): 3.2.0 plus read-path cross-fact currentness.

    ``rank(..., cross_fact=...)`` takes the adapter's guarded evidence
    (``GovernedMemoryAdapter.cross_fact_applicability``). A target T is limited only when its
    own label is ``unknown_temporal_basis`` and at least one accepted source S is also unknown
    (where S is applicable the #584 pairwise rule already governs). A limited T is labelled
    ``limited_by_cross_fact_state_change`` (basis ``interpreted_cross_fact``), which the
    existing ``temporal_applicability_tier`` stage demotes for current intent only. No stage
    is added, admission is unchanged, and with no cross-fact evidence the ranking and every
    evidence field equal 3.2.0's apart from the policy identity. 3.4.0 changes only the
    evidence it is given: typed-proposition relations may pass the guards (assertion filter
    6.1.0); the ranking stages are 3.3.0's.
    """

    version: str = POLICY_VERSION
    cross_fact_policy: str = CROSS_FACT_POLICY

    def identity(self) -> dict[str, Any]:
        identity = super().identity()
        identity["cross_fact_policy"] = self.cross_fact_policy
        return identity

    def evidence(self, candidate_ref: str, hits: Sequence[Any], fact: Any, intent: TemporalIntent | None = None) -> dict[str, Any]:
        record = super().evidence(candidate_ref, hits, fact, intent)
        decision = (_CROSS_FACT_DECISIONS.get() or {}).get(candidate_ref)
        if decision is not None:
            if decision.get("limited"):
                record["temporal_applicability"] = CROSS_FACT_LABEL
                record["temporal_applicability_basis"] = CROSS_FACT_BASIS
                record["cross_fact_limitation"] = [dict(item) for item in decision["limited"]]
            else:
                record["cross_fact_refusal_reason"] = decision["refusal"]
        return record

    def rank(
        self,
        admitted: Iterable[str],
        hits_by_candidate: Mapping[str, Sequence[Any]],
        fact_lookup: Callable[[str], Any],
        query: str = "",
        intent: TemporalIntent | None = None,
        cross_fact: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> tuple[list[str], dict[str, dict[str, Any]]]:
        intent = intent or TemporalIntent()
        admitted = list(admitted)
        decisions: dict[str, dict[str, Any]] = {}
        if cross_fact:
            labels = {ref: temporal_applicability(intent, typed_temporal_evidence(fact_lookup(ref))) for ref in admitted}
            for target, record in cross_fact.items():
                if target not in labels:
                    continue
                accepted = list(record.get("accepted") or ())
                if not accepted:
                    decisions[target] = {"refusal": record.get("refusal")}
                elif labels[target] != UNKNOWN_TEMPORAL_BASIS:
                    decisions[target] = {"refusal": "target_has_temporal_basis"}
                else:
                    # single pass: a source's own pre-cross-fact label decides its eligibility
                    usable = [item for item in accepted if labels.get(item["source_fact_uuid"]) == UNKNOWN_TEMPORAL_BASIS]
                    decisions[target] = {"limited": usable} if usable else {"refusal": "source_has_temporal_basis"}
        token = _CROSS_FACT_DECISIONS.set(decisions)
        try:
            return super().rank(admitted, hits_by_candidate, fact_lookup, query=query, intent=intent)
        finally:
            _CROSS_FACT_DECISIONS.reset(token)


__all__ = [
    "APPLICABLE",
    "ConstrainedOrderResult",
    "CROSS_FACT_POLICY",
    "ExplicitCurrentConstrainedRankingPolicy",
    "ExplicitCurrentCrossFactRankingPolicy",
    "POLICY_VERSION",
    "TemporalConstraintEdge",
    "UNKNOWN_BASIS_POLICY",
    "UNKNOWN_TEMPORAL_BASIS",
    "apply_pairwise_constraints",
    "build_explicit_current_constraints",
    "content_identity_digest",
    "explicit_current_profile",
    "explicit_current_residual_key",
]
