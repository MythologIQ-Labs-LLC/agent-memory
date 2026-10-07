from __future__ import annotations

from dataclasses import asdict
import math
import tempfile
import unittest

from agentmem_ref import AgentMemory
from agentmem_ref.runtime.recall_control import (
    ADAPTIVE_ABLATION_PROFILES,
    AdaptiveControlDecision,
    ControllerDecisionCache,
    DeterministicAdaptiveRecallController,
    EvidenceAssessment,
    RecallOuterBudget,
    RecallRouteBudget,
    RecallRouteNeed,
    adaptive_cache_key,
    allocate_route_budgets,
    assess_evidence,
    estimate_route_needs,
    stop_recommendation,
)
from agentmem_ref.runtime.runtime_composition import (
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
)
from agentmem_ref.runtime.vector_retrieval import SEMANTIC_VECTOR_ROUTE


class AdaptiveRecallControlTests(unittest.TestCase):
    def test_route_needs_are_boundary_valued_and_only_for_available_routes(self) -> None:
        needs = estimate_route_needs(
            "Where is the pottery class?",
            logical_memory_refs=("memory:pottery",),
            available_routes=(LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE, SEMANTIC_VECTOR_ROUTE),
        )
        self.assertEqual(
            [(item.route_id, item.probability) for item in needs],
            [
                (EXACT_IDENTITY_ROUTE, 1.0),
                (LEXICAL_ROUTE, 1.0),
                (SEMANTIC_VECTOR_ROUTE, 1.0),
            ],
        )
        self.assertTrue(all(item.authority_effect == "none" for item in needs))

    def test_route_need_refuses_unknown_host_capability(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported routes"):
            estimate_route_needs(
                "anything",
                logical_memory_refs=(),
                available_routes=("invented-route",),
            )

    def test_probability_fields_refuse_nan_and_out_of_range(self) -> None:
        for value in (math.nan, math.inf, -0.01, 1.01):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    RecallRouteNeed(LEXICAL_ROUTE, value)
        with self.assertRaises(ValueError):
            EvidenceAssessment(1.0, 0.0, 0.0, math.nan)


    def test_route_budget_rejects_malformed_work_bounds(self) -> None:
        for args in (
            ("", 1, 0),
            (LEXICAL_ROUTE, 1.5, 0),
            (LEXICAL_ROUTE, 1, True),
            (LEXICAL_ROUTE, 1, 2),
        ):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    RecallRouteBudget(*args)

    def test_adaptive_decision_requires_one_budget_per_route_need(self) -> None:
        need = RecallRouteNeed(LEXICAL_ROUTE, 1.0)
        assessment = EvidenceAssessment(0.0, 1.0, 1.0, 0.0)
        with self.assertRaisesRegex(ValueError, "match route needs"):
            AdaptiveControlDecision(
                route_needs=(need,),
                route_budgets=(),
                assessment=assessment,
                stop_recommendation="continue_retrieval",
            )
        with self.assertRaisesRegex(ValueError, "duplicate route budgets"):
            AdaptiveControlDecision(
                route_needs=(need,),
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, 1),
                    RecallRouteBudget(LEXICAL_ROUTE, 1),
                ),
                assessment=assessment,
                stop_recommendation="continue_retrieval",
            )

    def test_allocation_is_deterministic_across_need_input_order(self) -> None:
        needs = (
            RecallRouteNeed(LEXICAL_ROUTE, 1.0),
            RecallRouteNeed(EXACT_IDENTITY_ROUTE, 1.0),
            RecallRouteNeed(SEMANTIC_VECTOR_ROUTE, 1.0),
            RecallRouteNeed(SHARED_EVIDENCE_ROUTE, 1.0),
        )
        kwargs = {
            "outer_budget": RecallOuterBudget(maximum_candidates=11),
            "host_caps": {
                LEXICAL_ROUTE: 32,
                EXACT_IDENTITY_ROUTE: 16,
                SEMANTIC_VECTOR_ROUTE: 16,
                SHARED_EVIDENCE_ROUTE: 24,
            },
        }
        first = allocate_route_budgets(needs, **kwargs)
        second = allocate_route_budgets(tuple(reversed(needs)), **kwargs)
        self.assertEqual(first, second)
        self.assertEqual(sum(item.candidate_limit for item in first), 11)

    def test_allocation_never_exceeds_outer_or_host_caps(self) -> None:
        needs = (
            RecallRouteNeed(LEXICAL_ROUTE, 1.0),
            RecallRouteNeed(EXACT_IDENTITY_ROUTE, 1.0),
            RecallRouteNeed(SEMANTIC_VECTOR_ROUTE, 1.0),
        )
        caps = {LEXICAL_ROUTE: 2, EXACT_IDENTITY_ROUTE: 1, SEMANTIC_VECTOR_ROUTE: 3}
        budgets = allocate_route_budgets(
            needs,
            outer_budget=RecallOuterBudget(maximum_candidates=100),
            host_caps=caps,
        )
        self.assertEqual(sum(item.candidate_limit for item in budgets), sum(caps.values()))
        for item in budgets:
            self.assertLessEqual(item.candidate_limit, caps[item.route_id])

    def test_zero_outer_budget_allocates_no_work(self) -> None:
        budgets = allocate_route_budgets(
            (RecallRouteNeed(LEXICAL_ROUTE, 1.0),),
            outer_budget=RecallOuterBudget(maximum_candidates=0),
            host_caps={LEXICAL_ROUTE: 32},
        )
        self.assertEqual(budgets[0].candidate_limit, 0)


    def test_zero_controller_decisions_is_a_valid_disabled_outer_budget(self) -> None:
        budget = RecallOuterBudget(maximum_controller_decisions=0, maximum_candidates=0)
        self.assertEqual(budget.maximum_controller_decisions, 0)
        self.assertEqual(budget.maximum_candidates, 0)


    def test_zero_controller_decision_budget_cannot_be_spent(self) -> None:
        controller = DeterministicAdaptiveRecallController()
        with self.assertRaisesRegex(ValueError, "decision budget exhausted"):
            controller.decide(
                "pottery class",
                logical_memory_refs=(),
                available_routes=(LEXICAL_ROUTE,),
                outer_budget=RecallOuterBudget(
                    maximum_controller_decisions=0,
                    maximum_candidates=8,
                ),
                host_caps={LEXICAL_ROUTE: 32},
            )

    def test_outer_and_host_work_budgets_require_integers(self) -> None:
        invalid_outer = (
            {"maximum_controller_decisions": 1.5},
            {"maximum_candidates": 1.5},
            {"deadline_ms": 1.5},
            {"maximum_nodes": True},
        )
        for kwargs in invalid_outer:
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, "integer"):
                    RecallOuterBudget(**kwargs)

        with self.assertRaisesRegex(ValueError, "integer"):
            allocate_route_budgets(
                (RecallRouteNeed(LEXICAL_ROUTE, 1.0),),
                outer_budget=RecallOuterBudget(maximum_candidates=4),
                host_caps={LEXICAL_ROUTE: 2.5},
            )

    def test_host_cap_is_required_for_every_route_need(self) -> None:
        with self.assertRaisesRegex(ValueError, "no host cap"):
            allocate_route_budgets(
                (RecallRouteNeed(LEXICAL_ROUTE, 1.0),),
                outer_budget=RecallOuterBudget(maximum_candidates=5),
                host_caps={},
            )

    def test_candidate_quantity_alone_is_not_sufficiency(self) -> None:
        assessment = assess_evidence(
            candidate_count=50,
            exact_identity_count=0,
            corroborated_count=0,
            routes_remaining=2,
        )
        self.assertEqual(assessment.evidence_sufficient, 0.0)
        self.assertEqual(assessment.continue_useful, 1.0)
        self.assertEqual(stop_recommendation(assessment, routes_remaining=2, resource_exhausted=False),
                         "continue_retrieval")

    def test_identity_or_independent_corroboration_can_satisfy(self) -> None:
        identity = assess_evidence(
            candidate_count=1,
            exact_identity_count=1,
            routes_remaining=3,
        )
        corroborated = assess_evidence(
            candidate_count=2,
            corroborated_count=1,
            routes_remaining=1,
        )
        self.assertEqual(identity.evidence_sufficient, 1.0)
        self.assertEqual(corroborated.evidence_sufficient, 1.0)
        self.assertEqual(stop_recommendation(identity, routes_remaining=3, resource_exhausted=False),
                         "evidence_sufficient")

    def test_resource_exhaustion_never_becomes_sufficiency(self) -> None:
        assessment = assess_evidence(
            candidate_count=0,
            routes_remaining=4,
            resource_exhausted=True,
        )
        self.assertEqual(assessment.evidence_sufficient, 0.0)
        self.assertEqual(assessment.continue_useful, 0.0)
        self.assertIn("resource_exhausted", assessment.basis)
        self.assertEqual(stop_recommendation(assessment, routes_remaining=4, resource_exhausted=True),
                         "budget_exhausted")

    def test_contradiction_is_independent_of_sufficiency(self) -> None:
        assessment = assess_evidence(
            candidate_count=2,
            exact_identity_count=1,
            contradiction_detected=True,
            routes_remaining=1,
        )
        self.assertEqual(assessment.evidence_sufficient, 1.0)
        self.assertEqual(assessment.contradiction, 1.0)
        self.assertIn("contradiction_detected", assessment.basis)

    def test_frontier_exhaustion_stays_distinct_from_resource_exhaustion(self) -> None:
        assessment = assess_evidence(candidate_count=0, routes_remaining=0)
        self.assertEqual(
            stop_recommendation(assessment, routes_remaining=0, resource_exhausted=False),
            "frontier_exhausted",
        )

    def test_cache_key_binds_contract_backend_policy_and_isolation(self) -> None:
        base = dict(
            operation="retrieval_planning",
            canonical_request_state={"query": "pottery", "routes": ["lexical"]},
            controller_contract_version="1.0.0",
            backend_ref="agent-memory:deterministic-recall-controller",
            backend_version="2.0.0",
            model_or_policy_ref="deterministic-adaptive-rule-policy",
            host_policy_version="3.3.0",
            isolation_namespace="tenant:a/project:a",
        )
        original = adaptive_cache_key(**base)
        for field, value in (
            ("controller_contract_version", "1.1.0"),
            ("backend_version", "2.1.0"),
            ("host_policy_version", "3.4.0"),
            ("isolation_namespace", "tenant:b/project:a"),
        ):
            changed = dict(base)
            changed[field] = value
            self.assertNotEqual(original, adaptive_cache_key(**changed), field)

    def test_cache_is_process_local_and_derives_identity_bound_keys(self) -> None:
        controller = DeterministicAdaptiveRecallController()
        decision = controller.decide(
            "pottery class",
            logical_memory_refs=(),
            available_routes=(LEXICAL_ROUTE,),
            outer_budget=RecallOuterBudget(maximum_candidates=8),
            host_caps={LEXICAL_ROUTE: 32},
            routes_remaining=1,
        )
        identity = {
            "operation": "retrieval_planning",
            "canonical_request_state": {"query": "pottery class"},
            "controller_contract_version": "1.0.0",
            "backend_ref": decision.controller_ref,
            "backend_version": decision.controller_version,
            "model_or_policy_ref": "deterministic-adaptive-rule-policy",
            "host_policy_version": "3.3.0",
            "isolation_namespace": "tenant:a/project:a",
        }
        cache = ControllerDecisionCache()
        key = cache.put(decision, **identity)
        self.assertEqual(key, adaptive_cache_key(**identity))
        self.assertIs(cache.get(**identity), decision)
        self.assertEqual(len(cache), 1)

        other_scope = dict(identity)
        other_scope["isolation_namespace"] = "tenant:b/project:a"
        self.assertIsNone(cache.get(**other_scope))


    def test_cache_hits_do_not_mutate_canonical_memory(self) -> None:
        with AgentMemory.open(tempfile.mkdtemp(), tenant="tenant:cache-proof") as memory:
            committed = memory.remember(
                "memory:cache-proof",
                "The pottery class is on Thursday.",
            )
            substrate = memory.runtime.adapter.checkpoint_substrate()
            before_facts = tuple(asdict(fact) for fact in substrate.all_facts())
            before_state = memory.runtime.adapter.state_version("memory:cache-proof")

            decision = DeterministicAdaptiveRecallController().decide(
                "When is the pottery class?",
                logical_memory_refs=("memory:cache-proof",),
                available_routes=(LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE),
                outer_budget=RecallOuterBudget(maximum_candidates=8),
                host_caps={LEXICAL_ROUTE: 32, EXACT_IDENTITY_ROUTE: 16},
                routes_remaining=2,
            )
            identity = {
                "operation": "retrieval_planning",
                "canonical_request_state": {
                    "query": "When is the pottery class?",
                    "logical_memory_refs": ["memory:cache-proof"],
                },
                "controller_contract_version": "1.0.0",
                "backend_ref": decision.controller_ref,
                "backend_version": decision.controller_version,
                "model_or_policy_ref": "deterministic-adaptive-rule-policy",
                "host_policy_version": "3.3.0",
                "isolation_namespace": "tenant:cache-proof/default",
            }
            cache = ControllerDecisionCache()
            cache.put(decision, **identity)
            self.assertIs(cache.get(**identity), decision)

            after_facts = tuple(asdict(fact) for fact in substrate.all_facts())
            after_state = memory.runtime.adapter.state_version("memory:cache-proof")
            self.assertEqual(after_facts, before_facts)
            self.assertEqual(after_state, before_state)
            self.assertEqual(
                memory.runtime.adapter.current_fact_uuid("memory:cache-proof"),
                committed["fact_uuid"],
            )

    def test_all_mandatory_ablation_profiles_are_executable(self) -> None:
        controller = DeterministicAdaptiveRecallController()
        for profile in ADAPTIVE_ABLATION_PROFILES:
            with self.subTest(profile=profile):
                decision = controller.decide(
                    "pottery class",
                    logical_memory_refs=("memory:pottery",),
                    available_routes=(LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE),
                    outer_budget=RecallOuterBudget(maximum_candidates=8),
                    host_caps={LEXICAL_ROUTE: 32, EXACT_IDENTITY_ROUTE: 16},
                    routes_remaining=2,
                    ablation_profile=profile,
                )
                self.assertEqual(decision.ablation_profile, profile)
                self.assertEqual(decision.authority_effect, "none")
                if profile in ("controller_off", "adaptive_routing_only", "adaptive_budgeting_only"):
                    self.assertEqual(decision.stop_recommendation, "abstain")

    def test_decision_projection_preserves_frozen_evidence_vocabulary(self) -> None:
        decision = DeterministicAdaptiveRecallController().decide(
            "pottery class",
            logical_memory_refs=("memory:pottery",),
            available_routes=(LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE),
            outer_budget=RecallOuterBudget(maximum_candidates=5),
            host_caps={LEXICAL_ROUTE: 32, EXACT_IDENTITY_ROUTE: 16},
            candidate_count=1,
            exact_identity_count=1,
            routes_remaining=1,
        )
        projected = decision.to_dict()
        self.assertEqual(projected["authority_effect"], "none")
        self.assertEqual(
            set(projected["evidence_assessment"]),
            {
                "evidence_sufficient",
                "continue_useful",
                "missing_evidence",
                "contradiction",
                "basis",
                "authority_effect",
            },
        )
        self.assertIn(projected["stop_recommendation"], {
            "evidence_sufficient",
            "further_retrieval_unhelpful",
            "continue_retrieval",
            "budget_exhausted",
            "frontier_exhausted",
            "controller_unavailable",
            "abstain",
        })
        # Slice 2A is typed controller evidence, not the full System-One wire exchange.
        self.assertNotIn("decision_status", projected)
        self.assertNotIn("usage", projected)
        self.assertNotIn("actual_stop", projected)


if __name__ == "__main__":
    unittest.main()
