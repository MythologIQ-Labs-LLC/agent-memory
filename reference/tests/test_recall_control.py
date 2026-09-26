from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.recall_control import (
    ControlledRecallPlanner,
    DeterministicRecallController,
    RecallControlPlan,
    RecallRouteBudget,
)
from agentmem_ref.restart_runtime import RuntimeRecoveryError
from agentmem_ref.runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    ConfiguredCompositionRuntime,
)
from agentmem_ref.runtime_config import validate_runtime_configuration


from tests.prefilter_bypass import admission_only  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reference" / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-recall-control"
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
        actor_id="agent:recall-control-test",
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
        purpose="recall-control-test",
    )


def _context(project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:recall-control-test",
        project_ref=project_ref,
        purpose="recall-control-test",
    )


class _FixedController:
    def __init__(self, plan: RecallControlPlan) -> None:
        self._plan = plan
        self.calls = 0

    def plan(self, query, *, logical_memory_refs, available_routes):
        self.calls += 1
        return self._plan


class RecallControlTests(unittest.TestCase):
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

    def test_deterministic_controller_selects_bounded_routes(self) -> None:
        controller = DeterministicRecallController()
        available = (LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE, SHARED_EVIDENCE_ROUTE)

        first = controller.plan(
            "Which pottery class produced the blue bowl?",
            logical_memory_refs=("memory:known",),
            available_routes=available,
        )
        second = controller.plan(
            "Which pottery class produced the blue bowl?",
            logical_memory_refs=("memory:known",),
            available_routes=available,
        )

        self.assertEqual(first, second)
        self.assertGreater(first.budget_for(LEXICAL_ROUTE).candidate_limit, 0)
        self.assertEqual(first.budget_for(EXACT_IDENTITY_ROUTE).candidate_limit, 1)
        self.assertGreater(first.budget_for(SHARED_EVIDENCE_ROUTE).candidate_limit, 0)
        self.assertGreater(first.budget_for(SHARED_EVIDENCE_ROUTE).anchor_limit, 0)
        self.assertEqual(first.authority_effect, "none")

    def test_controller_budget_changes_executed_candidate_work(self) -> None:
        first = self._retain(
            "memory:first",
            "pottery class blue bowl",
            evidence_refs=("session:1", "dialog:1"),
        )
        self._retain(
            "memory:second",
            "pottery class clay glaze",
            evidence_refs=("session:2", "dialog:2"),
        )
        fixed = _FixedController(
            RecallControlPlan(
                controller_ref="test:fixed",
                controller_version="1",
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, 1),
                    RecallRouteBudget(EXACT_IDENTITY_ROUTE, 0),
                    RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0),
                ),
            )
        )
        result = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=fixed,
        ).recall("pottery class", _context())

        self.assertEqual(fixed.calls, 1)
        self.assertEqual(result.controller_calls, 1)
        self.assertEqual(result.route_candidate_counts[LEXICAL_ROUTE], 1)
        self.assertEqual(result.recall.routes_executed, (LEXICAL_ROUTE,))
        self.assertEqual(result.candidates, [first.fact_uuid])
        self.assertEqual(result.authority_effect, "none")

    def test_relational_budget_is_enforced(self) -> None:
        seed = self._retain(
            "memory:seed",
            "pottery class started last week",
            evidence_refs=("session:1", "dialog:seed"),
        )
        self._retain(
            "memory:neighbor-a",
            "a blue bowl",
            evidence_refs=("session:1", "dialog:a"),
        )
        self._retain(
            "memory:neighbor-b",
            "a red mug",
            evidence_refs=("session:1", "dialog:b"),
        )
        fixed = _FixedController(
            RecallControlPlan(
                controller_ref="test:fixed",
                controller_version="1",
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, 4),
                    RecallRouteBudget(EXACT_IDENTITY_ROUTE, 0),
                    RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 1, anchor_limit=1),
                ),
            )
        )
        result = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=fixed,
        ).recall("pottery class", _context())

        self.assertIn(seed.fact_uuid, result.admitted)
        self.assertEqual(result.route_candidate_counts[SHARED_EVIDENCE_ROUTE], 1)
        relation_hits = [
            hit
            for hits in result.recall.route_hits.values()
            for hit in hits
            if hit.route_id == SHARED_EVIDENCE_ROUTE
        ]
        self.assertEqual(len(relation_hits), 1)

    @admission_only()  # exercises full admission's own domain refusal (#548)

    def test_controller_cannot_authorize_cross_project_neighbor(self) -> None:
        self._retain(
            "memory:seed",
            "pottery class started last week",
            evidence_refs=("session:shared", "dialog:seed"),
        )
        foreign = self._retain(
            "memory:foreign",
            "a blue bowl",
            evidence_refs=("session:shared", "dialog:foreign"),
            project_ref="project-beta",
        )
        fixed = _FixedController(
            RecallControlPlan(
                controller_ref="test:maximal-retriever",
                controller_version="1",
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, 32),
                    RecallRouteBudget(EXACT_IDENTITY_ROUTE, 16),
                    RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 24, anchor_limit=3),
                ),
                evidence_sufficiency_target=1,
            )
        )
        result = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=fixed,
        ).recall("pottery class", _context())

        self.assertIn(foreign.fact_uuid, result.candidates)
        self.assertNotIn(foreign.fact_uuid, result.admitted)
        self.assertNotIn(foreign.fact_uuid, result.ranked_admitted)
        self.assertEqual(
            result.recall.refusals[foreign.fact_uuid],
            "required_isolation_domain_missing",
        )

    def test_exact_identity_budget_resolves_only_current_logical_refs(self) -> None:
        known = self._retain(
            "memory:known",
            "known identity content",
            evidence_refs=("session:known",),
        )
        fixed = _FixedController(
            RecallControlPlan(
                controller_ref="test:identity",
                controller_version="1",
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, 0),
                    RecallRouteBudget(EXACT_IDENTITY_ROUTE, 1),
                    RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0),
                ),
            )
        )
        result = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=fixed,
        ).recall(
            "the and of",
            _context(),
            logical_memory_refs=("memory:known", "memory:missing"),
        )

        self.assertEqual(result.candidates, [known.fact_uuid])
        self.assertEqual(result.recall.routes_executed, (EXACT_IDENTITY_ROUTE,))

    def test_unavailable_route_plan_fails_closed(self) -> None:
        fixed = _FixedController(
            RecallControlPlan(
                controller_ref="test:bad-route",
                controller_version="1",
                route_budgets=(RecallRouteBudget("imaginary_vector_route", 5),),
            )
        )
        planner = ControlledRecallPlanner(self.runtime.adapter, controller=fixed)
        with self.assertRaisesRegex(RuntimeRecoveryError, "unavailable routes"):
            planner.recall("anything", _context())

    def test_plan_cannot_claim_authority(self) -> None:
        with self.assertRaisesRegex(ValueError, "authority effect"):
            RecallControlPlan(
                controller_ref="test:authority",
                controller_version="1",
                route_budgets=(RecallRouteBudget(LEXICAL_ROUTE, 1),),
                authority_effect="allow",
            )


if __name__ == "__main__":
    unittest.main()
