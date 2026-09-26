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
        "external_evidence": (
            {
                "variant": "lite_protocol_comparable_99_query_100_edge",
                "status": "blocked",
                "blocker": "exact redacted past-task projections and batch/distractor selection provenance (#467)",
            },
        ),
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
        "external_evidence_status": "longmemeval_s_full_complete_m_not_run_qa_not_run",
        "external_evidence": (
            {
                "variant": "longmemeval_s_cleaned",
                "status": "complete",
                "dataset_revision": "xiaowu0162/longmemeval-cleaned@98d7416c24c778c2fee6e6f3006e7a073259d48f",
                "input_sha256": "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442",
                "agent_memory_revision": "f73b872c7f062d0b1e80b4812650b854e3bd2ac8",
                "report": "reports/benchmarks/longmemeval/longmemeval-s-full-f73b872.json",
                "evidence_pr": 536,
            },
            {"variant": "longmemeval_m_cleaned", "status": "not_run"},
            {"variant": "upstream_model_judged_qa", "status": "not_run"},
        ),
        "product_findings": (
            {"issue": 531, "summary": "currentness ordering: anti-recency exact ties and stale-higher-score cases"},
            {"issue": 538, "summary": "default post-admission ranking below the lexical baseline"},
            {"issue": 522, "summary": "commit and recall cost grow with store size"},
        ),
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
    {
        "profile_id": "agent-memory-agentmembench-memdialogue-operational-v1",
        "benchmark_id": "agentmembench-memdialogue",
        "owning_issue": 517,
        "runner": "reference/run_agentmembench.py",
        "supporting_runners": (),
        "implementation_status": "implemented_bounded_profile",
        "external_evidence_status": "memdialogue_v2_upstream_defaults_complete_llm_judge_not_run",
        "external_evidence": (
            {
                "variant": "memdialogue_v2_upstream_defaults",
                "status": "complete",
                "dataset_revision": "mazaiying/AgentMemBench@186c9a54edd47aae42d8b6990520f8e902b60303",
                "input_sha256": "33632710ae6495b95724df455ff6f9947d231ee68ebc0ef10eb8291fd55ca2a6",
                "agent_memory_revision": "03197cd5c866b890b1f9b4505eee3b6f93bcbe2b",
                "report": "reports/benchmarks/agentmembench/memdialogue-v2-agent_memory-03197cd.json",
                "evidence_pr": 533,
            },
            {"variant": "upstream_llm_judged_retrieval_recall", "status": "not_run"},
            {"variant": "llm_portability_m6", "status": "not_run"},
        ),
        "product_findings": (
            {"issue": 531, "summary": "independent newer writes lose to stale writes (staleness 1.00)"},
            {"issue": 530, "summary": "public handle is thread-affine (concurrency success 0.0)"},
            {"issue": 522, "summary": "write and recall latency grow with retained-state and tenant size"},
        ),
        "dimensions": (
            "retrieval",
            "currentness",
            "governance",
            "efficiency",
            "evaluator_integrity",
            "reproducibility",
        ),
        "description": (
            "AgentMemBench MemDialogue operational phases (write, exact-source retrieval, "
            "conflict/currentness, isolation, deletion, concurrency, scale) with no-memory, "
            "lexical-overlap, and governed Agent Memory arms."
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
