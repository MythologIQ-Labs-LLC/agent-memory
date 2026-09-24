from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.recall_control import (
    GRAPH_BOTH,
    ControlledRecallPlanner,
    GraphTraversalSpec,
    NativeTypedGraphCandidateRetriever,
    RecallControlPlan,
    RecallRouteBudget,
    TYPED_GRAPH_ROUTE,
)
from agentmem_ref.runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    ConfiguredCompositionRuntime,
)
from agentmem_ref.runtime_config import validate_runtime_configuration
from agentmem_ref.sqlite_substrate import SQLiteTemporalGraph
from agentmem_ref.substrate import Fact, InMemoryTemporalGraph, TypedRelation


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reference" / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-typed-graph"
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
        actor_id="agent:typed-graph-test",
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
        purpose="typed-graph-test",
    )


def _context(project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:typed-graph-test",
        project_ref=project_ref,
        purpose="typed-graph-test",
    )


def _fact(ref: str, *, group: str = TENANT) -> Fact:
    return Fact(
        uuid=ref,
        fact_text=f"fact {ref}",
        group_id=group,
        created_at="2026-09-24T00:00:00Z",
        valid_at="2026-09-24T00:00:00Z",
    )


def _relation(
    relation_id: str,
    source: str,
    target: str,
    *,
    relation_type: str = "supports",
    weight: float = 1.0,
    group: str = TENANT,
    evidence: tuple[str, ...] = (),
) -> TypedRelation:
    return TypedRelation(
        relation_id=relation_id,
        source_uuid=source,
        target_uuid=target,
        relation_type=relation_type,
        group_id=group,
        evidence_refs=evidence,
        retrieval_weight=weight,
        created_at="2026-09-24T00:00:00Z",
        valid_at="2026-09-24T00:00:00Z",
    )


class _FixedController:
    def __init__(self, plan: RecallControlPlan) -> None:
        self._plan = plan

    def plan(self, query, *, logical_memory_refs, available_routes):
        return self._plan


