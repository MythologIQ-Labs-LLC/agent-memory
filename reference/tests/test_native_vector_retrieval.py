from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.configured_restart import ConfigBoundRestartRuntime
from agentmem_ref.recall_control import (
    ControlledRecallPlanner,
    RecallControlPlan,
    RecallRouteBudget,
)
from agentmem_ref.runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    ConfiguredCompositionRuntime,
    DeterministicMultiRouteRecallPlanner,
)
from agentmem_ref.runtime_config import validate_runtime_configuration
from agentmem_ref.vector_retrieval import (
    DETERMINISTIC_REBUILD_POSTURE,
    SEMANTIC_VECTOR_ROUTE,
    NativeVectorCandidateRetriever,
    VectorRepresentationSpec,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reference" / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-native-vector"
PROJECT = "project-alpha"


def _plan():
    return validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8")))


def _proposal(
    target: str,
    *,
    evidence_refs: tuple[str, ...],
    project_ref: str = PROJECT,
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=f"proposal:{target}",
        actor_id="agent:native-vector-test",
        charter_version="charter-v1",
        target_reference=target,
        target_class=policy.M2,
        scope=TENANT,
        operation="promotion",
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=evidence_refs,
        tenant_ref=TENANT,
        isolation_domain_refs=(TENANT, project_ref),
        required_isolation_domain_refs=(project_ref,),
        project_ref=project_ref,
        purpose="native-vector-test",
    )


def _prune_proposal(target: str) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=f"prune:{target}",
        actor_id="agent:native-vector-test",
        charter_version="charter-v1",
        target_reference=target,
        target_class=policy.M1,
        scope=TENANT,
        operation="pruning",
        current_strength="observed",
        proposed_strength="tentative",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=("evidence:forget",),
        tenant_ref=TENANT,
        isolation_domain_refs=(TENANT, PROJECT),
        required_isolation_domain_refs=(PROJECT,),
        project_ref=PROJECT,
        purpose="native-vector-test",
        review_satisfied=True,
        approval_refs=("approver:fixture",),
    )


def _context(project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:native-vector-test",
        project_ref=project_ref,
        purpose="native-vector-test",
    )


class _FixtureRepresentation:
    """Credential-free deterministic semantic fixture, not a product embedding model."""

    spec = VectorRepresentationSpec(
        representation_ref="agent-memory:test-semantic-fixture",
        representation_version="1.0.0",
        config_digest="sha256:test-semantic-fixture-v1",
        dimensions=3,
        deterministic_rebuild=True,
    )

    def __init__(self, vectors: dict[str, tuple[float, float, float]]) -> None:
        self._vectors = vectors

    def embed(self, text: str) -> tuple[float, ...]:
        return self._vectors.get(text, (0.0, 0.0, 0.0))


class _FixedController:
    def __init__(self, plan: RecallControlPlan) -> None:
        self._plan = plan

    def plan(self, query, *, logical_memory_refs, available_routes):
        return self._plan


