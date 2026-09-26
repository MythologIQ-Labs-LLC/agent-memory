"""Explicit post-admission ranking and query-conditioned applicability (#538, ADR-039 proposed).

Ranking orders candidates that canonical governed admission has *already admitted*.
It never admits, refuses, supersedes, mutates, or grants authority:

    candidate routes -> canonical admission / refusal -> admitted set
        -> typed relevance evidence + typed temporal evidence
        -> query-conditioned applicability policy -> ordered recall

A policy is a documented, versioned sequence of lexicographic stages. Stage values keep
their own types; nothing is summed into one number, and the final order is not a claim
that the contributing evidence shares a unit.

Stages (policy version 3.0.0, ``temporal_regime = query_conditioned``):

1. temporal applicability tier. **Only** when the query's temporal intent is explicit or
   inferred with high confidence, and only for ``current``, ``as_of``, and
   ``prospective``. A candidate whose *declared* validity interval establishes that it
   does not apply to the target instant sorts after candidates that apply or whose
   temporal basis is unknown. It is demoted, not removed: still admitted, still
   returned, labelled with why. This stage is non-compensatory. Relevance cannot rescue
   a candidate whose declared validity excludes it from the requested time (ADR-039
   C1, C2, C23). Unknown temporal basis is never treated as timeless or as current.
2. route corroboration: the number of distinct candidate routes that surfaced the fact;
3. exact identity: surfaced by an exact logical-memory lookup;
4. route-native relevance, one stage per route in declared order, never summed or
   cross-scaled. For the lexical route under ``bm25_admitted_set``, Okapi BM25
   (k1=1.2, b=0.75, untuned) with term statistics over the admitted set only;
5. temporal order within the query's regime, among candidates equal on every earlier
   stage, only when the intent orders temporally:
   ``current``: newest first; ``as_of``: latest evidence at or before the target first,
   later evidence after; ``prospective``: soonest upcoming first. ``historical``,
   ``atemporal_or_unspecified``, and low-confidence inferred intents apply **no**
   temporal preference. Clocks are compared only within the same clock kind, in the
   order declared ``valid_from`` > declared ``observed_at`` > runtime transaction time
   (a declared weak fallback), and every candidate records which clock was used;
6. stable fallback: a time-neutral digest of ``candidate_ref``. The runtime's
   identifiers are allocated in write order, so ordering by identifier would be a
   hidden transaction clock (old first).

Temporal evidence is typed by clock. ``valid_from``/``valid_until``/``observed_at`` are
caller-declared claims stored with the fact. They are evidence, not lifecycle: an
expired declared interval never refuses a candidate at admission and never supersedes
anything. Transaction time is the runtime's own write clock. In this runtime the
substrate's ``valid_at`` is assigned from the same write clock, so it is reported as
transaction time rather than presented as valid time. Metabolic evidence is not used
by this policy and is reported as ``not_used``.

``temporal_regime = universal_newer_first`` reproduces policy 2.x (newer-first among
relevance ties for every query), and ``none`` disables temporal ordering. Both are kept
so frozen evidence stays reproducible and alternatives stay testable.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Sequence

from .temporal_intent import AS_OF, CURRENT, DECLARED_TEMPORAL_KEY, PROSPECTIVE, TIMELINE, TemporalIntent, parse_time

POLICY_FAMILY = "agent-memory-post-admission-ranking"
POLICY_VERSION = "3.0.0"
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
    """Policy 2.x temporal evidence: (axis, raw value, POSIX seconds), ``valid_at`` then ``created_at``.

    Retained so the universal tie-break regime reproduces frozen 2.x orderings exactly.
    """

    if fact is None:
        return None, None, None
    for axis in ("valid_at", "created_at"):
        raw = getattr(fact, axis, None)
        seconds = parse_time(raw)
        if seconds is not None:
            return axis, str(raw), seconds
    return None, None, None


_CLOCK_ORDER = ("declared_valid_from", "declared_observed_at", "transaction_time")


def typed_temporal_evidence(fact: Any) -> dict[str, Any]:
    """Every temporal clock available for a fact, each labelled by kind. Nothing collapsed."""

    if fact is None:
        return {"clocks": {}, "declared_valid_from": None, "declared_valid_until": None}
    declared = dict((getattr(fact, "attributes", None) or {}).get(DECLARED_TEMPORAL_KEY) or {})
    clocks: dict[str, dict[str, Any]] = {}
    for kind, raw in (
        ("declared_valid_from", declared.get("valid_from")),
        ("declared_valid_until", declared.get("valid_until")),
        ("declared_observed_at", declared.get("observed_at")),
        ("transaction_time", getattr(fact, "created_at", None)),
    ):
        seconds = parse_time(raw)
        if seconds is not None:
            clocks[kind] = {"value": str(raw), "seconds": seconds}
    lifecycle = {
        key: getattr(fact, key)
        for key in ("invalid_at", "expired_at")
        if getattr(fact, key, None)
    }
    return {
        "clocks": clocks,
        "declared_basis": declared.get("basis"),
        "lifecycle": lifecycle,
        "substrate_valid_at_basis": "runtime_write_clock",
    }


def _ordering_clock(temporal: Mapping[str, Any]) -> tuple[str | None, float | None]:
    for kind in _CLOCK_ORDER:
        clock = temporal["clocks"].get(kind)
        if clock is not None:
            return kind, clock["seconds"]
    return None, None


def temporal_applicability(intent: TemporalIntent, temporal: Mapping[str, Any]) -> str:
    """Relationship between the query's temporal target and a candidate's declared validity."""

    if not intent.orders_temporally:
        return "not_evaluated"
    target = intent.target_instant()
    clocks = temporal["clocks"]
    start = clocks.get("declared_valid_from", {}).get("seconds")
    end = clocks.get("declared_valid_until", {}).get("seconds")
    if start is None and end is None:
        return "unknown_temporal_basis"
    if target is None:
        return "no_reference_time"
    if intent.mode == PROSPECTIVE:
        if start is not None and start > target:
            return "prospectively_applicable"
        if end is not None and end <= target:
            return "outside_target_interval"
        return "applicable_not_prospective"
    if start is not None and start > target:
        return "prospectively_applicable"
    if end is not None and end <= target:
        return "outside_target_interval"
    return "applicable"


_DEMOTED = {
    CURRENT: {"prospectively_applicable", "outside_target_interval"},
    AS_OF: {"prospectively_applicable", "outside_target_interval"},
    PROSPECTIVE: {"outside_target_interval", "applicable_not_prospective"},
}


def _neutral_digest(candidate_ref: str) -> str:
    return hashlib.sha256(candidate_ref.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PostAdmissionRankingPolicy:
    """One explicit, inspectable, deterministic ordering over admitted candidates."""

    policy_id: str
    route_score_order: tuple[str, ...]
    exact_identity_route: str
    temporal_regime: str = "query_conditioned"
    lexical_route: str | None = None
    lexical_relevance: str = "route_score"
    stable_fallback: str = "neutral_digest"
    unspecified_intent_order: str = "none"
    version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if self.temporal_regime not in {"query_conditioned", "universal_newer_first", "none"}:
            raise ValueError(f"unsupported temporal_regime: {self.temporal_regime}")
        if self.lexical_relevance not in {"route_score", "bm25_admitted_set"}:
            raise ValueError(f"unsupported lexical_relevance: {self.lexical_relevance}")
        if self.unspecified_intent_order not in {"none", "newer_first_among_ties"}:
            raise ValueError(f"unsupported unspecified_intent_order: {self.unspecified_intent_order}")
        if self.stable_fallback not in {"neutral_digest", "candidate_ref_asc"}:
            raise ValueError(f"unsupported stable_fallback: {self.stable_fallback}")
        if self.lexical_relevance == "bm25_admitted_set" and self.lexical_route not in self.route_score_order:
            raise ValueError("bm25_admitted_set requires lexical_route to be one of route_score_order")
        if len(set(self.route_score_order)) != len(self.route_score_order):
            raise ValueError("route_score_order must not repeat a route")

    def stage_names(self) -> list[str]:
        stages = []
        if self.temporal_regime == "query_conditioned":
            stages.append("temporal_applicability_tier")
        stages += ["route_corroboration_count_desc", "exact_identity_desc"]
        stages += [self._stage_name(route) for route in self.route_score_order]
        if self.temporal_regime == "query_conditioned":
            stages.append("temporal_order_within_query_regime")
        elif self.temporal_regime == "universal_newer_first":
            stages.append("temporal_evidence:newer_first")
        stages.append("candidate_ref_neutral_digest" if self.stable_fallback == "neutral_digest" else "candidate_ref_asc")
        return stages

    def identity(self) -> dict[str, Any]:
        return {
            "policy_family": POLICY_FAMILY,
            "policy_id": self.policy_id,
            "policy_version": self.version,
            "temporal_regime": self.temporal_regime,
            "stages": self.stage_names(),
            "route_scores_cross_comparable": False,
            "lexical_relevance": self.lexical_relevance,
            "lexical_relevance_statistics_scope": "admitted_set" if self.lexical_relevance == "bm25_admitted_set" else None,
            "bm25_parameters": {"k1": BM25_K1, "b": BM25_B} if self.lexical_relevance == "bm25_admitted_set" else None,
            "stable_fallback": self.stable_fallback,
            "unspecified_intent_order": self.unspecified_intent_order,
            "metabolic_evidence": "not_used",
            "authority_effect": "none",
        }

    def _stage_name(self, route: str) -> str:
        if route == self.lexical_route and self.lexical_relevance == "bm25_admitted_set":
            return f"lexical_relevance_desc:bm25_admitted_set:{route}"
        return f"route_score_desc:{route}"

    def evidence(self, candidate_ref: str, hits: Sequence[Any], fact: Any, intent: TemporalIntent | None = None) -> dict[str, Any]:
        route_ids = sorted({hit.route_id for hit in hits})
        scores = {
            route: max((float(hit.raw_score) for hit in hits if hit.route_id == route), default=None)
            for route in self.route_score_order
        }
        record: dict[str, Any] = {
            "candidate_ref": candidate_ref,
            "routes": route_ids,
            "route_corroboration_count": len(route_ids),
            "exact_identity": self.exact_identity_route in route_ids,
            "route_scores": {route: score for route, score in scores.items() if score is not None},
            "metabolic_evidence": "not_used",
        }
        if self.temporal_regime == "universal_newer_first":
            axis, raw, seconds = temporal_evidence(fact)
            record.update(temporal_axis=axis, temporal_value=raw, temporal_seconds=seconds)
        elif self.temporal_regime == "query_conditioned":
            intent = intent or TemporalIntent()
            temporal = typed_temporal_evidence(fact)
            clock, seconds = _ordering_clock(temporal)
            record["temporal_evidence"] = temporal
            record["temporal_applicability"] = temporal_applicability(intent, temporal)
            record["temporal_ordering_clock"] = clock if (intent.orders_temporally or self._defaults_unspecified(intent)) else None
            record["_ordering_seconds"] = seconds
        return record

    def _defaults_unspecified(self, intent: TemporalIntent) -> bool:
        """Evaluated alternative, off by default: unestablished intent behaves as current among ties.

        ADR-039 forbids silently treating unspecified intent as current. This option makes
        that default explicit and versioned so it can be measured, never implied.
        """

        return self.unspecified_intent_order == "newer_first_among_ties" and not intent.orders_temporally

    def _temporal_order_key(self, evidence: Mapping[str, Any], intent: TemporalIntent) -> tuple[Any, ...]:
        if self._defaults_unspecified(intent):
            clock, seconds = evidence.get("temporal_ordering_clock"), evidence.get("_ordering_seconds")
            if clock is None or seconds is None:
                return (1, len(_CLOCK_ORDER), 0.0)
            return (0, _CLOCK_ORDER.index(clock), -seconds)
        if not intent.orders_temporally:
            return (0,)
        clock = evidence.get("temporal_ordering_clock")
        seconds = evidence.get("_ordering_seconds")
        if clock is None or seconds is None:
            return (1, len(_CLOCK_ORDER), 0.0)
        clock_rank = _CLOCK_ORDER.index(clock)
        if intent.mode == CURRENT:
            return (0, clock_rank, -seconds)
        if intent.mode == AS_OF:
            target = intent.target_instant()
            if target is None:
                return (0,)
            return (0, clock_rank, 0, -seconds) if seconds <= target else (0, clock_rank, 1, seconds)
        if intent.mode == PROSPECTIVE:
            target = intent.target_instant()
            if target is not None and seconds > target:
                return (0, clock_rank, 0, seconds)
            return (0, clock_rank, 1, -seconds)
        return (0,)

    def keyed_stages(self, evidence: Mapping[str, Any], intent: TemporalIntent | None = None) -> list[tuple[str, Any]]:
        intent = intent or TemporalIntent()
        stages: list[tuple[str, Any]] = []
        if self.temporal_regime == "query_conditioned":
            demoted = intent.orders_temporally and evidence["temporal_applicability"] in _DEMOTED.get(intent.mode, set())
            stages.append(("temporal_applicability_tier", 1 if demoted else 0))
        stages.append(("route_corroboration_count_desc", -evidence["route_corroboration_count"]))
        stages.append(("exact_identity_desc", -int(evidence["exact_identity"])))
        for route in self.route_score_order:
            if route == self.lexical_route and self.lexical_relevance == "bm25_admitted_set":
                stages.append((self._stage_name(route), -evidence.get("lexical_relevance_score", 0.0)))
            else:
                stages.append((self._stage_name(route), -evidence["route_scores"].get(route, 0.0)))
        if self.temporal_regime == "query_conditioned":
            stages.append(("temporal_order_within_query_regime", self._temporal_order_key(evidence, intent)))
        elif self.temporal_regime == "universal_newer_first":
            seconds = evidence["temporal_seconds"]
            stages.append(("temporal_evidence:newer_first", (0 if seconds is not None else 1, -(seconds or 0.0))))
        if self.stable_fallback == "neutral_digest":
            stages.append(("candidate_ref_neutral_digest", _neutral_digest(evidence["candidate_ref"])))
        else:
            stages.append(("candidate_ref_asc", evidence["candidate_ref"]))
        return stages

    def sort_key(self, evidence: Mapping[str, Any], intent: TemporalIntent | None = None) -> tuple[Any, ...]:
        return tuple(value for _, value in self.keyed_stages(evidence, intent))

    def rank(
        self,
        admitted: Iterable[str],
        hits_by_candidate: Mapping[str, Sequence[Any]],
        fact_lookup: Callable[[str], Any],
        query: str = "",
        intent: TemporalIntent | None = None,
    ) -> tuple[list[str], dict[str, dict[str, Any]]]:
        """Order admitted candidates; return (ordered refs, per-candidate evidence)."""

        intent = intent or TemporalIntent()
        admitted = list(admitted)
        facts = {candidate_ref: fact_lookup(candidate_ref) for candidate_ref in admitted}
        evidence = {
            candidate_ref: self.evidence(candidate_ref, hits_by_candidate.get(candidate_ref, ()), facts[candidate_ref], intent)
            for candidate_ref in admitted
        }
        if self.lexical_relevance == "bm25_admitted_set":
            texts = {ref: getattr(fact, "fact_text", "") or "" for ref, fact in facts.items()}
            for ref, score in admitted_set_bm25(query, texts).items():
                evidence[ref]["lexical_relevance_score"] = score
        keyed = {ref: self.keyed_stages(evidence[ref], intent) for ref in evidence}
        ordered = sorted(evidence, key=lambda ref: tuple(value for _, value in keyed[ref]))
        identity = self.identity()
        interpretation = intent.to_dict() if self.temporal_regime == "query_conditioned" else None
        timeline = self._timeline(ordered, evidence, intent)
        for position, candidate_ref in enumerate(ordered, start=1):
            record = evidence[candidate_ref]
            record.pop("_ordering_seconds", None)
            record["rank_position"] = position
            record["policy_id"] = identity["policy_id"]
            record["policy_version"] = identity["policy_version"]
            record["temporal_regime"] = self.temporal_regime
            if interpretation is not None:
                record["query_temporal_intent"] = interpretation
            if position < len(ordered):
                successor = keyed[ordered[position]]
                record["ordered_before_next_by"] = next(
                    (name for (name, mine), (_, theirs) in zip(keyed[candidate_ref], successor) if mine != theirs),
                    "indistinguishable",
                )
            if timeline is not None:
                record["recall_shape"] = TIMELINE
                record["timeline_position"] = timeline.get(candidate_ref)
            record["authority_effect"] = "none"
        return ordered, evidence

    def _timeline(
        self, ordered: Sequence[str], evidence: Mapping[str, Mapping[str, Any]], intent: TemporalIntent
    ) -> dict[str, int | None] | None:
        """Chronological positions for a timeline-shaped recall; the ranked order is unchanged.

        Every admitted candidate is placed by its best available clock (declared valid
        time, then declared observation time, then transaction time), compared only
        within the same clock kind. Candidates with no clock have no position.
        """

        if self.temporal_regime != "query_conditioned" or intent.expected_recall_shape != TIMELINE:
            return None
        placed = []
        for ref in ordered:
            clock, seconds = _ordering_clock(evidence[ref]["temporal_evidence"])
            if clock is not None:
                placed.append((_CLOCK_ORDER.index(clock), seconds, _neutral_digest(ref), ref))
        positions: dict[str, int | None] = {ref: None for ref in ordered}
        for index, (_, _, _, ref) in enumerate(sorted(placed), start=1):
            positions[ref] = index
        return positions
