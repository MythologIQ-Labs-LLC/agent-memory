# Canonical Agent Memory benchmark dashboard

Status: **current accepted evidence through #594**, plus a clearly separated published-market reference layer as of 2026-09-28. No universal aggregate score exists. `blocked`, `not_run`, `unsupported`, and `evidence_gap` are states, never numeric zero.

Current merged main boundary: `80566b5e3affd7b038f31bc24039054ef87d07a1` (PR #595 merged). Competitive same-harness work is tracked by #601 under maturity program #600.

## How to read this dashboard

This dashboard has three different comparison classes. They must not be mixed.

1. **Agent Memory longitudinal** — current accepted Agent Memory evidence versus an earlier accepted Agent Memory signal under a sufficiently comparable profile.
2. **Same-harness systems** — competing memory systems executed locally against the exact same frozen input, evaluator, retrieval/context budget, and model/judge configuration. This is the preferred competitive evidence class.
3. **Published reference** — current vendor/research results useful for market context but not numerically comparable to Agent Memory unless their methodology matches exactly.

A missing historical baseline is normal when a metric is new. A missing same-harness competitor is a **competitive evidence gap** and is being remediated by #601.

## Executive view — Agent Memory longitudinal

| track | current accepted signal | previous accepted signal | delta / disposition | evidence class |
| --- | --- | --- | --- | --- |
| AgentMemBench retrieval | exact-source@5 **0.899** | 0.889 | +0.010 | external efficacy |
| LongMemEval_S session retrieval | recall_all@5 **0.823389** | 0.675 | +0.148389 | external efficacy |
| LongMemEval_S turn retrieval | recall_all@10 **0.723** | 0.525 | +0.198 | external efficacy |
| LongMemEval_M | session@5 **0.708831**, turn@5 **0.532220** | not available | first accepted M baseline | external efficacy |
| AgentMemBench currentness | new-fact **0.20**, staleness **0.80** | 0.00 / 1.00 | +0.20 / -0.20 | external efficacy |
| LongMemEval_S latest-gold-first | session **0.457**, turn **0.557** | 0.343 / 0.486 | +0.114 / +0.071 | external efficacy |
| #580 self-description currentness | **0.273** | 0.091 | +0.182 | repository-owned conformance |
| #591 search performance | p50 **7.7 ms**, p95 **11.9 ms**, wall **38.6 s** | 17.9 / 31.4 / 54.6 | -10.2 / -19.5 / -16.0 | repository-owned performance |
| #594 adapted self-validity efficacy | **EVIDENCE GAP** | not run | C=P1=P2; 0 changed rows | adapted external evidence |
| #594 proposition known precision | **0.800** | not run | first accepted natural-data baseline | repository-owned conformance |
| #594 proposition known recall | **0.148** | not run | first baseline; remediation #596 | repository-owned conformance |
| #594 unknown precision / recall | **1.000 / 0.848** | not run | first baseline | repository-owned conformance |
| #594 strict slot/value conformance | **0.000** | not run | exact-label diagnostic only; #597 | repository-owned conformance |

The strict slot/value number deliberately uses zero aliases frozen before scoring. It mixes true extraction failures with semantically close property labels and must not be sold as semantic synonym precision. That distinction is governed by #597 rather than repaired after seeing the score.

## Competitive view — same-harness systems

**Status: competitive evidence gap / implementation active in #601.**

No non-Agent-Memory runtime has yet been accepted into this dashboard as a same-harness LongMemEval or AgentMemBench result. Existing repository comparators, including the pinned Mem0 P6 adversarial comparator, measure useful runtime behavior but are not the same retrieval/QA profile used for the headline rows above.

The first-wave same-harness targets are:

1. Mem0 OSS;
2. Hindsight;
3. Zep / Graphiti;
4. Letta;
5. Cognee;
6. LangMem.

Required competitive lanes are:

- exact frozen LongMemEval_S retrieval parity;
- a separate end-to-end LongMemEval QA lane with one frozen answer model/judge/budget;
- AgentMemBench / MemDialogue operational parity where semantics are meaningfully expressible;
- matched latency/token/storage evidence where technically comparable.

Unsupported lifecycle or benchmark surfaces are reported as `unsupported`, never zero.

## Market context — published reference only

These rows answer **“what are leading systems currently publishing?”** They do **not** answer **“is Agent Memory better or worse?”** Different rows use different metrics, models, retrieval budgets, managed/OSS implementations, and evaluation protocols. They are retained here so readers have current market context while #601 builds controlled reproduction.

| system | published signal | methodology distinction | comparability here | source |
| --- | --- | --- | --- | --- |
| **Hindsight v0.4.19** | LongMemEval **94.6%**; LoCoMo **92.0%** | single-query end-to-end accuracy in Hindsight Agent Memory Benchmark; open pluggable harness | `published_reference` until reproduced | [Hindsight AMB](https://hindsight.vectorize.io/blog/2026/03/23/agent-memory-benchmark) |
| **Mem0 managed platform** | LongMemEval **94.4%**; LoCoMo **92.5%**; BEAM-1M avg **0.641** | end-to-end QA / managed production pipeline; LongMemEval top-200/top-50 published separately | `published_reference`; not Agent Memory recall@k | [Mem0 evaluation](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-evaluation.mdx) |
| **Zep** | LongMemEval **90.2%** (451/500); LoCoMo **94.7%** | end-to-end accuracy; published LongMemEval retrieval p50/p95 **104/162 ms**, median context **4,408 tokens** | `published_reference`; model/judge differs | [Zep research](https://www.getzep.com/research/) |
| **Supermemory** | LongMemEval-S **97% Recall@20** with aggregation | retrieval Recall@20, not end-to-end QA and not Agent Memory recall_all@5/@10 | `published_reference`; metric differs materially | [Supermemory research](https://supermemory.ai/research/) |
| **Cognee** | BEAM 100K **0.79**, BEAM 10M **0.67** | BEAM long-horizon evaluation; different benchmark family | `published_reference`; ecosystem context only | [Cognee results](https://www.cognee.ai/research-and-evaluation-results) |

Independent multi-system benchmark suites may also be recorded as `external_cross_system_reference`, but they do not replace our same-harness reproduction because model, adapter, and evaluator choices can move results substantially.

## Architecture progression

| milestone | architectural move | evidence outcome |
| --- | --- | --- |
| frozen pre-remediation `f73b872` | baseline external retrieval/currentness | LME-S session recall@5 0.675; latest-first 0.343 / 0.486 |
| #538 ranking policy | explicit post-admission tie-break | currentness improved among ties; retrieval regression recorded |
| #538 admitted-set BM25 | relevance over admitted set only | LME-S session recall@5 0.823; turn recall@10 0.723; currentness trade-off exposed |
| #530 | runtime-owned handle serialization | concurrency failures -> operation/materialization success 1.0 |
| #522 / #548 | incremental attestation + identity/domain prefilter | removed major O(state) integrity/candidate costs without authority change |
| #576 | deterministic BM25 accumulation | score bits and order stable across hash seeds |
| #550 | typed proposition/cardinality/aspect/self-validity evidence | no external rank drift; four #580 target units honest_unknown -> pass; policy 3.1.0 |
| #591 | identity-first candidate materialization | p50 17.9 -> 7.7 ms; p95 31.4 -> 11.9 ms; semantic rankings identical |
| #594 Phase A | source-anchored natural external profile | no effect; demotion efficacy remains an explicit evidence gap |
| #594 Phase B | independently frozen 268-turn gold | interpreter is safe-leaning but severely under-recognizes valid propositions; defects split to #596-#598 |
| #600 / #601 | pre-1.0 competitive maturity program | same-harness market comparison now an explicit evidence requirement |
| #602 | Python-vs-Rust runtime qualification | implementation-language decision moved from preference to cross-language evidence |

## #594 Phase B, unbiased Part R

| gold status | predicted known | predicted ambiguous | predicted unknown |
| --- | ---: | ---: | ---: |
| known (54) | 8 | **46** | 0 |
| ambiguous (13) | 0 | 13 | 0 |
| unknown (33) | 2 | 3 | 28 |

The largest measured weakness is **over-ambiguity / under-recognition**. Known precision is 0.80, but known recall is only 0.148. Unknown precision is 1.0. This is materially weak efficacy, but its dominant failure mode is conservative and does not create authority.

Other Part R counters: wrong slot 8, unknown->known 2, aspect mismatch 4, aspect over-classification 1, over-eager single-valued 0.

## Governance / safety posture

Still true:

```text
interpretation != authority
semantic interpretation != retention/lifecycle policy
classifier output != truth
classifier confidence != permission
proposal != application
ranking != admission
ranking != truth
relevance != currentness
recency != authority
newer != superseding
benchmark score != memory authority
published vendor score != same-harness comparator
implementation language != doctrine
```

Active state:

- #591 complete.
- #594 **QUALIFIED**.
- canonical dashboard complete and now explicitly exposes the competitive evidence gap.
- #600 is the pre-1.0 maturity umbrella.
- #601 owns same-harness competitive comparison.
- #602 owns Python-vs-Rust implementation-profile qualification under ADR-028.
- ADR-039 remains **Proposed**.
- #583 / PR #587 remains **DRAFT / HOLD**; old lexical-cue-removal implementation must not be revived.
- #585 is the next query-side RC step.
- #598 is a prerequisite before redesigned #583 because #594 exposed memory-side aspect calibration defects.
- #596 and #597 are high-priority interpreter-quality work, but are not automatic RC1 blockers while their dominant failure remains fail-safe ambiguity/abstention.
- #586 remains post-RC unless later evidence pulls it forward.

## Next RC and maturity paths

```text
RC temporal path
#585 query-intent span calibration
  -> #598 write-time aspect calibration
  -> redesigned #583
  -> final #580 replay
  -> #584 policy ruling
  -> RC1 declaration decision

pre-1.0 maturity path (parallel)
#600
  +-> #601 same-harness competitive league
  +-> #602 Python-vs-Rust runtime qualification
```

A later 1.0 decision should require both an explicit RC disposition and a defensible maturity position. Beating named products on one benchmark is not sufficient; neither is merely being better than an older Agent Memory commit.

Machine-readable form: `current.json`.
