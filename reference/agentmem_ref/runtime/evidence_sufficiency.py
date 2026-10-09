"""Typed, post-admission sufficiency observation for controlled recall (#644).

This module observes ONLY references already admitted by governed recall. It
never retrieves, orders, admits, supersedes, stops execution, or mutates memory.
An asserted typed coverage relationship is mechanical evidence, not proof that
an answer is correct or that its source is independent/trustworthy.
"""

from __future__ import annotations

from dataclasses import dataclass

SUFFICIENCY_OBSERVER_VERSION = "1.1.0"
TYPED_OBSERVATION = "runtime_typed_observation"
CONTROLLER_ESTIMATE = "controller_estimate"
_ORIGINS = frozenset((TYPED_OBSERVATION, CONTROLLER_ESTIMATE))


def _ident(value: str, label: str) -> None:
    if type(value) is not str or not value or not value.strip() or len(value) > 256:
        raise ValueError(f"{label} must be a non-empty string of at most 256 chars")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{label} must not contain control characters")


def _unique_refs(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must not repeat identities")
    for value in values:
        _ident(value, label)


@dataclass(frozen=True)
class CoverageNeed:
    """Caller-declared query need, not inferred or authorized by a model."""

    key: str
    min_admitted_supports: int = 1

    def __post_init__(self) -> None:
        _ident(self.key, "need key")
        if type(self.min_admitted_supports) is not int or not 1 <= self.min_admitted_supports <= 256:
            raise ValueError("min_admitted_supports must be an integer from 1 to 256")


@dataclass(frozen=True)
class CoverageObservation:
    """Evidence mapping, not a truth or independence certificate."""

    candidate_ref: str
    need_keys: tuple[str, ...]
    origin: str = CONTROLLER_ESTIMATE

    def __post_init__(self) -> None:
        _ident(self.candidate_ref, "candidate reference")
        _unique_refs(self.need_keys, "coverage need keys")
        if self.origin not in _ORIGINS:
            raise ValueError("unsupported coverage observation origin")


@dataclass(frozen=True)
class TypedValueClaim:
    """Eligible persisted claim only. It grants neither truth nor state-change status."""

    candidate_ref: str
    need_key: str
    value: str
    cardinality: str | None = None
    assertion: str = "state"

    def __post_init__(self) -> None:
        _ident(self.candidate_ref, "claim candidate reference")
        _ident(self.need_key, "claim need key")
        _ident(self.value, "claim value")
        if self.cardinality not in (None, "single", "multi"):
            raise ValueError("invalid typed claim cardinality")
        if self.assertion not in ("state", "change"):
            raise ValueError("invalid typed claim assertion")


@dataclass(frozen=True)
class ValueCoherenceAssessment:
    """Groups exact values by admitted fact identity, never exposes raw values."""

    need_key: str
    status: str
    fact_groups: tuple[tuple[str, ...], ...]


def assess_value_coherence(
    needs: tuple[CoverageNeed, ...], claims: tuple[TypedValueClaim, ...]
) -> tuple[ValueCoherenceAssessment, ...]:
    """Conservative same-slot evidence comparison, NOT contradiction resolution.

    Raw values are grouped by strict string equality only. An asserted change
    is not a governed correction. Distinct facts are not independent sources.
    Unknown cardinality cannot establish single-valued incompatibility.
    """
    if type(needs) is not tuple or type(claims) is not tuple:
        raise TypeError("typed value inputs must be tuples")
    requested = {need.key for need in needs}
    if len(requested) != len(needs) or any(type(need) is not CoverageNeed for need in needs):
        raise ValueError("unique typed coverage needs required")
    seen: set[tuple[str, str]] = set()
    for claim in claims:
        if type(claim) is not TypedValueClaim or claim.need_key not in requested:
            raise ValueError("claim is not a declared typed coverage need")
        identity = (claim.need_key, claim.candidate_ref)
        if identity in seen:
            raise ValueError("duplicate value claim per fact and slot")
        seen.add(identity)
    assessments = []
    for need in sorted(requested):
        subset = [claim for claim in claims if claim.need_key == need]
        groups: dict[str, set[str]] = {}
        for claim in subset:
            groups.setdefault(claim.value, set()).add(claim.candidate_ref)
        fact_groups = tuple(sorted(tuple(sorted(refs)) for refs in groups.values()))
        if not subset:
            status = "no_eligible_value"
        elif any(item.assertion == "change" for item in subset):
            status = "change_assertion_unresolved"
        elif any(item.cardinality == "multi" for item in subset):
            status = "coexistence_possible"
        elif any(item.cardinality is None for item in subset):
            status = "cardinality_unresolved"
        elif len(groups) == 1:
            status = "same_value_observed"
        else:
            status = "competing_values_unresolved"
        assessments.append(ValueCoherenceAssessment(need, status, fact_groups))
    return tuple(assessments)


@dataclass(frozen=True)
class RouteWorkObservation:
    route_id: str
    candidate_limit: int
    returned_count: int
    executed: bool

    def __post_init__(self) -> None:
        _ident(self.route_id, "route id")
        if (type(self.candidate_limit) is not int or self.candidate_limit < 0
                or type(self.returned_count) is not int or self.returned_count < 0):
            raise ValueError("route counters must be nonnegative integers")
        if type(self.executed) is not bool:
            raise TypeError("executed must be a boolean")
        if self.returned_count > self.candidate_limit:
            raise ValueError("route returned_count exceeds its candidate limit")
        if not self.executed and self.returned_count:
            raise ValueError("unexecuted route cannot return candidates")


@dataclass(frozen=True)
class SufficiencyObservation:
    admitted_refs: tuple[str, ...]
    needs: tuple[CoverageNeed, ...] = ()
    coverage: tuple[CoverageObservation, ...] = ()
    contradictions: tuple[tuple[str, str], ...] = ()
    route_work: tuple[RouteWorkObservation, ...] = ()
    count_target: int = 1
    typed_value_claims: tuple[TypedValueClaim, ...] = ()

    def __post_init__(self) -> None:
        _unique_refs(self.admitted_refs, "admitted references")
        if type(self.count_target) is not int or self.count_target < 1:
            raise ValueError("count_target must be a positive integer")
        for label, values, type_ in (
            ("needs", self.needs, CoverageNeed),
            ("coverage", self.coverage, CoverageObservation),
            ("contradictions", self.contradictions, tuple),
            ("route_work", self.route_work, RouteWorkObservation),
            ("typed_value_claims", self.typed_value_claims, TypedValueClaim),
        ):
            if type(values) is not tuple or any(type(item) is not type_ for item in values):
                raise TypeError(f"{label} must contain typed tuple entries")
        need_keys = [need.key for need in self.needs]
        if len(need_keys) != len(set(need_keys)):
            raise ValueError("duplicate requested need")
        route_ids = [route.route_id for route in self.route_work]
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("duplicate route-work identity")
        admitted = set(self.admitted_refs)
        known_needs = set(need_keys)
        for item in self.coverage:
            if item.candidate_ref not in admitted:
                raise ValueError("coverage may refer only to governed admitted evidence")
            if not set(item.need_keys).issubset(known_needs):
                raise ValueError("coverage names an undeclared need")
        typed_support = {(item.candidate_ref, key) for item in self.coverage
                         if item.origin == TYPED_OBSERVATION for key in item.need_keys}
        for claim in self.typed_value_claims:
            if claim.candidate_ref not in admitted or claim.need_key not in known_needs:
                raise ValueError("typed value claim must refer to admitted declared evidence")
            if (claim.candidate_ref, claim.need_key) not in typed_support:
                raise ValueError("typed value claim requires matching typed support evidence")
        assess_value_coherence(self.needs, self.typed_value_claims)
        for pair in self.contradictions:
            if len(pair) != 2 or any(type(ref) is not str for ref in pair):
                raise ValueError("contradiction must be a pair of admitted refs")
            if pair[0] == pair[1] or not set(pair).issubset(admitted):
                raise ValueError("contradiction must link distinct admitted refs")


@dataclass(frozen=True)
class SufficiencyReport:
    observation_version: str
    admitted_count: int
    count_target_met: bool
    mechanical_coverage_met: bool
    need_support_counts: tuple[tuple[str, int], ...]
    need_support_refs: tuple[tuple[str, tuple[str, ...]], ...]
    missing_needs: tuple[str, ...]
    contradiction_pairs: tuple[tuple[str, str], ...]
    budget_bound_routes: tuple[str, ...]
    unexecuted_routes: tuple[str, ...]
    diagnosis: str
    continuation_proposal: str
    # These three never change: a controller observation cannot establish
    # semantic correctness, governed admission, or lifecycle permission.
    answer_quality_verified: bool = False
    can_admit: bool = False
    can_mutate: bool = False
    authority_effect: str = "none"
    value_coherence: tuple[ValueCoherenceAssessment, ...] = ()

    def __post_init__(self) -> None:
        if (self.answer_quality_verified is not False
                or self.can_admit is not False or self.can_mutate is not False
                or self.authority_effect != "none"):
            raise ValueError("sufficiency report cannot grant authority or certify quality")
        if self.continuation_proposal not in ("review_stop", "continue_if_permitted"):
            raise ValueError("unsupported continuation proposal")
        if (self.continuation_proposal == "review_stop"
                and any(item.status not in ("no_eligible_value", "same_value_observed")
                        for item in self.value_coherence)):
            raise ValueError("unresolved typed values cannot recommend stopping")

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_version": self.observation_version,
            "admitted_count": self.admitted_count,
            "count_target_met": self.count_target_met,
            "mechanical_coverage_met": self.mechanical_coverage_met,
            "need_support_counts": dict(self.need_support_counts),
            "need_support_refs": {need: list(refs) for need, refs in self.need_support_refs},
            "missing_needs": list(self.missing_needs),
            "value_coherence": [
                {"need_key": item.need_key, "status": item.status,
                 "fact_groups": [list(group) for group in item.fact_groups]}
                for item in self.value_coherence
            ],
            "contradiction_pairs": [list(x) for x in self.contradiction_pairs],
            "budget_bound_routes": list(self.budget_bound_routes),
            "unexecuted_routes": list(self.unexecuted_routes),
            "diagnosis": self.diagnosis,
            "continuation_proposal": self.continuation_proposal,
            "answer_quality_verified": False,
            "can_admit": False,
            "can_mutate": False,
            "authority_effect": "none",
        }


