"""Substrate port and a deliberately permissive in-memory temporal graph.

The port describes the narrow set of operations a governed adapter needs from a
temporal knowledge-graph substrate. `InMemoryTemporalGraph` implements it while
reproducing the **verified** semantics of the mapped substrate documented in
`docs/programs/runtime-evidence/graphiti-conformance.md`, including the
permissive ones:

- identity is an opaque generated identifier, not a content address;
- partition filtering is an optional query argument that defaults to unfiltered;
- supersession marks validity fields rather than deleting a row;
- deletion is physical and leaves no tombstone;
- no operation checks actor identity or authority.

Reproducing the permissiveness is the entire point. A stub that were already
safe would prove nothing about the governance layer under test: the negative
paths need something real to escape through.

Checkpoint ownership is deliberately separate from ``TemporalGraphPort``. A
provider may satisfy the runtime graph contract without claiming restart-safe
state export/import. Durability is therefore an explicit optional capability,
not something the runtime infers by scraping provider internals.

Shared-evidence neighbor lookup follows the same rule. It is an optional
retrieval capability rather than a new mandatory member of ``TemporalGraphPort``.
Providers that cannot traverse provenance relationships remain valid canonical
substrates; the planner simply cannot claim that route for them.

Issue #461 adds a second optional capability: durable typed relations. Relations
are canonical graph state, but relation traversal remains retrieval evidence
only. A substrate may implement ordinary temporal facts without implementing
this relation surface, and callers must not infer graph capability from the
base ``TemporalGraphPort`` alone.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import math
from typing import Iterable, Mapping, Protocol, runtime_checkable

UNFILTERED = None
CHECKPOINT_SCHEMA_VERSION = "1.0.0"
CHECKPOINT_OWNER = "in_memory_temporal_graph"
TYPED_RELATION_SCHEMA_VERSION = "1.0.0"


class DeterministicIds:
    """Counter-based identifier factory, so runs are reproducible."""

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix
        self._n = 0

    def next(self) -> str:
        self._n += 1
        return f"{self._prefix}-{self._n:04d}"

    def checkpoint_value(self) -> int:
        """Return durable identifier progress without exposing private state."""
        return self._n

    def restore_checkpoint_value(self, value: int) -> None:
        """Restore durable identifier progress, never allowing negative state."""
        parsed = int(value)
        if parsed < 0:
            raise ValueError("identifier checkpoint cannot be negative")
        self._n = parsed


@dataclass(frozen=True)
class Episode:
    """Raw source material, retained verbatim."""

    uuid: str
    content: str
    source_description: str
    valid_at: str
    group_id: str


@dataclass(frozen=True)
class Fact:
    """A temporal assertion with event-time and transaction-time axes."""

    uuid: str
    fact_text: str
    group_id: str
    episode_uuids: tuple[str, ...] = ()
    valid_at: str | None = None
    invalid_at: str | None = None
    created_at: str | None = None
    expired_at: str | None = None
    attributes: dict = field(default_factory=dict)

    @property
    def is_event_invalid(self) -> bool:
        return self.invalid_at is not None

    @property
    def is_transaction_expired(self) -> bool:
        return self.expired_at is not None


@dataclass(frozen=True)
class TypedRelation:
    """A typed, provenance-bearing relation between canonical fact identities.

    ``retrieval_weight`` is deliberately named for what it is: route evidence.
    It is not truth confidence, currentness, scope permission, or PAMA authority.
    Relation validity has the same explicit event-time / transaction-time split
    as facts so graph lifecycle does not collapse into one ambiguous timestamp.
    """

    relation_id: str
    source_uuid: str
    target_uuid: str
    relation_type: str
    group_id: str
    evidence_refs: tuple[str, ...] = ()
    retrieval_weight: float = 1.0
    valid_at: str | None = None
    invalid_at: str | None = None
    created_at: str | None = None
    expired_at: str | None = None
    attributes: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.relation_id:
            raise ValueError("typed relation id is required")
        if not self.source_uuid or not self.target_uuid:
            raise ValueError("typed relation source and target are required")
        if not self.relation_type:
            raise ValueError("typed relation type is required")
        if not self.group_id:
            raise ValueError("typed relation group_id is required")
        if not math.isfinite(self.retrieval_weight):
            raise ValueError("typed relation retrieval_weight must be finite")
        if self.retrieval_weight < 0.0 or self.retrieval_weight > 1.0:
            raise ValueError("typed relation retrieval_weight must be between 0 and 1")

    @property
    def is_event_invalid(self) -> bool:
        return self.invalid_at is not None

    @property
    def is_transaction_expired(self) -> bool:
        return self.expired_at is not None


class TemporalGraphPort(Protocol):
    """Operations a governed adapter requires from a temporal graph."""

    def add_episode(self, episode: Episode) -> None: ...

    def write_fact(self, fact: Fact) -> None: ...

    def invalidate_fact(self, uuid: str, invalid_at: str, expired_at: str) -> None: ...

    def get_fact(self, uuid: str) -> Fact | None: ...

    def delete_fact(self, uuid: str) -> None: ...

    def search(self, query: str, group_ids: list[str] | None = UNFILTERED) -> list[tuple[Fact, float]]: ...


@runtime_checkable
class CheckpointableTemporalGraphPort(Protocol):
    """Optional durable-state capability for a temporal graph provider.

    This protocol intentionally does not extend ``TemporalGraphPort``. External
    providers that do not implement checkpointing remain valid graph providers;
    a restart-safe runtime must simply refuse to claim durability for them.
    """

    def export_checkpoint_state(self) -> dict: ...

    def restore_checkpoint_state(self, snapshot: Mapping[str, object]) -> None: ...

    def identifier_checkpoint(self) -> int: ...

    def restore_identifier_checkpoint(self, value: int) -> None: ...


@runtime_checkable
class EvidenceNeighborTemporalGraphPort(Protocol):
    """Optional provenance-neighbor retrieval capability.

    Results are retrieval evidence only. Implementations may surface stale or
    otherwise inadmissible facts; the governed recall layer remains responsible
    for currentness, scope, dispute, tombstone, and isolation admission.
    """

    def evidence_neighbors(
        self,
        seed_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
    ) -> list[tuple[Fact, tuple[str, ...], float]]: ...


@runtime_checkable
class TypedRelationTemporalGraphPort(Protocol):
    """Optional native typed-relation capability for canonical graph state.

    Implementations own relation persistence and lifecycle. Traversal scores and
    paths built from this surface remain derived retrieval evidence and confer no
    authority. Relation-type vocabulary is intentionally open and domain-
    extensible; Agent Memory does not impose a universal ontology here.
    """

    def write_relation(self, relation: TypedRelation) -> None: ...

    def get_relation(self, relation_id: str) -> TypedRelation | None: ...

    def invalidate_relation(
        self,
        relation_id: str,
        invalid_at: str,
        expired_at: str,
    ) -> None: ...

    def delete_relation(self, relation_id: str) -> None: ...

    def relations_from(
        self,
        source_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
        relation_types: tuple[str, ...] | None = None,
    ) -> list[TypedRelation]: ...

    def relations_to(
        self,
        target_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
        relation_types: tuple[str, ...] | None = None,
    ) -> list[TypedRelation]: ...


class InMemoryTemporalGraph:
    """Permissive substrate model. Executes whatever reaches it."""

    def __init__(self) -> None:
        self._episodes: dict[str, Episode] = {}
        self._facts: dict[str, Fact] = {}
        self._relations: dict[str, TypedRelation] = {}
        self.write_log: list[tuple[str, str]] = []
        # GAP-SEC-08: identifiers are minted per substrate, not per adapter.
        # Two adapters sharing one substrate previously ran independent
        # counters and collided on every id -- fact uuid, receipt_id,
        # correlation_id, and all four event ids -- silently replacing each
        # other's facts and merging each other's evidence records.
        self._ids = DeterministicIds("ref")

    def next_id(self) -> str:
        """Mint the next substrate-scoped identifier.

        Discovered by attribute rather than declared on ``TemporalGraphPort``:
        adding a Protocol member would break every external implementation,
        and the declared contract is Sprint 4's to change.
        """
        return self._ids.next()

    # -- declared checkpoint capability --------------------------------

    def identifier_checkpoint(self) -> int:
        """Return substrate-owned identifier progress for restart compatibility."""
        return self._ids.checkpoint_value()

    def restore_identifier_checkpoint(self, value: int) -> None:
        """Restore substrate-owned identifier progress."""
        self._ids.restore_checkpoint_value(value)

    def export_checkpoint_state(self) -> dict:
        """Export canonical substrate state through the provider-owned seam."""
        return {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "checkpoint_owner": CHECKPOINT_OWNER,
            "relation_schema_version": TYPED_RELATION_SCHEMA_VERSION,
            "episodes": [asdict(value) for _, value in sorted(self._episodes.items())],
            "facts": [asdict(value) for _, value in sorted(self._facts.items())],
            "relations": [asdict(value) for _, value in sorted(self._relations.items())],
            "write_log": [list(item) for item in self.write_log],
            "id_counter": self.identifier_checkpoint(),
        }

    def restore_checkpoint_state(self, snapshot: Mapping[str, object]) -> None:
        """Restore canonical substrate state, failing closed on malformed input.

        ``checkpoint_owner``, ``id_counter``, and typed relations are additive to
        the original v1 payload. Their absence is accepted for legacy v1
        recovery. If a relation schema is declared, it must match the supported
        typed-relation contract exactly.
        """
        if snapshot.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("unsupported substrate state schema")
        owner = snapshot.get("checkpoint_owner")
        if owner not in (None, CHECKPOINT_OWNER):
            raise ValueError("substrate checkpoint owner mismatch")
        relation_schema = snapshot.get("relation_schema_version")
        if relation_schema not in (None, TYPED_RELATION_SCHEMA_VERSION):
            raise ValueError("unsupported typed relation state schema")

        raw_episodes = snapshot.get("episodes", [])
        raw_facts = snapshot.get("facts", [])
        raw_relations = snapshot.get("relations", [])
        raw_log = snapshot.get("write_log", [])
        if (
            not isinstance(raw_episodes, list)
            or not isinstance(raw_facts, list)
            or not isinstance(raw_relations, list)
            or not isinstance(raw_log, list)
        ):
            raise ValueError("substrate checkpoint collections are malformed")

        try:
            episodes: dict[str, Episode] = {}
            for raw in raw_episodes:
                if not isinstance(raw, Mapping):
                    raise TypeError("episode checkpoint row must be a mapping")
                episode = Episode(**dict(raw))
                episodes[episode.uuid] = episode

            facts: dict[str, Fact] = {}
            for raw in raw_facts:
                if not isinstance(raw, Mapping):
                    raise TypeError("fact checkpoint row must be a mapping")
                value = dict(raw)
                value["episode_uuids"] = tuple(value.get("episode_uuids", ()))
                fact = Fact(**value)
                facts[fact.uuid] = fact

            relations: dict[str, TypedRelation] = {}
            for raw in raw_relations:
                if not isinstance(raw, Mapping):
                    raise TypeError("typed relation checkpoint row must be a mapping")
                value = dict(raw)
                value["evidence_refs"] = tuple(value.get("evidence_refs", ()))
                relation = TypedRelation(**value)
                relations[relation.relation_id] = relation

            write_log: list[tuple[str, str]] = []
            for item in raw_log:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    raise ValueError("substrate write-log entry must contain operation and reference")
                write_log.append((str(item[0]), str(item[1])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("substrate state cannot be reconstructed") from exc

        self._episodes = episodes
        self._facts = facts
        self._relations = relations
        self.write_log = write_log
        if "id_counter" in snapshot:
            self.restore_identifier_checkpoint(int(snapshot["id_counter"]))

    # -- writes ---------------------------------------------------------

    def add_episode(self, episode: Episode) -> None:
        self._episodes[episode.uuid] = episode
        self.write_log.append(("add_episode", episode.uuid))

    def write_fact(self, fact: Fact) -> None:
        """Direct write. No authority check, by design and by observation.

        GAP-SEC-08 guard: refuse a uuid that already holds a *different* fact
        rather than replacing it. Defence in depth behind the substrate-scoped
        counter -- a foreign substrate without ``next_id`` still falls back to
        per-adapter counters, and this turns the resulting cross-tenant data
        loss into a loud failure at the point of harm. An identical re-write
        stays a no-op, so replay remains idempotent.
        """
        existing = self._facts.get(fact.uuid)
        if existing is not None and existing != fact:
            raise ValueError(
                f"refusing to overwrite fact {fact.uuid!r} "
                f"(stored group_id={existing.group_id!r}, "
                f"incoming group_id={fact.group_id!r}): "
                "identifier collision would destroy a committed fact"
            )
        self._facts[fact.uuid] = fact
        self.write_log.append(("write_fact", fact.uuid))

    def invalidate_fact(self, uuid: str, invalid_at: str, expired_at: str) -> None:
        """Supersession marks; it never deletes."""
        current = self._facts.get(uuid)
        if current is None:
            return
        self._facts[uuid] = replace(current, invalid_at=invalid_at, expired_at=expired_at)
        self.write_log.append(("invalidate_fact", uuid))

    def delete_fact(self, uuid: str) -> None:
        """Physical removal. No tombstone is written by the substrate."""
        self._facts.pop(uuid, None)
        self.write_log.append(("delete_fact", uuid))

    def write_relation(self, relation: TypedRelation) -> None:
        """Persist one typed relation without granting it governance authority."""
        if relation.source_uuid not in self._facts or relation.target_uuid not in self._facts:
            raise ValueError("typed relation endpoints must exist when the relation is written")
        existing = self._relations.get(relation.relation_id)
        if existing is not None and existing != relation:
            raise ValueError(
                f"refusing to overwrite relation {relation.relation_id!r}: "
                "identifier collision would destroy canonical graph state"
            )
        self._relations[relation.relation_id] = relation
        self.write_log.append(("write_relation", relation.relation_id))

    def invalidate_relation(
        self,
        relation_id: str,
        invalid_at: str,
        expired_at: str,
    ) -> None:
        current = self._relations.get(relation_id)
        if current is None:
            return
        self._relations[relation_id] = replace(
            current,
            invalid_at=invalid_at,
            expired_at=expired_at,
        )
        self.write_log.append(("invalidate_relation", relation_id))

    def delete_relation(self, relation_id: str) -> None:
        self._relations.pop(relation_id, None)
        self.write_log.append(("delete_relation", relation_id))

    # -- reads ----------------------------------------------------------

    def get_fact(self, uuid: str) -> Fact | None:
        return self._facts.get(uuid)

    def get_episode(self, uuid: str) -> Episode | None:
        return self._episodes.get(uuid)

    def get_relation(self, relation_id: str) -> TypedRelation | None:
        return self._relations.get(relation_id)

    def all_facts(self) -> Iterable[Fact]:
        return tuple(self._facts.values())

    def all_relations(self) -> Iterable[TypedRelation]:
        return tuple(self._relations[key] for key in sorted(self._relations))

    def relations_from(
        self,
        source_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
        relation_types: tuple[str, ...] | None = None,
    ) -> list[TypedRelation]:
        return self._relations_matching(
            endpoint="source_uuid",
            endpoint_ref=source_uuid,
            group_ids=group_ids,
            relation_types=relation_types,
        )

    def relations_to(
        self,
        target_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
        relation_types: tuple[str, ...] | None = None,
    ) -> list[TypedRelation]:
        return self._relations_matching(
            endpoint="target_uuid",
            endpoint_ref=target_uuid,
            group_ids=group_ids,
            relation_types=relation_types,
        )

    def _relations_matching(
        self,
        *,
        endpoint: str,
        endpoint_ref: str,
        group_ids: list[str] | None,
        relation_types: tuple[str, ...] | None,
    ) -> list[TypedRelation]:
        allowed_types = None if relation_types is None else set(relation_types)
        values: list[TypedRelation] = []
        for relation in self._relations.values():
            if getattr(relation, endpoint) != endpoint_ref:
                continue
            if group_ids is not UNFILTERED and relation.group_id not in group_ids:
                continue
            if allowed_types is not None and relation.relation_type not in allowed_types:
                continue
            values.append(relation)
        values.sort(
            key=lambda item: (
                -item.retrieval_weight,
                item.relation_type,
                item.source_uuid,
                item.target_uuid,
                item.relation_id,
            )
        )
        return values

    def evidence_neighbors(
        self,
        seed_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
    ) -> list[tuple[Fact, tuple[str, ...], float]]:
        """Return direct neighbors that share retained evidence with one seed.

        The score is deterministic Jaccard overlap over evidence references. It
        expresses relationship strength for retrieval only. Invalid/stale facts
        are deliberately not filtered here so the governed admission boundary
        remains the single authority for current influence.
        """
        seed = self._facts.get(seed_uuid)
        if seed is None:
            return []
        seed_evidence = set(seed.episode_uuids)
        if not seed_evidence:
            return []

        neighbors: list[tuple[Fact, tuple[str, ...], float]] = []
        for fact in self._facts.values():
            if fact.uuid == seed_uuid:
                continue
            if group_ids is not UNFILTERED and fact.group_id not in group_ids:
                continue
            candidate_evidence = set(fact.episode_uuids)
            shared = tuple(sorted(seed_evidence.intersection(candidate_evidence)))
            if not shared:
                continue
            union = seed_evidence.union(candidate_evidence)
            score = len(shared) / len(union) if union else 0.0
            neighbors.append((fact, shared, score))

        neighbors.sort(key=lambda item: (-item[2], item[0].uuid))
        return neighbors

    def search(self, query: str, group_ids: list[str] | None = UNFILTERED) -> list[tuple[Fact, float]]:
        """Candidate generation by lexical overlap.

        Two modelled behaviors matter more than the ranking quality:

        1. `group_ids` defaults to unfiltered, so a caller that forgets the
           argument reads across every partition;
        2. event-invalid facts remain retrievable, matching the conservative
           reading of an open question the source review could not settle.
        """
        terms = _tokens(query)
        scored: list[tuple[Fact, float]] = []
        for fact in self._facts.values():
            if group_ids is not UNFILTERED and fact.group_id not in group_ids:
                continue
            overlap = terms & _tokens(fact.fact_text)
            if not overlap:
                continue
            scored.append((fact, len(overlap) / max(len(terms), 1)))
        scored.sort(key=lambda pair: (-pair[1], pair[0].uuid))
        return scored


def _tokens(text: str) -> set[str]:
    return {token.strip(".,;:!?").lower() for token in text.split() if token.strip(".,;:!?")}
