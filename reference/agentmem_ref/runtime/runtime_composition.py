"""Executable multi-capability runtime composition for Agent Memory issue #280.

This bounded reference harness consumes a validated ``RuntimeConfigurationPlan``
and composes three already-existing Agent Memory surfaces:

* governed canonical semantic memory through ``GovernedMemoryAdapter``;
* governed recall admission through the same canonical adapter; and
* deterministic/reproducible derived-state lifecycle through
  ``ProjectionGovernor``.

RC-3 adds a deterministic multi-route candidate planner over that same governed
adapter. Retrieval routes remain discovery/ranking mechanisms only; a deduped
candidate union crosses one canonical admission boundary before ranking.

Issue #433 adds an Agent Memory-native relational route over shared retained
evidence. The relation is deliberately narrow: direct provenance neighbors,
not a claim of semantic graph search or GraphRAG.

The purpose is not to invent a new projection engine. It proves that a
configured derived component can be disabled, physically removed, and rebuilt
from canonical state without changing canonical logical memory identity or
letting stale/residual derived state influence the active path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .adapter import RecallContext
from .configured_restart import ConfigBoundRestartRuntime
from .contextual_recall_adapter import admit_preselected_candidates
from .projection_governance import ProjectionGovernor
from ..state.projections import (
    CURRENT,
    DETERMINISTIC,
    REFERENCE_ONLY,
    REPRODUCIBLE,
)
from ..state.substrate import EvidenceNeighborTemporalGraphPort
from .restart_runtime import RuntimeRecoveryError
from .runtime_config import RuntimeConfigurationPlan


CANONICAL_CAPABILITY = "semantic_fact_memory"
RETRIEVAL_CAPABILITY = "exact_identity_retrieval"
PROJECTION_CAPABILITY = "rebuild_projection"
LEXICAL_ROUTE = "lexical"
EXACT_IDENTITY_ROUTE = "exact_logical_identity"
SHARED_EVIDENCE_ROUTE = "shared_evidence_neighbor"


@dataclass(frozen=True)
class RetrievalRouteHit:
    route_id: str
    candidate_ref: str
    raw_score: float
    logical_memory_ref: str = ""
    seed_candidate_ref: str = ""
    shared_evidence_refs: tuple[str, ...] = ()
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "candidate_ref": self.candidate_ref,
            "raw_score": self.raw_score,
            "logical_memory_ref": self.logical_memory_ref,
            "seed_candidate_ref": self.seed_candidate_ref,
            "shared_evidence_refs": list(self.shared_evidence_refs),
            "authority_effect": self.authority_effect,
        }


@dataclass
class MultiRouteRecallResult:
    query: str
    routes_executed: tuple[str, ...]
    candidates: list[str] = field(default_factory=list)
    admitted: list[str] = field(default_factory=list)
    refusals: dict[str, str] = field(default_factory=dict)
    decisions: dict[str, dict] = field(default_factory=dict)
    route_hits: dict[str, list[RetrievalRouteHit]] = field(default_factory=dict)
    ranked_admitted: list[str] = field(default_factory=list)
    policy_version: str = ""
    evaluated_at: str = ""
    authority_effect: str = "none"

    def provenance_for(self, candidate_ref: str) -> tuple[RetrievalRouteHit, ...]:
        return tuple(self.route_hits.get(candidate_ref, ()))


class DeterministicMultiRouteRecallPlanner:
    """Candidate planner: lexical, exact identity, and optional provenance neighbors.

    The planner remains deliberately provider-neutral and deterministic. Shared-
    evidence traversal is enabled only when the configured substrate explicitly
    implements ``EvidenceNeighborTemporalGraphPort``. Future vector, graph,
    temporal, or System-One routes can add candidate evidence behind this same
    result shape without inheriting recall authority.
    """

    def __init__(self, adapter) -> None:
        self.adapter = adapter
        substrate_reader = getattr(adapter, "checkpoint_substrate", None)
        tenant_reader = getattr(adapter, "checkpoint_tenant", None)
        if not callable(substrate_reader) or not callable(tenant_reader):
            raise RuntimeRecoveryError(
                "RC multi-route recall requires the restart-safe adapter substrate/tenant contract"
            )

    def recall(
        self,
        query: str,
        context: RecallContext,
        *,
        logical_memory_refs: tuple[str, ...] = (),
    ) -> MultiRouteRecallResult:
        substrate = self.adapter.checkpoint_substrate()
        tenant = self.adapter.checkpoint_tenant()

        hits: list[RetrievalRouteHit] = []
        routes_executed = [LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE]
        for fact, score in substrate.search(query, group_ids=[tenant]):
            hits.append(
                RetrievalRouteHit(
                    route_id=LEXICAL_ROUTE,
                    candidate_ref=fact.uuid,
                    raw_score=float(score),
                )
            )

        seed_pairs: list[tuple[str, str]] = []
        for logical_ref in dict.fromkeys(logical_memory_refs):
            current = self.adapter.current_fact_uuid(logical_ref)
            if current is None:
                continue
            hits.append(
                RetrievalRouteHit(
                    route_id=EXACT_IDENTITY_ROUTE,
                    candidate_ref=current,
                    raw_score=1.0,
                    logical_memory_ref=logical_ref,
                )
            )
            seed_pairs.append((logical_ref, current))

        if seed_pairs and isinstance(substrate, EvidenceNeighborTemporalGraphPort):
            routes_executed.append(SHARED_EVIDENCE_ROUTE)
            for logical_ref, seed_ref in seed_pairs:
                seed_fact = substrate.get_fact(seed_ref)
                if seed_fact is None or seed_fact.is_event_invalid:
                    continue
                for fact, shared_refs, score in substrate.evidence_neighbors(
                    seed_ref,
                    group_ids=[tenant],
                ):
                    hits.append(
                        RetrievalRouteHit(
                            route_id=SHARED_EVIDENCE_ROUTE,
                            candidate_ref=fact.uuid,
                            raw_score=float(score),
                            logical_memory_ref=logical_ref,
                            seed_candidate_ref=seed_ref,
                            shared_evidence_refs=tuple(shared_refs),
                        )
                    )

        by_candidate: dict[str, list[RetrievalRouteHit]] = {}
        ordered_candidates: list[str] = []
        for hit in hits:
            if hit.candidate_ref not in by_candidate:
                by_candidate[hit.candidate_ref] = []
                ordered_candidates.append(hit.candidate_ref)
            by_candidate[hit.candidate_ref].append(hit)

        admission = admit_preselected_candidates(
            self.adapter,
            ordered_candidates,
            context,
            query_label=query,
        )

        ranked = sorted(
            admission.admitted,
            key=lambda candidate_ref: self._rank_key(
                candidate_ref,
                by_candidate.get(candidate_ref, ()),
            ),
        )
        return MultiRouteRecallResult(
            query=query,
            routes_executed=tuple(routes_executed),
            candidates=list(admission.candidates),
            admitted=list(admission.admitted),
            refusals=dict(admission.refusals),
            decisions=dict(admission.decisions),
            route_hits=by_candidate,
            ranked_admitted=ranked,
            policy_version=admission.policy_version,
            evaluated_at=admission.evaluated_at,
        )

    @staticmethod
    def _rank_key(candidate_ref: str, hits) -> tuple[object, ...]:
        route_ids = {hit.route_id for hit in hits}
        exact = 1 if EXACT_IDENTITY_ROUTE in route_ids else 0
        relational_score = max(
            (hit.raw_score for hit in hits if hit.route_id == SHARED_EVIDENCE_ROUTE),
            default=0.0,
        )
        lexical_score = max(
            (hit.raw_score for hit in hits if hit.route_id == LEXICAL_ROUTE),
            default=0.0,
        )
        return (
            -len(route_ids),
            -exact,
            -relational_score,
            -lexical_score,
            candidate_ref,
        )


@dataclass(frozen=True)
class ProjectionAdmission:
    projection_id: str
    admitted: bool
    freshness: str | None
    refusal: str | None
    component_enabled: bool
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, object]:
        return {
            "projection_id": self.projection_id,
            "admitted": self.admitted,
            "freshness": self.freshness,
            "refusal": self.refusal,
            "component_enabled": self.component_enabled,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class ComponentLifecycleEvidence:
    component_id: str
    action: str
    canonical_memory_id: str
    canonical_fact_uuid_before: str | None
    canonical_fact_uuid_after: str | None
    canonical_version_before: int
    canonical_version_after: int
    projection_present: bool
    projection_freshness: str | None
    authority_effect: str = "none"

    @property
    def canonical_identity_unchanged(self) -> bool:
        return (
            self.canonical_fact_uuid_before == self.canonical_fact_uuid_after
            and self.canonical_version_before == self.canonical_version_after
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "action": self.action,
            "canonical_memory_id": self.canonical_memory_id,
            "canonical_fact_uuid_before": self.canonical_fact_uuid_before,
            "canonical_fact_uuid_after": self.canonical_fact_uuid_after,
            "canonical_version_before": self.canonical_version_before,
            "canonical_version_after": self.canonical_version_after,
            "canonical_identity_unchanged": self.canonical_identity_unchanged,
            "projection_present": self.projection_present,
            "projection_freshness": self.projection_freshness,
            "authority_effect": self.authority_effect,
        }


class ConfiguredCompositionRuntime:
    """Reference execution layer over a validated #280 runtime plan."""

    def __init__(
        self,
        *,
        durable_runtime: ConfigBoundRestartRuntime,
        plan: RuntimeConfigurationPlan,
    ) -> None:
        self.durable_runtime = durable_runtime
        self.plan = plan
        self.adapter = durable_runtime.adapter
        self.projections = ProjectionGovernor(self.adapter)
        self.recall_planner = DeterministicMultiRouteRecallPlanner(self.adapter)
        self._projection_component_enabled = True
        self._projection_component_id = self._component_for(PROJECTION_CAPABILITY)
        self._canonical_component_id = self._component_for(CANONICAL_CAPABILITY)
        self._retrieval_component_id = self._component_for(RETRIEVAL_CAPABILITY)
        self._projection_id = self._projection_identity()
        self._assert_reference_topology()

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        tenant: str,
        plan: RuntimeConfigurationPlan,
        verifier_registry=None,
    ) -> "ConfiguredCompositionRuntime":
        """ADR-037 step 4b-2, DoD 20: forwards host-configured verifier trust."""
        durable = ConfigBoundRestartRuntime.create(
            root, tenant=tenant, plan=plan, verifier_registry=verifier_registry
        )
        return cls(durable_runtime=durable, plan=plan)

    def _route_for(self, capability_id: str):
        matches = [
            route for route in self.plan.resolved_routes
            if route.primary.capability_id == capability_id
        ]
        if len(matches) != 1:
            raise RuntimeRecoveryError(
                f"reference composition requires exactly one route for {capability_id!r}"
            )
        return matches[0]

    def _component_for(self, capability_id: str) -> str:
        return self._route_for(capability_id).primary.component_id

    def _projection_identity(self) -> str:
        route = self._route_for(PROJECTION_CAPABILITY)
        if not route.currentness_required or not route.projection_id:
            raise RuntimeRecoveryError(
                "reference derived capability requires an explicit currentness projection identity"
            )
        return route.projection_id

    def _assert_reference_topology(self) -> None:
        if self._canonical_component_id != self._retrieval_component_id:
            raise RuntimeRecoveryError(
                "reference canonical/retrieval capabilities must resolve to one governed adapter component"
            )
        if self._projection_component_id == self._canonical_component_id:
            raise RuntimeRecoveryError(
                "composition proof requires a materially distinct derived component"
            )

    @property
    def projection_component_enabled(self) -> bool:
        return self._projection_component_enabled

    @property
    def projection_id(self) -> str:
        return self._projection_id

    def retain(self, proposal, fact_text: str, *, evidence=None, attestation=None):
        """Commit canonical memory, then materialize the configured derived declaration.

        Forwards the qualified-evidence channel (ADR-037 step 4b-2, DoD 20).
        Without it this composition would be a path that reaches a governed
        mutation while making the remediation route unreachable.
        """
        result = self.durable_runtime.commit_proposal(
            proposal, fact_text, evidence=evidence, attestation=attestation
        )
        if result.committed and self._projection_component_enabled:
            if self.projections.store.get(self._projection_id) is None:
                self.projections.declare(
                    self._projection_id,
                    (proposal.target_reference,),
                    DETERMINISTIC,
                    REFERENCE_ONLY,
                    REPRODUCIBLE,
                    proposal.scope,
                    note="configured reference derived projection",
                )
        return result

    def correct(self, proposal, fact_text: str, *, evidence=None, attestation=None):
        """Commit a governed correction; derived currentness changes by relation.

        No rebuild is triggered here. A correction therefore cannot use
        invalidation as an implicit write channel.

        Forwards the qualified-evidence channel (ADR-037 step 4b-2, DoD 20).
        """
        return self.durable_runtime.commit_proposal(
            proposal, fact_text, evidence=evidence, attestation=attestation
        )

    def recall(self, query: str, context: RecallContext):
        """Compatibility path: lexical retrieval through the governed adapter."""
        self._route_for(RETRIEVAL_CAPABILITY)
        return self.adapter.governed_recall(query, context)

    def multi_route_recall(
        self,
        query: str,
        context: RecallContext,
        *,
        logical_memory_refs: tuple[str, ...] = (),
    ) -> MultiRouteRecallResult:
        """Multiple candidate routes, one canonical governed admission boundary."""
        self._route_for(RETRIEVAL_CAPABILITY)
        return self.recall_planner.recall(
            query,
            context,
            logical_memory_refs=logical_memory_refs,
        )

    def projection_admission(self) -> ProjectionAdmission:
        projection = self.projections.store.get(self._projection_id)
        if not self._projection_component_enabled:
            return ProjectionAdmission(
                projection_id=self._projection_id,
                admitted=False,
                freshness=self.projections.freshness(self._projection_id),
                refusal="component_disabled",
                component_enabled=False,
            )
        if projection is None:
            return ProjectionAdmission(
                projection_id=self._projection_id,
                admitted=False,
                freshness=None,
                refusal="projection_unavailable",
                component_enabled=True,
            )
        freshness = self.projections.freshness(self._projection_id)
        if freshness != CURRENT:
            return ProjectionAdmission(
                projection_id=self._projection_id,
                admitted=False,
                freshness=freshness,
                refusal=f"projection_{freshness}",
                component_enabled=True,
            )
        return ProjectionAdmission(
            projection_id=self._projection_id,
            admitted=True,
            freshness=freshness,
            refusal=None,
            component_enabled=True,
        )

    def rebuild_projection(self):
        if not self._projection_component_enabled:
            raise RuntimeRecoveryError("derived component is disabled")
        return self.projections.propose_rebuild(self._projection_id)

    def disable_projection_component(self, memory_id: str) -> ComponentLifecycleEvidence:
        before_fact = self.adapter.current_fact_uuid(memory_id)
        before_version = self.adapter.state_version(memory_id)
        self._projection_component_enabled = False
        return self._lifecycle_evidence(
            action="disable",
            memory_id=memory_id,
            before_fact=before_fact,
            before_version=before_version,
        )

    def remove_projection_component(self, memory_id: str) -> ComponentLifecycleEvidence:
        before_fact = self.adapter.current_fact_uuid(memory_id)
        before_version = self.adapter.state_version(memory_id)
        self._projection_component_enabled = False
        self.projections.store.drop(self._projection_id)
        return self._lifecycle_evidence(
            action="remove",
            memory_id=memory_id,
            before_fact=before_fact,
            before_version=before_version,
        )

    def restore_and_rebuild_projection_component(
        self,
        memory_id: str,
        *,
        scope: str,
    ) -> ComponentLifecycleEvidence:
        before_fact = self.adapter.current_fact_uuid(memory_id)
        before_version = self.adapter.state_version(memory_id)
        self._projection_component_enabled = True
        self.projections.store.drop(self._projection_id)
        self.projections.declare(
            self._projection_id,
            (memory_id,),
            DETERMINISTIC,
            REFERENCE_ONLY,
            REPRODUCIBLE,
            scope,
            note="rebuilt after configured derived component restoration",
        )
        return self._lifecycle_evidence(
            action="restore_and_rebuild",
            memory_id=memory_id,
            before_fact=before_fact,
            before_version=before_version,
        )

    def delete_current(self, proposal, *, evidence=None, external_verification=None):
        """ADR-037 step 4b-2, DoD 20: forwards the deletion channels."""
        current = self.adapter.current_fact_uuid(proposal.target_reference)
        if current is None:
            raise RuntimeRecoveryError("cannot delete memory with no current canonical fact")
        return self.durable_runtime.governed_delete(
            proposal,
            current,
            derived_refs=(self._projection_id,),
            external_verification=external_verification,
            evidence=evidence,
        )

    def _lifecycle_evidence(
        self,
        *,
        action: str,
        memory_id: str,
        before_fact: str | None,
        before_version: int,
    ) -> ComponentLifecycleEvidence:
        return ComponentLifecycleEvidence(
            component_id=self._projection_component_id,
            action=action,
            canonical_memory_id=memory_id,
            canonical_fact_uuid_before=before_fact,
            canonical_fact_uuid_after=self.adapter.current_fact_uuid(memory_id),
            canonical_version_before=before_version,
            canonical_version_after=self.adapter.state_version(memory_id),
            projection_present=self.projections.store.get(self._projection_id) is not None,
            projection_freshness=self.projections.freshness(self._projection_id),
        )
