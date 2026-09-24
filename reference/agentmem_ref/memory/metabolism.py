"""Agent Memory-native deterministic cognitive metabolism for issue #463.

This module turns explicit lifecycle observations into non-authoritative decay,
reinforcement, consolidation, and prune/archive proposals.  It deliberately
contains no storage mutation or PAMA shortcut: every output has
``authority_effect = "none"`` and consequential state changes remain owned by
the existing lifecycle/governance/maintenance path.

The first profile is stdlib-only and stateless.  Fixed observations plus fixed
configuration therefore produce identical evidence across restart without
hidden mutable access counters or provider state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from typing import Iterable


PROFILE_VERSION = "1.0.0"
ESTIMATOR_REF = "agent-memory:native-metabolism"
DECAY_FORMULA_REF = "cmhl-bounded-v1"
REINFORCEMENT_FORMULA_REF = "bounded-weighted-pinning-v1"

KEEP_ACTIVE = "keep_active"
ARCHIVE_CANDIDATE = "archive_candidate"
PRUNE_CANDIDATE = "prune_candidate"
RETENTION_HOLD = "retention_hold"
REQUIRE_REVIEW = "require_review"
MANDATORY_DELETION_REVIEW = "mandatory_deletion_review"

ACCESS = "access"
CROSS_REFERENCE = "cross_reference"
CORROBORATION = "corroboration"
VERIFICATION = "verification"
TASK_SUCCESS = "task_success"
USER_RETENTION_SIGNAL = "user_retention_signal"
REINFORCEMENT_KINDS = frozenset(
    {
        ACCESS,
        CROSS_REFERENCE,
        CORROBORATION,
        VERIFICATION,
        TASK_SUCCESS,
        USER_RETENTION_SIGNAL,
    }
)


class MetabolismValidationError(ValueError):
    """Raised when a metabolism input would make semantics ambiguous."""


def _unit_interval(name: str, value: float) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or not 0.0 <= parsed <= 1.0:
        raise MetabolismValidationError(f"{name} must be finite and between 0 and 1")
    return parsed


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_ref(value: object) -> str:
    return "sha256:" + hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


@dataclass(frozen=True)
class MetabolismConfig:
    """Version-bound deterministic operating point for the first profile."""

    half_life_ms: int = 604_800_000  # seven days
    prune_enter_weight: float = 0.20
    prune_exit_weight: float = 0.30
    archive_weight: float = 0.45
    access_event_weight: float = 0.001
    max_access_contribution: float = 0.05
    cross_reference_weight: float = 0.04
    corroboration_weight: float = 0.08
    verification_weight: float = 0.15
    task_success_weight: float = 0.06
    user_retention_signal_weight: float = 0.20
    crystallization_candidate_saturation: float = 0.80

    def __post_init__(self) -> None:
        if self.half_life_ms <= 0:
            raise MetabolismValidationError("half_life_ms must be positive")
        for name in (
            "prune_enter_weight",
            "prune_exit_weight",
            "archive_weight",
            "access_event_weight",
            "max_access_contribution",
            "cross_reference_weight",
            "corroboration_weight",
            "verification_weight",
            "task_success_weight",
            "user_retention_signal_weight",
            "crystallization_candidate_saturation",
        ):
            _unit_interval(name, getattr(self, name))
        if not self.prune_enter_weight < self.prune_exit_weight <= self.archive_weight:
            raise MetabolismValidationError(
                "thresholds must satisfy prune_enter < prune_exit <= archive"
            )

    @property
    def config_digest(self) -> str:
        return _sha256_ref(asdict(self))

    def weight_for(self, kind: str) -> float:
        mapping = {
            ACCESS: self.access_event_weight,
            CROSS_REFERENCE: self.cross_reference_weight,
            CORROBORATION: self.corroboration_weight,
            VERIFICATION: self.verification_weight,
            TASK_SUCCESS: self.task_success_weight,
            USER_RETENTION_SIGNAL: self.user_retention_signal_weight,
        }
        try:
            return mapping[kind]
        except KeyError as exc:
            raise MetabolismValidationError(f"unsupported reinforcement kind {kind!r}") from exc


@dataclass(frozen=True)
class ReinforcementObservation:
    """One explicit class of lifecycle support, never an authority record."""

    kind: str
    count: int = 1
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in REINFORCEMENT_KINDS:
            raise MetabolismValidationError(f"unsupported reinforcement kind {self.kind!r}")
        if self.count < 0:
            raise MetabolismValidationError("reinforcement count cannot be negative")
        object.__setattr__(self, "evidence_refs", _unique(self.evidence_refs))


@dataclass(frozen=True)
class RetentionConstraints:
    """Hard constraints that cannot be overruled by a low decay score."""

    legal_or_compliance_hold: bool = False
    user_pin: bool = False
    active_commitment: bool = False
    unresolved_dispute: bool = False
    certified_evidence_dependency: bool = False
    provenance_dependency: bool = False
    tombstone_or_residue_required: bool = False
    active_dependency: bool = False
    mandatory_deletion: bool = False

    def ordinary_prune_blockers(self) -> tuple[str, ...]:
        mapping = (
            ("legal_or_compliance_hold", self.legal_or_compliance_hold),
            ("user_pin", self.user_pin),
            ("active_commitment", self.active_commitment),
            ("unresolved_dispute", self.unresolved_dispute),
            ("certified_evidence_dependency", self.certified_evidence_dependency),
            ("provenance_dependency", self.provenance_dependency),
            ("tombstone_or_residue_required", self.tombstone_or_residue_required),
            ("active_dependency", self.active_dependency),
        )
        return tuple(name for name, active in mapping if active)


@dataclass(frozen=True)
class MetabolismSnapshot:
    """Complete deterministic input snapshot for one memory evaluation.

    ``last_meaningful_use_ms`` is intentionally distinct from event time and
    transaction time.  Callers must choose and record the lifecycle observation
    that represents meaningful reuse rather than silently reusing another clock.
    """

    memory_ref: str
    lifecycle_state: str
    evaluated_at_ms: int
    last_meaningful_use_ms: int
    baseline_saturation: float = 0.0
    contradiction_pressure: float = 0.0
    reinforcement_observations: tuple[ReinforcementObservation, ...] = ()
    constraints: RetentionConstraints = field(default_factory=RetentionConstraints)
    prior_prune_candidate: bool = False
    scope_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.memory_ref:
            raise MetabolismValidationError("memory_ref is required")
        if not self.lifecycle_state:
            raise MetabolismValidationError("lifecycle_state is required")
        if self.evaluated_at_ms < 0 or self.last_meaningful_use_ms < 0:
            raise MetabolismValidationError("metabolism timestamps cannot be negative")
        _unit_interval("baseline_saturation", self.baseline_saturation)
        _unit_interval("contradiction_pressure", self.contradiction_pressure)
        object.__setattr__(
            self,
            "reinforcement_observations",
            tuple(self.reinforcement_observations),
        )
        object.__setattr__(self, "scope_refs", _unique(self.scope_refs))
        object.__setattr__(self, "evidence_refs", _unique(self.evidence_refs))


@dataclass(frozen=True)
class ReinforcementEvidence:
    """Explainable bounded reinforcement calculation."""

    contributions: tuple[tuple[str, float], ...]
    total_pressure: float
    saturation_before: float
    saturation_after_reinforcement: float
    contradiction_pressure: float
    effective_saturation: float
    formula_ref: str = REINFORCEMENT_FORMULA_REF
    authority_effect: str = "none"


@dataclass(frozen=True)
class MetabolismEvaluation:
    """Non-authoritative metabolism result for one memory snapshot."""

    memory_ref: str
    lifecycle_state: str
    evaluated_at_ms: int
    elapsed_since_meaningful_use_ms: int
    decay_weight: float
    reinforcement: ReinforcementEvidence
    disposition: str
    disposition_reasons: tuple[str, ...]
    prune_threshold_used: float
    crystallization_candidate: bool
    evidence_refs: tuple[str, ...]
    scope_refs: tuple[str, ...]
    estimator_ref: str
    profile_version: str
    config_digest: str
    decay_formula_ref: str = DECAY_FORMULA_REF
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_ref": self.memory_ref,
            "lifecycle_state": self.lifecycle_state,
            "evaluated_at_ms": self.evaluated_at_ms,
            "elapsed_since_meaningful_use_ms": self.elapsed_since_meaningful_use_ms,
            "decay_weight": self.decay_weight,
            "reinforcement": {
                "contributions": [
                    {"kind": kind, "pressure": pressure}
                    for kind, pressure in self.reinforcement.contributions
                ],
                "total_pressure": self.reinforcement.total_pressure,
                "saturation_before": self.reinforcement.saturation_before,
                "saturation_after_reinforcement": self.reinforcement.saturation_after_reinforcement,
                "contradiction_pressure": self.reinforcement.contradiction_pressure,
                "effective_saturation": self.reinforcement.effective_saturation,
                "formula_ref": self.reinforcement.formula_ref,
                "authority_effect": self.reinforcement.authority_effect,
            },
            "disposition": self.disposition,
            "disposition_reasons": list(self.disposition_reasons),
            "prune_threshold_used": self.prune_threshold_used,
            "crystallization_candidate": self.crystallization_candidate,
            "evidence_refs": list(self.evidence_refs),
            "scope_refs": list(self.scope_refs),
            "estimator_ref": self.estimator_ref,
            "profile_version": self.profile_version,
            "config_digest": self.config_digest,
            "decay_formula_ref": self.decay_formula_ref,
            "authority_effect": self.authority_effect,
        }

    @property
    def evidence_ref(self) -> str:
        return f"metabolism-evidence:{_sha256_ref(self.to_dict())}"


@dataclass(frozen=True)
class ConsolidationSource:
    """One current source proposed for deterministic consolidation."""

    memory_ref: str
    fact_ref: str
    currentness: str
    scope_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    exception_refs: tuple[str, ...] = ()
    disputed: bool = False

    def __post_init__(self) -> None:
        if not self.memory_ref or not self.fact_ref:
            raise MetabolismValidationError("consolidation source requires memory_ref and fact_ref")
        object.__setattr__(self, "scope_refs", _unique(self.scope_refs))
        object.__setattr__(self, "evidence_refs", _unique(self.evidence_refs))
        object.__setattr__(self, "exception_refs", _unique(self.exception_refs))


@dataclass(frozen=True)
class ConsolidationProposal:
    """Derived-state proposal.  It is never a certification or commit."""

    proposal_ref: str
    source_memory_refs: tuple[str, ...]
    source_fact_refs: tuple[str, ...]
    target_scope_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    exception_refs: tuple[str, ...]
    method_ref: str
    method_version: str
    eligible: bool
    reasons: tuple[str, ...]
    derived_posture: str = "proposed_derived"
    certification_status: str = "not_established"
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_ref": self.proposal_ref,
            "source_memory_refs": list(self.source_memory_refs),
            "source_fact_refs": list(self.source_fact_refs),
            "target_scope_refs": list(self.target_scope_refs),
            "evidence_refs": list(self.evidence_refs),
            "exception_refs": list(self.exception_refs),
            "method_ref": self.method_ref,
            "method_version": self.method_version,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "derived_posture": self.derived_posture,
            "certification_status": self.certification_status,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class MetabolismBatchEvidence:
    """Stable evidence bundle suitable for a governed maintenance run."""

    evaluations: tuple[MetabolismEvaluation, ...]
    estimator_ref: str
    profile_version: str
    config_digest: str
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, object]:
        return {
            "evaluations": [evaluation.to_dict() for evaluation in self.evaluations],
            "estimator_ref": self.estimator_ref,
            "profile_version": self.profile_version,
            "config_digest": self.config_digest,
            "authority_effect": self.authority_effect,
        }

    @property
    def evidence_ref(self) -> str:
        return f"metabolism-batch:{_sha256_ref(self.to_dict())}"


class NativeMetabolismEstimator:
    """Stateless deterministic first profile for Agent Memory metabolism."""

    def __init__(self, config: MetabolismConfig | None = None) -> None:
        self.config = config or MetabolismConfig()

    def evaluate(self, snapshot: MetabolismSnapshot) -> MetabolismEvaluation:
        reinforcement = self.reinforcement(snapshot)
        elapsed = max(0, snapshot.evaluated_at_ms - snapshot.last_meaningful_use_ms)
        decay_weight = self.decay_weight(
            elapsed_ms=elapsed,
            effective_saturation=reinforcement.effective_saturation,
        )
        disposition, reasons, threshold = self._disposition(
            snapshot,
            decay_weight=decay_weight,
            effective_saturation=reinforcement.effective_saturation,
        )
        evidence_refs = list(snapshot.evidence_refs)
        for observation in snapshot.reinforcement_observations:
            evidence_refs.extend(observation.evidence_refs)
        return MetabolismEvaluation(
            memory_ref=snapshot.memory_ref,
            lifecycle_state=snapshot.lifecycle_state,
            evaluated_at_ms=snapshot.evaluated_at_ms,
            elapsed_since_meaningful_use_ms=elapsed,
            decay_weight=decay_weight,
            reinforcement=reinforcement,
            disposition=disposition,
            disposition_reasons=reasons,
            prune_threshold_used=threshold,
            crystallization_candidate=(
                reinforcement.effective_saturation
                >= self.config.crystallization_candidate_saturation
            ),
            evidence_refs=_unique(evidence_refs),
            scope_refs=snapshot.scope_refs,
            estimator_ref=ESTIMATOR_REF,
            profile_version=PROFILE_VERSION,
            config_digest=self.config.config_digest,
        )

    def evaluate_batch(self, snapshots: Iterable[MetabolismSnapshot]) -> MetabolismBatchEvidence:
        ordered = sorted(tuple(snapshots), key=lambda snapshot: snapshot.memory_ref)
        refs = [snapshot.memory_ref for snapshot in ordered]
        if len(refs) != len(set(refs)):
            raise MetabolismValidationError("batch contains duplicate memory_ref values")
        evaluations = tuple(self.evaluate(snapshot) for snapshot in ordered)
        return MetabolismBatchEvidence(
            evaluations=evaluations,
            estimator_ref=ESTIMATOR_REF,
            profile_version=PROFILE_VERSION,
            config_digest=self.config.config_digest,
        )

    def reinforcement(self, snapshot: MetabolismSnapshot) -> ReinforcementEvidence:
        by_kind: dict[str, int] = {kind: 0 for kind in REINFORCEMENT_KINDS}
        for observation in snapshot.reinforcement_observations:
            by_kind[observation.kind] += observation.count

        contributions: list[tuple[str, float]] = []
        total_pressure = 0.0
        for kind in sorted(REINFORCEMENT_KINDS):
            count = by_kind[kind]
            if count <= 0:
                continue
            raw = 1.0 - math.exp(-self.config.weight_for(kind) * count)
            if kind == ACCESS:
                raw = min(raw, self.config.max_access_contribution)
            contribution = min(1.0, raw)
            contributions.append((kind, contribution))
            total_pressure += contribution
        total_pressure = min(1.0, total_pressure)

        baseline = _unit_interval("baseline_saturation", snapshot.baseline_saturation)
        reinforced = 1.0 - (1.0 - baseline) * math.exp(-total_pressure)
        contradiction = _unit_interval("contradiction_pressure", snapshot.contradiction_pressure)
        effective = reinforced * (1.0 - contradiction)
        return ReinforcementEvidence(
            contributions=tuple(contributions),
            total_pressure=total_pressure,
            saturation_before=baseline,
            saturation_after_reinforcement=reinforced,
            contradiction_pressure=contradiction,
            effective_saturation=max(0.0, min(1.0, effective)),
        )

    def decay_weight(self, *, elapsed_ms: int, effective_saturation: float) -> float:
        if elapsed_ms <= 0:
            return 1.0
        saturation = _unit_interval("effective_saturation", effective_saturation)
        base_lambda = math.log(2.0) / self.config.half_life_ms
        context_temperature = (1.0 - saturation) * math.log(2.0)
        effective_lambda = base_lambda * context_temperature
        return max(0.0, min(1.0, math.exp(-effective_lambda * elapsed_ms)))

    def _disposition(
        self,
        snapshot: MetabolismSnapshot,
        *,
        decay_weight: float,
        effective_saturation: float,
    ) -> tuple[str, tuple[str, ...], float]:
        threshold = (
            self.config.prune_exit_weight
            if snapshot.prior_prune_candidate
            else self.config.prune_enter_weight
        )
        constraints = snapshot.constraints
        if constraints.mandatory_deletion:
            return (
                MANDATORY_DELETION_REVIEW,
                ("mandatory_deletion_requires_governed_consequence",),
                threshold,
            )

        blockers = constraints.ordinary_prune_blockers()
        if blockers:
            return RETENTION_HOLD, blockers, threshold

        if snapshot.lifecycle_state in {"Disputed", "Pending Verification", "PendingVerification"}:
            return REQUIRE_REVIEW, ("lifecycle_state_requires_review",), threshold

        if (
            decay_weight < threshold
            and effective_saturation < self.config.crystallization_candidate_saturation
        ):
            return PRUNE_CANDIDATE, ("decay_below_prune_threshold",), threshold
        if decay_weight < self.config.archive_weight:
            return ARCHIVE_CANDIDATE, ("decay_below_archive_threshold",), threshold
        return KEEP_ACTIVE, ("retention_pressure_sufficient",), threshold


def propose_consolidation(
    sources: Iterable[ConsolidationSource],
    *,
    method_ref: str,
    method_version: str,
) -> ConsolidationProposal:
    """Build a deterministic derived-state proposal from explicit sources.

    The first profile requires identical scope sets across sources.  This is
    intentionally conservative: computing a broader common ancestor scope from
    mixed project inputs could launder scope.  A future governed narrowing
    contract may relax this only with explicit evidence and authority.
    """

    ordered = tuple(sorted(tuple(sources), key=lambda source: (source.memory_ref, source.fact_ref)))
    if not ordered:
        raise MetabolismValidationError("consolidation requires at least one source")
    if not method_ref or not method_version:
        raise MetabolismValidationError("consolidation method identity/version are required")

    source_memory_refs = tuple(source.memory_ref for source in ordered)
    if len(source_memory_refs) != len(set(source_memory_refs)):
        raise MetabolismValidationError("consolidation source memory refs must be unique")
    source_fact_refs = tuple(source.fact_ref for source in ordered)
    target_scope_refs = ordered[0].scope_refs
    reasons: list[str] = []
    if any(source.scope_refs != target_scope_refs for source in ordered[1:]):
        reasons.append("scope_mismatch")
    if any(source.currentness != "current" for source in ordered):
        reasons.append("non_current_source")
    if any(source.disputed for source in ordered):
        reasons.append("disputed_source")

    evidence_refs: list[str] = []
    exception_refs: list[str] = []
    for source in ordered:
        evidence_refs.extend(source.evidence_refs)
        exception_refs.extend(source.exception_refs)
    body = {
        "source_memory_refs": source_memory_refs,
        "source_fact_refs": source_fact_refs,
        "target_scope_refs": target_scope_refs,
        "evidence_refs": _unique(evidence_refs),
        "exception_refs": _unique(exception_refs),
        "method_ref": method_ref,
        "method_version": method_version,
        "eligible": not reasons,
        "reasons": tuple(reasons),
        "derived_posture": "proposed_derived",
        "certification_status": "not_established",
        "authority_effect": "none",
    }
    proposal_ref = f"consolidation-proposal:{_sha256_ref(body)}"
    return ConsolidationProposal(proposal_ref=proposal_ref, **body)
