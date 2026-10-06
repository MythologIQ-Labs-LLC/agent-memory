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


def _longmemeval_system(execution: Mapping[str, Any], backend: str) -> tuple[dict[str, Any], str]:
    """System identity for one backend: built-in backends bind the repository revision,
    externally registered backends (#640 lanes) bind the identity the runner recorded."""

    external = (execution.get("external_backends") or {}).get(backend)
    if external is not None:
        system = {
            "id": external["system_id"],
            "kind": external["system_kind"],
            "revision": external["system_revision"],
            "configuration_digest": _digest(external["configuration"]),
            "adapter_id": external["adapter_id"],
            "adapter_revision": external["adapter_revision"],
        }
        return system, external["system_revision"]
    if backend not in SYSTEM_KINDS:
        raise ValueError(f"backend {backend!r} is neither built in nor recorded under execution.external_backends")
    system = {
        "id": backend,
        "kind": SYSTEM_KINDS[backend],
        "revision": execution["agent_memory_revision"],
        "adapter_id": "reference/run_longmemeval.py",
        "adapter_revision": execution["agent_memory_revision"],
    }
    return system, execution["agent_memory_revision"]


def _longmemeval_manifest(report: Mapping[str, Any], plane: str, backend: str) -> dict[str, Any]:
    execution = report["execution"]
    input_block = report["input"]
    native = report["planes"][plane]["backends"][backend]
    system, system_revision = _longmemeval_system(execution, backend)
    external = (execution.get("external_backends") or {}).get(backend)
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
    else:
        governance_dimension = _absent("not_applicable", f"{backend} has no governed admission path")
    if "ingest_seconds_total" in native["timing"]:
        efficiency.extend(
            [
                metric_observation("ingest_seconds_total", value=native["timing"]["ingest_seconds_total"], direction="lower_better", unit="seconds"),
                metric_observation("recall_seconds_total", value=native["timing"]["recall_seconds_total"], direction="lower_better", unit="seconds"),
                metric_observation("recall_seconds_max", value=native["timing"]["recall_seconds_max"], direction="lower_better", unit="seconds"),
            ]
        )
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
        "run_id": f"longmemeval:{plane}:{backend}:{system_revision[:12]}",
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
        "system": system,
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
            **({"external_system": native["external_system"]} if "external_system" in native else {}),
            **({"external_backend_identity": external} if external is not None else {}),
            "comparability": report["comparability"],
            "input": dict(input_block),
        },
        "limitations": [
            "retrieval/currentness only; not answer-generation quality",
            "lexical_overlap is a profile-local baseline, not an upstream BM25/dense retriever",
            *(
                [
                    f"{backend} is an externally registered system; its identity and configuration digest come from "
                    "execution.external_backends, and it is comparable only within a frozen same-harness lane"
                ]
                if external is not None
                else []
            ),
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


# AMB / PrecisionMemBench same-harness lane --------------------------------

AMB_PRECISIONMEMBENCH_BENCHMARK_ID = "amb-precisionmembench"
_AMB_SYSTEM_KINDS = {"repository_runtime": "agent_memory", "harness_builtin": "lexical", "python_package": "external_memory"}
_AMB_ADAPTERS = {
    "agent-memory": "reference/amb_agent_memory_bridge.py",
    "mem0-explicit": "reference/amb_mem0_explicit_bridge.py",
    "bm25": "memory_bench.memory.bm25.BM25MemoryProvider (frozen AMB revision)",
}


def _amb_evidence_directory(record: Mapping[str, Any]) -> str:
    execution = record["execution"]
    return f"reports/benchmarks/amb/{record['lane_id']}/{execution['memory']}-{execution['agent_memory_revision'][:12]}"


def normalize_amb_precisionmembench(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One manifest per accepted lane row, built from its committed ``evidence.json``.

    The record is the bound evidence record ``scripts/import_amb_lane_evidence.py`` wrote
    next to the raw AMB ``EvalSummary``; its ``native_summary`` is the harness's own
    PrecisionMemBench table recomputed from the per-case results. Only that table, the
    execution identity and the input identity are mapped; the record is kept whole under
    ``native_results`` and the raw per-case artifact is referenced by digest, never
    restated. Rows of one lane share the comparison identity (harness revision, fixture
    digest, selection, sample count), so they land on one scorecard with the BM25 row as
    the lexical baseline.
    """

    if record.get("contract_family") != "agent-memory-same-harness-lane-evidence":
        raise ValueError("normalize_amb_precisionmembench expects a same-harness lane evidence record")
    native = record["native_summary"]
    execution = record["execution"]
    input_block = record["input"]
    row = record["row"]
    system = record["system"]
    constraints = execution.get("harness_constraints") or {}
    directory = _amb_evidence_directory(record)
    active_population = "active cases: query-dependent belief ids required (upstream-comparable)"
    retrieval = [
        metric_observation("active_passes", value=native["active_passes"], direction="higher_better", denominator=native["active_total"], unit="count", population=active_population, note="the only number comparable to upstream's Active passes column"),
        metric_observation("structural_passes", value=native["structural_passes"], direction="higher_better", denominator=native["structural_total"], unit="count", population="structural cases: satisfiable by a provider returning nothing"),
        metric_observation("trivially_empty_passes", value=native["trivially_empty_passes"], direction="higher_better", denominator=native["trivially_empty_total"], unit="count", population="trivially-empty cases: satisfiable by a provider returning nothing"),
        metric_observation("total_passes", value=native["total_passes"], direction="higher_better", denominator=native["total_queries"], unit="count", population="all cases", note="includes structural and trivially-empty cases a provider returning nothing can satisfy"),
        metric_observation("mean_precision", value=native["mean_precision"], direction="higher_better", unit="ratio", population="cases with a relevantBeliefs tier"),
        metric_observation("mean_recall", value=native["mean_recall"], direction="higher_better", unit="ratio", population="cases with a relevantBeliefs tier"),
    ]
    efficiency = [
        metric_observation("mean_retrieve_ms", value=native["mean_retrieve_ms"], direction="lower_better", unit="ms", population="all cases", note="provider retrieve wall time on a GitHub-hosted runner; environment-bound"),
        metric_observation("ingestion_time_ms", value=native["ingestion_time_ms"], direction="lower_better", unit="ms", denominator=native["ingested_docs"], population="ingested beliefs", note="harness-measured memory.ingest wall time; environment-bound"),
    ]
    reproducibility = [
        metric_observation("input_sha256_bound", value=bool(input_block.get("sha256")), note=input_block.get("verified_by")),
        metric_observation("full_selection", value=execution.get("full_selection") is True),
        metric_observation("return_cap_unset", value=execution.get("amb_pmb_return_cap") is None, note="AMB_PMB_RETURN_CAP must be unset for the frozen budget"),
        metric_observation("harness_lock_bound", value=bool(constraints.get("uv_lock_git_blob")), note="harness installed under its own uv.lock as pip constraints; lifted pins recorded in native_results.execution.harness_constraints"),
        metric_observation("self_check_recorded", value="precisionmembench-selfcheck.txt" in record.get("files", {}), note="perfect-provider self-check output committed with the row"),
    ]
    files = record.get("files", {})
    artifacts = [
        {"artifact_id": "amb-eval-summary", "kind": "benchmark_native_results", "uri": f"{directory}/single-turn.json", **({"sha256": files["single-turn.json"]} if "single-turn.json" in files else {})},
        {"artifact_id": "execution-identity", "kind": "execution_identity", "uri": f"{directory}/execution-identity.json", **({"sha256": files["execution-identity.json"]} if "execution-identity.json" in files else {})},
        {"artifact_id": "precisionmembench-selfcheck", "kind": "evaluator_integrity_selfcheck", "uri": f"{directory}/precisionmembench-selfcheck.txt", **({"sha256": files["precisionmembench-selfcheck.txt"]} if "precisionmembench-selfcheck.txt" in files else {})},
        {"artifact_id": "lane-evidence-record", "kind": "same_harness_lane_evidence", "uri": f"{directory}/evidence.json"},
    ]
    manifest = {
        "schema_version": "1.0.0",
        "run_id": f"{AMB_PRECISIONMEMBENCH_BENCHMARK_ID}:{execution['split']}:{system['id']}:{system['revision'][:12]}",
        "status": "complete",
        "benchmark": {
            "id": AMB_PRECISIONMEMBENCH_BENCHMARK_ID,
            "source_url": "https://github.com/vectorize-io/agent-memory-benchmark",
            "source_revision": execution["amb_revision"],
            "dataset_id": "tenurehq/precisionmembench:fixtures/{beliefs.seed.json,retrieval.cases.json}",
            "dataset_revision": input_block["dataset_revision"],
            "input_sha256": input_block["sha256"],
            "task_profile": f"{record['lane_id']}:{execution['split']}:{execution['mode']}",
        },
        "system": {
            "id": system["id"],
            "kind": _AMB_SYSTEM_KINDS[system["source_kind"]],
            "revision": system["revision"],
            "configuration_digest": _digest({"provider_key": row["provider_key"], "resolved_packages": system.get("resolved_packages"), "mem0_optional_components": system.get("mem0_optional_components"), "constraints_sha256": constraints.get("constraints_sha256")}),
            "adapter_id": _AMB_ADAPTERS[row["provider_key"]],
            "adapter_revision": execution["amb_revision"] if system["source_kind"] == "harness_builtin" else execution["agent_memory_revision"],
        },
        "execution": {
            "selection_id": input_block["selection_id"],
            "selection_method": "full single-turn case set",
            "sample_count": int(input_block["query_count"]),
            "environment": {
                "runner": "github-hosted ubuntu-latest (Independent AMB Competitive Run)",
                "harness_lock_git_blob": constraints.get("uv_lock_git_blob"),
                "resolved_packages": system.get("resolved_packages"),
                "mem0_optional_components": system.get("mem0_optional_components"),
            },
        },
        "dimensions": {
            "retrieval": _dimension(retrieval, ["active_passes/active_total is the upstream-comparable number; total passes include cases a provider returning nothing can satisfy"]),
            "currentness": _absent("not_applicable", "single-version beliefs; supersession is a scope/exclusion assertion scored natively"),
            "reasoning": _absent("not_applicable", "retrieval mode has no answer generation"),
            "governance": _absent("not_measured", "the cross-user leak case is scored natively inside the 77 cases; no governance dimension is mapped"),
            "efficiency": _dimension(efficiency, ["GitHub-hosted runner; environment-bound and comparable only within one lane execution class"]),
            "evaluator_integrity": _absent("not_measured", "the perfect-provider self-check (scripts/precisionmembench_selfcheck.py) ran before the contestant and its output is committed as an artifact; it is not parsed into a metric"),
            "reproducibility": _dimension(reproducibility),
        },
        "native_results": json.loads(json.dumps(record)),
        "limitations": [
            "retrieval-only belief-id precision; not conversational QA and not comparable to LongMemEval recall_all@k",
            "35 documents and 77 cases: a precision/isolation probe, not a scale benchmark",
            "BM25 is a baseline and Agent Memory the control; no row is a market claim",
            "efficiency is environment-bound (GitHub-hosted runner)",
        ],
        "artifacts": artifacts,
        "authority_effect": "none",
    }
    return [validate_run(manifest)]
