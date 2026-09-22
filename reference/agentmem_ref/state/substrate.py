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

Stdlib only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Iterable, Mapping, Protocol, runtime_checkable

UNFILTERED = None
CHECKPOINT_SCHEMA_VERSION = "1.0.0"
CHECKPOINT_OWNER = "in_memory_temporal_graph"


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


class InMemoryTemporalGraph:
    """Permissive substrate model. Executes whatever reaches it."""

    def __init__(self) -> None:
        self._episodes: dict[str, Episode] = {}
        self._facts: dict[str, Fact] = {}
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
            "episodes": [asdict(value) for _, value in sorted(self._episodes.items())],
            "facts": [asdict(value) for _, value in sorted(self._facts.items())],
            "write_log": [list(item) for item in self.write_log],
            "id_counter": self.identifier_checkpoint(),
        }

    def restore_checkpoint_state(self, snapshot: Mapping[str, object]) -> None:
        """Restore canonical substrate state, failing closed on malformed input.

        ``checkpoint_owner`` and ``id_counter`` are additive to the original v1
        wire payload. Their absence is accepted only for legacy v1 recovery;
        the runtime supplies legacy identifier progress through the separate
        identifier checkpoint seam before this method returns.
        """
        if snapshot.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("unsupported substrate state schema")
        owner = snapshot.get("checkpoint_owner")
        if owner not in (None, CHECKPOINT_OWNER):
            raise ValueError("substrate checkpoint owner mismatch")

        raw_episodes = snapshot.get("episodes", [])
        raw_facts = snapshot.get("facts", [])
        raw_log = snapshot.get("write_log", [])
        if not isinstance(raw_episodes, list) or not isinstance(raw_facts, list) or not isinstance(raw_log, list):
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

            write_log: list[tuple[str, str]] = []
            for item in raw_log:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    raise ValueError("substrate write-log entry must contain operation and reference")
                write_log.append((str(item[0]), str(item[1])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("substrate state cannot be reconstructed") from exc

        self._episodes = episodes
        self._facts = facts
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

    # -- reads ----------------------------------------------------------

    def get_fact(self, uuid: str) -> Fact | None:
        return self._facts.get(uuid)

    def get_episode(self, uuid: str) -> Episode | None:
        return self._episodes.get(uuid)

    def all_facts(self) -> Iterable[Fact]:
        return tuple(self._facts.values())

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
