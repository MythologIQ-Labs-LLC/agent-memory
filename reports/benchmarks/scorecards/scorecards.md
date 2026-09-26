# Memory Evaluation scorecards

Generated deterministically from normalized run manifests by `scripts/build_benchmark_scorecards.py`. No aggregate score is defined; `authority_effect: none`.

Reading rules: each Δ outcome applies one metric's own direction and says nothing about the system overall. Read related metrics together; for example, a no-memory system's zero staleness comes with a zero new-fact rate. Systems share a table only when benchmark, frozen input, task profile, and selection match. `not_measured`, `not_applicable`, `blocked`, and `not_run` are never zero.

## Portfolio status

| profile | issue | evidence variant | status | systems run | dimensions measured | findings |
| --- | --- | --- | --- | --- | --- | --- |
| `agent-memory-agentmembench-memdialogue-operational-v1` | #517 | memdialogue_v2_upstream_defaults | complete | agent_memory, lexical_overlap, no_memory | currentness, efficiency, governance, reproducibility, retrieval | #531, #530, #522 |
|  |  | upstream_llm_judged_retrieval_recall | not_run |  |  |  |
|  |  | llm_portability_m6 | not_run |  |  |  |
| `agent-memory-longmemeval-retrieval-currentness-v1` | #516 | longmemeval_s_cleaned | complete | agent_memory, lexical_overlap, no_memory | currentness, efficiency, governance, reproducibility, retrieval | #531, #538, #522 |
|  |  | longmemeval_m_cleaned | not_run |  |  |  |
|  |  | upstream_model_judged_qa | not_run |  |  |  |
| `swe-context-bench-lite-external-retrieval-v1` | #467 | lite_protocol_comparable_99_query_100_edge | blocked | none | none | none |

## agentmembench-memdialogue — agent-memory-agentmembench-memdialogue-operational-v1

Input sha256 `33632710ae6495b95724df455ff6f9947d231ee68ebc0ef10eb8291fd55ca2a6` · source `186c9a54edd47aae42d8b6990520f8e902b60303` · selection `upstream load_records: source-unique, event-type-stratified, numpy default_rng(seed)` (n=1000) · baseline for deltas: `lexical_overlap`

### retrieval (no_memory=partial, lexical_overlap=partial, agent_memory=partial)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| exact_source_recall_at_5 | 0.000 | 0.912 | 0.889 | -0.912 (regressed) | -0.023 (regressed) |
| exact_source_recall_at_5_personal_fact | 0.000 | 0.972 | 0.938 | -0.972 (regressed) | -0.034 (regressed) |
| exact_source_recall_at_5_task_request | 0.000 | 0.852 | 0.840 | -0.852 (regressed) | -0.012 (regressed) |
| upstream_llm_judged_recall_at_k | not_measured | not_measured | not_measured | state_not_measured | state_not_measured |
| write_success_rate | 0.000 | 1.000 | 1.000 | -1.000 (regressed) | +0.000 (unchanged) |

### currentness (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| dual_version_rate | 0.000 | 0.000 | 0.000 | +0.000 (unchanged) | +0.000 (unchanged) |
| new_fact_rate | 0.000 | 0.200 | 0.000 | -0.200 (regressed) | -0.200 (regressed) |
| staleness_rate | 0.000 | 0.800 | 1.000 | -0.800 (improved) | +0.200 (regressed) |

### reasoning (no_memory=not_measured, lexical_overlap=not_measured, agent_memory=not_measured)

- agent_memory: no answer-generation or LLM-judged phase was run
- lexical_overlap: no answer-generation or LLM-judged phase was run
- no_memory: no answer-generation or LLM-judged phase was run

### governance (no_memory=partial, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| audited_deletion_rate | not_applicable | 1.000 | 1.000 | state_not_measured | +0.000 (unchanged) |
| cross_user_leak_rate | 0.000 | 0.000 | 0.000 | +0.000 (unchanged) | +0.000 (unchanged) |

