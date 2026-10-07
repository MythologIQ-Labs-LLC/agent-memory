# PRD-002 Wireframe Specification: Benchmark Evidence Console

Status: **Draft / Future post-RC feature**

Parent: PRD-002, #696  
UX implementation issue: #699  
Architecture boundary: proposed ADR-041

## Purpose

This document makes the Benchmark Evidence Console structurally intentional before frontend implementation.

A production frame is not considered designed merely because its route or feature appears in the PRD.

Every frame in the inventory below must have:

1. a defensible structural wireframe;
2. a clearly stated user intent;
3. a defined evidence/data contract;
4. a representative seed from evidence Agent Memory actually has, or an explicit real missing-state where the evidence does not exist yet;
5. a responsive behavior;
6. primary interactions and transitions;
7. a reason the frame exists.

No production frame may be invented during implementation without either:

- adding it to this specification; or
- explicitly classifying it as a minor state of an existing frame.

This prevents the frontend from becoming a collection of locally reasonable screens with no coherent product structure.

---

# Evidence seed used for structural validation

The wireframes below are validated against the canonical benchmark dashboard currently committed at:

`reports/benchmarks/dashboard/current.json`

Dashboard evidence identity:

- dashboard as-of: **2026-10-06**
- dashboard Agent Memory head: **ca0f9a748b3b7296c5a99c7e81cca35a570609fd**
- repository main advanced after this dashboard; that difference itself is used to validate the stale-catalog frame.

Representative measured values used in the wireframes:

| Evidence | Current | Comparison / prior |
| --- | ---: | ---: |
| AgentMemBench exact-source recall@5 | 0.899 | previous 0.889 |
| LongMemEval_S session recall_all@5 | 0.823389 | previous 0.675 |
| LongMemEval_S turn recall_all@10 | 0.723 | previous 0.525 |
| LongMemEval_S session latest-gold-first | 0.457 | previous 0.343 |
| LongMemEval_S turn latest-gold-first | 0.557 | previous 0.486 |
| AgentMemBench new-fact-first | 0.20 | previous 0.00 |
| AgentMemBench staleness | 0.80 | previous 1.00 |
| search latency p50 | 7.7 ms | previous 17.9 ms |
| search latency p95 | 11.9 ms | previous 31.4 ms |
| Part R known precision | 0.800 | first baseline |
| Part R known recall | 0.148148 | first baseline |
| Part R unknown precision | 1.000 | first baseline |
| Part R unknown recall | 0.848485 | first baseline |
| cross-user leakage | 0.000 | previous 0.000 |
| audited deletion | 1.000 | previous 1.000 |

Accepted same-harness LongMemEval_S session evidence:

| Metric | Agent Memory | Mem0 explicit | lexical overlap |
| --- | ---: | ---: | ---: |
| recall_all@5 | 0.823389 | 0.809069 | 0.730310 |
| recall_all@10 | 0.892601 | 0.883055 | 0.825776 |
| ndcg_any@10 | 0.878274 | 0.841054 | 0.792944 |
| knowledge-update recall_all@5 | 0.972222 | 0.902778 | 0.916667 |
| latest-gold-ranked-first | 0.457143 | 0.442857 | 0.457143 |

Accepted same-harness PrecisionMemBench evidence:

| Metric | Agent Memory | Mem0 explicit | BM25 |
| --- | ---: | ---: | ---: |
| active passes | 4/43 | 0/43 | 0/43 |
| mean precision | 0.1806 | 0.1049 | 0.0536 |
| mean recall | 0.9535 | 1.0000 | 0.9651 |

Published-reference values available in the current dashboard include:

- Hindsight v0.4.19 LongMemEval end-to-end accuracy 0.946;
- Mem0 managed LongMemEval accuracy 0.944;
- Zep LongMemEval accuracy 0.902;
- Supermemory LongMemEval_S Recall@20 with aggregation 0.97;
- Cognee BEAM 100K 0.79 and BEAM 10M 0.67.

These are deliberately used only in published-reference frames and never as same-harness peers.

---

# Canonical frame inventory

A frame is either a full route, a materially different route state, or a major overlay/drawer whose structure affects the user's interpretation.

