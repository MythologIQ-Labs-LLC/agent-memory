"""#757 untrusted append-only, replayable proposition-link EVIDENCE journal.

Evaluation ONLY. Content digests and an internally consistent hash chain DO NOT
authenticate an issuer, establish semantic proposition identity, prove truth,
grant supersession/recall authority, or provide durable multi-process CAS.
There is intentionally no approval/acceptance event or runtime import.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import json
from threading import Lock
from typing import Literal

from .proposition_link_preflight import (
    ClaimOfIdentity,
    ObservedWrite,
    ProposedIdentityLink,
    preflight,
)

CONTRACT = "agent-memory/identity-link-journal/v0.1"
GENESIS_DOMAIN = b"am-link-journal-genesis-v1\x00"
PROPOSAL_DOMAIN = b"am-link-proposal-v1\x00"
EVENT_DOMAIN = b"am-link-event-v1\x00"
MAX_EVENTS = 128
MAX_PAYLOAD_BYTES = 16384
MAX_REASON_LENGTH = 256
EventKind = Literal["proposed", "withdrawn", "disputed"]


class JournalError(ValueError):
    """Refusal of an invalid or stale audit-journal operation."""


@dataclass(frozen=True)
class LinkEvent:
    stream_ref: str
    sequence: int
    previous_digest: str
    kind: EventKind
    proposal_digest: str
    proposal_payload: str | None
    reason: str | None
    event_digest: str


@dataclass(frozen=True)
class JournalReport:
    stream_ref: str
    head_digest: str
    events: tuple[LinkEvent, ...]
    proposal_states: tuple[tuple[str, str], ...]
    authority_effect: Literal["none"] = "none"
    identity_verified: Literal[False] = False
    can_supersede: Literal[False] = False
    mutates_memory: Literal[False] = False
    integration_state: Literal["evaluation_only"] = "evaluation_only"


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or not value or len(value) > MAX_REASON_LENGTH or value != value.strip():
        raise JournalError(f"{name} must be a bounded, trimmed, nonempty string")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise JournalError(f"{name} includes control characters")
    return value


def _digest(value: object, name: str) -> str:
    if type(value) is not str or len(value) != 71 or not value.startswith("sha256:"):
        raise JournalError(f"{name} is not a sha256 digest")
    if any(c not in "0123456789abcdef" for c in value[7:]):
        raise JournalError(f"{name} must use lowercase hex")
    return value


def _hash(domain: bytes, contents: bytes) -> str:
    return "sha256:" + sha256(domain + contents).hexdigest()


def _json_bytes(value: object) -> bytes:
    try:
        data = (json.dumps(value, ensure_ascii=True, sort_keys=True,
                           separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")
    except (ValueError, TypeError, UnicodeError) as error:
        raise JournalError("not a canonical JSON value") from error
    if len(data) > MAX_PAYLOAD_BYTES:
        raise JournalError("journal payload exceeds size limit")
    return data


def genesis(stream_ref: str) -> str:
    return _hash(GENESIS_DOMAIN, _identifier(stream_ref, "stream_ref").encode("utf-8"))


def _typed(cls: type, data: object):
    if type(data) is not dict or set(data) != {field.name for field in fields(cls)}:
        raise JournalError(f"malformed {cls.__name__} structure")
    try:
        return cls(**data)
    except (TypeError, ValueError) as error:
        raise JournalError(f"invalid {cls.__name__}") from error


def _load_proposal(raw: str) -> ProposedIdentityLink:
    if type(raw) is not str or len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise JournalError("proposal payload is missing or oversized")
    try:
        envelope = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise JournalError("proposal payload is malformed") from error
    if type(envelope) is not dict or set(envelope) != {"contract", "proposal", "preflight"}:
        raise JournalError("proposal envelope shape mismatch")
    if envelope["contract"] != CONTRACT:
        raise JournalError("unsupported journal contract")
    if _json_bytes(envelope).decode("ascii") != raw:
        raise JournalError("proposal JSON not in required canonical form")
    p = envelope["proposal"]
    if type(p) is not dict or set(p) != {field.name for field in fields(ProposedIdentityLink)}:
        raise JournalError("invalid proposed link shape")
    if type(p["claims"]) is not list:
        raise JournalError("claims must be an array")
    older = _typed(ObservedWrite, p["older"])
    newer = _typed(ObservedWrite, p["newer"])
    claims = tuple(_typed(ClaimOfIdentity, item) for item in p["claims"])
    try:
        proposal = ProposedIdentityLink(
            older=older, newer=newer,
            expected_head_ref=p["expected_head_ref"],
            observed_head_ref=p["observed_head_ref"],
            claims=claims,
        )
    except (TypeError, ValueError) as error:
        raise JournalError("invalid proposed-link parameters") from error
    verdict = preflight(proposal)
    recorded = envelope["preflight"]
    if recorded != {"status": verdict.status, "reasons": list(verdict.reasons)}:
        raise JournalError("proposal preflight does not replay at this contract version")
    if verdict.status == "refused":
        raise JournalError("refused structural link cannot enter proposal journal")
    return proposal


def proposal_payload(proposal: ProposedIdentityLink) -> str:
    if not isinstance(proposal, ProposedIdentityLink):
        raise TypeError("proposal must be ProposedIdentityLink")
    verdict = preflight(proposal)
    if verdict.status == "refused":
        raise JournalError("structurally refused proposals must not be journaled")
    envelope = {
        "contract": CONTRACT,
        "proposal": asdict(proposal),
        "preflight": {"status": verdict.status, "reasons": list(verdict.reasons)},
    }
    payload = _json_bytes(envelope).decode("ascii")
    # The canonical serializer is the only supported way to admit a proposal.
    _load_proposal(payload)
    return payload


def _event_fields(event: LinkEvent) -> dict:
    return {key: getattr(event, key) for key in (
        "stream_ref", "sequence", "previous_digest", "kind",
        "proposal_digest", "proposal_payload", "reason",
    )}


def _event_hash(event: LinkEvent) -> str:
    return _hash(EVENT_DOMAIN, _json_bytes(_event_fields(event)))


def _append_event(stream_ref: str, sequence: int, previous_digest: str,
                  kind: EventKind, proposal_digest: str,
                  proposal_payload_text: str | None, reason: str | None) -> LinkEvent:
    event = LinkEvent(stream_ref, sequence, previous_digest, kind, proposal_digest,
                      proposal_payload_text, reason, "")
    return LinkEvent(stream_ref, sequence, previous_digest, kind, proposal_digest,
                     proposal_payload_text, reason, _event_hash(event))


def replay(stream_ref: str, events: tuple[LinkEvent, ...]) -> JournalReport:
    """Validate internal chain consistency. NO external authenticity asserted."""
    head = genesis(stream_ref)
    if type(events) is not tuple or len(events) > MAX_EVENTS:
        raise JournalError("events must be a bounded tuple")
    statuses: dict[str, str] = {}
    for index, item in enumerate(events):
        if type(item) is not LinkEvent:
            raise JournalError("unexpected event type")
        if item.stream_ref != stream_ref or type(item.sequence) is not int or item.sequence != index + 1:
            raise JournalError("wrong stream or sequence")
        if _digest(item.previous_digest, "previous_digest") != head:
            raise JournalError("fork/stale journal head")
        _digest(item.proposal_digest, "proposal_digest")
        if _digest(item.event_digest, "event_digest") != _event_hash(item):
            raise JournalError("event body does not match its content digest")
        if item.kind == "proposed":
            if item.reason is not None or type(item.proposal_payload) is not str:
                raise JournalError("proposal event shape is invalid")
            _load_proposal(item.proposal_payload)
            if item.proposal_digest != _hash(PROPOSAL_DOMAIN, item.proposal_payload.encode("ascii")):
                raise JournalError("proposal content digest mismatch")
            if item.proposal_digest in statuses:
                raise JournalError("duplicate proposal")
            statuses[item.proposal_digest] = "under_review"
        elif item.kind in ("withdrawn", "disputed"):
            if item.proposal_payload is not None:
                raise JournalError("resolution must not duplicate proposal payload")
            _identifier(item.reason, "resolution reason")
            if statuses.get(item.proposal_digest) != "under_review":
                raise JournalError("unknown or already resolved proposal")
            statuses[item.proposal_digest] = item.kind
        else:
            raise JournalError("unsupported event kind; there is no approval event")
        head = item.event_digest
    return JournalReport(
        stream_ref=stream_ref, head_digest=head, events=events,
        proposal_states=tuple(sorted(statuses.items())),
    )


class LinkEvidenceJournal:
    """Bounded process-local append-only diagnostics, NOT a durable trust ledger."""

    def __init__(self, stream_ref: str, events: tuple[LinkEvent, ...] = ()):
        _identifier(stream_ref, "stream_ref")
        self._stream_ref = stream_ref
        self._lock = Lock()
        self._events = replay(stream_ref, events).events

    def inspect(self) -> JournalReport:
        with self._lock:
            return replay(self._stream_ref, self._events)

    def propose(self, proposal: ProposedIdentityLink, *,
                expected_head: str) -> LinkEvent:
        # Preparation can run outside the lock; commit rechecks exact head.
        payload = proposal_payload(proposal)
        payload_digest = _hash(PROPOSAL_DOMAIN, payload.encode("ascii"))
        return self._commit("proposed", payload_digest, payload, None, expected_head)

    def resolve(self, proposal_digest: str, *, kind: Literal["withdrawn", "disputed"],
                reason: str, expected_head: str) -> LinkEvent:
        if kind not in ("withdrawn", "disputed"):
            raise JournalError("only negative/uncertain resolutions are supported")
        _digest(proposal_digest, "proposal_digest")
        _identifier(reason, "reason")
        return self._commit(kind, proposal_digest, None, reason, expected_head)

    def _commit(self, kind: EventKind, proposal_digest: str,
                payload: str | None, reason: str | None,
                expected_head: str) -> LinkEvent:
        _digest(expected_head, "expected_head")
        with self._lock:
            before = replay(self._stream_ref, self._events)
            if before.head_digest != expected_head:
                raise JournalError("stale expected head; no event appended")
            if len(self._events) >= MAX_EVENTS:
                raise JournalError("bounded journal is full")
            state = dict(before.proposal_states)
            if kind == "proposed" and proposal_digest in state:
                raise JournalError("duplicate proposal digest")
            if kind != "proposed" and state.get(proposal_digest) != "under_review":
                raise JournalError("cannot resolve absent or already resolved proposal")
            event = _append_event(
                self._stream_ref, len(self._events) + 1, before.head_digest,
                kind, proposal_digest, payload, reason,
            )
            candidate = self._events + (event,)
            replay(self._stream_ref, candidate)  # fail closed before commit
            self._events = candidate
            return event
