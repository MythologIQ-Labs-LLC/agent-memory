"""Governed epistemic belief memory and the first RC1 multi-memory composition.

The bounded epistemic runtime retains claims, beliefs, and hypotheses as
explicit epistemic state. Confidence and estimator output remain evidence; they
never become truth or authority.

The RC1 specialization in this module adds an owner checkpoint contract and
composes epistemic state with canonical semantic memory through the existing
restart-safe runtime. The composition deliberately keeps the memory forms
separate:

    shared experience / provenance
        -> semantic consequence
        -> epistemic consequence

    same runtime != same memory type
    shared provenance != duplicated truth
    confidence != authority

The two consequences are governed independently. A refusal on one path never
fabricates rollback of a consequence that already committed on the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from ..core import policy
from ..core.contextual_recall import (
    ADMITTING_OUTCOMES,
    DeterministicContextualRecallPolicy,
)
from ..runtime.adapter import CommitResult, GovernedMemoryAdapter, RecallContext
from ..runtime.auxiliary_checkpoint import ComposedRestartSafeRuntime
from ..runtime.restart_runtime import RuntimeProfile, RuntimeRecoveryError
from .cognitive_mesh import (
    ActiveCognition,
    CognitiveExperience,
    CognitiveMeshRuntime,
    CognitiveSignal,
    MeshObject,
)

EPISTEMIC_COMPONENT_ID = "agent-memory-epistemic-reference"
CAPABILITY_ID = "epistemic_belief_memory"
EPISTEMIC_AUXILIARY_COMPONENT_ID = "epistemic_belief_memory"
EPISTEMIC_CHECKPOINT_SCHEMA_VERSION = "1.0.0"
EPISTEMIC_CHECKPOINT_OWNER = "epistemic_belief_memory"

EPISTEMIC_KINDS = frozenset({"claim", "belief", "hypothesis"})
EPISTEMIC_STATUSES = frozenset({"active", "disputed", "retracted"})


class EpistemicRevisionError(ValueError):
    """Base error for an invalid epistemic revision."""


class StaleEpistemicRevision(EpistemicRevisionError):
    """A revision did not extend the current append-only lineage."""


class RetractedBeliefError(EpistemicRevisionError):
    """A retracted belief requires an explicit future readmission path."""


@dataclass(frozen=True)
class EpistemicScope:
    """Governed scope carried by every revision of one belief."""

    scope: str
    isolation_domain_refs: tuple[str, ...] = ()
    required_isolation_domain_refs: tuple[str, ...] = ()
    project_ref: str = ""
    task_ref: str = ""
    purpose: str = "reasoning"

    def __post_init__(self) -> None:
        if not self.scope:
            raise EpistemicRevisionError("epistemic scope is required")
        required = set(self.required_isolation_domain_refs)
        bound = set(self.isolation_domain_refs)
        if required and not required.issubset(bound):
            raise EpistemicRevisionError(
                "required isolation domains must be present in isolation_domain_refs"
            )


@dataclass(frozen=True)
class BeliefRevision:
    """One immutable epistemic revision.

    ``epistemic_kind`` describes the retained epistemic object, not truth.
    ``epistemic_status`` is the status of this revision when it becomes current.
    Historical current/superseded posture is computed from append-only lineage.
    """

    belief_ref: str
    revision_ref: str
    epistemic_kind: str
    claim_text: str
    confidence: float | None
    scope: EpistemicScope
    source_component: str
    observed_at: str
    supporting_evidence_refs: tuple[str, ...] = ()
    contradicting_evidence_refs: tuple[str, ...] = ()
    revision_reason: str = ""
    prior_revision_ref: str = ""
    epistemic_status: str = "active"
    estimator_ref: str = ""
    estimator_version: str = ""

    def __post_init__(self) -> None:
        if not self.belief_ref or not self.revision_ref:
            raise EpistemicRevisionError("belief_ref and revision_ref are required")
        if self.epistemic_kind not in EPISTEMIC_KINDS:
            raise EpistemicRevisionError(
                f"unsupported epistemic_kind: {self.epistemic_kind}"
            )
        if self.epistemic_status not in EPISTEMIC_STATUSES:
            raise EpistemicRevisionError(
                f"unsupported epistemic_status: {self.epistemic_status}"
            )
        if not self.source_component or not self.observed_at:
            raise EpistemicRevisionError(
                "source_component and observed_at are required"
            )
        if self.epistemic_status == "retracted":
            if self.claim_text:
                raise EpistemicRevisionError(
                    "retracted revision must not carry replacement claim_text"
                )
        elif not self.claim_text:
            raise EpistemicRevisionError(
                "active/disputed epistemic revision requires claim_text"
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise EpistemicRevisionError("confidence must be between 0 and 1")
        if self.prior_revision_ref and not self.revision_reason:
            raise EpistemicRevisionError(
                "non-initial revision requires revision_reason"
            )
        for name, refs in (
            ("supporting_evidence_refs", self.supporting_evidence_refs),
            ("contradicting_evidence_refs", self.contradicting_evidence_refs),
        ):
            if len(set(refs)) != len(refs):
                raise EpistemicRevisionError(f"{name} must not contain duplicates")

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        """Directional evidence flattened only for the generic PAMA evidence list."""
        return tuple(
            dict.fromkeys(
                self.supporting_evidence_refs + self.contradicting_evidence_refs
            )
        )


@dataclass(frozen=True)
class EpistemicRevisionResult:
    """Governed consequence of one attempted epistemic revision."""

    revision: BeliefRevision
    commit: CommitResult
    fact_uuid: str | None
    lineage_state: str


@dataclass
class EpistemicBeliefMemory:
    """Reference runtime for governed epistemic belief state.

    By itself this class is process-local, matching the existing v3 capability
    profile. ``CheckpointedEpistemicBeliefMemory`` below is the bounded RC1
    durability specialization used only when a restart-safe host explicitly
    composes it.
    """

    adapter: GovernedMemoryAdapter
    available_components: tuple[str, ...]
    recall_policy: DeterministicContextualRecallPolicy | None = None
    _mesh: CognitiveMeshRuntime = field(init=False, repr=False)
    _history: dict[str, list[BeliefRevision]] = field(
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
        revision: BeliefRevision,
        *,
        actor_id: str,
        target_class: str = policy.M2,
        downstream_authority: str = policy.A1,
        risk_class: str = "low",
        review_satisfied: bool = False,
        approval_refs: tuple[str, ...] = (),
        evidence=None,
        attestation=None,
    ) -> EpistemicRevisionResult:
        """Retain or revise a belief through Cognitive Mesh and PAMA.

        A refused proposal is returned to the caller but is never appended to
        current/history state. Confidence is carried as estimator evidence only.
        """
        if revision.epistemic_status == "retracted":
            return self.retract(
                revision,
                actor_id=actor_id,
                target_class=target_class,
                downstream_authority=downstream_authority,
                risk_class=risk_class,
                review_satisfied=review_satisfied,
                approval_refs=approval_refs,
                evidence=evidence,
                attestation=attestation,
            )

        current = self.current(revision.belief_ref)
        self._ensure_new_revision_ref(revision)
        self._validate_lineage(revision, current)
        if current is not None and current.epistemic_status == "retracted":
            raise RetractedBeliefError(
                "retracted belief requires an explicit readmission path"
            )

        operation = "promotion" if current is None else "correction"
        experience = CognitiveExperience(
            experience_ref=revision.revision_ref,
            content=revision.claim_text,
            source_description=(
                f"epistemic {revision.epistemic_kind} revision "
                f"from {revision.source_component}"
            ),
            observed_at=revision.observed_at,
        )
        cognitive_object = MeshObject(
            object_ref=revision.belief_ref,
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
            module_role="epistemic_memory",
            source_component=revision.source_component,
            signal_type="epistemic_revision",
            evidence_refs=revision.evidence_refs,
            estimator_ref=revision.estimator_ref,
            estimator_version=revision.estimator_version,
            confidence=revision.confidence,
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
            current_strength=(
                "observed"
                if current is None
                else (
                    "tentative"
                    if current.epistemic_status == "disputed"
                    else "promoted"
                )
            ),
            proposed_strength=(
                "tentative"
                if revision.epistemic_status == "disputed"
                else "promoted"
            ),
            charter_version="epistemic-belief-memory-ref-v1",
            proposal_id=f"proposal:{revision.revision_ref}",
            review_satisfied=review_satisfied,
            approval_refs=approval_refs,
            evidence=evidence,
            attestation=attestation,
        )

        if transition.commit.committed:
            self._history.setdefault(revision.belief_ref, []).append(revision)
            if transition.commit.fact_uuid is None:
                raise RuntimeError("committed epistemic revision requires fact_uuid")
            self._fact_by_revision[revision.revision_ref] = transition.commit.fact_uuid

        return EpistemicRevisionResult(
            revision=revision,
            commit=transition.commit,
            fact_uuid=transition.commit.fact_uuid,
            lineage_state=(
                self.revision_state(revision.belief_ref, revision.revision_ref)
                if transition.commit.committed
                else "refused"
            ),
        )

    def retract(
        self,
        revision: BeliefRevision,
        *,
        actor_id: str,
        target_class: str = policy.M2,
        downstream_authority: str = policy.A1,
        risk_class: str = "low",
        review_satisfied: bool = False,
        approval_refs: tuple[str, ...] = (),
        evidence=None,
        attestation=None,
    ) -> EpistemicRevisionResult:
        """Append a retraction while pruning the current claim from active recall."""
        if revision.epistemic_status != "retracted":
            raise EpistemicRevisionError(
                "retract() requires epistemic_status='retracted'"
            )
        current = self.current(revision.belief_ref)
        self._ensure_new_revision_ref(revision)
        if current is None:
            raise EpistemicRevisionError("cannot retract an unknown belief")
        self._validate_lineage(revision, current)
        if current.epistemic_status == "retracted":
            raise RetractedBeliefError("belief is already retracted")

        current_fact_uuid = self.adapter.current_fact_uuid(revision.belief_ref)
        if current_fact_uuid is None:
            raise EpistemicRevisionError(
                "current belief has no governed recall fact to retract"
            )

        evidence_refs = tuple(
            dict.fromkeys(revision.evidence_refs + (revision.prior_revision_ref,))
        )
        proposal = policy.Proposal(
            proposal_id=f"proposal:{revision.revision_ref}",
            actor_id=actor_id,
            charter_version="epistemic-belief-memory-ref-v1",
            target_reference=revision.belief_ref,
            target_class=target_class,
            scope=revision.scope.scope,
            operation="pruning",
            current_strength=(
                "tentative"
                if current.epistemic_status == "disputed"
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
                (revision.estimator_version,)
                if revision.estimator_version
                else ()
            ),
            confidence=revision.confidence,
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
            self._history.setdefault(revision.belief_ref, []).append(revision)

        return EpistemicRevisionResult(
            revision=revision,
            commit=commit,
            fact_uuid=current_fact_uuid if commit.committed else None,
            lineage_state=(
                self.revision_state(revision.belief_ref, revision.revision_ref)
                if commit.committed
                else "refused"
            ),
        )

    def current(self, belief_ref: str) -> BeliefRevision | None:
        history = self._history.get(belief_ref, ())
        return history[-1] if history else None

    def current_claim(self, belief_ref: str) -> str | None:
        current = self.current(belief_ref)
        if current is None or current.epistemic_status == "retracted":
            return None
        return current.claim_text

    def history(self, belief_ref: str) -> tuple[BeliefRevision, ...]:
        return tuple(self._history.get(belief_ref, ()))

    def revision_state(self, belief_ref: str, revision_ref: str) -> str:
        history = self._history.get(belief_ref, ())
        matches = [item for item in history if item.revision_ref == revision_ref]
        if not matches:
            raise KeyError(revision_ref)
        current = history[-1]
        if current.revision_ref != revision_ref:
            return "superseded"
        if current.epistemic_status == "disputed":
            return "disputed"
        if current.epistemic_status == "retracted":
            return "retracted"
        return "current"

    def fact_uuid(self, revision_ref: str) -> str | None:
        return self._fact_by_revision.get(revision_ref)

    def retained_fact_uuids(self) -> tuple[str, ...]:
        """Fact identities owned by this memory form, including superseded history."""
        return tuple(self._fact_by_revision.values())

    def _belief_ref_for_fact(self, fact_uuid: str) -> str | None:
        for belief_ref, revisions in self._history.items():
            for revision in revisions:
                if self._fact_by_revision.get(revision.revision_ref) == fact_uuid:
                    return belief_ref
        return None

    def recall_active(
        self,
        query: str,
        *,
        context: RecallContext,
    ) -> ActiveCognition:
        """Recall epistemic memory without retyping other memory forms.

        Candidate generation remains shared at the adapter/substrate layer. This
        method may only narrow that already-governed result to facts owned by the
        epistemic memory form, then apply the contextual recall policy to the
        stable belief identity. It never admits a candidate the adapter refused.
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
            belief_ref = self._belief_ref_for_fact(fact_uuid)
            if belief_ref is None:
                result.refusals.setdefault(
                    fact_uuid, "memory_type_mismatch:epistemic_belief_memory"
                )
                continue
            decision = recall_policy.evaluate(
                belief_ref,
                context,
                evaluated_at="2026-01-01T00:10:00Z",
            )
            result.contextual_decisions[belief_ref] = decision
            if decision["outcome"] not in ADMITTING_OUTCOMES:
                result.refusals[fact_uuid] = f"contextual_{decision['outcome']}"
                continue
            current = self.current(belief_ref)
            if current is None:
                result.refusals[fact_uuid] = "epistemic_state_missing"
                continue
            if current.epistemic_status == "disputed":
                result.refusals[fact_uuid] = "epistemic_disputed"
                continue
            if current.epistemic_status == "retracted":
                result.refusals[fact_uuid] = "epistemic_retracted"
                continue
            if self._fact_by_revision.get(current.revision_ref) != fact_uuid:
                result.refusals[fact_uuid] = "epistemic_not_current_revision"
                continue
            result.active_object_refs.append(belief_ref)
        return result

    def replace_component(self, *, old_component: str, new_component: str) -> None:
        self._mesh.replace_component(
            old_component=old_component,
            new_component=new_component,
        )
        components = [item for item in self.available_components if item != old_component]
        if new_component not in components:
            components.append(new_component)
        self.available_components = tuple(components)

    def _ensure_new_revision_ref(self, revision: BeliefRevision) -> None:
        if any(
            item.revision_ref == revision.revision_ref
            for item in self._history.get(revision.belief_ref, ())
        ):
            raise EpistemicRevisionError(
                f"revision_ref already exists for belief: {revision.revision_ref}"
            )

    @staticmethod
    def _validate_lineage(
        revision: BeliefRevision,
        current: BeliefRevision | None,
    ) -> None:
        if current is None:
            if revision.prior_revision_ref:
                raise StaleEpistemicRevision(
                    "initial belief revision must not declare prior_revision_ref"
                )
            return
        if revision.prior_revision_ref != current.revision_ref:
            raise StaleEpistemicRevision(
                "revision must extend the current revision_ref"
            )
        if revision.scope != current.scope:
            raise EpistemicRevisionError(
                "belief revision cannot silently change governed scope"
            )


