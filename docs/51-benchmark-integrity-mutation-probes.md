# Benchmark Integrity Mutation Probes

## Purpose

Agent Memory now carries a small evaluator-integrity harness for retrieval benchmarks:

```text
reference/run_benchmark_integrity_mutants.py
```

The harness does **not** measure Agent Memory retrieval efficacy. It verifies that the benchmark evaluator itself responds to controlled failures in the expected direction.

That distinction matters because a benchmark pipeline that always emits a plausible report can be more dangerous than a benchmark pipeline that fails loudly.

## Harvest ancestry

This mechanism was added while completing ancestry harvest #470 after reviewing two UOR Foundation verification surfaces.

### `UOR-Foundation/uor-jcs-nfc`

Exact inspected revision:

```text
303591128094362857791930fdc12b73875d1ff6
```

The source remains a provisional RC5 publication. Its canonicalization profile is **not** adopted as Agent Memory memory doctrine. The useful generic lesson is narrower: conformance checks should demonstrate that deliberately broken variants are actually detected, and surviving mutations should be reported rather than silently discarded.

### `UOR-Foundation/PrismPM`

Exact inspected revision:

```text
73d041a46a4e15127e7fdef1dc16a8d592c5ccd3
```

PrismPM similarly distinguishes authority material from executable verification and uses positive/negative corpora plus mutation pressure to detect stale, bypassed, changed, or trivially passing checks.

Agent Memory independently re-expresses that verification lesson. No PrismPM or `uor-jcs-nfc` code, schemas, fixtures, or distinctive prose are copied.

## Current probes

Probes are organized per accepted external benchmark profile (#518). Each profile's mutations respect that benchmark's own semantics and are scored by that profile's existing evaluator, never by a re-implementation.

### SWE-ContextBench (`run_swe_context_bench_harness._quality`)

| Probe | Required detection |
|---|---|
| admitted noise | false admissions rise and precision falls |
| missing gold edge | false refusals rise and recall falls without changing the gold denominator |
| candidate/admission collapse | candidate recall remains stable while improper final admission is penalized |
| rank inversion | nDCG@1 falls even when final recall remains preserved |
| admission refusal | candidate recall and final admitted recall remain independently measurable |

### LongMemEval (`run_longmemeval.score_record` / `summarize`)

The baseline applies an ideal gold-only ranking (most recent gold first, nothing for abstention) to the upstream-shaped synthetic fixture, at session granularity, through the replicated upstream retrieval evaluator.

| Probe | Required detection |
|---|---|
| missing gold | `recall_all@5` falls; scored denominator unchanged |
| irrelevant ahead | an irrelevant session ahead of a gold session lowers `ndcg_any@5`; `recall_all@5` unchanged |
| rank below cutoff | gold pushed below k=1 lowers `recall_all@1` only; `recall_all@5` unchanged |
| stale over current | superseded knowledge-update session ranked first lowers `latest_gold_ranked_first`; recall unchanged |
| suppressed abstention | losing the `_abs` identity changes the scored denominator |
| identity mapping corruption | returned memories mapped to the wrong benchmark ids lower recall |
| cross-scope injection | an item from another question's haystack is counted out-of-corpus and earns no recall |

Known upstream evaluator insensitivity, recorded rather than hidden: upstream `eval_utils.dcg` weights ranks 1 and 2 equally (`rel₁ + rel₂/log₂2 + …`). Displacing a single gold item from rank 1 to rank 2 therefore leaves `ndcg_any` unchanged. The `irrelevant_at_rank_one` probe asserts that this non-detection still holds (`known_insensitivities_confirmed`). For that damage, `recall_all@1` is the sensitive signal. The profile keeps upstream parity and does not silently "fix" upstream arithmetic.

### AgentMemBench / MemDialogue (`run_agentmembench` phase functions)

AgentMemBench's deterministic phases score backend behavior, so these probes wrap an ideal per-user reference store (newest matching memory first) in controlled misbehavior and require the re-expressed upstream phase metrics to notice:

| Probe | Required detection |
|---|---|
| stale over current | conflict `staleness_rate` rises and `new_fact_rate` falls |
| cross-user leak | isolation `cross_user_leak_rate` rises |
| deletion ignored | `audited_deletion_rate` falls |
| write dropped | scale write success and `recall_at_3` fall |
| identity mapping corruption | scale `recall_at_3` falls |

Retrieval is not probed, because `exact_source_recall` is a direct string-membership check and the upstream LLM-judged metric is not run. Concurrency is not probed either, because it measures errors and throughput rather than a scored quality outcome.

The process exits non-zero if any expected detection fails in any exercised profile.

## Governance boundary

```text
mutation-probe pass
    !=
benchmark quality result
    !=
external comparability
    !=
memory authority
```

A passing integrity probe means only that these evaluator failure classes are observable under controlled mutation.

It does not establish that Agent Memory performs well on SWE-ContextBench, LoCoMo, LongMemEval, a production workload, or any other external task.

## Relationship to #467

The real SWE-ContextBench lane remains #467.

The pull-and-run comparison harness and the 99-query / 100-gold-edge runner are already present. Protocol-comparable evidence still requires the exact frozen external past-task projection and batch/distractor provenance.

Mutation integrity strengthens confidence in the evaluator used around that work. It does not manufacture the missing external corpus or turn a synthetic run into a public benchmark result.

## Why this belongs in Agent Memory

Benchmarking is part of memory-system correctness because candidate retrieval, governed admission, currentness, and false-admission/refusal behavior are easy to collapse accidentally into flattering aggregate numbers.

The mutation probes preserve the current doctrine:

```text
candidate generation
    !=
final governed admission

retrieval quality
    !=
governance correctness

benchmark score
    !=
authority
```

This is intentionally a small evaluator guard rather than another benchmark framework.
