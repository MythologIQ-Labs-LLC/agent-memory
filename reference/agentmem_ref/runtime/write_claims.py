"""Reference pre-write coordination for shared durable memory.

This module is evidence for proposed ADR-024. It does not replace PAMA and it
does not prescribe one distributed lock implementation. A claim establishes a
narrow coordination right to *attempt* a shared write. The governed adapter
still evaluates the proposal and remains the authority boundary for durable
mutation.

The reference mechanism is deliberately small:

claim -> acquire/reject -> revalidate before commit -> PAMA -> mutation/refusal

Claims bind actor, task, scope, target, mutation class, authority basis, state
snapshot, and lease validity. Conflicts, stale state, expiry, unauthorized
claims, and claim/proposal mismatches fail before the adapter is allowed to
attempt the durable mutation. Every outcome remains audit evidence.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable, Mapping

from ..core import policy, receipts
from .adapter import CommitResult, GovernedMemoryAdapter

ACQUIRED = "acquired"
REJECTED = "rejected"
EXPIRED = "expired"
COMMITTED = "committed"
INVALIDATED = "invalidated"

WRITE_CLAIM_CHECKPOINT_SCHEMA_VERSION = "1.0.0"
WRITE_CLAIM_CHECKPOINT_OWNER = "shared_write_coordinator"
RESTART_INVALIDATION_REASON = "process_restart_invalidated_active_claim"


@dataclass(frozen=True)
class WriteClaim:
    claim_id: str
    actor_id: str
    task_id: str
    scope: str
    target_reference: str
    mutation_class: str
    authority_ref: str
    state_snapshot: str
    issued_at: str
    expires_at: str


@dataclass
class ClaimRecord:
    claim: WriteClaim
    status: str
    reason: str | None = None
    events: list[dict] = field(default_factory=list)
    commit_result: CommitResult | None = None
    commit_receipt_ref: str | None = None


class SharedWriteCoordinator:
    """Exact-scope reference coordinator for ADR-024 evidence.

    ``authority_resolver`` answers only whether the actor may acquire the
    coordination claim identified by ``authority_ref``. It does not evaluate
    PAMA and cannot authorize the durable mutation. ``adapter.commit_proposal``
    remains mandatory after claim validation.
    """

    def __init__(
        self,
        adapter: GovernedMemoryAdapter,
        authority_resolver: Callable[[WriteClaim], bool],
        now: Callable[[], str],
    ) -> None:
        self._adapter = adapter
        self._authority_resolver = authority_resolver
        self._now = now
        self._records: dict[str, ClaimRecord] = {}
        self._active_by_key: dict[tuple[str, str], str] = {}
        self._event_counter = 0
        self.events: list[dict] = []

    # -- declared checkpoint capability --------------------------------

    def export_checkpoint_state(self) -> dict:
        """Export claim/audit evidence without treating a lease as durable authority."""
        return {
            "schema_version": WRITE_CLAIM_CHECKPOINT_SCHEMA_VERSION,
            "checkpoint_owner": WRITE_CLAIM_CHECKPOINT_OWNER,
            "event_counter": self._event_counter,
            "records": [
                {
                    "claim": asdict(record.claim),
                    "status": record.status,
                    "reason": record.reason,
                    "events": copy.deepcopy(record.events),
                    "commit_receipt_ref": record.commit_receipt_ref,
                }
                for _, record in sorted(self._records.items())
            ],
            "events": copy.deepcopy(self.events),
        }

    def restore_checkpoint_state(self, snapshot: Mapping[str, object]) -> None:
        """Restore claim evidence while invalidating every pre-crash active lease.

        An in-process coordination lease is not durable authority. Any claim that
        was ``ACQUIRED`` at the checkpoint boundary is restored as ``INVALIDATED``
        with a new audit event and is deliberately omitted from the active-key
        index. A fresh claim is required before another shared mutation attempt.
        """
        if snapshot.get("schema_version") != WRITE_CLAIM_CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("unsupported write-claim checkpoint schema")
        if snapshot.get("checkpoint_owner") != WRITE_CLAIM_CHECKPOINT_OWNER:
            raise ValueError("write-claim checkpoint owner mismatch")
        raw_records = snapshot.get("records")
        raw_events = snapshot.get("events")
        raw_counter = snapshot.get("event_counter")
        if not isinstance(raw_records, list) or not isinstance(raw_events, list):
            raise ValueError("write-claim checkpoint collections are malformed")
        try:
            event_counter = int(raw_counter)
        except (TypeError, ValueError) as exc:
            raise ValueError("write-claim checkpoint event counter is malformed") from exc
        if event_counter < 0:
            raise ValueError("write-claim checkpoint event counter cannot be negative")

        records: dict[str, ClaimRecord] = {}
        events: list[dict] = []
        allowed_statuses = {ACQUIRED, REJECTED, EXPIRED, COMMITTED, INVALIDATED}
        try:
            for raw_event in raw_events:
                event = _validated_event_copy(raw_event)
                events.append(event)

            max_event_sequence = max((_event_sequence(event) for event in events), default=0)
            if event_counter < max_event_sequence:
                raise ValueError("write-claim checkpoint event counter rewinds audit identity")

            for raw in raw_records:
                if not isinstance(raw, Mapping):
                    raise TypeError("write-claim checkpoint row must be a mapping")
                raw_claim = raw.get("claim")
                if not isinstance(raw_claim, Mapping):
                    raise TypeError("write-claim checkpoint claim must be a mapping")
                claim = WriteClaim(**dict(raw_claim))
                self._validate_shape(claim)
                if claim.claim_id in records:
                    raise ValueError("duplicate write-claim identity")

                status = raw.get("status")
                if status not in allowed_statuses:
                    raise ValueError("write-claim checkpoint has unknown status")
                reason = raw.get("reason")
                if reason is not None and not isinstance(reason, str):
                    raise ValueError("write-claim checkpoint reason must be string or null")
                raw_record_events = raw.get("events", [])
                if not isinstance(raw_record_events, list):
                    raise ValueError("write-claim record events must be a list")
                record_events = [
                    _validated_event_copy(event) for event in raw_record_events
                ]
                receipt_ref = raw.get("commit_receipt_ref")
                if receipt_ref is not None and not isinstance(receipt_ref, str):
                    raise ValueError("write-claim commit receipt ref must be string or null")
                if status == COMMITTED and not receipt_ref:
                    raise ValueError("committed write-claim checkpoint requires receipt reference")

                records[claim.claim_id] = ClaimRecord(
                    claim=claim,
                    status=str(status),
                    reason=reason,
                    events=record_events,
                    commit_result=None,
                    commit_receipt_ref=receipt_ref,
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("write-claim checkpoint cannot be reconstructed") from exc

        self._records = records
        self._active_by_key = {}
        self._event_counter = event_counter
        self.events = events

        for claim_id in sorted(self._records):
            record = self._records[claim_id]
            if record.status != ACQUIRED:
                continue
            timestamp = self._now()
            record.status = INVALIDATED
            record.reason = RESTART_INVALIDATION_REASON
            event = self._event(
                "memory.write_claim_invalidated",
                record.claim,
                timestamp,
                status=INVALIDATED,
                reason=RESTART_INVALIDATION_REASON,
            )
            record.events.append(event)
            self.events.append(event)

    def acquire(self, claim: WriteClaim) -> ClaimRecord:
        if claim.claim_id in self._records:
            raise ValueError(f"claim already exists: {claim.claim_id}")
        self._validate_shape(claim)
        now = self._now()
        key = self._key(claim)

        active_id = self._active_by_key.get(key)
        if active_id:
            active = self._records[active_id]
            if self._is_expired(active.claim, now):
                self._expire(active, now, "lease_expired_before_conflicting_acquire")
            elif active.status == ACQUIRED:
                return self._record_rejection(claim, now, "claim_conflict")

        if self._is_expired(claim, now):
            return self._record_expiry(claim, now, "claim_expired")
        if not self._authority_resolver(claim):
            return self._record_rejection(claim, now, "unauthorized_claim")

        current_state = self._state_snapshot(claim.target_reference)
        if claim.state_snapshot != current_state:
            return self._record_rejection(claim, now, "stale_claim")

        event = self._event("memory.write_claim_acquired", claim, now, status=ACQUIRED)
        record = ClaimRecord(claim=claim, status=ACQUIRED, events=[event])
        self._records[claim.claim_id] = record
        self._active_by_key[key] = claim.claim_id
        self.events.append(event)
        return record

    def commit(self, claim_id: str, proposal: policy.Proposal, fact_text: str) -> ClaimRecord:
        record = self._records.get(claim_id)
        if record is None:
            raise ValueError(f"unknown claim: {claim_id}")
        if record.status != ACQUIRED:
            return record

        now = self._now()
        claim = record.claim
        reason = self._precommit_refusal(claim, proposal, now)
        if reason == "claim_expired":
            self._expire(record, now, reason)
            return record
        if reason:
            self._reject(record, now, reason)
            return record

        result = self._adapter.commit_proposal(proposal, fact_text)
        record.commit_result = result
        record.commit_receipt_ref = result.receipt["receipt_id"]
        if result.committed:
            record.status = COMMITTED
            record.reason = None
            event = self._event(
                "memory.write_claim_committed",
                claim,
                self._now(),
                status=COMMITTED,
                receipt_ref=result.receipt["receipt_id"],
                extra_payload={"pama_outcome": result.decision.outcome},
            )
            record.events.append(event)
            self.events.append(event)
            self._release(record)
            return record

        # A valid coordination claim is not authority. PAMA or another adapter
        # guard may still refuse the mutation, and that refusal is preserved.
        record.status = REJECTED
        record.reason = result.refusal or "pama_not_committed"
        event = self._event(
            "memory.write_claim_rejected",
            claim,
            self._now(),
            status=REJECTED,
            reason=record.reason,
            receipt_ref=result.receipt["receipt_id"],
            extra_payload={
                "pama_outcome": result.decision.outcome,
                "selected_action": result.receipt["selected_action"],
            },
        )
        record.events.append(event)
        self.events.append(event)
        self._release(record)
        return record

    def record(self, claim_id: str) -> ClaimRecord | None:
        return self._records.get(claim_id)

    def active_claim_id(self, scope: str, target_reference: str) -> str | None:
        return self._active_by_key.get((scope, target_reference))

    def _precommit_refusal(self, claim: WriteClaim, proposal: policy.Proposal, now: str) -> str | None:
        if self._is_expired(claim, now):
            return "claim_expired"
        if self._active_by_key.get(self._key(claim)) != claim.claim_id:
            return "claim_not_active"
        if claim.actor_id != proposal.actor_id:
            return "claim_actor_mismatch"
        if claim.scope != proposal.scope:
            return "claim_scope_mismatch"
        if claim.target_reference != proposal.target_reference:
            return "claim_target_mismatch"
        if claim.mutation_class != proposal.operation:
            return "claim_mutation_mismatch"
        if claim.task_id and claim.task_id != proposal.task_ref:
            return "claim_task_mismatch"
        current_state = self._state_snapshot(claim.target_reference)
        if claim.state_snapshot != current_state:
            return "stale_claim"
        if proposal.state_snapshot and proposal.state_snapshot != claim.state_snapshot:
            return "claim_state_mismatch"
        return None

    def _record_rejection(self, claim: WriteClaim, now: str, reason: str) -> ClaimRecord:
        event = self._event("memory.write_claim_rejected", claim, now, status=REJECTED, reason=reason)
        record = ClaimRecord(claim=claim, status=REJECTED, reason=reason, events=[event])
        self._records[claim.claim_id] = record
        self.events.append(event)
        return record

    def _record_expiry(self, claim: WriteClaim, now: str, reason: str) -> ClaimRecord:
        event = self._event("memory.write_claim_expired", claim, now, status=EXPIRED, reason=reason)
        record = ClaimRecord(claim=claim, status=EXPIRED, reason=reason, events=[event])
        self._records[claim.claim_id] = record
        self.events.append(event)
        return record

    def _reject(self, record: ClaimRecord, now: str, reason: str) -> None:
        record.status = REJECTED
        record.reason = reason
        event = self._event("memory.write_claim_rejected", record.claim, now, status=REJECTED, reason=reason)
        record.events.append(event)
        self.events.append(event)
        self._release(record)

    def _expire(self, record: ClaimRecord, now: str, reason: str) -> None:
        record.status = EXPIRED
        record.reason = reason
        event = self._event("memory.write_claim_expired", record.claim, now, status=EXPIRED, reason=reason)
        record.events.append(event)
        self.events.append(event)
        self._release(record)

    def _release(self, record: ClaimRecord) -> None:
        key = self._key(record.claim)
        if self._active_by_key.get(key) == record.claim.claim_id:
            self._active_by_key.pop(key, None)

    def _state_snapshot(self, target_reference: str) -> str:
        return f"v{self._adapter.state_version(target_reference)}"

    @staticmethod
    def _key(claim: WriteClaim) -> tuple[str, str]:
        return (claim.scope, claim.target_reference)

    @staticmethod
    def _parse_time(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid claim timestamp: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @classmethod
    def _is_expired(cls, claim: WriteClaim, now: str) -> bool:
        return cls._parse_time(now) >= cls._parse_time(claim.expires_at)

    @classmethod
    def _validate_shape(cls, claim: WriteClaim) -> None:
        for name in (
            "claim_id",
            "actor_id",
            "task_id",
            "scope",
            "target_reference",
            "mutation_class",
            "authority_ref",
            "state_snapshot",
            "issued_at",
            "expires_at",
        ):
            if not getattr(claim, name):
                raise ValueError(f"claim field {name} must be non-empty")
        if cls._parse_time(claim.expires_at) <= cls._parse_time(claim.issued_at):
            raise ValueError("claim expires_at must be later than issued_at")

    def _event(
        self,
        event_type: str,
        claim: WriteClaim,
        timestamp: str,
        *,
        status: str,
        reason: str | None = None,
        receipt_ref: str | None = None,
        extra_payload: dict | None = None,
    ) -> dict:
        self._event_counter += 1
        payload = {
            "claim_id": claim.claim_id,
            "task_id": claim.task_id,
            "scope": claim.scope,
            "mutation_class": claim.mutation_class,
            "authority_ref": claim.authority_ref,
            "state_snapshot": claim.state_snapshot,
            "issued_at": claim.issued_at,
            "expires_at": claim.expires_at,
            "status": status,
        }
        if reason:
            payload["reason"] = reason
        if extra_payload:
            payload.update(extra_payload)
        document = {
            "schema_version": "1.0.0",
            "event_id": f"write-claim-event:{self._event_counter}",
            "event_type": event_type,
            "event_version": "1.0.0",
            "timestamp": timestamp,
            "component": "shared-write-coordinator",
            "memory_id": claim.target_reference,
            "actor": claim.actor_id,
            "correlation_id": claim.claim_id,
            "authority": {"authority_refs": [claim.authority_ref]},
            "payload": payload,
        }
        if receipt_ref:
            document["receipt_ref"] = receipt_ref
        receipts.validate("memory-audit-event.schema.json", document)
        return document


def _validated_event_copy(raw: object) -> dict:
    if not isinstance(raw, Mapping):
        raise TypeError("write-claim audit event must be a mapping")
    event = copy.deepcopy(dict(raw))
    receipts.validate("memory-audit-event.schema.json", event)
    return event


def _event_sequence(event: Mapping[str, object]) -> int:
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id.startswith("write-claim-event:"):
        return 0
    try:
        return int(event_id.rsplit(":", 1)[1])
    except ValueError as exc:
        raise ValueError("write-claim event id sequence is malformed") from exc
