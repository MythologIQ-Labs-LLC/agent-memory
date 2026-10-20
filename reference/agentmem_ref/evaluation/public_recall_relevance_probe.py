"""Evaluation-only #775/#819 probe over PUBLIC returned recall IDs.

Never reads the substrate, requests candidate or refused content, or changes
admission/ranking. Caller-provided text and typed claims are not authenticated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .subject_relevance_challenge import ChallengeInput, ChallengeResult, challenge


@dataclass(frozen=True)
class PublicRelevanceObservation:
    fact_ref: str
    route_ids: tuple[str, ...]
    status: str
    relevance: ChallengeResult | None = None
    authority_effect: str = "none"


def inspect_returned(
    recall: Mapping[str, Any],
    authorized_content: Mapping[str, str],
    annotations: Mapping[str, ChallengeInput],
) -> tuple[PublicRelevanceObservation, ...]:
    """Only inspect returned PUBLIC references; inputs are not trust roots."""
    returned = recall.get("returned")
    admitted = recall.get("admitted")
    admissions = recall.get("admissions")
    if not isinstance(returned, list) or not isinstance(admitted, list):
        raise ValueError("public recall returned/admitted must be lists")
    if not isinstance(admissions, Mapping):
        raise ValueError("public recall admissions must be a mapping")
    if any(not isinstance(ref, str) or not ref for ref in returned):
        raise ValueError("public returned references must be strings")
    if len(returned) != len(set(returned)):
        raise ValueError("public returned references must be unique")
    if any(ref not in admitted for ref in returned):
        raise ValueError("public returned reference is not admitted")
    # Only access content/annotations for returned refs, never candidate IDs.
    records: list[PublicRelevanceObservation] = []
    for ref in returned:
        receipt = admissions.get(ref)
        if not isinstance(receipt, Mapping):
            raise ValueError("public returned reference lacks admission receipt")
        routes = receipt.get("route_provenance") or ()
        if not isinstance(routes, (list, tuple)):
            raise ValueError("invalid route provenance")
        route_ids = tuple(sorted({
            hit["route_id"] for hit in routes
            if isinstance(hit, Mapping) and isinstance(hit.get("route_id"), str)
        }))
        memory_text = authorized_content.get(ref)
        item = annotations.get(ref)
        if not isinstance(memory_text, str) or not isinstance(item, ChallengeInput):
            records.append(PublicRelevanceObservation(ref, route_ids, "unresolved"))
            continue
        # Annotation verification flags are claims, not authenticated evidence.
        inspected = ChallengeInput(
            query=item.query,
            memory_text=memory_text,
            query_subject_refs=item.query_subject_refs,
            memory_subject_refs=item.memory_subject_refs,
            related_subject_refs=item.related_subject_refs,
            query_property_refs=item.query_property_refs,
            memory_property_refs=item.memory_property_refs,
            identity_binding_checked=item.identity_binding_checked,
        )
        records.append(PublicRelevanceObservation(
            ref, route_ids, "inspected", challenge(inspected),
        ))
    return tuple(records)


__all__ = ["PublicRelevanceObservation", "inspect_returned"]