### efficiency (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| concurrency_16_operation_success_rate | 1.000 | 1.000 | 0.000 | +0.000 (unchanged) | -1.000 (regressed) |
| concurrency_1_operation_success_rate | 1.000 | 1.000 | 0.000 | +0.000 (unchanged) | -1.000 (regressed) |
| concurrency_4_operation_success_rate | 1.000 | 1.000 | 0.000 | +0.000 (unchanged) | -1.000 (regressed) |
| concurrency_8_operation_success_rate | 1.000 | 1.000 | 0.000 | +0.000 (unchanged) | -1.000 (regressed) |
| peak_rss_mb | 52.700 | 52.700 | 678.400 | +0.000 (unchanged) | +625.700 (regressed) |
| retrieval_read_latency_mean_ms | 0.001 | 0.160 | 1,273.7 | -0.159 (improved) | +1273.522 (regressed) |
| retrieval_read_latency_p95_ms | 0.001 | 0.234 | 2,059.0 | -0.233 (improved) | +2058.750 (regressed) |
| retrieval_write_latency_mean_ms | 0.001 | 0.001 | 56.791 | -0.001 (improved) | +56.790 (regressed) |
| scale_1000_read_latency_mean_ms | 0.000 | 0.049 | 497.235 | -0.049 (improved) | +497.186 (regressed) |
| scale_1000_recall_at_3 | 0.000 | 1.000 | 1.000 | -1.000 (regressed) | +0.000 (unchanged) |
| scale_1000_write_latency_mean_ms | 0.000 | 0.001 | 52.595 | -0.000 (improved) | +52.594 (regressed) |
| scale_100_read_latency_mean_ms | 0.000 | 0.010 | 41.877 | -0.010 (improved) | +41.867 (regressed) |
| scale_100_recall_at_3 | 0.000 | 1.000 | 1.000 | -1.000 (regressed) | +0.000 (unchanged) |
| scale_100_write_latency_mean_ms | 0.001 | 0.001 | 7.949 | -0.000 (improved) | +7.948 (regressed) |

### evaluator_integrity (no_memory=not_measured, lexical_overlap=not_measured, agent_memory=not_measured)

- agent_memory: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run
- lexical_overlap: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run
- no_memory: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run

### reproducibility (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| agent_memory_worktree_clean | true | true | true | comparable_non_numeric | comparable_non_numeric |
| input_matches_upstream_release | true | true | true | comparable_non_numeric | comparable_non_numeric |
| input_sha256_bound | true | true | true | comparable_non_numeric | comparable_non_numeric |

## longmemeval — agent-memory-longmemeval-retrieval-currentness-v1:session

Input sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` · source `9e0b455f4ef0e2ab8f2e582289761153549043fc` · selection `all` (n=500) · baseline for deltas: `lexical_overlap`

### retrieval (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| ndcg_any@10 | 0.000 | 0.793 | 0.756 | -0.793 (regressed) | -0.037 (regressed) |
| ndcg_any@5 | 0.000 | 0.767 | 0.722 | -0.767 (regressed) | -0.045 (regressed) |
| recall_all@10 | 0.000 | 0.826 | 0.797 | -0.826 (regressed) | -0.029 (regressed) |
| recall_all@5 | 0.000 | 0.730 | 0.675 | -0.730 (regressed) | -0.055 (regressed) |

### currentness (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| knowledge_update_ndcg_any@10 | 0.000 | 0.923 | 0.916 | -0.923 (regressed) | -0.007 (regressed) |
| knowledge_update_ndcg_any@5 | 0.000 | 0.917 | 0.912 | -0.917 (regressed) | -0.005 (regressed) |
| knowledge_update_recall_all@10 | 0.000 | 0.944 | 0.944 | -0.944 (regressed) | +0.000 (unchanged) |
| knowledge_update_recall_all@5 | 0.000 | 0.917 | 0.931 | -0.917 (regressed) | +0.014 (improved) |
| latest_gold_ranked_first | 0.000 | 0.457 | 0.343 | -0.457 (regressed) | -0.114 (regressed) |

### reasoning (no_memory=not_measured, lexical_overlap=not_measured, agent_memory=not_measured)

- agent_memory: upstream model-judged QA was not run
- lexical_overlap: upstream model-judged QA was not run
- no_memory: upstream model-judged QA was not run

### governance (no_memory=not_applicable, lexical_overlap=not_applicable, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| candidate_count_total | absent | absent | 22631 | metric_missing | metric_missing |
| refused_candidate_count_total | absent | absent | 0 | metric_missing | metric_missing |
| unmapped_admitted_count_total | absent | absent | 0 | metric_missing | metric_missing |

### efficiency (no_memory=partial, lexical_overlap=partial, agent_memory=partial)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| backend_wall_seconds | 0.156 | 1.612 | 169.339 | -1.456 (improved) | +167.727 (regressed) |
| ingest_seconds_total | absent | absent | 149.417 | metric_missing | metric_missing |
| peak_rss_mb | not_measured | not_measured | not_measured | state_not_measured | state_not_measured |
| recall_seconds_max | absent | absent | 0.089 | metric_missing | metric_missing |
| recall_seconds_total | absent | absent | 10.688 | metric_missing | metric_missing |
| store_size_bytes | not_measured | not_measured | not_measured | state_not_measured | state_not_measured |

### evaluator_integrity (no_memory=not_measured, lexical_overlap=not_measured, agent_memory=not_measured)

- agent_memory: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run
- lexical_overlap: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run
- no_memory: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run

### reproducibility (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| agent_memory_worktree_clean | true | true | true | comparable_non_numeric | comparable_non_numeric |
| execution_ingestion_failure_count | 0 | 0 | 0 | +0.000 (unchanged) | +0.000 (unchanged) |
| execution_out_of_corpus_returned_count | 0 | 0 | 0 | +0.000 (unchanged) | +0.000 (unchanged) |
| execution_runtime_failure_count | 0 | 0 | 0 | +0.000 (unchanged) | +0.000 (unchanged) |
| input_sha256_bound | true | true | true | comparable_non_numeric | comparable_non_numeric |

## longmemeval — agent-memory-longmemeval-retrieval-currentness-v1:turn

Input sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` · source `9e0b455f4ef0e2ab8f2e582289761153549043fc` · selection `all` (n=500) · baseline for deltas: `lexical_overlap`