def assess_sufficiency(observation: SufficiencyObservation) -> SufficiencyReport:
    """Deterministic post-admission diagnosis; no effect on actual recall.

    Only `runtime_typed_observation` claims contribute mechanical coverage.
    The caller, NOT this module, must establish whether that label is backed
    by authentic, permitted typed evidence. Even then coverage != truth.
    Count-only targets are always reported separately and NEVER stop search.
    A route at its cap is conservatively classified as resource-bound.
    """
    if type(observation) is not SufficiencyObservation:
        raise TypeError("expected SufficiencyObservation")
    supports = {need.key: set() for need in observation.needs}
    for item in observation.coverage:
        if item.origin == TYPED_OBSERVATION:
            for key in item.need_keys:
                supports[key].add(item.candidate_ref)
    missing = tuple(sorted(need.key for need in observation.needs
                           if len(supports[need.key]) < need.min_admitted_supports))
    pairings = tuple(sorted({tuple(sorted(pair)) for pair in observation.contradictions}))
    capped = tuple(sorted(route.route_id for route in observation.route_work
                          if route.executed and route.candidate_limit > 0
                          and route.returned_count == route.candidate_limit))
    unexecuted = tuple(sorted(route.route_id for route in observation.route_work
                              if not route.executed and route.candidate_limit > 0))
    covered = bool(observation.needs) and not missing
    value_coherence = assess_value_coherence(observation.needs, observation.typed_value_claims)
    ambiguous_values = any(
        item.status not in ("no_eligible_value", "same_value_observed")
        for item in value_coherence
    )
    if not observation.admitted_refs:
        diagnosis = "no_admitted_evidence"
    elif pairings:
        diagnosis = "unresolved_contradiction"
    elif not observation.needs:
        diagnosis = "coverage_undetermined"
    elif unexecuted:
        diagnosis = "planned_routes_not_executed"
    elif not covered:
        diagnosis = "budget_bound_missing_evidence" if capped else "missing_declared_evidence"
    elif ambiguous_values:
        diagnosis = "value_coherence_unresolved"
    elif capped:
        diagnosis = "coverage_observed_resource_bound"
    else:
        diagnosis = "mechanical_coverage_observed"
    proposal = ("review_stop" if diagnosis == "mechanical_coverage_observed"
                else "continue_if_permitted")
    return SufficiencyReport(
        observation_version=SUFFICIENCY_OBSERVER_VERSION,
        admitted_count=len(observation.admitted_refs),
        count_target_met=len(observation.admitted_refs) >= observation.count_target,
        mechanical_coverage_met=covered,
        need_support_counts=tuple(sorted((k, len(refs)) for k, refs in supports.items())),
        need_support_refs=tuple(sorted((k, tuple(sorted(refs))) for k, refs in supports.items())),
        missing_needs=missing,
        contradiction_pairs=pairings,
        budget_bound_routes=capped,
        unexecuted_routes=unexecuted,
        diagnosis=diagnosis,
        continuation_proposal=proposal,
        value_coherence=value_coherence if observation.typed_value_claims else (),
    )
