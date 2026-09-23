"""Provider-neutral recall control for the Agent Memory RC runtime.

This module adds an executable fast-control seam above candidate generation and
below governed recall admission.  A controller may choose which retrieval
routes to use and how much work each route may perform, but its output is
strictly retrieval evidence.  It cannot create scope, currentness, privacy, or
authority and it cannot bypass the canonical admission boundary.

The first implementation is deterministic and stdlib-only.  Learned/local or
external System-One controllers can implement the same contract later without
becoming Agent Memory's authority layer or changing retained-memory semantics.

Issue #456 adds the Agent Memory-native semantic/vector route to this same
budgeting contract.  Vector similarity is candidate evidence only; it does not
change the authority semantics of controlled recall.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

from .adapter import RecallContext
from .contextual_recall_adapter import admit_preselected_candidates
from .restart_runtime import RuntimeRecoveryError
from .runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    MultiRouteRecallResult,
    RetrievalRouteHit,
)
from .vector_retrieval import NativeVectorCandidateRetriever, SEMANTIC_VECTOR_ROUTE
from ..state.substrate import EvidenceNeighborTemporalGraphPort


DETERMINISTIC_CONTROLLER_REF = "agent-memory:deterministic-recall-controller"
DETERMINISTIC_CONTROLLER_VERSION = "1.1.0"

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
    """Estimator/controller contract.  Implementations own no recall authority."""

    def plan(
        self,
        query: str,
        *,
        logical_memory_refs: tuple[str, ...],
        available_routes: tuple[str, ...],
    ) -> RecallControlPlan: ...


class DeterministicRecallController:
    """Small deterministic System-One control baseline for RC evaluation.

    The controller uses query shape and explicit seed availability to select
    bounded work.  It deliberately does not inspect governance decisions and
    therefore cannot learn how to route around a refusal.
    """

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
        if shared_candidate_limit:
            reason_codes.append("bounded_relational_expansion")

        target = 1 if len(terms) <= 4 else 3
        budgets = tuple(
            budget
            for budget in (
                RecallRouteBudget(LEXICAL_ROUTE, lexical_limit),
                RecallRouteBudget(EXACT_IDENTITY_ROUTE, exact_limit),
                RecallRouteBudget(SEMANTIC_VECTOR_ROUTE, vector_limit),
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
    ) -> None:
        self.adapter = adapter
        self.controller = controller or DeterministicRecallController()
        self.vector_retriever = vector_retriever
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
    ) -> ControlledRecallResult:
        substrate = self.adapter.checkpoint_substrate()
        tenant = self.adapter.checkpoint_tenant()
        available_routes = [LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE]
        if self.vector_retriever is not None and self.vector_retriever.available_for(substrate):
            available_routes.append(SEMANTIC_VECTOR_ROUTE)
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

        lexical_budget = plan.budget_for(LEXICAL_ROUTE)
        lexical_results = list(substrate.search(query, group_ids=[tenant]))
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
            for logical_ref in tuple(dict.fromkeys(logical_memory_refs))[
                : exact_budget.candidate_limit
            ]:
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

        admission = admit_preselected_candidates(
            self.adapter,
            ordered_candidates,
            context,
            query_label=query,
        )
        ranked = sorted(
            admission.admitted,
            key=lambda candidate_ref: self._rank_key(
                candidate_ref,
                by_candidate.get(candidate_ref, ()),
            ),
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
            route_hits=by_candidate,
            ranked_admitted=ranked,
            policy_version=admission.policy_version,
            evaluated_at=admission.evaluated_at,
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

    @staticmethod
    def _rank_key(candidate_ref: str, hits) -> tuple[object, ...]:
        route_ids = {hit.route_id for hit in hits}
        exact = 1 if EXACT_IDENTITY_ROUTE in route_ids else 0
        vector_score = max(
            (hit.raw_score for hit in hits if hit.route_id == SEMANTIC_VECTOR_ROUTE),
            default=0.0,
        )
        lexical_score = max(
            (hit.raw_score for hit in hits if hit.route_id == LEXICAL_ROUTE),
            default=0.0,
        )
        relational_score = max(
            (hit.raw_score for hit in hits if hit.route_id == SHARED_EVIDENCE_ROUTE),
            default=0.0,
        )
        return (
            -len(route_ids),
            -exact,
            -vector_score,
            -lexical_score,
            -relational_score,
            candidate_ref,
        )