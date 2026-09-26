"""Normalize benchmark-native profile reports into common run manifests (#524).

Normalization maps only observations whose meaning is stable within one frozen
benchmark input and task profile. Everything the native report contains is kept under
``native_results`` so no benchmark semantics are lost. Nothing absent from the native
report is invented: unmeasured dimensions and metrics are declared ``not_measured`` or
``not_applicable`` with a reason, never zero.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .contract import dimension_report, metric_observation, validate_run

SYSTEM_KINDS = {"no_memory": "no_memory", "lexical_overlap": "lexical", "agent_memory": "agent_memory"}
_EVALUATOR_INTEGRITY_NOTE = (
    "evaluator-integrity mutation probes for this profile run separately "
    "(reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run"
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _measured(metrics: list[dict[str, Any]]) -> str:
    states = {metric["state"] for metric in metrics}
    if states == {"measured"}:
        return "measured"
    return "partial" if "measured" in states else "not_measured"


def _dimension(metrics: list[dict[str, Any]], notes: list[str] | None = None) -> dict[str, Any]:
    return dimension_report(_measured(metrics), metrics, notes=notes or [])


def _absent(status: str, note: str) -> dict[str, Any]:
    return dimension_report(status, [], notes=[note])


def _reproducibility(
    execution: Mapping[str, Any], input_block: Mapping[str, Any], extra: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    metrics = list(extra or []) + [
        metric_observation("input_sha256_bound", value=bool(input_block.get("sha256"))),
        metric_observation(
            "agent_memory_worktree_clean",
            value=execution.get("agent_memory_worktree_dirty") is False,
            note="false or unknown means the run cannot be bound to an exact committed tree",
        ),
    ]
    if "matches_upstream_release" in input_block:
        metrics.append(metric_observation("input_matches_upstream_release", value=bool(input_block["matches_upstream_release"])))
    return _dimension(metrics)


def _environment(execution: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("python", "implementation", "platform", "numpy", "agent_memory_package_version", "resource_consumption")
    return {key: execution[key] for key in keys if key in execution}


# LongMemEval ---------------------------------------------------------------


def _longmemeval_manifest(report: Mapping[str, Any], plane: str, backend: str) -> dict[str, Any]:
    execution = report["execution"]
    input_block = report["input"]
    native = report["planes"][plane]["backends"][backend]
    aggregate = native["aggregate"]
    scored = aggregate["evaluated_question_count"]
    population = "scored questions (upstream _abs and no-user-target exclusions applied)"
    retrieval = [
        metric_observation(
            name,
            value=value,
            direction="higher_better",
            denominator=scored,
            unit="ratio",
            population=population,
        )
        for name, value in sorted(aggregate["headline"].items())
    ]
    knowledge_update = native["currentness"]["knowledge_update"]
    latest = native["currentness"]["latest_gold_ranked_first"]
    currentness = [
        metric_observation(
            f"knowledge_update_{name}",
            value=value,
            direction="higher_better",
            denominator=knowledge_update["evaluated_question_count"],
            unit="ratio",
            population="scored knowledge-update questions",
        )
        for name, value in sorted(knowledge_update["headline"].items())
    ]
    currentness.append(
        metric_observation(
            "latest_gold_ranked_first",
            value=latest["rate"],
            direction="higher_better",
            denominator=latest["applicable_question_count"],
            unit="ratio",
            population="knowledge-update questions with gold on >=2 distinct dates",
            note="profile-local diagnostic; not an upstream LongMemEval metric",
        )
    )
    failures = native["failures"]
    efficiency = [
        metric_observation(
            "backend_wall_seconds",
            value=native["timing"]["wall_seconds"],
            direction="lower_better",
            denominator=input_block["question_count"],
            unit="seconds",
            population="all questions",
        )
    ]
    if backend == "agent_memory":
        governance_native = native["governance"]
        governance = [
            metric_observation("candidate_count_total", value=governance_native["candidate_count_total"], unit="count"),
            metric_observation("refused_candidate_count_total", value=governance_native["refused_candidate_count_total"], unit="count"),
            metric_observation(
                "unmapped_admitted_count_total",
                value=governance_native["unmapped_admitted_count_total"],
                direction="zero_target",
                unit="count",
            ),
        ]
        governance_dimension = _dimension(
            governance,
            ["one tenant and scope per question: admission is exercised but not a filter in this workload"],
        )
        efficiency.extend(
            [
                metric_observation("ingest_seconds_total", value=native["timing"]["ingest_seconds_total"], direction="lower_better", unit="seconds"),
                metric_observation("recall_seconds_total", value=native["timing"]["recall_seconds_total"], direction="lower_better", unit="seconds"),
                metric_observation("recall_seconds_max", value=native["timing"]["recall_seconds_max"], direction="lower_better", unit="seconds"),
            ]
        )
    else:
        governance_dimension = _absent("not_applicable", f"{backend} has no governed admission path")
    efficiency.append(
        metric_observation(
            "peak_rss_mb",
            state="not_measured",
            note="peak RSS was measured once for the whole multi-backend process and is not attributable to one backend",
        )
    )
    efficiency.append(metric_observation("store_size_bytes", state="not_measured", note="per-question stores were temporary"))
    efficiency_notes = ["single-process local execution; " + execution.get("platform", "platform unknown")]
    failure_metrics = [
        metric_observation(f"execution_{name}", value=value, direction="zero_target", unit="count")
        for name, value in sorted(failures.items())
    ]
    return {
        "schema_version": "1.0.0",
        "run_id": f"longmemeval:{plane}:{backend}:{execution['agent_memory_revision'][:12]}",
        "status": "complete",
        "benchmark": {
            "id": "longmemeval",
            "source_url": "https://github.com/xiaowu0162/LongMemEval",
            "source_revision": report["upstream"]["revision"],
            "dataset_id": "xiaowu0162/longmemeval-cleaned:" + input_block["path_name"],
            "dataset_revision": execution.get("dataset_revision", "unrecorded"),
            "input_sha256": input_block["sha256"],
            "task_profile": f"{report['profile_id']}:{plane}",
        },
        "system": {
            "id": backend,
            "kind": SYSTEM_KINDS[backend],
            "revision": execution["agent_memory_revision"],
            "adapter_id": "reference/run_longmemeval.py",
            "adapter_revision": execution["agent_memory_revision"],
        },
        "execution": {
            "selection_id": input_block["selection"]["question_ids_sha256"],
            "selection_method": input_block["selection"]["method"],
            "sample_count": input_block["question_count"],
            "started_at": execution["started_at"],
            "elapsed_ms": round(native["timing"]["wall_seconds"] * 1000, 3),
            "environment": _environment(execution),
        },
        "dimensions": {
            "retrieval": _dimension(retrieval),
            "currentness": _dimension(currentness),
            "reasoning": _absent("not_measured", "upstream model-judged QA was not run"),
            "governance": governance_dimension,
            "efficiency": _dimension(efficiency, efficiency_notes),
            "evaluator_integrity": _absent("not_measured", _EVALUATOR_INTEGRITY_NOTE),
            "reproducibility": _reproducibility(execution, input_block, failure_metrics),
        },
        "native_results": {
            "profile_id": report["profile_id"],
            "plane": plane,
            "backend": backend,
            "aggregate": aggregate,
            "by_question_type": native["by_question_type"],
            "currentness": native["currentness"],
            "failures": failures,
            "timing": native["timing"],
            **({"governance": native["governance"]} if "governance" in native else {}),
            "comparability": report["comparability"],
            "input": dict(input_block),
        },
        "limitations": [
            "retrieval/currentness only; not answer-generation quality",
            "lexical_overlap is a profile-local baseline, not an upstream BM25/dense retriever",
        ],
        "artifacts": [],
        "authority_effect": "none",
    }


def normalize_longmemeval(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One manifest per (plane, backend); runs compare only within the same plane."""

    manifests = []
    for plane in sorted(report["planes"]):
        for backend in sorted(report["planes"][plane]["backends"]):
            manifests.append(validate_run(_longmemeval_manifest(report, plane, backend)))
    return manifests


