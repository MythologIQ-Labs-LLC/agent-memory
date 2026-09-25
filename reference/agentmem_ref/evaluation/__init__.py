"""Benchmark-neutral Memory Evaluation utilities.

This package is intentionally independent from Agent Memory runtime authority. It may
validate and compare evidence emitted by Agent Memory or other systems, but benchmark
output never authorizes recall admission or mutation.
"""

from .contract import (
    BenchmarkContractError,
    ComparisonCompatibilityError,
    canonical_json_bytes,
    compare_runs,
    dimension_report,
    load_run,
    metric_observation,
    validate_run,
    write_run,
)

__all__ = [
    "BenchmarkContractError",
    "ComparisonCompatibilityError",
    "canonical_json_bytes",
    "compare_runs",
    "dimension_report",
    "load_run",
    "metric_observation",
    "validate_run",
    "write_run",
]
