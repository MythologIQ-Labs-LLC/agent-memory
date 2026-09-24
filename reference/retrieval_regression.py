"""Continuous regression layer over the existing retrieval-quality benchmark.

This module does not execute a second retrieval implementation. It repeatedly
invokes the canonical deterministic benchmark, enriches its admitted metrics
with F1, binds directional evaluation targets, and compares compatible reports.
Candidate generation remains distinct from governed final admission.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from agentmem_ref.harness.retrieval_quality_benchmark import run_benchmark


REGRESSION_SCHEMA_VERSION = "1.0.0"
REGRESSION_ENGINE_ID = "agent-memory-continuous-retrieval-regression"


def _f1(precision: float, recall: float) -> float:
    denominator = precision + recall
    if denominator <= 0.0:
        return 0.0
    return round(2.0 * precision * recall / denominator, 6)


def enrich_admitted_f1(report: Mapping[str, Any]) -> dict[str, Any]:
    """Add final-admission F1 without changing candidate or governance semantics."""
    result = deepcopy(dict(report))
    systems = result.get("systems", {})
    for system in systems.values():
        for row in system.get("cases", []):
            metrics = row.get("metrics", {})
            metrics["admitted_f1"] = _f1(
                float(metrics.get("admitted_precision", 0.0)),
                float(metrics.get("admitted_recall", 0.0)),
            )
        aggregate = system.get("aggregate", {})
        aggregate["admitted_f1"] = _f1(
            float(aggregate.get("admitted_precision", 0.0)),
            float(aggregate.get("admitted_recall", 0.0)),
        )

    lexical = systems.get("lexical_only", {}).get("aggregate", {})
    multi = systems.get("multi_route", {}).get("aggregate", {})
    comparison = result.setdefault("comparison", {})
    if lexical and multi:
        comparison["admitted_f1_delta"] = round(
            float(multi.get("admitted_f1", 0.0))
            - float(lexical.get("admitted_f1", 0.0)),
            6,
        )
    controlled = systems.get("controlled_typed_graph", {}).get("aggregate", {})
    if controlled and multi:
        comparison["typed_graph_admitted_f1_delta_over_multi_route"] = round(
            float(controlled.get("admitted_f1", 0.0))
            - float(multi.get("admitted_f1", 0.0)),
            6,
        )

    result["metric_contract"] = {
        "candidate_generation": [
            "candidate_recall",
            "candidate_total",
            "candidate_noise",
            "route_contribution_counts",
            "unique_recall_gain_by_route",
        ],
        "final_governed_admission": [
            "admitted_recall",
            "admitted_precision",
            "admitted_f1",
            "mean_reciprocal_rank",
        ],
        "governance": "reported_separately",
        "aggregate_health_score": "not_defined",
    }
    return result


def _selected_system(report: Mapping[str, Any]) -> str:
    systems = report.get("systems", {})
    if "controlled_typed_graph" in systems:
        return "controlled_typed_graph"
    if "multi_route" in systems:
        return "multi_route"
    raise ValueError("retrieval report lacks a governed final-admission system")


def _comparison_signature(report: Mapping[str, Any]) -> dict[str, Any]:
    system = _selected_system(report)
    return {
        "benchmark_id": report.get("benchmark_id"),
        "benchmark_version": report.get("benchmark_version"),
        "fixture_sha256": report.get("fixture", {}).get("sha256"),
        "runtime_configuration_sha256": report.get("runtime_configuration", {}).get("sha256"),
        "vector_route": report.get("vector_route"),
        "typed_graph_route": report.get("typed_graph_route"),
        "selected_system": system,
    }


def compare_reports(
    current: Mapping[str, Any], baseline: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare only reports whose fixture/config/profile denominators match."""
    try:
        current_signature = _comparison_signature(current)
        baseline_signature = _comparison_signature(baseline)
    except (AttributeError, TypeError, ValueError):
        return {
            "status": "not-comparable",
            "reason": "missing_reproducible_benchmark_contract",
        }

    mismatches = [
        key
        for key in current_signature
        if current_signature.get(key) != baseline_signature.get(key)
    ]
    if mismatches:
        return {
            "status": "not-comparable",
            "reason": "benchmark_contract_mismatch",
            "mismatched_fields": mismatches,
            "current_signature": current_signature,
            "baseline_signature": baseline_signature,
        }

    system = str(current_signature["selected_system"])
    current_metrics = current["systems"][system]["aggregate"]
    baseline_metrics = baseline["systems"][system]["aggregate"]
    rows: dict[str, Any] = {}
    for metric in (
        "candidate_recall",
        "admitted_recall",
        "admitted_precision",
        "admitted_f1",
    ):
        current_value = float(current_metrics[metric])
        baseline_value = float(baseline_metrics[metric])
        delta = round(current_value - baseline_value, 6)
        classification = (
            "improved" if delta > 0.0 else "regressed" if delta < 0.0 else "unchanged"
        )
        rows[metric] = {
            "baseline": baseline_value,
            "current": current_value,
            "delta": delta,
            "classification": classification,
        }
    return {
        "status": "comparable",
        "baseline_revision": baseline.get("agent_memory_revision"),
        "current_revision": current.get("agent_memory_revision"),
        "selected_system": system,
        "metrics": rows,
    }


