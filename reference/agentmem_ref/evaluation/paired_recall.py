"""#636 offline paired comparisons of two already-executed PUBLIC recall profiles.

This evaluator never invokes a backend, alters ranking, or assigns authority.
It requires aligned corpus, labels, queries, eligibility context and return
budgets, but those declarations are caller-supplied, not independently proven.
It measures evidence presence, NOT downstream answer correctness or cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RunIdentity:
    profile_id: str
    revision: str
    configuration_digest: str
    corpus_digest: str
    questions_digest: str
    labels_digest: str
    harness_digest: str
    scope_digest: str
    case_ref: str
    case_input_digest: str
    budget_k: int

    def __post_init__(self) -> None:
        if any(not isinstance(x, str) or not x.strip() for x in (
            self.profile_id, self.revision, self.configuration_digest, self.corpus_digest,
            self.questions_digest, self.labels_digest, self.harness_digest,
            self.scope_digest, self.case_ref, self.case_input_digest,
        )) or type(self.budget_k) is not int or self.budget_k < 1:
            raise ValueError("paired profile identities and bounded k are required")


@dataclass(frozen=True)
class CaseLabels:
    required_refs: frozenset[str]
    forbidden_refs: frozenset[str]
    no_safe_answer: bool = False

    def __post_init__(self) -> None:
        if any(not isinstance(v, frozenset) or any(type(x) is not str or not x for x in v)
               for v in (self.required_refs, self.forbidden_refs)):
            raise ValueError("labels must be frozensets of nonempty refs")
        if self.required_refs & self.forbidden_refs:
            raise ValueError("required and forbidden labels must be disjoint")
        if type(self.no_safe_answer) is not bool:
            raise ValueError("no_safe_answer flag must be bool")
        if self.no_safe_answer and self.required_refs:
            raise ValueError("no-safe-answer tasks must not list required returned evidence")


@dataclass(frozen=True)
class CaseMetrics:
    required_retained: int
    required_missing: int
    forbidden_returned: int
    unlabelled_returned: int
    returned: int
    evidence_success: bool
    no_answer_context_empty: bool | None


@dataclass(frozen=True)
class PairedResult:
    original: CaseMetrics
    candidate: CaseMetrics
    required_lost: int
    required_gained: int
    forbidden_newly_returned: int
    forbidden_removed: int
    regression: bool
    interpretation: str = "offline_paired_public_evidence_not_answer_quality_or_backend_ablation"
    authority_effect: str = "none"


def _visible(recall: Mapping[str, Any], budget: int) -> frozenset[str]:
    if not isinstance(recall, Mapping):
        raise ValueError("recall must be a public result mapping")
    returned, admitted, admissions = (recall.get(key) for key in (
        "returned", "admitted", "admissions"))
    if not isinstance(returned, list) or not isinstance(admitted, list) or not isinstance(admissions, Mapping):
        raise ValueError("public returned/admitted/admissions fields are required")
    if any(type(ref) is not str or not ref for ref in returned + admitted):
        raise ValueError("returned/admitted references must be strings")
    if len(returned) != len(set(returned)) or len(admitted) != len(set(admitted)):
        raise ValueError("duplicate returned/admitted references")
    if len(returned) > budget or not set(returned) <= set(admitted):
        raise ValueError("return budget or governed admission violation")
    if any(not isinstance(admissions.get(ref), Mapping) for ref in returned):
        raise ValueError("returned item missing public admission receipt")
    return frozenset(returned)


def _measure(returned: frozenset[str], labels: CaseLabels) -> CaseMetrics:
    missed = len(labels.required_refs - returned)
    forbidden = len(labels.forbidden_refs & returned)
    return CaseMetrics(
        required_retained=len(returned & labels.required_refs),
        required_missing=missed,
        forbidden_returned=forbidden,
        unlabelled_returned=len(returned - labels.required_refs - labels.forbidden_refs),
        returned=len(returned),
        evidence_success=(bool(labels.required_refs) and missed == 0 and forbidden == 0 and not labels.no_safe_answer),
        no_answer_context_empty=(not bool(returned)) if labels.no_safe_answer else None,
    )


def compare_public_profiles(
    original: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    original_run: RunIdentity,
    candidate_run: RunIdentity,
    labels: CaseLabels,
) -> PairedResult:
    """Compare matching public evidence without peeking into hidden candidates.

    Both arms must be executed externally with independently reviewable source,
    corpus, harness and configuration. This function checks declarations only;
    it does not prove operational fairness, latency, source rights, or validity
    of gold labels. In particular an empty no-answer context is not proof that
    a reader/agent abstained from making up an answer.
    """
    for field in ("corpus_digest", "questions_digest", "labels_digest", "harness_digest", "scope_digest", "case_ref", "case_input_digest", "budget_k"):
        if getattr(original_run, field) != getattr(candidate_run, field):
            raise ValueError(f"incomparable profiles: {field} differs")
    a = _visible(original, original_run.budget_k)
    b = _visible(candidate, candidate_run.budget_k)
    lost = len((a & labels.required_refs) - b)
    gained = len((b & labels.required_refs) - a)
    added_bad = len((b & labels.forbidden_refs) - a)
    removed_bad = len((a & labels.forbidden_refs) - b)
    first, second = _measure(a, labels), _measure(b, labels)
    return PairedResult(
        original=first,
        candidate=second,
        required_lost=lost,
        required_gained=gained,
        forbidden_newly_returned=added_bad,
        forbidden_removed=removed_bad,
        regression=bool(lost or added_bad or (labels.no_safe_answer and not first.returned and second.returned)),
    )


__all__ = ["RunIdentity", "CaseLabels", "CaseMetrics", "PairedResult", "compare_public_profiles"]
