# Canonical Agent Memory benchmark dashboard

Status: **current accepted evidence through #594**, plus current pre-1.0 comparator/runtime-qualification state as of 2026-09-28.

Current merged `main`: `a24e993958d741379993341e8b3f63ed37482df3`.

No universal aggregate score exists. `blocked`, `not_run`, `unsupported`, and `evidence_gap` are states, never numeric zero.

## How to read this dashboard

Four evidence classes are intentionally separate:

1. **Agent Memory longitudinal** — current accepted Agent Memory evidence versus an earlier accepted Agent Memory signal under a sufficiently comparable profile.
2. **Same-harness systems** — multiple memory systems executed against the same frozen input, evaluator, retrieval/context budget, and model/judge configuration.
3. **Published reference** — vendor/research results useful for market context but not numerically comparable unless methodology is proven equivalent.
4. **Runtime qualification** — implementation-profile evidence such as Python/Rust parity. This is not a memory-quality score.

A new metric having no prior Agent Memory baseline is normal. A missing controlled competitor is a **competitive evidence gap**.

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

The strict slot/value result uses zero aliases frozen before scoring. It is exact-label conformance, not semantic-synonym precision.

## Competitive view — same-harness systems

**Status: infrastructure merged, accepted competitive result pending.**

#601 now has executable independent-harness infrastructure:

- AMB bridge merged in PR #604;
- frozen external harness revision `03c1d0f1d27da63034f0931121c858faba512383`;
- credential-free AMB retrieval lane merged in PR #606;
- manual competitive workflow at `.github/workflows/amb-competitive.yml`.

The first credential-free profile is:

```text
dataset: precisionmembench
split: single-turn
mode: retrieval
providers: agent-memory, bm25
```

Frozen AMB `RetrievalMode` makes no LLM calls and scores returned belief/document IDs directly.

**No same-harness competitive result is accepted into this dashboard yet.** The manual run must be deliberately executed and its raw artifact reviewed first. BM25 is a baseline comparator, not a market-position claim.

The LLM-judged AMB profile is frozen to `gemini:gemini-2.5-flash-lite` for answer and judge, but remains **blocked pending authorized evaluation credentials**.

First-wave market targets remain:

1. Mem0 OSS;
2. Hindsight;
3. Zep / Graphiti;
4. Letta;
5. Cognee;
6. LangMem.

Unsupported lifecycle or benchmark surfaces are `unsupported`, never zero.

## Market context — published reference only

These rows answer “what are leading systems currently publishing?” They do **not** answer “is Agent Memory better or worse?”