class CheckpointedEpistemicBeliefMemory(EpistemicBeliefMemory):
    """Restart-safe RC1 specialization with explicit owner checkpoint semantics."""

    def export_checkpoint_state(self) -> dict:
        if self.recall_policy is not None:
            raise ValueError(
                "checkpointed epistemic reference currently supports only the default recall policy"
            )
        return {
            "schema_version": EPISTEMIC_CHECKPOINT_SCHEMA_VERSION,
            "checkpoint_owner": EPISTEMIC_CHECKPOINT_OWNER,
            "available_components": list(self.available_components),
            "recall_policy_profile": "default_cognitive_mesh_v1",
            "history": {
                belief_ref: [_revision_checkpoint_row(item) for item in revisions]
                for belief_ref, revisions in sorted(self._history.items())
            },
            "fact_by_revision": dict(sorted(self._fact_by_revision.items())),
        }

    def restore_checkpoint_state(self, snapshot: Mapping[str, object]) -> None:
        if snapshot.get("schema_version") != EPISTEMIC_CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("unsupported epistemic checkpoint schema")
        if snapshot.get("checkpoint_owner") != EPISTEMIC_CHECKPOINT_OWNER:
            raise ValueError("epistemic checkpoint owner mismatch")
        if snapshot.get("recall_policy_profile") != "default_cognitive_mesh_v1":
            raise ValueError("epistemic checkpoint recall policy changed")
        if self.recall_policy is not None:
            raise ValueError(
                "checkpointed epistemic reference currently supports only the default recall policy"
            )

        raw_components = snapshot.get("available_components")
        raw_history = snapshot.get("history")
        raw_facts = snapshot.get("fact_by_revision")
        if not isinstance(raw_components, list):
            raise ValueError("epistemic checkpoint component set is malformed")
        if not isinstance(raw_history, Mapping) or not isinstance(raw_facts, Mapping):
            raise ValueError("epistemic checkpoint collections are malformed")

        components = tuple(str(item) for item in raw_components)
        if any(not item for item in components) or len(set(components)) != len(components):
            raise ValueError("epistemic checkpoint component set is invalid")
        if components != self.available_components:
            raise ValueError("epistemic checkpoint component interpretation changed")

        history: dict[str, list[BeliefRevision]] = {}
        revision_refs: set[str] = set()
        try:
            for belief_ref, raw_revisions in raw_history.items():
                if not isinstance(belief_ref, str) or not belief_ref:
                    raise ValueError("belief checkpoint key must be non-empty")
                if not isinstance(raw_revisions, list) or not raw_revisions:
                    raise ValueError("belief checkpoint history must be a non-empty list")
                revisions: list[BeliefRevision] = []
                current: BeliefRevision | None = None
                for raw in raw_revisions:
                    revision = _revision_from_checkpoint_row(raw)
                    if revision.belief_ref != belief_ref:
                        raise ValueError("belief checkpoint identity does not match its key")
                    if revision.revision_ref in revision_refs:
                        raise ValueError("duplicate epistemic revision identity")
                    self._validate_lineage(revision, current)
                    revision_refs.add(revision.revision_ref)
                    revisions.append(revision)
                    current = revision
                history[belief_ref] = revisions

            fact_by_revision: dict[str, str] = {}
            for revision_ref, fact_uuid in raw_facts.items():
                if not isinstance(revision_ref, str) or not revision_ref:
                    raise ValueError("epistemic fact binding revision must be non-empty")
                if not isinstance(fact_uuid, str) or not fact_uuid:
                    raise ValueError("epistemic fact binding uuid must be non-empty")
                fact_by_revision[revision_ref] = fact_uuid
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("epistemic checkpoint cannot be reconstructed") from exc

        expected_fact_refs = {
            revision.revision_ref
            for revisions in history.values()
            for revision in revisions
            if revision.epistemic_status != "retracted"
        }
        if set(fact_by_revision) != expected_fact_refs:
            raise ValueError("epistemic checkpoint fact bindings are incomplete or extraneous")
        if len(set(fact_by_revision.values())) != len(fact_by_revision):
            raise ValueError("epistemic checkpoint reuses a fact uuid across revisions")

        for belief_ref, revisions in history.items():
            current = revisions[-1]
            governed_current = self.adapter.current_fact_uuid(belief_ref)
            if current.epistemic_status == "retracted":
                if governed_current is not None:
                    raise ValueError(
                        "retracted epistemic checkpoint conflicts with governed currentness"
                    )
            else:
                expected_current = fact_by_revision[current.revision_ref]
                if governed_current != expected_current:
                    raise ValueError(
                        "epistemic checkpoint conflicts with governed current fact"
                    )

        self._history = history
        self._fact_by_revision = fact_by_revision