class TypedGraphSubstrateTests(unittest.TestCase):
    def test_checkpoint_round_trip_preserves_typed_relations_and_legacy_is_accepted(self) -> None:
        graph = InMemoryTemporalGraph()
        graph.write_fact(_fact("a"))
        graph.write_fact(_fact("b"))
        relation = _relation(
            "r1",
            "a",
            "b",
            relation_type="supports",
            weight=0.75,
            evidence=("evidence:1",),
        )
        graph.write_relation(relation)

        snapshot = graph.export_checkpoint_state()
        restored = InMemoryTemporalGraph()
        restored.restore_checkpoint_state(snapshot)
        self.assertEqual(restored.get_relation("r1"), relation)
        self.assertEqual(tuple(restored.all_relations()), (relation,))

        legacy = dict(snapshot)
        legacy.pop("relation_schema_version")
        legacy.pop("relations")
        legacy_restored = InMemoryTemporalGraph()
        legacy_restored.restore_checkpoint_state(legacy)
        self.assertEqual(tuple(legacy_restored.all_relations()), ())
        self.assertIsNotNone(legacy_restored.get_fact("a"))

    def test_traversal_is_typed_bounded_cycle_safe_and_keeps_best_path(self) -> None:
        graph = InMemoryTemporalGraph()
        for ref in ("a", "b", "c", "d", "e"):
            graph.write_fact(_fact(ref))
        graph.write_relation(_relation("r-ab", "a", "b", weight=0.60))
        graph.write_relation(_relation("r-ac", "a", "c", weight=0.90))
        graph.write_relation(_relation("r-cb", "c", "b", weight=0.90))
        graph.write_relation(_relation("r-ba", "b", "a", weight=0.95))
        graph.write_relation(
            _relation("r-bd", "b", "d", relation_type="contradicts", weight=1.0)
        )
        graph.write_relation(_relation("r-ce", "c", "e", weight=0.80))

        retriever = NativeTypedGraphCandidateRetriever(
            GraphTraversalSpec(
                max_depth=2,
                max_fanout=3,
                relation_types=("supports",),
            )
        )
        hits = retriever.search(graph, ("a",), group_id=TENANT, candidate_limit=10)
        by_ref = {hit.candidate_ref: hit for hit in hits}

        self.assertEqual(set(by_ref), {"b", "c", "e"})
        self.assertAlmostEqual(by_ref["b"].path_score, 0.81)
        self.assertEqual(by_ref["b"].path_refs, ("a", "c", "b"))
        self.assertEqual(by_ref["b"].relation_ids, ("r-ac", "r-cb"))
        self.assertEqual(by_ref["b"].hop_count, 2)
        self.assertNotIn("d", by_ref)
        self.assertNotIn("a", by_ref)
        self.assertEqual(by_ref["b"].authority_effect, "none")

    def test_invalid_relation_is_hidden_but_stale_fact_remains_candidate_evidence(self) -> None:
        graph = InMemoryTemporalGraph()
        graph.write_fact(_fact("a"))
        graph.write_fact(_fact("b"))
        graph.write_fact(_fact("c"))
        graph.write_relation(_relation("r-ab", "a", "b", weight=0.9))
        graph.write_relation(_relation("r-ac", "a", "c", weight=0.8))
        graph.invalidate_relation(
            "r-ac",
            "2026-09-24T01:00:00Z",
            "2026-09-24T01:00:00Z",
        )
        graph.invalidate_fact(
            "b",
            "2026-09-24T02:00:00Z",
            "2026-09-24T02:00:00Z",
        )

        hits = NativeTypedGraphCandidateRetriever().search(
            graph,
            ("a",),
            group_id=TENANT,
            candidate_limit=10,
        )
        self.assertEqual([hit.candidate_ref for hit in hits], ["b"])

        graph.delete_fact("b")
        self.assertIsNotNone(graph.get_relation("r-ab"))
        hits_after_delete = NativeTypedGraphCandidateRetriever().search(
            graph,
            ("a",),
            group_id=TENANT,
            candidate_limit=10,
        )
        self.assertEqual(hits_after_delete, [])

    def test_sqlite_reopen_matches_in_memory_traversal_and_preserves_relation_residue(self) -> None:
        memory = InMemoryTemporalGraph()
        for ref in ("a", "b", "c"):
            memory.write_fact(_fact(ref))
        memory.write_relation(_relation("r-ab", "a", "b", weight=0.8, evidence=("ev:ab",)))
        memory.write_relation(_relation("r-bc", "b", "c", weight=0.5, evidence=("ev:bc",)))

        retriever = NativeTypedGraphCandidateRetriever(
            GraphTraversalSpec(max_depth=2, max_fanout=4, direction=GRAPH_BOTH)
        )
        expected = retriever.search(memory, ("a",), group_id=TENANT, candidate_limit=10)

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.sqlite3"
            sqlite = SQLiteTemporalGraph(path)
            for ref in ("a", "b", "c"):
                sqlite.write_fact(_fact(ref))
            sqlite.write_relation(_relation("r-ab", "a", "b", weight=0.8, evidence=("ev:ab",)))
            sqlite.write_relation(_relation("r-bc", "b", "c", weight=0.5, evidence=("ev:bc",)))
            digest_before = sqlite.state_digest()
            sqlite.close()

            reopened = SQLiteTemporalGraph(path)
            actual = retriever.search(reopened, ("a",), group_id=TENANT, candidate_limit=10)
            self.assertEqual(actual, expected)
            self.assertEqual(reopened.state_digest(), digest_before)
            self.assertEqual(
                reopened.operational_identity()["relation_schema_version"],
                "1.0.0",
            )

            reopened.delete_fact("b")
            self.assertIsNotNone(reopened.get_relation("r-ab"))
            self.assertIsNotNone(reopened.get_relation("r-bc"))
            remaining = retriever.search(reopened, ("a",), group_id=TENANT, candidate_limit=10)
            self.assertEqual(remaining, [])
            reopened.close()


class TypedGraphGovernedRecallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = ConfiguredCompositionRuntime.create(
            Path(self.temp.name),
            tenant=TENANT,
            plan=_plan(),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _retain(
        self,
        target: str,
        text: str,
        *,
        project_ref: str = PROJECT,
    ):
        outcome = self.runtime.retain(
            _proposal(
                target,
                evidence_refs=(f"evidence:{target}",),
                project_ref=project_ref,
            ),
            text,
        )
        self.assertTrue(outcome.committed)
        self.assertIsNotNone(outcome.fact_uuid)
        return outcome

    @staticmethod
    def _graph_only_controller() -> _FixedController:
        return _FixedController(
            RecallControlPlan(
                controller_ref="test:typed-graph",
                controller_version="1",
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, 0),
                    RecallRouteBudget(EXACT_IDENTITY_ROUTE, 1),
                    RecallRouteBudget(TYPED_GRAPH_ROUTE, 8),
                    RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0),
                ),
            )
        )

    def test_graph_path_provenance_crosses_one_governed_admission_boundary(self) -> None:
        seed = self._retain("memory:seed", "seed memory")
        neighbor = self._retain("memory:neighbor", "related memory")
        substrate = self.runtime.adapter.checkpoint_substrate()
        substrate.write_relation(
            _relation(
                "relation:seed-neighbor",
                seed.fact_uuid,
                neighbor.fact_uuid,
                relation_type="supports",
                weight=0.7,
                evidence=("evidence:relation",),
            )
        )

        result = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=self._graph_only_controller(),
            graph_retriever=NativeTypedGraphCandidateRetriever(),
        ).recall(
            "",
            _context(),
            logical_memory_refs=("memory:seed",),
        )

        self.assertEqual(result.route_candidate_counts[TYPED_GRAPH_ROUTE], 1)
        self.assertIn(seed.fact_uuid, result.admitted)
        self.assertIn(neighbor.fact_uuid, result.admitted)
        graph_hit = result.graph_candidate_hits[neighbor.fact_uuid]
        self.assertEqual(graph_hit.path_refs, (seed.fact_uuid, neighbor.fact_uuid))
        self.assertEqual(graph_hit.relation_ids, ("relation:seed-neighbor",))
        self.assertEqual(graph_hit.relation_types, ("supports",))
        self.assertEqual(graph_hit.relation_evidence_refs, ("evidence:relation",))
        self.assertEqual(graph_hit.authority_effect, "none")

    def test_graph_reachable_cross_project_fact_is_discovered_then_refused(self) -> None:
        seed = self._retain("memory:seed", "seed memory")
        foreign = self._retain(
            "memory:foreign",
            "foreign related memory",
            project_ref="project-beta",
        )
        substrate = self.runtime.adapter.checkpoint_substrate()
        substrate.write_relation(
            _relation(
                "relation:cross-project",
                seed.fact_uuid,
                foreign.fact_uuid,
                relation_type="affects",
                weight=1.0,
            )
        )

        result = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=self._graph_only_controller(),
            graph_retriever=NativeTypedGraphCandidateRetriever(),
        ).recall(
            "",
            _context(PROJECT),
            logical_memory_refs=("memory:seed",),
        )

        self.assertIn(foreign.fact_uuid, result.candidates)
        self.assertNotIn(foreign.fact_uuid, result.admitted)
        self.assertEqual(
            result.recall.refusals[foreign.fact_uuid],
            "required_isolation_domain_missing",
        )
        self.assertEqual(
            result.graph_candidate_hits[foreign.fact_uuid].authority_effect,
            "none",
        )

    def test_graph_reachable_superseded_fact_is_candidate_but_not_active_influence(self) -> None:
        seed = self._retain("memory:seed", "seed memory")
        stale = self._retain("memory:stale", "stale related memory")
        substrate = self.runtime.adapter.checkpoint_substrate()
        substrate.write_relation(
            _relation(
                "relation:stale",
                seed.fact_uuid,
                stale.fact_uuid,
                relation_type="references",
                weight=1.0,
            )
        )
        substrate.invalidate_fact(
            stale.fact_uuid,
            "2026-09-24T03:00:00Z",
            "2026-09-24T03:00:00Z",
        )

        result = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=self._graph_only_controller(),
            graph_retriever=NativeTypedGraphCandidateRetriever(),
        ).recall(
            "",
            _context(),
            logical_memory_refs=("memory:seed",),
        )

        self.assertIn(stale.fact_uuid, result.candidates)
        self.assertNotIn(stale.fact_uuid, result.admitted)
        self.assertIn(stale.fact_uuid, result.recall.refusals)


if __name__ == "__main__":
    unittest.main()
