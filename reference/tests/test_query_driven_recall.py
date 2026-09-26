from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.query_driven_recall import (
    DeterministicQueryDrivenRecallPlanner,
    QueryDrivenRecallConfig,
)
from agentmem_ref.runtime_composition import SHARED_EVIDENCE_ROUTE, ConfiguredCompositionRuntime
from agentmem_ref.runtime_config import validate_runtime_configuration


from tests.prefilter_bypass import admission_only  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reference" / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-query-driven"
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
        actor_id="agent:query-driven-test",
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
        purpose="query-driven-recall-test",
    )


def _context(project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:query-driven-test",
        project_ref=project_ref,
        purpose="query-driven-recall-test",
    )


class QueryDrivenRecallTests(unittest.TestCase):
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
        outcome = self.runtime.retain(
            _proposal(target, evidence_refs=evidence_refs, project_ref=project_ref),
            text,
        )
        self.assertTrue(outcome.committed)
        self.assertIsNotNone(outcome.fact_uuid)
        return outcome

    def test_query_lexical_anchor_expands_to_shared_evidence_neighbor(self) -> None:
        seed = self._retain(
            "memory:pottery-anchor",
            "pottery class started last week",
            evidence_refs=("dialog:D1:1", "session:1"),
        )
        related = self._retain(
            "memory:pottery-answer",
            "a blue bowl",
            evidence_refs=("dialog:D1:3", "session:1"),
        )
        self._retain(
            "memory:unrelated",
            "team lunch is Tuesday",
            evidence_refs=("dialog:D2:1", "session:2"),
        )

        planner = DeterministicQueryDrivenRecallPlanner(
            self.runtime.adapter,
            config=QueryDrivenRecallConfig(lexical_anchor_limit=1),
        )
        result = planner.recall("pottery class", _context())

        self.assertIn(seed.fact_uuid, result.admitted)
        self.assertIn(related.fact_uuid, result.admitted)
        relation_hits = [
            hit
            for hit in result.provenance_for(related.fact_uuid)
            if hit.route_id == SHARED_EVIDENCE_ROUTE
        ]
        self.assertEqual(len(relation_hits), 1)
        self.assertEqual(relation_hits[0].seed_candidate_ref, seed.fact_uuid)
        self.assertEqual(relation_hits[0].shared_evidence_refs, ("session:1",))
        self.assertEqual(relation_hits[0].authority_effect, "none")

    def test_anchor_limit_zero_disables_query_driven_relation_expansion(self) -> None:
        self._retain(
            "memory:seed",
            "pottery class started last week",
            evidence_refs=("dialog:D1:1", "session:1"),
        )
        related = self._retain(
            "memory:related",
            "a blue bowl",
            evidence_refs=("dialog:D1:3", "session:1"),
        )

        planner = DeterministicQueryDrivenRecallPlanner(
            self.runtime.adapter,
            config=QueryDrivenRecallConfig(lexical_anchor_limit=0),
        )
        result = planner.recall("pottery class", _context())

        self.assertNotIn(related.fact_uuid, result.candidates)
        self.assertNotIn(SHARED_EVIDENCE_ROUTE, result.routes_executed)

    def test_superseded_lexical_anchor_cannot_expand(self) -> None:
        seed = self._retain(
            "memory:seed",
            "pottery class started last week",
            evidence_refs=("dialog:D1:1", "session:1"),
        )
        related = self._retain(
            "memory:related",
            "a blue bowl",
            evidence_refs=("dialog:D1:3", "session:1"),
        )
        substrate = self.runtime.adapter.checkpoint_substrate()
        substrate.invalidate_fact(
            seed.fact_uuid,
            invalid_at="2026-09-23T12:00:00Z",
            expired_at="2026-09-23T12:00:01Z",
        )

        planner = DeterministicQueryDrivenRecallPlanner(
            self.runtime.adapter,
            config=QueryDrivenRecallConfig(lexical_anchor_limit=1),
        )
        result = planner.recall("pottery class", _context())

        self.assertIn(seed.fact_uuid, result.candidates)
        self.assertEqual(result.refusals[seed.fact_uuid], "superseded_not_current")
        self.assertNotIn(related.fact_uuid, result.candidates)

    @admission_only()  # exercises full admission's own domain refusal (#548)

    def test_cross_project_neighbor_is_discovered_but_refused(self) -> None:
        shared = ("session:1",)
        self._retain(
            "memory:seed",
            "pottery class started last week",
            evidence_refs=("dialog:D1:1", *shared),
        )
        foreign = self._retain(
            "memory:foreign",
            "a blue bowl",
            evidence_refs=("dialog:D1:3", *shared),
            project_ref="project-beta",
        )

        planner = DeterministicQueryDrivenRecallPlanner(
            self.runtime.adapter,
            config=QueryDrivenRecallConfig(lexical_anchor_limit=1),
        )
        result = planner.recall("pottery class", _context())

        self.assertIn(foreign.fact_uuid, result.candidates)
        self.assertNotIn(foreign.fact_uuid, result.admitted)
        self.assertNotIn(foreign.fact_uuid, result.ranked_admitted)
        self.assertEqual(result.refusals[foreign.fact_uuid], "required_isolation_domain_missing")

    def test_explicit_logical_seed_still_expands_with_query_anchor_limit_zero(self) -> None:
        seed = self._retain(
            "memory:seed",
            "seed text",
            evidence_refs=("dialog:D1:1", "session:1"),
        )
        related = self._retain(
            "memory:related",
            "neighbor text",
            evidence_refs=("dialog:D1:3", "session:1"),
        )

        planner = DeterministicQueryDrivenRecallPlanner(
            self.runtime.adapter,
            config=QueryDrivenRecallConfig(lexical_anchor_limit=0),
        )
        result = planner.recall(
            "no lexical overlap",
            _context(),
            logical_memory_refs=("memory:seed",),
        )

        self.assertIn(seed.fact_uuid, result.admitted)
        self.assertIn(related.fact_uuid, result.admitted)
        self.assertIn(SHARED_EVIDENCE_ROUTE, result.routes_executed)

    def test_default_runtime_behavior_remains_unexpanded_without_explicit_seed(self) -> None:
        self._retain(
            "memory:seed",
            "pottery class started last week",
            evidence_refs=("dialog:D1:1", "session:1"),
        )
        related = self._retain(
            "memory:related",
            "a blue bowl",
            evidence_refs=("dialog:D1:3", "session:1"),
        )

        result = self.runtime.multi_route_recall("pottery class", _context())

        self.assertNotIn(related.fact_uuid, result.candidates)


if __name__ == "__main__":
    unittest.main()
