"""Governed local retention for privacy-minimized telemetry projections.

Telemetry is derived operational state. This store never retains raw memory ids
or HMAC keys. Deletion receives the raw memory id transiently and resolves it
against every available telemetry key generation.

If retained projections use a key generation that is no longer available, a
memory-targeted purge is explicitly incomplete. Losing the key does not turn
unsearchable pseudonymous state into proof of deletion.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from ..core import receipts
from .telemetry import TelemetryProjector

TELEMETRY_CHECKPOINT_SCHEMA_VERSION = "1.0.0"
TELEMETRY_CHECKPOINT_OWNER = "telemetry_store"


@dataclass(frozen=True)
class TelemetryRecord:
    projection: dict
    expires_at: str


@dataclass(frozen=True)
class TelemetryPurgeResult:
    removed_count: int
    unresolved_key_ids: tuple[str, ...]
    complete: bool


class TelemetryStore:
    """In-memory reference store for minimized telemetry plus expiry metadata."""

    def __init__(self) -> None:
        self._records: list[TelemetryRecord] = []

    # -- declared checkpoint capability --------------------------------

    def export_checkpoint_state(self) -> dict:
        """Export retained telemetry evidence without raw memory ids or keys."""
        return {
            "schema_version": TELEMETRY_CHECKPOINT_SCHEMA_VERSION,
            "checkpoint_owner": TELEMETRY_CHECKPOINT_OWNER,
            "records": [
                {
                    "projection": copy.deepcopy(record.projection),
                    "expires_at": record.expires_at,
                }
                for record in self._records
            ],
        }

    def restore_checkpoint_state(self, snapshot: Mapping[str, object]) -> None:
        """Restore retained telemetry while preserving deletion uncertainty."""
        if snapshot.get("schema_version") != TELEMETRY_CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("unsupported telemetry checkpoint schema")
        if snapshot.get("checkpoint_owner") != TELEMETRY_CHECKPOINT_OWNER:
            raise ValueError("telemetry checkpoint owner mismatch")
        raw_records = snapshot.get("records")
        if not isinstance(raw_records, list):
            raise ValueError("telemetry checkpoint records are malformed")

        restored: list[TelemetryRecord] = []
        try:
            for raw in raw_records:
                if not isinstance(raw, Mapping):
                    raise TypeError("telemetry checkpoint row must be a mapping")
                projection = raw.get("projection")
                expires_at = raw.get("expires_at")
                if not isinstance(projection, Mapping):
                    raise TypeError("telemetry checkpoint projection must be a mapping")
                if not isinstance(expires_at, str) or not expires_at:
                    raise ValueError("telemetry checkpoint expires_at must be non-empty")
                projection_copy = copy.deepcopy(dict(projection))
                receipts.validate("telemetry-projection.schema.json", projection_copy)
                _parse_time(expires_at)
                restored.append(
                    TelemetryRecord(
                        projection=projection_copy,
                        expires_at=expires_at,
                    )
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("telemetry checkpoint cannot be reconstructed") from exc

        self._records = restored

    def append(self, projection: dict, *, expires_at: str) -> None:
        receipts.validate("telemetry-projection.schema.json", projection)
        _parse_time(expires_at)
        self._records.append(TelemetryRecord(projection=projection.copy(), expires_at=expires_at))

    def records(self) -> tuple[TelemetryRecord, ...]:
        return tuple(self._records)

    def purge_expired(self, *, now: str) -> int:
        cutoff = _parse_time(now)
        retained: list[TelemetryRecord] = []
        removed = 0
        for record in self._records:
            if _parse_time(record.expires_at) <= cutoff:
                removed += 1
            else:
                retained.append(record)
        self._records = retained
        return removed

    def purge_memory(
        self,
        memory_id: str,
        *,
        projectors: dict[str, TelemetryProjector],
    ) -> TelemetryPurgeResult:
        """Remove projections linked to one memory across every known key generation.

        Any retained key generation for which no projector is supplied makes the
        result incomplete because those records cannot be tested for membership
        in the target memory's telemetry closure.
        """
        if not memory_id:
            raise ValueError("memory_id must be non-empty")

        retained_key_ids = {record.projection["key_id"] for record in self._records}
        unresolved = tuple(sorted(retained_key_ids - set(projectors)))
        expected_refs = {
            key_id: projector.memory_ref(memory_id)
            for key_id, projector in projectors.items()
        }

        retained: list[TelemetryRecord] = []
        removed = 0
        for record in self._records:
            key_id = record.projection["key_id"]
            expected = expected_refs.get(key_id)
            memory_ref = record.projection["attributes"].get("am.memory_ref")
            if expected is not None and memory_ref == expected:
                removed += 1
            else:
                retained.append(record)
        self._records = retained

        return TelemetryPurgeResult(
            removed_count=removed,
            unresolved_key_ids=unresolved,
            complete=not unresolved,
        )


def _parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("telemetry retention timestamps must include timezone")
    return parsed.astimezone(timezone.utc)