@dataclass(frozen=True)
class MultiMemoryExperienceResult:
    """Independent governed consequences bound to one source experience ref."""

    experience_ref: str
    semantic_commit: CommitResult
    epistemic_result: EpistemicRevisionResult

    @property
    def fully_retained(self) -> bool:
        return self.semantic_commit.committed and self.epistemic_result.commit.committed

    @property
    def partially_retained(self) -> bool:
        return self.semantic_commit.committed != self.epistemic_result.commit.committed


class SemanticEpistemicCompositionRuntime:
    """First RC1 runtime composing two materially different memory responsibilities."""

    def __init__(
        self,
        *,
        runtime: ComposedRestartSafeRuntime,
        available_components: tuple[str, ...],
    ) -> None:
        self.runtime = runtime
        self.adapter = runtime.adapter
        self.available_components = tuple(available_components)
        owner = runtime.auxiliary(EPISTEMIC_AUXILIARY_COMPONENT_ID)
        if not isinstance(owner, CheckpointedEpistemicBeliefMemory):
            raise RuntimeRecoveryError("epistemic auxiliary owner has unexpected type")
        self.epistemic = owner

    @staticmethod
    def _factories(available_components: tuple[str, ...]):
        components = tuple(dict.fromkeys(available_components))
        if not components:
            raise ValueError("at least one epistemic source component is required")

        def epistemic_factory(adapter: GovernedMemoryAdapter):
            return CheckpointedEpistemicBeliefMemory(
                adapter=adapter,
                available_components=components,
            )

        return {EPISTEMIC_AUXILIARY_COMPONENT_ID: epistemic_factory}

    @classmethod
    def create(
        cls,
        root,
        *,
        tenant: str,
        profile: RuntimeProfile,
        available_components: tuple[str, ...],
        verifier_registry=None,
    ) -> "SemanticEpistemicCompositionRuntime":
        components = tuple(dict.fromkeys(available_components))
        runtime = ComposedRestartSafeRuntime.create(
            root,
            tenant=tenant,
            profile=profile,
            auxiliary_factories=cls._factories(components),
            verifier_registry=verifier_registry,
        )
        return cls(runtime=runtime, available_components=components)

    @classmethod
    def recover(
        cls,
        root,
        *,
        profile: RuntimeProfile,
        available_components: tuple[str, ...],
        available_bindings=None,
        verifier_registry=None,
    ) -> "SemanticEpistemicCompositionRuntime":
        components = tuple(dict.fromkeys(available_components))
        runtime = ComposedRestartSafeRuntime.recover(
            root,
            profile=profile,
            auxiliary_factories=cls._factories(components),
            available_bindings=available_bindings,
            verifier_registry=verifier_registry,
        )
        return cls(runtime=runtime, available_components=components)

    def retain_semantic(self, proposal, fact_text: str, *, evidence=None, attestation=None):
        return self.runtime.commit_proposal(
            proposal,
            fact_text,
            evidence=evidence,
            attestation=attestation,
        )

    def apply_epistemic_revision(
        self,
        revision: BeliefRevision,
        *,
        actor_id: str,
        target_class: str = policy.M2,
        downstream_authority: str = policy.A1,
        risk_class: str = "low",
        review_satisfied: bool = False,
        approval_refs: tuple[str, ...] = (),
        evidence=None,
        attestation=None,
    ) -> EpistemicRevisionResult:
        result = self.epistemic.apply_revision(
            revision,
            actor_id=actor_id,
            target_class=target_class,
            downstream_authority=downstream_authority,
            risk_class=risk_class,
            review_satisfied=review_satisfied,
            approval_refs=approval_refs,
            evidence=evidence,
            attestation=attestation,
        )
        # A refused/parked operation may still change governance/audit state.
        # Checkpoint the complete runtime consequence, not only successful writes.
        self.runtime.checkpoint()
        return result

    def retain_experience(
        self,
        *,
        experience_ref: str,
        semantic_proposal,
        semantic_fact_text: str,
        epistemic_revision: BeliefRevision,
        actor_id: str,
        semantic_evidence=None,
        semantic_attestation=None,
        epistemic_evidence=None,
        epistemic_attestation=None,
        epistemic_review_satisfied: bool = False,
        epistemic_approval_refs: tuple[str, ...] = (),
    ) -> MultiMemoryExperienceResult:
        self._validate_shared_experience(
            experience_ref,
            semantic_proposal,
            epistemic_revision,
        )
        semantic = self.retain_semantic(
            semantic_proposal,
            semantic_fact_text,
            evidence=semantic_evidence,
            attestation=semantic_attestation,
        )
        epistemic = self.apply_epistemic_revision(
            epistemic_revision,
            actor_id=actor_id,
            review_satisfied=epistemic_review_satisfied,
            approval_refs=epistemic_approval_refs,
            evidence=epistemic_evidence,
            attestation=epistemic_attestation,
        )
        return MultiMemoryExperienceResult(
            experience_ref=experience_ref,
            semantic_commit=semantic,
            epistemic_result=epistemic,
        )

    def recall_semantic(self, query: str, context: RecallContext):
        """Governed semantic recall that never retypes epistemic facts as semantic."""
        result = self.adapter.governed_recall(query, context)
        epistemic_facts = set(self.epistemic.retained_fact_uuids())
        for fact_uuid in result.candidates:
            if fact_uuid not in epistemic_facts:
                continue
            if fact_uuid in result.admitted:
                result.admitted.remove(fact_uuid)
            result.refusals.setdefault(
                fact_uuid, "memory_type_mismatch:semantic_fact_memory"
            )
        return result

    def recall_epistemic(self, query: str, context: RecallContext) -> ActiveCognition:
        return self.epistemic.recall_active(query, context=context)

    def checkpoint(self):
        return self.runtime.checkpoint()

    @staticmethod
    def _validate_shared_experience(
        experience_ref: str,
        semantic_proposal,
        epistemic_revision: BeliefRevision,
    ) -> None:
        if not experience_ref:
            raise ValueError("shared experience_ref is required")
        if experience_ref not in tuple(semantic_proposal.evidence_refs):
            raise ValueError("semantic consequence is not bound to shared experience_ref")
        if experience_ref not in epistemic_revision.evidence_refs:
            raise ValueError("epistemic consequence is not bound to shared experience_ref")
        if semantic_proposal.target_reference == epistemic_revision.belief_ref:
            raise ValueError("different memory forms require distinct logical identities")

        scope = epistemic_revision.scope
        comparisons = (
            (semantic_proposal.scope, scope.scope, "scope"),
            (semantic_proposal.project_ref, scope.project_ref, "project_ref"),
            (semantic_proposal.task_ref, scope.task_ref, "task_ref"),
            (semantic_proposal.purpose, scope.purpose, "purpose"),
            (
                tuple(semantic_proposal.isolation_domain_refs),
                scope.isolation_domain_refs,
                "isolation_domain_refs",
            ),
            (
                tuple(semantic_proposal.required_isolation_domain_refs),
                scope.required_isolation_domain_refs,
                "required_isolation_domain_refs",
            ),
        )
        for left, right, name in comparisons:
            if left != right:
                raise ValueError(f"shared experience {name} mismatch")