| ID | Frame | Type |
| --- | --- | --- |
| F00 | Application shell / current snapshot | shell |
| F01 | Overview / North Star | route |
| F02 | Capability posture inspector | drawer |
| F03 | Compare / valid same-harness set | route |
| F04 | Compare / non-comparable selection | route state |
| F05 | Benchmarks index | route |
| F06 | Benchmark profile detail | route |
| F07 | Changes timeline | route |
| F08 | Before/after revision comparison | route state |
| F09 | Failure Explorer aggregate | route |
| F10 | Failure case detail | route |
| F11 | Coverage matrix | route |
| F12 | Coverage-gap inspector | drawer |
| F13 | Evidence index / run browser | route |
| F14 | Run detail | route |
| F15 | Evidence / comparability inspector | drawer |
| F16 | Snapshot selector / history | overlay |
| F17 | Historical shared snapshot | route state |
| F18 | Share / export | overlay |
| F19 | Methodology / metric glossary | route |
| F20 | No same-harness comparator | empty state |
| F21 | Blocked / unsupported evidence | empty state |
| F22 | Failed attempted run with previous accepted evidence | route state |
| F23 | Catalog stale relative to repository | global state |
| F24 | Invalid or unavailable snapshot | error state |
| R01 | Mobile Overview | responsive canonical |
| R02 | Mobile pair comparison | responsive canonical |
| R03 | Mobile evidence/run detail | responsive canonical |
| R04 | Tablet comparison matrix | responsive canonical |

Any future implementation frame not represented here must be reconciled with #699 before implementation.

---

# F00 — Application shell / current snapshot

## User intent

Know immediately which evidence state is being viewed before interpreting any number.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Agent Memory Benchmark Evidence                                             │
│ CURRENT EVIDENCE · 2026-10-06 · AM ca0f9a7 · Runtime Baseline v2           │
│ Repo has newer changes                                                      │
│                                                        [Snapshots] [Share]   │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ Overview      │                                                              │
│ Compare       │                    PAGE CONTENT                              │
│ Benchmarks    │                                                              │
│ Changes       │                                                              │
│ Failures      │                                                              │
│ Coverage      │                                                              │
│ Evidence      │                                                              │
│ Methodology   │                                                              │
└───────────────┴──────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

The current dashboard is bound to `ca0f9a7`, while repository main is newer. The shell therefore needs separate concepts for:

- evidence snapshot revision;
- repository current revision;
- runtime baseline identity;
- evidence date.

A single "latest" label is insufficient.

## Required catalog fields

- snapshot.id
- snapshot.as_of
- snapshot.agent_memory_revision
- snapshot.runtime_baseline
- snapshot.is_current
- snapshot.repository_head_if_known
- snapshot.staleness_state

## Responsive rule

Navigation collapses, but snapshot identity remains visible without opening a menu.

---

# F01 — Overview / North Star

## User intent

Understand current measured posture before learning the benchmark taxonomy.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Overview                                                                    │
│ Evidence state: 2026-10-06 · AM ca0f9a7                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ NORTH STAR                                                                  │
│                                                                              │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐              │
│ │ Retrieval        │ │ Currentness      │ │ Performance      │              │
│ │ COMPETITIVE      │ │ MATERIAL WEAKNESS│ │ IMPROVED         │              │
│ │ LME S R@5 .823   │ │ new-fact .200   │ │ p95 11.9 ms      │              │
│ │ Same harness     │ │ external efficacy│ │ was 31.4 ms      │              │
│ │ [Inspect]        │ │ [Inspect]        │ │ [Inspect]        │              │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘              │
│                                                                              │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐              │
│ │ Governance       │ │ Reasoning / QA   │ │ Scale / BEAM     │              │
│ │ MEASURED         │ │ NOT MEASURED     │ │ EVIDENCE GAP     │              │
│ │ leak 0.000       │ │ judged lane —    │ │ Agent Memory —   │              │
│ │ deletion 1.000   │ │ [Coverage]       │ │ [Coverage]       │              │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘              │
├──────────────────────────────────────────────────────────────────────────────┤
│ MATERIAL FINDINGS                                                           │
│                                                                              │
│ Currentness remains weak: new-fact-first 0.20        [Why?] [Investigate]   │
│ LME session R@5 ahead of Mem0: .823 vs .809          [Compare]              │
│ Precision remains low: .181 vs Mem0 .105             [Benchmark]            │
│ BEAM scale evidence not yet accepted                  [View gap]             │
├──────────────────────────────────────────────────────────────────────────────┤
│ RECENT EVIDENCE CHANGES                                                     │
│ + LME S session recall_all@5: .675 -> .823                                  │
│ + search p95: 31.4ms -> 11.9ms                                              │
│ + AgentMemBench currentness: .00 -> .20                                     │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Why this structure

The first screen answers user questions, not benchmark names.

The posture cards intentionally mix:

- a measured value;
- an evidence state;
- an evidence class.

They do not produce a universal score.

## Real-data validation

All displayed numeric seeds above exist in `current.json`.

Reasoning/QA and BEAM use real missing states rather than fabricated values.

## Primary transitions

- card -> F02 Capability posture inspector
- Compare finding -> F03
- weak finding -> F09 or F06 depending evidence availability
- coverage gap -> F11

---

# F02 — Capability posture inspector

## User intent

Understand why Overview labels a capability strong, weak, mixed, or unknown.

## Wireframe

