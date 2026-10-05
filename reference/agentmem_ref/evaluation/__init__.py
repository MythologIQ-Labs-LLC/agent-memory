"""Benchmark-neutral Memory Evaluation utilities.

This package is intentionally independent from Agent Memory runtime authority. It may
validate and compare evidence emitted by Agent Memory or other systems, but benchmark
output never authorizes recall admission or mutation.
"""

from .benchmark_integration import (
    CONTRACT_VERSION as BENCHMARK_INTEGRATION_CONTRACT_VERSION,
    BenchmarkIntegrationError,
    check_profile_binding,
    integration_digest,
    load_integration,
    mapped_metric_observations,
    validate_integration,
)
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
from .gauntlet_contract import (
    CONTRACT_VERSION as GAUNTLET_CONTRACT_VERSION,
    GauntletContractError,
    canonical_manifest_bytes,
    capability_support,
    manifest_digest,
    negotiate_capabilities,
    validate_manifest,
    validate_operation_envelope,
    validate_profile_requirements,
)

__all__ = [
    "BENCHMARK_INTEGRATION_CONTRACT_VERSION",
    "BenchmarkIntegrationError",
    "check_profile_binding",
    "integration_digest",
    "load_integration",
    "mapped_metric_observations",
    "validate_integration",
    "BenchmarkContractError",
    "ComparisonCompatibilityError",
    "canonical_json_bytes",
    "compare_runs",
    "dimension_report",
    "load_run",
    "metric_observation",
    "validate_run",
    "write_run",
    "GAUNTLET_CONTRACT_VERSION",
    "GauntletContractError",
    "canonical_manifest_bytes",
    "capability_support",
    "manifest_digest",
    "negotiate_capabilities",
    "validate_manifest",
    "validate_operation_envelope",
    "validate_profile_requirements",
]