class _NoAllFactsSubstrate:
    """Delegating view that intentionally omits canonical enumeration."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def get_fact(self, uuid):
        return self._inner.get_fact(uuid)

    def search(self, query, group_ids=None):
        return self._inner.search(query, group_ids=group_ids)

    def evidence_neighbors(self, seed_uuid, group_ids=None):
        return self._inner.evidence_neighbors(seed_uuid, group_ids=group_ids)


class NativeVectorRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.representation = _FixtureRepresentation(
            {
                "vehicle maintenance question": (1.0, 0.0, 0.0),
                "the mechanic repaired the sedan": (1.0, 0.0, 0.0),
                "orchids need indirect light": (0.0, 1.0, 0.0),
                "private vehicle repair note": (0.95, 0.05, 0.0),
                "old vehicle repair guidance": (0.90, 0.10, 0.0),
                "new replacement guidance": (0.85, 0.15, 0.0),
                "vehicle maintenance": (1.0, 0.0, 0.0),
            }
        )
        self.vector = NativeVectorCandidateRetriever(self.representation)
        self.runtime = ConfiguredCompositionRuntime.create(
            Path(self.temp.name),
            tenant=TENANT,
            plan=_plan(),
            vector_retriever=self.vector,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _retain(
        self,
        target: str,
        text: str,
        *,
        evidence_refs: tuple[str, ...],
        project_ref: str = PROJECT,
    ):
        outcome = self.runtime.retain(
            _proposal(target, evidence_refs=evidence_refs, project_ref=project_ref),
            text,
        )
        self.assertTrue(outcome.committed)
        self.assertIsNotNone(outcome.fact_uuid)
        return outcome

    def test_vector_route_recovers_semantic_candidate_when_lexical_route_misses(self) -> None:
        semantic = self._retain(
            "memory:mechanic",
            "the mechanic repaired the sedan",
            evidence_refs=("experience:vehicle",),
        )
        unrelated = self._retain(
            "memory:orchids",
            "orchids need indirect light",
            evidence_refs=("experience:garden",),
        )

        lexical = self.runtime.adapter.governed_recall(
            "vehicle maintenance question",
            _context(),
        )
        result = self.runtime.multi_route_recall(
            "vehicle maintenance question",
            _context(),
        )

        self.assertNotIn(semantic.fact_uuid, lexical.candidates)
        self.assertIn(SEMANTIC_VECTOR_ROUTE, result.routes_executed)
        self.assertIn(semantic.fact_uuid, result.admitted)
        self.assertNotIn(unrelated.fact_uuid, result.candidates)

        hits = [
            hit
            for hit in result.provenance_for(semantic.fact_uuid)
            if hit.route_id == SEMANTIC_VECTOR_ROUTE
        ]
        self.assertEqual(len(hits), 1)
        hit = hits[0]
        self.assertAlmostEqual(hit.raw_score, 1.0)
        self.assertEqual(hit.representation_ref, self.representation.spec.representation_ref)
        self.assertEqual(hit.representation_version, self.representation.spec.representation_version)
        self.assertEqual(hit.representation_config_digest, self.representation.spec.config_digest)
        self.assertEqual(hit.vector_dimension, 3)
        self.assertEqual(hit.similarity_metric, "cosine")
        self.assertEqual(hit.currentness_basis, "governed_recall_admission")
        self.assertEqual(hit.authority_effect, "none")

    def test_vector_candidate_in_wrong_project_is_discovered_then_refused(self) -> None:
        foreign = self._retain(
            "memory:foreign",
            "private vehicle repair note",
            evidence_refs=("experience:foreign",),
            project_ref="project-beta",
        )

        result = self.runtime.multi_route_recall(
            "vehicle maintenance question",
            _context(),
        )

        self.assertIn(foreign.fact_uuid, result.candidates)
        self.assertNotIn(foreign.fact_uuid, result.admitted)
        self.assertNotIn(foreign.fact_uuid, result.ranked_admitted)
        self.assertEqual(
            result.refusals[foreign.fact_uuid],
            "required_isolation_domain_missing",
        )

    def test_superseded_high_similarity_vector_candidate_cannot_influence(self) -> None:
        stale = self._retain(
            "memory:stale",
            "old vehicle repair guidance",
            evidence_refs=("experience:stale",),
        )
        substrate = self.runtime.adapter.checkpoint_substrate()
        substrate.invalidate_fact(
            stale.fact_uuid,
            invalid_at="2026-09-23T20:00:00Z",
            expired_at="2026-09-23T20:00:01Z",
        )

        result = self.runtime.multi_route_recall(
            "vehicle maintenance question",
            _context(),
        )

        self.assertIn(stale.fact_uuid, result.candidates)
        self.assertNotIn(stale.fact_uuid, result.admitted)
        self.assertEqual(result.refusals[stale.fact_uuid], "superseded_not_current")

    def test_tombstoned_high_similarity_vector_residue_cannot_influence(self) -> None:
        forgotten = self._retain(
            "memory:forgotten",
            "the mechanic repaired the sedan",
            evidence_refs=("experience:forgotten",),
        )
        deleted = self.runtime.delete_current(_prune_proposal("memory:forgotten"))
        self.assertTrue(deleted.committed, f"refused: {deleted.refusal}")
        self.assertIsNotNone(self.runtime.adapter.tombstone(forgotten.fact_uuid))

        result = self.runtime.multi_route_recall(
            "vehicle maintenance question",
            _context(),
        )

        # Pruning intentionally leaves reconstructable canonical content. The
        # vector route may therefore rediscover physical residue, but governed
        # recall must keep that residue non-influential.
        self.assertIn(forgotten.fact_uuid, result.candidates)
        self.assertNotIn(forgotten.fact_uuid, result.admitted)
        self.assertNotIn(forgotten.fact_uuid, result.ranked_admitted)
        self.assertTrue(result.refusals[forgotten.fact_uuid])

    def test_deterministic_vector_rebuild_survives_restart_without_new_memory_identity(self) -> None:
        retained = self._retain(
            "memory:mechanic",
            "the mechanic repaired the sedan",
            evidence_refs=("experience:restart",),
        )
        before = self.runtime.multi_route_recall(
            "vehicle maintenance question",
            _context(),
        )
        self.assertIn(retained.fact_uuid, before.admitted)

        recovered_durable = ConfigBoundRestartRuntime.recover(
            Path(self.temp.name),
            plan=_plan(),
        )
        recovered = ConfiguredCompositionRuntime(
            durable_runtime=recovered_durable,
            plan=_plan(),
            vector_retriever=self.vector,
        )
        after = recovered.multi_route_recall(
            "vehicle maintenance question",
            _context(),
        )

        self.assertEqual(
            recovered.adapter.current_fact_uuid("memory:mechanic"),
            retained.fact_uuid,
        )
        self.assertIn(retained.fact_uuid, after.admitted)
        vector_hits = [
            hit
            for hit in after.provenance_for(retained.fact_uuid)
            if hit.route_id == SEMANTIC_VECTOR_ROUTE
        ]
        self.assertEqual(len(vector_hits), 1)
        self.assertEqual(
            vector_hits[0].representation_ref,
            self.representation.spec.representation_ref,
        )
        self.assertEqual(
            vector_hits[0].representation_version,
            self.representation.spec.representation_version,
        )
        self.assertEqual(
            vector_hits[0].representation_config_digest,
            self.representation.spec.config_digest,
        )
        # Rebuild posture belongs to the representation profile rather than the
        # per-candidate normalized hit. The benchmark binds the same profile.
        self.assertEqual(
            self.vector.spec.rebuild_posture,
            DETERMINISTIC_REBUILD_POSTURE,
        )

    def test_same_candidate_from_lexical_and_vector_routes_is_deduped_with_both_provenances(self) -> None:
        candidate = self._retain(
            "memory:vehicle",
            "vehicle maintenance",
            evidence_refs=("experience:vehicle",),
        )

        result = self.runtime.multi_route_recall(
            "vehicle maintenance",
            _context(),
        )

        self.assertEqual(result.candidates.count(candidate.fact_uuid), 1)
        route_ids = {hit.route_id for hit in result.provenance_for(candidate.fact_uuid)}
        self.assertIn(LEXICAL_ROUTE, route_ids)
        self.assertIn(SEMANTIC_VECTOR_ROUTE, route_ids)

    def test_controlled_recall_enforces_vector_candidate_budget(self) -> None:
        first = self._retain(
            "memory:first",
            "the mechanic repaired the sedan",
            evidence_refs=("experience:first",),
        )
        self._retain(
            "memory:second",
            "old vehicle repair guidance",
            evidence_refs=("experience:second",),
        )
        fixed = _FixedController(
            RecallControlPlan(
                controller_ref="test:vector-budget",
                controller_version="1",
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, 0),
                    RecallRouteBudget(EXACT_IDENTITY_ROUTE, 0),
                    RecallRouteBudget(SEMANTIC_VECTOR_ROUTE, 1),
                    RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0),
                ),
            )
        )

        result = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=fixed,
            vector_retriever=self.vector,
        ).recall("vehicle maintenance question", _context())

        self.assertEqual(result.route_candidate_counts[SEMANTIC_VECTOR_ROUTE], 1)
        self.assertEqual(result.recall.routes_executed, (SEMANTIC_VECTOR_ROUTE,))
        self.assertEqual(result.candidates, [first.fact_uuid])
        self.assertEqual(result.authority_effect, "none")

    def test_missing_enumeration_capability_omits_vector_route_without_fail_open(self) -> None:
        retained = self._retain(
            "memory:mechanic",
            "the mechanic repaired the sedan",
            evidence_refs=("experience:vehicle",),
        )
        original = self.runtime.adapter.checkpoint_substrate
        wrapper = _NoAllFactsSubstrate(original())
        self.runtime.adapter.checkpoint_substrate = lambda: wrapper
        try:
            planner = DeterministicMultiRouteRecallPlanner(
                self.runtime.adapter,
                vector_retriever=self.vector,
            )
            result = planner.recall(
                "vehicle maintenance question",
                _context(),
            )
        finally:
            self.runtime.adapter.checkpoint_substrate = original

        self.assertNotIn(SEMANTIC_VECTOR_ROUTE, result.routes_executed)
        self.assertNotIn(retained.fact_uuid, result.candidates)

    def test_representation_dimension_mismatch_fails_loudly(self) -> None:
        class BrokenRepresentation:
            spec = VectorRepresentationSpec(
                representation_ref="test:broken",
                representation_version="1",
                config_digest="sha256:broken",
                dimensions=3,
                deterministic_rebuild=True,
            )

            def embed(self, text):
                return (1.0, 0.0)

        broken = NativeVectorCandidateRetriever(BrokenRepresentation())
        with self.assertRaisesRegex(ValueError, "dimension mismatch"):
            broken.search(
                self.runtime.adapter.checkpoint_substrate(),
                "vehicle maintenance question",
                group_id=TENANT,
                candidate_limit=3,
            )

    def test_nondeterministic_representation_cannot_claim_first_profile(self) -> None:
        with self.assertRaisesRegex(ValueError, "deterministic rebuild"):
            VectorRepresentationSpec(
                representation_ref="test:nondeterministic",
                representation_version="1",
                config_digest="sha256:nondeterministic",
                dimensions=3,
                deterministic_rebuild=False,
            )


if __name__ == "__main__":
    unittest.main()