~~~text
                                                    ┌─────────────────────────┐
                                                    │ Currentness             │
                                                    │ MATERIAL WEAKNESS       │
                                                    ├─────────────────────────┤
                                                    │ Supporting evidence      │
                                                    │                         │
                                                    │ AgentMemBench           │
                                                    │ new-fact-first 0.200    │
                                                    │ previous 0.000          │
                                                    │ External efficacy       │
                                                    │                         │
                                                    │ staleness 0.800         │
                                                    │ previous 1.000          │
                                                    │                         │
                                                    │ LongMemEval_S           │
                                                    │ latest-first session    │
                                                    │ 0.457 (was 0.343)       │
                                                    │                         │
                                                    │ latest-first turn       │
                                                    │ 0.557 (was 0.486)       │
                                                    ├─────────────────────────┤
                                                    │ Evidence limitations     │
                                                    │ Formal MESA pending #694 │
                                                    │ Demotion: EVIDENCE GAP  │
                                                    ├─────────────────────────┤
                                                    │ [Benchmark] [Failures]  │
                                                    │ [Inspect provenance]    │
                                                    └─────────────────────────┘
~~~

## Real-data validation

Uses only current dashboard currentness rows.

The formal MESA result is not fabricated. It is represented as pending future evidence.

## Required catalog fields

- capability_posture
- supporting_run_refs[]
- supporting_metric_refs[]
- evidence_limitations[]
- related_coverage_gaps[]
- related_issue_refs[]

---

# F03 — Compare / valid same-harness set

## User intent

Compare systems without personally reconstructing protocol eligibility.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Compare systems                                                             │
│ Systems [Agent Memory ×] [Mem0 explicit ×]   Evidence [Same harness only]  │
│ Benchmark [LongMemEval_S] Profile [Retrieval parity v2] Plane [Session]     │
├────────────────────────────────────────────────────────────┬─────────────────┤
│ EXACT SAME-HARNESS                                         │ Why comparable? │
│                                                           │ ✓ input digest  │
│ Metric                    Agent Memory   Mem0       Delta   │ ✓ 419 questions │
│ recall_all@5              0.823389       0.809069  +.01432 │ ✓ session plane │
│ recall_all@10             0.892601       0.883055  +.00955 │ ✓ metric defs   │
│ ndcg_any@10               0.878274       0.841054  +.03722 │ ✓ budget/profile│
│ knowledge-update R@5      0.972222       0.902778  +.06944 │                 │
│ latest gold first         0.457143       0.442857  +.01429 │ [Full evidence] │
│                                                           │                 │
│ [Open benchmark] [Inspect AM run] [Inspect Mem0 run]      │                 │
├────────────────────────────────────────────────────────────┴─────────────────┤
│ PUBLISHED MARKET CONTEXT · NOT PART OF THIS HEAD-TO-HEAD                    │
│ Hindsight LME QA 0.946   Mem0 managed 0.944   Zep 0.902                    │
│ [Why separate?]                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

All same-harness values are from the accepted LongMemEval_S v2 session lane.

Published values are current dashboard reference rows and are structurally separated.

## Responsive rule

On narrow screens, only two systems may be compared at once.

---

# F04 — Compare / non-comparable selection

## User intent

Understand why two attractive-looking numbers cannot support a direct conclusion.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Compare systems                                                             │
│ Agent Memory: LongMemEval_S session recall_all@5 = 0.823389                │
│ Hindsight: LongMemEval end-to-end QA accuracy = 0.946                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ ⚠ RELATED EVIDENCE, NOT NUMERICALLY COMPARABLE                              │
│                                                                              │
│ Agent Memory                    Hindsight                                    │
│ Retrieval metric               End-to-end QA metric                         │
│ recall_all@5                   accuracy                                     │
│ same-harness LME replica       published Hindsight AMB                      │
│ reader/judge: not applicable   reader/judge part of pipeline                │
│                                                                              │
│ No delta or winner is calculated.                                           │
│                                                                              │
│ [View methodology side by side] [Find same-harness Hindsight evidence]      │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

Uses actual Agent Memory LME retrieval evidence and current published Hindsight QA reference.

The lack of a direct comparison is the real state.

---

# F05 — Benchmarks index

## User intent

Find the benchmark that answers a particular question and understand coverage before opening it.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Benchmarks                                                                  │
│ [Search]  Capability [All]  Status [All]                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ LongMemEval_S                                                               │
│ Long-horizon retrieval · session + turn                                     │
│ Agent Memory: ACCEPTED · same-harness comparators: Mem0 + lexical           │
│ Key evidence: session R@5 .823 · turn R@10 .723          [Open]             │
├──────────────────────────────────────────────────────────────────────────────┤
│ PrecisionMemBench / AMB                                                     │
│ Precision / over-retrieval                                                   │
│ Agent Memory: ACCEPTED · same-harness: Mem0 + BM25                          │
│ Mean precision .181 · recall .954                         [Open]             │
├──────────────────────────────────────────────────────────────────────────────┤
│ AgentMemBench currentness                                                   │
│ Temporal consistency                                                        │
│ Adapted signal: new-fact .200 · staleness .800                              │
│ Formal MESA baseline: PENDING #694                        [Open]             │
├──────────────────────────────────────────────────────────────────────────────┤
│ BEAM                                                                        │
│ Scale / long-horizon                                                         │
│ Agent Memory: NOT RUN · published refs available          [Coverage gap]     │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

