"""Explicit post-admission ranking policy (#538, #531).

Ranking orders candidates that canonical governed admission has *already admitted*.
It never admits, refuses, supersedes, mutates, or grants authority:

    candidate routes -> canonical admission / refusal -> admitted set -> ranking policy

A policy is a documented, versioned sequence of stages applied lexicographically:

1. route corroboration: the number of distinct candidate routes that surfaced the fact;
2. exact identity: surfaced by an exact logical-memory lookup;
3. route-native scores, one stage per route, in the policy's declared order. Scores from
   different routes are treated as not comparable with each other, so they are never
   summed or cross-scaled. Each route's own maximum raw score is compared only against
   the same route's score on other candidates. When ``lexical_relevance`` is
   ``bm25_admitted_set``, the lexical route's stage instead compares Okapi BM25
   (standard k1=1.2, b=0.75; untuned) of each admitted fact's text against the query,
   with term statistics computed over the admitted set only. The route's raw
   discovery score is still reported in evidence but no longer orders candidates;
4. temporal evidence: among candidates equal on every earlier stage, a candidate with
   explicit temporal evidence sorts before one without, and newer evidence before
   older. Temporal evidence is the fact's ``valid_at`` (event-time axis), falling back
   to ``created_at`` (transaction-time axis). Unparseable values count as absent, never
   guessed;
5. stable fallback: ascending ``candidate_ref``.

Temporal evidence is ordering evidence among equally relevant admitted candidates only.
Newer is not truer, and recency never changes admission, supersession, lifecycle, or
authority. Canonical currentness remains owned by governed correction and supersession.
Recall has no as-of/historical mode: superseded and tombstoned facts are refused at
admission, and history is served by ``history()``, which this policy does not order.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Sequence

POLICY_FAMILY = "agent-memory-post-admission-ranking"
POLICY_VERSION = "2.1.0"
BM25_K1 = 1.2
BM25_B = 0.75
_TOKEN = re.compile(r"[a-z0-9]+")


def relevance_tokens(text: str) -> list[str]:
    """Lower-cased alphanumeric tokens (``user's`` -> ``user``, ``s``)."""

    return _TOKEN.findall(text.lower())


def admitted_set_bm25(query: str, texts: Mapping[str, str]) -> dict[str, float]:
    """Okapi BM25 (standard k1=1.2, b=0.75) of each admitted text against the query.

    Term statistics (document frequency, average length) are computed over the
    **admitted set only**. Refused candidates, other scopes, and other tenants never
    contribute statistics, so their vocabulary cannot influence how an authorized
    requester's memories are ordered.
    """

    documents = {ref: relevance_tokens(text) for ref, text in texts.items()}
    count = len(documents)
    if not count:
        return {}
    average = sum(len(tokens) for tokens in documents.values()) / count or 1.0
    frequency = Counter(token for tokens in documents.values() for token in set(tokens))
    terms = set(relevance_tokens(query))
    scores: dict[str, float] = {}
    for ref, tokens in documents.items():
        term_counts = Counter(tokens)
        score = 0.0
        for term in terms:
            tf = term_counts.get(term, 0)
            if not tf:
                continue
            idf = math.log(1.0 + (count - frequency[term] + 0.5) / (frequency[term] + 0.5))
            score += idf * tf * (BM25_K1 + 1) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * len(tokens) / average))
        scores[ref] = score
    return scores


def temporal_evidence(fact: Any) -> tuple[str | None, str | None, float | None]:
    """Return (axis, raw value, POSIX seconds) for a fact's explicit temporal evidence."""

    if fact is None:
        return None, None, None
    for axis in ("valid_at", "created_at"):
        raw = getattr(fact, axis, None)
        if not raw:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return axis, str(raw), parsed.timestamp()
    return None, None, None


