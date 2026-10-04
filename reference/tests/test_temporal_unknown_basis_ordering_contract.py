from __future__ import annotations

import json
import unittest
from pathlib import Path

from agentmem_ref.runtime import proposition_semantics as ps
from agentmem_ref.runtime import runtime_composition
from agentmem_ref.runtime import temporal_intent as ti
from agentmem_ref.state.substrate import DeterministicIds


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reference" / "fixtures" / "runtime" / "temporal-unknown-basis-ordering-v1.json"
EXPECTED_CASES = [f"M{i}" for i in range(1, 16)]


class TemporalUnknownBasisOrderingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.by_id = {case["id"].split("-", 1)[0]: case for case in cls.fixture["cases"]}

    def test_preimplementation_oracle_identity_and_boundary(self):
        self.assertEqual(self.fixture["status"], "FROZEN_PREIMPLEMENTATION_CONTRACT_REVIEWED")
        self.assertEqual(self.fixture["issue"], 584)
        self.assertEqual(self.fixture["base_sha"], "5f0e85e67a170cc633396a195a9bc4e6d2728bff")
        self.assertEqual(list(self.by_id), EXPECTED_CASES)
        self.assertEqual(len(self.fixture["cases"]), 15)
        self.assertEqual(
            self.fixture["freeze_history"]["draft_oracle_commit"],
            "f270bb1f2023d37aab64169eac880d7e8ee2dd72",
        )

        deps = self.fixture["dependencies"]
        self.assertEqual(deps["ranking_policy"], "agent-memory-post-admission-ranking/3.1.1")
        self.assertEqual(deps["temporal_interpreter"], "agent-memory-deterministic-temporal-cues/1.1.0")
        self.assertEqual(deps["write_semantics"], "agent-memory-deterministic-write-semantics/1.1.0")

        policy = runtime_composition.MULTI_ROUTE_RANKING_POLICY.identity()
        self.assertEqual(policy["policy_version"], "3.1.1")
        self.assertEqual(ti.INTERPRETER_VERSION, "1.1.0")
        self.assertEqual(ps.INTERPRETER_VERSION, "1.1.0")

    def test_ruling_invariants_are_explicit_and_non_authoritative(self):
        contract = self.fixture["contract"]
        self.assertTrue(contract["pairwise_not_global"])
        self.assertTrue(contract["global_applicable_over_unknown_tier_forbidden"])
        self.assertTrue(contract["exclusive_competition_required"])
        self.assertEqual(self.fixture["authority_effect"], "none")
        self.assertEqual(
            set(contract["activation"]["intent_basis"]),
            {ti.CALLER_DECLARED, ti.QUERY_LANGUAGE_EXPLICIT},
        )
        self.assertEqual(
            contract["forbidden_currentness_clocks"],
            ["transaction_time", "observation_time_without_validity_contract"],
        )
        self.assertEqual(
            contract["residual_fallback"],
            "stable_content_digest_then_candidate_ref_only_for_identical_content",
        )
        self.assertTrue(
            {
                "ranking != admission",
                "ranking != truth",
                "relevance != currentness",
                "unknown != stale",
                "unknown != current",
                "newer != current",
                "newer != superseding",
                "write order != semantic preference",
                "interpretation != authority",
                "conflict detection != mutation",
            }
            <= set(contract["preserved_invariants"])
        )

    def test_m1_is_real_same_slot_single_valued_change_pressure(self):
        case = self.by_id["M1"]
        intent = ti.resolve_intent(case["query"], reference_time=case["reference_time"])
        self.assertEqual(
            (intent.mode, intent.posture, intent.intent_basis, intent.orders_temporally),
            (ti.CURRENT, ti.EXPLICIT, ti.QUERY_LANGUAGE_EXPLICIT, True),
        )

        unknown = ps.interpret_write(case["memories"][0]["text"])
        applicable = ps.interpret_write(case["memories"][1]["text"])
        self.assertEqual(unknown["proposition"]["status"], ps.KNOWN)
        self.assertEqual(applicable["proposition"]["status"], ps.KNOWN)
        self.assertEqual(ps.write_slot(unknown), ps.write_slot(applicable))
        self.assertEqual(applicable["cardinality"]["class"], ps.SINGLE_VALUED)
        [relation] = ps.classify_write(
            applicable,
            "ref-new",
            case["memories"][1]["text"],
            [("ref-old", "memory:old", unknown)],
        )
        self.assertEqual(relation["classification"], ps.STATE_CHANGE_CANDIDATE)
        self.assertEqual(case["expect"]["precedes"], ["applicable", "unknown"])
        self.assertTrue(case["expect"]["unknown_label_preserved"])

    def test_m3_same_slot_unknown_cardinality_cannot_invent_exclusivity(self):
        case = self.by_id["M3"]
        first = ps.interpret_write(case["memories"][0]["text"])
        second = ps.interpret_write(case["memories"][1]["text"])
        self.assertEqual(first["proposition"]["status"], ps.KNOWN)
        self.assertEqual(second["proposition"]["status"], ps.KNOWN)
        self.assertEqual(ps.write_slot(first), ps.write_slot(second))
        self.assertEqual(first["cardinality"]["class"], ps.UNKNOWN)
        self.assertEqual(second["cardinality"]["class"], ps.UNKNOWN)
        [relation] = ps.classify_write(
            second,
            "ref-new",
            case["memories"][1]["text"],
            [("ref-old", "memory:old", first)],
        )
        self.assertEqual((relation["classification"], relation["basis"]), (ps.UNRESOLVED, "cardinality_unknown"))
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertEqual(case["expect"]["constraint_refusal_reason"], "exclusive_relation_not_established")

    def test_m4_multivalued_evidence_is_a_hard_negative_control(self):
        case = self.by_id["M4"]
        existing = ps.interpret_write(case["memories"][0]["text"])
        added = ps.interpret_write(case["memories"][1]["text"])
        self.assertEqual(ps.write_slot(existing), ps.write_slot(added))
        self.assertEqual(added["cardinality"]["class"], ps.MULTI_VALUED)
        [relation] = ps.classify_write(
            added,
            "ref-new",
            case["memories"][1]["text"],
            [("ref-old", "memory:old", existing)],
        )
        self.assertEqual(relation["classification"], ps.COEXISTENCE)
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertEqual(case["expect"]["constraint_refusal_reason"], "coexistence_or_multivalued")

    def test_m5_refuses_hierarchy_claim_when_positive_evidence_is_not_established(self):
        case = self.by_id["M5"]
        self.assertTrue(case["preconditions"]["positive_hierarchical_evidence_required"])
        self.assertTrue(case["preconditions"]["current_interpreter_positive_hierarchy_not_assumed"])
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertTrue(case["expect"]["no_invented_single_valued_semantics"])
        self.assertIn(ps.HIERARCHICAL, ps.CARDINALITIES)

    def test_m6_and_m7_really_run_under_explicit_current_intent(self):
        for name in ("M6", "M7"):
            case = self.by_id[name]
            intent = ti.resolve_intent(
                case["query"],
                case["temporal_intent"],
                reference_time=case["reference_time"],
            )
            self.assertEqual(
                (intent.mode, intent.posture, intent.intent_basis, intent.orders_temporally),
                (ti.CURRENT, ti.EXPLICIT, ti.CALLER_DECLARED, True),
                name,
            )
            self.assertEqual(case["expect"]["intent_basis"], ti.CALLER_DECLARED)

    def test_m7_proves_candidate_ref_digest_is_not_write_order_neutral(self):
        case = self.by_id["M7"]
        variants = case["variants"]

        def allocated_by_key(memories: list[dict]) -> dict[str, str]:
            ids = DeterministicIds("ref")
            return {memory["key"]: ids.next() for memory in memories}

        first = allocated_by_key(variants[0]["memories"])
        reversed_order = allocated_by_key(variants[1]["memories"])
        self.assertNotEqual(first["denver"], reversed_order["denver"])
        self.assertNotEqual(first["boston"], reversed_order["boston"])
        self.assertEqual(case["preconditions"]["candidate_ref_allocation"], "counter_based_write_order")
        self.assertTrue(case["preconditions"]["candidate_ref_digest_is_not_content_stable"])
        self.assertTrue(case["expect"]["same_semantic_order_across_write_order_variants"])
        self.assertEqual(case["expect"]["fallback"], "stable_content_digest")
        self.assertTrue(case["expect"]["candidate_ref_digest_only_for_identical_content"])

    def test_m10_is_atemporal_and_therefore_outside_584_activation(self):
        case = self.by_id["M10"]
        intent = ti.resolve_intent(case["query"], reference_time=case["reference_time"])
        self.assertEqual((intent.mode, intent.posture, intent.intent_basis), (ti.ATEMPORAL, ti.UNSPECIFIED, ti.NO_BASIS))
        self.assertFalse(intent.orders_temporally)
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertTrue(case["expect"]["byte_identical_to_base_ranking_policy"])

    def test_m11_binds_both_explicit_bases_without_equating_authority(self):
        case = self.by_id["M11"]
        query_variant = case["query_language_variant"]
        caller_variant = case["caller_declared_variant"]
        query_intent = ti.resolve_intent(query_variant["query"], reference_time=case["reference_time"])
        caller_intent = ti.resolve_intent(
            caller_variant["query"],
            caller_variant["temporal_intent"],
            reference_time=case["reference_time"],
        )
        self.assertEqual((query_intent.posture, query_intent.intent_basis), (ti.EXPLICIT, ti.QUERY_LANGUAGE_EXPLICIT))
        self.assertEqual((caller_intent.posture, caller_intent.intent_basis), (ti.EXPLICIT, ti.CALLER_DECLARED))
        self.assertTrue(case["expect"]["same_pairwise_ranking_semantics"])
        self.assertFalse(case["expect"]["admission_authority_equivalence"])

    def test_m12_pins_high_confidence_inferred_current_outside_first_profile(self):
        case = self.by_id["M12"]
        intent = ti.resolve_intent(case["query"], reference_time=case["reference_time"])
        self.assertEqual(
            (intent.mode, intent.posture, intent.confidence, intent.intent_basis, intent.orders_temporally),
            (ti.CURRENT, ti.INFERRED, ti.HIGH, ti.QUERY_CUE_INFERENCE, True),
        )
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertEqual(case["expect"]["constraint_refusal_reason"], "current_intent_not_explicit")

    def test_m13_is_explicit_cycle_refusal_not_a_natural_language_claim(self):
        case = self.by_id["M13"]
        self.assertEqual(case["fixture_kind"], "policy_graph_negative_control")
        constraints = {tuple(edge) for edge in case["proposed_constraints"]}
        self.assertEqual(constraints, {("a", "b"), ("b", "c"), ("c", "a")})
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertTrue(case["expect"]["preserve_base_order"])
        self.assertTrue(case["expect"]["recency_cycle_break_forbidden"])

    def test_m14_conflict_relation_is_positive_exclusive_evidence(self):
        case = self.by_id["M14"]
        unknown = ps.interpret_write(case["memories"][0]["text"])
        applicable = ps.interpret_write(case["memories"][1]["text"])
        self.assertEqual(ps.write_slot(unknown), ps.write_slot(applicable))
        self.assertEqual(unknown["cardinality"]["class"], ps.SINGLE_VALUED)
        self.assertEqual(applicable["cardinality"]["class"], ps.UNKNOWN)
        [relation] = ps.classify_write(
            applicable,
            "ref-new",
            case["memories"][1]["text"],
            [("ref-old", "memory:old", unknown)],
        )
        self.assertEqual(
            (relation["classification"], relation["basis"]),
            (ps.CONFLICT, "single_valued_without_change_evidence"),
        )
        self.assertTrue(case["expect"]["constraint_applied"])

    def test_m15_untrusted_self_claim_downgrades_change_relation(self):
        case = self.by_id["M15"]
        unknown = ps.interpret_write(case["memories"][0]["text"])
        claimed = ps.interpret_write(case["memories"][1]["text"])
        self.assertIn("untrusted_self_claim", claimed["proposal_ineligible_reasons"])
        [relation] = ps.classify_write(
            claimed,
            "ref-new",
            case["memories"][1]["text"],
            [("ref-old", "memory:old", unknown)],
        )
        self.assertEqual(relation["classification"], ps.UNRESOLVED)
        self.assertTrue(relation["basis"].startswith("change_evidence_not_proposable:untrusted_self_claim"))
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertTrue(case["expect"]["no_authority_from_self_claim"])


if __name__ == "__main__":
    unittest.main()
