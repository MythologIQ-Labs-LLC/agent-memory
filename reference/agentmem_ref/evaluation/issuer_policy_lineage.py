"""#757 J57-J72: evaluation-only issuer-policy lineage and rollback observations.

A matching lineage proves internal consistency, NOT that an external pin is
trusted, fresh or current. No issuer, semantic identity, recall, correction,
PAMA or memory-mutation authority exists in this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from threading import Lock
from typing import Literal

from ..memory.temporal_commitment import canonical_json
from .identity_link_journal import _digest
from .issuer_policy import IssuerGrant, IssuerPolicySnapshot, policy_digest

PROFILE = "agent-memory/issuer-policy-lineage"
VERSION = "0.1.0"
GENESIS_DOMAIN = b"am-issuer-policy-genesis-v1\x00"
EVENT_DOMAIN = b"am-issuer-policy-event-v1\x00"
MAX_TRANSITIONS = 64


class PolicyLineageError(ValueError):
    """Invalid lineage shape, transition, stale write or replay."""


@dataclass(frozen=True)
class PolicyLineageEvent:
    sequence: int
    previous_head: str
    snapshot: IssuerPolicySnapshot
    snapshot_digest: str
    head_digest: str


@dataclass(frozen=True)
class PolicyLineageReport:
    genesis_snapshot: IssuerPolicySnapshot
    genesis_head: str
    head_digest: str
    events: tuple[PolicyLineageEvent, ...]
    issuer_authorized: Literal[False] = False
    identity_verified: Literal[False] = False
    can_supersede: Literal[False] = False
    authority_effect: Literal["none"] = "none"
    mutates_memory: Literal[False] = False
    currentness: Literal["not_established"] = "not_established"
    integration_state: Literal["evaluation_only"] = "evaluation_only"


@dataclass(frozen=True)
class PolicyLineageVerification:
    status: Literal["mechanical_match", "pin_mismatch", "invalid_history"]
    reason_codes: tuple[str, ...]
    replayed_head: str | None
    genesis_matches: bool
    head_matches: bool
    count_matches: bool
    issuer_authorized: Literal[False] = False
    identity_verified: Literal[False] = False
    can_supersede: Literal[False] = False
    authority_effect: Literal["none"] = "none"
    mutates_memory: Literal[False] = False
    trusted_time: Literal["not_established"] = "not_established"
    currentness: Literal["not_established"] = "not_established"
    integration_state: Literal["evaluation_only"] = "evaluation_only"


def _hash(domain: bytes, body: dict[str, object]) -> str:
    return "sha256:" + sha256(domain + canonical_json(body)).hexdigest()


def genesis_head(snapshot: IssuerPolicySnapshot) -> str:
    if type(snapshot) is not IssuerPolicySnapshot:
        raise TypeError("genesis must be an exact IssuerPolicySnapshot")
    return _hash(GENESIS_DOMAIN, {
        "profile": PROFILE,
        "version": VERSION,
        "policy_ref": snapshot.policy_ref,
        "snapshot_digest": policy_digest(snapshot),
    })


def _event_head(sequence: int, prior: str, snapshot_hash: str) -> str:
    if type(sequence) is not int or not 1 <= sequence <= MAX_TRANSITIONS:
        raise PolicyLineageError("invalid lineage event sequence")
    _digest(prior, "previous_head")
    _digest(snapshot_hash, "snapshot_digest")
    return _hash(EVENT_DOMAIN, {
        "profile": PROFILE,
        "version": VERSION,
        "sequence": sequence,
        "previous_head": prior,
        "snapshot_digest": snapshot_hash,
    })


def _snapshot_copy(snapshot: IssuerPolicySnapshot) -> IssuerPolicySnapshot:
    """Deep-copy a snapshot: frozen objects can be mutated with object.__setattr__."""
    if type(snapshot) is not IssuerPolicySnapshot:
        raise PolicyLineageError("noncanonical snapshot type")
    return IssuerPolicySnapshot(
        policy_ref=snapshot.policy_ref,
        revision_ref=snapshot.revision_ref,
        grants=tuple(IssuerGrant(**asdict(x)) for x in snapshot.grants),
        revoked_key_digests=tuple(snapshot.revoked_key_digests),
        invalidated_registry_revisions=tuple(snapshot.invalidated_registry_revisions),
    )


def _event_copy(item: PolicyLineageEvent) -> PolicyLineageEvent:
    return PolicyLineageEvent(
        item.sequence, item.previous_head, _snapshot_copy(item.snapshot),
        item.snapshot_digest, item.head_digest,
    )


def _grants(snapshot: IssuerPolicySnapshot) -> dict[tuple[str, ...], IssuerGrant]:
    return {grant.scope_key: grant for grant in snapshot.grants}


def _validate_transition(old: IssuerPolicySnapshot,
                         new: IssuerPolicySnapshot) -> None:
    if type(old) is not IssuerPolicySnapshot or type(new) is not IssuerPolicySnapshot:
        raise PolicyLineageError("transition requires exact typed policy snapshots")
    # Digest revalidates inner immutable data and bounds.
    policy_digest(old)
    policy_digest(new)
    if new.policy_ref != old.policy_ref:
        raise PolicyLineageError("policy identity cannot change in one lineage")
    if new.revision_ref == old.revision_ref:
        raise PolicyLineageError("policy revision must change")

    if not set(old.revoked_key_digests).issubset(new.revoked_key_digests):
        raise PolicyLineageError("key revocation cannot be removed")
    if not set(old.invalidated_registry_revisions).issubset(
        new.invalidated_registry_revisions
    ):
        raise PolicyLineageError("registry invalidation cannot be removed")

    prev = _grants(old)
    next_grants = _grants(new)
    if not prev.keys() <= next_grants.keys():
        raise PolicyLineageError("issuer grant scope cannot be silently removed")
    for scope, was in prev.items():
        now = next_grants[scope]
        if was.state == "revoked":
            if now != was:
                raise PolicyLineageError("revoked grant cannot be revived or rewritten")
            continue
        if now.state == "revoked":
            if (now.issuer_key_ref != was.issuer_key_ref
                    or now.public_key_digest != was.public_key_digest):
                raise PolicyLineageError("grant tombstone must retain old issuer identity")
            continue
        if (now.issuer_key_ref != was.issuer_key_ref
                or now.public_key_digest != was.public_key_digest):
            if (now.public_key_digest == was.public_key_digest
                    or was.public_key_digest not in new.revoked_key_digests):
                raise PolicyLineageError("issuer rotation requires new key and revoked old key")


class PolicyLineage:
    """Bounded process-local journal. Lock is not durable or distributed CAS."""

    def __init__(self, genesis: IssuerPolicySnapshot) -> None:
        owned = _snapshot_copy(genesis)
        self._genesis = owned
        self._genesis_head = genesis_head(owned)
        self._head = self._genesis_head
        self._current = owned
        self._events: tuple[PolicyLineageEvent, ...] = ()
        self._seen_revision_refs = {owned.revision_ref}
        self._lock = Lock()

    def append(self, next_snapshot: IssuerPolicySnapshot, *,
               expected_head: str) -> PolicyLineageEvent:
        _digest(expected_head, "expected_head")
        with self._lock:
            if expected_head != self._head:
                raise PolicyLineageError("stale or forked expected policy head")
            if len(self._events) >= MAX_TRANSITIONS:
                raise PolicyLineageError("lineage transition limit reached")
            owned = _snapshot_copy(next_snapshot)
            if owned.revision_ref in self._seen_revision_refs:
                raise PolicyLineageError("policy revision ref cannot be reused")
            _validate_transition(self._current, owned)
            digest = policy_digest(owned)
            sequence = len(self._events) + 1
            event = PolicyLineageEvent(
                sequence=sequence,
                previous_head=self._head,
                snapshot=owned,
                snapshot_digest=digest,
                head_digest=_event_head(sequence, self._head, digest),
            )
            # Mutations occur only after all checks and hash generation.
            self._events += (event,)
            self._head = event.head_digest
            self._current = owned
            self._seen_revision_refs.add(owned.revision_ref)
            return _event_copy(event)

    def report(self) -> PolicyLineageReport:
        with self._lock:
            return PolicyLineageReport(
                genesis_snapshot=_snapshot_copy(self._genesis),
                genesis_head=self._genesis_head,
                head_digest=self._head,
                events=tuple(_event_copy(x) for x in self._events),
            )


def replay_policy_lineage(
    genesis: IssuerPolicySnapshot,
    events: tuple[PolicyLineageEvent, ...],
) -> PolicyLineageReport:
    if type(events) is not tuple or len(events) > MAX_TRANSITIONS:
        raise PolicyLineageError("events must be a bounded tuple")
    timeline = PolicyLineage(genesis)
    for item in events:
        if type(item) is not PolicyLineageEvent:
            raise PolicyLineageError("noncanonical lineage event")
        if type(item.sequence) is not int or item.sequence != len(timeline._events) + 1:
            raise PolicyLineageError("missing, repeated or reordered sequence")
        if type(item.snapshot) is not IssuerPolicySnapshot:
            raise PolicyLineageError("noncanonical policy snapshot in event")
        if item.previous_head != timeline._head:
            raise PolicyLineageError("lineage previous head mismatch")
        try:
            computed = timeline.append(item.snapshot, expected_head=item.previous_head)
        except (ValueError, TypeError) as exc:
            raise PolicyLineageError("invalid lineage transition") from exc
        if computed != item:
            raise PolicyLineageError("event contents/digests differ from canonical replay")
    return timeline.report()


def verify_policy_lineage(
    genesis: IssuerPolicySnapshot,
    events: tuple[PolicyLineageEvent, ...],
    *,
    expected_genesis_head: str,
    expected_current_head: str,
    expected_event_count: int,
) -> PolicyLineageVerification:
    """Compare replay to independently obtained expected state.

    Supplying one's own forged expectations can produce a mechanical match.
    There is no clock/remote authentication or actual trust-root here.
    """
    _digest(expected_genesis_head, "expected_genesis_head")
    _digest(expected_current_head, "expected_current_head")
    if (type(expected_event_count) is not int
            or not 0 <= expected_event_count <= MAX_TRANSITIONS):
        raise ValueError("expected_event_count must be a bounded integer")
    try:
        report = replay_policy_lineage(genesis, events)
    except (PolicyLineageError, ValueError, TypeError):
        return PolicyLineageVerification(
            status="invalid_history",
            reason_codes=("lineage_replay_invalid",),
            replayed_head=None,
            genesis_matches=False,
            head_matches=False,
            count_matches=False,
        )
    gmatch = report.genesis_head == expected_genesis_head
    hmatch = report.head_digest == expected_current_head
    cmatch = len(report.events) == expected_event_count
    reasons = []
    if not gmatch:
        reasons.append("independent_genesis_pin_mismatch")
    if not hmatch:
        reasons.append("independent_current_head_mismatch")
    if not cmatch:
        reasons.append("independent_event_count_mismatch")
    if not reasons:
        reasons.append("lineage_pin_provenance_and_freshness_unauthenticated")
    return PolicyLineageVerification(
        status="mechanical_match" if gmatch and hmatch and cmatch else "pin_mismatch",
        reason_codes=tuple(reasons),
        replayed_head=report.head_digest,
        genesis_matches=gmatch,
        head_matches=hmatch,
        count_matches=cmatch,
    )
