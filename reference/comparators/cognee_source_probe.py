"""Source-only Cognee CHUNKS retrieval -> exact benchmark source probe.

At pinned Cognee 1.4.2, DocumentChunk.document_id is source Document.id,
ChunksRetriever returns vector hit payloads, and Cognee's own references
renderer reads payload["document_id"]. No Cognee import or model call here.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .source_identity_gate import Attribution, attribute_hits


def attribute_cognee_chunks(
    chunk_payloads: Sequence[Mapping[str, Any]],
    *,
    cognee_data_id_to_doc: Mapping[str, str],
    allowed_doc_ids: frozenset[str],
    top_k: int,
) -> Attribution:
    """Attribute ONLY native CHUNKS payload.document_id from real ingestion.

    Ingestion must separately prove every key is the Cognee Data/Document id
    returned for the matching benchmark input. document_name, text,
    dataset ids, QA references and completion outputs are not source identities.

    This helper validates the source ID mapping, not the Cognee install or
    provenance completeness, and refuses any untraceable hit at scoring time.
    """
    if isinstance(chunk_payloads, (str, bytes)) or not isinstance(chunk_payloads, Sequence):
        raise TypeError("Cognee CHUNKS results must be a sequence of payload mappings")
    hits: list[dict[str, Any]] = []
    for payload in chunk_payloads:
        if not isinstance(payload, Mapping):
            hits.append({"source_handles": None})
            continue
        data_id = payload.get("document_id")
        handles = [data_id] if isinstance(data_id, str) and data_id else None
        hits.append({"source_handles": handles})
    return attribute_hits(
        hits,
        source_handles=cognee_data_id_to_doc,
        allowed_document_ids=allowed_doc_ids,
        top_k=top_k,
    )
