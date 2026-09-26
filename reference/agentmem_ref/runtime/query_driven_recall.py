"""Opt-in deterministic query-driven recall baseline for issue #437.

The RC multi-route runtime already supports lexical, exact logical-identity, and
shared-evidence neighbor candidate routes. Its relational route is seeded by
caller-supplied logical memory references, which is useful for known-memory
workflows but is not sufficient for natural-language benchmark questions.

This module adds a bounded baseline that may use the highest-value *current*
lexical candidates as relation anchors. Raw substrate lexical scores are not
trusted blindly for expansion because stop-word overlap can outrank the
content-bearing clue needed to reach related memory. Anchor selection therefore
re-ranks lexical candidates by deterministic content-term overlap before using
the substrate score as a tie-breaker.

It remains candidate generation only: all candidates cross the same canonical
governed admission boundary once, and route scores never create scope,
currentness, privacy, or authority.

The planner is intentionally opt-in and separate from the default runtime path.
That prevents benchmark experimentation from silently changing application
recall semantics while establishing a deterministic control for later learned
or System-One route planning.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .adapter import RecallContext, eligible_search
from .contextual_recall_adapter import admission_mode_for_intent, admit_preselected_candidates
from .temporal_intent import resolve_intent
from .ranking_policy import PostAdmissionRankingPolicy
from .restart_runtime import RuntimeRecoveryError
from .runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    MultiRouteRecallResult,
    RetrievalRouteHit,
)
from ..state.substrate import EvidenceNeighborTemporalGraphPort


QUERY_ANCHOR_SOURCE = "query_lexical_anchor"
EXPLICIT_ANCHOR_SOURCE = "explicit_logical_identity"

# Pre-existing route precedence of this planner, now declared rather than implicit.
QUERY_DRIVEN_RANKING_POLICY = PostAdmissionRankingPolicy(
    policy_id="query-driven-relational",
    route_score_order=(LEXICAL_ROUTE, SHARED_EVIDENCE_ROUTE),
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
    """Return deterministic content-bearing terms for anchor selection only.

    This is intentionally not a replacement for the substrate's lexical search
    contract. It is a bounded route-planning heuristic used after lexical
    candidate generation so common function-word overlap cannot choose an
    unrelated relational expansion seed.
    """
    return {term for term in _WORD.findall(text.lower()) if term not in _STOPWORDS}


def _content_overlap(query: str, fact_text: str) -> int:
    return len(_content_terms(query).intersection(_content_terms(fact_text)))


@dataclass(frozen=True)
class QueryDrivenRecallConfig:
    """Bounded deterministic route-planning controls."""

    lexical_anchor_limit: int = 3
    minimum_anchor_content_overlap: int = 1

    def __post_init__(self) -> None:
        if self.lexical_anchor_limit < 0:
            raise ValueError("lexical_anchor_limit must be non-negative")
        if self.minimum_anchor_content_overlap < 1:
            raise ValueError("minimum_anchor_content_overlap must be >= 1")


class DeterministicQueryDrivenRecallPlanner:
    """Lexical candidates + bounded query anchors + optional exact seeds.

    Retrieval order and limits are deterministic. A query-derived anchor must
    be current and have content-bearing overlap before it can expand. Neighbor
    facts themselves may still be stale or otherwise inadmissible so the
    canonical admission layer can record the controlling refusal rather than
    silently erasing discoverability evidence.
    """

    def __init__(self, adapter, *, config: QueryDrivenRecallConfig | None = None) -> None:
        self.adapter = adapter
        self.config = config or QueryDrivenRecallConfig()
        substrate_reader = getattr(adapter, "checkpoint_substrate", None)
        tenant_reader = getattr(adapter, "checkpoint_tenant", None)
        if not callable(substrate_reader) or not callable(tenant_reader):
            raise RuntimeRecoveryError(
                "query-driven recall requires the restart-safe adapter substrate/tenant contract"
            )

    def recall(
        self,
        query: str,
        context: RecallContext,
        *,
        logical_memory_refs: tuple[str, ...] = (),
        temporal_intent=None,
    ) -> MultiRouteRecallResult:
        substrate = self.adapter.checkpoint_substrate()
        tenant = self.adapter.checkpoint_tenant()

        hits: list[RetrievalRouteHit] = []
        routes_executed: list[str] = [LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE]
        lexical_results = list(eligible_search(substrate, query, tenant, lambda fact: self.adapter.domain_eligible(fact, context)))
        for fact, score in lexical_results:
            hits.append(
                RetrievalRouteHit(
                    route_id=LEXICAL_ROUTE,
                    candidate_ref=fact.uuid,
                    raw_score=float(score),
                )
            )

        explicit_seeds: list[tuple[str, str]] = []
        for logical_ref in dict.fromkeys(logical_memory_refs):
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

        relational_capable = isinstance(substrate, EvidenceNeighborTemporalGraphPort)
        if relational_capable and (explicit_seeds or self.config.lexical_anchor_limit > 0):
            routes_executed.append(SHARED_EVIDENCE_ROUTE)
            expanded_seeds: set[str] = set()

            for logical_ref, seed_ref in explicit_seeds:
                self._expand_seed(
                    substrate,
                    tenant,
                    hits,
                    seed_ref=seed_ref,
                    logical_memory_ref=logical_ref,
                    expanded_seeds=expanded_seeds,
                )

            ranked_anchors: list[tuple[int, float, object]] = []
            for fact, raw_score in lexical_results:
                if fact.uuid in expanded_seeds:
                    continue
                if fact.is_event_invalid or fact.is_transaction_expired:
                    continue
                overlap = _content_overlap(query, fact.fact_text)
                if overlap < self.config.minimum_anchor_content_overlap:
                    continue
                ranked_anchors.append((overlap, float(raw_score), fact))

            ranked_anchors.sort(key=lambda item: (-item[0], -item[1], item[2].uuid))
            for _overlap, _raw_score, fact in ranked_anchors[: self.config.lexical_anchor_limit]:
                self._expand_seed(
                    substrate,
                    tenant,
                    hits,
                    seed_ref=fact.uuid,
                    logical_memory_ref="",
                    expanded_seeds=expanded_seeds,
                )

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
        ranked, ranking_evidence = QUERY_DRIVEN_RANKING_POLICY.rank(
            admission.admitted,
            by_candidate,
            substrate.get_fact,
            query=query,
            intent=intent,
        )
        return MultiRouteRecallResult(
            query=query,
            routes_executed=tuple(routes_executed),
            candidates=list(admission.candidates),
            admitted=list(admission.admitted),
            refusals=dict(admission.refusals),
            decisions=dict(admission.decisions),
            route_hits={ref: hits for ref, hits in by_candidate.items() if ref in admission.candidates},
            ranked_admitted=ranked,
            policy_version=admission.policy_version,
            evaluated_at=admission.evaluated_at,
            ranking_policy=QUERY_DRIVEN_RANKING_POLICY.identity(),
            ranking_evidence=ranking_evidence,
            candidate_policy=dict(admission.candidate_policy),
            admission_mode=admission.admission_mode,
            admission_basis=dict(admission.admission_basis),
            query_temporal_intent=intent.to_dict(),
        )

    def _expand_seed(
        self,
        substrate: EvidenceNeighborTemporalGraphPort,
        tenant: str,
        hits: list[RetrievalRouteHit],
        *,
        seed_ref: str,
        logical_memory_ref: str,
        expanded_seeds: set[str],
    ) -> None:
        if seed_ref in expanded_seeds:
            return
        seed_fact = substrate.get_fact(seed_ref)
        if seed_fact is None or seed_fact.is_event_invalid or seed_fact.is_transaction_expired:
            return
        expanded_seeds.add(seed_ref)
        for fact, shared_refs, score in substrate.evidence_neighbors(
            seed_ref,
            group_ids=[tenant],
        ):
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

