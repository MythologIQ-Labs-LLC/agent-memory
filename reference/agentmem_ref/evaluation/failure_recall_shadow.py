"""Evaluation-only qualification of native failure-memory recall composition (#690).

This module exercises the EXISTING governed adapter and FailureMemory.recall_active,
rather than copying or replacing admission/authority rules. It is not imported
by the runtime and cannot mutate recall, lifecycle, ranking, or PAMA outcomes.
Its output is diagnostic evidence, NOT a consumer-facing or accepted API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..core.contextual_recall import ADMITTING_OUTCOMES
from ..memory.failure_memory import FailureMemory
from ..runtime.adapter import RecallContext


@dataclass(frozen=True)
class UsableFailureEvidence:
    """Only owner-recognized, contextually allowed, current failure metadata."""
    failure_ref: str
    revision_ref: str
    fact_uuid: str
    memory_status: Literal["active"]
    causal_status: str
    severity_label: str
    occurrence_count: int
    action_class: str
    # Severity/recurrence are context, not authorization or automated blocking.
    authority_effect: Literal["none"] = "none"


@dataclass(frozen=True)
class ShadowFailureRecall:
    """A diagnostic comparison against the same governed candidate/admission call.

    generic_admitted_fact_uuids may include facts not belonging to the failure
    owner. Only usable_failures passed the FAILURE-SPECIFIC contextual gate.
    This distinction must be retained in a future facade composition.
    """
    query: str
    candidate_fact_uuids: tuple[str, ...]
    generic_admitted_fact_uuids: tuple[str, ...]
    usable_failures: tuple[UsableFailureEvidence, ...]
    rejected_fact_reasons: tuple[tuple[str, str], ...]
    contextual_outcomes: tuple[tuple[str, str], ...]
    authority_effect: Literal["none"] = "none"
    mutates_memory: Literal[False] = False
    integration_state: Literal["evaluation_only"] = "evaluation_only"


def inspect_failure_recall(
    failure_memory: FailureMemory,
    query: str,
    *,
    context: RecallContext,
) -> ShadowFailureRecall:
    """Inspect one governed recall via the existing specialized failure owner.

    Do not derive an action-block recommendation, new similarity score, or
    synthetic recurrence from these records. A process-local owner and a single
    admission call do not establish cross-process provenance or atomicity.
    """
    if not isinstance(failure_memory, FailureMemory):
        raise TypeError("failure_memory must be a native FailureMemory")
    if not isinstance(context, RecallContext):
        raise TypeError("context must be an existing governed RecallContext")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be nonempty text")

    result = failure_memory.recall_active(query, context=context)
    admitted = tuple(result.admitted_fact_uuids)
    admitted_ids = set(admitted)
    usable: list[UsableFailureEvidence] = []

    for ref in result.active_object_refs:
        decision = result.contextual_decisions.get(ref)
        if not isinstance(decision, dict) or decision.get("outcome") not in ADMITTING_OUTCOMES:
            # Even if an upstream result falsely labels the owner active, a
            # missing / review-required contextual receipt is not admission.
            continue
        current = failure_memory.current(ref)
        # A stale/externally modified owner state MUST NOT be turned into a
        # shadow acceptance. Do not promote generic admission to failure use.
        if current is None or current.memory_status != "active":
            continue
        fact_uuid = failure_memory.fact_uuid(current.revision_ref)
        if not fact_uuid or fact_uuid not in admitted_ids:
            continue
        usable.append(
            UsableFailureEvidence(
                failure_ref=ref,
                revision_ref=current.revision_ref,
                fact_uuid=fact_uuid,
                memory_status="active",
                causal_status=current.causal_status,
                severity_label=current.severity_label,
                occurrence_count=current.occurrence_count,
                action_class=current.action_class,
            )
        )

    return ShadowFailureRecall(
        query=query,
        candidate_fact_uuids=tuple(result.candidate_fact_uuids),
        generic_admitted_fact_uuids=admitted,
        usable_failures=tuple(usable),
        rejected_fact_reasons=tuple(sorted(result.refusals.items())),
        contextual_outcomes=tuple(
            sorted((ref, decision["outcome"])
                   for ref, decision in result.contextual_decisions.items())
        ),
    )
