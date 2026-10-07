"""Provider-neutral recall control for the Agent Memory RC runtime.

A controller may choose candidate-generation routes and bounded work, but its
output is retrieval evidence only. It cannot create scope, currentness, privacy,
or authority and cannot bypass governed recall admission.

Issue #456 adds native semantic/vector retrieval. Issue #461 adds native typed
graph traversal over canonical relations. Similarity, graph proximity, path
weights, and relation density remain non-authoritative candidate evidence.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from typing import Any, Mapping, Protocol

from .adapter import RecallContext, eligible_search
from .contextual_recall_adapter import admission_mode_for_intent, admit_preselected_candidates
from .temporal_intent import resolve_intent
from .temporal_order_constraints import ExplicitCurrentCrossFactRankingPolicy
from .restart_runtime import RuntimeRecoveryError
from .runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    MultiRouteRecallResult,
    RetrievalRouteHit,
)
from .vector_retrieval import NativeVectorCandidateRetriever, SEMANTIC_VECTOR_ROUTE
from ..state.substrate import (
    EvidenceNeighborTemporalGraphPort,
    TypedRelation,
    TypedRelationTemporalGraphPort,
)


DETERMINISTIC_CONTROLLER_REF = "agent-memory:deterministic-recall-controller"
DETERMINISTIC_CONTROLLER_VERSION = "1.2.0"
ADAPTIVE_CONTROLLER_VERSION = "2.0.0"
ADAPTIVE_ABLATION_PROFILES = (
    "controller_off",
    "adaptive_routing_only",
    "adaptive_budgeting_only",
    "adaptive_stopping_only",
    "combined_controller",
)
TYPED_GRAPH_ROUTE = "typed_graph"
GRAPH_OUTGOING = "outgoing"
GRAPH_INCOMING = "incoming"
GRAPH_BOTH = "both"
MAX_GRAPH_SEED_REFS = 16

# Pre-existing route precedence of the controlled planner, now declared rather than implicit.
CONTROLLED_RECALL_RANKING_POLICY = ExplicitCurrentCrossFactRankingPolicy(
    policy_id="controlled-multi-route",
    route_score_order=(SEMANTIC_VECTOR_ROUTE, TYPED_GRAPH_ROUTE, LEXICAL_ROUTE, SHARED_EVIDENCE_ROUTE),
    exact_identity_route=EXACT_IDENTITY_ROUTE,
    lexical_route=LEXICAL_ROUTE,
    lexical_relevance="bm25_admitted_set",
)

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
        "did", "do", "does", "for", "from", "had", "has", "have", "he",
        "her", "hers", "him", "his", "how", "i", "in", "into", "is", "it",
        "its", "me", "my", "of", "on", "or", "our", "ours", "she", "that",
        "the", "their", "theirs", "them", "they", "this", "to", "was", "we",
        "were", "what", "when", "where", "which", "who", "why", "with", "you",
        "your", "yours",
    }
)


def _content_terms(text: str) -> set[str]:
    return {term for term in _WORD.findall(text.lower()) if term not in _STOPWORDS}


def _content_overlap(query: str, fact_text: str) -> int:
    return len(_content_terms(query).intersection(_content_terms(fact_text)))


@dataclass(frozen=True)
class GraphTraversalSpec:
    """Deterministic work and semantics contract for one typed-graph route."""

    max_depth: int = 2
    max_fanout: int = 8
    relation_types: tuple[str, ...] = ()
    direction: str = GRAPH_OUTGOING
    min_path_score: float = 0.0
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.max_depth < 1:
            raise ValueError("graph traversal max_depth must be >= 1")
        if self.max_fanout < 1:
            raise ValueError("graph traversal max_fanout must be >= 1")
        if self.direction not in (GRAPH_OUTGOING, GRAPH_INCOMING, GRAPH_BOTH):
            raise ValueError("unsupported graph traversal direction")
        if not math.isfinite(self.min_path_score):
            raise ValueError("graph traversal min_path_score must be finite")
        if self.min_path_score < 0.0 or self.min_path_score > 1.0:
            raise ValueError("graph traversal min_path_score must be between 0 and 1")
        if any(not relation_type for relation_type in self.relation_types):
            raise ValueError("graph traversal relation types must be non-empty strings")
        if len(self.relation_types) != len(set(self.relation_types)):
            raise ValueError("graph traversal relation types must be unique")
        if self.authority_effect != "none":
            raise ValueError("graph traversal cannot have authority effect")


@dataclass(frozen=True)
class GraphCandidateHit:
    """One deterministic best path from a seed to a candidate fact."""

    candidate_ref: str
    seed_candidate_ref: str
    path_score: float
    path_refs: tuple[str, ...]
    relation_ids: tuple[str, ...]
    relation_types: tuple[str, ...]
    relation_evidence_refs: tuple[str, ...]
    relation_weights: tuple[float, ...]
    hop_count: int
    currentness_basis: str = "governed_recall_admission"
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if not self.candidate_ref or not self.seed_candidate_ref:
            raise ValueError("graph candidate and seed references are required")
        if not math.isfinite(self.path_score):
            raise ValueError("graph path score must be finite")
        if self.path_score < 0.0 or self.path_score > 1.0:
            raise ValueError("graph path score must be between 0 and 1")
        if self.hop_count < 1:
            raise ValueError("graph candidate hop_count must be >= 1")
        if len(self.path_refs) != self.hop_count + 1:
            raise ValueError("graph candidate path length does not match hop_count")
        if len(self.relation_ids) != self.hop_count:
            raise ValueError("graph candidate relation path does not match hop_count")
        if len(self.relation_types) != self.hop_count:
            raise ValueError("graph candidate relation types do not match hop_count")
        if len(self.relation_weights) != self.hop_count:
            raise ValueError("graph candidate relation weights do not match hop_count")
        if self.path_refs[0] != self.seed_candidate_ref:
            raise ValueError("graph candidate path must start at the seed")
        if self.path_refs[-1] != self.candidate_ref:
            raise ValueError("graph candidate path must end at the candidate")
        if self.authority_effect != "none":
            raise ValueError("graph candidate hits cannot have authority effect")


class NativeTypedGraphCandidateRetriever:
    """Bounded deterministic traversal over Agent Memory canonical relations.

    Relation group filtering is applied during expansion as containment and work
    control. Fact-level scope, isolation, currentness, dispute, and tombstone
    checks remain at governed recall admission.
    """

    def __init__(self, spec: GraphTraversalSpec | None = None) -> None:
        self.spec = spec or GraphTraversalSpec()

    def available_for(self, substrate: object) -> bool:
        return isinstance(substrate, TypedRelationTemporalGraphPort)

    def search(
        self,
        substrate: TypedRelationTemporalGraphPort,
        seed_refs: tuple[str, ...],
        *,
        group_id: str,
        candidate_limit: int,
    ) -> list[GraphCandidateHit]:
        if candidate_limit < 0:
            raise ValueError("graph candidate_limit must be non-negative")
        if candidate_limit == 0 or not seed_refs:
            return []
        if not self.available_for(substrate):
            raise ValueError("substrate does not support native typed relations")

        best_by_candidate: dict[str, GraphCandidateHit] = {}
        for seed_ref in tuple(dict.fromkeys(seed_refs)):
            if substrate.get_fact(seed_ref) is None:
                continue
            for hit in self._traverse_seed(substrate, seed_ref, group_id=group_id):
                existing = best_by_candidate.get(hit.candidate_ref)
                if existing is None or self._hit_key(hit) < self._hit_key(existing):
                    best_by_candidate[hit.candidate_ref] = hit

        ordered = sorted(best_by_candidate.values(), key=self._hit_key)
        return ordered[:candidate_limit]

    def _traverse_seed(
        self,
        substrate: TypedRelationTemporalGraphPort,
        seed_ref: str,
        *,
        group_id: str,
    ) -> list[GraphCandidateHit]:
        queue = deque(
            [
                (
                    seed_ref,
                    (seed_ref,),
                    tuple(),
                    tuple(),
                    tuple(),
                    tuple(),
                    1.0,
                )
            ]
        )
        best_score_by_node = {seed_ref: 1.0}
        hits: list[GraphCandidateHit] = []
        relation_filter = self.spec.relation_types or None

        while queue:
            (
                node_ref,
                path_refs,
                relation_ids,
                relation_types,
                relation_evidence,
                relation_weights,
                path_score,
            ) = queue.popleft()
            depth = len(relation_ids)
            if depth >= self.spec.max_depth:
                continue

            neighbors = self._neighbors(
                substrate,
                node_ref,
                group_id=group_id,
                relation_types=relation_filter,
            )
            for next_ref, relation in neighbors[: self.spec.max_fanout]:
                if next_ref in path_refs:
                    continue
                if relation.is_event_invalid or relation.is_transaction_expired:
                    continue
                next_score = path_score * relation.retrieval_weight
                if next_score < self.spec.min_path_score:
                    continue
                if substrate.get_fact(next_ref) is None:
                    continue
                prior_score = best_score_by_node.get(next_ref)
                if prior_score is not None and next_score <= prior_score:
                    continue
                best_score_by_node[next_ref] = next_score

                next_path = path_refs + (next_ref,)
                next_relation_ids = relation_ids + (relation.relation_id,)
                next_relation_types = relation_types + (relation.relation_type,)
                next_evidence = tuple(
                    dict.fromkeys(relation_evidence + tuple(relation.evidence_refs))
                )
                next_weights = relation_weights + (relation.retrieval_weight,)
                hit = GraphCandidateHit(
                    candidate_ref=next_ref,
                    seed_candidate_ref=seed_ref,
                    path_score=next_score,
                    path_refs=next_path,
                    relation_ids=next_relation_ids,
                    relation_types=next_relation_types,
                    relation_evidence_refs=next_evidence,
                    relation_weights=next_weights,
                    hop_count=len(next_relation_ids),
                )
                hits.append(hit)
                queue.append(
                    (
                        next_ref,
                        next_path,
                        next_relation_ids,
                        next_relation_types,
                        next_evidence,
                        next_weights,
                        next_score,
                    )
                )

        return hits

    def _neighbors(
        self,
        substrate: TypedRelationTemporalGraphPort,
        node_ref: str,
        *,
        group_id: str,
        relation_types: tuple[str, ...] | None,
    ) -> list[tuple[str, TypedRelation]]:
        values: dict[tuple[str, str], tuple[str, TypedRelation]] = {}
        if self.spec.direction in (GRAPH_OUTGOING, GRAPH_BOTH):
            for relation in substrate.relations_from(
                node_ref,
                group_ids=[group_id],
                relation_types=relation_types,
            ):
                values[(relation.relation_id, relation.target_uuid)] = (
                    relation.target_uuid,
                    relation,
                )
        if self.spec.direction in (GRAPH_INCOMING, GRAPH_BOTH):
            for relation in substrate.relations_to(
                node_ref,
                group_ids=[group_id],
                relation_types=relation_types,
            ):
                values[(relation.relation_id, relation.source_uuid)] = (
                    relation.source_uuid,
                    relation,
                )
        return sorted(
            values.values(),
            key=lambda item: (
                -item[1].retrieval_weight,
                item[1].relation_type,
                item[0],
                item[1].relation_id,
            ),
        )

    @staticmethod
    def _hit_key(hit: GraphCandidateHit) -> tuple[object, ...]:
        return (
            -hit.path_score,
            hit.hop_count,
            hit.candidate_ref,
            hit.seed_candidate_ref,
            hit.relation_ids,
        )


@dataclass(frozen=True)
class RecallRouteBudget:
    """Controller-selected work budget for one retrieval route."""

    route_id: str
    candidate_limit: int
    anchor_limit: int = 0

    def __post_init__(self) -> None:
        if not self.route_id:
            raise ValueError("route budget requires a route_id")
        for name in ("candidate_limit", "anchor_limit"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.anchor_limit > self.candidate_limit:
            raise ValueError("anchor_limit cannot exceed candidate_limit")


@dataclass(frozen=True)
class RecallControlPlan:
    """Non-authoritative route-selection result emitted by a recall controller."""

    controller_ref: str
    controller_version: str
    route_budgets: tuple[RecallRouteBudget, ...]
    evidence_sufficiency_target: int = 1
    reason_codes: tuple[str, ...] = ()
    input_projection_ref: str = "query_and_route_availability_v1"
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if not self.controller_ref or not self.controller_version:
            raise ValueError("controller identity and version are required")
        if self.evidence_sufficiency_target < 1:
            raise ValueError("evidence_sufficiency_target must be >= 1")
        if self.authority_effect != "none":
            raise ValueError("recall controller output cannot have authority effect")
        route_ids = [budget.route_id for budget in self.route_budgets]
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("recall control plan contains duplicate route budgets")

    def budget_for(self, route_id: str) -> RecallRouteBudget:
        for budget in self.route_budgets:
            if budget.route_id == route_id:
                return budget
        return RecallRouteBudget(route_id=route_id, candidate_limit=0)

    def to_dict(self) -> dict[str, object]:
        return {
            "controller_ref": self.controller_ref,
            "controller_version": self.controller_version,
            "route_budgets": [
                {
                    "route_id": budget.route_id,
                    "candidate_limit": budget.candidate_limit,
                    "anchor_limit": budget.anchor_limit,
                }
                for budget in self.route_budgets
            ],
            "evidence_sufficiency_target": self.evidence_sufficiency_target,
            "reason_codes": list(self.reason_codes),
            "input_projection_ref": self.input_projection_ref,
            "authority_effect": self.authority_effect,
        }



ADAPTIVE_ROUTE_ORDER = (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SEMANTIC_VECTOR_ROUTE,
    TYPED_GRAPH_ROUTE,
    SHARED_EVIDENCE_ROUTE,
)
STOP_RECOMMENDATIONS = frozenset(
    {
        "evidence_sufficient",
        "further_retrieval_unhelpful",
        "continue_retrieval",
        "budget_exhausted",
        "frontier_exhausted",
        "controller_unavailable",
        "abstain",
    }
)


def _probability(value: float, *, field_name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be a finite probability between 0 and 1")
    return value


def _non_negative_int(value: int, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


@dataclass(frozen=True)
class RecallOuterBudget:
    """Host-owned outer budget for one controller request (#644 T-controller-2)."""

    maximum_controller_decisions: int = 4
    maximum_candidates: int = 64
    deadline_ms: int | None = None
    maximum_nodes: int | None = None
    maximum_edges: int | None = None
    maximum_depth: int | None = None

    def __post_init__(self) -> None:
        _non_negative_int(self.maximum_controller_decisions, field_name="maximum_controller_decisions")
        _non_negative_int(self.maximum_candidates, field_name="maximum_candidates")
        for name in ("deadline_ms", "maximum_nodes", "maximum_edges", "maximum_depth"):
            value = getattr(self, name)
            if value is not None:
                _non_negative_int(value, field_name=name)

    def to_dict(self) -> dict[str, int | None]:
        return {
            "maximum_controller_decisions": self.maximum_controller_decisions,
            "maximum_candidates": self.maximum_candidates,
            "deadline_ms": self.deadline_ms,
            "maximum_nodes": self.maximum_nodes,
            "maximum_edges": self.maximum_edges,
            "maximum_depth": self.maximum_depth,
        }


@dataclass(frozen=True)
class RecallRouteNeed:
    """Typed route-usefulness evidence. Probability is evidence, never permission."""

    route_id: str
    probability: float
    basis: tuple[str, ...] = ()
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if not self.route_id:
            raise ValueError("route need requires a route_id")
        object.__setattr__(self, "probability", _probability(self.probability, field_name="route need"))
        if self.authority_effect != "none":
            raise ValueError("route need cannot have authority effect")

    def to_dict(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "probability": self.probability,
            "basis": list(self.basis),
            "authority_effect": "none",
        }


@dataclass(frozen=True)
class EvidenceAssessment:
    """Four independent System-One evidence propositions from the frozen contract."""

    evidence_sufficient: float
    continue_useful: float
    missing_evidence: float
    contradiction: float
    basis: tuple[str, ...] = ()
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        for name in (
            "evidence_sufficient",
            "continue_useful",
            "missing_evidence",
            "contradiction",
        ):
            object.__setattr__(
                self,
                name,
                _probability(getattr(self, name), field_name=name),
            )
        if self.authority_effect != "none":
            raise ValueError("evidence assessment cannot have authority effect")

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_sufficient": self.evidence_sufficient,
            "continue_useful": self.continue_useful,
            "missing_evidence": self.missing_evidence,
            "contradiction": self.contradiction,
            "basis": list(self.basis),
            "authority_effect": "none",
        }


