"""Opt-in deterministic query-driven recall baseline for issue #437.

The RC multi-route runtime already supports lexical, exact logical-identity, and
shared-evidence neighbor candidate routes. Its relational route is seeded by
caller-supplied logical memory references, which is useful for known-memory
workflows but is not sufficient for natural-language benchmark questions.

This module adds a bounded baseline that may use the highest-ranked *current*
lexical candidates as relation anchors. It remains candidate generation only:
all candidates cross the same canonical governed admission boundary once, and
route scores never create scope, currentness, privacy, or authority.

The planner is intentionally opt-in and separate from the default runtime path.
That prevents benchmark experimentation from silently changing application
recall semantics while establishing a deterministic control for later learned
or System-One route planning.
"""

from __future__ import annotations

from dataclasses import dataclass

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
from ..state.substrate import EvidenceNeighborTemporalGraphPort


QUERY_ANCHOR_SOURCE = "query_lexical_anchor"
EXPLICIT_ANCHOR_SOURCE = "explicit_logical_identity"


@dataclass(frozen=True)
class QueryDrivenRecallConfig:
    """Bounded deterministic route-planning controls."""

    lexical_anchor_limit: int = 3

    def __post_init__(self) -> None:
        if self.lexical_anchor_limit < 0:
            raise ValueError("lexical_anchor_limit must be non-negative")


class DeterministicQueryDrivenRecallPlanner:
    """Lexical anchors + optional exact seeds + provenance neighbors.

    Retrieval order and limits are deterministic. A lexical anchor must be
    current at candidate-generation time before it can expand. Neighbor facts
    themselves may still be stale or otherwise inadmissible so the canonical
    admission layer can record the controlling refusal rather than silently
    erasing discoverability evidence.
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
    ) -> MultiRouteRecallResult:
        substrate = self.adapter.checkpoint_substrate()
        tenant = self.adapter.checkpoint_tenant()

        hits: list[RetrievalRouteHit] = []
        routes_executed: list[str] = [LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE]
        lexical_results = list(substrate.search(query, group_ids=[tenant]))
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

            remaining = self.config.lexical_anchor_limit
            for fact, _score in lexical_results:
                if remaining <= 0:
                    break
                if fact.uuid in expanded_seeds:
                    continue
                if fact.is_event_invalid or fact.is_transaction_expired:
                    continue
                self._expand_seed(
                    substrate,
                    tenant,
                    hits,
                    seed_ref=fact.uuid,
                    logical_memory_ref="",
                    expanded_seeds=expanded_seeds,
                )
                remaining -= 1

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
        return MultiRouteRecallResult(
            query=query,
            routes_executed=tuple(routes_executed),
            candidates=list(admission.candidates),
            admitted=list(admission.admitted),
            refusals=dict(admission.refusals),
            decisions=dict(admission.decisions),
            route_hits=by_candidate,
            ranked_admitted=ranked,
            policy_version=admission.policy_version,
            evaluated_at=admission.evaluated_at,
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

    @staticmethod
    def _rank_key(candidate_ref: str, hits) -> tuple[object, ...]:
        route_ids = {hit.route_id for hit in hits}
        exact = 1 if EXACT_IDENTITY_ROUTE in route_ids else 0
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
            -lexical_score,
            -relational_score,
            candidate_ref,
        )
