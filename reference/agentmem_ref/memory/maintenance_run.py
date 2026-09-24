"""Maintenance-run evidence validation and native metabolism intake.

The metabolism integration in this module is deliberately a proposal adapter,
not a mutation executor.  It translates deterministic metabolism evidence into
existing PAMA proposal shapes and binds those proposal/evidence references into
the existing maintenance-run transaction contract.  PAMA evaluation, action
selection, commit/rollback/quarantine, and cursor progression remain owned by
the pre-existing authority and maintenance paths.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable

from ..core import policy
from .maintenance_run_bindings import validate_bindings
from .maintenance_run_rules import validate_rules
from .maintenance_run_state import seal
from .metabolism import (
    ARCHIVE_CANDIDATE,
    KEEP_ACTIVE,
    MANDATORY_DELETION_REVIEW,
    PRUNE_CANDIDATE,
    REQUIRE_REVIEW,
    RETENTION_HOLD,
    ConsolidationProposal,
    MetabolismEvaluation,
)


@dataclass(frozen=True)
class MetabolismMaintenanceContext:
    """Governance context used to construct existing PAMA proposal shapes.

    This context grants no authority.  In particular, ``risk_class`` and the
    PAMA target/authority classes are supplied by the caller's governed runtime,
    not inferred from a metabolism score.
    """

    actor_id: str
    charter_version: str
    target_class: str
    scope: str
    downstream_authority: str
    risk_class: str
    tenant_ref: str
    purpose: str
    isolation_domain_refs: tuple[str, ...]
    required_isolation_domain_refs: tuple[str, ...] = ()
    project_ref: str = ""
    task_ref: str = ""

    def __post_init__(self) -> None:
        required = (
            self.actor_id,
            self.charter_version,
            self.target_class,
            self.scope,
            self.downstream_authority,
            self.risk_class,
            self.tenant_ref,
            self.purpose,
        )
        if any(not value for value in required):
            raise ValueError("metabolism maintenance context requires complete authority scope")
        if self.risk_class not in {"low", "medium", "high", "critical"}:
            raise ValueError("unsupported metabolism maintenance risk class")
        if not self.isolation_domain_refs:
            raise ValueError("metabolism maintenance context requires isolation domains")
        if not set(self.required_isolation_domain_refs).issubset(
            set(self.isolation_domain_refs)
        ):
            raise ValueError("required isolation domains must be bound")


@dataclass(frozen=True)
class MetabolismMaintenanceProposal:
    """One metabolism-derived proposal routed toward existing PAMA authority."""

    consequence_family: str
    metabolism_evidence_ref: str
    proposal: policy.Proposal
    authority_effect: str = "none"


@dataclass(frozen=True)
class MetabolismMaintenancePlan:
    """Deterministic proposal intake for one maintenance transaction.

    Consolidation proposals remain proposal-only here.  An eligible derived
    consolidation is not silently relabeled as promotion or crystallization;
    once a concrete semantic mutation is proposed, that later consequence must
    receive its own existing PAMA operation and decision.
    """

    proposals: tuple[MetabolismMaintenanceProposal, ...]
    consolidation_proposals: tuple[ConsolidationProposal, ...]
    proposal_refs: tuple[str, ...]
    planned_operations: tuple[str, ...]
    estimator_evidence_refs: tuple[str, ...]
    context: MetabolismMaintenanceContext
    authority_effect: str = "none"


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _proposal(
    evaluation: MetabolismEvaluation,
    context: MetabolismMaintenanceContext,
    *,
    family: str,
    operation: str,
    proposed_strength: str = "not_applicable",
    reversibility: str = "reversible",
) -> MetabolismMaintenanceProposal:
    if evaluation.authority_effect != "none":
        raise ValueError("metabolism evidence must not carry mutation authority")
    evidence_ref = evaluation.evidence_ref
    proposal = policy.Proposal(
        proposal_id=f"{evidence_ref}:{family}",
        actor_id=context.actor_id,
        charter_version=context.charter_version,
        target_reference=evaluation.memory_ref,
        target_class=context.target_class,
        scope=context.scope,
        operation=operation,
        current_strength="not_applicable",
        proposed_strength=proposed_strength,
        downstream_authority=context.downstream_authority,
        reversibility=reversibility,
        risk_class=context.risk_class,
        evidence_refs=_unique((evidence_ref,) + evaluation.evidence_refs),
        estimator_refs=(evaluation.estimator_ref,),
        estimator_versions=(evaluation.profile_version,),
        tenant_ref=context.tenant_ref,
        purpose=context.purpose,
        isolation_domain_refs=context.isolation_domain_refs,
        required_isolation_domain_refs=context.required_isolation_domain_refs,
        project_ref=context.project_ref,
        task_ref=context.task_ref,
    )
    return MetabolismMaintenanceProposal(
        consequence_family=family,
        metabolism_evidence_ref=evidence_ref,
        proposal=proposal,
    )


def plan_metabolism_maintenance(
    evaluations: Iterable[MetabolismEvaluation],
    *,
    context: MetabolismMaintenanceContext,
    consolidation_proposals: Iterable[ConsolidationProposal] = (),
) -> MetabolismMaintenancePlan:
    """Translate metabolism evidence into deterministic maintenance proposals.

    The four native consequence families remain distinct:

    * decay pressure -> reversible ``score_adjustment`` proposal;
    * reinforcement/contradiction pressure -> separate ``score_adjustment`` proposal;
    * consolidation -> retained as a derived proposal only;
    * prune/archive candidacy -> ``pruning`` proposal, while mandatory deletion
      routes to the existing ``permanent_deletion`` operation.

    No proposal is evaluated or committed here.  A crystallization candidate is
    intentionally left as evidence rather than converted to a crystallization
    operation by saturation alone.
    """

    ordered = tuple(
        sorted(
            evaluations,
            key=lambda item: (item.memory_ref, item.evidence_ref),
        )
    )
    consolidation = tuple(
        sorted(
            consolidation_proposals,
            key=lambda item: item.proposal_ref,
        )
    )
    proposals: list[MetabolismMaintenanceProposal] = []

    for evaluation in ordered:
        if evaluation.authority_effect != "none" or evaluation.reinforcement.authority_effect != "none":
            raise ValueError("metabolism evidence must remain non-authoritative")

        if evaluation.decay_weight < 1.0:
            proposals.append(
                _proposal(
                    evaluation,
                    context,
                    family="decay_pressure",
                    operation="score_adjustment",
                )
            )

        reinforcement = evaluation.reinforcement
        if reinforcement.total_pressure > 0.0 or reinforcement.contradiction_pressure > 0.0:
            proposals.append(
                _proposal(
                    evaluation,
                    context,
                    family="reinforcement_pressure",
                    operation="score_adjustment",
                )
            )

        if evaluation.disposition in {ARCHIVE_CANDIDATE, PRUNE_CANDIDATE}:
            proposals.append(
                _proposal(
                    evaluation,
                    context,
                    family="prune_archive_candidacy",
                    operation="pruning",
                    proposed_strength="archived",
                )
            )
        elif evaluation.disposition == MANDATORY_DELETION_REVIEW:
            proposals.append(
                _proposal(
                    evaluation,
                    context,
                    family="prune_archive_candidacy",
                    operation="permanent_deletion",
                    reversibility="irreversible",
                )
            )
        elif evaluation.disposition not in {
            KEEP_ACTIVE,
            RETENTION_HOLD,
            REQUIRE_REVIEW,
        }:
            raise ValueError(f"unsupported metabolism disposition: {evaluation.disposition}")

    for item in consolidation:
        if item.authority_effect != "none":
            raise ValueError("consolidation proposal must remain non-authoritative")
        if item.certification_status != "not_established":
            raise ValueError("consolidation proposal must not establish certification")
        if item.derived_posture != "proposed_derived":
            raise ValueError("consolidation proposal must retain explicit derived posture")

    proposal_refs = _unique(
        tuple(item.proposal.proposal_id for item in proposals)
        + tuple(item.proposal_ref for item in consolidation)
    )
    planned_operations = _unique(
        tuple(item.proposal.operation for item in proposals)
    )
    estimator_evidence_refs = _unique(
        tuple(item.metabolism_evidence_ref for item in proposals)
        + tuple(evaluation.evidence_ref for evaluation in ordered)
    )

    return MetabolismMaintenancePlan(
        proposals=tuple(proposals),
        consolidation_proposals=consolidation,
        proposal_refs=proposal_refs,
        planned_operations=planned_operations,
        estimator_evidence_refs=estimator_evidence_refs,
        context=context,
    )


def bind_metabolism_plan(
    record: dict[str, Any],
    plan: MetabolismMaintenancePlan,
) -> dict[str, Any]:
    """Bind metabolism proposal/evidence refs into an existing run record.

    This function does not manufacture constituent decisions.  If a governed
    planned operation lacks an actual PAMA decision, ``validate_run`` will fail
    closed through the pre-existing binding rules.
    """

    if plan.authority_effect != "none":
        raise ValueError("maintenance plan must not carry mutation authority")

    context = plan.context
    actor = record["maintenance_actor"]
    scope = record["scope"]
    if actor["id"] != context.actor_id or actor["charter_ref"] != context.charter_version:
        raise ValueError("metabolism plan actor/charter does not match maintenance run")
    if scope["tenant_ref"] != context.tenant_ref or scope["purpose"] != context.purpose:
        raise ValueError("metabolism plan tenant/purpose does not match maintenance run")
    if context.project_ref and scope.get("project_ref", "") != context.project_ref:
        raise ValueError("metabolism plan project does not match maintenance run")
    if context.task_ref and scope.get("task_ref", "") != context.task_ref:
        raise ValueError("metabolism plan task does not match maintenance run")
    if not set(context.required_isolation_domain_refs).issubset(
        set(scope["isolation_domain_refs"])
    ):
        raise ValueError("maintenance run omits required metabolism isolation domain")

    result = deepcopy(record)
    result["proposal_refs"] = list(
        _unique(tuple(result.get("proposal_refs", ())) + plan.proposal_refs)
    )
    result["planned_operations"] = list(
        _unique(tuple(result.get("planned_operations", ())) + plan.planned_operations)
    )
    result["estimator_evidence_refs"] = list(
        _unique(
            tuple(result.get("estimator_evidence_refs", ()))
            + plan.estimator_evidence_refs
        )
    )
    return seal(result)


def validate_run(record: dict[str, Any], pama_decisions: dict[str, dict[str, Any]]) -> None:
    validate_rules(record)
    validate_bindings(record, pama_decisions)


def next_cursor(
    record: dict[str, Any],
    current_cursor: str | int,
    seen_run_ids: set[str],
) -> str | int:
    run_id = record["run_id"]
    if run_id in seen_run_ids:
        raise ValueError("duplicate run identity")
    if record["cursor_before"] != current_cursor:
        raise ValueError("cursor mismatch")
    seen_run_ids.add(run_id)
    if record["transaction_status"] == "committed":
        return record["cursor_after"]
    return current_cursor