@dataclass(frozen=True)
class AdaptiveControlDecision:
    """One inspectable adaptive-control decision, still non-authoritative."""

    route_needs: tuple[RecallRouteNeed, ...]
    route_budgets: tuple[RecallRouteBudget, ...]
    assessment: EvidenceAssessment
    stop_recommendation: str
    ablation_profile: str = "combined_controller"
    controller_ref: str = DETERMINISTIC_CONTROLLER_REF
    controller_version: str = ADAPTIVE_CONTROLLER_VERSION
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.stop_recommendation not in STOP_RECOMMENDATIONS:
            raise ValueError("unsupported stop recommendation")
        if self.ablation_profile not in ADAPTIVE_ABLATION_PROFILES:
            raise ValueError("unsupported controller ablation profile")
        if self.authority_effect != "none":
            raise ValueError("adaptive control decision cannot have authority effect")
        routes = [item.route_id for item in self.route_needs]
        if len(routes) != len(set(routes)):
            raise ValueError("adaptive control decision contains duplicate route needs")
        budget_routes = [item.route_id for item in self.route_budgets]
        if len(budget_routes) != len(set(budget_routes)):
            raise ValueError("adaptive control decision contains duplicate route budgets")
        if set(budget_routes) != set(routes):
            raise ValueError("adaptive control decision route budgets must match route needs")

    def to_dict(self) -> dict[str, object]:
        return {
            "controller_identity": {
                "backend_ref": self.controller_ref,
                "backend_version": self.controller_version,
                "model_or_policy_ref": "deterministic-adaptive-rule-policy",
            },
            "route_needs": {
                item.route_id: {
                    "probability": item.probability,
                    "basis": list(item.basis),
                }
                for item in self.route_needs
            },
            "route_budgets": [
                {
                    "route_id": item.route_id,
                    "candidate_limit": item.candidate_limit,
                    "anchor_limit": item.anchor_limit,
                }
                for item in self.route_budgets
            ],
            "evidence_assessment": self.assessment.to_dict(),
            "stop_recommendation": self.stop_recommendation,
            "ablation_profile": self.ablation_profile,
            "authority_effect": "none",
        }


