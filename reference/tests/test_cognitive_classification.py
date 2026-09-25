from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

from agentmem_ref.capabilities import ComponentRegistry  # noqa: E402
from agentmem_ref.cognitive_classification import (  # noqa: E402
    ClassificationChoice,
    ClassificationRequest,
    CognitiveClassificationRuntime,
    ProviderMetadata,
    RawClassification,
    ReplayClassificationProvider,
    classification_component,
    semantic_result_fingerprint,
)

RUNNER = REFERENCE / "run_cognitive_classification_evaluation.py"
FIXTURE = REFERENCE / "fixtures" / "cognitive-classification-v1.json"


def _runner_module():
    spec = importlib.util.spec_from_file_location("run_cognitive_classification_evaluation", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER_MODULE = _runner_module()


class CognitiveClassificationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.runtime, self.provider_ids = RUNNER_MODULE.build_runtime(fixture)
        self.cases = {row["request_id"]: row for row in fixture["cases"]}

    def request(self, request_id: str) -> ClassificationRequest:
        return RUNNER_MODULE._request(self.cases[request_id])

    def test_reuses_component_registry_and_has_no_authority_effect(self) -> None:
        self.assertIsInstance(self.runtime.registry, ComponentRegistry)
        result = self.runtime.classify(self.request("sensitivity-explicit"), "deterministic-rule-baseline")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.effective_label, "sensitive")
        self.assertEqual(result.authority_effect, "none")
        resolved = self.runtime.registry.component("deterministic-rule-baseline")
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved.capabilities[0].capability_id, "cognitive_classification")
        self.assertFalse(resolved.capabilities[0].behavior_contract.write)

    def test_exact_metadata_overrides_high_confidence_provider(self) -> None:
        result = self.runtime.classify(self.request("retention-protected"), "ordinary-llm-replay")
        self.assertEqual(result.provider_label, "review_prune")
        self.assertEqual(result.effective_label, "retain")
        self.assertTrue(result.exact_metadata_override)
        self.assertIn("provider_conflicts_exact_metadata", result.gate_reasons)
        self.assertEqual(result.authority_effect, "none")

    def test_cross_scope_high_confidence_is_refused(self) -> None:
        result = self.runtime.classify(self.request("relationship-cross-scope"), "ordinary-llm-replay")
        self.assertEqual(result.provider_label, "related")
        self.assertEqual(result.status, "refused")
        self.assertFalse(result.consequence_eligible)
        self.assertIn("cross_scope_input", result.gate_reasons)

    def test_stale_source_is_refused_without_erasing_provider_observation(self) -> None:
        result = self.runtime.classify(self.request("recall-stale"), "specialized-model-replay")
        self.assertEqual(result.provider_label, "high")
        self.assertEqual(result.status, "refused")
        self.assertIn("stale_source_evidence", result.gate_reasons)

    def test_disagreement_remains_visible_without_aggregation(self) -> None:
        comparison = self.runtime.compare(self.request("contradiction-clean"), self.provider_ids)
        self.assertTrue(comparison.disagreement)
        payload = comparison.to_dict()
        self.assertEqual(payload["aggregation"], "none")
        self.assertEqual(payload["authority_effect"], "none")

    def test_abstention_is_terminal_unless_fallback_is_explicit(self) -> None:
        request = self.request("contradiction-clean")
        terminal = self.runtime.classify_with_fallback(
            request,
            "specialized-model-replay",
            ("deterministic-rule-baseline",),
        )
        self.assertEqual(terminal.selected.status, "abstained")
        self.assertFalse(terminal.fallback_used)

        explicit = self.runtime.classify_with_fallback(
            request,
            "specialized-model-replay",
            ("deterministic-rule-baseline",),
            fallback_on_abstention=True,
        )
        self.assertTrue(explicit.fallback_used)
        self.assertEqual(explicit.selected.status, "ok")
        self.assertEqual(explicit.selected.effective_label, "consistent")

    def test_malformed_provider_output_fails_closed(self) -> None:
        metadata = ProviderMetadata(
            provider_id="malformed-replay",
            provider_version="1",
            provider_class="ordinary_llm",
            model_runtime_ref="simulated:malformed",
            configuration_ref="test:malformed",
            local_offline=False,
            data_egress=True,
        )
        provider = ReplayClassificationProvider(
            metadata=metadata,
            records={
                "sensitivity-public": RawClassification(
                    status="ok",
                    choices=(ClassificationChoice(label="secret_magic", probability=0.99),),
                )
            },
        )
        registry = ComponentRegistry()
        registry.register(classification_component(metadata))
        runtime = CognitiveClassificationRuntime(registry=registry, provider_bindings={metadata.provider_id: provider})
        result = runtime.classify(self.request("sensitivity-public"), metadata.provider_id)
        self.assertEqual(result.status, "malformed")
        self.assertFalse(result.consequence_eligible)
        self.assertEqual(result.choices, ())

    def test_missing_or_ineligible_provider_is_explicitly_unavailable(self) -> None:
        result = self.runtime.classify(self.request("sensitivity-public"), "not-configured")
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(result.consequence_eligible)
        self.assertIn("provider_unavailable", result.gate_reasons)

    def test_frozen_result_is_reproducible(self) -> None:
        request = self.request("sensitivity-explicit")
        first = self.runtime.classify(request, "ordinary-llm-replay")
        second = self.runtime.classify(request, "ordinary-llm-replay")
        self.assertEqual(first.result_digest, second.result_digest)
        self.assertEqual(semantic_result_fingerprint(first), semantic_result_fingerprint(second))


class CognitiveClassificationEvaluationTests(unittest.TestCase):
    def test_three_materially_different_provider_classes_share_contract(self) -> None:
        report = RUNNER_MODULE.run(FIXTURE, agent_memory_revision="test-revision")
        self.assertTrue(report["simulation_only"])
        self.assertEqual(report["aggregate_health_score"], "not_defined")
        self.assertEqual(
            set(report["provider_metrics"]),
            {"deterministic-rule-baseline", "ordinary-llm-replay", "specialized-model-replay"},
        )
        self.assertFalse(report["claim_boundary"]["provider_output_is_authority"])
        self.assertEqual(report["claim_boundary"]["live_provider_qualification_owner"], "#495")

    def test_metrics_keep_provider_quality_separate_from_deterministic_override(self) -> None:
        report = RUNNER_MODULE.run(FIXTURE, agent_memory_revision="test-revision")
        llm = report["provider_metrics"]["ordinary-llm-replay"]
        self.assertLess(llm["provider_label_accuracy"], llm["effective_label_accuracy_after_deterministic_overrides"])
        self.assertEqual(llm["exact_metadata_override_count"], 1)
        self.assertGreaterEqual(llm["governance"]["cross_scope_refusal_count"], 1)
        self.assertGreaterEqual(llm["governance"]["stale_source_refusal_count"], 1)
        self.assertEqual(llm["governance"]["authority_effect_violations"], 0)

    def test_replay_latency_and_cost_are_not_labeled_live_measurements(self) -> None:
        report = RUNNER_MODULE.run(FIXTURE, agent_memory_revision="test-revision")
        llm = report["provider_metrics"]["ordinary-llm-replay"]
        self.assertEqual(llm["latency_ms"]["measurement_class"], "simulated_fixture_value")
        self.assertEqual(llm["cost_usd"]["measurement_class"], "simulated_fixture_value")
        self.assertEqual(llm["privacy"]["measurement_class"], "declared_fixture_posture")


if __name__ == "__main__":
    unittest.main()