# AgentMemBench / MemDialogue -----------------------------------------------


def _ratio(metric_id: str, value: Any, *, direction: str, denominator: int, population: str, note: str | None = None) -> dict[str, Any]:
    if value is None:
        return metric_observation(metric_id, state="not_applicable", direction=direction, note=note or "undefined for this system")
    return metric_observation(
        metric_id, value=value, direction=direction, denominator=denominator, unit="ratio", population=population, note=note
    )


def normalize_agentmembench(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One manifest per backend in a native AgentMemBench profile report."""

    manifests = []
    execution = report["execution"]
    input_block = report["input"]
    params = report["parameters"]
    for backend, native in sorted(report["backends"].items()):
        phases = native["phases"]
        if native.get("phase_errors"):
            status = "partial"
        else:
            status = "complete"
        retrieval_native = phases["retrieval"]
        retrieval = [
            _ratio(
                "exact_source_recall_at_5",
                retrieval_native["exact_source_recall_at_k"],
                direction="higher_better",
                denominator=retrieval_native["records"],
                population="stratified source-unique records, 10 per user group",
                note="profile-local deterministic metric; upstream LLM-judged recall not run",
            ),
            _ratio("write_success_rate", retrieval_native["write_success_rate"], direction="higher_better", denominator=retrieval_native["records"], population="retrieval-phase writes"),
            metric_observation("upstream_llm_judged_recall_at_k", state="not_measured", direction="higher_better", note="no judge endpoint provisioned"),
        ]
        for event_type, value in sorted(retrieval_native["exact_source_recall_by_event_type"].items()):
            retrieval.append(metric_observation(f"exact_source_recall_at_5_{event_type.lower()}", value=value, direction="higher_better", unit="ratio", population=f"{event_type} records"))
        conflict = phases["conflict"]
        currentness = [
            _ratio("new_fact_rate", conflict["new_fact_rate"], direction="higher_better", denominator=conflict["pairs"], population="independent old/new write pairs, top-1"),
            _ratio("staleness_rate", conflict["staleness_rate"], direction="lower_better", denominator=conflict["pairs"], population="independent old/new write pairs, top-1"),
            _ratio("dual_version_rate", conflict["dual_version_rate"], direction="descriptive", denominator=conflict["pairs"], population="independent old/new write pairs, top-1"),
        ]
        isolation = phases["isolation"]
        deletion = phases["deletion"]
        governance = [
            _ratio("cross_user_leak_rate", isolation["cross_user_leak_rate"], direction="zero_target", denominator=isolation["cross_user_queries"], population="cross-user canary queries"),
            _ratio(
                "audited_deletion_rate",
                deletion["audited_deletion_rate"],
                direction="higher_better",
                denominator=deletion["records"],
                population="deletion canaries visible before delete",
                note=None if deletion["audited_deletion_rate"] is not None else "nothing was visible before deletion",
            ),
        ]
        efficiency = [
            metric_observation("retrieval_write_latency_mean_ms", value=retrieval_native["write_latency"]["mean_ms"], direction="lower_better", unit="ms", population="retrieval-phase writes"),
            metric_observation("retrieval_read_latency_mean_ms", value=retrieval_native["read_latency"]["mean_ms"], direction="lower_better", unit="ms", population="retrieval-phase reads"),
            metric_observation("retrieval_read_latency_p95_ms", value=retrieval_native["read_latency"]["p95_ms"], direction="lower_better", unit="ms", population="retrieval-phase reads"),
        ]
        for scale, values in sorted(phases["scale"].items(), key=lambda item: int(item[0])):
            efficiency.append(metric_observation(f"scale_{scale}_recall_at_3", value=values["recall_at_3"], direction="higher_better", unit="ratio", population=f"{scale} stored facts"))
            efficiency.append(metric_observation(f"scale_{scale}_write_latency_mean_ms", value=values["write_latency"]["mean_ms"], direction="lower_better", unit="ms", population=f"{scale} stored facts"))
            efficiency.append(metric_observation(f"scale_{scale}_read_latency_mean_ms", value=values["read_latency"]["mean_ms"], direction="lower_better", unit="ms", population=f"{scale} stored facts"))
        for workers, values in sorted(phases["concurrency"].items(), key=lambda item: int(item[0])):
            efficiency.append(metric_observation(f"concurrency_{workers}_operation_success_rate", value=values["operation_success_rate"], direction="higher_better", unit="ratio", denominator=values["records"], population=f"{workers} worker threads"))
        rss = execution.get("resource_consumption", {}).get("peak_rss_mb_process") if isinstance(execution.get("resource_consumption"), dict) else None
        if rss is not None and execution.get("backends") == [backend]:
            efficiency.append(metric_observation("peak_rss_mb", value=rss, direction="lower_better", unit="MB", population="whole process, one backend"))
        else:
            efficiency.append(metric_observation("peak_rss_mb", state="not_measured", note="not attributable to this backend"))
        manifests.append(
            validate_run(
                {
                    "schema_version": "1.0.0",
                    "run_id": f"agentmembench-memdialogue:{backend}:{execution['agent_memory_revision'][:12]}",
                    "status": status,
                    "benchmark": {
                        "id": "agentmembench-memdialogue",
                        "source_url": "https://github.com/mazaiying/AgentMemBench",
                        "source_revision": report["upstream"]["revision"],
                        "dataset_id": "mazaiying/AgentMemBench:" + report["upstream"]["dataset"],
                        "dataset_revision": report["upstream"]["revision"],
                        "input_sha256": input_block["sha256"],
                        "task_profile": report["profile_id"],
                    },
                    "system": {
                        "id": backend,
                        "kind": SYSTEM_KINDS[backend],
                        "revision": execution["agent_memory_revision"],
                        "configuration_digest": _digest(params),
                        "adapter_id": "reference/run_agentmembench.py",
                        "adapter_revision": execution["agent_memory_revision"],
                    },
                    "execution": {
                        "selection_id": input_block["selection"]["source_ids_sha256"],
                        "selection_method": input_block["selection"]["method"],
                        "sample_count": input_block["selection"]["records"],
                        "started_at": execution["started_at"],
                        "elapsed_ms": round(native["wall_seconds"] * 1000, 3),
                        "environment": _environment(execution),
                        "seed": params["seed"],
                    },
                    "dimensions": {
                        "retrieval": _dimension(retrieval),
                        "currentness": _dimension(currentness),
                        "reasoning": _absent("not_measured", "no answer-generation or LLM-judged phase was run"),
                        "governance": _dimension(governance),
                        "efficiency": _dimension(efficiency, ["local in-process latency; not comparable to upstream service-backed latency"]),
                        "evaluator_integrity": _absent("not_measured", _EVALUATOR_INTEGRITY_NOTE),
                        "reproducibility": _reproducibility(execution, input_block),
                    },
                    "native_results": {
                        "profile_id": report["profile_id"],
                        "backend": backend,
                        "phases": phases,
                        "phase_errors": native.get("phase_errors", {}),
                        "governance": native.get("governance", {}),
                        "parameters": params,
                        "comparability": report["comparability"],
                        "input": dict(input_block),
                    },
                    "limitations": [
                        "M6 LLM portability not exercised",
                        "upstream reference systems (Mem0, Graphiti, LangMem, Letta, Naive RAG) not reproduced",
                    ],
                    "artifacts": [],
                    "authority_effect": "none",
                }
            )
        )
    return manifests
