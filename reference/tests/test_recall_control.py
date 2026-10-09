from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.recall_control import (
    ControlledRecallPlanner,
    DeterministicRecallController,
    RecallControlPlan,
    RecallRouteBudget,
)
from agentmem_ref.runtime import typed_proposition as typed
from agentmem_ref.runtime.evidence_sufficiency import (
    CoverageNeed,
    CoverageObservation,
    TYPED_OBSERVATION,
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
        typed_write: dict | None = None,
    ):
        outcome = self.runtime.retain(
            _proposal(target, evidence_refs=evidence_refs, project_ref=project_ref),
            text,
            **({"typed_write": typed_write} if typed_write is not None else {}),
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

    def test_sufficiency_observer_cannot_change_governed_recall(self) -> None:
        retained = self._retain(
            "memory:sufficiency",
            "blue ceramic glaze in the pottery class",
            evidence_refs=("session:pottery",),
        )
        fixed = _FixedController(RecallControlPlan(
            controller_ref="test:typed-sufficiency",
            controller_version="1",
            route_budgets=(
                RecallRouteBudget(LEXICAL_ROUTE, 5),
                RecallRouteBudget(EXACT_IDENTITY_ROUTE, 0),
                RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0),
            ),
        ))
        result = ControlledRecallPlanner(
            self.runtime.adapter, controller=fixed,
        ).recall("blue ceramic glaze", _context())
        original = (
            list(result.candidates),
            list(result.admitted),
            list(result.ranked_admitted),
            dict(result.recall.refusals),
        )
        self.assertIn(retained.fact_uuid, result.admitted)
        estimate = result.observe_evidence_sufficiency(
            needs=(CoverageNeed("glaze"),),
            coverage=(CoverageObservation(retained.fact_uuid, ("glaze",)),),
        )
        self.assertTrue(estimate.count_target_met)
        self.assertFalse(estimate.mechanical_coverage_met)
        self.assertEqual(estimate.diagnosis, "missing_declared_evidence")

        observed = result.observe_evidence_sufficiency(
            needs=(CoverageNeed("glaze"),),
            coverage=(CoverageObservation(
                retained.fact_uuid, ("glaze",), TYPED_OBSERVATION,
            ),),
        )
        self.assertEqual(observed.diagnosis, "mechanical_coverage_observed")
        self.assertEqual(observed.continuation_proposal, "continue_if_permitted")
        self.assertFalse(observed.answer_quality_verified)
        self.assertFalse(observed.can_admit)
        self.assertFalse(observed.can_mutate)
        self.assertEqual(observed.authority_effect, "none")
        self.assertEqual(
            (
                list(result.candidates),
                list(result.admitted),
                list(result.ranked_admitted),
                dict(result.recall.refusals),
            ),
            original,
        )
        with self.assertRaisesRegex(ValueError, "governed admitted"):
            result.observe_evidence_sufficiency(
                needs=(CoverageNeed("glaze"),),
                coverage=(CoverageObservation(
                    "foreign-unadmitted-reference", ("glaze",), TYPED_OBSERVATION,
                ),),
            )

    @staticmethod
    def _typed_write(subject: str, attribute: str, value: str, *,
                     basis: str = typed.CALLER_DECLARED,
                     flags: dict | None = None, assertion: str = "state",
                     cardinality: str | None = "single") -> dict:
        validated = typed.validate({
            "subject": subject,
            "attribute": attribute,
            "value": value,
            "assertion": assertion,
            "cardinality": cardinality,
            "flags": flags or {},
        })
        return {"typed_proposition": typed.typed_record(validated, basis)}

    def _typed_plan(self):
        fixed = _FixedController(RecallControlPlan(
            controller_ref="test:persisted-coverage",
            controller_version="1",
            route_budgets=(
                RecallRouteBudget(LEXICAL_ROUTE, 12),
                RecallRouteBudget(EXACT_IDENTITY_ROUTE, 0),
                RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0),
            ),
        ))
        return ControlledRecallPlanner(self.runtime.adapter, controller=fixed)

    def test_persisted_slot_coverage_reads_real_governed_facts(self) -> None:
        kept = self._retain(
            "memory:typed",
            "Acme service base URL is api.acme.internal",
            evidence_refs=("session:typed",),
            typed_write=self._typed_write("Acme service", "base URL", "api.acme.internal"),
        )
        self._retain(
            "memory:untyped",
            "Acme service is running in production",
            evidence_refs=("session:other",),
        )
        planner = self._typed_plan()
        result = planner.recall("Acme service", _context())
        before = (list(result.admitted), list(result.ranked_admitted),
                  dict(result.recall.refusals))
        need = CoverageNeed(typed.typed_slot("Acme service", "base URL"))
        evidence = planner.observe_persisted_typed_coverage(
            result, _context(), needs=(need,),
        )
        self.assertEqual(evidence.diagnosis, "mechanical_coverage_observed")
        self.assertEqual(evidence.need_support_counts, ((need.key, 1),))
        self.assertEqual(evidence.need_support_refs, ((need.key, (kept.fact_uuid,)),))
        self.assertFalse(evidence.answer_quality_verified)
        self.assertFalse(evidence.can_admit)
        self.assertFalse(evidence.can_mutate)
        self.assertEqual(
            (list(result.admitted), list(result.ranked_admitted),
             dict(result.recall.refusals)), before,
        )

    def test_extracted_and_hedged_facts_do_not_launder_support(self) -> None:
        self._retain(
            "memory:extracted",
            "Orion client quota is 16",
            evidence_refs=("session:extracted",),
            typed_write=self._typed_write(
                "Orion client", "quota", "16", basis="extracted:test@1",
            ),
        )
        self._retain(
            "memory:hedged",
            "Orion client quota might be 24",
            evidence_refs=("session:hedged",),
            typed_write=self._typed_write(
                "Orion client", "quota", "24", flags={"hedged": True},
            ),
        )
        planner = self._typed_plan()
        result = planner.recall("Orion client quota", _context())
        need = CoverageNeed(typed.typed_slot("Orion client", "quota"))
        evidence = planner.observe_persisted_typed_coverage(
            result, _context(), needs=(need,),
        )
        self.assertEqual(evidence.need_support_counts, ((need.key, 0),))
        self.assertEqual(evidence.need_support_refs, ((need.key, ()),))
        self.assertFalse(evidence.mechanical_coverage_met)

    def test_recheck_blocks_foreign_fact_in_tampered_admitted_list(self) -> None:
        foreign = self._retain(
            "memory:foreign-typed",
            "Nebula deploy status is online",
            evidence_refs=("session:foreign",),
            project_ref="project-beta",
            typed_write=self._typed_write("Nebula deploy", "status", "online"),
        )
        planner = self._typed_plan()
        result = planner.recall("Nebula deploy status", _context())
        self.assertNotIn(foreign.fact_uuid, result.admitted)
        # Even a caller-mutated result cannot cause the observer to read
        # typed metadata from another project.
        result.recall.admitted.append(foreign.fact_uuid)
        need = CoverageNeed(typed.typed_slot("Nebula deploy", "status"))
        evidence = planner.observe_persisted_typed_coverage(
            result, _context(), needs=(need,),
        )
        self.assertEqual(evidence.admitted_count, 0)
        self.assertEqual(evidence.need_support_counts, ((need.key, 0),))
        self.assertEqual(evidence.diagnosis, "no_admitted_evidence")

    def test_persisted_coverage_rechecks_changed_context(self) -> None:
        retained = self._retain(
            "memory:context-dependent",
            "Atlas build has release channel stable",
            evidence_refs=("session:current",),
            typed_write=self._typed_write("Atlas build", "release channel", "stable"),
        )
        planner = self._typed_plan()
        result = planner.recall("Atlas build release channel", _context())
        self.assertIn(retained.fact_uuid, result.admitted)
        need = CoverageNeed(typed.typed_slot("Atlas build", "release channel"))
        downgraded = planner.observe_persisted_typed_coverage(
            result, _context("project-beta"), needs=(need,),
        )
        self.assertEqual(downgraded.admitted_count, 0)
        self.assertEqual(downgraded.need_support_refs, ((need.key, ()),))
        self.assertFalse(downgraded.mechanical_coverage_met)

    def test_persisted_support_is_distinct_facts_not_duplicate_claims(self) -> None:
        first = self._retain(
            "memory:version-1",
            "Gateway runtime version is 4",
            evidence_refs=("session:one",),
            typed_write=self._typed_write("Gateway runtime", "version", "4"),
        )
        second = self._retain(
            "memory:version-2",
            "Gateway runtime version is 4",
            evidence_refs=("session:two",),
            typed_write=self._typed_write("Gateway runtime", "version", "4"),
        )
        planner = self._typed_plan()
        result = planner.recall("Gateway runtime version", _context())
        need = CoverageNeed(typed.typed_slot("Gateway runtime", "version"), 2)
        report = planner.observe_persisted_typed_coverage(
            result, _context(), needs=(need,),
        )
        self.assertTrue(report.mechanical_coverage_met)
        self.assertEqual(report.need_support_counts, ((need.key, 2),))
        self.assertEqual(report.need_support_refs, (
            (need.key, tuple(sorted((first.fact_uuid, second.fact_uuid)))),))
        self.assertFalse(report.answer_quality_verified)

    def test_user_claimed_typed_origin_does_not_mint_persisted_support(self) -> None:
        plain = self._retain(
            "memory:plain",
            "Skylark approval window is Friday",
            evidence_refs=("session:untyped",),
        )
        planner = self._typed_plan()
        result = planner.recall("Skylark approval window", _context())
        need = CoverageNeed(typed.typed_slot("Skylark", "approval window"))
        # The older manual diagnostic accepts a caller-supplied origin, but
        # that label is not sufficient to support the governed read helper.
        claimed = result.observe_evidence_sufficiency(
            needs=(need,),
            coverage=(CoverageObservation(plain.fact_uuid,
                                          (need.key,), TYPED_OBSERVATION),),
        )
        self.assertTrue(claimed.mechanical_coverage_met)
        self.assertEqual(claimed.continuation_proposal, "continue_if_permitted")
        trusted = planner.observe_persisted_typed_coverage(
            result, _context(), needs=(need,),
        )
        self.assertEqual(trusted.admitted_count, 1)
        self.assertFalse(trusted.mechanical_coverage_met)
        self.assertEqual(trusted.need_support_refs, ((need.key, ()),))

    def test_corrupted_stored_slot_is_never_counted(self) -> None:
        retained = self._retain(
            "memory:corrupt-slot",
            "Sigma product code is 472",
            evidence_refs=("session:corruption",),
            typed_write=self._typed_write("Sigma product", "code", "472"),
        )
        planner = self._typed_plan()
        result = planner.recall("Sigma product code", _context())
        need = CoverageNeed(typed.typed_slot("Sigma product", "code"))
        stored = self.runtime.adapter.write_semantics(retained.fact_uuid, _context())
        self.assertIsNotNone(stored)
        stored["typed_proposition"]["slot"] = "typed:unrelated|property"
        with patch.object(self.runtime.adapter, "write_semantics", return_value=stored):
            report = planner.observe_persisted_typed_coverage(
                result, _context(), needs=(need,),
            )
        self.assertEqual(report.admitted_count, 1)
        self.assertFalse(report.mechanical_coverage_met)
        self.assertEqual(report.need_support_refs, ((need.key, ()),))

    def test_foreign_candidate_never_reaches_semantics_reader(self) -> None:
        foreign = self._retain(
            "memory:foreign-private",
            "Secretus rollout flag is enabled",
            evidence_refs=("session:foreign-private",),
            project_ref="project-beta",
            typed_write=self._typed_write("Secretus rollout", "flag", "enabled"),
        )
        planner = self._typed_plan()
        result = planner.recall("Secretus rollout", _context())
        result.recall.admitted.append(foreign.fact_uuid)
        need = CoverageNeed(typed.typed_slot("Secretus rollout", "flag"))
        with patch.object(self.runtime.adapter, "write_semantics",
                          wraps=self.runtime.adapter.write_semantics) as read:
            report = planner.observe_persisted_typed_coverage(
                result, _context(), needs=(need,),
            )
            read.assert_not_called()
        self.assertEqual(report.need_support_counts, ((need.key, 0),))

    def test_two_current_values_do_not_fake_single_slot_resolution(self) -> None:
        first = self._retain(
            "memory:owner-first", "Hydra service owner is Linda",
            evidence_refs=("session:owner-a",),
            typed_write=self._typed_write("Hydra service", "owner", "Linda"),
        )
        second = self._retain(
            "memory:owner-second", "Hydra service owner is Simon",
            evidence_refs=("session:owner-b",),
            typed_write=self._typed_write("Hydra service", "owner", "Simon"),
        )
        planner = self._typed_plan()
        result = planner.recall("Hydra service owner", _context())
        self.assertTrue({first.fact_uuid, second.fact_uuid}.issubset(result.admitted))
        need = CoverageNeed(typed.typed_slot("Hydra service", "owner"))
        assessment = planner.observe_persisted_typed_coverage(result, _context(), needs=(need,))
        self.assertTrue(assessment.mechanical_coverage_met)
        self.assertEqual(assessment.value_coherence[0].status, "competing_values_unresolved")
        self.assertEqual(assessment.diagnosis, "value_coherence_unresolved")
        self.assertEqual(assessment.continuation_proposal, "continue_if_permitted")
        self.assertFalse(assessment.answer_quality_verified)
        self.assertEqual(assessment.contradiction_pairs, ())

    def test_multi_value_slot_coexistence_does_not_claim_conflict(self) -> None:
        self._retain(
            "memory:tag-first", "Nimbus application tag is blue",
            evidence_refs=("session:tags-1",),
            typed_write=self._typed_write("Nimbus application", "tag", "blue",
                                         cardinality="multi"),
        )
        self._retain(
            "memory:tag-second", "Nimbus application tag is orange",
            evidence_refs=("session:tags-2",),
            typed_write=self._typed_write("Nimbus application", "tag", "orange",
                                         cardinality="multi"),
        )
        planner = self._typed_plan()
        result = planner.recall("Nimbus application tag", _context())
        need = CoverageNeed(typed.typed_slot("Nimbus application", "tag"))
        report = planner.observe_persisted_typed_coverage(result, _context(), needs=(need,))
        self.assertEqual(report.value_coherence[0].status, "coexistence_possible")
        self.assertEqual(report.diagnosis, "value_coherence_unresolved")
        self.assertEqual(report.contradiction_pairs, ())

    def test_claimed_change_is_not_equivalent_to_applied_correction(self) -> None:
        self._retain(
            "memory:change-without-apply", "Beacon API region changed to west",
            evidence_refs=("session:claimed-change",),
            typed_write=self._typed_write("Beacon API", "region", "west",
                                         assertion="change"),
        )
        planner = self._typed_plan()
        result = planner.recall("Beacon API region changed", _context())
        need = CoverageNeed(typed.typed_slot("Beacon API", "region"))
        report = planner.observe_persisted_typed_coverage(result, _context(), needs=(need,))
        self.assertEqual(report.value_coherence[0].status, "change_assertion_unresolved")
        self.assertEqual(report.diagnosis, "value_coherence_unresolved")
        self.assertEqual(report.continuation_proposal, "continue_if_permitted")

    def test_compatible_values_are_not_independent_source_proof(self) -> None:
        for idx in (1, 2):
            self._retain(
                f"memory:same-value-{idx}", "Lyra service tier is gold",
                evidence_refs=(f"session:duplicated-{idx}",),
                typed_write=self._typed_write("Lyra service", "tier", "gold"),
            )
        planner = self._typed_plan()
        result = planner.recall("Lyra service tier", _context())
        need = CoverageNeed(typed.typed_slot("Lyra service", "tier"), 2)
        report = planner.observe_persisted_typed_coverage(result, _context(), needs=(need,))
        self.assertEqual(report.value_coherence[0].status, "same_value_observed")
        self.assertEqual(len(report.value_coherence[0].fact_groups[0]), 2)
        self.assertFalse(report.answer_quality_verified)

    def test_persisted_coverage_requires_canonical_slot_identity(self) -> None:
        planner = self._typed_plan()
        result = planner.recall("unused", _context())
        for candidate in ("quota", "typed:missing-divider",
                          "typed:two||separators", "typed:|empty"):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                planner.observe_persisted_typed_coverage(
                    result, _context(), needs=(CoverageNeed(candidate),),
                )

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
