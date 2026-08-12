"""Deterministic rejected-value history for governed re-admission.

This module implements only the exact/normalized identity slice proven by #147.
It deliberately does not attempt semantic-equivalence detection. A learned or
probabilistic matcher may later propose a reconciliation path, but it must not
independently authorize durable rejection or re-admission.

Raw memory content is not retained here. Rejection history stores a scoped
SHA-256 fingerprint plus provenance needed to reconstruct the lifecycle event.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


def normalize_value(value: str) -> str:
    """Canonicalize only deterministic presentation differences.

    Case and repeated whitespace are normalized. Punctuation, word order, and
    semantic paraphrase are intentionally untouched so this helper cannot
    quietly become a probabilistic equivalence oracle.
    """

    return " ".join(value.casefold().split())


def value_fingerprint(value: str) -> str:
    normalized = normalize_value(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class RejectionRecord:
    memory_id: str
    value_fingerprint: str
    superseded_fact_uuid: str
    correction_proposal_id: str
    evidence_refs: tuple[str, ...]
    scope: str
    rejected_at: str
    active: bool = True
    readmitted_at: str | None = None
    readmission_proposal_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "value_fingerprint": self.value_fingerprint,
            "superseded_fact_uuid": self.superseded_fact_uuid,
            "correction_proposal_id": self.correction_proposal_id,
            "evidence_refs": list(self.evidence_refs),
            "scope": self.scope,
            "rejected_at": self.rejected_at,
            "active": self.active,
            "readmitted_at": self.readmitted_at,
            "readmission_proposal_id": self.readmission_proposal_id,
        }


class RejectedValueRegistry:
    """Append-oriented rejection history keyed by memory and exact value identity."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], list[RejectionRecord]] = {}

    def _key(self, memory_id: str, value: str) -> tuple[str, str]:
        return memory_id, value_fingerprint(value)

    def active(self, memory_id: str, value: str) -> RejectionRecord | None:
        records = self._records.get(self._key(memory_id, value), ())
        for record in reversed(records):
            if record.active:
                return record
        return None

    def reject(
        self,
        *,
        memory_id: str,
        value: str,
        superseded_fact_uuid: str,
        correction_proposal_id: str,
        evidence_refs: tuple[str, ...],
        scope: str,
        rejected_at: str,
    ) -> RejectionRecord:
        record = RejectionRecord(
            memory_id=memory_id,
            value_fingerprint=value_fingerprint(value),
            superseded_fact_uuid=superseded_fact_uuid,
            correction_proposal_id=correction_proposal_id,
            evidence_refs=tuple(evidence_refs),
            scope=scope,
            rejected_at=rejected_at,
        )
        self._records.setdefault(self._key(memory_id, value), []).append(record)
        return record

    def readmit(
        self,
        *,
        memory_id: str,
        value: str,
        proposal_id: str,
        readmitted_at: str,
    ) -> RejectionRecord | None:
        record = self.active(memory_id, value)
        if record is None:
            return None
        record.active = False
        record.readmitted_at = readmitted_at
        record.readmission_proposal_id = proposal_id
        return record

    def history(self, memory_id: str, value: str) -> tuple[dict, ...]:
        return tuple(record.as_dict() for record in self._records.get(self._key(memory_id, value), ()))
