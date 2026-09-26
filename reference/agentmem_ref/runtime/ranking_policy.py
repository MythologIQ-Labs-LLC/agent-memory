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
   the same route's score on other candidates;
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

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Sequence

POLICY_FAMILY = "agent-memory-post-admission-ranking"
POLICY_VERSION = "2.0.0"


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
    version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if self.temporal_tiebreak not in {"newer_first", "none"}:
            raise ValueError(f"unsupported temporal_tiebreak: {self.temporal_tiebreak}")
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
                *[f"route_score_desc:{route}" for route in self.route_score_order],
                "temporal_evidence:" + self.temporal_tiebreak,
                "candidate_ref_asc",
            ],
            "route_scores_cross_comparable": False,
            "authority_effect": "none",
        }

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
    ) -> tuple[list[str], dict[str, dict[str, Any]]]:
        """Order admitted candidates; return (ordered refs, per-candidate ranking evidence)."""

        evidence = {
            candidate_ref: self.evidence(candidate_ref, hits_by_candidate.get(candidate_ref, ()), fact_lookup(candidate_ref))
            for candidate_ref in admitted
        }
        ordered = sorted(evidence, key=lambda candidate_ref: self.sort_key(evidence[candidate_ref]))
        identity = self.identity()
        for position, candidate_ref in enumerate(ordered, start=1):
            evidence[candidate_ref]["rank_position"] = position
            evidence[candidate_ref]["policy_id"] = identity["policy_id"]
            evidence[candidate_ref]["policy_version"] = identity["policy_version"]
            evidence[candidate_ref]["authority_effect"] = "none"
        return ordered, evidence