| system | published signal | methodology distinction | comparability here | source |
| --- | --- | --- | --- | --- |
| **Hindsight v0.4.19** | LongMemEval **94.6%**; LoCoMo **92.0%** | single-query end-to-end accuracy in Hindsight AMB; open pluggable harness | `published_reference` until reproduced | [Hindsight AMB](https://hindsight.vectorize.io/blog/2026/03/23/agent-memory-benchmark) |
| **Mem0 managed platform** | LongMemEval **94.4%**; LoCoMo **92.5%**; BEAM-1M avg **0.641** | managed end-to-end QA; published retrieval budgets differ | `published_reference` | [Mem0 evaluation](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-evaluation.mdx) |
| **Zep** | LongMemEval **90.2%**; LoCoMo **94.7%** | end-to-end accuracy; published retrieval p50/p95 **104/162 ms**, median context **4,408 tokens** | `published_reference` | [Zep research](https://www.getzep.com/research/) |
| **Supermemory** | LongMemEval-S **97% Recall@20** with aggregation | retrieval Recall@20, not Agent Memory recall_all@5/@10 | `published_reference` | [Supermemory research](https://supermemory.ai/research/) |
| **Cognee** | BEAM 100K **0.79**, BEAM 10M **0.67** | different benchmark family | `published_reference` | [Cognee results](https://www.cognee.ai/research-and-evaluation-results) |

Independent multi-system suites may be recorded as `external_cross_system_reference`, but they do not replace local same-harness reproduction.

## Runtime qualification — Python vs Rust

**Status: three deterministic Rust-shadow slices qualified; runtime promotion not established.**

ADR-028 remains controlling: the normative core is language-neutral.

Python remains the qualified runtime/reference implementation. Rust remains evaluation-only and is not linked into the product runtime.

### Accepted Rust-shadow evidence

**PR #605 — ranking and digest primitives**

- workflow `36457677348`: exact relevance-token vectors and every admitted-set BM25 IEEE-754 score bit reproduced on Ubuntu CI, including an exact tie;
- workflow `36458112635`: BM25 parity retained and UTF-8 SHA-256 vectors reproduced exactly.

**PR #610 — non-floating canonical JSON bytes**

- workflow `36485253610`: Python and Rust reproduced exact frozen UTF-8 canonical bytes and SHA-256 digests for null, booleans, exact integers, strings, arrays, and string-keyed objects;
- full exact-head repository validation was green before merge;
- the Rust value model for this slice cannot represent floats, making the qualification boundary structural rather than advisory.

**PR #611 — #591 identity-first candidate prefilter**

- workflow `36486001629`: exact candidate membership, ordering, and score-bit parity across wrong-group exclusion, identity-ineligible exclusion, exact ties, duplicate query terms, empty stripped queries, and current punctuation semantics;
- the full exact-head repository matrix was green before merge;
- this is candidate-generation/minimization parity only. Materialized fact eligibility and canonical recall admission remain downstream and authoritative.

### Persistence determinism gap — #609

#602 exposed a real portability defect in the current persistence contract.

`TypedRelation.retrieval_weight` is a float and typed-relation rows participate in SQLite integrity commitments. Current canonical serialization delegates floating-number spelling to CPython's JSON encoder. Therefore full cross-language persisted-state identity is not yet language-neutral.

Issue #609 owns the numeric canonicalization and migration contract. A draft ADR-040 proposal is under review separately; no current runtime bytes or digest schemes have changed.

Until #609 is dispositioned, the following remain **not established**:

- float-bearing persisted canonical serialization parity;
- state/integrity parity over affected rows;
- restart/checkpoint compatibility for a Rust-owned state runtime;
- cross-platform floating-math identity beyond the currently qualified BM25 CI profile;
- matched Python/Rust performance advantage;
- FFI or native-Rust runtime promotion.

Current decision candidates remain:

```text
A. Python preferred runtime
B. Python facade + Rust kernel
C. native Rust runtime + Python bindings
D. parallel conformant Python and Rust profiles
```

Current evidence strengthens **B as a hypothesis**, not as a decision. Deterministic ranking, hashing, non-floating canonical bytes, and a real candidate-generation hot path have all ported exactly so far. The next meaningful question is whether Rust produces material matched performance/assurance value without creating unacceptable FFI and maintenance cost.

## Architecture progression

| milestone | architectural move | evidence outcome |
| --- | --- | --- |
| frozen pre-remediation `f73b872` | baseline external retrieval/currentness | LME-S session recall@5 0.675; latest-first 0.343 / 0.486 |
| #538 | explicit ranking policy / admitted-set BM25 | retrieval improved; currentness trade-offs exposed |
| #530 | runtime-owned serialization | concurrency failure -> operation/materialization success 1.0 |
| #522 / #548 | incremental attestation + domain prefilter | major state/candidate costs removed without authority change |
| #576 | deterministic BM25 accumulation | score bits/order stable across hash seeds |
| #550 | typed proposition/cardinality/aspect/self-validity evidence | four #580 targets improved; policy 3.1.0 |
| #591 | identity-first materialization | p50 17.9 -> 7.7 ms; p95 31.4 -> 11.9 ms; rankings identical |
| #594 A | source-anchored external profile | interpreted-demotion efficacy remains evidence gap |
| #594 B | independently frozen natural-data gold | severe under-recognition exposed; #596-#598 split out |
| #600 / #601 | pre-1.0 competitive maturity program | independent AMB infrastructure merged; result pending |
| #602 / #605 | Rust deterministic shadow | BM25/tokenization/SHA exact parity passes on qualified CI |
| #602 / #610 | canonical non-float byte shadow | exact Python/Rust byte + digest parity; float persistence gap isolated |
| #602 / #611 | Rust #591 prefilter shadow | exact candidate membership/order/score-bit parity on a real hot path |
| #609 | language-neutral persistence determinism | float-bearing integrity serialization identified as an explicit architecture/migration gate |

## #594 Phase B — unbiased Part R

| gold status | predicted known | predicted ambiguous | predicted unknown |
| --- | ---: | ---: | ---: |
| known (54) | 8 | **46** | 0 |
| ambiguous (13) | 0 | 13 | 0 |
| unknown (33) | 2 | 3 | 28 |

Largest measured weakness: **over-ambiguity / under-recognition**. Known precision is 0.80, but known recall is only 0.148. Unknown precision is 1.0.

Other Part R counters: wrong slot 8, unknown->known 2, aspect mismatch 4, aspect over-classification 1, over-eager single-valued 0.

## Governance posture

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
cross-language parity != runtime promotion
non-float canonical parity != persisted-state parity
```

Active state:

- #591 complete;
- #594 **QUALIFIED**;
- #600 pre-1.0 maturity program active;
- #601 competitive infrastructure merged, first accepted same-harness result pending;
- #602 Rust shadow tokenization/BM25/SHA/non-float-canonical/prefilter qualification **PASS**, runtime not promoted;
- #609 active persistence-determinism gate; ADR-040 proposal is draft/unaccepted;
- ADR-028 **Accepted**;
- ADR-039 **Proposed**;
- #583 / PR #587 remains **DRAFT / HOLD**;
- #585 remains next query-side RC step;
- #598 remains prerequisite before redesigned #583;
- #596/#597 remain high-priority nonautomatic RC blockers;
- #586 remains post-RC unless evidence pulls it forward.

## Next paths

```text
RC temporal path
#585
  -> #598
  -> redesigned #583
  -> final #580 replay
  -> #584
  -> RC1 declaration decision

pre-1.0 maturity path
#600
  +-> #601 first independent retrieval result
  |      -> controlled market systems
  |      -> accepted dashboard competitor rows
  |
  +-> #602 matched candidate-prefilter performance
         -> #609 numeric canonicalization + migration
         -> state/integrity parity
         -> lifecycle shadow
         -> matched operational evidence
         -> A/B/C/D runtime decision
```

A later 1.0 decision should require both a defensible RC disposition and a defensible maturity position. Beating one product on one benchmark is insufficient. So is merely beating our former selves.

Machine-readable form: `current.json`.