def estimate_route_needs(
    query: str,
    *,
    logical_memory_refs: tuple[str, ...],
    available_routes: tuple[str, ...],
) -> tuple[RecallRouteNeed, ...]:
    """Deterministic boundary-valued route evidence.

    Values are intentionally 0.0/1.0 until calibration evidence exists. Calling
    them 0.73 because it looks more statistical would be theatre, not evidence.
    """

    terms = _content_terms(query)
    identities = tuple(dict.fromkeys(logical_memory_refs))
    available = set(available_routes)
    unknown = available.difference(ADAPTIVE_ROUTE_ORDER)
    if unknown:
        raise ValueError("route need input contains unsupported routes: " + ", ".join(sorted(unknown)))

    needs: list[RecallRouteNeed] = []
    for route in ADAPTIVE_ROUTE_ORDER:
        if route not in available:
            continue
        if route == EXACT_IDENTITY_ROUTE:
            active, basis = bool(identities), ("explicit_identity_seed",) if identities else ("no_identity_seed",)
        elif route in (LEXICAL_ROUTE, SEMANTIC_VECTOR_ROUTE):
            active, basis = bool(terms), ("content_query",) if terms else ("no_content_terms",)
        elif route == TYPED_GRAPH_ROUTE:
            active, basis = bool(identities), ("identity_seed_for_graph",) if identities else ("no_graph_seed",)
        else:
            active = bool(terms or identities)
            basis = ("content_or_identity_seed",) if active else ("no_relational_seed",)
        needs.append(RecallRouteNeed(route, 1.0 if active else 0.0, basis))
    return tuple(needs)


