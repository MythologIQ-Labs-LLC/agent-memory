"""Agent Memory-native typed graph candidate retrieval.

Issue #461 harvests generic graph mechanics from first-party ancestry without
creating an EvolveAI or CodeGenome runtime dependency. Typed relations are
canonical substrate state. Traversal paths, path weights, and graph proximity
are derived retrieval evidence only and must cross the ordinary governed recall
admission boundary before they can influence active cognition.

The first profile is intentionally small and deterministic:

* bounded breadth-first traversal;
* explicit direction and relation-type filters;
* explicit hop, fan-out, score and candidate limits;
* cycle containment;
* complete path/relation provenance;
* no model, network, graph-database, or domain-specific ontology dependency.

A relation that is itself invalid/expired is not an active traversal edge. A
reachable fact may still be stale, superseded, disputed, tombstoned, or out of
scope; those fact-level conditions remain the responsibility of governed recall
admission. A physically deleted target cannot become a candidate because no
canonical fact remains to admit.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math

from ..state.substrate import TypedRelation, TypedRelationTemporalGraphPort


TYPED_GRAPH_ROUTE = "typed_graph"
OUTGOING = "outgoing"
INCOMING = "incoming"
BOTH = "both"


@dataclass(frozen=True)
class GraphTraversalSpec:
    """Deterministic work and semantics contract for one graph route."""

    max_depth: int = 2
    max_fanout: int = 8
    relation_types: tuple[str, ...] = ()
    direction: str = OUTGOING
    min_path_score: float = 0.0
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.max_depth < 1:
            raise ValueError("graph traversal max_depth must be >= 1")
        if self.max_fanout < 1:
            raise ValueError("graph traversal max_fanout must be >= 1")
        if self.direction not in (OUTGOING, INCOMING, BOTH):
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
    """One best deterministic path from a seed to a candidate fact."""

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
    """Bounded deterministic traversal over Agent Memory canonical relations."""

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
        visited = {seed_ref}
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
                if next_ref in visited:
                    continue
                if relation.is_event_invalid or relation.is_transaction_expired:
                    continue
                next_score = path_score * relation.retrieval_weight
                if next_score < self.spec.min_path_score:
                    continue
                # Relations intentionally survive fact deletion as residue. A
                # deleted target has no canonical fact to admit, so it cannot be
                # emitted as an active retrieval candidate or expansion point.
                if substrate.get_fact(next_ref) is None:
                    continue

                visited.add(next_ref)
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
        if self.spec.direction in (OUTGOING, BOTH):
            for relation in substrate.relations_from(
                node_ref,
                group_ids=[group_id],
                relation_types=relation_types,
            ):
                values[(relation.relation_id, relation.target_uuid)] = (
                    relation.target_uuid,
                    relation,
                )
        if self.spec.direction in (INCOMING, BOTH):
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
        """Best path first; deterministic ties prefer fewer hops then identity."""
        return (
            -hit.path_score,
            hit.hop_count,
            hit.candidate_ref,
            hit.seed_candidate_ref,
            hit.relation_ids,
        )
