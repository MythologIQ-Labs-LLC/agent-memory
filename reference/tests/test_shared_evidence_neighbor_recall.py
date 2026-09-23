from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    ConfiguredCompositionRuntime,
    DeterministicMultiRouteRecallPlanner,
)
from agentmem_ref.runtime_config import validate_runtime_configuration


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reference" / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-acme"
PROJECT = "project-alpha"


def _plan():
    return validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8")))


def _proposal(
    proposal_id: str,
    target: str,
    *,
    evidence_refs: tuple[str, ...],
    project_ref: str = PROJECT,
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:evidence-neighbor-test",
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
        purpose="deployment-planning",
    )


def _context(project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:evidence-neighbor-test",
        project_ref=project_ref,
        purpose="deployment-planning",
    )


class _NoEvidenceNeighborSubstrate:
    """Delegating view that intentionally omits evidence_neighbors()."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def get_fact(self, uuid):
        return self._inner.get_fact(uuid)

    def search(self, query, group_ids=None):
        return self._inner.search(query, group_ids=group_ids)


class SharedEvidenceNeighborRecallTests(unittest.TestCase):
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
        evidence_refs: tuple[str, ...],
        project_ref: str = PROJECT,
    ):
        result = self.runtime.retain(
            _proposal(
                f"proposal:{target}",
                target,
                evidence_refs=evidence_refs,
                project_ref=project_ref,
            ),
            text,
        )
        self.assertTrue(result.committed)
        self.assertIsNotNone(result.fact_uuid)
        return result

    def test_shared_evidence_neighbor_recovers_related_memory_when_text_misses(self) -> None:
        seed = self._retain(
            "memory:deploy-decision",
            "release branch is main",
            evidence_refs=("experience:deploy-001",),
        )
        related = self._retain(
            "memory:deploy-belief",
            "staged rollout remains preferred",
            evidence_refs=("experience:deploy-001",),
        )
        unrelated = self._retain(
            "memory:lunch",
            "team lunch is Tuesday",
            evidence_refs=("experience:lunch-001",),
        )

        result = self.runtime.multi_route_recall(
            "weather forecast",
            _context(),
            logical_memory_refs=("memory:deploy-decision",),
        )

        self.assertIn(SHARED_EVIDENCE_ROUTE, result.routes_executed)
        self.assertIn(seed.fact_uuid, result.admitted)
        self.assertIn(related.fact_uuid, result.admitted)
        self.assertNotIn(unrelated.fact_uuid, result.candidates)
        hits = result.provenance_for(related.fact_uuid)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].route_id, SHARED_EVIDENCE_ROUTE)
        self.assertEqual(hits[0].seed_candidate_ref, seed.fact_uuid)
        self.assertEqual(hits[0].shared_evidence_refs, ("experience:deploy-001",))
        self.assertEqual(hits[0].authority_effect, "none")

    def test_multiple_shared_evidence_refs_do_not_duplicate_candidate(self) -> None:
        shared = ("evidence:a", "evidence:b")
        self._retain("memory:seed", "seed text", evidence_refs=shared)
        neighbor = self._retain("memory:neighbor", "neighbor text", evidence_refs=shared)

        result = self.runtime.multi_route_recall(
            "no lexical overlap",
            _context(),
            logical_memory_refs=("memory:seed",),
        )

        self.assertEqual(result.candidates.count(neighbor.fact_uuid), 1)
        hits = [
            hit
            for hit in result.provenance_for(neighbor.fact_uuid)
            if hit.route_id == SHARED_EVIDENCE_ROUTE
        ]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].shared_evidence_refs, shared)
        self.assertEqual(hits[0].raw_score, 1.0)

    def test_cross_project_related_candidate_is_still_refused(self) -> None:
        shared = ("experience:cross-project",)
        self._retain("memory:seed", "seed text", evidence_refs=shared)
        foreign = self._retain(
            "memory:foreign",
            "foreign related text",
            evidence_refs=shared,
            project_ref="project-beta",
        )

        result = self.runtime.multi_route_recall(
            "no lexical overlap",
            _context(),
            logical_memory_refs=("memory:seed",),
        )

        self.assertIn(foreign.fact_uuid, result.candidates)
        self.assertNotIn(foreign.fact_uuid, result.admitted)
        self.assertNotIn(foreign.fact_uuid, result.ranked_admitted)
        self.assertEqual(
            result.refusals[foreign.fact_uuid],
            "required_isolation_domain_missing",
        )

    def test_superseded_related_candidate_is_discovered_but_cannot_influence(self) -> None:
        shared = ("experience:superseded-neighbor",)
        self._retain("memory:seed", "seed text", evidence_refs=shared)
        stale = self._retain("memory:stale", "stale related text", evidence_refs=shared)
        substrate = self.runtime.adapter.checkpoint_substrate()
        substrate.invalidate_fact(
            stale.fact_uuid,
            invalid_at="2026-09-23T12:00:00Z",
            expired_at="2026-09-23T12:00:01Z",
        )

        result = self.runtime.multi_route_recall(
            "no lexical overlap",
            _context(),
            logical_memory_refs=("memory:seed",),
        )

        self.assertIn(stale.fact_uuid, result.candidates)
        self.assertNotIn(stale.fact_uuid, result.admitted)
        self.assertEqual(result.refusals[stale.fact_uuid], "superseded_not_current")

    def test_invalid_seed_does_not_expand_to_neighbors(self) -> None:
        shared = ("experience:invalid-seed",)
        seed = self._retain("memory:seed", "seed text", evidence_refs=shared)
        neighbor = self._retain("memory:neighbor", "neighbor text", evidence_refs=shared)
        substrate = self.runtime.adapter.checkpoint_substrate()
        substrate.invalidate_fact(
            seed.fact_uuid,
            invalid_at="2026-09-23T12:00:00Z",
            expired_at="2026-09-23T12:00:01Z",
        )

        result = self.runtime.multi_route_recall(
            "no lexical overlap",
            _context(),
            logical_memory_refs=("memory:seed",),
        )

        self.assertIn(seed.fact_uuid, result.candidates)
        self.assertEqual(result.refusals[seed.fact_uuid], "superseded_not_current")
        self.assertNotIn(neighbor.fact_uuid, result.candidates)

    def test_missing_optional_neighbor_capability_omits_route_without_fail_open(self) -> None:
        seed = self._retain(
            "memory:seed",
            "seed text",
            evidence_refs=("experience:optional-port",),
        )
        self._retain(
            "memory:neighbor",
            "neighbor text",
            evidence_refs=("experience:optional-port",),
        )
        original = self.runtime.adapter.checkpoint_substrate
        wrapper = _NoEvidenceNeighborSubstrate(original())
        self.runtime.adapter.checkpoint_substrate = lambda: wrapper
        try:
            planner = DeterministicMultiRouteRecallPlanner(self.runtime.adapter)
            result = planner.recall(
                "no lexical overlap",
                _context(),
                logical_memory_refs=("memory:seed",),
            )
        finally:
            self.runtime.adapter.checkpoint_substrate = original

        self.assertNotIn(SHARED_EVIDENCE_ROUTE, result.routes_executed)
        self.assertEqual(result.candidates, [seed.fact_uuid])
        self.assertEqual(result.admitted, [seed.fact_uuid])
        self.assertEqual(
            {hit.route_id for hit in result.provenance_for(seed.fact_uuid)},
            {EXACT_IDENTITY_ROUTE},
        )


if __name__ == "__main__":
    unittest.main()