def allocate_route_budgets(
    route_needs: tuple[RecallRouteNeed, ...],
    *,
    outer_budget: RecallOuterBudget,
    host_caps: Mapping[str, int],
    minimum_allocation: int = 1,
) -> tuple[RecallRouteBudget, ...]:
    """Allocate one bounded total candidate budget by deterministic largest remainder."""

    if minimum_allocation < 0:
        raise ValueError("minimum_allocation must be non-negative")
    needs_by_route = {item.route_id: item for item in route_needs}
    if len(needs_by_route) != len(route_needs):
        raise ValueError("duplicate route need")
    unsupported = set(needs_by_route).difference(host_caps)
    if unsupported:
        raise ValueError("route need has no host cap: " + ", ".join(sorted(unsupported)))
    for route, cap in host_caps.items():
        _non_negative_int(cap, field_name=f"host cap for {route}")

    active = [
        route
        for route in ADAPTIVE_ROUTE_ORDER
        if route in needs_by_route
        and needs_by_route[route].probability > 0.0
        and host_caps.get(route, 0) > 0
    ]
    allocations = {route: 0 for route in needs_by_route}
    remaining = outer_budget.maximum_candidates

    if minimum_allocation:
        for route in active:
            if remaining <= 0:
                break
            grant = min(minimum_allocation, host_caps[route], remaining)
            allocations[route] += grant
            remaining -= grant

    while remaining > 0:
        eligible = [route for route in active if allocations[route] < host_caps[route]]
        if not eligible:
            break
        total_weight = sum(needs_by_route[route].probability for route in eligible)
        if total_weight <= 0.0:
            break

        ideal = {
            route: remaining * needs_by_route[route].probability / total_weight
            for route in eligible
        }
        progressed = 0
        for route in eligible:
            floor_share = int(math.floor(ideal[route]))
            if floor_share <= 0:
                continue
            grant = min(floor_share, host_caps[route] - allocations[route], remaining)
            allocations[route] += grant
            remaining -= grant
            progressed += grant
            if remaining <= 0:
                break
        if remaining <= 0:
            break

        eligible = [route for route in active if allocations[route] < host_caps[route]]
        if not eligible:
            break
        if progressed == 0:
            route = min(
                eligible,
                key=lambda candidate: (
                    -(ideal.get(candidate, 0.0) - math.floor(ideal.get(candidate, 0.0))),
                    ADAPTIVE_ROUTE_ORDER.index(candidate),
                ),
            )
            allocations[route] += 1
            remaining -= 1

    budgets: list[RecallRouteBudget] = []
    for route in ADAPTIVE_ROUTE_ORDER:
        if route not in needs_by_route:
            continue
        candidate_limit = allocations[route]
        anchor_limit = 0
        if route == SHARED_EVIDENCE_ROUTE and candidate_limit:
            anchor_limit = min(3, candidate_limit)
        budgets.append(RecallRouteBudget(route, candidate_limit, anchor_limit=anchor_limit))
    return tuple(budgets)


def assess_evidence(
    *,
    candidate_count: int,
    exact_identity_count: int = 0,
    corroborated_count: int = 0,
    routes_remaining: int = 0,
    resource_exhausted: bool = False,
    contradiction_detected: bool = False,
    sufficiency_target: int = 1,
) -> EvidenceAssessment:
    """Conservative deterministic four-way evidence assessment.

    Sufficiency requires identity evidence or independent-route corroboration.
    Candidate quantity alone never means sufficient.
    """

    for name, value in (
        ("candidate_count", candidate_count),
        ("exact_identity_count", exact_identity_count),
        ("corroborated_count", corroborated_count),
        ("routes_remaining", routes_remaining),
    ):
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
    if sufficiency_target < 1:
        raise ValueError("sufficiency_target must be >= 1")

    sufficient = (
        exact_identity_count >= sufficiency_target
        or corroborated_count >= sufficiency_target
    )
    missing = candidate_count < sufficiency_target
    continue_useful = (not sufficient) and routes_remaining > 0 and not resource_exhausted
    basis: list[str] = []
    if exact_identity_count >= sufficiency_target:
        basis.append("exact_identity_target_met")
    if corroborated_count >= sufficiency_target:
        basis.append("independent_route_corroboration_target_met")
    if missing:
        basis.append("candidate_target_missing")
    if routes_remaining:
        basis.append("routes_remaining")
    if resource_exhausted:
        basis.append("resource_exhausted")
    if contradiction_detected:
        basis.append("contradiction_detected")
    return EvidenceAssessment(
        evidence_sufficient=1.0 if sufficient else 0.0,
        continue_useful=1.0 if continue_useful else 0.0,
        missing_evidence=1.0 if missing else 0.0,
        contradiction=1.0 if contradiction_detected else 0.0,
        basis=tuple(basis),
    )


