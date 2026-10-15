# Plan: #640 credential-free Hindsight same-harness comparator

**change_class**: evaluation
**risk_grade**: L1
**owning_issue**: #640
**parents**: #600, #601
**doctrine**: published reference != same-harness evidence; missing != zero; benchmark score != authority; comparator configuration is frozen before score

## Purpose

Replace the long-deferred, benchmark-shaped Hindsight row with one
benchmark-agnostic Hindsight composition that can run unchanged across the
credential-free PrecisionMemBench retrieval lane and LongMemEval_S retrieval
lane.

This plan does not claim that chunk-only Hindsight represents every Hindsight
product capability. It qualifies one exact, reproducible retrieval composition.

## Frozen product source

Use Hindsight v0.10.2 at the source revision already named by the existing
deferred rows:

`5fc4ce20917b916240cef27c212c387a177f115b`

No later Hindsight source revision may silently satisfy this plan.

## Comparator composition

The candidate composition is the Hindsight v0.10.2 plain-retrieval posture:

```text
LLM provider                 none
retain extraction mode       chunks
observations                  false
temporal retrieval            false
graph retrieval               false
reranking                     false
embedding provider            onnx
embedding model               intfloat/multilingual-e5-small
embedding snapshot revision   03415a4be176a1620747c692ed433219fabc3def
embedding ONNX path           onnx/model.onnx
embedding dimensions          384
```

The ONNX model graph expected SHA-256 is:

`ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665`

The tokenizer/configuration files must be obtained from the same immutable
snapshot revision and their actual downloaded SHA-256 values recorded in the
execution identity before any benchmark query is scored.

### Why this composition

At the pinned Hindsight source:

- provider `none` is a first-class no-LLM mode;
- retain is forced to chunk storage rather than LLM fact extraction;
- reflect/consolidation are unavailable instead of silently invoking a model;
- the product ships a plain-retrieval template that disables observations,
  temporal retrieval, graph retrieval and reranking;
- recall therefore remains a product retrieval path without a benchmark-specific
  retain mission or provider credential.

That is a materially cleaner comparator than the upstream AMB Hindsight adapter,
whose benchmark-specific retain mission is already recorded as unacceptable.

## Independence constraints

The exact same Hindsight product composition is used in every applicable lane.

Forbidden:

- a PrecisionMemBench-specific retain mission;
- a LongMemEval-specific retain mission;
- different embedding models between benchmarks;
- an LLM extractor on one benchmark but not the other;
- benchmark-specific graph/temporal/reranker toggles;
- score-dependent parameter changes;
- injecting temporal metadata that the benchmark did not supply;
- using gold, labels or benchmark metadata in retain or recall;
- editing an accepted lane in place.

If the same composition cannot be expressed faithfully in one harness, that row
is `unsupported` or `blocked`; the configuration is not changed to force it
through.

## H1 — Immutable embedding bootstrap

Add a repository-owned bootstrap/verifier that:

1. downloads or restores the embedding model and tokenizer from the exact
   snapshot revision;
2. refuses any floating revision;
3. verifies the ONNX graph SHA-256 above;
4. computes and records SHA-256 for every tokenizer/config file actually read;
5. records the resolved local paths;
6. refuses execution if any expected byte changes.

CI may cache these bytes only by a key containing the immutable snapshot
revision and verifier identity. Cache presence is never verification.

## H2 — Repository-owned Hindsight adapter

Do not use `memory_bench.memory.hindsight` as the frozen product identity.

Implement a repository-owned adapter/bridge that:

- owns only harness translation;
- invokes the pinned Hindsight product API/composition;
- has no benchmark-specific prompt or retrieval heuristic;
- maps benchmark documents/turns to Hindsight retain inputs without semantic
  rewriting;
- maps Hindsight recall results back to exact corpus identities;
- refuses an unmappable result rather than guessing;
- records Hindsight source revision, resolved package set, bank configuration,
  embedding artifact digests and adapter blob;
- exposes no authority effect.

The bridge must have deterministic tests with a fake product seam. Product smoke
uses real Hindsight but no benchmark score.

## H3 — Product smoke before lane freeze

Before any benchmark score exists, run a bounded real-product smoke showing:

- Hindsight starts at the pinned source/configuration;
- provider `none` makes no LLM call and requires no LLM credential;
- chunk retain succeeds;
- recall succeeds;
- every returned item maps to an inserted corpus identity;
- the embedding verifier passes;
- the effective bank configuration equals this plan.

The smoke is product qualification only and is not entered as a benchmark row.

## H4 — New same-harness lane identities

Existing accepted lane ids are immutable.

After H1–H3 pass, create new lane identities for the Hindsight qualification.
The freeze PR chooses the exact ids and records them before any score. Each
applicable lane includes and re-executes:

- Agent Memory control;
- the existing lexical/BM25 baseline;
- Mem0 OSS 2.2.1 explicit-memory comparator;
- Hindsight v0.10.2 chunk-retrieval comparator.

All rows execute in the same frozen lane generation. An old accepted score is
never copied into the new card merely because its configuration looks equal.

The Hindsight row declares its capability posture explicitly as chunk-based
retrieval with no LLM extraction, observation synthesis, temporal arm, graph arm
or reranker. That bounded posture is part of the result.

## H5 — PrecisionMemBench first

Freeze and execute the new PrecisionMemBench retrieval lane first.

Required outputs remain native to the harness:

- active passes / 43;
- total passes / 77;
- mean precision;
- mean recall;
- matched retrieval timing where technically comparable;
- failures and unmapped-return counts.

No overall memory score is created.

If Hindsight cannot run faithfully under the frozen AMB environment, classify
the row with the exact blocker. Do not modify its product configuration.

## H6 — LongMemEval_S second

Only after the AMB composition is proven executable, freeze the LongMemEval_S
lane using the exact same product configuration.

Keep session and turn planes separate. Report:

- recall_all@5 / @10 and @50 where defined;
- nDCG metrics;
- knowledge-update retrieval metrics;
- latest-gold-ranked-first diagnostic;
- failures, out-of-corpus and unmapped counts;
- timing where comparable.

No end-to-end answer-generation score is implied by this retrieval row.

## H7 — Acceptance and scorecard integration

Acceptance requires:

- lane files were frozen before score;
- exact Hindsight source and embedding identities are bound;
- every executed row has raw evidence and execution identity;
- zero silent result-identity guessing;
- no benchmark-specific Hindsight configuration;
- normalizers preserve the new row as `same_harness`;
- dashboards/scorecards identify this exact bounded Hindsight composition rather
  than the Hindsight product generically.

A bad Hindsight score is still valid evidence. A good score does not authorize
runtime architecture changes by itself.

## Non-goals

- changing Agent Memory runtime behavior;
- #732 remediation or R6;
- #673 route fusion;
- benchmarking Hindsight's LLM fact extraction;
- benchmarking Hindsight observations/reflect;
- selecting a universal "winner";
- replacing future richer Hindsight lanes.

## Execution order

1. Gate this plan.
2. Implement H1/H2 with offline tests.
3. Run H3 product smoke.
4. Gate/freeze the new AMB lane before score.
5. Execute/import/accept AMB.
6. Gate/freeze the new LongMemEval_S lane before score.
7. Execute/import/accept LongMemEval_S.
8. Reconcile #640/#601/#719 and the competitive scorecards.

No score may be inspected before the lane that owns it is frozen.
