#!/usr/bin/env python3
"""Evaluate credential-free cognitive-classification baselines for #490.

This is a conformance/replay harness. Ordinary-LLM and specialized-model rows
come from frozen replay records and MUST NOT be presented as live latency, cost,
or provider-quality measurements. Issue #495 owns live provider qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping

from agentmem_ref.capabilities import ComponentRegistry
from agentmem_ref.cognitive_classification import (
    ClassificationChoice,
    ClassificationRequest,
    CognitiveClassificationRuntime,
    DeterministicRuleProvider,
    ProviderMetadata,
    RawClassification,
    ReplayClassificationProvider,
    classification_component,
    semantic_result_fingerprint,
)

REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURE = REFERENCE_ROOT / "fixtures" / "cognitive-classification-v1.json"
REPORT_SCHEMA_VERSION = "1.0.0"
REPORT_ID = "agent-memory-cognitive-classification-evaluation"


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("classification fixture must be an object")
    if value.get("schema_version") != "1.0.0":
        raise ValueError("unsupported classification fixture schema")
    if value.get("simulation_only") is not True:
        raise ValueError("this runner only accepts fixtures explicitly marked simulation_only=true")
    return value


def _metadata(value: Mapping[str, Any]) -> ProviderMetadata:
    return ProviderMetadata(
        provider_id=str(value["provider_id"]),
        provider_version=str(value["provider_version"]),
        provider_class=str(value["provider_class"]),
        model_runtime_ref=str(value["model_runtime_ref"]),
        configuration_ref=str(value["configuration_ref"]),
        local_offline=bool(value["local_offline"]),
        data_egress=bool(value["data_egress"]),
    )


def _choice(value: Mapping[str, Any]) -> ClassificationChoice:
    probability = value.get("probability")
    return ClassificationChoice(
        label=str(value["label"]),
        score=float(value.get("score", 0.0)),
        probability=None if probability is None else float(probability),
    )


def _raw(value: Mapping[str, Any]) -> RawClassification:
    return RawClassification(
        status=str(value["status"]),
        choices=tuple(_choice(item) for item in value.get("choices", ())),
        reason=str(value.get("reason", "")),
        latency_ms=float(value.get("latency_ms", 0.0)),
        cost_usd=float(value.get("cost_usd", 0.0)),
        trace_ref=str(value.get("trace_ref", "")),
    )


def _request(value: Mapping[str, Any]) -> ClassificationRequest:
    return ClassificationRequest(
        request_id=str(value["request_id"]),
        task=str(value["task"]),
        input_data=value.get("input_data", {}),
        output_labels=tuple(str(item) for item in value["output_labels"]),
        scope=str(value["scope"]),
        purpose=str(value["purpose"]),
        tenant=str(value.get("tenant", "")),
        candidate_scope=str(value.get("candidate_scope", "")),
        source_current=bool(value.get("source_current", True)),
        exact_label=str(value.get("exact_label", "")),
        evidence_refs=tuple(str(item) for item in value.get("evidence_refs", ())),
        policy_context_refs=tuple(str(item) for item in value.get("policy_context_refs", ())),
    )


def _deterministic_rule(request: ClassificationRequest) -> RawClassification:
    data = request.input_data
    task = request.task
    if task == "sensitivity":
        label = "sensitive" if bool(data.get("explicit_sensitive")) else "public"
    elif task == "contradiction":
        label = "contradiction" if bool(data.get("exact_conflict")) else "consistent"
    elif task == "recurrence":
        label = "recurring" if int(data.get("recurrence_count", 0)) >= 2 else "novel"
    elif task == "retention_recommendation":
        if bool(data.get("protected_memory")):
            label = "retain"
        elif bool(data.get("low_utility_stale")):
            label = "review_prune"
        else:
            label = "retain"
    elif task == "relationship":
        label = "related" if bool(data.get("shared_entity_exact")) else "unrelated"
    elif task == "recall_priority":
        label = "high" if bool(data.get("exact_match")) else "low"
    else:
        return RawClassification(status="abstained", reason=f"no deterministic rule for {task}")
    return RawClassification(
        status="ok",
        choices=(ClassificationChoice(label=label, score=1.0, probability=1.0),),
        latency_ms=0.05,
        cost_usd=0.0,
        trace_ref=f"deterministic-rule:{request.request_id}",
    )


def build_runtime(fixture: Mapping[str, Any]) -> tuple[CognitiveClassificationRuntime, tuple[str, ...]]:
    provider_rows = fixture["providers"]
    if not isinstance(provider_rows, list):
        raise ValueError("providers must be an array")

    providers: dict[str, object] = {}
    components = []
    provider_ids: list[str] = []
    for row in provider_rows:
        if not isinstance(row, Mapping):
            raise ValueError("provider row must be an object")
        metadata = _metadata(row)
        provider_ids.append(metadata.provider_id)
        if metadata.provider_class == "deterministic":
            provider = DeterministicRuleProvider(metadata=metadata, rule=_deterministic_rule)
        else:
            replay_rows = row.get("replay", {})
            if not isinstance(replay_rows, Mapping):
                raise ValueError("replay provider requires replay object")
            provider = ReplayClassificationProvider(
                metadata=metadata,
                records={str(key): _raw(value) for key, value in replay_rows.items()},
            )
        providers[metadata.provider_id] = provider
        components.append(
            classification_component(
                metadata,
                maturity="implemented",
                evidence_refs=("#490", "#500", str(fixture["fixture_id"])),
            )
        )

    registry = ComponentRegistry()
    registry.register_many(components)
    return CognitiveClassificationRuntime(registry=registry, provider_bindings=providers), tuple(provider_ids)


def _provider_metrics(results, runtime: CognitiveClassificationRuntime, provider_id: str) -> dict[str, Any]:
    total = len(results)
    provider_correct = 0
    effective_correct = 0
    abstained = unavailable = malformed = refused = exact_overrides = 0
    critical_fp = critical_fn = 0
    probabilities: list[tuple[float, float]] = []
    latencies: list[float] = []
    total_cost = 0.0
    cross_scope_refusals = stale_refusals = authority_violations = 0
    reproducible = True

    for case, result in results:
        expected = str(case["expected_label"])
        critical = str(case.get("critical_label", ""))
        provider_correct += int(result.provider_label == expected)
        effective_correct += int(result.effective_label == expected)
        abstained += int(result.status == "abstained")
        unavailable += int(result.status == "unavailable")
        malformed += int(result.status == "malformed")
        refused += int(result.status == "refused")
        exact_overrides += int(result.exact_metadata_override)
        cross_scope_refusals += int("cross_scope_input" in result.gate_reasons)
        stale_refusals += int("stale_source_evidence" in result.gate_reasons)
        authority_violations += int(result.authority_effect != "none")

        if critical:
            critical_fp += int(result.provider_label == critical and expected != critical)
            critical_fn += int(expected == critical and result.provider_label != critical)

        if result.choices and result.choices[0].probability is not None:
            probabilities.append((result.choices[0].probability, 1.0 if result.provider_label == expected else 0.0))
        latencies.append(result.latency_ms)
        total_cost += result.cost_usd

        repeated = runtime.classify(_request(case), provider_id)
        if semantic_result_fingerprint(repeated) != semantic_result_fingerprint(result):
            reproducible = False

    brier = None
    if probabilities:
        brier = round(sum((probability - outcome) ** 2 for probability, outcome in probabilities) / len(probabilities), 6)

    metadata = results[0][1].provider if results else None
    simulated = bool(metadata and metadata.provider_class != "deterministic")
    measurement_class = "simulated_fixture_value" if simulated else "local_rule_harness_value"
    return {
        "case_count": total,
        "provider_label_accuracy": round(provider_correct / total, 6) if total else 0.0,
        "effective_label_accuracy_after_deterministic_overrides": round(effective_correct / total, 6) if total else 0.0,
        "top_choice_brier": brier,
        "abstention_count": abstained,
        "unavailable_count": unavailable,
        "malformed_count": malformed,
        "refused_count": refused,
        "exact_metadata_override_count": exact_overrides,
        "critical_false_positive_count": critical_fp,
        "critical_false_negative_count": critical_fn,
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 6) if latencies else 0.0,
            "median": round(statistics.median(latencies), 6) if latencies else 0.0,
            "measurement_class": measurement_class,
        },
        "cost_usd": {"total": round(total_cost, 8), "measurement_class": measurement_class},
        "privacy": {
            "local_offline": bool(metadata.local_offline) if metadata else False,
            "data_egress": bool(metadata.data_egress) if metadata else False,
            "measurement_class": "declared_fixture_posture",
        },
        "reproducible_on_frozen_fixture": reproducible,
        "governance": {
            "cross_scope_refusal_count": cross_scope_refusals,
            "stale_source_refusal_count": stale_refusals,
            "authority_effect_violations": authority_violations,
        },
    }


def run(fixture_path: Path = DEFAULT_FIXTURE, *, agent_memory_revision: str = "unbound") -> dict[str, Any]:
    fixture = _load(fixture_path)
    runtime, provider_ids = build_runtime(fixture)
    raw_cases = fixture["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("fixture cases must be a non-empty array")

    per_provider_results = {provider_id: [] for provider_id in provider_ids}
    disagreement_count = 0
    comparisons = []

    for case in raw_cases:
        if not isinstance(case, Mapping):
            raise ValueError("case must be an object")
        request = _request(case)
        comparison = runtime.compare(request, provider_ids)
        comparisons.append(comparison.to_dict())
        disagreement_count += int(comparison.disagreement)
        by_id = {result.provider.provider_id: result for result in comparison.results}
        for provider_id in provider_ids:
            per_provider_results[provider_id].append((case, by_id[provider_id]))

    metrics = {
        provider_id: _provider_metrics(rows, runtime, provider_id)
        for provider_id, rows in per_provider_results.items()
    }

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "fixture_id": fixture["fixture_id"],
        "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "agent_memory_revision": agent_memory_revision,
        "simulation_only": True,
        "provider_metrics": metrics,
        "provider_disagreement_case_count": disagreement_count,
        "comparisons": comparisons,
        "dimensions": [
            "provider label quality",
            "deterministic override effect",
            "calibration",
            "abstention/failure",
            "latency",
            "cost",
            "privacy/data egress",
            "reproducibility",
            "governance outcome",
        ],
        "aggregate_health_score": "not_defined",
        "claim_boundary": {
            "replay_is_live_provider_measurement": False,
            "provider_output_is_authority": False,
            "confidence_is_permission": False,
            "ranking_is_recall_admission": False,
            "recommendation_is_mutation_authority": False,
            "live_provider_qualification_owner": "#495",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--agent-memory-revision", default="unbound")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.fixture.resolve(), agent_memory_revision=args.agent_memory_revision)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