def stop_recommendation(
    assessment: EvidenceAssessment,
    *,
    routes_remaining: int,
    resource_exhausted: bool,
) -> str:
    """Map independent evidence propositions to one contract stop recommendation."""

    if resource_exhausted:
        return "budget_exhausted"
    if assessment.evidence_sufficient == 1.0:
        return "evidence_sufficient"
    if assessment.continue_useful == 1.0 and routes_remaining > 0:
        return "continue_retrieval"
    if routes_remaining <= 0 and assessment.missing_evidence == 1.0:
        return "frontier_exhausted"
    if routes_remaining <= 0:
        return "further_retrieval_unhelpful"
    return "abstain"


def adaptive_cache_key(
    *,
    operation: str,
    canonical_request_state: Mapping[str, Any],
    controller_contract_version: str,
    backend_ref: str,
    backend_version: str,
    model_or_policy_ref: str,
    host_policy_version: str,
    isolation_namespace: str,
) -> str:
    """Version/scope-bound key for derived controller evidence."""

    required = (
        operation,
        controller_contract_version,
        backend_ref,
        backend_version,
        model_or_policy_ref,
        host_policy_version,
        isolation_namespace,
    )
    if any(not value for value in required):
        raise ValueError("adaptive cache identity fields must be non-empty")
    material = {
        "operation": operation,
        "canonical_request_state": canonical_request_state,
        "controller_contract_version": controller_contract_version,
        "backend_ref": backend_ref,
        "backend_version": backend_version,
        "model_or_policy_ref": model_or_policy_ref,
        "host_policy_version": host_policy_version,
        "isolation_namespace": isolation_namespace,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class ControllerDecisionCache:
    """Process-local cache of non-authoritative controller evidence."""

    def __init__(self) -> None:
        self._values: dict[str, AdaptiveControlDecision] = {}

    def get(self, key: str) -> AdaptiveControlDecision | None:
        return self._values.get(key)

    def put(self, key: str, decision: AdaptiveControlDecision) -> None:
        if not key:
            raise ValueError("controller cache key is required")
        if decision.authority_effect != "none":
            raise ValueError("controller cache cannot store authoritative decisions")
        self._values[key] = decision

    def __len__(self) -> int:
        return len(self._values)


class DeterministicAdaptiveRecallController:
    """Deterministic T-controller-2 estimator baseline.

    This class computes bounded evidence and recommendations. It does not execute
    retrieval or grant recall admission.
    """

    controller_ref = DETERMINISTIC_CONTROLLER_REF
    controller_version = ADAPTIVE_CONTROLLER_VERSION

    def decide(
        self,
        query: str,
        *,
        logical_memory_refs: tuple[str, ...],
        available_routes: tuple[str, ...],
        outer_budget: RecallOuterBudget,
        host_caps: Mapping[str, int],
        candidate_count: int = 0,
        exact_identity_count: int = 0,
        corroborated_count: int = 0,
        routes_remaining: int | None = None,
        resource_exhausted: bool = False,
        contradiction_detected: bool = False,
        ablation_profile: str = "combined_controller",
    ) -> AdaptiveControlDecision:
        if ablation_profile not in ADAPTIVE_ABLATION_PROFILES:
            raise ValueError("unsupported controller ablation profile")
        needs = estimate_route_needs(
            query,
            logical_memory_refs=logical_memory_refs,
            available_routes=available_routes,
        )
        if routes_remaining is None:
            routes_remaining = sum(item.probability > 0.0 for item in needs)

        if ablation_profile in ("controller_off", "adaptive_stopping_only"):
            # No adaptive route/budget selection. Host caps are copied, then outer-clamped
            # deterministically so the evidence object still obeys the request budget.
            neutral_needs = tuple(
                RecallRouteNeed(item.route_id, 1.0 if host_caps.get(item.route_id, 0) else 0.0, ("host_available",))
                for item in needs
            )
            budgets = allocate_route_budgets(
                neutral_needs,
                outer_budget=outer_budget,
                host_caps=host_caps,
            )
        else:
            budgets = allocate_route_budgets(
                needs,
                outer_budget=outer_budget,
                host_caps=host_caps,
            )

        assessment = assess_evidence(
            candidate_count=candidate_count,
            exact_identity_count=exact_identity_count,
            corroborated_count=corroborated_count,
            routes_remaining=routes_remaining,
            resource_exhausted=resource_exhausted,
            contradiction_detected=contradiction_detected,
        )
        recommendation = (
            "abstain"
            if ablation_profile in ("controller_off", "adaptive_routing_only", "adaptive_budgeting_only")
            else stop_recommendation(
                assessment,
                routes_remaining=routes_remaining,
                resource_exhausted=resource_exhausted,
            )
        )
        return AdaptiveControlDecision(
            route_needs=needs,
            route_budgets=budgets,
            assessment=assessment,
            stop_recommendation=recommendation,
            ablation_profile=ablation_profile,
        )


class RecallController(Protocol):
    """Estimator/controller contract. Implementations own no recall authority."""

    def plan(
        self,
        query: str,
        *,
        logical_memory_refs: tuple[str, ...],
        available_routes: tuple[str, ...],
    ) -> RecallControlPlan: ...


class DeterministicRecallController:
    """Small deterministic System-One control baseline for RC evaluation."""

    def plan(
        self,
        query: str,
        *,
        logical_memory_refs: tuple[str, ...],
        available_routes: tuple[str, ...],
    ) -> RecallControlPlan:
        terms = _content_terms(query)
        unique_refs = tuple(dict.fromkeys(logical_memory_refs))
        available = set(available_routes)

        lexical_limit = 0
        if LEXICAL_ROUTE in available and terms:
            lexical_limit = min(32, max(8, len(terms) * 4))

        exact_limit = 0
        if EXACT_IDENTITY_ROUTE in available and unique_refs:
            exact_limit = min(16, len(unique_refs))

        vector_limit = 0
        if SEMANTIC_VECTOR_ROUTE in available and terms:
            vector_limit = min(24, max(8, len(terms) * 4))

        graph_limit = 0
        if TYPED_GRAPH_ROUTE in available and unique_refs:
            graph_limit = min(24, max(4, len(unique_refs) * 8))

        shared_candidate_limit = 0
        shared_anchor_limit = 0
        if SHARED_EVIDENCE_ROUTE in available and (terms or unique_refs):
            shared_anchor_limit = 1 if len(terms) <= 4 else 3
            shared_candidate_limit = min(
                24,
                max(4, len(terms) * 2 + exact_limit * 2),
            )

        reason_codes: list[str] = []
        if terms:
            reason_codes.append("content_query")
        else:
            reason_codes.append("no_content_terms")
        if unique_refs:
            reason_codes.append("explicit_identity_seed")
        if vector_limit:
            reason_codes.append("bounded_semantic_vector_search")
        if graph_limit:
            reason_codes.append("bounded_typed_graph_traversal")
        if shared_candidate_limit:
            reason_codes.append("bounded_relational_expansion")

        target = 1 if len(terms) <= 4 else 3
        budgets = tuple(
            budget
            for budget in (
                RecallRouteBudget(LEXICAL_ROUTE, lexical_limit),
                RecallRouteBudget(EXACT_IDENTITY_ROUTE, exact_limit),
                RecallRouteBudget(SEMANTIC_VECTOR_ROUTE, vector_limit),
                RecallRouteBudget(TYPED_GRAPH_ROUTE, graph_limit),
                RecallRouteBudget(
                    SHARED_EVIDENCE_ROUTE,
                    shared_candidate_limit,
                    anchor_limit=shared_anchor_limit,
                ),
            )
            if budget.route_id in available
        )
        return RecallControlPlan(
            controller_ref=DETERMINISTIC_CONTROLLER_REF,
            controller_version=DETERMINISTIC_CONTROLLER_VERSION,
            route_budgets=budgets,
            evidence_sufficiency_target=target,
            reason_codes=tuple(reason_codes),
        )


@dataclass
class ControlledRecallResult:
    """Recall result plus the exact non-authoritative control decision used."""

    plan: RecallControlPlan
    recall: MultiRouteRecallResult
    route_candidate_counts: dict[str, int]
    evidence_sufficiency_met: bool
    stop_reason: str
    graph_candidate_hits: dict[str, GraphCandidateHit] = field(default_factory=dict)
    controller_calls: int = 1
    authority_effect: str = "none"

    @property
    def ranked_admitted(self) -> list[str]:
        return self.recall.ranked_admitted

    @property
    def admitted(self) -> list[str]:
        return self.recall.admitted

    @property
    def candidates(self) -> list[str]:
        return self.recall.candidates


class ControlledRecallPlanner:
    """Execute controller-selected route budgets, then one governed admission pass."""

    def __init__(
        self,
        adapter,
        *,
        controller: RecallController | None = None,
        vector_retriever: NativeVectorCandidateRetriever | None = None,
        graph_retriever: NativeTypedGraphCandidateRetriever | None = None,
    ) -> None:
        self.adapter = adapter
        self.controller = controller or DeterministicRecallController()
        self.vector_retriever = vector_retriever
        self.graph_retriever = graph_retriever
        substrate_reader = getattr(adapter, "checkpoint_substrate", None)
        tenant_reader = getattr(adapter, "checkpoint_tenant", None)
        if not callable(substrate_reader) or not callable(tenant_reader):
            raise RuntimeRecoveryError(
                "controlled recall requires the restart-safe adapter substrate/tenant contract"
            )

    def recall(
        self,
        query: str,
        context: RecallContext,
        *,
        logical_memory_refs: tuple[str, ...] = (),
        temporal_intent=None,
    ) -> ControlledRecallResult:
        substrate = self.adapter.checkpoint_substrate()
        tenant = self.adapter.checkpoint_tenant()
        unique_logical_refs = tuple(dict.fromkeys(logical_memory_refs))
        available_routes = [LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE]
        if self.vector_retriever is not None and self.vector_retriever.available_for(substrate):
            available_routes.append(SEMANTIC_VECTOR_ROUTE)
        if self.graph_retriever is not None and self.graph_retriever.available_for(substrate):
            available_routes.append(TYPED_GRAPH_ROUTE)
        if isinstance(substrate, EvidenceNeighborTemporalGraphPort):
            available_routes.append(SHARED_EVIDENCE_ROUTE)

        plan = self.controller.plan(
            query,
            logical_memory_refs=logical_memory_refs,
            available_routes=tuple(available_routes),
        )
        self._validate_plan(plan, tuple(available_routes))

        hits: list[RetrievalRouteHit] = []
        route_counts = {route_id: 0 for route_id in available_routes}
        graph_candidate_hits: dict[str, GraphCandidateHit] = {}

        lexical_budget = plan.budget_for(LEXICAL_ROUTE)
        lexical_results = list(eligible_search(
            substrate, query, tenant, lambda fact: self.adapter.domain_eligible(fact, context),
            lambda uuid, group_id: self.adapter.domain_eligible_identity(uuid, group_id, context),
        ))
        if lexical_budget.candidate_limit:
            lexical_results = lexical_results[: lexical_budget.candidate_limit]
            for fact, score in lexical_results:
                hits.append(
                    RetrievalRouteHit(
                        route_id=LEXICAL_ROUTE,
                        candidate_ref=fact.uuid,
                        raw_score=float(score),
                    )
                )
            route_counts[LEXICAL_ROUTE] = len(lexical_results)
        else:
            lexical_results = []

        exact_budget = plan.budget_for(EXACT_IDENTITY_ROUTE)
        explicit_seeds: list[tuple[str, str]] = []
        if exact_budget.candidate_limit:
            for logical_ref in unique_logical_refs[: exact_budget.candidate_limit]:
                current = self.adapter.current_fact_uuid(logical_ref)
                if current is None:
                    continue
                hits.append(
                    RetrievalRouteHit(
                        route_id=EXACT_IDENTITY_ROUTE,
                        candidate_ref=current,
                        raw_score=1.0,
                        logical_memory_ref=logical_ref,
                    )
                )
                explicit_seeds.append((logical_ref, current))
            route_counts[EXACT_IDENTITY_ROUTE] = len(explicit_seeds)

        vector_budget = plan.budget_for(SEMANTIC_VECTOR_ROUTE)
        if (
            self.vector_retriever is not None
            and vector_budget.candidate_limit
            and self.vector_retriever.available_for(substrate)
        ):
            vector_results = self.vector_retriever.search(
                substrate,
                query,
                group_id=tenant,
                candidate_limit=vector_budget.candidate_limit,
                # The same domain-eligibility prefilter the lexical route receives
                # (docs/44: "not optional per request"); #644 T-controller S6.
                eligible=lambda fact: self.adapter.domain_eligible(fact, context),
            )
            for vector_hit in vector_results:
                hits.append(
                    RetrievalRouteHit(
                        route_id=SEMANTIC_VECTOR_ROUTE,
                        candidate_ref=vector_hit.candidate_ref,
                        raw_score=vector_hit.similarity,
                        representation_ref=vector_hit.representation_ref,
                        representation_version=vector_hit.representation_version,
                        representation_config_digest=vector_hit.representation_config_digest,
                        vector_dimension=vector_hit.vector_dimension,
                        similarity_metric=vector_hit.similarity_metric,
                        currentness_basis=vector_hit.currentness_basis,
                    )
                )
            route_counts[SEMANTIC_VECTOR_ROUTE] = len(vector_results)

        graph_budget = plan.budget_for(TYPED_GRAPH_ROUTE)
        if (
            self.graph_retriever is not None
            and graph_budget.candidate_limit
            and self.graph_retriever.available_for(substrate)
        ):
            graph_seed_refs: list[str] = []
            graph_seed_limit = min(MAX_GRAPH_SEED_REFS, graph_budget.candidate_limit)
            for logical_ref in unique_logical_refs[:graph_seed_limit]:
                current = self.adapter.current_fact_uuid(logical_ref)
                if current is not None:
                    graph_seed_refs.append(current)
            graph_results = self.graph_retriever.search(
                substrate,
                tuple(graph_seed_refs),
                group_id=tenant,
                candidate_limit=graph_budget.candidate_limit,
            )
            for graph_hit in graph_results:
                graph_candidate_hits[graph_hit.candidate_ref] = graph_hit
                hits.append(
                    RetrievalRouteHit(
                        route_id=TYPED_GRAPH_ROUTE,
                        candidate_ref=graph_hit.candidate_ref,
                        raw_score=graph_hit.path_score,
                        seed_candidate_ref=graph_hit.seed_candidate_ref,
                        shared_evidence_refs=graph_hit.relation_evidence_refs,
                        currentness_basis=graph_hit.currentness_basis,
                    )
                )
            route_counts[TYPED_GRAPH_ROUTE] = len(graph_results)

        shared_budget = plan.budget_for(SHARED_EVIDENCE_ROUTE)
        if (
            isinstance(substrate, EvidenceNeighborTemporalGraphPort)
            and shared_budget.candidate_limit
        ):
            remaining = shared_budget.candidate_limit
            expanded_seeds: set[str] = set()

            for logical_ref, seed_ref in explicit_seeds:
                if remaining <= 0:
                    break
                added = self._expand_seed(
                    substrate,
                    tenant,
                    hits,
                    seed_ref=seed_ref,
                    logical_memory_ref=logical_ref,
                    expanded_seeds=expanded_seeds,
                    candidate_limit=remaining,
                )
                remaining -= added

            ranked_anchors: list[tuple[int, float, object]] = []
            for fact, raw_score in lexical_results:
                if fact.uuid in expanded_seeds:
                    continue
                if fact.is_event_invalid or fact.is_transaction_expired:
                    continue
                overlap = _content_overlap(query, fact.fact_text)
                if overlap <= 0:
                    continue
                ranked_anchors.append((overlap, float(raw_score), fact))
            ranked_anchors.sort(key=lambda item: (-item[0], -item[1], item[2].uuid))

            for _overlap, _raw_score, fact in ranked_anchors[: shared_budget.anchor_limit]:
                if remaining <= 0:
                    break
                added = self._expand_seed(
                    substrate,
                    tenant,
                    hits,
                    seed_ref=fact.uuid,
                    logical_memory_ref="",
                    expanded_seeds=expanded_seeds,
                    candidate_limit=remaining,
                )
                remaining -= added
            route_counts[SHARED_EVIDENCE_ROUTE] = shared_budget.candidate_limit - remaining

        by_candidate: dict[str, list[RetrievalRouteHit]] = {}
        ordered_candidates: list[str] = []
        for hit in hits:
            if hit.candidate_ref not in by_candidate:
                by_candidate[hit.candidate_ref] = []
                ordered_candidates.append(hit.candidate_ref)
            by_candidate[hit.candidate_ref].append(hit)

        intent = resolve_intent(query, temporal_intent)
        admission_mode, historical_target = admission_mode_for_intent(intent)
        admission = admit_preselected_candidates(
            self.adapter,
            ordered_candidates,
            context,
            query_label=query,
            admission_mode=admission_mode,
            historical_target_seconds=historical_target,
        )
        ranked, ranking_evidence = CONTROLLED_RECALL_RANKING_POLICY.rank(
            admission.admitted,
            by_candidate,
            substrate.get_fact,
            query=query,
            intent=intent,
            # #671: guarded cross-fact currentness evidence (empty outside explicit-current intent)
            cross_fact=self.adapter.cross_fact_applicability(admission.admitted, intent),
        )
        routes_executed = tuple(
            budget.route_id
            for budget in plan.route_budgets
            if budget.candidate_limit > 0
        )
        recall = MultiRouteRecallResult(
            query=query,
            routes_executed=routes_executed,
            candidates=list(admission.candidates),
            admitted=list(admission.admitted),
            refusals=dict(admission.refusals),
            decisions=dict(admission.decisions),
            route_hits={ref: hits for ref, hits in by_candidate.items() if ref in admission.candidates},
            ranked_admitted=ranked,
            policy_version=admission.policy_version,
            evaluated_at=admission.evaluated_at,
            ranking_policy=CONTROLLED_RECALL_RANKING_POLICY.identity(),
            ranking_evidence=ranking_evidence,
            candidate_policy=dict(admission.candidate_policy),
            admission_mode=admission.admission_mode,
            admission_basis=dict(admission.admission_basis),
            query_temporal_intent=intent.to_dict(),
        )
        sufficient = len(ranked) >= plan.evidence_sufficiency_target
        return ControlledRecallResult(
            plan=plan,
            recall=recall,
            route_candidate_counts=route_counts,
            evidence_sufficiency_met=sufficient,
            stop_reason=(
                "evidence_target_met" if sufficient else "planned_routes_exhausted"
            ),
            graph_candidate_hits=graph_candidate_hits,
        )

    @staticmethod
    def _validate_plan(plan: RecallControlPlan, available_routes: tuple[str, ...]) -> None:
        if plan.authority_effect != "none":
            raise RuntimeRecoveryError("recall controller attempted to claim authority")
        unsupported = {
            budget.route_id
            for budget in plan.route_budgets
            if budget.route_id not in available_routes
        }
        if unsupported:
            raise RuntimeRecoveryError(
                "recall controller selected unavailable routes: "
                + ", ".join(sorted(unsupported))
            )

    @staticmethod
    def _expand_seed(
        substrate: EvidenceNeighborTemporalGraphPort,
        tenant: str,
        hits: list[RetrievalRouteHit],
        *,
        seed_ref: str,
        logical_memory_ref: str,
        expanded_seeds: set[str],
        candidate_limit: int,
    ) -> int:
        if seed_ref in expanded_seeds or candidate_limit <= 0:
            return 0
        seed_fact = substrate.get_fact(seed_ref)
        if seed_fact is None or seed_fact.is_event_invalid or seed_fact.is_transaction_expired:
            return 0
        expanded_seeds.add(seed_ref)
        added = 0
        for fact, shared_refs, score in substrate.evidence_neighbors(
            seed_ref,
            group_ids=[tenant],
        ):
            if added >= candidate_limit:
                break
            hits.append(
                RetrievalRouteHit(
                    route_id=SHARED_EVIDENCE_ROUTE,
                    candidate_ref=fact.uuid,
                    raw_score=float(score),
                    logical_memory_ref=logical_memory_ref,
                    seed_candidate_ref=seed_ref,
                    shared_evidence_refs=tuple(shared_refs),
                )
            )
            added += 1
        return added


# Shadow recall control (#644 T-controller, docs/plan-644-t-controller.md) ---------------
#
# The controller plans beside the unchanged default planner. Nothing here reaches candidate
# generation, admission or ranking: the report describes what the controller *proposed* and
# what the default planner *actually did*, in the frozen System-One controller contract's
# vocabulary (reference/fixtures/runtime/system-one-controller-contract-v1.json).

SYSTEM_ONE_CONTRACT_VERSION = "1.0.0"
SHADOW_STOP_CLASSES = {
    "no_evidence": "search_space",
    "frontier_exhausted": "search_space",
    "max_candidates": "resource",
}


def shadow_actual_stop(route_counts: dict[str, int], host_caps: dict[str, int], candidate_count: int) -> dict[str, object]:
    """The default planner's actual stop, never the controller's (plan S3).

    ``no_evidence`` when nothing was found; ``max_candidates`` when a host-capped route
    returned exactly its cap (a bound that binds is a resource stop, conservatively also
    when exactly ``cap`` facts qualified); ``frontier_exhausted`` otherwise. No quality
    class is ever reported: nothing decided on quality.
    """

    if candidate_count == 0:
        reason = "no_evidence"
    elif any(route_counts.get(route, 0) >= cap for route, cap in host_caps.items()):
        reason = "max_candidates"
    else:
        reason = "frontier_exhausted"
    return {
        "actual_stop_reason": reason,
        "stop_class": SHADOW_STOP_CLASSES[reason],
        "controller_recommendation": "abstain",
        "budget_state": {"host_caps": dict(sorted(host_caps.items()))},
    }


def shadow_control_report(
    *,
    controller: RecallController,
    query: str,
    logical_memory_refs: tuple[str, ...],
    available_routes: tuple[str, ...],
    routes_executed: tuple[str, ...],
    route_counts: dict[str, int],
    host_caps: dict[str, int],
    candidate_count: int,
    policy_context: dict[str, str],
    clock=None,
) -> dict[str, object]:
    """Plan once in shadow and report proposal beside execution (plan S2-S4).

    A controller failure has no effect on recall: it is reported in ``decision_status``
    and ``fallback_events`` only, and the stop record still describes the default planner.
    """

    import time

    clock = clock or time.perf_counter
    started = clock()
    plan: RecallControlPlan | None = None
    decision_status = "complete"
    fallback_events: list[str] = []
    try:
        plan = controller.plan(query, logical_memory_refs=logical_memory_refs, available_routes=available_routes)
        if not isinstance(plan, RecallControlPlan):
            raise TypeError("controller returned a non-plan")
        ControlledRecallPlanner._validate_plan(plan, available_routes)
    except (RuntimeRecoveryError, ValueError, TypeError):
        plan, decision_status = None, "invalid_response"
        fallback_events.append("controller_failure_no_effect")
    except Exception:  # noqa: BLE001 - any other controller fault is "unavailable", never a recall failure
        plan, decision_status = None, "unavailable"
        fallback_events.append("controller_failure_no_effect")
    elapsed_ms = round((clock() - started) * 1000.0, 3)

    identity = {
        "backend_ref": getattr(plan, "controller_ref", None) or getattr(controller, "controller_ref", DETERMINISTIC_CONTROLLER_REF),
        "backend_version": getattr(plan, "controller_version", None) or DETERMINISTIC_CONTROLLER_VERSION,
        "model_or_policy_ref": "deterministic-rule-policy",
    }
    shadow_delta = {}
    if plan is not None:
        for route in available_routes:
            budget = plan.budget_for(route)
            actual = int(route_counts.get(route, 0))
            shadow_delta[route] = {
                "proposed_limit": budget.candidate_limit,
                "actual_count": actual,
                "would_truncate": actual > budget.candidate_limit,
            }
    return {
        "mode": "shadow",
        "controller_contract_version": SYSTEM_ONE_CONTRACT_VERSION,
        "request": {
            "operation": "retrieval_planning",
            "available_capabilities": list(available_routes),
            "budget": {"maximum_controller_decisions": 1, "deadline_ms": None},
            "policy_context": dict(policy_context),
        },
        "response": {
            "controller_identity": identity,
            "operation": "retrieval_planning",
            "decision_status": decision_status,
            "evidence": {
                "route_budgets": None if plan is None else plan.to_dict()["route_budgets"],
                "stop_recommendation": "abstain",
            },
            "authority_effect": "none",
        },
        "usage": {
            "controller_decisions_used": 1,
            "cache_hits": 0,
            "elapsed_ms": elapsed_ms,
            "fallback_events": fallback_events,
        },
        "routes_executed": list(routes_executed),
        "route_candidate_counts": {route: int(route_counts.get(route, 0)) for route in available_routes},
        "shadow_delta": shadow_delta,
        "actual_stop": shadow_actual_stop(route_counts, host_caps, candidate_count),
        "authority_effect": "none",
    }