def _scope_checkpoint_row(scope: EpistemicScope) -> dict:
    return {
        "scope": scope.scope,
        "isolation_domain_refs": list(scope.isolation_domain_refs),
        "required_isolation_domain_refs": list(scope.required_isolation_domain_refs),
        "project_ref": scope.project_ref,
        "task_ref": scope.task_ref,
        "purpose": scope.purpose,
    }


def _scope_from_checkpoint_row(raw) -> EpistemicScope:
    if not isinstance(raw, Mapping):
        raise TypeError("epistemic scope checkpoint row must be a mapping")
    return EpistemicScope(
        scope=str(raw["scope"]),
        isolation_domain_refs=tuple(str(item) for item in raw.get("isolation_domain_refs", ())),
        required_isolation_domain_refs=tuple(
            str(item) for item in raw.get("required_isolation_domain_refs", ())
        ),
        project_ref=str(raw.get("project_ref", "")),
        task_ref=str(raw.get("task_ref", "")),
        purpose=str(raw.get("purpose", "reasoning")),
    )


def _revision_checkpoint_row(revision: BeliefRevision) -> dict:
    return {
        "belief_ref": revision.belief_ref,
        "revision_ref": revision.revision_ref,
        "epistemic_kind": revision.epistemic_kind,
        "claim_text": revision.claim_text,
        "confidence": revision.confidence,
        "scope": _scope_checkpoint_row(revision.scope),
        "source_component": revision.source_component,
        "observed_at": revision.observed_at,
        "supporting_evidence_refs": list(revision.supporting_evidence_refs),
        "contradicting_evidence_refs": list(revision.contradicting_evidence_refs),
        "revision_reason": revision.revision_reason,
        "prior_revision_ref": revision.prior_revision_ref,
        "epistemic_status": revision.epistemic_status,
        "estimator_ref": revision.estimator_ref,
        "estimator_version": revision.estimator_version,
    }


def _revision_from_checkpoint_row(raw) -> BeliefRevision:
    if not isinstance(raw, Mapping):
        raise TypeError("epistemic revision checkpoint row must be a mapping")
    confidence = raw.get("confidence")
    return BeliefRevision(
        belief_ref=str(raw["belief_ref"]),
        revision_ref=str(raw["revision_ref"]),
        epistemic_kind=str(raw["epistemic_kind"]),
        claim_text=str(raw["claim_text"]),
        confidence=None if confidence is None else float(confidence),
        scope=_scope_from_checkpoint_row(raw["scope"]),
        source_component=str(raw["source_component"]),
        observed_at=str(raw["observed_at"]),
        supporting_evidence_refs=tuple(
            str(item) for item in raw.get("supporting_evidence_refs", ())
        ),
        contradicting_evidence_refs=tuple(
            str(item) for item in raw.get("contradicting_evidence_refs", ())
        ),
        revision_reason=str(raw.get("revision_reason", "")),
        prior_revision_ref=str(raw.get("prior_revision_ref", "")),
        epistemic_status=str(raw.get("epistemic_status", "active")),
        estimator_ref=str(raw.get("estimator_ref", "")),
        estimator_version=str(raw.get("estimator_version", "")),
    )
