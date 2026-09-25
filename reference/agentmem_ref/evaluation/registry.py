"""Static registry of repository-owned memory benchmark profiles.

Registry metadata is descriptive only. It does not establish that an external run has
occurred, that a score is comparable, or that any benchmark result has memory authority.
"""

from __future__ import annotations

from copy import deepcopy


_PROFILES = (
    {
        "profile_id": "swe-context-bench-lite-external-retrieval-v1",
        "benchmark_id": "swe-context-bench-lite",
        "owning_issue": 467,
        "runner": "reference/run_swe_context_bench_harness.py",
        "supporting_runners": (
            "reference/run_swe_context_bench.py",
            "reference/run_swe_context_bench_real_100.py",
        ),
        "implementation_status": "runner_ready",
        "external_evidence_status": "blocked_on_exact_frozen_projection_and_selection_provenance",
        "dimensions": (
            "retrieval",
            "governance",
            "efficiency",
            "evaluator_integrity",
            "reproducibility",
        ),
        "description": (
            "SWE-ContextBench Lite prior-experience retrieval comparison with no-memory, "
            "lexical-overlap, and governed Agent Memory arms."
        ),
    },
    {
        "profile_id": "agent-memory-longmemeval-retrieval-currentness-v1",
        "benchmark_id": "longmemeval",
        "owning_issue": 516,
        "runner": "reference/run_longmemeval.py",
        "supporting_runners": (),
        "implementation_status": "implemented_bounded_profile",
        "external_evidence_status": "external_full_run_not_asserted_by_registry",
        "dimensions": (
            "retrieval",
            "currentness",
            "governance",
            "efficiency",
            "evaluator_integrity",
            "reproducibility",
        ),
        "description": (
            "LongMemEval session/turn retrieval and knowledge-update currentness profile "
            "with no-memory, lexical-overlap, and governed Agent Memory arms."
        ),
    },
)


def list_profiles() -> list[dict]:
    """Return stable profile metadata sorted by profile id."""

    return [deepcopy(profile) for profile in sorted(_PROFILES, key=lambda item: item["profile_id"])]


def get_profile(profile_id: str) -> dict:
    """Return one registered profile or raise KeyError."""

    for profile in _PROFILES:
        if profile["profile_id"] == profile_id:
            return deepcopy(profile)
    raise KeyError(profile_id)
