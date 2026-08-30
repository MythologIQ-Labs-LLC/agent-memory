"""Checkpoint-transition behavioral assessment for Agent Memory.

This reference module evaluates whether a memory checkpoint transition preserves
retrieval behavior that Agent Memory already treats as load-bearing. It emits
evidence. It does not approve a checkpoint, mutate memory, or grant PAMA
authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, Sequence

PROFILE_ID = "agent-memory/checkpoint-behavior"
PROFILE_VERSION = "0.1.0"


class BehavioralResult(str, Enum):
    """What the exercised probes established about retrieval behavior."""

    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"


class EvidencePosture(str, Enum):
    """Whether the evidence needed for a behavioral result was exercised."""

    EXERCISED = "exercised"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    NOT_EXERCISED = "not_exercised"


class ProbeKind(str, Enum):
    CORRECTION_PRECEDENCE = "correction_precedence"
    ANCHOR_PRESERVATION = "anchor_preservation"
    SCOPE_ISOLATION = "scope_isolation"
    STATE_CONDITIONED_DIFFERENTIATION = "state_conditioned_differentiation"


class RetrieverUnavailable(RuntimeError):
    """Raised when the configured retriever cannot be exercised."""


class UnsupportedProbe(RuntimeError):
    """Raised when a retriever cannot support a requested probe."""


class AssessmentStateChanged(RuntimeError):
    """Raised when bound checkpoint state changes while an assessment is running."""


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _parse_time(value: str) -> datetime:
    _require_text(value, "timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid RFC 3339 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class CheckpointBinding:
    checkpoint_ref: str
    state_digest: str

    def __post_init__(self) -> None:
        _require_text(self.checkpoint_ref, "checkpoint_ref")
        _require_text(self.state_digest, "state_digest")


@dataclass(frozen=True)
class RetrieverBinding:
    component_ref: str
    component_version: str
    profile_ref: str
    profile_version: str
    config_digest: str

    def __post_init__(self) -> None:
        for field_name in (
            "component_ref",
            "component_version",
            "profile_ref",
            "profile_version",
            "config_digest",
        ):
            _require_text(getattr(self, field_name), field_name)

    @property
    def digest(self) -> str:
        return _digest(
            {
                "component_ref": self.component_ref,
                "component_version": self.component_version,
                "profile_ref": self.profile_ref,
                "profile_version": self.profile_version,
                "config_digest": self.config_digest,
            }
        )


@dataclass(frozen=True)
class RetrievalRequest:
    request_ref: str
    query: str
    context_ref: str

    def __post_init__(self) -> None:
        _require_text(self.request_ref, "request_ref")
        _require_text(self.query, "query")
        _require_text(self.context_ref, "context_ref")


@dataclass(frozen=True)
class RetrievedItem:
    logical_ref: str
    rank: int
    version_ref: str = ""
    scope_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.logical_ref, "logical_ref")
        if self.rank < 1:
            raise ValueError("rank must be >= 1")
        if len(set(self.scope_refs)) != len(self.scope_refs):
            raise ValueError("scope_refs must not contain duplicates")
        if not all(isinstance(ref, str) and ref for ref in self.scope_refs):
            raise ValueError("scope_refs must contain non-empty strings")


@dataclass(frozen=True)
class ProbeDefinition:
    probe_id: str
    kind: ProbeKind
    required: bool = True
    baseline_request: RetrievalRequest | None = None
    candidate_request: RetrievalRequest | None = None
    corrected_ref: str = ""
    superseded_ref: str = ""
    anchor_refs: tuple[str, ...] = ()
    max_rank_drop: int = 0
    forbidden_refs: tuple[str, ...] = ()
    forbidden_scope_refs: tuple[str, ...] = ()
    expected_baseline_refs: tuple[str, ...] = ()
    expected_candidate_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.probe_id, "probe_id")
        if self.max_rank_drop < 0:
            raise ValueError("max_rank_drop must be >= 0")

        if self.kind is ProbeKind.CORRECTION_PRECEDENCE:
            if self.candidate_request is None:
                raise ValueError("correction_precedence requires candidate_request")
            _require_text(self.corrected_ref, "corrected_ref")
            _require_text(self.superseded_ref, "superseded_ref")
            if self.corrected_ref == self.superseded_ref:
                raise ValueError("corrected_ref and superseded_ref must differ")
        elif self.kind is ProbeKind.ANCHOR_PRESERVATION:
            if self.baseline_request is None or self.candidate_request is None:
                raise ValueError(
                    "anchor_preservation requires baseline and candidate requests"
                )
            if not self.anchor_refs:
                raise ValueError("anchor_preservation requires anchor_refs")
        elif self.kind is ProbeKind.SCOPE_ISOLATION:
            if self.candidate_request is None:
                raise ValueError("scope_isolation requires candidate_request")
            if not self.forbidden_refs and not self.forbidden_scope_refs:
                raise ValueError("scope_isolation requires a forbidden ref or scope")
        elif self.kind is ProbeKind.STATE_CONDITIONED_DIFFERENTIATION:
            if self.baseline_request is None or self.candidate_request is None:
                raise ValueError(
                    "state_conditioned_differentiation requires baseline and candidate requests"
                )
            if self.baseline_request.context_ref == self.candidate_request.context_ref:
                raise ValueError(
                    "state_conditioned_differentiation requires distinct contexts"
                )
            if not self.expected_baseline_refs or not self.expected_candidate_refs:
                raise ValueError(
                    "state_conditioned_differentiation requires expected refs for both states"
                )
            if set(self.expected_baseline_refs) == set(self.expected_candidate_refs):
                raise ValueError(
                    "state_conditioned_differentiation expectations must differ"
                )

        for values, field_name in (
            (self.anchor_refs, "anchor_refs"),
            (self.forbidden_refs, "forbidden_refs"),
            (self.forbidden_scope_refs, "forbidden_scope_refs"),
            (self.expected_baseline_refs, "expected_baseline_refs"),
            (self.expected_candidate_refs, "expected_candidate_refs"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
            if not all(isinstance(ref, str) and ref for ref in values):
                raise ValueError(f"{field_name} must contain non-empty strings")

    def identity(self) -> dict[str, object]:
        def request(value: RetrievalRequest | None) -> dict[str, str] | None:
            if value is None:
                return None
            return {
                "request_ref": value.request_ref,
                "query": value.query,
                "context_ref": value.context_ref,
            }

        return {
            "probe_id": self.probe_id,
            "kind": self.kind.value,
            "required": self.required,
            "baseline_request": request(self.baseline_request),
            "candidate_request": request(self.candidate_request),
            "corrected_ref": self.corrected_ref,
            "superseded_ref": self.superseded_ref,
            "anchor_refs": list(self.anchor_refs),
            "max_rank_drop": self.max_rank_drop,
            "forbidden_refs": list(self.forbidden_refs),
            "forbidden_scope_refs": list(self.forbidden_scope_refs),
            "expected_baseline_refs": list(self.expected_baseline_refs),
            "expected_candidate_refs": list(self.expected_candidate_refs),
        }


@dataclass(frozen=True)
class ProbeSuite:
    suite_ref: str
    suite_version: str
    probes: tuple[ProbeDefinition, ...]
    trials: int = 1

    def __post_init__(self) -> None:
        _require_text(self.suite_ref, "suite_ref")
        _require_text(self.suite_version, "suite_version")
        if not self.probes:
            raise ValueError("probe suite must contain at least one probe")
        ids = [probe.probe_id for probe in self.probes]
        if len(ids) != len(set(ids)):
            raise ValueError("probe IDs must be unique")
        if self.trials < 1:
            raise ValueError("trials must be >= 1")

    @property
    def digest(self) -> str:
        return _digest(
            {
                "suite_ref": self.suite_ref,
                "suite_version": self.suite_version,
                "trials": self.trials,
                "probes": [probe.identity() for probe in self.probes],
            }
        )


class CheckpointRetriever(Protocol):
    """Minimal adapter needed by the behavioral assessment harness."""

    @property
    def binding(self) -> RetrieverBinding: ...

    def state_digest(self, checkpoint_ref: str) -> str: ...

    def retrieve(
        self,
        checkpoint_ref: str,
        request: RetrievalRequest,
    ) -> Sequence[RetrievedItem]: ...


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    kind: ProbeKind
    required: bool
    result: BehavioralResult
    posture: EvidencePosture
    reason_codes: tuple[str, ...]
    invocation_digests: tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckpointBehavioralAssessment:
    assessment_id: str
    profile_id: str
    profile_version: str
    baseline: CheckpointBinding
    candidate: CheckpointBinding
    probe_suite_digest: str
    retriever_profile_digest: str
    result: BehavioralResult
    posture: EvidencePosture
    probe_results: tuple[ProbeResult, ...]
    started_at: str
    completed_at: str
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.authority_effect != "none":
            raise ValueError("behavioral assessment cannot grant authority")
        started = _parse_time(self.started_at)
        completed = _parse_time(self.completed_at)
        if completed < started:
            raise ValueError("completed_at must not precede started_at")


@dataclass(frozen=True)
class AssessmentRequirement:
    requirement_ref: str
    baseline: CheckpointBinding
    candidate: CheckpointBinding
    probe_suite_digest: str
    retriever_profile_digest: str
    not_before: str = ""
    not_after: str = ""

    def __post_init__(self) -> None:
        _require_text(self.requirement_ref, "requirement_ref")
        _require_text(self.probe_suite_digest, "probe_suite_digest")
        _require_text(self.retriever_profile_digest, "retriever_profile_digest")
        if self.not_before:
            _parse_time(self.not_before)
        if self.not_after:
            _parse_time(self.not_after)
        if self.not_before and self.not_after:
            if _parse_time(self.not_after) < _parse_time(self.not_before):
                raise ValueError("not_after must not precede not_before")


@dataclass(frozen=True)
class RequirementEvaluation:
    requirement_ref: str
    status: str
    reason_codes: tuple[str, ...]
    applicable_assessment_ids: tuple[str, ...]
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.status not in {"satisfied", "not_satisfied"}:
            raise ValueError("status must be satisfied or not_satisfied")
        if self.authority_effect != "none":
            raise ValueError("assessment requirement cannot grant authority")


def _items_by_ref(items: Sequence[RetrievedItem]) -> dict[str, RetrievedItem]:
    by_ref: dict[str, RetrievedItem] = {}
    ranks: set[int] = set()
    for item in items:
        if item.logical_ref in by_ref:
            raise ValueError(f"duplicate retrieved logical_ref: {item.logical_ref}")
        if item.rank in ranks:
            raise ValueError(f"duplicate retrieved rank: {item.rank}")
        by_ref[item.logical_ref] = item
        ranks.add(item.rank)
    return by_ref


def _observation_digest(
    checkpoint: CheckpointBinding,
    request: RetrievalRequest,
    items: Sequence[RetrievedItem],
) -> str:
    return _digest(
        {
            "checkpoint_ref": checkpoint.checkpoint_ref,
            "state_digest": checkpoint.state_digest,
            "request": {
                "request_ref": request.request_ref,
                "query": request.query,
                "context_ref": request.context_ref,
            },
            "items": [
                {
                    "logical_ref": item.logical_ref,
                    "version_ref": item.version_ref,
                    "rank": item.rank,
                    "scope_refs": list(item.scope_refs),
                }
                for item in items
            ],
        }
    )


def _combine_trial_results(
    trial_results: Sequence[BehavioralResult],
) -> BehavioralResult:
    if BehavioralResult.CONTRADICTED in trial_results:
        return BehavioralResult.CONTRADICTED
    if BehavioralResult.INCONCLUSIVE in trial_results:
        return BehavioralResult.INCONCLUSIVE
    return BehavioralResult.VERIFIED


def _evaluate_probe_once(
    *,
    probe: ProbeDefinition,
    retriever: CheckpointRetriever,
    baseline: CheckpointBinding,
    candidate: CheckpointBinding,
) -> tuple[BehavioralResult, tuple[str, ...], tuple[str, ...]]:
    invocation_digests: list[str] = []

    def invoke(
        checkpoint: CheckpointBinding,
        request: RetrievalRequest,
    ) -> tuple[RetrievedItem, ...]:
        items = tuple(retriever.retrieve(checkpoint.checkpoint_ref, request))
        _items_by_ref(items)
        invocation_digests.append(_observation_digest(checkpoint, request, items))
        return items

    if probe.kind is ProbeKind.CORRECTION_PRECEDENCE:
        assert probe.candidate_request is not None
        items = invoke(candidate, probe.candidate_request)
        by_ref = _items_by_ref(items)
        corrected = by_ref.get(probe.corrected_ref)
        superseded = by_ref.get(probe.superseded_ref)
        if corrected is None:
            return (
                BehavioralResult.CONTRADICTED,
                ("corrected_memory_missing",),
                tuple(invocation_digests),
            )
        if superseded is not None and superseded.rank <= corrected.rank:
            return (
                BehavioralResult.CONTRADICTED,
                ("superseded_memory_outranks_correction",),
                tuple(invocation_digests),
            )
        return (
            BehavioralResult.VERIFIED,
            ("correction_precedence_preserved",),
            tuple(invocation_digests),
        )

    if probe.kind is ProbeKind.ANCHOR_PRESERVATION:
        assert probe.baseline_request is not None
        assert probe.candidate_request is not None
        before = _items_by_ref(invoke(baseline, probe.baseline_request))
        after = _items_by_ref(invoke(candidate, probe.candidate_request))
        reasons: list[str] = []
        for anchor_ref in probe.anchor_refs:
            baseline_item = before.get(anchor_ref)
            candidate_item = after.get(anchor_ref)
            if baseline_item is None:
                return (
                    BehavioralResult.INCONCLUSIVE,
                    ("baseline_anchor_missing",),
                    tuple(invocation_digests),
                )
            if candidate_item is None:
                reasons.append("anchor_missing_after_transition")
                continue
            if candidate_item.rank > baseline_item.rank + probe.max_rank_drop:
                reasons.append("anchor_rank_regressed")
        if reasons:
            return (
                BehavioralResult.CONTRADICTED,
                tuple(dict.fromkeys(reasons)),
                tuple(invocation_digests),
            )
        return (
            BehavioralResult.VERIFIED,
            ("anchors_preserved",),
            tuple(invocation_digests),
        )

    if probe.kind is ProbeKind.SCOPE_ISOLATION:
        assert probe.candidate_request is not None
        items = invoke(candidate, probe.candidate_request)
        forbidden_refs = set(probe.forbidden_refs)
        forbidden_scopes = set(probe.forbidden_scope_refs)
        for item in items:
            if item.logical_ref in forbidden_refs:
                return (
                    BehavioralResult.CONTRADICTED,
                    ("forbidden_memory_retrieved",),
                    tuple(invocation_digests),
                )
            if forbidden_scopes.intersection(item.scope_refs):
                return (
                    BehavioralResult.CONTRADICTED,
                    ("forbidden_scope_retrieved",),
                    tuple(invocation_digests),
                )
        # This is intentionally a negative confidentiality property. Empty
        # retrieval proves only that this probe observed no forbidden hit.
        return (
            BehavioralResult.VERIFIED,
            ("no_forbidden_retrieval_observed",),
            tuple(invocation_digests),
        )

    assert probe.kind is ProbeKind.STATE_CONDITIONED_DIFFERENTIATION
    assert probe.baseline_request is not None
    assert probe.candidate_request is not None
    before_items = invoke(baseline, probe.baseline_request)
    after_items = invoke(candidate, probe.candidate_request)
    before = _items_by_ref(before_items)
    after = _items_by_ref(after_items)
    if not set(probe.expected_baseline_refs).issubset(before):
        return (
            BehavioralResult.CONTRADICTED,
            ("baseline_expected_memory_missing",),
            tuple(invocation_digests),
        )
    if not set(probe.expected_candidate_refs).issubset(after):
        return (
            BehavioralResult.CONTRADICTED,
            ("candidate_expected_memory_missing",),
            tuple(invocation_digests),
        )
    before_signature = tuple(
        item.logical_ref for item in sorted(before_items, key=lambda item: item.rank)
    )
    after_signature = tuple(
        item.logical_ref for item in sorted(after_items, key=lambda item: item.rank)
    )
    if before_signature == after_signature:
        return (
            BehavioralResult.CONTRADICTED,
            ("retrieval_state_collapsed",),
            tuple(invocation_digests),
        )
    return (
        BehavioralResult.VERIFIED,
        ("state_conditioned_retrieval_distinguished",),
        tuple(invocation_digests),
    )


def _evaluate_probe(
    *,
    probe: ProbeDefinition,
    suite: ProbeSuite,
    retriever: CheckpointRetriever,
    baseline: CheckpointBinding,
    candidate: CheckpointBinding,
) -> ProbeResult:
    trial_results: list[BehavioralResult] = []
    reason_codes: list[str] = []
    invocation_digests: list[str] = []
    posture = EvidencePosture.EXERCISED

    for _ in range(suite.trials):
        try:
            result, reasons, digests = _evaluate_probe_once(
                probe=probe,
                retriever=retriever,
                baseline=baseline,
                candidate=candidate,
            )
        except RetrieverUnavailable:
            result = BehavioralResult.INCONCLUSIVE
            reasons = ("retriever_unavailable",)
            digests = ()
            posture = EvidencePosture.UNAVAILABLE
        except UnsupportedProbe:
            result = BehavioralResult.INCONCLUSIVE
            reasons = ("probe_unsupported",)
            digests = ()
            if posture is EvidencePosture.EXERCISED:
                posture = EvidencePosture.UNSUPPORTED

        trial_results.append(result)
        reason_codes.extend(reasons)
        invocation_digests.extend(digests)

    return ProbeResult(
        probe_id=probe.probe_id,
        kind=probe.kind,
        required=probe.required,
        result=_combine_trial_results(trial_results),
        posture=posture,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        invocation_digests=tuple(invocation_digests),
    )


def assess_checkpoint_transition(
    *,
    baseline: CheckpointBinding,
    candidate: CheckpointBinding,
    suite: ProbeSuite,
    retriever: CheckpointRetriever,
    started_at: str,
    completed_at: str,
) -> CheckpointBehavioralAssessment:
    """Exercise the suite against one exact checkpoint transition.

    Checkpoint state is sampled before the first retrieval and again after the
    last retrieval. A mismatch aborts artifact construction rather than
    emitting evidence against a state that was not actually held constant.
    """

    started = _parse_time(started_at)
    completed = _parse_time(completed_at)
    if completed < started:
        raise ValueError("completed_at must not precede started_at")
    if baseline.checkpoint_ref == candidate.checkpoint_ref:
        raise ValueError("baseline and candidate checkpoint refs must differ")

    expected = {
        baseline.checkpoint_ref: baseline.state_digest,
        candidate.checkpoint_ref: candidate.state_digest,
    }
    before = {
        checkpoint_ref: retriever.state_digest(checkpoint_ref)
        for checkpoint_ref in expected
    }
    if before != expected:
        raise AssessmentStateChanged("checkpoint state did not match the bound precondition")

    probe_results = tuple(
        _evaluate_probe(
            probe=probe,
            suite=suite,
            retriever=retriever,
            baseline=baseline,
            candidate=candidate,
        )
        for probe in suite.probes
    )

    after = {
        checkpoint_ref: retriever.state_digest(checkpoint_ref)
        for checkpoint_ref in expected
    }
    if after != expected or after != before:
        raise AssessmentStateChanged("checkpoint state changed during assessment")

    required = [result for result in probe_results if result.required]
    aggregate = _combine_trial_results([result.result for result in required])

    if all(result.posture is EvidencePosture.EXERCISED for result in required):
        posture = EvidencePosture.EXERCISED
    elif any(result.posture is EvidencePosture.UNAVAILABLE for result in required):
        posture = EvidencePosture.UNAVAILABLE
    elif any(result.posture is EvidencePosture.UNSUPPORTED for result in required):
        posture = EvidencePosture.UNSUPPORTED
    else:
        posture = EvidencePosture.NOT_EXERCISED

    identity = {
        "profile_id": PROFILE_ID,
        "profile_version": PROFILE_VERSION,
        "baseline": {
            "checkpoint_ref": baseline.checkpoint_ref,
            "state_digest": baseline.state_digest,
        },
        "candidate": {
            "checkpoint_ref": candidate.checkpoint_ref,
            "state_digest": candidate.state_digest,
        },
        "probe_suite_digest": suite.digest,
        "retriever_profile_digest": retriever.binding.digest,
        "result": aggregate.value,
        "posture": posture.value,
        "probe_results": [
            {
                "probe_id": result.probe_id,
                "result": result.result.value,
                "posture": result.posture.value,
                "reason_codes": list(result.reason_codes),
                "invocation_digests": list(result.invocation_digests),
            }
            for result in probe_results
        ],
    }
    return CheckpointBehavioralAssessment(
        assessment_id="checkpoint-behavior:" + _digest(identity),
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        baseline=baseline,
        candidate=candidate,
        probe_suite_digest=suite.digest,
        retriever_profile_digest=retriever.binding.digest,
        result=aggregate,
        posture=posture,
        probe_results=probe_results,
        started_at=started_at,
        completed_at=completed_at,
    )


def _matches_requirement(
    requirement: AssessmentRequirement,
    assessment: CheckpointBehavioralAssessment,
    *,
    evaluated_at: datetime,
) -> bool:
    if assessment.profile_id != PROFILE_ID or assessment.profile_version != PROFILE_VERSION:
        return False
    if assessment.baseline != requirement.baseline:
        return False
    if assessment.candidate != requirement.candidate:
        return False
    if assessment.probe_suite_digest != requirement.probe_suite_digest:
        return False
    if assessment.retriever_profile_digest != requirement.retriever_profile_digest:
        return False
    completed = _parse_time(assessment.completed_at)
    if requirement.not_before and completed < _parse_time(requirement.not_before):
        return False
    if requirement.not_after and completed > _parse_time(requirement.not_after):
        return False
    if completed > evaluated_at:
        return False
    return True


def evaluate_assessment_requirement(
    requirement: AssessmentRequirement,
    assessments: Sequence[CheckpointBehavioralAssessment],
    *,
    evaluated_at: str,
) -> RequirementEvaluation:
    """Evaluate whether evidence satisfies this conformance requirement.

    The return value has no authority effect. PAMA, certification, release
    policy, or a consuming deployment decides what consequence follows from an
    unsatisfied requirement.
    """

    now = _parse_time(evaluated_at)
    applicable = tuple(
        assessment
        for assessment in assessments
        if _matches_requirement(requirement, assessment, evaluated_at=now)
    )
    ids = tuple(assessment.assessment_id for assessment in applicable)
    if not applicable:
        return RequirementEvaluation(
            requirement_ref=requirement.requirement_ref,
            status="not_satisfied",
            reason_codes=("no_applicable_assessment",),
            applicable_assessment_ids=(),
        )
    if any(
        assessment.posture is not EvidencePosture.EXERCISED
        for assessment in applicable
    ):
        return RequirementEvaluation(
            requirement_ref=requirement.requirement_ref,
            status="not_satisfied",
            reason_codes=("behavior_not_established",),
            applicable_assessment_ids=ids,
        )
    if any(
        assessment.result is BehavioralResult.CONTRADICTED
        for assessment in applicable
    ):
        return RequirementEvaluation(
            requirement_ref=requirement.requirement_ref,
            status="not_satisfied",
            reason_codes=("applicable_contradiction",),
            applicable_assessment_ids=ids,
        )
    if any(
        assessment.result is BehavioralResult.INCONCLUSIVE
        for assessment in applicable
    ):
        return RequirementEvaluation(
            requirement_ref=requirement.requirement_ref,
            status="not_satisfied",
            reason_codes=("applicable_inconclusive",),
            applicable_assessment_ids=ids,
        )
    return RequirementEvaluation(
        requirement_ref=requirement.requirement_ref,
        status="satisfied",
        reason_codes=("applicable_behavior_verified",),
        applicable_assessment_ids=ids,
    )
