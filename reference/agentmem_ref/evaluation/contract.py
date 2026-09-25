"""Common result contract for memory benchmark evidence.

The contract normalizes evidence shape, not benchmark semantics. Native benchmark
outputs remain opaque and common metric observations are compared only when benchmark
identity, frozen input identity, selection identity, units, direction, and denominators
are compatible.

Benchmark evidence has no authority over Agent Memory runtime behavior.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .._paths import PACKAGE_NAME, REPO_ROOT

SCHEMA_VERSION = "1.0.0"
SCHEMA_NAME = "memory-benchmark-run.schema.json"
DIMENSIONS = (
    "retrieval",
    "currentness",
    "reasoning",
    "governance",
    "efficiency",
    "evaluator_integrity",
    "reproducibility",
)
METRIC_STATES = {"measured", "not_measured", "not_applicable", "blocked"}
DIMENSION_STATUSES = {"measured", "partial", "not_measured", "not_applicable", "blocked"}
DIRECTIONS = {"higher_better", "lower_better", "zero_target", "descriptive"}


class BenchmarkContractError(ValueError):
    """Raised when a benchmark evidence manifest violates the common contract."""


class ComparisonCompatibilityError(BenchmarkContractError):
    """Raised when two benchmark runs do not share the same comparison identity."""


def _schema_document() -> dict[str, Any]:
    source = REPO_ROOT / "schemas" / SCHEMA_NAME
    if source.is_file():
        return json.loads(source.read_text(encoding="utf-8"))
    try:
        resource = importlib.resources.files(PACKAGE_NAME) / "_schemas" / SCHEMA_NAME
        return json.loads(resource.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise BenchmarkContractError(f"benchmark schema unavailable: {SCHEMA_NAME}") from exc


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_schema_document(), format_checker=FormatChecker())


def _path(error: ValidationError) -> str:
    if not error.absolute_path:
        return "$"
    return "$" + "".join(f"[{item!r}]" if isinstance(item, int) else f".{item}" for item in error.absolute_path)


def _semantic_validate(document: Mapping[str, Any]) -> None:
    seen_dimensions = set(document["dimensions"])
    if seen_dimensions != set(DIMENSIONS):
        missing = sorted(set(DIMENSIONS) - seen_dimensions)
        extra = sorted(seen_dimensions - set(DIMENSIONS))
        raise BenchmarkContractError(f"dimension vocabulary mismatch: missing={missing}, extra={extra}")

    for dimension_id in DIMENSIONS:
        dimension = document["dimensions"][dimension_id]
        status = dimension["status"]
        metrics = dimension["metrics"]
        if status not in DIMENSION_STATUSES:
            raise BenchmarkContractError(f"unsupported dimension status: {dimension_id}={status}")
        ids: set[str] = set()
        measured_count = 0
        for metric in metrics:
            metric_id = metric["metric_id"]
            if metric_id in ids:
                raise BenchmarkContractError(f"duplicate metric_id in {dimension_id}: {metric_id}")
            ids.add(metric_id)
            if metric["state"] == "measured":
                measured_count += 1
                value = metric["value"]
                if isinstance(value, float) and not math.isfinite(value):
                    raise BenchmarkContractError(
                        f"measured metric must be finite: {dimension_id}.{metric_id}"
                    )
        if status == "measured":
            if not metrics or measured_count != len(metrics):
                raise BenchmarkContractError(
                    f"measured dimension requires only measured metrics: {dimension_id}"
                )
        elif status in {"not_measured", "not_applicable", "blocked"} and measured_count:
            raise BenchmarkContractError(
                f"{status} dimension may not contain measured metrics: {dimension_id}"
            )
        elif status == "partial" and not metrics:
            raise BenchmarkContractError(f"partial dimension requires metric evidence: {dimension_id}")


def validate_run(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached benchmark-run document.

    Validation is structural plus a small set of semantic consistency checks. It does
    not judge benchmark quality or grant authority.
    """

    detached = json.loads(json.dumps(document))
    errors = sorted(_validator().iter_errors(detached), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        raise BenchmarkContractError(f"{_path(first)}: {first.message}") from first
    _semantic_validate(detached)
    return detached


def metric_observation(
    metric_id: str,
    *,
    state: str = "measured",
    value: Any = None,
    direction: str = "descriptive",
    denominator: float | int | None = None,
    unit: str | None = None,
    population: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Build one common metric observation without conflating missingness and zero."""

    if not metric_id:
        raise BenchmarkContractError("metric_id must be non-empty")
    if state not in METRIC_STATES:
        raise BenchmarkContractError(f"unsupported metric state: {state}")
    if direction not in DIRECTIONS:
        raise BenchmarkContractError(f"unsupported metric direction: {direction}")
    if state == "measured" and value is None:
        raise BenchmarkContractError("measured metric requires value")
    if state != "measured" and value is not None:
        raise BenchmarkContractError(f"{state} metric must not carry a value")
    if denominator is not None and denominator < 0:
        raise BenchmarkContractError("denominator must be non-negative")

    result: dict[str, Any] = {
        "metric_id": metric_id,
        "state": state,
        "direction": direction,
    }
    if state == "measured":
        if isinstance(value, float) and not math.isfinite(value):
            raise BenchmarkContractError("measured metric must be finite")
        result["value"] = value
    if denominator is not None:
        result["denominator"] = denominator
    if unit is not None:
        result["unit"] = unit
    if population is not None:
        result["population"] = population
    if note is not None:
        result["note"] = note
    return result


def dimension_report(
    status: str,
    metrics: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    *,
    notes: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build a dimension container. Full run validation enforces consistency."""

    if status not in DIMENSION_STATUSES:
        raise BenchmarkContractError(f"unsupported dimension status: {status}")
    return {
        "status": status,
        "metrics": [dict(metric) for metric in metrics],
        "notes": list(notes),
    }


def canonical_json_bytes(document: Mapping[str, Any]) -> bytes:
    """Return stable JSON bytes for evidence hashing and artifact persistence."""

    validated = validate_run(document)
    return (
        json.dumps(validated, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def run_digest(document: Mapping[str, Any]) -> str:
    """SHA-256 digest of the validated canonical benchmark-run representation."""

    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def load_run(path: str | Path) -> dict[str, Any]:
    """Load and validate one benchmark run manifest."""

    location = Path(path)
    try:
        document = json.loads(location.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkContractError(f"unable to load benchmark run {location}: {exc}") from exc
    if not isinstance(document, dict):
        raise BenchmarkContractError("benchmark run root must be a JSON object")
    return validate_run(document)


def write_run(path: str | Path, document: Mapping[str, Any]) -> str:
    """Atomically write validated benchmark evidence and return its SHA-256 digest."""

    location = Path(path)
    payload = canonical_json_bytes(document)
    digest = hashlib.sha256(payload).hexdigest()
    location.parent.mkdir(parents=True, exist_ok=True)
    temporary = location.with_name(location.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, location)
    return digest


def comparison_identity(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return the frozen facts that must match before cross-system deltas are valid."""

    benchmark = document["benchmark"]
    execution = document["execution"]
    return {
        "benchmark_id": benchmark["id"],
        "source_revision": benchmark["source_revision"],
        "dataset_id": benchmark.get("dataset_id"),
        "dataset_revision": benchmark.get("dataset_revision"),
        "input_sha256": benchmark["input_sha256"],
        "task_profile": benchmark.get("task_profile"),
        "selection_id": execution["selection_id"],
        "selection_method": execution["selection_method"],
        "sample_count": execution["sample_count"],
    }


def _metric_map(dimension: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {metric["metric_id"]: metric for metric in dimension["metrics"]}


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _outcome(direction: str, baseline: float, candidate: float) -> str:
    if candidate == baseline:
        return "unchanged"
    if direction == "higher_better":
        return "improved" if candidate > baseline else "regressed"
    if direction == "lower_better":
        return "improved" if candidate < baseline else "regressed"
    if direction == "zero_target":
        if abs(candidate) == abs(baseline):
            return "unchanged"
        return "improved" if abs(candidate) < abs(baseline) else "regressed"
    return "changed"


def _compare_metric(
    metric_id: str,
    baseline: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"metric_id": metric_id}
    if baseline is None or candidate is None:
        result["comparison_state"] = "metric_missing"
        result["baseline_state"] = None if baseline is None else baseline["state"]
        result["candidate_state"] = None if candidate is None else candidate["state"]
        return result

    result["baseline_state"] = baseline["state"]
    result["candidate_state"] = candidate["state"]
    if baseline["state"] != "measured" or candidate["state"] != "measured":
        result["comparison_state"] = "state_not_measured"
        return result
    if baseline["direction"] != candidate["direction"]:
        result["comparison_state"] = "direction_mismatch"
        return result
    if baseline.get("unit") != candidate.get("unit"):
        result["comparison_state"] = "unit_mismatch"
        return result
    if baseline.get("denominator") != candidate.get("denominator"):
        result["comparison_state"] = "denominator_mismatch"
        return result
    if baseline.get("population") != candidate.get("population"):
        result["comparison_state"] = "population_mismatch"
        return result

    baseline_value = baseline["value"]
    candidate_value = candidate["value"]
    result["baseline_value"] = baseline_value
    result["candidate_value"] = candidate_value
    result["direction"] = baseline["direction"]
    result["unit"] = baseline.get("unit")
    result["denominator"] = baseline.get("denominator")
    result["population"] = baseline.get("population")

    if not (_numeric(baseline_value) and _numeric(candidate_value)):
        result["comparison_state"] = "comparable_non_numeric"
        result["outcome"] = "unchanged" if baseline_value == candidate_value else "changed"
        return result

    baseline_number = float(baseline_value)
    candidate_number = float(candidate_value)
    result["comparison_state"] = "comparable"
    result["delta"] = candidate_number - baseline_number
    result["outcome"] = _outcome(baseline["direction"], baseline_number, candidate_number)
    return result


def compare_runs(
    baseline_document: Mapping[str, Any],
    candidate_document: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare compatible runs without synthesizing an aggregate memory score.

    Run-level compatibility is fail-closed. Metric-level deltas are emitted only when
    both observations are measured and their direction, unit, denominator, and
    population semantics match.
    """

    baseline = validate_run(baseline_document)
    candidate = validate_run(candidate_document)
    baseline_identity = comparison_identity(baseline)
    candidate_identity = comparison_identity(candidate)
    mismatches = {
        key: {"baseline": baseline_identity[key], "candidate": candidate_identity[key]}
        for key in baseline_identity
        if baseline_identity[key] != candidate_identity[key]
    }
    if mismatches:
        rendered = ", ".join(
            f"{key}={value['baseline']!r}!={value['candidate']!r}"
            for key, value in sorted(mismatches.items())
        )
        raise ComparisonCompatibilityError(f"benchmark runs are not comparable: {rendered}")

    dimensions: dict[str, list[dict[str, Any]]] = {}
    for dimension_id in DIMENSIONS:
        baseline_metrics = _metric_map(baseline["dimensions"][dimension_id])
        candidate_metrics = _metric_map(candidate["dimensions"][dimension_id])
        metric_ids = sorted(set(baseline_metrics) | set(candidate_metrics))
        dimensions[dimension_id] = [
            _compare_metric(metric_id, baseline_metrics.get(metric_id), candidate_metrics.get(metric_id))
            for metric_id in metric_ids
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "comparison_status": "comparable",
        "comparison_identity": baseline_identity,
        "baseline": {
            "run_id": baseline["run_id"],
            "status": baseline["status"],
            "system": baseline["system"],
        },
        "candidate": {
            "run_id": candidate["run_id"],
            "status": candidate["status"],
            "system": candidate["system"],
        },
        "dimensions": dimensions,
        "authority_effect": "none",
    }
