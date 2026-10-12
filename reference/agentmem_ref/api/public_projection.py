"""#777 public read projection: withhold deleted-generation identifiers from ordinary reads.

Applied to caller-facing responses only, AFTER canonical governance decided the read.
It never retrieves hidden text, never broadens admission, and never rewrites stored
semantics, tombstones or audit events. Detailed deletion records stay internal.
"""
from __future__ import annotations

from typing import Any, Callable

POLICY = {
    "policy_id": "public-deleted-lineage-redaction",
    "policy_version": "1.0.0",
    "deleted_lineage": "withheld",
}

#: Refusal reasons that would disclose a deletion relationship to an ordinary reader.
DELETION_REFUSALS = frozenset({
    "tombstoned", "derived_from_tombstoned_source",
    "logical_memory_deleted", "derived_from_deleted_logical_memory",
})


def withheld_predicate(adapter) -> Callable[[str], bool]:
    cache: dict[str, bool] = {}

    def withheld(value: str) -> bool:
        if value not in cache:
            cache[value] = bool(adapter.public_identifier_withheld(value) or adapter.public_memory_withheld(value))
        return cache[value]

    return withheld


def _mentions(value: Any, withheld: Callable[[str], bool]) -> bool:
    if isinstance(value, str):
        return withheld(value)
    if isinstance(value, dict):
        return any(withheld(k) or _mentions(v, withheld) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_mentions(v, withheld) for v in value)
    return False


def scrub(value: Any, withheld: Callable[[str], bool]) -> Any:
    """Drop list items and mapping entries that name a withheld identifier; blank scalar refs."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if withheld(key):
                continue
            if isinstance(item, str) and withheld(item):
                out[key] = ""
                continue
            out[key] = scrub(item, withheld)
        return out
    if isinstance(value, (list, tuple)):
        return [scrub(item, withheld) for item in value if not _mentions(item, withheld)]
    return value


def withheld_candidates(candidates, refusals, withheld: Callable[[str], bool]) -> set[str]:
    return {c for c in candidates if refusals.get(c) in DELETION_REFUSALS or withheld(c)}


def project_semantics(document: dict | None, withheld: Callable[[str], bool]) -> dict | None:
    if document is None:
        return None
    relations = [r for r in document.get("relations", ()) if not _mentions(r, withheld)]
    out = dict(document)
    if "relations" in document:
        out["relations"] = relations
    if "relation_count" in document:
        out["relation_count"] = len(relations)
    out["public_projection"] = dict(POLICY)
    return out