def evaluate_targets(
    report: Mapping[str, Any], targets: Mapping[str, Any]
) -> dict[str, Any]:
    """Evaluate directional expectations as evidence gates, never authority rules."""
    system = _selected_system(report)
    metrics = report["systems"][system]["aggregate"]
    candidate_target = float(targets["candidate_recall_target"])
    tolerance = float(targets.get("candidate_recall_tolerance", 0.0))
    checks = {
        "candidate_recall": {
            "value": float(metrics["candidate_recall"]),
            "target": candidate_target,
            "tolerance": tolerance,
            "passed": float(metrics["candidate_recall"]) >= candidate_target - tolerance,
        },
        "final_admitted_recall": {
            "value": float(metrics["admitted_recall"]),
            "minimum": float(targets["final_admitted_recall_min"]),
            "passed": float(metrics["admitted_recall"])
            >= float(targets["final_admitted_recall_min"]),
        },
        "final_admitted_precision": {
            "value": float(metrics["admitted_precision"]),
            "minimum": float(targets["final_admitted_precision_min"]),
            "passed": float(metrics["admitted_precision"])
            >= float(targets["final_admitted_precision_min"]),
        },
        "final_admitted_f1": {
            "value": float(metrics["admitted_f1"]),
            "minimum": float(targets["final_admitted_f1_min"]),
            "passed": float(metrics["admitted_f1"])
            >= float(targets["final_admitted_f1_min"]),
        },
    }
    governance_values = [
        value
        for value in report.get("governance", {}).values()
        if isinstance(value, (int, float))
    ]
    governance_passed = all(value == 0 for value in governance_values)
    checks["governance_zero_violations"] = {
        "value": sum(int(value) for value in governance_values),
        "target": 0,
        "passed": governance_passed,
    }
    return {
        "profile_version": targets.get("profile_version", "unknown"),
        "selected_system": system,
        "checks": checks,
        "all_expectations_met": all(item["passed"] for item in checks.values()),
        "authority_effect": "none",
    }


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run_continuous_regression(
    *,
    fixture_path: Path,
    runtime_config_path: Path,
    agent_memory_revision: str,
    targets: Mapping[str, Any],
    historical_baseline: Mapping[str, Any] | None = None,
    baseline_report: Mapping[str, Any] | None = None,
    benchmark_runner: Callable[..., dict[str, Any]] = run_benchmark,
) -> dict[str, Any]:
    """Run deterministic repeated reconstruction around the canonical benchmark."""
    first = enrich_admitted_f1(
        benchmark_runner(
            fixture_path=fixture_path,
            runtime_config_path=runtime_config_path,
            agent_memory_revision=agent_memory_revision,
        )
    )
    repeat = enrich_admitted_f1(
        benchmark_runner(
            fixture_path=fixture_path,
            runtime_config_path=runtime_config_path,
            agent_memory_revision=agent_memory_revision,
        )
    )
    reconstruction = enrich_admitted_f1(
        benchmark_runner(
            fixture_path=fixture_path,
            runtime_config_path=runtime_config_path,
            agent_memory_revision=agent_memory_revision,
        )
    )

    result = first
    result["continuous_regression"] = {
        "schema_version": REGRESSION_SCHEMA_VERSION,
        "engine_id": REGRESSION_ENGINE_ID,
        "same_process_repeat_consistent": first == repeat,
        "fresh_runtime_reconstruction_consistent": first == reconstruction,
        "reconstruction_posture": "fresh_fixture_rebuild_from_canonical_inputs",
        "persisted_restart_exercised_by_this_runner": False,
        "targets": evaluate_targets(first, targets),
        "baseline_comparison": (
            compare_reports(first, enrich_admitted_f1(baseline_report))
            if baseline_report is not None
            else {"status": "not-requested"}
        ),
        "historical_baselines": (
            [deepcopy(dict(historical_baseline))]
            if historical_baseline is not None
            else []
        ),
        "authority_effect": "none",
    }
    return result
