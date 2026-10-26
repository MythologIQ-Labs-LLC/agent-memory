"""Source-only Graphiti EntityEdge -> benchmark source attribution probe.

Source pin #789 provides EntityEdge.episodes: list[str] and supports
Graphiti.add_episode(uuid=...). This does NOT invoke a vendor SDK, model,
database, or accept any benchmark result.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .source_identity_gate import Attribution, attribute_hits


def attribute_graphiti_edges(
    edges: Sequence[Any],
    *,
    episode_to_doc: Mapping[str, str],
    allowed_doc_ids: frozenset[str],
    top_k: int,
) -> Attribution:
    """Use ALL edge.episodes handles, never a text or gold-ID heuristic.

    episode_to_doc must derive only from actual add_episode source identity
    recorded at ingestion. Multi-document edge provenance remains ambiguous.
    """
    hits = [{"source_handles": getattr(edge, "episodes", None)} for edge in edges]
    return attribute_hits(
        hits,
        source_handles=episode_to_doc,
        allowed_document_ids=allowed_doc_ids,
        top_k=top_k,
    )
