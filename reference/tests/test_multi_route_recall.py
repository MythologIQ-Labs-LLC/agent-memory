from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    ConfiguredCompositionRuntime,
)
from agentmem_ref.runtime_config import validate_runtime_configuration


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reference" / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-acme"
PROJECT = "project-alpha"
MEMORY_DEPLOY = "memory:deploy-window"
MEMORY_BACKUP = "memory:backup-policy"


def _plan():
    return validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8")))


def _proposal(proposal_id: str, target: str, *, project_ref: str = PROJECT) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:multi-route-test",
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
        evidence_refs=(f"evidence:{proposal_id}",),
        tenant_ref=TENANT,
        isolation_domain_refs=(TENANT, project_ref),
        required_isolation_domain_refs=(project_ref,),
        project_ref=project_ref,
        purpose="deployment-planning",
    )


def _context(project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:multi-route-test",
        project_ref=project_ref,
        purpose="deployment-planning",
    )


class MultiRouteRecallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = ConfiguredCompositionRuntime.create(
            Path(self.temp.name),
            tenant=TENANT,
            plan=_plan(),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _retain(self, target: str, text: str, *, project_ref: str = PROJECT):
        result = self.runtime.retain(
            _proposal(f"proposal:{target}", target, project_ref=project_ref),
            text,
        )
        self.assertTrue(result.committed)
        self.assertIsNotNone(result.fact_uuid)
        return result

    def test_one_request_executes_both_routes_and_unions_candidates(self) -> None:
        deploy = self._retain(MEMORY_DEPLOY, "deploy window is Thursday")
        backup = self._retain(MEMORY_BACKUP, "database backups run nightly")

        result = self.runtime.multi_route_recall(
            "deploy window",
            _context(),
            logical_memory_refs=(MEMORY_BACKUP,),
        )

        self.assertEqual(result.routes_executed, (LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE))
        self.assertEqual(set(result.candidates), {deploy.fact_uuid, backup.fact_uuid})
        self.assertEqual(set(result.admitted), {deploy.fact_uuid, backup.fact_uuid})
        self.assertEqual(
            {hit.route_id for hit in result.provenance_for(deploy.fact_uuid)},
            {LEXICAL_ROUTE},
        )
        self.assertEqual(
            {hit.route_id for hit in result.provenance_for(backup.fact_uuid)},
            {EXACT_IDENTITY_ROUTE},
        )

    def test_exact_identity_recalls_current_fact_when_lexical_query_misses(self) -> None:
        backup = self._retain(MEMORY_BACKUP, "database backups run nightly")

        result = self.runtime.multi_route_recall(
            "weather forecast",
            _context(),
            logical_memory_refs=(MEMORY_BACKUP,),
        )

        self.assertIn(backup.fact_uuid, result.candidates)
        self.assertIn(backup.fact_uuid, result.admitted)
        hits = result.provenance_for(backup.fact_uuid)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].route_id, EXACT_IDENTITY_ROUTE)
        self.assertEqual(hits[0].raw_score, 1.0)

    def test_candidate_found_by_both_routes_keeps_both_provenance_records(self) -> None:
        deploy = self._retain(MEMORY_DEPLOY, "deploy window is Thursday")

        result = self.runtime.multi_route_recall(
            "deploy window",
            _context(),
            logical_memory_refs=(MEMORY_DEPLOY,),
        )

        self.assertEqual(result.candidates.count(deploy.fact_uuid), 1)
        self.assertEqual(result.admitted.count(deploy.fact_uuid), 1)
        self.assertEqual(
            {hit.route_id for hit in result.provenance_for(deploy.fact_uuid)},
            {LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE},
        )
        self.assertEqual(result.ranked_admitted, [deploy.fact_uuid])

    def test_exact_identity_score_cannot_bypass_project_scope(self) -> None:
        deploy = self._retain(MEMORY_DEPLOY, "deploy window is Thursday")

        result = self.runtime.multi_route_recall(
            "query that does not match",
            _context("project-beta"),
            logical_memory_refs=(MEMORY_DEPLOY,),
        )

        self.assertIn(deploy.fact_uuid, result.candidates)
        self.assertNotIn(deploy.fact_uuid, result.admitted)
        self.assertNotIn(deploy.fact_uuid, result.ranked_admitted)
        self.assertEqual(result.refusals[deploy.fact_uuid], "required_isolation_domain_missing")
        hit = result.provenance_for(deploy.fact_uuid)[0]
        self.assertEqual(hit.raw_score, 1.0)
        self.assertEqual(hit.authority_effect, "none")
        self.assertEqual(result.authority_effect, "none")

    def test_exact_identity_does_not_resurrect_superseded_currentness(self) -> None:
        deploy = self._retain(MEMORY_DEPLOY, "deploy window is Thursday")
        substrate = self.runtime.adapter.checkpoint_substrate()
        substrate.invalidate_fact(
            deploy.fact_uuid,
            invalid_at="2026-09-23T11:00:00Z",
            expired_at="2026-09-23T11:00:01Z",
        )

        result = self.runtime.multi_route_recall(
            "query that does not match",
            _context(),
            logical_memory_refs=(MEMORY_DEPLOY,),
        )

        self.assertIn(deploy.fact_uuid, result.candidates)
        self.assertNotIn(deploy.fact_uuid, result.admitted)
        self.assertEqual(result.refusals[deploy.fact_uuid], "superseded_not_current")

    def test_refused_candidate_never_enters_ranked_list(self) -> None:
        deploy = self._retain(MEMORY_DEPLOY, "deploy window is Thursday")
        backup = self._retain(MEMORY_BACKUP, "database backups run nightly", project_ref="project-beta")

        result = self.runtime.multi_route_recall(
            "deploy window",
            _context(),
            logical_memory_refs=(MEMORY_BACKUP,),
        )

        self.assertIn(deploy.fact_uuid, result.ranked_admitted)
        self.assertNotIn(backup.fact_uuid, result.ranked_admitted)
        self.assertEqual(result.refusals[backup.fact_uuid], "required_isolation_domain_missing")

    def test_compatibility_recall_preserves_existing_lexical_behavior(self) -> None:
        deploy = self._retain(MEMORY_DEPLOY, "deploy window is Thursday")

        legacy = self.runtime.recall("deploy window", _context())
        multi = self.runtime.multi_route_recall("deploy window", _context())

        self.assertEqual(legacy.candidates, [deploy.fact_uuid])
        self.assertEqual(legacy.admitted, [deploy.fact_uuid])
        self.assertEqual(multi.candidates, legacy.candidates)
        self.assertEqual(multi.admitted, legacy.admitted)
        self.assertEqual(multi.refusals, legacy.refusals)


if __name__ == "__main__":
    unittest.main()
