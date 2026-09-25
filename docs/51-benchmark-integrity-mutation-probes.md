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

The harness starts from a clean synthetic retrieval-evaluation baseline and applies controlled mutations:

| Probe | Required detection |
|---|---|
| admitted noise | false admissions rise and precision falls |
| missing gold edge | false refusals rise and recall falls without changing the gold denominator |
| candidate/admission collapse | candidate recall remains stable while improper final admission is penalized |
| rank inversion | nDCG@1 falls even when final recall remains preserved |
| admission refusal | candidate recall and final admitted recall remain independently measurable |

The process exits non-zero if any expected mutation is not detected.

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
