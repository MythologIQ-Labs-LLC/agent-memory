"""Compositional current-context recall adapter for issue #200.

The wrapped GovernedMemoryAdapter executes canonical lifecycle/scope admission
first. This adapter only evaluates candidates that survived that gate and may
further restrict them. It has no path that can widen or repair a built-in
refusal.

RC-3 also needs candidate generation to be separable from canonical admission.
``admit_preselected_candidates`` is the narrow reference seam for that purpose:
retrieval routes may discover candidate identifiers, but this module sends the
union through the same built-in lifecycle/scope/currentness rules exactly once.
It is intentionally runtime-internal rather than a public product API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..core import policy, receipts
from .adapter import AdmissionResult, Clock, GovernedMemoryAdapter, RecallContext, candidate_policy_evidence
from ..core.contextual_recall import ADMITTING_OUTCOMES, fail_closed_decision


def admit_preselected_candidates(
    base: GovernedMemoryAdapter,
    candidate_refs: Iterable[str],
    context: RecallContext,
    *,
    query_label: str = "preselected-candidates",
) -> AdmissionResult:
    """Apply canonical built-in admission to a preselected candidate set once.

    Candidate generation is deliberately outside this function. The caller may
    use lexical, identity, graph, vector, or future controller-backed routes,
    but route output is only evidence of discoverability. Every distinct
    candidate is re-bound to the adapter's current substrate object and passed
    through the adapter's canonical admission rules before it can enter active
    cognition.

    The current reference adapter predates an explicit public candidate-
    admission port, so this same-runtime helper delegates to its internal
    admission/decision/event builders. That dependency is intentionally
    concentrated here instead of duplicated by every retrieval route. No raw
    substrate object is returned to the caller and no refusal can be widened.
    """
    substrate_reader = getattr(base, "checkpoint_substrate", None)
    if not callable(substrate_reader):
        raise ValueError(
            "preselected candidate admission requires a runtime adapter with a declared substrate collaborator"
        )
    substrate = substrate_reader()

    evaluated_at = base._clock.now()
    result = AdmissionResult(
        policy_version=policy.POLICY_VERSION,
        evaluated_at=evaluated_at,
    )
    result.candidate_policy = candidate_policy_evidence()
    correlation = base._ids.next()
    seen: set[str] = set()

    for candidate_ref in candidate_refs:
        if not candidate_ref or candidate_ref in seen:
            continue
        seen.add(candidate_ref)
        fact = substrate.get_fact(candidate_ref)
        # #548: a discovered fact outside the caller's domain never becomes a candidate.
        # Full admission below re-applies the same conditions to everything that remains.
        if fact is not None and not base.domain_eligible(fact, context):
            continue
        result.candidates.append(candidate_ref)

        refusal = (
            "candidate_not_found"
            if fact is None
            else base._admission_refusal(fact, context)
        )
        if refusal:
            result.refusals[candidate_ref] = refusal
        else:
            result.admitted.append(candidate_ref)
        result.decisions[candidate_ref] = base._recall_decision(
            candidate_ref,
            context,
            refusal,
            evaluated_at,
        )

    base.events.append(
        base._recall_event(
            query_label,
            context,
            result,
            correlation,
            evaluated_at,
        )
    )
    return result


@dataclass
class ContextualAdmissionResult:
    candidates: list[str] = field(default_factory=list)
    admitted: list[str] = field(default_factory=list)
    refusals: dict[str, str] = field(default_factory=dict)
    contextual_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    context_surface: list[str] = field(default_factory=list)
    downstream_influence: list[str] = field(default_factory=list)


class ContextualRecallAdapter:
    """Apply current contextual recall policy monotonically after built-ins."""

    def __init__(
        self,
        base: GovernedMemoryAdapter,
        *,
        policy: object | None = None,
        require_policy: bool = False,
        required_policy_ref: str = "contextual-recall-policy:required",
        required_policy_version: str = "required-current",
        clock: Clock | None = None,
    ) -> None:
        self._base = base
        self._policy = policy
        self._require_policy = require_policy
        self._required_policy_ref = required_policy_ref
        self._required_policy_version = required_policy_version
        self._clock = clock or Clock(start=40)

    def set_policy(self, policy: object | None) -> None:
        """Replace the current policy without touching retained memory."""
        self._policy = policy

    def governed_recall(self, query: str, context: RecallContext | None = None) -> ContextualAdmissionResult:
        """Run canonical recall, then freshly re-evaluate current contextual policy."""
        context = context or RecallContext(target_domain_refs=())
        base_result = self._base.governed_recall(query, context)
        result = ContextualAdmissionResult(
            candidates=list(base_result.candidates),
            refusals=dict(base_result.refusals),
        )

        # Only built-in admitted candidates reach the contextual policy. Thus a
        # contextual "admit" can never resurrect a built-in refusal.
        for candidate_ref in base_result.admitted:
            decision = self._evaluate_current(candidate_ref, context)
            if decision is None:
                result.admitted.append(candidate_ref)
                continue
            result.contextual_decisions[candidate_ref] = decision
            if decision["outcome"] in ADMITTING_OUTCOMES:
                result.admitted.append(candidate_ref)
            else:
                result.refusals[candidate_ref] = (
                    f"contextual:{decision['outcome']}:{decision['reason_code']}"
                )

        # These final surfaces are aliases by value, not extra authority. They
        # make the sleeper proof explicit: a blocked candidate can remain
        # discoverable while being absent from context/downstream influence.
        result.context_surface = list(result.admitted)
        result.downstream_influence = list(result.admitted)
        return result

    def _evaluate_current(self, candidate_ref: str, context: RecallContext) -> dict[str, Any] | None:
        evaluated_at = self._clock.now()
        if self._policy is None:
            if not self._require_policy:
                return None
            return fail_closed_decision(
                candidate_ref=candidate_ref,
                context=context,
                policy_ref=self._required_policy_ref,
                policy_version=self._required_policy_version,
                status="unavailable",
                reason_code="contextual_policy_unavailable",
                evaluated_at=evaluated_at,
            )

        policy_ref = str(getattr(self._policy, "policy_ref", self._required_policy_ref) or self._required_policy_ref)
        policy_version = str(
            getattr(self._policy, "policy_version", self._required_policy_version)
            or self._required_policy_version
        )
        try:
            decision = self._policy.evaluate(candidate_ref, context, evaluated_at=evaluated_at)
        except Exception:
            return fail_closed_decision(
                candidate_ref=candidate_ref,
                context=context,
                policy_ref=policy_ref,
                policy_version=policy_version,
                status="error",
                reason_code="contextual_policy_error",
                evaluated_at=evaluated_at,
            )

        try:
            receipts.validate("contextual-recall-admission.schema.json", decision)
        except Exception:
            return fail_closed_decision(
                candidate_ref=candidate_ref,
                context=context,
                policy_ref=policy_ref,
                policy_version=policy_version,
                status="invalid",
                reason_code="contextual_policy_invalid_decision",
                evaluated_at=evaluated_at,
            )
        return decision
