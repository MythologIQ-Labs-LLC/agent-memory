"""Fail-closed source attribution gate for prospective external memory adapters.

Does NOT claim vendor integration or same-harness qualification. Protects exact
source IDs from opaque provider IDs, gold leakage and content-based guesses.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Attribution:
    status: str
    ranked: tuple[str, ...]
    unmapped_hits: int
    ambiguous_hits: int
    invalid_hits: int
    duplicate_hits: int
    raw_hits: int
    notes: tuple[str, ...]

    def ranked_for_scoring(self) -> tuple[str, ...]:
        """Refuse numerical import unless all observed hits were attributable."""
        if self.status != "attributed":
            raise ValueError(f"external evidence is not fully attributable: {self.status}")
        return self.ranked

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "ranked": list(self.ranked),
            "unmapped_hits": self.unmapped_hits,
            "ambiguous_hits": self.ambiguous_hits,
            "invalid_hits": self.invalid_hits,
            "duplicate_hits": self.duplicate_hits,
            "raw_hits": self.raw_hits,
            "notes": list(self.notes),
        }


def attribute_hits(
    provider_hits: Sequence[Mapping],
    *,
    source_handles: Mapping[str, str],
    allowed_document_ids: frozenset[str],
    top_k: int,
) -> Attribution:
    """Map native ingestion source handles to allowed benchmark document IDs.

    Input per hit: {"source_handles": [<native_handle>, ...]}. A hit may
    contribute to ranking only when ALL its native handles resolve to exactly
    ONE allowed ingested document. Unknown/mixed provenance is never guessed.
    The ingestion map must cover every allowed document: a corpus that was not
    fully ingested is refused rather than scored as misses.

    This function does not interpret gold answers, source text, or fuzzy
    similarity as source identity. The provider's native rank order is retained.
    """
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if isinstance(provider_hits, (str, bytes)) or not isinstance(provider_hits, Sequence):
        raise TypeError("provider_hits must be a sequence")
    if not isinstance(allowed_document_ids, frozenset) or not allowed_document_ids:
        raise ValueError("allowed_document_ids must be a nonempty frozen set")
    for handle, doc_id in source_handles.items():
        if not isinstance(handle, str) or not handle or not isinstance(doc_id, str) or not doc_id:
            raise ValueError("source mapping must use nonempty strings")
        if doc_id not in allowed_document_ids:
            raise ValueError("ingestion map includes an out-of-scope document ID")
        if handle in allowed_document_ids and handle != doc_id:
            raise ValueError("a native handle that names an allowed document ID must map to itself")
    if allowed_document_ids - set(source_handles.values()):
        # An un-ingested document can never be retrieved, so scoring it would turn an
        # ingestion failure into a scored miss. The adapter must record ingestion
        # failure as a typed outcome instead of calling the gate.
        raise ValueError("ingestion map must cover every allowed document ID")

    ranked: list[str] = []
    seen: set[str] = set()
    diagnostics = {"unmapped_hits": 0, "ambiguous_hits": 0, "invalid_hits": 0, "duplicate_hits": 0}
    reasons = set()
    for hit in provider_hits:
        if not isinstance(hit, Mapping):
            diagnostics["invalid_hits"] += 1
            reasons.add("invalid_hit_shape")
            continue
        refs = hit.get("source_handles")
        if not isinstance(refs, (list, tuple)) or not refs or any(not isinstance(h, str) or not h for h in refs):
            diagnostics["unmapped_hits"] += 1
            reasons.add("source_provenance_absent")
            continue
        if any(h not in source_handles for h in refs):
            diagnostics["unmapped_hits"] += 1
            reasons.add("unrecognized_native_source_handle")
            continue
        docs = {source_handles[h] for h in refs}
        if len(docs) != 1:
            diagnostics["ambiguous_hits"] += 1
            reasons.add("multi_document_provenance")
            continue
        doc = next(iter(docs))
        if doc in seen:
            diagnostics["duplicate_hits"] += 1
            continue
        seen.add(doc)
        if len(ranked) < top_k:
            ranked.append(doc)
    if provider_hits and not ranked and (
        diagnostics["unmapped_hits"] or diagnostics["ambiguous_hits"] or diagnostics["invalid_hits"]
    ):
        status = "unsupported_source_identity"
    elif any(diagnostics[n] for n in ("unmapped_hits", "ambiguous_hits", "invalid_hits")):
        status = "partial_source_attribution"
    else:
        status = "attributed"
    return Attribution(
        status, tuple(ranked), **diagnostics, raw_hits=len(provider_hits), notes=tuple(sorted(reasons))
    )
