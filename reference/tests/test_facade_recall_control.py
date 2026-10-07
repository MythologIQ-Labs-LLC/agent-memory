"""Shadow recall control through the facade (#644 T-controller, docs/plan-644-t-controller.md).

The controller plans beside the unchanged default planner. Retrieval, admission and ranking
are identical with ``recall_control="off"`` and ``"shadow"`` (S1); shadow only adds a
``recall_control`` report in the frozen System-One controller contract's vocabulary (S3),
whose stop record describes what the default planner actually did.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api import surface  # noqa: E402
from agentmem_ref.runtime import representation_onnx  # noqa: E402
from agentmem_ref.runtime.recall_control import (  # noqa: E402
    ControlledRecallPlanner,
    DeterministicRecallController,
    RecallControlPlan,
    shadow_actual_stop,
    shadow_control_report,
)
from agentmem_ref.runtime.vector_retrieval import SEMANTIC_VECTOR_ROUTE, VectorRepresentationSpec  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((REPO_ROOT / "reference/fixtures/runtime/system-one-controller-contract-v1.json").read_text(encoding="utf-8"))


class _ConstantProvider:
    """Every text embeds to the same direction, so every eligible fact clears the threshold."""

    spec = VectorRepresentationSpec(
        representation_ref="agent-memory:test-constant",
        representation_version="1.0.0",
        config_digest="sha256:" + "ab" * 32,
        dimensions=3,
        deterministic_rebuild=True,
    )

    def __init__(self, model_dir=None) -> None:
        pass

    def embed(self, text: str) -> tuple[float, ...]:
        return (0.6, 0.8, 0.0)


def _seed_adversarial(memory: AgentMemory) -> None:
    # S1 adversarial corpus: more than 32 lexical hits for one query, a newer fact among
    # older strong lexical matches, and an out-of-scope domain that must stay invisible.
    for index in range(40):
        memory.remember(f"memory:budget:{index}", f"The quarterly budget review number {index} discussed the budget.")
    memory.remember("memory:budget:current", "The budget is now final.")
    domains = [memory.tenant, "project:other"]
    memory.remember(
        "memory:foreign",
        "The budget of the other project is secret.",
        overrides={"scope": "project:other", "project_ref": "project:other",
                   "isolation_domain_refs": domains, "required_isolation_domain_refs": domains},
    )


def _retrieval(result: dict) -> dict:
    return {key: value for key, value in result.items() if key != "recall_control"}


class FacadeShadowRecallControlTests(unittest.TestCase):
    def _recall_both(self, seed, queries, **open_kwargs):
        # Two byte-identical copies of one seeded store, so audit sequence numbers and the
        # deterministic clock advance identically in both modes.
        root = Path(tempfile.mkdtemp()) / "seeded"
        with AgentMemory.open(root, **open_kwargs) as memory:
            seed(memory)
        outputs = {}
        for mode in ("off", "shadow"):
            copy = Path(tempfile.mkdtemp()) / mode
            shutil.copytree(root, copy)
            with AgentMemory.open(copy, recall_control=mode, **open_kwargs) as memory:
                outputs[mode] = [memory.recall(query, **kwargs) for query, kwargs in queries]
        return outputs

    def test_default_is_off_and_adds_nothing(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            memory.remember("memory:a", "The user's dog is called Biscuit.")
            result = memory.recall("What is the dog called?")
        self.assertNotIn("recall_control", result)
        self.assertEqual(result["contract_version"], "1.5.0")
        with self.assertRaises(ValueError):
            AgentMemory.open(tempfile.mkdtemp(), recall_control="deterministic")

    def test_shadow_retrieval_is_identical_to_off_on_the_adversarial_corpus(self):
        queries = [
            ("What is the budget now?", {}),
            ("What is the budget now?", {"temporal_intent": {"mode": "current"}}),
            ("quarterly budget review", {"logical_memory_refs": ["memory:budget:3"]}),
            ("budget", {"budget": 5}),
            ("nothing matches this zebra", {}),
        ]
        outputs = self._recall_both(_seed_adversarial, queries)
        for off, shadow in zip(outputs["off"], outputs["shadow"]):
            self.assertNotIn("recall_control", off)
            self.assertIn("recall_control", shadow)
            self.assertEqual(json.dumps(_retrieval(off), sort_keys=True), json.dumps(_retrieval(shadow), sort_keys=True))
        lexical_heavy = outputs["shadow"][0]
        self.assertGreater(lexical_heavy["recall_control"]["route_candidate_counts"]["lexical"], 32)
        self.assertTrue(lexical_heavy["recall_control"]["shadow_delta"]["lexical"]["would_truncate"])

    def test_shadow_report_conforms_to_the_frozen_controller_contract(self):
        outputs = self._recall_both(_seed_adversarial, [("What is the budget now?", {})])
        report = outputs["shadow"][0]["recall_control"]
        request, response = CONTRACT["request"], CONTRACT["response"]
        self.assertTrue(set(request["required"]) - {"query_or_observation"} <= set(report["request"]))
        self.assertTrue(set(request["budget"]["required"]) <= set(report["request"]["budget"]))
        self.assertTrue(set(request["policy_context"]["required"]) <= set(report["request"]["policy_context"]))
        self.assertTrue(set(response["required"]) - {"usage"} <= set(report["response"]))
        self.assertTrue(set(response["controller_identity"]["required"]) <= set(report["response"]["controller_identity"]))
        self.assertIn(report["response"]["decision_status"], response["decision_status_enum"])
        self.assertIn(report["response"]["evidence"]["stop_recommendation"], response["evidence"]["stop_recommendation"]["enum"])
        self.assertTrue(set(response["usage"]["required"]) <= set(report["usage"]))
        stop = report["actual_stop"]
        self.assertTrue(set(CONTRACT["actual_stop_record"]["required"]) <= set(stop))
        classes = CONTRACT["actual_stop_record"]["reason_classes"]
        self.assertIn(stop["actual_stop_reason"], classes[stop["stop_class"]])
        self.assertNotIn(stop["actual_stop_reason"], classes["quality"])
        self.assertEqual((report["authority_effect"], report["response"]["authority_effect"]), ("none", "none"))

    def test_route_counts_are_caller_visible_only(self):
        outputs = self._recall_both(_seed_adversarial, [("secret budget of the other project", {})])
        shadow = outputs["shadow"][0]
        self.assertEqual(sum(shadow["recall_control"]["route_candidate_counts"].values()) >= 0, True)
        self.assertEqual(shadow["recall_control"]["route_candidate_counts"]["lexical"],
                         sum(1 for ref in shadow["candidates"]
                             if any(hit["route_id"] == "lexical" for hit in shadow["admissions"][ref]["route_provenance"])))
        foreign_text = [ref for ref, decision in shadow["admissions"].items() if "secret" in json.dumps(decision)]
        self.assertEqual(foreign_text, [])

    def test_stop_record_follows_the_default_planner(self):
        outputs = self._recall_both(_seed_adversarial, [("nothing matches this zebra", {}), ("What is the budget now?", {})])
        empty, found = (item["recall_control"]["actual_stop"] for item in outputs["shadow"])
        self.assertEqual((empty["actual_stop_reason"], empty["stop_class"]), ("no_evidence", "search_space"))
        self.assertEqual((found["actual_stop_reason"], found["stop_class"]), ("frontier_exhausted", "search_space"))
        self.assertEqual(found["budget_state"], {"host_caps": {}})

    def test_semantic_cap_binding_is_a_resource_stop(self):
        def seed(memory):
            for index in range(20):
                memory.remember(f"memory:pet:{index}", f"Note {index} about a household animal.")

        with mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _ConstantProvider):
            outputs = self._recall_both(seed, [("Which pet?", {})], semantic_retrieval="required")
        off, shadow = outputs["off"][0], outputs["shadow"][0]
        self.assertEqual(json.dumps(_retrieval(off), sort_keys=True), json.dumps(_retrieval(shadow), sort_keys=True))
        report = shadow["recall_control"]
        self.assertEqual(report["route_candidate_counts"][SEMANTIC_VECTOR_ROUTE], surface.SEMANTIC_CANDIDATE_LIMIT)
        self.assertEqual(report["actual_stop"]["actual_stop_reason"], "max_candidates")
        self.assertEqual(report["actual_stop"]["stop_class"], "resource")
        self.assertEqual(report["actual_stop"]["budget_state"], {"host_caps": {SEMANTIC_VECTOR_ROUTE: surface.SEMANTIC_CANDIDATE_LIMIT}})

    @unittest.skipUnless(os.environ.get("AGENT_MEMORY_REPRESENTATION_DIR") or os.environ.get("AGENT_MEMORY_REQUIRE_REPRESENTATION"),
                         "pinned representation model not provisioned")
    def test_semantic_cap_binding_with_the_pinned_model(self):
        def seed(memory):
            for index in range(24):
                memory.remember(f"memory:dog:{index}", f"My dog number {index} loves long walks in the park.")

        outputs = self._recall_both(seed, [("Tell me about my dog and its walks", {})], semantic_retrieval="required")
        report = outputs["shadow"][0]["recall_control"]
        self.assertEqual(json.dumps(_retrieval(outputs["off"][0]), sort_keys=True),
                         json.dumps(_retrieval(outputs["shadow"][0]), sort_keys=True))
        self.assertEqual(report["route_candidate_counts"][SEMANTIC_VECTOR_ROUTE], surface.SEMANTIC_CANDIDATE_LIMIT)
        self.assertEqual(report["actual_stop"]["actual_stop_reason"], "max_candidates")


class ShadowHelperTests(unittest.TestCase):
    def test_controller_failure_has_no_effect_and_is_not_a_controller_failure_stop(self):
        class Raising:
            def plan(self, *args, **kwargs):
                raise RuntimeError("controller down")

        class Invalid:
            def plan(self, *args, **kwargs):
                return "not a plan"

        common = dict(query="q", logical_memory_refs=(), available_routes=("lexical",), routes_executed=("lexical",),
                      route_counts={"lexical": 3}, host_caps={}, candidate_count=3,
                      policy_context={"tenant_scope_ref": "t#s", "recall_policy_ref": "p", "controller_contract_version": "1.0.0"})
        for controller, status in ((Raising(), "unavailable"), (Invalid(), "invalid_response")):
            report = shadow_control_report(controller=controller, **common)
            self.assertEqual(report["response"]["decision_status"], status)
            self.assertEqual(report["usage"]["fallback_events"], ["controller_failure_no_effect"])
            self.assertEqual(report["shadow_delta"], {})
            self.assertEqual(report["actual_stop"]["actual_stop_reason"], "frontier_exhausted")

    def test_stop_precedence(self):
        self.assertEqual(shadow_actual_stop({}, {"semantic_vector": 16}, 0)["actual_stop_reason"], "no_evidence")
        self.assertEqual(shadow_actual_stop({"semantic_vector": 16}, {"semantic_vector": 16}, 16)["actual_stop_reason"], "max_candidates")
        self.assertEqual(shadow_actual_stop({"semantic_vector": 15}, {"semantic_vector": 16}, 15)["actual_stop_reason"], "frontier_exhausted")

    def test_shadow_plan_is_the_deterministic_controller_plan(self):
        report = shadow_control_report(
            controller=DeterministicRecallController(), query="budget review", logical_memory_refs=(),
            available_routes=("lexical", "exact_logical_identity"), routes_executed=("lexical",),
            route_counts={"lexical": 40}, host_caps={}, candidate_count=40,
            policy_context={"tenant_scope_ref": "t#s", "recall_policy_ref": "p", "controller_contract_version": "1.0.0"})
        plan = DeterministicRecallController().plan("budget review", logical_memory_refs=(),
                                                    available_routes=("lexical", "exact_logical_identity"))
        self.assertIsInstance(plan, RecallControlPlan)
        self.assertEqual(report["response"]["evidence"]["route_budgets"], plan.to_dict()["route_budgets"])
        self.assertTrue(report["shadow_delta"]["lexical"]["would_truncate"])


class HarnessVectorPrefilterTests(unittest.TestCase):
    def test_controlled_planner_passes_the_domain_prefilter_to_the_vector_route(self):
        # S6: the harness planner's vector search receives eligible=, as the default planner's does.
        seen = {}

        class Retriever:
            def available_for(self, substrate):
                return True

            def search(self, substrate, query, **kwargs):
                seen.update(kwargs)
                return []

        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            memory.remember("memory:a", "The budget is final.")
            adapter = memory.runtime.adapter
            planner = ControlledRecallPlanner(adapter, vector_retriever=Retriever())
            context = memory.runtime.adapter  # placeholder replaced below
            from agentmem_ref.api import contract
            envelope = {"contract_version": contract.CONTRACT_VERSION, "target_domain_refs": list(memory._domain_refs()),
                        "principal_ref": memory.actor_id, "project_ref": memory.scope, "purpose": memory.purpose}
            context = contract.recall_context_from_envelope(contract.validate_recall_context(envelope))
            planner.recall("budget", context)
        self.assertIn("eligible", seen)
        self.assertTrue(callable(seen["eligible"]))


if __name__ == "__main__":
    unittest.main()
