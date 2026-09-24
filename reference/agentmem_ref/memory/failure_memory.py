"""Native governed negative/failure memory for Agent Memory.

Issue #471 harvests useful failure-memory mechanisms from first-party ancestry
without importing the unsafe authority shortcut that similarity, severity, or
recurrence may directly block an action.

The runtime keeps three boundaries explicit:

    failure observation / revision
        -> typed failure memory + recurrence evidence
        -> Cognitive Mesh proposal
        -> existing PAMA-governed durable consequence

    recall / similarity / recurrence
        -> candidate evidence only
        -> existing recall admission and downstream action authority

    evidence != authority

The generic ``FailureMemory`` revision owner is process-local. Bounded restart
support is provided by ``CheckpointedFailureMemory`` in ``failure_checkpoint``
when an explicit restart-safe host composes that owner state with the durable
Agent Memory substrate. Neither form gives failure evidence authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json

from ..core import policy
from ..runtime.adapter import CommitResult, GovernedMemoryAdapter, RecallContext
from ..core.contextual_recall import (
    ADMITTING_OUTCOMES,
    DeterministicContextualRecallPolicy,
)
from .cognitive_mesh import (
    ActiveCognition,
    CognitiveExperience,
    CognitiveMeshRuntime,
    CognitiveSignal,
    MeshObject,
)


FAILURE_COMPONENT_ID = "agent-memory-failure-memory-reference"
CAPABILITY_ID = "negative_failure_memory"
CAUSAL_STATUSES = frozenset({"observed", "inferred", "hypothesis"})
MEMORY_STATUSES = frozenset({"active", "disputed", "retracted"})


class FailureMemoryError(ValueError):
    """Base error for an invalid failure-memory operation."""


class StaleFailureRevision(FailureMemoryError):
    """A revision did not extend the current append-only lineage."""


class RetractedFailureError(FailureMemoryError):
    """A retracted failure memory requires an explicit future readmission path."""


def derive_failure_ref(
    *,
    scope: str,
    action_class: str,
    category: str,
    identity_basis: str,
) -> str:
    """Derive a stable logical identity from caller-declared identity inputs.

    The caller supplies ``identity_basis`` specifically so mutable prose such as
    an exception message or generated explanation does not silently become the
    identity contract. Similar but materially different failures should use a
    different identity basis.
    """
    if not scope or not action_class or not category or not identity_basis:
        raise FailureMemoryError(
            "scope, action_class, category, and identity_basis are required"
        )
    payload = json.dumps(
        {
            "action_class": action_class,
            "category": category,
            "identity_basis": identity_basis,
            "scope": scope,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"failure:sha256:{hashlib.sha256(payload).hexdigest()}"


@dataclass(frozen=True)
class FailureScope:
    """Governed scope carried by every revision of one failure memory."""

    scope: str
    isolation_domain_refs: tuple[str, ...] = ()
    required_isolation_domain_refs: tuple[str, ...] = ()
    project_ref: str = ""
    task_ref: str = ""
    purpose: str = "failure_recurrence_prevention"

    def __post_init__(self) -> None:
        if not self.scope:
            raise FailureMemoryError("failure scope is required")
        required = set(self.required_isolation_domain_refs)
        bound = set(self.isolation_domain_refs)
        if required and not required.issubset(bound):
            raise FailureMemoryError(
                "required isolation domains must be present in isolation_domain_refs"
            )


@dataclass(frozen=True)
class FailureRevision:
    """One immutable revision of a negative/failure memory.

    ``similarity_score`` and ``impact_score`` are estimator/evaluation evidence.
    Neither field grants recall admission, mutation authority, action authority,
    truth, permanence, or certification.
    """

    failure_ref: str
    revision_ref: str
    action_class: str
    summary: str
    category: str
    causal_status: str
    scope: FailureScope
    source_component: str
    observed_at: str
    expected_outcome: str = ""
    actual_outcome: str = ""
    severity_label: str = "unspecified"
    impact_score: float | None = None
    root_cause_candidates: tuple[str, ...] = ()
    mitigation: str = ""
    verification_evidence_refs: tuple[str, ...] = ()
    applicability_conditions: tuple[str, ...] = ()
    source_evidence_refs: tuple[str, ...] = ()
    recurrence_evidence_refs: tuple[str, ...] = ()
    similarity_score: float | None = None
    prior_revision_ref: str = ""
    revision_reason: str = ""
    memory_status: str = "active"
    estimator_ref: str = ""
    estimator_version: str = ""

    def __post_init__(self) -> None:
        for name, value in (
            ("failure_ref", self.failure_ref),
            ("revision_ref", self.revision_ref),
            ("action_class", self.action_class),
            ("category", self.category),
            ("source_component", self.source_component),
            ("observed_at", self.observed_at),
        ):
            if not value:
                raise FailureMemoryError(f"{name} is required")
        if self.causal_status not in CAUSAL_STATUSES:
            raise FailureMemoryError(
                f"unsupported causal_status: {self.causal_status}"
            )
        if self.memory_status not in MEMORY_STATUSES:
            raise FailureMemoryError(
                f"unsupported memory_status: {self.memory_status}"
            )
        if self.memory_status == "retracted":
            if self.summary:
                raise FailureMemoryError(
                    "retracted failure revision must not carry replacement summary"
                )
        elif not self.summary:
            raise FailureMemoryError(
                "active/disputed failure revision requires summary"
            )
        for name, value in (
            ("impact_score", self.impact_score),
            ("similarity_score", self.similarity_score),
        ):
            if value is not None and not 0.0 <= value <= 1.0:
                raise FailureMemoryError(f"{name} must be between 0 and 1")
        if self.prior_revision_ref and not self.revision_reason:
            raise FailureMemoryError(
                "non-initial failure revision requires revision_reason"
            )
        for name, values in (
            ("root_cause_candidates", self.root_cause_candidates),
            ("verification_evidence_refs", self.verification_evidence_refs),
            ("applicability_conditions", self.applicability_conditions),
            ("source_evidence_refs", self.source_evidence_refs),
            ("recurrence_evidence_refs", self.recurrence_evidence_refs),
        ):
            if len(values) != len(set(values)):
                raise FailureMemoryError(f"{name} must not contain duplicates")

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                self.source_evidence_refs
                + self.verification_evidence_refs
                + self.recurrence_evidence_refs
            )
        )

    @property
    def occurrence_count(self) -> int:
        """Initial observed failure plus explicitly recorded recurrence evidence."""
        return 1 + len(self.recurrence_evidence_refs)

    def recall_text(self) -> str:
        fields = (
            self.action_class,
            self.summary,
            self.category,
            self.expected_outcome,
            self.actual_outcome,
            self.mitigation,
            *self.root_cause_candidates,
            *self.applicability_conditions,
        )
        return " | ".join(item for item in fields if item)


@dataclass(frozen=True)
class FailureRevisionResult:
    """Governed consequence of one attempted failure-memory revision."""

    revision: FailureRevision
    commit: CommitResult
    fact_uuid: str | None
    lineage_state: str


@dataclass(frozen=True)
class FailureMatchEvidence:
    """Non-authoritative recurrence/similarity evidence for a failure memory."""

    failure_ref: str
    similarity_score: float
    occurrence_count: int
    severity_label: str
    memory_status: str
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if not 0.0 <= self.similarity_score <= 1.0:
            raise FailureMemoryError("similarity_score must be between 0 and 1")
        if self.occurrence_count < 1:
            raise FailureMemoryError("occurrence_count must be at least 1")
        if self.authority_effect != "none":
            raise FailureMemoryError(
                "failure match evidence cannot have authority effect"
            )


@dataclass
class FailureMemory:
    """Process-local revision owner for native governed failure memory."""

    adapter: GovernedMemoryAdapter
    available_components: tuple[str, ...]
    recall_policy: DeterministicContextualRecallPolicy | None = None
    _mesh: CognitiveMeshRuntime = field(init=False, repr=False)
    _history: dict[str, list[FailureRevision]] = field(
        default_factory=dict, init=False, repr=False
    )
    _fact_by_revision: dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.available_components = tuple(dict.fromkeys(self.available_components))
        self._mesh = CognitiveMeshRuntime(
            adapter=self.adapter,
            available_components=self.available_components,
            recall_policy=self.recall_policy,
        )

    def apply_revision(
        self,
        revision: FailureRevision,
        *,
        actor_id: str,
        target_class: str = policy.M2,
        downstream_authority: str = policy.A1,
        risk_class: str = "low",
        review_satisfied: bool = False,
        approval_refs: tuple[str, ...] = (),
        evidence=None,
        attestation=None,
    ) -> FailureRevisionResult:
        """Retain or revise failure memory through Cognitive Mesh and PAMA."""
        if revision.memory_status == "retracted":
            return self.retract(
                revision,
                actor_id=actor_id,
                target_class=target_class,
                downstream_authority=downstream_authority,
                risk_class=risk_class,
                review_satisfied=review_satisfied,
                approval_refs=approval_refs,
                evidence=evidence,
            )

        current = self.current(revision.failure_ref)
        self._ensure_new_revision_ref(revision)
        self._validate_lineage(revision, current)
        if current is not None and current.memory_status == "retracted":
            raise RetractedFailureError(
                "retracted failure memory requires an explicit readmission path"
            )

        operation = "promotion" if current is None else "correction"
        current_strength = "observed"
        if current is not None:
            current_strength = (
                "tentative" if current.memory_status == "disputed" else "promoted"
            )
        proposed_strength = (
            "tentative" if revision.memory_status == "disputed" else "promoted"
        )

        experience = CognitiveExperience(
            experience_ref=revision.revision_ref,
            content=revision.recall_text(),
            source_description=(
                f"failure-memory {revision.category} revision "
                f"from {revision.source_component}"
            ),
            observed_at=revision.observed_at,
        )
        cognitive_object = MeshObject(
            object_ref=revision.failure_ref,
            object_type=CAPABILITY_ID,
            scope=revision.scope.scope,
            evidence_refs=revision.evidence_refs,
            isolation_domain_refs=revision.scope.isolation_domain_refs,
            required_isolation_domain_refs=(
                revision.scope.required_isolation_domain_refs
            ),
            project_ref=revision.scope.project_ref,
            task_ref=revision.scope.task_ref,
            purpose=revision.scope.purpose,
        )
        signal = CognitiveSignal(
            module_role="negative_failure_memory",
            source_component=revision.source_component,
            signal_type="failure_memory_revision",
            evidence_refs=revision.evidence_refs,
            estimator_ref=revision.estimator_ref,
            estimator_version=revision.estimator_version,
            confidence=revision.similarity_score,
            provider_verdict="",
        )
        transition = self._mesh.apply_signal(
            experience=experience,
            cognitive_object=cognitive_object,
            signal=signal,
            actor_id=actor_id,
            requested_operation=operation,
            target_class=target_class,
            downstream_authority=downstream_authority,
            risk_class=risk_class,
            current_strength=current_strength,
            proposed_strength=proposed_strength,
            charter_version="failure-memory-ref-v1",
            proposal_id=f"proposal:{revision.revision_ref}",
            review_satisfied=review_satisfied,
            approval_refs=approval_refs,
            evidence=evidence,
            attestation=attestation,
        )

        if transition.commit.committed:
            self._history.setdefault(revision.failure_ref, []).append(revision)
            if transition.commit.fact_uuid is None:
                raise RuntimeError("committed failure revision requires fact_uuid")
            self._fact_by_revision[revision.revision_ref] = transition.commit.fact_uuid

        return FailureRevisionResult(
            revision=revision,
            commit=transition.commit,
            fact_uuid=transition.commit.fact_uuid,
            lineage_state=(
                self.revision_state(revision.failure_ref, revision.revision_ref)
                if transition.commit.committed
                else "refused"
            ),
        )

    def record_recurrence(
        self,
        failure_ref: str,
        *,
        revision_ref: str,
        recurrence_evidence_ref: str,
        observed_at: str,
        actor_id: str,
        similarity_score: float | None = None,
        review_satisfied: bool = False,
        approval_refs: tuple[str, ...] = (),
        evidence=None,
    ) -> FailureRevisionResult:
        """Append one explicit recurrence observation as a governed revision.

        Reading or recalling a failure memory never calls this method and cannot
        increase recurrence evidence.
        """
        if not recurrence_evidence_ref:
            raise FailureMemoryError("recurrence_evidence_ref is required")
        current = self.current(failure_ref)
        if current is None:
            raise FailureMemoryError("cannot recur an unknown failure memory")
        if current.memory_status == "retracted":
            raise RetractedFailureError("cannot recur a retracted failure memory")
        if recurrence_evidence_ref in current.recurrence_evidence_refs:
            raise FailureMemoryError(
                "recurrence evidence has already been recorded for this failure"
            )
        revised = replace(
            current,
            revision_ref=revision_ref,
            observed_at=observed_at,
            recurrence_evidence_refs=(
                current.recurrence_evidence_refs + (recurrence_evidence_ref,)
            ),
            similarity_score=similarity_score,
            prior_revision_ref=current.revision_ref,
            revision_reason="explicit recurrence observation",
        )
        return self.apply_revision(
            revised,
            actor_id=actor_id,
            review_satisfied=review_satisfied,
            approval_refs=approval_refs,
            evidence=evidence,
        )

    def retract(
        self,
        revision: FailureRevision,
        *,
        actor_id: str,
        target_class: str = policy.M2,
        downstream_authority: str = policy.A1,
        risk_class: str = "low",
        review_satisfied: bool = False,
        approval_refs: tuple[str, ...] = (),
        evidence=None,
    ) -> FailureRevisionResult:
        """Append a retraction while removing current failure influence."""
        if revision.memory_status != "retracted":
            raise FailureMemoryError("retract() requires memory_status='retracted'")
        current = self.current(revision.failure_ref)
        self._ensure_new_revision_ref(revision)
        if current is None:
            raise FailureMemoryError("cannot retract an unknown failure memory")
        self._validate_lineage(revision, current)
        if current.memory_status == "retracted":
            raise RetractedFailureError("failure memory is already retracted")

        current_fact_uuid = self.adapter.current_fact_uuid(revision.failure_ref)
        if current_fact_uuid is None:
            raise FailureMemoryError(
                "current failure memory has no governed recall fact to retract"
            )
        evidence_refs = tuple(
            dict.fromkeys(revision.evidence_refs + (revision.prior_revision_ref,))
        )
        proposal = policy.Proposal(
            proposal_id=f"proposal:{revision.revision_ref}",
            actor_id=actor_id,
            charter_version="failure-memory-ref-v1",
            target_reference=revision.failure_ref,
            target_class=target_class,
            scope=revision.scope.scope,
            operation="pruning",
            current_strength=(
                "tentative"
                if current.memory_status == "disputed"
                else "promoted"
            ),
            proposed_strength="archived",
            downstream_authority=downstream_authority,
            reversibility="reversible",
            risk_class=risk_class,
            evidence_refs=evidence_refs,
            estimator_refs=(
                (revision.estimator_ref,) if revision.estimator_ref else ()
            ),
            estimator_versions=(
                (revision.estimator_version,) if revision.estimator_version else ()
            ),
            confidence=revision.similarity_score,
            review_satisfied=review_satisfied,
            approval_refs=approval_refs,
            purpose=revision.scope.purpose,
            isolation_domain_refs=revision.scope.isolation_domain_refs,
            required_isolation_domain_refs=(
                revision.scope.required_isolation_domain_refs
            ),
            project_ref=revision.scope.project_ref,
            task_ref=revision.scope.task_ref,
        )
        commit = self.adapter.governed_delete(
            proposal,
            current_fact_uuid,
            evidence=evidence,
        )
        if commit.committed:
            self._history.setdefault(revision.failure_ref, []).append(revision)

        return FailureRevisionResult(
            revision=revision,
            commit=commit,
            fact_uuid=current_fact_uuid if commit.committed else None,
            lineage_state=(
                self.revision_state(revision.failure_ref, revision.revision_ref)
                if commit.committed
                else "refused"
            ),
        )

    def current(self, failure_ref: str) -> FailureRevision | None:
        history = self._history.get(failure_ref, ())
        return history[-1] if history else None

    def history(self, failure_ref: str) -> tuple[FailureRevision, ...]:
        return tuple(self._history.get(failure_ref, ()))

    def occurrence_count(self, failure_ref: str) -> int:
        current = self.current(failure_ref)
        if current is None:
            return 0
        return current.occurrence_count

    def revision_state(self, failure_ref: str, revision_ref: str) -> str:
        history = self._history.get(failure_ref, ())
        matches = [item for item in history if item.revision_ref == revision_ref]
        if not matches:
            raise KeyError(revision_ref)
        current = history[-1]
        if current.revision_ref != revision_ref:
            return "superseded"
        if current.memory_status == "disputed":
            return "disputed"
        if current.memory_status == "retracted":
            return "retracted"
        return "current"

    def fact_uuid(self, revision_ref: str) -> str | None:
        return self._fact_by_revision.get(revision_ref)

    def match_evidence(
        self,
        failure_ref: str,
        *,
        similarity_score: float,
    ) -> FailureMatchEvidence:
        current = self.current(failure_ref)
        if current is None:
            raise FailureMemoryError("unknown failure memory")
        return FailureMatchEvidence(
            failure_ref=failure_ref,
            similarity_score=similarity_score,
            occurrence_count=current.occurrence_count,
            severity_label=current.severity_label,
            memory_status=current.memory_status,
        )

    def recall_active(
        self,
        query: str,
        *,
        context: RecallContext,
    ) -> ActiveCognition:
        """Recall only current failure-owned facts after normal governed admission.

        Candidate generation and adapter admission remain shared. This specialized
        surface may only narrow that admitted set. A fact that the failure-memory
        owner does not recognize fails closed as a type mismatch rather than
        inheriting the generic Cognitive Mesh fact-UUID fallback.
        """
        admission = self.adapter.governed_recall(query, context=context)
        result = ActiveCognition(
            candidate_fact_uuids=list(admission.candidates),
            admitted_fact_uuids=list(admission.admitted),
            refusals=dict(admission.refusals),
        )
        recall_policy = self.recall_policy or DeterministicContextualRecallPolicy(
            policy_ref="policy:cognitive-mesh-recall",
            policy_version="1.0.0",
        )
        for fact_uuid in admission.admitted:
            failure_ref = self._failure_ref_for_fact(fact_uuid)
            if failure_ref is None:
                result.refusals.setdefault(
                    fact_uuid,
                    "memory_type_mismatch:negative_failure_memory",
                )
                continue

            decision = recall_policy.evaluate(
                failure_ref,
                context,
                evaluated_at="2026-01-01T00:10:00Z",
            )
            result.contextual_decisions[failure_ref] = decision
            if decision["outcome"] not in ADMITTING_OUTCOMES:
                result.refusals[fact_uuid] = f"contextual_{decision['outcome']}"
                continue

            current = self.current(failure_ref)
            if current is None:
                result.refusals[fact_uuid] = "failure_state_missing"
                continue
            if current.memory_status == "disputed":
                result.refusals[fact_uuid] = "failure_disputed"
                continue
            if current.memory_status == "retracted":
                result.refusals[fact_uuid] = "failure_retracted"
                continue
            if self._fact_by_revision.get(current.revision_ref) != fact_uuid:
                result.refusals[fact_uuid] = "failure_not_current_revision"
                continue
            result.active_object_refs.append(failure_ref)
        return result

    def replace_component(self, *, old_component: str, new_component: str) -> None:
        self.available_components = tuple(
            new_component if item == old_component else item
            for item in self.available_components
        )
        self.available_components = tuple(dict.fromkeys(self.available_components))
        self._mesh.replace_component(
            old_component=old_component,
            new_component=new_component,
        )

    def _failure_ref_for_fact(self, fact_uuid: str) -> str | None:
        for failure_ref, revisions in self._history.items():
            for revision in revisions:
                if self._fact_by_revision.get(revision.revision_ref) == fact_uuid:
                    return failure_ref
        return None

    def _ensure_new_revision_ref(self, revision: FailureRevision) -> None:
        if revision.revision_ref in self._fact_by_revision:
            raise FailureMemoryError(
                f"failure revision already committed: {revision.revision_ref}"
            )
        for revisions in self._history.values():
            if any(item.revision_ref == revision.revision_ref for item in revisions):
                raise FailureMemoryError(
                    f"failure revision already exists: {revision.revision_ref}"
                )

    @staticmethod
    def _validate_lineage(
        revision: FailureRevision,
        current: FailureRevision | None,
    ) -> None:
        if current is None:
            if revision.prior_revision_ref:
                raise StaleFailureRevision(
                    "initial failure revision must not name a prior revision"
                )
            return
        if revision.prior_revision_ref != current.revision_ref:
            raise StaleFailureRevision(
                "failure revision must extend the current revision"
            )
        if revision.scope != current.scope:
            raise FailureMemoryError(
                "failure revision cannot silently change governed scope"
            )
        if revision.action_class != current.action_class:
            raise FailureMemoryError(
                "failure revision cannot silently change action_class identity"
            )