### retrieval (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| ndcg_any@10 | 0.000 | 0.560 | 0.528 | -0.560 (regressed) | -0.032 (regressed) |
| ndcg_any@5 | 0.000 | 0.527 | 0.502 | -0.527 (regressed) | -0.025 (regressed) |
| ndcg_any@50 | 0.000 | 0.598 | 0.578 | -0.598 (regressed) | -0.021 (regressed) |
| recall_all@10 | 0.000 | 0.587 | 0.525 | -0.587 (regressed) | -0.062 (regressed) |
| recall_all@5 | 0.000 | 0.487 | 0.439 | -0.487 (regressed) | -0.048 (regressed) |
| recall_all@50 | 0.000 | 0.761 | 0.764 | -0.761 (regressed) | +0.002 (improved) |

### currentness (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| knowledge_update_ndcg_any@10 | 0.000 | 0.704 | 0.691 | -0.704 (regressed) | -0.012 (regressed) |
| knowledge_update_ndcg_any@5 | 0.000 | 0.673 | 0.668 | -0.673 (regressed) | -0.005 (regressed) |
| knowledge_update_ndcg_any@50 | 0.000 | 0.725 | 0.720 | -0.725 (regressed) | -0.006 (regressed) |
| knowledge_update_recall_all@10 | 0.000 | 0.806 | 0.736 | -0.806 (regressed) | -0.069 (regressed) |
| knowledge_update_recall_all@5 | 0.000 | 0.681 | 0.639 | -0.681 (regressed) | -0.042 (regressed) |
| knowledge_update_recall_all@50 | 0.000 | 0.917 | 0.903 | -0.917 (regressed) | -0.014 (regressed) |
| latest_gold_ranked_first | 0.000 | 0.614 | 0.486 | -0.614 (regressed) | -0.129 (regressed) |

### reasoning (no_memory=not_measured, lexical_overlap=not_measured, agent_memory=not_measured)

- agent_memory: upstream model-judged QA was not run
- lexical_overlap: upstream model-judged QA was not run
- no_memory: upstream model-judged QA was not run

### governance (no_memory=not_applicable, lexical_overlap=not_applicable, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| candidate_count_total | absent | absent | 103356 | metric_missing | metric_missing |
| refused_candidate_count_total | absent | absent | 0 | metric_missing | metric_missing |
| unmapped_admitted_count_total | absent | absent | 0 | metric_missing | metric_missing |

### efficiency (no_memory=partial, lexical_overlap=partial, agent_memory=partial)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| backend_wall_seconds | 0.665 | 2.680 | 2,215.5 | -2.015 (improved) | +2212.785 (regressed) |
| ingest_seconds_total | absent | absent | 2,162.5 | metric_missing | metric_missing |
| peak_rss_mb | not_measured | not_measured | not_measured | state_not_measured | state_not_measured |
| recall_seconds_max | absent | absent | 0.172 | metric_missing | metric_missing |
| recall_seconds_total | absent | absent | 42.029 | metric_missing | metric_missing |
| store_size_bytes | not_measured | not_measured | not_measured | state_not_measured | state_not_measured |

### evaluator_integrity (no_memory=not_measured, lexical_overlap=not_measured, agent_memory=not_measured)

- agent_memory: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run
- lexical_overlap: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run
- no_memory: evaluator-integrity mutation probes for this profile run separately (reference/run_benchmark_integrity_mutants.py, #518); they are not bound to this run

### reproducibility (no_memory=measured, lexical_overlap=measured, agent_memory=measured)

| metric | no_memory | lexical_overlap | agent_memory | Δ no_memory vs lexical_overlap | Δ agent_memory vs lexical_overlap |
| --- | ---: | ---: | ---: | --- | --- |
| agent_memory_worktree_clean | true | true | true | comparable_non_numeric | comparable_non_numeric |
| execution_ingestion_failure_count | 0 | 0 | 0 | +0.000 (unchanged) | +0.000 (unchanged) |
| execution_out_of_corpus_returned_count | 0 | 0 | 0 | +0.000 (unchanged) | +0.000 (unchanged) |
| execution_runtime_failure_count | 0 | 0 | 0 | +0.000 (unchanged) | +0.000 (unchanged) |
| input_sha256_bound | true | true | true | comparable_non_numeric | comparable_non_numeric |