The first three rows use current repository evidence.

BEAM is intentionally represented as not run for Agent Memory while published comparator references exist.

---

# F06 — Benchmark profile detail

## User intent

Understand one benchmark in its native semantics and inspect its accepted runs.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ LongMemEval_S                                                               │
│ Retrieval parity v2 · SESSION · ACCEPTED                                    │
│ Lane: longmemeval-s-retrieval-parity-v2                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ WHAT THIS MEASURES                                                          │
│ Long-horizon retrieval over 419 scored questions after frozen exclusions.   │
│ Session and turn are distinct planes and are never averaged.                │
├──────────────────────────────────────────────────────────────────────────────┤
│ RESULTS                                                                     │
│ Metric                    Agent Memory   Mem0        lexical                 │
│ recall_all@5              .823389        .809069     .730310                │
│ recall_all@10             .892601        .883055     .825776                │
│ ndcg_any@10               .878274        .841054     .792944                │
│ knowledge-update R@5      .972222        .902778     .916667                │
│ latest gold first         .457143        .442857     .457143                │
├──────────────────────────────────────────────────────────────────────────────┤
│ METHODOLOGY                                                                 │
│ input SHA  d6f21e…a442      scored questions 419                            │
│ runtime failures 0          Agent Memory revision ca0f9a7                   │
│ [Full methodology] [Compare] [Runs] [Evidence]                              │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

Entire frame can be rendered from existing accepted v2 lane data.

---

# F07 — Changes timeline

## User intent

See the sequence of architecture/runtime transitions and associated evidence without assuming every transition is directly comparable.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Changes                                                                     │
│ [Current accepted evidence]                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│  f73b872  PRE-REMEDIATION                                                   │
│      LME S session R@5 .675                                                 │
│      latest-first session .343                                              │
│        │                                                                     │
│        ├── #538 ranking-policy transition                                   │
│        ├── #576 deterministic BM25                                          │
│        ├── #550 proposition semantics                                       │
│        └── #591 identity-first materialization                              │
│        ▼                                                                     │
│  ca0f9a7  RUNTIME BASELINE v2                                               │
│      LME S session R@5 .823                                                 │
│      turn R@10 .723                                                         │
│      search p95 11.9ms                                                      │
│                                                                              │
│ [Compare selected revisions]                                                │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

Uses architecture progression and longitudinal values already recorded by the current dashboard.

The timeline is association, not automatic causality.

---

# F08 — Before/after revision comparison

## User intent

