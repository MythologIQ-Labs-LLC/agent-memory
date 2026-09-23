"""Checkpoint-transition behavioral conformance evidence.

This module harvests the still-valid behavioral probes from the historical
``implementation/332-checkpoint-behavioral-assessment`` branch into the current
harness layer. It is deliberately evidence-only: no result grants PAMA,
certification, recall-admission, deployment, or mutation authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

PROFILE_ID = "agent-memory/checkpoint-behavior-conformance"
PROFILE_VERSION = "1.0.0"


class BehavioralResult(str, Enum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"


class RecallStage(str, Enum):
    CANDIDATE = "candidate"
    ADMITTED = "admitted"
    CONTEXT_SURFACED = "context_surfaced"


class ObservationUnavailable(RuntimeError):
    """The declared observation could not be exercised."""


class CheckpointStateChanged(RuntimeError):
    """The checkpoint state moved while evidence was being collected."""


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class RetrievedItem:
    logical_ref: str
    rank: int
    scope_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.logical_ref:
            raise ValueError("logical_ref is required")
        if self.rank < 1:
            raise ValueError("rank must be >= 1")
        if len(set(self.scope_refs)) != len(self.scope_refs):
            raise ValueError("scope_refs must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_ref": self.logical_ref,
            "rank": self.rank,
            "scope_refs": list(self.scope_refs),
        }


@dataclass(frozen=True)
class CheckpointRef:
    checkpoint_ref: str
    state_digest: str

    def __post_init__(self) -> None:
        if not self.checkpoint_ref or not self.state_digest:
            raise ValueError("checkpoint_ref and state_digest are required")

    def to_dict(self) -> dict[str, str]:
        return {
            "checkpoint_ref": self.checkpoint_ref,
            "state_digest": self.state_digest,
        }


@dataclass(frozen=True)
class CheckpointBehaviorContract:
    baseline: CheckpointRef
    candidate: CheckpointRef
    recall_stage: RecallStage
    observer_ref: str
    observer_version: str
    observer_config_digest: str
    tie_policy_ref: str
    corrected_ref: str
    superseded_ref: str
    anchor_refs: tuple[str, ...]
    max_anchor_rank_drop: int
    forbidden_refs: tuple[str, ...]
    forbidden_scope_refs: tuple[str, ...]
    expected_baseline_refs: tuple[str, ...]
    expected_candidate_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.recall_stage, RecallStage):
            raise ValueError("recall_stage must be a RecallStage")
        for name in (
            "observer_ref",
            "observer_version",
            "observer_config_digest",
            "tie_policy_ref",
            "corrected_ref",
            "superseded_ref",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")
        if self.corrected_ref == self.superseded_ref:
            raise ValueError("corrected_ref and superseded_ref must differ")
        if not self.anchor_refs:
            raise ValueError("at least one anchor_ref is required")
        if self.max_anchor_rank_drop < 0:
            raise ValueError("max_anchor_rank_drop must be >= 0")
        if not self.forbidden_refs and not self.forbidden_scope_refs:
            raise ValueError("scope isolation requires a forbidden ref or scope")
        if not self.expected_baseline_refs or not self.expected_candidate_refs:
            raise ValueError("state-conditioned expectations are required")
        if set(self.expected_baseline_refs) == set(self.expected_candidate_refs):
            raise ValueError("state-conditioned expectations must differ")

    @property
    def observer_binding_digest(self) -> str:
        return _digest(
            {
                "observer_ref": self.observer_ref,
                "observer_version": self.observer_version,
                "observer_config_digest": self.observer_config_digest,
                "recall_stage": self.recall_stage.value,
                "tie_policy_ref": self.tie_policy_ref,
            }
        )

    @property
    def contract_digest(self) -> str:
        return _digest(
            {
                "baseline": self.baseline.to_dict(),
                "candidate": self.candidate.to_dict(),
                "observer_binding_digest": self.observer_binding_digest,
                "corrected_ref": self.corrected_ref,
                "superseded_ref": self.superseded_ref,
                "anchor_refs": list(self.anchor_refs),
                "max_anchor_rank_drop": self.max_anchor_rank_drop,
                "forbidden_refs": list(self.forbidden_refs),
                "forbidden_scope_refs": list(self.forbidden_scope_refs),
                "expected_baseline_refs": list(self.expected_baseline_refs),
                "expected_candidate_refs": list(self.expected_candidate_refs),
            }
        )


class CheckpointBehaviorObserver(Protocol):
    def state_digest(self, checkpoint_ref: str) -> str: ...

    def observe(
        self,
        checkpoint_ref: str,
        observation_ref: str,
        stage: RecallStage,
    ) -> Sequence[RetrievedItem]: ...


@dataclass(frozen=True)
class ProbeResult:
    probe: str
    result: BehavioralResult
    reason_codes: tuple[str, ...]
    observation_digests: tuple[str, ...]
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.authority_effect != "none":
            raise ValueError("checkpoint behavior probes cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        return {
            "probe": self.probe,
            "result": self.result.value,
            "reason_codes": list(self.reason_codes),
            "observation_digests": list(self.observation_digests),
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class CheckpointBehaviorAssessment:
    profile_id: str
    profile_version: str
    baseline: CheckpointRef
    candidate: CheckpointRef
    contract_digest: str
    observer_binding_digest: str
    result: BehavioralResult
    probe_results: tuple[ProbeResult, ...]
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.authority_effect != "none":
            raise ValueError("checkpoint behavior assessment cannot grant authority")

    @property
    def assessment_id(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "contract_digest": self.contract_digest,
            "observer_binding_digest": self.observer_binding_digest,
            "result": self.result.value,
            "probe_results": [item.to_dict() for item in self.probe_results],
            "authority_effect": self.authority_effect,
        }


def _items_by_ref(items: Sequence[RetrievedItem]) -> dict[str, RetrievedItem]:
    refs: dict[str, RetrievedItem] = {}
    ranks: set[int] = set()
    for item in items:
        if item.logical_ref in refs:
            raise ValueError(f"duplicate retrieved logical_ref: {item.logical_ref}")
        if item.rank in ranks:
            raise ValueError(f"duplicate retrieved rank: {item.rank}")
        refs[item.logical_ref] = item
        ranks.add(item.rank)
    return refs


def _observe(
    observer: CheckpointBehaviorObserver,
    checkpoint: CheckpointRef,
    observation_ref: str,
    stage: RecallStage,
) -> tuple[Sequence[RetrievedItem] | None, str]:
    try:
        items = tuple(observer.observe(checkpoint.checkpoint_ref, observation_ref, stage))
    except ObservationUnavailable:
        return None, _digest(
            {
                "checkpoint": checkpoint.to_dict(),
                "observation_ref": observation_ref,
                "stage": stage.value,
                "posture": "unavailable",
            }
        )
    return items, _digest(
        {
            "checkpoint": checkpoint.to_dict(),
            "observation_ref": observation_ref,
            "stage": stage.value,
            "items": [item.to_dict() for item in items],
        }
    )


def _combine(results: Sequence[ProbeResult]) -> BehavioralResult:
    values = [item.result for item in results]
    if BehavioralResult.CONTRADICTED in values:
        return BehavioralResult.CONTRADICTED
    if BehavioralResult.INCONCLUSIVE in values:
        return BehavioralResult.INCONCLUSIVE
    return BehavioralResult.VERIFIED


def assess_checkpoint_behavior(
    contract: CheckpointBehaviorContract,
    observer: CheckpointBehaviorObserver,
) -> CheckpointBehaviorAssessment:
    """Exercise four first-party checkpoint behavior probes.

    State digests are checked before and after observation collection. A change
    aborts the assessment rather than binding evidence to a checkpoint state
    that was not actually observed.
    """
    for checkpoint in (contract.baseline, contract.candidate):
        if observer.state_digest(checkpoint.checkpoint_ref) != checkpoint.state_digest:
            raise CheckpointStateChanged(
                f"checkpoint {checkpoint.checkpoint_ref} does not match bound precondition"
            )

    results: list[ProbeResult] = []

    correction, correction_digest = _observe(
        observer,
        contract.candidate,
        "correction_precedence",
        contract.recall_stage,
    )
    if correction is None:
        results.append(
            ProbeResult(
                "correction_precedence",
                BehavioralResult.INCONCLUSIVE,
                ("observation_unavailable",),
                (correction_digest,),
            )
        )
    else:
        by_ref = _items_by_ref(correction)
        corrected = by_ref.get(contract.corrected_ref)
        superseded = by_ref.get(contract.superseded_ref)
        reasons: list[str] = []
        if corrected is None:
            reasons.append("corrected_memory_missing")
        elif superseded is not None and superseded.rank < corrected.rank:
            reasons.append("superseded_memory_outranks_correction")
        results.append(
            ProbeResult(
                "correction_precedence",
                BehavioralResult.CONTRADICTED if reasons else BehavioralResult.VERIFIED,
                tuple(reasons or ["correction_precedence_preserved"]),
                (correction_digest,),
            )
        )

    anchor_before, anchor_before_digest = _observe(
        observer,
        contract.baseline,
        "anchor_preservation",
        contract.recall_stage,
    )
    anchor_after, anchor_after_digest = _observe(
        observer,
        contract.candidate,
        "anchor_preservation",
        contract.recall_stage,
    )
    if anchor_before is None or anchor_after is None:
        anchor_result = ProbeResult(
            "anchor_preservation",
            BehavioralResult.INCONCLUSIVE,
            ("observation_unavailable",),
            (anchor_before_digest, anchor_after_digest),
        )
    else:
        before = _items_by_ref(anchor_before)
        after = _items_by_ref(anchor_after)
        reasons = []
        inconclusive = False
        for ref in contract.anchor_refs:
            if ref not in before:
                reasons.append("baseline_anchor_missing")
                inconclusive = True
                continue
            if ref not in after:
                reasons.append("anchor_missing_after_transition")
                continue
            if after[ref].rank - before[ref].rank > contract.max_anchor_rank_drop:
                reasons.append("anchor_rank_regressed")
        if inconclusive:
            result = BehavioralResult.INCONCLUSIVE
        elif reasons:
            result = BehavioralResult.CONTRADICTED
        else:
            result = BehavioralResult.VERIFIED
        anchor_result = ProbeResult(
            "anchor_preservation",
            result,
            tuple(reasons or ["anchor_preserved"]),
            (anchor_before_digest, anchor_after_digest),
        )
    results.append(anchor_result)

    scope_items, scope_digest = _observe(
        observer,
        contract.candidate,
        "scope_isolation",
        contract.recall_stage,
    )
    if scope_items is None:
        results.append(
            ProbeResult(
                "scope_isolation",
                BehavioralResult.INCONCLUSIVE,
                ("observation_unavailable",),
                (scope_digest,),
            )
        )
    else:
        forbidden_refs = set(contract.forbidden_refs)
        forbidden_scopes = set(contract.forbidden_scope_refs)
        reasons = []
        if any(item.logical_ref in forbidden_refs for item in scope_items):
            reasons.append("forbidden_ref_retrieved")
        if any(forbidden_scopes.intersection(item.scope_refs) for item in scope_items):
            reasons.append("forbidden_scope_retrieved")
        results.append(
            ProbeResult(
                "scope_isolation",
                BehavioralResult.CONTRADICTED if reasons else BehavioralResult.VERIFIED,
                tuple(reasons or ["no_forbidden_retrieval_observed"]),
                (scope_digest,),
            )
        )

    state_before, state_before_digest = _observe(
        observer,
        contract.baseline,
        "state_conditioned_differentiation",
        contract.recall_stage,
    )
    state_after, state_after_digest = _observe(
        observer,
        contract.candidate,
        "state_conditioned_differentiation",
        contract.recall_stage,
    )
    if state_before is None or state_after is None:
        state_result = ProbeResult(
            "state_conditioned_differentiation",
            BehavioralResult.INCONCLUSIVE,
            ("observation_unavailable",),
            (state_before_digest, state_after_digest),
        )
    else:
        before_refs = {item.logical_ref for item in state_before}
        after_refs = {item.logical_ref for item in state_after}
        reasons = []
        if before_refs == after_refs:
            reasons.append("retrieval_state_collapsed")
        candidate_only = set(contract.expected_candidate_refs) - set(contract.expected_baseline_refs)
        baseline_only = set(contract.expected_baseline_refs) - set(contract.expected_candidate_refs)
        if candidate_only.intersection(before_refs):
            reasons.append("candidate_only_memory_leaked_into_baseline_state")
        if baseline_only.intersection(after_refs):
            reasons.append("baseline_only_memory_leaked_into_candidate_state")
        if not set(contract.expected_baseline_refs).issubset(before_refs):
            reasons.append("expected_baseline_memory_missing")
        if not set(contract.expected_candidate_refs).issubset(after_refs):
            reasons.append("expected_candidate_memory_missing")
        state_result = ProbeResult(
            "state_conditioned_differentiation",
            BehavioralResult.CONTRADICTED if reasons else BehavioralResult.VERIFIED,
            tuple(reasons or ["state_conditioned_retrieval_preserved"]),
            (state_before_digest, state_after_digest),
        )
    results.append(state_result)

    for checkpoint in (contract.baseline, contract.candidate):
        if observer.state_digest(checkpoint.checkpoint_ref) != checkpoint.state_digest:
            raise CheckpointStateChanged(
                f"checkpoint {checkpoint.checkpoint_ref} changed during assessment"
            )

    return CheckpointBehaviorAssessment(
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        baseline=contract.baseline,
        candidate=contract.candidate,
        contract_digest=contract.contract_digest,
        observer_binding_digest=contract.observer_binding_digest,
        result=_combine(results),
        probe_results=tuple(results),
    )


@dataclass(frozen=True)
class AssessmentRequirement:
    baseline: CheckpointRef
    candidate: CheckpointRef
    contract_digest: str
    observer_binding_digest: str


@dataclass(frozen=True)
class RequirementEvaluation:
    status: str
    reason_codes: tuple[str, ...]
    applicable_assessment_ids: tuple[str, ...]
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.status not in {"satisfied", "not_satisfied"}:
            raise ValueError("invalid requirement status")
        if self.authority_effect != "none":
            raise ValueError("checkpoint behavior requirement cannot grant authority")


def evaluate_requirement(
    requirement: AssessmentRequirement,
    assessments: Sequence[CheckpointBehaviorAssessment],
) -> RequirementEvaluation:
    """Evaluate exact-bound evidence without granting consequence authority."""
    applicable = [
        item
        for item in assessments
        if item.baseline == requirement.baseline
        and item.candidate == requirement.candidate
        and item.contract_digest == requirement.contract_digest
        and item.observer_binding_digest == requirement.observer_binding_digest
    ]
    if not applicable:
        return RequirementEvaluation("not_satisfied", ("no_applicable_assessment",), ())
    if any(item.result is BehavioralResult.CONTRADICTED for item in applicable):
        return RequirementEvaluation(
            "not_satisfied",
            ("applicable_contradiction",),
            tuple(item.assessment_id for item in applicable),
        )
    if not any(item.result is BehavioralResult.VERIFIED for item in applicable):
        return RequirementEvaluation(
            "not_satisfied",
            ("applicable_evidence_inconclusive",),
            tuple(item.assessment_id for item in applicable),
        )
    return RequirementEvaluation(
        "satisfied",
        ("exact_verified_assessment_present",),
        tuple(item.assessment_id for item in applicable),
    )
