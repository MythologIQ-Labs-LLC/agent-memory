"""Behavioral assessment for Agent Memory checkpoint transitions.

The assessment records retrieval evidence. It never approves a checkpoint,
mutates memory, or grants PAMA authority.
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
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"


class EvidencePosture(str, Enum):
    EXERCISED = "exercised"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    NOT_EXERCISED = "not_exercised"


class ProbeKind(str, Enum):
    CORRECTION_PRECEDENCE = "correction_precedence"
    ANCHOR_PRESERVATION = "anchor_preservation"
    SCOPE_ISOLATION = "scope_isolation"
    STATE_CONDITIONED_DIFFERENTIATION = "state_conditioned_differentiation"


class RecallStage(str, Enum):
    CANDIDATE = "candidate"
    ADMITTED = "admitted"
    CONTEXT_SURFACED = "context_surfaced"


class RetrieverUnavailable(RuntimeError):
    pass


class UnsupportedProbe(RuntimeError):
    pass


class AssessmentStateChanged(RuntimeError):
    pass


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} is required")


def _digest(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _time(value: str) -> datetime:
    _text(value, "timestamp")
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
        _text(self.checkpoint_ref, "checkpoint_ref")
        _text(self.state_digest, "state_digest")

    def to_dict(self) -> dict[str, str]:
        return {
            "checkpoint_ref": self.checkpoint_ref,
            "state_digest": self.state_digest,
        }


@dataclass(frozen=True)
class RetrieverBinding:
    component_ref: str
    component_version: str
    profile_ref: str
    profile_version: str
    config_digest: str
    assessment_stage: RecallStage = RecallStage.ADMITTED
    tie_policy_ref: str = "rank:stable-explicit-v1"

    def __post_init__(self) -> None:
        for name in (
            "component_ref",
            "component_version",
            "profile_ref",
            "profile_version",
            "config_digest",
            "tie_policy_ref",
        ):
            _text(getattr(self, name), name)
        if not isinstance(self.assessment_stage, RecallStage):
            raise ValueError("assessment_stage must be a RecallStage")

    @property
    def digest(self) -> str:
        return _digest(
            {
                "component_ref": self.component_ref,
                "component_version": self.component_version,
                "profile_ref": self.profile_ref,
                "profile_version": self.profile_version,
                "config_digest": self.config_digest,
                "assessment_stage": self.assessment_stage.value,
                "tie_policy_ref": self.tie_policy_ref,
            }
        )


@dataclass(frozen=True)
class RetrievalRequest:
    request_ref: str
    query: str
    context_ref: str

    def __post_init__(self) -> None:
        _text(self.request_ref, "request_ref")
        _text(self.query, "query")
        _text(self.context_ref, "context_ref")

    def to_dict(self) -> dict[str, str]:
        return {
            "request_ref": self.request_ref,
            "query": self.query,
            "context_ref": self.context_ref,
        }


@dataclass(frozen=True)
class RetrievedItem:
    logical_ref: str
    rank: int
    version_ref: str = ""
    scope_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.logical_ref, "logical_ref")
        if self.rank < 1:
            raise ValueError("rank must be >= 1")
        if len(set(self.scope_refs)) != len(self.scope_refs):
            raise ValueError("scope_refs must not contain duplicates")
        if not all(isinstance(ref, str) and ref for ref in self.scope_refs):
            raise ValueError("scope_refs must contain non-empty strings")

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_ref": self.logical_ref,
            "version_ref": self.version_ref,
            "rank": self.rank,
            "scope_refs": list(self.scope_refs),
        }


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
        _text(self.probe_id, "probe_id")
        if not isinstance(self.kind, ProbeKind):
            raise ValueError("kind must be a ProbeKind")
        if self.max_rank_drop < 0:
            raise ValueError("max_rank_drop must be >= 0")

        if self.kind is ProbeKind.CORRECTION_PRECEDENCE:
            if self.candidate_request is None:
                raise ValueError("correction_precedence requires candidate_request")
            _text(self.corrected_ref, "corrected_ref")
            _text(self.superseded_ref, "superseded_ref")
            if self.corrected_ref == self.superseded_ref:
                raise ValueError("corrected_ref and superseded_ref must differ")
        elif self.kind is ProbeKind.ANCHOR_PRESERVATION:
            if (
                self.baseline_request is None
                or self.candidate_request is None
                or not self.anchor_refs
            ):
                raise ValueError(
                    "anchor_preservation requires baseline/candidate requests and anchor_refs"
                )
        elif self.kind is ProbeKind.SCOPE_ISOLATION:
            if self.candidate_request is None or (
                not self.forbidden_refs and not self.forbidden_scope_refs
            ):
                raise ValueError(
                    "scope_isolation requires candidate_request and a forbidden ref or scope"
                )
        elif self.kind is ProbeKind.STATE_CONDITIONED_DIFFERENTIATION:
            if self.baseline_request is None or self.candidate_request is None:
                raise ValueError(
                    "state_conditioned_differentiation requires baseline and candidate requests"
                )
            if (
                self.baseline_request.context_ref
                == self.candidate_request.context_ref
            ):
                raise ValueError(
                    "state_conditioned_differentiation requires distinct contexts"
                )
            if not self.expected_baseline_refs or not self.expected_candidate_refs:
                raise ValueError(
                    "state_conditioned_differentiation requires expected refs for both states"
                )
            if set(self.expected_baseline_refs) == set(
                self.expected_candidate_refs
            ):
                raise ValueError(
                    "state_conditioned_differentiation expectations must differ"
                )

        for values, name in (
            (self.anchor_refs, "anchor_refs"),
            (self.forbidden_refs, "forbidden_refs"),
            (self.forbidden_scope_refs, "forbidden_scope_refs"),
            (self.expected_baseline_refs, "expected_baseline_refs"),
            (self.expected_candidate_refs, "expected_candidate_refs"),
        ):
            if len(values) != len(set(values)) or not all(
                isinstance(ref, str) and ref for ref in values
            ):
                raise ValueError(
                    f"{name} must contain unique non-empty strings"
                )

    def identity(self) -> dict[str, object]:
        return {
            "probe_id": self.probe_id,
            "kind": self.kind.value,
            "required": self.required,
            "baseline_request": (
                self.baseline_request.to_dict()
                if self.baseline_request
                else None
            ),
            "candidate_request": (
                self.candidate_request.to_dict()
                if self.candidate_request
                else None
            ),
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
        _text(self.suite_ref, "suite_ref")
        _text(self.suite_version, "suite_version")
        if self.trials < 1:
            raise ValueError("trials must be >= 1")
        ids = [probe.probe_id for probe in self.probes]
        if not self.probes or len(ids) != len(set(ids)):
            raise ValueError("probe IDs must be unique")
        required_kinds = {probe.kind for probe in self.probes if probe.required}
        if set(ProbeKind) - required_kinds:
            raise ValueError("required checkpoint probes missing")

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

    def to_dict(self) -> dict[str, object]:
        return {
            "probe_id": self.probe_id,
            "kind": self.kind.value,
            "required": self.required,
            "result": self.result.value,
            "posture": self.posture.value,
            "reason_codes": list(self.reason_codes),
            "invocation_digests": list(self.invocation_digests),
        }


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
        if _time(self.completed_at) < _time(self.started_at):
            raise ValueError("completed_at must not precede started_at")

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "probe_suite_digest": self.probe_suite_digest,
            "retriever_profile_digest": self.retriever_profile_digest,
            "result": self.result.value,
            "posture": self.posture.value,
            "probe_results": [result.to_dict() for result in self.probe_results],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "authority_effect": self.authority_effect,
        }


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
        _text(self.requirement_ref, "requirement_ref")
        _text(self.probe_suite_digest, "probe_suite_digest")
        _text(self.retriever_profile_digest, "retriever_profile_digest")
        if self.not_before:
            _time(self.not_before)
        if self.not_after:
            _time(self.not_after)
        if (
            self.not_before
            and self.not_after
            and _time(self.not_after) < _time(self.not_before)
        ):
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
            raise ValueError("invalid requirement status")
        if self.authority_effect != "none":
            raise ValueError("assessment requirement cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_ref": self.requirement_ref,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "applicable_assessment_ids": list(self.applicable_assessment_ids),
            "authority_effect": self.authority_effect,
        }


def _by_ref(items: Sequence[RetrievedItem]) -> dict[str, RetrievedItem]:
    refs: dict[str, RetrievedItem] = {}
    ranks: set[int] = set()
    for item in items:
        if item.logical_ref in refs:
            raise ValueError(
                f"duplicate retrieved logical_ref: {item.logical_ref}"
            )
        if item.rank in ranks:
            raise ValueError(f"duplicate retrieved rank: {item.rank}")
        refs[item.logical_ref] = item
        ranks.add(item.rank)
    return refs


def _observation_digest(
    checkpoint: CheckpointBinding,
    request: RetrievalRequest,
    items: Sequence[RetrievedItem],
    stage: RecallStage,
) -> str:
    return _digest(
        {
            "checkpoint": checkpoint.to_dict(),
            "request": request.to_dict(),
            "recall_stage": stage.value,
            "items": [item.to_dict() for item in items],
        }
    )


def _combine(results: Sequence[BehavioralResult]) -> BehavioralResult:
    if BehavioralResult.CONTRADICTED in results:
        return BehavioralResult.CONTRADICTED
    if BehavioralResult.INCONCLUSIVE in results:
        return BehavioralResult.INCONCLUSIVE
    return BehavioralResult.VERIFIED


def _evaluate_once(
    probe: ProbeDefinition,
    retriever: CheckpointRetriever,
    baseline: CheckpointBinding,
    candidate: CheckpointBinding,
) -> tuple[BehavioralResult, tuple[str, ...], tuple[str, ...]]:
    digests: list[str] = []

    def run(
        checkpoint: CheckpointBinding,
        request: RetrievalRequest,
    ) -> tuple[RetrievedItem, ...]:
        items = tuple(retriever.retrieve(checkpoint.checkpoint_ref, request))
        _by_ref(items)
        digests.append(
            _observation_digest(
                checkpoint,
                request,
                items,
                retriever.binding.assessment_stage,
            )
        )
        return items

    if probe.kind is ProbeKind.CORRECTION_PRECEDENCE:
        assert probe.candidate_request is not None
        found = _by_ref(run(candidate, probe.candidate_request))
        current = found.get(probe.corrected_ref)
        old = found.get(probe.superseded_ref)
        if current is None:
            return (
                BehavioralResult.CONTRADICTED,
                ("corrected_memory_missing",),
                tuple(digests),
            )
        if old is not None and old.rank <= current.rank:
            return (
                BehavioralResult.CONTRADICTED,
                ("superseded_memory_outranks_correction",),
                tuple(digests),
            )
        return (
            BehavioralResult.VERIFIED,
            ("correction_precedence_preserved",),
            tuple(digests),
        )

    if probe.kind is ProbeKind.ANCHOR_PRESERVATION:
        assert probe.baseline_request is not None
        assert probe.candidate_request is not None
        before = _by_ref(run(baseline, probe.baseline_request))
        after = _by_ref(run(candidate, probe.candidate_request))
        reasons: list[str] = []
        for ref in probe.anchor_refs:
            if ref not in before:
                return (
                    BehavioralResult.INCONCLUSIVE,
                    ("baseline_anchor_missing",),
                    tuple(digests),
                )
            if ref not in after:
                reasons.append("anchor_missing_after_transition")
            elif after[ref].rank > before[ref].rank + probe.max_rank_drop:
                reasons.append("anchor_rank_regressed")
        if reasons:
            return (
                BehavioralResult.CONTRADICTED,
                tuple(dict.fromkeys(reasons)),
                tuple(digests),
            )
        return (
            BehavioralResult.VERIFIED,
            ("anchors_preserved",),
            tuple(digests),
        )

    if probe.kind is ProbeKind.SCOPE_ISOLATION:
        assert probe.candidate_request is not None
        forbidden_refs = set(probe.forbidden_refs)
        forbidden_scopes = set(probe.forbidden_scope_refs)
        for item in run(candidate, probe.candidate_request):
            if item.logical_ref in forbidden_refs:
                return (
                    BehavioralResult.CONTRADICTED,
                    ("forbidden_memory_retrieved",),
                    tuple(digests),
                )
            if forbidden_scopes.intersection(item.scope_refs):
                return (
                    BehavioralResult.CONTRADICTED,
                    ("forbidden_scope_retrieved",),
                    tuple(digests),
                )
        return (
            BehavioralResult.VERIFIED,
            ("no_forbidden_retrieval_observed",),
            tuple(digests),
        )

    assert probe.baseline_request is not None
    assert probe.candidate_request is not None
    before_items = run(baseline, probe.baseline_request)
    after_items = run(candidate, probe.candidate_request)
    before = _by_ref(before_items)
    after = _by_ref(after_items)
    baseline_expected = set(probe.expected_baseline_refs)
    candidate_expected = set(probe.expected_candidate_refs)

    if not baseline_expected.issubset(before):
        return (
            BehavioralResult.CONTRADICTED,
            ("baseline_expected_memory_missing",),
            tuple(digests),
        )
    if not candidate_expected.issubset(after):
        return (
            BehavioralResult.CONTRADICTED,
            ("candidate_expected_memory_missing",),
            tuple(digests),
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
            tuple(digests),
        )
    if (baseline_expected - candidate_expected).intersection(after):
        return (
            BehavioralResult.CONTRADICTED,
            ("baseline_only_memory_leaked_into_candidate_state",),
            tuple(digests),
        )
    if (candidate_expected - baseline_expected).intersection(before):
        return (
            BehavioralResult.CONTRADICTED,
            ("candidate_only_memory_leaked_into_baseline_state",),
            tuple(digests),
        )
    return (
        BehavioralResult.VERIFIED,
        ("state_conditioned_retrieval_distinguished",),
        tuple(digests),
    )


def _evaluate_probe(
    probe: ProbeDefinition,
    suite: ProbeSuite,
    retriever: CheckpointRetriever,
    baseline: CheckpointBinding,
    candidate: CheckpointBinding,
) -> ProbeResult:
    results: list[BehavioralResult] = []
    reasons: list[str] = []
    digests: list[str] = []
    posture = EvidencePosture.EXERCISED

    for _ in range(suite.trials):
        try:
            result, trial_reasons, trial_digests = _evaluate_once(
                probe,
                retriever,
                baseline,
                candidate,
            )
        except RetrieverUnavailable:
            result = BehavioralResult.INCONCLUSIVE
            trial_reasons = ("retriever_unavailable",)
            trial_digests = ()
            posture = EvidencePosture.UNAVAILABLE
        except UnsupportedProbe:
            result = BehavioralResult.INCONCLUSIVE
            trial_reasons = ("probe_unsupported",)
            trial_digests = ()
            if posture is EvidencePosture.EXERCISED:
                posture = EvidencePosture.UNSUPPORTED

        results.append(result)
        reasons.extend(trial_reasons)
        digests.extend(trial_digests)

    return ProbeResult(
        probe_id=probe.probe_id,
        kind=probe.kind,
        required=probe.required,
        result=_combine(results),
        posture=posture,
        reason_codes=tuple(dict.fromkeys(reasons)),
        invocation_digests=tuple(digests),
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
    """Assess one exact transition while the bound checkpoint state is stable."""
    if _time(completed_at) < _time(started_at):
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
        raise AssessmentStateChanged(
            "checkpoint state did not match the bound precondition"
        )

    probe_results = tuple(
        _evaluate_probe(probe, suite, retriever, baseline, candidate)
        for probe in suite.probes
    )

    after = {
        checkpoint_ref: retriever.state_digest(checkpoint_ref)
        for checkpoint_ref in expected
    }
    if after != expected or after != before:
        raise AssessmentStateChanged("checkpoint state changed during assessment")

    required = [result for result in probe_results if result.required]
    aggregate = _combine([result.result for result in required])

    if all(
        result.posture is EvidencePosture.EXERCISED for result in required
    ):
        posture = EvidencePosture.EXERCISED
    elif any(
        result.posture is EvidencePosture.UNAVAILABLE for result in required
    ):
        posture = EvidencePosture.UNAVAILABLE
    elif any(
        result.posture is EvidencePosture.UNSUPPORTED for result in required
    ):
        posture = EvidencePosture.UNSUPPORTED
    else:
        posture = EvidencePosture.NOT_EXERCISED

    identity = {
        "profile_id": PROFILE_ID,
        "profile_version": PROFILE_VERSION,
        "baseline": baseline.to_dict(),
        "candidate": candidate.to_dict(),
        "probe_suite_digest": suite.digest,
        "retriever_profile_digest": retriever.binding.digest,
        "result": aggregate.value,
        "posture": posture.value,
        "probe_results": [result.to_dict() for result in probe_results],
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


def _applies(
    requirement: AssessmentRequirement,
    assessment: CheckpointBehavioralAssessment,
    evaluated_at: datetime,
) -> bool:
    if (
        assessment.profile_id != PROFILE_ID
        or assessment.profile_version != PROFILE_VERSION
    ):
        return False
    if assessment.baseline != requirement.baseline:
        return False
    if assessment.candidate != requirement.candidate:
        return False
    if assessment.probe_suite_digest != requirement.probe_suite_digest:
        return False
    if assessment.retriever_profile_digest != requirement.retriever_profile_digest:
        return False

    completed = _time(assessment.completed_at)
    if requirement.not_before and completed < _time(requirement.not_before):
        return False
    if requirement.not_after and completed > _time(requirement.not_after):
        return False
    return completed <= evaluated_at


def evaluate_assessment_requirement(
    requirement: AssessmentRequirement,
    assessments: Sequence[CheckpointBehavioralAssessment],
    *,
    evaluated_at: str,
) -> RequirementEvaluation:
    """Evaluate evidence applicability without granting any authority."""
    applicable = tuple(
        assessment
        for assessment in assessments
        if _applies(requirement, assessment, _time(evaluated_at))
    )
    ids = tuple(assessment.assessment_id for assessment in applicable)

    if not applicable:
        return RequirementEvaluation(
            requirement.requirement_ref,
            "not_satisfied",
            ("no_applicable_assessment",),
            (),
        )
    if any(
        assessment.result is BehavioralResult.CONTRADICTED
        for assessment in applicable
    ):
        return RequirementEvaluation(
            requirement.requirement_ref,
            "not_satisfied",
            ("applicable_contradiction",),
            ids,
        )
    if any(
        assessment.posture is not EvidencePosture.EXERCISED
        for assessment in applicable
    ):
        return RequirementEvaluation(
            requirement.requirement_ref,
            "not_satisfied",
            ("behavior_not_established",),
            ids,
        )
    if any(
        assessment.result is BehavioralResult.INCONCLUSIVE
        for assessment in applicable
    ):
        return RequirementEvaluation(
            requirement.requirement_ref,
            "not_satisfied",
            ("applicable_inconclusive",),
            ids,
        )
    return RequirementEvaluation(
        requirement.requirement_ref,
        "satisfied",
        ("applicable_behavior_verified",),
        ids,
    )
