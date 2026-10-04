from __future__ import annotations

import json
import unittest
from pathlib import Path

from agentmem_ref.runtime.recall_control import (
    RecallControlPlan,
    RecallRouteBudget,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reference" / "fixtures" / "runtime" / "system-one-controller-contract-v1.json"


class SystemOneControllerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_identity_and_frozen_ancestry(self):
        self.assertEqual(self.contract["contract_id"], "agent-memory-system-one-controller-v1")
        self.assertEqual(self.contract["version"], "1.0.0")
        self.assertEqual(self.contract["status"], "FROZEN_PREIMPLEMENTATION_CONTRACT")
        self.assertEqual(self.contract["issue"], 644)
        ancestry = self.contract["ancestry"]
        self.assertEqual(ancestry["system"], "Jev-Mem")
        self.assertEqual(ancestry["repository"], "libingzheren/Jev-Mem")
        self.assertEqual(ancestry["revision"], "7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44")
        self.assertEqual(ancestry["license"], "MIT")
        self.assertEqual(ancestry["relationship"], "implementation_ancestry_not_runtime_dependency")
        self.assertEqual(self.contract["authority_effect"], "none")

    def test_existing_recall_control_plan_already_obeys_non_authority_boundary(self):
        plan = RecallControlPlan(
            controller_ref="fixture-controller",
            controller_version="1",
            route_budgets=(RecallRouteBudget("lexical", 8),),
            reason_codes=("query_has_content_terms",),
        )
        self.assertEqual(plan.authority_effect, "none")
        projected = plan.to_dict()
        self.assertEqual(projected["authority_effect"], "none")
        self.assertEqual(projected["route_budgets"][0]["route_id"], "lexical")
        self.assertEqual(projected["route_budgets"][0]["candidate_limit"], 8)

    def test_controller_permissions_are_strictly_estimator_side(self):
        enforcement = self.contract["host_enforcement"]
        allowed = set(enforcement["controller_may_estimate_or_propose"])
        forbidden = set(enforcement["controller_may_not_own"])
        self.assertIn("retrieval routes", allowed)
        self.assertIn("search budget", allowed)
        self.assertIn("evidence sufficiency", allowed)
        self.assertIn("stop recommendation", allowed)
        self.assertIn("recall admission", forbidden)
        self.assertIn("durable commit", forbidden)
        self.assertIn("supersession", forbidden)
        self.assertIn("deletion or tombstone authority", forbidden)
        self.assertIn("truth", forbidden)
        self.assertIn("currentness authority", forbidden)
        self.assertFalse(allowed & forbidden)

    def test_route_need_and_budget_outputs_cannot_create_capabilities(self):
        request = self.contract["request"]
        response = self.contract["response"]["evidence"]
        self.assertIn("available_capabilities", request["required"])
        self.assertIn("route_needs", response)
        self.assertIn("route_budgets", response)
        self.assertIn("cannot activate a route", request["available_capabilities"]["semantics"])
        self.assertIn("host-provided outer budget", response["route_budgets"]["semantics"])

    def test_sufficiency_is_not_resource_exhaustion(self):
        assessment = self.contract["response"]["evidence"]["evidence_assessment"]
        self.assertEqual(
            set(assessment["fields"]),
            {"evidence_sufficient", "continue_useful", "missing_evidence", "contradiction"},
        )
        stop = self.contract["actual_stop_record"]
        quality = set(stop["reason_classes"]["quality"])
        resource = set(stop["reason_classes"]["resource"])
        failure = set(stop["reason_classes"]["controller_failure"])
        self.assertIn("evidence_sufficient", quality)
        self.assertIn("max_latency", resource)
        self.assertIn("max_controller_decisions", resource)
        self.assertIn("controller_unavailable", failure)
        self.assertFalse(quality & resource)
        self.assertFalse(quality & failure)
        self.assertFalse(resource & failure)
        self.assertIn("remain distinct", stop["invariant"])

    def test_controller_budget_owns_provider_retry_and_followup_work(self):
        budget = self.contract["request"]["budget"]
        self.assertEqual(
            budget["required"],
            ["maximum_controller_decisions", "deadline_ms"],
        )
        self.assertIn("Provider retries", budget["rule"])
        self.assertIn("outer request budget", budget["rule"])
        self.assertIn("never reported as evidence sufficiency", budget["rule"])

    def test_typed_candidate_factors_do_not_define_a_universal_scalar(self):
        candidate = self.contract["response"]["evidence"]["candidate_estimates"]
        self.assertEqual(
            candidate["typed_factors"],
            [
                "relevance",
                "relation_usefulness",
                "novelty",
                "corroboration",
                "requirement_coverage",
            ],
        )
        self.assertEqual(candidate["forbidden_implicit_factor"], "recency_as_currentness_or_authority")
        self.assertIn("No mandatory universal weighted scalar", candidate["semantics"])

    def test_consolidation_is_proposal_evidence_not_mutation_authority(self):
        consolidation = self.contract["response"]["evidence"]["consolidation_estimates"]
        self.assertEqual(
            consolidation["representation_choice_enum"],
            ["keep_separate", "merge", "promote", "uncertain"],
        )
        self.assertIn("does not authorize supersession", consolidation["semantics"])
        self.assertIn("does not authorize destructive rewrite", consolidation["semantics"])

    def test_consumer_profile_is_reserved_without_collapsing_truth_or_admission(self):
        profile = self.contract["request"]["consumer_profile"]
        self.assertEqual(profile["status"], "optional_v1_input_reserved_for_consumer_aware_delivery")
        self.assertIn("available_context_tokens", profile["fields"])
        self.assertIn("memory_package_tokens", profile["fields"])
        self.assertIn("supports_progressive_expansion", profile["fields"])
        self.assertIn("consumer capacity != truth", profile["invariants"])
        self.assertIn("consumer budget != recall admission", profile["invariants"])
        self.assertIn("omitted from package != forgotten", profile["invariants"])

    def test_cache_identity_is_version_and_scope_bound(self):
        cache = self.contract["cache_identity"]
        required = set(cache["must_bind"])
        self.assertIn("controller contract version", required)
        self.assertIn("backend identity", required)
        self.assertIn("model or policy identity", required)
        self.assertIn("relevant host policy version", required)
        self.assertIn("tenant or isolation namespace where state is scope-sensitive", required)
        self.assertIn("never authority", cache["rule"])

    def test_ablation_matrix_keeps_governance_separate(self):
        evaluation = self.contract["evaluation"]
        self.assertEqual(
            evaluation["mandatory_ablations"],
            [
                "controller_off",
                "adaptive_routing_only",
                "adaptive_budgeting_only",
                "adaptive_stopping_only",
                "combined_controller",
            ],
        )
        self.assertIn("governance violations or refusals", evaluation["report_separately"])
        self.assertIn("No single aggregate score", evaluation["forbidden_claim"])

    def test_load_bearing_invariants_are_explicit(self):
        invariants = set(self.contract["invariants"])
        self.assertTrue(
            {
                "controller output != truth",
                "controller confidence != permission",
                "routing != recall admission",
                "ranking != recall admission",
                "recency != currentness",
                "stop recommendation != actual stop reason",
                "stopping because sufficient != stopping because budget exhausted",
                "consumer capacity != truth",
                "benchmark score != authority",
            }
            <= invariants
        )


if __name__ == "__main__":
    unittest.main()
