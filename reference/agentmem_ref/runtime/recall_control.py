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
import math
import re
from typing import Protocol

from .adapter import RecallContext, eligible_search
from .contextual_recall_adapter import admission_mode_for_intent, admit_preselected_candidates
from .temporal_intent import resolve_intent
from .temporal_order_constraints import ExplicitCurrentCrossFactRankingPolicy
from .recall_observation_receipt import (
    RecallObservationReceipt,
    RouteObservation,
    capture_recall_observation,
)
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
        if self.candidate_limit < 0:
            raise ValueError("candidate_limit must be non-negative")
        if self.anchor_limit < 0:
            raise ValueError("anchor_limit must be non-negative")


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
    observation_receipt: RecallObservationReceipt | None = None

    def observation_unchanged(self) -> bool:
        """Detect result tampering; never authorize a stop or state action."""
        receipt = self.observation_receipt
        return receipt is not None and receipt.matches_mutable_result(
            candidates=self.recall.candidates,
            admitted=self.recall.admitted,
            ranked=self.recall.ranked_admitted,
            route_counts=self.route_candidate_counts,
            routes_executed=self.recall.routes_executed,
        )

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
        # Capture while route/admission membership is still planner-owned.
        # The receipt is frozen and content-committed, NOT an attested durable
        # state revision or a certificate of complete slot exploration.
        receipt = capture_recall_observation(
            query=query,
            reader_domain_refs=tuple(context.target_domain_refs),
            principal_ref=context.principal_ref,
            project_ref=context.project_ref,
            purpose=context.purpose,
            task_ref=context.task_ref,
            controller_ref=plan.controller_ref,
            admission_policy=recall.policy_version,
            admission_mode=recall.admission_mode,
            evaluated_at=recall.evaluated_at,
            candidates=recall.candidates,
            admitted=recall.admitted,
            ranked=recall.ranked_admitted,
            route_observations=tuple(
                RouteObservation(
                    route_id=budget.route_id,
                    candidate_limit=budget.candidate_limit,
                    anchor_limit=budget.anchor_limit,
                    returned_count=route_counts.get(budget.route_id, 0),
                    executed=budget.candidate_limit > 0,
                )
                for budget in plan.route_budgets
            ),
        )
        return ControlledRecallResult(
            plan=plan,
            recall=recall,
            route_candidate_counts=route_counts,
            evidence_sufficiency_met=sufficient,
            stop_reason=(
                "evidence_target_met" if sufficient else "planned_routes_exhausted"
            ),
            graph_candidate_hits=graph_candidate_hits,
            observation_receipt=receipt,
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