Determine which measured signals changed between two valid evidence states.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Compare revisions                                                           │
│ Before [pre-remediation f73b872]     After [accepted post-#591 evidence]    │
├──────────────────────────────────────────────────────────────────────────────┤
│ COMPARABLE LONGITUDINAL EVIDENCE                                            │
│                                                                              │
│ LongMemEval_S session recall_all@5    .675  -> .823389   +.148389           │
│ LongMemEval_S turn recall_all@10      .525  -> .723      +.198              │
│ latest-first session                  .343  -> .457      +.114              │
│ AgentMemBench new-fact-first          .000  -> .200      +.200              │
│ search p95                            31.4  -> 11.9 ms    -19.5 ms          │
│                                                                              │
│ FIRST BASELINE / NOT LONGITUDINAL                                            │
│ LongMemEval_M session R@5             .708831                                │
│                                                                              │
│ EVIDENCE GAP                                                                 │
│ self-validity demotion                   EVIDENCE GAP                        │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

Every shown value/state exists in the current dashboard.

No hypothetical future numbers appear.

---

# F09 — Failure Explorer aggregate

## User intent

Move from a weak aggregate result to the actual failure population that produced it.

## Seed choice

Current formal MESA failure-stage classification does not yet exist.

The canonical wireframe therefore uses a real existing row-level diagnostic where failure structure is known: **#594 Part R proposition recognition**.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Failures                                                                    │
│ Dataset [#594 Part R proposition semantics]  Outcome [Known recall]         │
│ Current known recall: 0.148148                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ GOLD / PREDICTION MATRIX                                                    │
│                                                                              │
│ Gold known (54)       predicted known 8     predicted ambiguous 46           │
│ Gold ambiguous (13)   predicted ambiguous 13                                │
│ Gold unknown (33)     predicted known 2     ambiguous 3     unknown 28       │
│                                                                              │
│ Additional diagnostic counters                                              │
│ Wrong slot: 8                                                               │
│ Unknown -> known: 2                                                         │
│ Aspect mismatch: 4                                                          │
│ Aspect over-classification: 1                                               │
│                                                                              │
│ [Filter cases] [Inspect evidence]                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│ MESA CURRENTNESS FAILURE STAGES                                             │
│ Formal stage-classified evidence: NOT YET AVAILABLE · #694                  │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Why this structure

The frame proves the product can show:

- measured confusion structure;
- diagnostic counters;
- explicit absence of a different failure taxonomy.

It does not fabricate MESA stage percentages before #694 produces them.

---

# F10 — Failure case detail

## User intent

Inspect one benchmark case without losing aggregate context.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Failure case                                                                │
│ #594 Part R · Gold class: known · Predicted class: ambiguous               │
│ [Back to 46 known→ambiguous cases]                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ CASE EVIDENCE                                                               │
│ Case id                 {native case id from row evidence}                   │
│ Gold proposition status known                                               │
│ Predicted status        ambiguous                                           │
│ Slot result             {native value if available}                         │
│ Aspect result           {native value if available}                         │
│                                                                              │
│ CLASSIFICATION                                                              │
│ Primary observed failure known proposition not recognized                   │
│ Secondary counters       only when native evidence records them              │
├──────────────────────────────────────────────────────────────────────────────┤
│ PROVENANCE                                                                  │
│ Native row -> phase-b score/evidence -> accepted gold manifest              │
│ [Open native evidence] [Open gold definition]                               │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation rule

This frame intentionally does **not** invent a case id or text.

Until the row-level catalog exposes the native case, the placeholders above render as typed unavailable fields.

The production frame must be populated only from row-level evidence.

---

# F11 — Coverage matrix

## User intent

Understand what Agent Memory does not yet know about itself.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Evidence Coverage                                                           │
├──────────────────────┬────────────┬────────────┬────────────┬────────────────┤
│ Capability           │ AMB/MESA   │ LongMemEval│ BEAM       │ Other          │
├──────────────────────┼────────────┼────────────┼────────────┼────────────────┤
│ Retrieval            │ measured   │ measured   │ —          │ Precision ✓    │
│ Currentness          │ partial    │ measured   │ —          │ #580 measured  │
│ End-to-end QA        │ pending    │ not run    │ —          │ LoCoMo not run │
│ Scale                │ partial    │ partial     │ not run    │                │
│ Isolation/privacy    │ measured   │ —          │ —          │                │
│ Deletion/lifecycle   │ measured   │ —          │ —          │                │
│ Action memory        │ —          │ —          │ —          │ not measured   │
│ Coding experience    │ —          │ —          │ —          │ SWE-CB pending │
└──────────────────────┴────────────┴────────────┴────────────┴────────────────┘
Legend: measured · partial · not measured · evidence gap · blocked · unsupported
~~~

## Real-data validation

Current measured, partial, and missing states are derived from the dashboard and current benchmark program.

No missing cell becomes zero.

---

# F12 — Coverage-gap inspector

## User intent

Turn "not measured" into an understandable planning fact.

## Wireframe

~~~text
                                                    ┌─────────────────────────┐
                                                    │ Scale / BEAM            │
                                                    │ NOT RUN FOR AGENT MEMORY│
                                                    ├─────────────────────────┤
                                                    │ What is missing          │
                                                    │ Agent Memory BEAM       │
                                                    │ 100K / 1M / 10M evidence│
                                                    │                         │
                                                    │ Published context        │
                                                    │ Mem0 BEAM 1M .641       │
                                                    │ Cognee 100K .79          │
                                                    │ Cognee 10M .67           │
                                                    │ PUBLISHED REFERENCE ONLY │
                                                    │                         │
                                                    │ [Related benchmark plan] │
                                                    │ [Methodology]            │
                                                    └─────────────────────────┘
~~~

## Real-data validation

The missing Agent Memory BEAM evidence and the published Mem0/Cognee values are current known states.

---

# F13 — Evidence index / run browser

## User intent

Find evidence directly by benchmark, system, revision, or run.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Evidence                                                                    │
│ Search [ca0f9a7________________]  Benchmark [All] System [All] State [All]  │
├──────────────────────────────────────────────────────────────────────────────┤
│ ACCEPTED                                                                     │
│ LongMemEval_S / session / Agent Memory                                      │
│ ca0f9a7 · run 37543549261 · 419 scored · runtime failures 0   [Open]       │
│                                                                              │
│ ACCEPTED                                                                     │
│ LongMemEval_S / turn / Agent Memory                                         │
│ ca0f9a7 · run 37543552664 · 419 scored · runtime failures 0   [Open]       │
│                                                                              │
│ ACCEPTED                                                                     │
│ PrecisionMemBench / Agent Memory                                            │
│ ca0f9a7 · run 37543540355 · active 4/43                       [Open]       │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

Run ids and revisions are current accepted dashboard lane values.

---

# F14 — Run detail

## User intent

Understand exactly what one run measured and how it was produced.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Run                                                                         │
│ LongMemEval_S / session / Agent Memory                                      │
│ ACCEPTED · workflow 37543549261                                             │
├──────────────────────────────────────────────────────────────────────────────┤
│ IDENTITY                                                                     │
│ System revision       ca0f9a748b3b…                                         │
│ Lane                  longmemeval-s-retrieval-parity-v2                     │
│ Input SHA             d6f21ea9…a442                                         │
│ Scored questions      419                                                   │
│ Runtime failures      0                                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ NATIVE RESULTS                                                               │
│ recall_all@5              .823389                                            │
│ recall_all@10             .892601                                            │
│ ndcg_any@10               .878274                                            │
│ knowledge-update R@5      .972222                                            │
│ latest gold first         .457143                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ EVIDENCE                                                                     │
│ evidence.json · execution-identity.json · report.json                        │
│ [Open provenance] [Compare] [Share snapshot]                                │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

All identity and result fields are from one accepted v2 lane row.

---

# F15 — Evidence / comparability inspector

## User intent

Verify a displayed result without leaving the current analytical context.

## Wireframe

~~~text
                                              ┌───────────────────────────────┐
                                              │ Evidence inspector            │
                                              │ recall_all@5 · AM vs Mem0    │
                                              ├───────────────────────────────┤
                                              │ Comparison state: EXACT       │
                                              │                               │
                                              │ ✓ LongMemEval_S              │
                                              │ ✓ retrieval parity v2        │
                                              │ ✓ session plane              │
                                              │ ✓ input d6f21e…a442          │
                                              │ ✓ 419 scored questions       │
                                              │ ✓ compatible metric semantics│
                                              │                               │
                                              │ Agent Memory .823389         │
                                              │ Mem0 .809069                 │
                                              │ Delta +.014320               │
                                              ├───────────────────────────────┤
                                              │ Evidence chain                │
                                              │ normalized -> native -> run   │
                                              │ -> lane -> input -> revision  │
                                              │                               │
                                              │ [Open full run]               │
                                              └───────────────────────────────┘
~~~

---

# F16 — Snapshot selector / history

## User intent

Move between current and historical evidence states knowingly.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────┐
│ Evidence snapshots                                           │
├──────────────────────────────────────────────────────────────┤
│ ● Current generated snapshot                                 │
│   2026-10-06 · AM ca0f9a7 · Runtime Baseline v2             │
│                                                              │
│ Historical                                                   │
│ ○ previous accepted dashboard snapshot                       │
│   {snapshot identity from generated catalog}                 │
│                                                              │
│ Repository has newer commits than current benchmark catalog. │
│ [View current repo state]                                    │
└──────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

The current dashboard versus newer repository main validates the need for a snapshot selector and stale-state explanation.

---

# F17 — Historical shared snapshot

## User intent

Understand a shared historical result without confusing it with current evidence.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ HISTORICAL SNAPSHOT                                                         │
│ Evidence state 2026-10-06 · AM ca0f9a7                                     │
│ Newer evidence may exist.                                      [View current]│
├──────────────────────────────────────────────────────────────────────────────┤
│ Shared comparison                                                            │
│ Agent Memory vs Mem0 · LongMemEval_S · session · retrieval parity v2        │
│                                                                              │
│ recall_all@5   .823389 vs .809069                                            │
│ ndcg_any@10    .878274 vs .841054                                            │
│                                                                              │
│ Same-harness · revision-bound snapshot                                       │
│ [Why comparable?] [Evidence]                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

---

# F18 — Share / export

## User intent

Share a result without detaching its methodology.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────┐
│ Share evidence                                               │
├──────────────────────────────────────────────────────────────┤
│ Snapshot                                                     │
│ 2026-10-06 · AM ca0f9a7                                     │
│                                                              │
│ Included context                                             │
│ ✓ Agent Memory + Mem0                                        │
│ ✓ LongMemEval_S / session / retrieval parity v2             │
│ ✓ same-harness evidence class                                │
│ ✓ selected metrics                                           │
│                                                              │
│ [Copy immutable link]                                        │
│ [Export evidence-aware CSV]                                  │
│ [Export snapshot metadata JSON]                              │
│                                                              │
│ CSV export includes metric and comparability metadata.       │
└──────────────────────────────────────────────────────────────┘
~~~

---

# F19 — Methodology / metric glossary

## User intent

Learn what terms mean without reverse-engineering benchmark code.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Methodology & Metrics                                                       │
│ Search [latest gold________________]                                         │
├───────────────────────┬──────────────────────────────────────────────────────┤
│ recall_all@5          │ LongMemEval retrieval                               │
│                       │ Fraction of required gold evidence retrieved by k=5. │
│                       │ Higher is better.                                    │
│                       │ Native benchmark metric.                             │
├───────────────────────┼──────────────────────────────────────────────────────┤
│ latest gold first     │ Currentness-oriented LongMemEval diagnostic.         │
│                       │ Distinct from recall and from MESA new-fact rate.    │
├───────────────────────┼──────────────────────────────────────────────────────┤
│ published reference   │ Externally published result not reproduced in the   │
│                       │ current same-harness comparison set.                 │
└───────────────────────┴──────────────────────────────────────────────────────┘
~~~

---

# F20 — No same-harness comparator

## User intent

Understand that absence of a comparator is an evidence gap, not a product loss.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Compare · Hindsight                                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ No accepted same-harness Hindsight row exists for this profile yet.         │
│                                                                              │
│ Available now                                                               │
│ Published Hindsight LongMemEval QA: 0.946                                   │
│ Evidence class: PUBLISHED REFERENCE                                          │
│                                                                              │
│ [View published methodology] [View comparator gap]                          │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

Hindsight is currently deferred in accepted local same-harness lanes while published reference evidence exists.

---

# F21 — Blocked / unsupported evidence

## User intent

Know whether a missing result is blocked, unsupported, or simply not run.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ End-to-end judged benchmark lane                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ BLOCKED                                                                      │
│                                                                              │
│ Reader/judge configuration is frozen, but execution requires the authorized │
│ evaluation setup recorded by the benchmark program.                         │
│                                                                              │
│ This is not a score of zero and not a failed memory result.                 │
│                                                                              │
│ [View coverage] [View methodology requirement]                              │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

The benchmark dashboard records the judged profile as blocked rather than scored.

---

# F22 — Failed attempted run with previous accepted evidence

## User intent

See operational failure without losing the last valid accepted result.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ LongMemEval_S / Agent Memory                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│ LAST ACCEPTED                                                               │
│ ca0f9a7 · session recall_all@5 .823389 · runtime failures 0                │
│                                                                              │
│ LATEST ATTEMPT                                                              │
│ FAILED RUN · no accepted benchmark result                                   │
│ Failure category: {execution/import/validation state from evidence}          │
│                                                                              │
│ The failed attempt does not replace the accepted row.                       │
│ [Inspect failed attempt] [Inspect accepted run]                             │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Validation rule

Current data validates the accepted side. The failed-attempt side is a contract state and must render only when such evidence exists.

No synthetic failed score is displayed.

---

# F23 — Catalog stale relative to repository

## User intent

Know that current benchmark evidence does not yet include newer repository changes.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ⚠ BENCHMARK CATALOG BEHIND REPOSITORY                                      │
│ Evidence snapshot: ca0f9a7 · 2026-10-06                                    │
│ Repository main: newer revision available                                   │
│                                                                              │
│ Scores below remain valid for their recorded snapshot.                      │
│ They do not automatically describe the newer runtime.                       │
│                                                                              │
│ [Continue with snapshot] [View Changes]                                     │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Real-data validation

This is the current real state while repository main has moved beyond the current dashboard head.

---

# F24 — Invalid or unavailable snapshot

## User intent

Understand why a deep link cannot be reconstructed.

## Wireframe

~~~text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Snapshot unavailable                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ The requested evidence snapshot is not present in this build.               │
│                                                                              │
│ Requested: {snapshot id}                                                    │
│                                                                              │
│ No substitute evidence has been loaded automatically.                       │
│ [Open current snapshot] [Browse available snapshots]                        │
└──────────────────────────────────────────────────────────────────────────────┘
~~~

## Structural rule

Never silently redirect an unavailable historical evidence link to current evidence.

---

# R01 — Mobile Overview

## User intent

Consume current posture and shared findings without reproducing the entire desktop matrix.

## Wireframe

~~~text
┌────────────────────────────┐
│ Agent Memory Evidence      │
│ 2026-10-06 · ca0f9a7      │
│ [☰]              [Share]   │
├────────────────────────────┤
│ Overview                   │
│                            │
│ Retrieval                  │
│ COMPETITIVE · Same harness │
│ LME S R@5 .823             │
│ [Inspect]                  │
│                            │
│ Currentness                │
│ WEAK                       │
│ new-fact .200              │
│ [Inspect]                  │
│                            │
│ Performance                │
│ IMPROVED                   │
│ p95 11.9ms                 │
│ [Inspect]                  │
│                            │
│ Evidence gaps              │
│ Reasoning / QA · not meas. │
│ BEAM · not run             │
└────────────────────────────┘
~~~

---

# R02 — Mobile pair comparison

## User intent

Compare two systems legibly on a narrow screen.

## Wireframe

~~~text
┌────────────────────────────┐
│ Compare                    │
│ AM ↔ Mem0                  │
│ LongMemEval_S · Session    │
│ SAME HARNESS               │
├────────────────────────────┤
│ recall_all@5               │
│ AM       .823389           │
│ Mem0     .809069           │
│ Δ       +.014320           │
│ [Why comparable?]          │
├────────────────────────────┤
│ ndcg_any@10                │
│ AM       .878274           │
│ Mem0     .841054           │
│ Δ       +.037220           │
├────────────────────────────┤
│ [Evidence] [Share]         │
└────────────────────────────┘
~~~

## Responsive rule

Mobile does not support a many-system matrix. The user chooses a pair.

---

# R03 — Mobile evidence/run detail

## User intent

Verify a shared or selected result from a phone without losing identity metadata.

## Wireframe

~~~text
┌────────────────────────────┐
│ Run                        │
│ LME S / session / AM       │
│ ACCEPTED                   │
├────────────────────────────┤
│ Revision                   │
│ ca0f9a748b3b…              │
│                            │
│ Run                        │
│ 37543549261                │
│                            │
│ Questions                  │
│ 419                        │
│                            │
│ recall_all@5               │
│ .823389                    │
│                            │
│ ndcg_any@10                │
│ .878274                    │
│                            │
│ Runtime failures           │
│ 0                          │
│                            │
│ [Evidence chain]           │
└────────────────────────────┘
~~~

---

# R04 — Tablet comparison matrix

## User intent

Retain a matrix mental model on medium-width screens without compressing evidence into unreadable columns.

## Wireframe

~~~text
┌─────────────────────────────────────────────────────┐
│ Compare · LongMemEval_S · Session                  │
│ [AM] [Mem0] [lexical]                              │
├─────────────────────────────────────────────────────┤
│ Metric            AM        Mem0       lexical      │
│ R@5               .823      .809       .730         │
│ R@10              .893      .883       .826         │
│ nDCG@10           .878      .841       .793         │
│ KU R@5            .972      .903       .917         │
│ latest first      .457      .443       .457         │
├─────────────────────────────────────────────────────┤
│ Same-harness comparison set                        │
│ [Why comparable?] [Evidence]                       │
└─────────────────────────────────────────────────────┘
~~~

---

# Cross-frame structural validation

## Navigation coverage

Every top-level navigation destination has a canonical wireframe:

- Overview -> F01
- Compare -> F03/F04
- Benchmarks -> F05/F06
- Changes -> F07/F08
- Failures -> F09/F10
- Coverage -> F11/F12
- Evidence -> F13/F14/F15
- Methodology -> F19

## Global workflow coverage

Every global action has a frame:

- snapshot selection -> F16
- historical shared result -> F17
- share/export -> F18
- stale snapshot -> F23
- unavailable snapshot -> F24

## Required evidence-state coverage

The design explicitly covers:

- measured -> F01/F03/F06
- published reference -> F03/F04/F12/F20
- not measured -> F01/F11
- evidence gap -> F01/F11/F12
- blocked -> F21
- unsupported -> F21
- failed attempted run -> F22
- non-comparable -> F04
- stale evidence -> F23

## Diagnostic coverage

- aggregate diagnostic -> F09
- case diagnostic -> F10
- run provenance -> F14
- contextual provenance -> F15

## Responsive coverage

- mobile assessment -> R01
- mobile comparison -> R02
- mobile verification -> R03
- tablet matrix -> R04

---

# Wireframe validation rules for #699

Issue #699 is not complete until every canonical frame above has been tested against its intended data shape.

For each frame, the visual prototype must record:

1. **source fixture** — exact catalog fixture or accepted evidence snapshot used;
2. **data density check** — longest realistic labels, system names, metric names, and evidence badges;
3. **missing-state check** — applicable typed missing states;
4. **comparability check** — exact, published-reference, or non-comparable state where relevant;
5. **keyboard path** — primary actions reachable without pointer;
6. **responsive disposition** — preserve, stack, pair, scroll, or collapse;
7. **evidence path** — how a user reaches provenance;
8. **exit path** — where the frame sends the user next.

The UX prototype must not use invented benchmark scores merely to make a layout look complete.

Permitted prototype data classes are:

- committed accepted evidence;
- committed published-reference metadata;
- explicit typed missing states;
- clearly labeled schema-only placeholders for fields whose real evidence does not yet exist.

A schema-only placeholder must never look like a measured result.

---

# Definition of wireframe-complete

PRD-002 becomes **wireframe-complete** when:

- every F00-F24 frame has a reviewed structural wireframe;
- R01-R04 establish responsive patterns;
- every numeric seed can be traced to current committed evidence;
- every future-only area renders an honest missing state rather than a fabricated score;
- all navigation and drill-down paths terminate in a defined frame;
- every frame identifies the catalog fields it requires or clearly delegates them to its parent frame contract;
- #699's high-fidelity prototype can be evaluated against this inventory without inventing page structure.

This document is the structural source of truth for the future UI until a later accepted design artifact supersedes it.
