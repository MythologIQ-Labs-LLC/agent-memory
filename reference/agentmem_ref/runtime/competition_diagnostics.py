"""Opt-in, post-admission diagnostic for untyped competition (#769).

This is a REAL runtime observation over already-admitted, CURRENT-visible facts.
It is NOT a completeness attestation, a same-slot identity oracle, a conflict
resolution mechanism or permission to stop searching. No default recall path
calls this module; no data is persisted or changed.

The visibility and typed-evidence origin MUST be supplied by the canonical
governed adapter, never by a caller-provided text or model prediction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .evidence_sufficiency import SufficiencyReport


OBSERVER_VERSION = "0.1.0"
_UNRESOLVED_TYPED = frozenset((
    "competing_values_unresolved", "change_assertion_unresolved",
    "coexistence_possible", "cardinality_unresolved",
))
_DIAGNOSES = frozenset((
    "recall_observation_unverified", "typed_values_unresolved",
    "typed_value_posture_unresolved", "typed_slot_obstacles_observed",
    "untyped_admitted_candidates_observed", "scope_enumeration_unattested",
))
_STATUSES = frozenset(("none_seen", "identity_unverified"))


@dataclass(frozen=True)
class CompetitionDiagnostic:
    """Redacted, non-authoritative status; contains no candidate refs/values."""

    diagnosis: str
    receipt_state: str
    admitted_untyped_count: int
    typed_coverage_observed: bool
    typed_value_statuses: tuple[str, ...]
    untyped_relation_status: str
    scope_enumeration: str = "read_path_observed"
    complete_enumeration_attested: bool = False
    stop_recommendation: str = "abstain"
    authority_effect: str = "none"
    version: str = OBSERVER_VERSION

    def __post_init__(self) -> None:
        if (self.version != OBSERVER_VERSION or self.diagnosis not in _DIAGNOSES
                or self.receipt_state not in ("mutable_receipt_match", "unverified")
                or type(self.admitted_untyped_count) is not int
                or self.admitted_untyped_count < 0
                or type(self.typed_coverage_observed) is not bool
                or type(self.typed_value_statuses) is not tuple
                or any(type(x) is not str for x in self.typed_value_statuses)
                or self.untyped_relation_status not in _STATUSES
                or self.scope_enumeration != "read_path_observed"
                or self.complete_enumeration_attested is not False
                or self.stop_recommendation != "abstain"
                or self.authority_effect != "none"):
            raise ValueError("invalid or authoritative competition diagnostic")
        if self.receipt_state == "unverified" and (
            self.diagnosis != "recall_observation_unverified"
            or self.admitted_untyped_count or self.typed_coverage_observed
            or self.typed_value_statuses
            or self.untyped_relation_status != "none_seen"
        ):
            raise ValueError("unverified receipt must not carry evidence")

    def to_dict(self) -> dict:
        """Only admitted projection metadata; no raw text, facts, or identities."""
        return {
            "version": self.version,
            "diagnosis": self.diagnosis,
            "receipt_state": self.receipt_state,
            "scope_enumeration": self.scope_enumeration,
            "complete_enumeration_attested": False,
            "admitted_untyped_count": self.admitted_untyped_count,
            "untyped_relation_status": self.untyped_relation_status,
            "typed_coverage_observed": self.typed_coverage_observed,
            "typed_value_statuses": list(self.typed_value_statuses),
            "stop_recommendation": "abstain",
            "authority_effect": "none",
        }


def diagnose(
    *,
    receipt_matches: bool,
    sufficiency: SufficiencyReport | None = None,
    admitted_untyped_count: int = 0,
) -> CompetitionDiagnostic:
    """Combine certified *local* observations without inventing global coverage.

    A receipt matching the mutable result is not query-membership certification,
    a durable read revision, full candidate enumeration or trusted slot identity.
    A visible admitted untyped candidate is not automatically a same-slot
    competitor: the unresolved status explicitly preserves that uncertainty.
    """
    if type(receipt_matches) is not bool:
        raise TypeError("receipt_matches requires an exact boolean")
    if not receipt_matches:
        return CompetitionDiagnostic(
            diagnosis="recall_observation_unverified", receipt_state="unverified",
            admitted_untyped_count=0, typed_coverage_observed=False,
            typed_value_statuses=(), untyped_relation_status="none_seen",
        )
    from .evidence_sufficiency import SufficiencyReport
    if type(sufficiency) is not SufficiencyReport:
        raise TypeError("verified diagnosis requires governed sufficiency report")
    if (sufficiency.stop_attested or sufficiency.authority_effect != "none"
            or sufficiency.continuation_proposal != "continue_if_permitted"):
        raise ValueError("sufficiency cannot provide stopping authority")
    if type(admitted_untyped_count) is not int or admitted_untyped_count < 0:
        raise ValueError("untyped count requires nonnegative integer")
    status = tuple(sorted({v.status for v in sufficiency.value_coherence}))
    if "competing_values_unresolved" in status:
        diagnosis = "typed_values_unresolved"
    elif any(x in _UNRESOLVED_TYPED for x in status):
        diagnosis = "typed_value_posture_unresolved"
    elif any((missing or counter or temporal)
             for _, missing, counter, temporal in sufficiency.slot_obstacles):
        diagnosis = "typed_slot_obstacles_observed"
    elif admitted_untyped_count:
        diagnosis = "untyped_admitted_candidates_observed"
    else:
        diagnosis = "scope_enumeration_unattested"
    return CompetitionDiagnostic(
        diagnosis=diagnosis, receipt_state="mutable_receipt_match",
        admitted_untyped_count=admitted_untyped_count,
        typed_coverage_observed=sufficiency.mechanical_coverage_met,
        typed_value_statuses=status,
        untyped_relation_status=("identity_unverified" if admitted_untyped_count else "none_seen"),
    )
