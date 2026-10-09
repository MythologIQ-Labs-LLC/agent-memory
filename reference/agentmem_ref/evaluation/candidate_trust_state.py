"""#757 evaluation-only single-state, paged, monotone revocation observations.

A process-local checkpoint is *not* authenticated by an external trust root.
All output remains non-authoritative; no link is accepted or memory changed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from threading import Lock
from typing import Literal

from ..memory.temporal_commitment import canonical_json
from .identity_link_journal import _digest, _identifier
from .issuer_policy import IssuerGrant, IssuerPolicySnapshot, policy_digest
from .issuer_policy_lineage import _validate_transition

PROFILE = "agent-memory/candidate-trust-state"
VERSION = "0.1.0"
GENESIS_DOMAIN = b"am-candidate-trust-genesis-v1\x00"
EVENT_DOMAIN = b"am-candidate-trust-event-v1\x00"
MAX_PAGE_EVENTS = 16
EventKind = Literal["key_revoked", "schema_invalidated", "policy_published"]


class TrustStateError(ValueError):
    """Stale expected head, malformed transition or noncanonical journal."""


def _hash(domain: bytes, value: dict[str, object]) -> str:
    return "sha256:" + sha256(domain + canonical_json(value)).hexdigest()


def _policy_copy(snapshot: IssuerPolicySnapshot) -> IssuerPolicySnapshot:
    if type(snapshot) is not IssuerPolicySnapshot:
        raise TrustStateError("noncanonical issuer policy type")
    return IssuerPolicySnapshot(
        policy_ref=snapshot.policy_ref,
        revision_ref=snapshot.revision_ref,
        grants=tuple(IssuerGrant(**asdict(g)) for g in snapshot.grants),
        revoked_key_digests=tuple(snapshot.revoked_key_digests),
        invalidated_registry_revisions=tuple(snapshot.invalidated_registry_revisions),
    )


@dataclass(frozen=True)
class TrustEvent:
    sequence: int
    previous_head: str
    kind: EventKind
    tenant_ref: str
    key_digest: str
    schema_ref: str
    registry_revision_ref: str
    policy_snapshot: IssuerPolicySnapshot | None
    head_digest: str


def _event_copy(event: TrustEvent) -> TrustEvent:
    return TrustEvent(
        event.sequence, event.previous_head, event.kind, event.tenant_ref,
        event.key_digest, event.schema_ref, event.registry_revision_ref,
        _policy_copy(event.policy_snapshot) if event.policy_snapshot is not None else None,
        event.head_digest,
    )


@dataclass(frozen=True)
class TrustPage:
    index: int
    start_head: str
    end_head: str
    events: tuple[TrustEvent, ...]


@dataclass(frozen=True)
class TrustCheckpoint:
    ledger_ref: str
    genesis_head: str
    current_head: str
    sequence: int
    epoch: int
    page_count: int
    policy_digest: str
    denied_key_count: int
    denied_schema_count: int
    authority_effect: Literal["none"] = "none"
    externally_authenticated: Literal[False] = False
    currentness: Literal["not_established"] = "not_established"


@dataclass(frozen=True)
class TrustView:
    checkpoint: TrustCheckpoint
    policy_snapshot: IssuerPolicySnapshot
    denied_keys: frozenset[tuple[str, str]]
    denied_schema_revisions: frozenset[tuple[str, str, str]]


@dataclass(frozen=True)
class TrustReplay:
    status: Literal["mechanical_match", "pin_mismatch", "invalid_history"]
    reason_codes: tuple[str, ...]
    replayed_head: str | None
    replayed_sequence: int | None
    authority_effect: Literal["none"] = "none"
    externally_authenticated: Literal[False] = False
    currentness: Literal["not_established"] = "not_established"
    mutates_memory: Literal[False] = False


def genesis_head(ledger_ref: str, genesis: IssuerPolicySnapshot) -> str:
    _identifier(ledger_ref, "ledger_ref")
    snapshot = _policy_copy(genesis)
    return _hash(GENESIS_DOMAIN, {
        "profile": PROFILE, "version": VERSION, "ledger_ref": ledger_ref,
        "policy_digest": policy_digest(snapshot),
    })


def _event_head(
    sequence: int, previous_head: str, kind: EventKind, tenant_ref: str,
    key_digest: str, schema_ref: str, registry_revision_ref: str,
    snapshot: IssuerPolicySnapshot | None,
) -> str:
    if type(sequence) is not int or sequence <= 0:
        raise TrustStateError("event sequence must increase")
    _digest(previous_head, "previous_head")
    if kind not in ("key_revoked", "schema_invalidated", "policy_published"):
        raise TrustStateError("unknown trust event operation")
    if kind == "key_revoked":
        _identifier(tenant_ref, "tenant_ref")
        _digest(key_digest, "key_digest")
        if schema_ref or registry_revision_ref or snapshot is not None:
            raise TrustStateError("unexpected key event payload")
    elif kind == "schema_invalidated":
        _identifier(tenant_ref, "tenant_ref")
        _identifier(schema_ref, "schema_ref")
        _identifier(registry_revision_ref, "registry_revision_ref")
        if key_digest or snapshot is not None:
            raise TrustStateError("unexpected schema event payload")
    else:
        if tenant_ref or key_digest or schema_ref or registry_revision_ref:
            raise TrustStateError("unexpected policy event payload")
        if type(snapshot) is not IssuerPolicySnapshot:
            raise TrustStateError("policy event requires policy snapshot")
    return _hash(EVENT_DOMAIN, {
        "profile": PROFILE, "version": VERSION, "sequence": sequence,
        "previous_head": previous_head, "kind": kind, "tenant_ref": tenant_ref,
        "key_digest": key_digest, "schema_ref": schema_ref,
        "registry_revision_ref": registry_revision_ref,
        "policy_digest": policy_digest(snapshot) if snapshot is not None else None,
    })


class CandidateTrustState:
    """Bounded per-page history with no global event cap (in-process only).

    This is not a durable database, trusted clock, distributed CAS or external
    key revocation service. Reopening it without externally anchored replay
    does not establish continuity.
    """

    def __init__(self, ledger_ref: str, genesis: IssuerPolicySnapshot) -> None:
        self._ledger_ref = ledger_ref
        self._policy = _policy_copy(genesis)
        self._genesis_head = genesis_head(ledger_ref, self._policy)
        self._head = self._genesis_head
        self._sequence = 0
        self._pages: list[list[TrustEvent]] = []
        self._denied_keys: set[tuple[str, str]] = set()
        self._denied_schemas: set[tuple[str, str, str]] = set()
        self._seen_revisions = {genesis.revision_ref}
        self._lock = Lock()

    def _ensure_head(self, expected_head: str) -> None:
        _digest(expected_head, "expected_head")
        if self._head != expected_head:
            raise TrustStateError("stale or forked expected trust head")

    def _append_locked(
        self, kind: EventKind, tenant_ref: str = "", key_digest: str = "",
        schema_ref: str = "", registry_revision_ref: str = "",
        snapshot: IssuerPolicySnapshot | None = None,
    ) -> TrustEvent:
        nxt = self._sequence + 1
        head = _event_head(
            nxt, self._head, kind, tenant_ref, key_digest, schema_ref,
            registry_revision_ref, snapshot,
        )
        event = TrustEvent(
            nxt, self._head, kind, tenant_ref, key_digest, schema_ref,
            registry_revision_ref, snapshot, head,
        )
        if not self._pages or len(self._pages[-1]) == MAX_PAGE_EVENTS:
            self._pages.append([])
        self._pages[-1].append(event)
        self._head = head
        self._sequence = nxt
        return _event_copy(event)

    def revoke_key(
        self, *, tenant_ref: str, key_digest: str, expected_head: str,
    ) -> TrustEvent:
        _identifier(tenant_ref, "tenant_ref")
        _digest(key_digest, "key_digest")
        with self._lock:
            self._ensure_head(expected_head)
            key = (tenant_ref, key_digest)
            if key in self._denied_keys:
                raise TrustStateError("signing key already revoked")
            event = self._append_locked("key_revoked", tenant_ref, key_digest)
            self._denied_keys.add(key)
            return event

    def invalidate_schema_revision(
        self, *, tenant_ref: str, schema_ref: str,
        registry_revision_ref: str, expected_head: str,
    ) -> TrustEvent:
        for label, value in (
            ("tenant_ref", tenant_ref), ("schema_ref", schema_ref),
            ("registry_revision_ref", registry_revision_ref),
        ):
            _identifier(value, label)
        with self._lock:
            self._ensure_head(expected_head)
            key = (tenant_ref, schema_ref, registry_revision_ref)
            if key in self._denied_schemas:
                raise TrustStateError("schema revision already invalidated")
            event = self._append_locked(
                "schema_invalidated", tenant_ref=tenant_ref,
                schema_ref=schema_ref, registry_revision_ref=registry_revision_ref,
            )
            self._denied_schemas.add(key)
            return event

    def publish_policy(
        self, snapshot: IssuerPolicySnapshot, *, expected_head: str,
    ) -> TrustEvent:
        incoming = _policy_copy(snapshot)
        with self._lock:
            self._ensure_head(expected_head)
            if incoming.revision_ref in self._seen_revisions:
                raise TrustStateError("policy revision reused in same trust state")
            _validate_transition(self._policy, incoming)
            event = self._append_locked("policy_published", snapshot=incoming)
            self._policy = incoming
            self._seen_revisions.add(incoming.revision_ref)
            return event

    def view(self) -> TrustView:
        with self._lock:
            checkpoint = TrustCheckpoint(
                ledger_ref=self._ledger_ref,
                genesis_head=self._genesis_head,
                current_head=self._head,
                sequence=self._sequence,
                epoch=(self._sequence - 1) // MAX_PAGE_EVENTS if self._sequence else 0,
                page_count=len(self._pages),
                policy_digest=policy_digest(self._policy),
                denied_key_count=len(self._denied_keys),
                denied_schema_count=len(self._denied_schemas),
            )
            return TrustView(
                checkpoint=checkpoint,
                policy_snapshot=_policy_copy(self._policy),
                denied_keys=frozenset(self._denied_keys),
                denied_schema_revisions=frozenset(self._denied_schemas),
            )

    def pages(self) -> tuple[TrustPage, ...]:
        with self._lock:
            preceding = self._genesis_head
            output = []
            for i, events in enumerate(self._pages):
                end = events[-1].head_digest
                output.append(TrustPage(
                    index=i, start_head=preceding, end_head=end,
                    events=tuple(_event_copy(event) for event in events),
                ))
                preceding = end
            return tuple(output)


def verify_trust_pages(
    ledger_ref: str, genesis: IssuerPolicySnapshot, pages: tuple[TrustPage, ...],
    *, expected_current_head: str, expected_sequence: int,
) -> TrustReplay:
    """Pure mechanical replay to caller-supplied expectations, NOT a trust root."""
    _digest(expected_current_head, "expected_current_head")
    if type(expected_sequence) is not int or expected_sequence < 0:
        raise TrustStateError("invalid expected sequence")
    if type(pages) is not tuple:
        raise TrustStateError("pages must be tuple")
    try:
        state = CandidateTrustState(ledger_ref, genesis)
        for index, page in enumerate(pages):
            if (type(page) is not TrustPage or page.index != index
                    or type(page.events) is not tuple
                    or not 1 <= len(page.events) <= MAX_PAGE_EVENTS
                    or (index < len(pages)-1
                        and len(page.events) != MAX_PAGE_EVENTS)
                    or page.start_head != state.view().checkpoint.current_head):
                raise TrustStateError("malformed, missing or reordered trust page")
            for item in page.events:
                if type(item) is not TrustEvent:
                    raise TrustStateError("malformed trust event")
                prior = state.view().checkpoint.current_head
                if item.previous_head != prior or item.sequence != state.view().checkpoint.sequence + 1:
                    raise TrustStateError("bad trust-event sequence or prior head")
                if item.kind == "key_revoked":
                    recomputed = state.revoke_key(
                        tenant_ref=item.tenant_ref, key_digest=item.key_digest,
                        expected_head=prior,
                    )
                elif item.kind == "schema_invalidated":
                    recomputed = state.invalidate_schema_revision(
                        tenant_ref=item.tenant_ref, schema_ref=item.schema_ref,
                        registry_revision_ref=item.registry_revision_ref,
                        expected_head=prior,
                    )
                elif item.kind == "policy_published":
                    recomputed = state.publish_policy(
                        item.policy_snapshot, expected_head=prior,
                    )
                else:
                    raise TrustStateError("unknown event kind")
                if recomputed != item:
                    raise TrustStateError("modified trust event payload or head")
            if state.view().checkpoint.current_head != page.end_head:
                raise TrustStateError("trust page end head mismatch")
        final = state.view().checkpoint
    except (ValueError, TypeError, AttributeError, KeyError):
        return TrustReplay("invalid_history", ("trust_replay_invalid",), None, None)
    if final.current_head != expected_current_head or final.sequence != expected_sequence:
        return TrustReplay(
            "pin_mismatch", ("independent_head_or_sequence_pin_mismatch",),
            final.current_head, final.sequence,
        )
    return TrustReplay(
        "mechanical_match", ("independent_anchor_origin_not_authenticated",),
        final.current_head, final.sequence,
    )
