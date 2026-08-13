"""Vendor-neutral admission evidence for model-internal conditional memory."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from . import receipts

NONCLAIMS = (
    "address_is_not_identity",
    "prefetch_is_not_admission",
    "external_deletion_is_not_internal_forgetting",
    "influence_is_not_mutation_authority",
    "collision_is_not_equivalence",
    "configured_gate_is_not_enforcement_proof",
)


def opaque_address_digest(address: Any) -> str:
    """Hash an address description without retaining token IDs or raw lookup values."""
    raw = json.dumps(address, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def decide_gate(
    *,
    table_partition: str | None,
    requested_partition: str | None,
    currentness: str | None,
    suppression: str | None,
) -> tuple[str, tuple[str, ...]]:
    """Return the narrowest explicit gate result for one influence attempt."""
    if not table_partition or not requested_partition:
        return "block_unknown", ("partition evidence unavailable",)
    if table_partition != requested_partition:
        return "block_scope", ("requested partition does not match active table partition",)
    if currentness in (None, "unknown"):
        return "block_unknown", ("table currentness unavailable",)
    if currentness != "current":
        return "block_stale", (f"table currentness is {currentness}",)
    if suppression in (None, "unknown"):
        return "block_unknown", ("suppression posture unavailable",)
    if suppression == "suppressed":
        return "block_suppressed", ("active suppression overlay applies",)
    if suppression != "clear":
        return "block_unknown", ("unsupported suppression posture",)
    return "allow", ("table current, partition matched, suppression clear",)


def normalize_influence(
    *,
    influence_id: str,
    lookup_ref: str,
    address: Any,
    table: dict[str, Any],
    request: dict[str, Any],
    currentness: str | None,
    suppression: str | None,
    enforcement_posture: str,
    correlation_ref: str,
    observed_at: str,
    collision_ref: str | None = None,
) -> dict[str, Any]:
    """Build privacy-minimized evidence for a conditional-memory influence gate."""
    result, reasons = decide_gate(
        table_partition=table.get("partition_ref"),
        requested_partition=request.get("partition_ref"),
        currentness=currentness,
        suppression=suppression,
    )
    document: dict[str, Any] = {
        "schema_version": "1.0.0",
        "profile_version": "0.1.0",
        "influence_id": influence_id,
        "lookup_ref": lookup_ref,
        "opaque_address_digest": opaque_address_digest(address),
        "table": dict(table),
        "request": dict(request),
        "currentness": currentness or "unknown",
        "suppression": suppression or "unknown",
        "gate": {
            "result": result,
            "reasons": list(reasons),
            "influence_eligible": result == "allow",
        },
        "enforcement_posture": enforcement_posture,
        "correlation_ref": correlation_ref,
        "observed_at": observed_at,
        "nonclaims": list(NONCLAIMS),
    }
    if collision_ref:
        document["collision_ref"] = collision_ref
    receipts.validate("conditional-memory-influence.schema.json", document)
    return document


def validate_table_replacement(old_record: dict[str, Any], new_record: dict[str, Any]) -> None:
    """Prove replacement identity without mutating historical influence evidence."""
    receipts.validate("conditional-memory-influence.schema.json", old_record)
    receipts.validate("conditional-memory-influence.schema.json", new_record)
    old_table = old_record["table"]
    new_table = new_record["table"]
    if old_table["table_id"] == new_table["table_id"]:
        raise ValueError("replacement table must have distinct table identity")
    if old_table["table_digest"] == new_table["table_digest"]:
        raise ValueError("replacement table must have distinct artifact digest")
    if new_record["gate"]["result"] == "allow" and new_record["currentness"] != "current":
        raise ValueError("replacement cannot be influence-eligible without current evidence")
