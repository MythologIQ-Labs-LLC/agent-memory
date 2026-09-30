"""Typed temporal lexical anti-laundering evidence for post-admission ranking (#583).

This module does not rank, admit, refuse, supersede, or mutate anything. It converts two
already-governed evidence sources into a narrow per-candidate lexical mask:

* #585 query temporal-intent spans identify which query token occurrences were consumed
  as high-confidence temporal intent for the resolved ordering mode;
* #550/#598 persisted write semantics identify candidates carrying high-risk untrusted
  self-claims.

The query is never globally rewritten. Ordinary candidates keep every lexical term.
A normalized term is mask-eligible only when *every* occurrence of that term in the
original query is wholly covered by a high-confidence consumed span for the resolved,
temporally-ordering intent. A content/declined/weak occurrence therefore keeps the
whole normalized term lexical, matching BM25's set-of-query-terms contract.

Candidate masking is deliberately narrower than ``markers.self_claims``. ``authority``
and ``verification`` are not sufficient because the current write interpreter also uses
those categories for ordinary words such as ``official`` and ``verified``. Only
``currentness``, ``supersession`` and ``instruction`` activate this guard.

Masking carries no temporal bonus and no currentness or authority. The ranking policy is
responsible for applying the returned mask without changing sorted term accumulation.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping

from .proposition_semantics import WRITE_SEMANTICS_KEY
from .temporal_intent import TemporalIntent

_TERM = re.compile(r"[a-z0-9]+")
HIGH_RISK_SELF_CLAIMS = frozenset({"currentness", "instruction", "supersession"})


def lexical_term_occurrences(text: str) -> tuple[tuple[str, int, int], ...]:
    """BM25-compatible normalized terms with source offsets in ``text``."""

    return tuple((match.group(0), match.start(), match.end()) for match in _TERM.finditer(text.lower()))


def eligible_temporal_query_terms(query: str, intent: TemporalIntent) -> tuple[str, ...]:
    """Return normalized query terms that are exclusively high-confidence intent spans.

    BM25 currently collapses query terms to a set. If the same normalized term appears
    once as temporal intent and once as content, occurrence-specific deletion cannot be
    represented safely at ranking time. Such a term therefore remains lexical in full.
    """

    if not intent.orders_temporally:
        return ()
    spans = tuple(
        span for span in intent.spans
        if span.mode == intent.mode and span.confidence == "high"
    )
    if not spans:
        return ()

    occurrences: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for term, start, end in lexical_term_occurrences(query):
        occurrences[term].append((start, end))

    eligible = []
    for term, ranges in occurrences.items():
        if all(any(span.start <= start and end <= span.end for span in spans) for start, end in ranges):
            eligible.append(term)
    return tuple(sorted(eligible))


def persisted_self_claims(fact: Any) -> tuple[str, ...]:
    """Read only the self-claim classes persisted with this fact; never reinterpret text."""

    attributes = getattr(fact, "attributes", None) or {}
    semantics = attributes.get(WRITE_SEMANTICS_KEY) if isinstance(attributes, Mapping) else None
    if not isinstance(semantics, Mapping):
        return ()
    markers = semantics.get("markers") or {}
    if not isinstance(markers, Mapping):
        return ()
    claims = markers.get("self_claims") or ()
    return tuple(sorted(str(claim) for claim in claims))


def is_high_risk_self_claim_candidate(fact: Any) -> bool:
    """Whether persisted evidence permits candidate-specific temporal lexical masking."""

    return bool(HIGH_RISK_SELF_CLAIMS & set(persisted_self_claims(fact)))


def suppressed_terms_for_candidate(query: str, intent: TemporalIntent, fact: Any) -> tuple[str, ...]:
    """Eligible temporal terms actually present in one high-risk candidate's text."""

    if not is_high_risk_self_claim_candidate(fact):
        return ()
    eligible = set(eligible_temporal_query_terms(query, intent))
    if not eligible:
        return ()
    document_terms = {term for term, _, _ in lexical_term_occurrences(getattr(fact, "fact_text", "") or "")}
    return tuple(sorted(eligible & document_terms))


def candidate_term_masks(
    query: str,
    intent: TemporalIntent,
    facts: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    """One deterministic lexical mask per candidate, including explicit empty masks."""

    return {
        candidate_ref: suppressed_terms_for_candidate(query, intent, fact)
        for candidate_ref, fact in facts.items()
    }