@dataclass(frozen=True)
class PostAdmissionRankingPolicy:
    """One explicit, inspectable, deterministic ordering over admitted candidates."""

    policy_id: str
    route_score_order: tuple[str, ...]
    exact_identity_route: str
    temporal_tiebreak: str = "newer_first"
    lexical_route: str | None = None
    lexical_relevance: str = "route_score"
    version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if self.temporal_tiebreak not in {"newer_first", "none"}:
            raise ValueError(f"unsupported temporal_tiebreak: {self.temporal_tiebreak}")
        if self.lexical_relevance not in {"route_score", "bm25_admitted_set"}:
            raise ValueError(f"unsupported lexical_relevance: {self.lexical_relevance}")
        if self.lexical_relevance == "bm25_admitted_set" and self.lexical_route not in self.route_score_order:
            raise ValueError("bm25_admitted_set requires lexical_route to be one of route_score_order")
        if len(set(self.route_score_order)) != len(self.route_score_order):
            raise ValueError("route_score_order must not repeat a route")

    def identity(self) -> dict[str, Any]:
        return {
            "policy_family": POLICY_FAMILY,
            "policy_id": self.policy_id,
            "policy_version": self.version,
            "stages": [
                "route_corroboration_count_desc",
                "exact_identity_desc",
                *[self._stage_name(route) for route in self.route_score_order],
                "temporal_evidence:" + self.temporal_tiebreak,
                "candidate_ref_asc",
            ],
            "route_scores_cross_comparable": False,
            "lexical_relevance": self.lexical_relevance,
            "lexical_relevance_statistics_scope": "admitted_set" if self.lexical_relevance == "bm25_admitted_set" else None,
            "bm25_parameters": {"k1": BM25_K1, "b": BM25_B} if self.lexical_relevance == "bm25_admitted_set" else None,
            "authority_effect": "none",
        }

    def _stage_name(self, route: str) -> str:
        if route == self.lexical_route and self.lexical_relevance == "bm25_admitted_set":
            return f"lexical_relevance_desc:bm25_admitted_set:{route}"
        return f"route_score_desc:{route}"

    def evidence(self, candidate_ref: str, hits: Sequence[Any], fact: Any) -> dict[str, Any]:
        route_ids = sorted({hit.route_id for hit in hits})
        scores = {
            route: max((float(hit.raw_score) for hit in hits if hit.route_id == route), default=None)
            for route in self.route_score_order
        }
        axis, raw, seconds = temporal_evidence(fact) if self.temporal_tiebreak != "none" else (None, None, None)
        return {
            "candidate_ref": candidate_ref,
            "routes": route_ids,
            "route_corroboration_count": len(route_ids),
            "exact_identity": self.exact_identity_route in route_ids,
            "route_scores": {route: score for route, score in scores.items() if score is not None},
            "temporal_axis": axis,
            "temporal_value": raw,
            "temporal_seconds": seconds,
        }

    def sort_key(self, evidence: Mapping[str, Any]) -> tuple[Any, ...]:
        key: list[Any] = [-evidence["route_corroboration_count"], -int(evidence["exact_identity"])]
        for route in self.route_score_order:
            if route == self.lexical_route and self.lexical_relevance == "bm25_admitted_set":
                key.append(-evidence.get("lexical_relevance_score", 0.0))
            else:
                key.append(-evidence["route_scores"].get(route, 0.0))
        if self.temporal_tiebreak == "newer_first":
            seconds = evidence["temporal_seconds"]
            key.extend([0 if seconds is not None else 1, -(seconds or 0.0)])
        key.append(evidence["candidate_ref"])
        return tuple(key)

    def rank(
        self,
        admitted: Iterable[str],
        hits_by_candidate: Mapping[str, Sequence[Any]],
        fact_lookup: Callable[[str], Any],
        query: str = "",
    ) -> tuple[list[str], dict[str, dict[str, Any]]]:
        """Order admitted candidates; return (ordered refs, per-candidate ranking evidence)."""

        admitted = list(admitted)
        facts = {candidate_ref: fact_lookup(candidate_ref) for candidate_ref in admitted}
        evidence = {
            candidate_ref: self.evidence(candidate_ref, hits_by_candidate.get(candidate_ref, ()), facts[candidate_ref])
            for candidate_ref in admitted
        }
        if self.lexical_relevance == "bm25_admitted_set":
            texts = {ref: getattr(fact, "fact_text", "") or "" for ref, fact in facts.items()}
            for ref, score in admitted_set_bm25(query, texts).items():
                evidence[ref]["lexical_relevance_score"] = score
        ordered = sorted(evidence, key=lambda candidate_ref: self.sort_key(evidence[candidate_ref]))
        identity = self.identity()
        for position, candidate_ref in enumerate(ordered, start=1):
            evidence[candidate_ref]["rank_position"] = position
            evidence[candidate_ref]["policy_id"] = identity["policy_id"]
            evidence[candidate_ref]["policy_version"] = identity["policy_version"]
            evidence[candidate_ref]["authority_effect"] = "none"
        return ordered, evidence
