# ADR-043: Trustworthy benchmark deficits enter a mandatory remediation loop

**Status**: Proposed  
**Issue**: #719  
**Parent program**: #668  
**Related doctrine**: ADR-019, ADR-020, ADR-039, ADR-041  
**Related evidence**: #537, #574, #594, #600, #601, #694

## Decision summary

Agent Memory treats a trustworthy, material benchmark deficit as an engineering obligation.

A benchmark result is not complete merely because it has been:

- imported;
- normalized;
- added to a dashboard;
- mentioned in a limitation;
- compared with another system.

Every accepted result MUST reach an explicit operational posture.

For material deficits, the default lifecycle is:

```text
measure
  -> validate evidence
  -> classify deficit
  -> attribute failure stage
  -> map to architecture/runtime owner
  -> freeze remediation hypothesis
  -> implement general fix
  -> replay exact benchmark
  -> run regression/cross-benchmark checks
  -> compare frontier + adequacy
  -> close or iterate again
```

The loop continues until one of the following is evidenced:

1. competitive frontier achieved and capability adequacy reached;
2. an explicit, reviewed trade-off is accepted;
3. the pressured capability is deliberately rejected as a product non-goal;
4. the evidence is invalidated or shown non-comparable and replaced.

"Improved" is not a closure state by itself.

## Motivation

Agent Memory already has strong evidence discipline and several successful remediation histories.

Examples include:

- ranking/currentness work under #538;
- admitted-set BM25;
- domain-eligibility prefiltering;
- incremental integrity-attestation performance work;
- #591 identity-first materialization;
- formal MESA localization of the M4 currentness defect.

These prove the repository knows how to remediate benchmark findings.

What has been missing is one canonical rule requiring that process for every material deficit.

Without such a rule, benchmark work can degrade into:

```text
run benchmark
-> record bad number
-> explain limitation
-> move on
```

That is not sufficient for a best-in-class North Star.

## Decision

### 1. Every accepted benchmark result receives an operational posture

Every result or material metric family MUST be classified into one of these postures.

#### frontier

Agent Memory reaches or exceeds the strongest defensible same-harness competitor and also meets the declared capability-adequacy target.

This result becomes regression-protected evidence.

#### frontier_but_inadequate

Agent Memory is currently the strongest reproduced system, but the benchmark-native or product-defined quality level is still poor.

This remains an **open deficit**.

Example: winning PrecisionMemBench against weak comparators while only passing a small fraction of active cases.

#### competitive_deficit

A same-harness reproduced competitor materially outperforms Agent Memory on a claimed capability.

This creates an active remediation obligation.

#### self_regression

A successor runtime regresses accepted prior evidence outside an explicitly accepted trade-off.

This is a release/baseline blocker at the appropriate severity.

#### architecture_gap

The benchmark exposes a missing, unreachable, or uncomposed capability in the accepted runtime architecture.

Attach the evidence to an existing tranche or create a new tranche.

#### implementation_defect

The capability exists architecturally but the implementation is incorrect, inefficient, inaccessible, or incomplete.

#### evaluator_protocol_defect

The result is not trustworthy because the benchmark, evaluator, judge, data, adapter, environment, or protocol identity is invalid.

Fix evidence infrastructure before runtime remediation.

#### published_reference_gap

A published result appears stronger but is not locally reproduced under the same comparison identity.

Track the gap, qualify/reproduce the comparator, and never treat the published delta as same-harness truth.

#### unsupported_deliberate_non_goal

The benchmark pressures a capability Agent Memory explicitly declines to claim.

This requires a product/architecture decision.

A poor result cannot be relabeled unsupported merely because remediation is inconvenient.

#### blocked

The evidence path cannot currently execute because of a real external dependency, credential, provider, or access requirement.

The blocker remains visible and resumable.

### 2. Competitive frontier and capability adequacy are separate targets

Best-in-class pursuit has two independent axes:

```text
competitive target:
  how do we compare with the best defensible comparator?

adequacy target:
  is the behavior actually good enough?
```

A system may be first among reproduced comparators and still fail the capability.

Therefore:

```text
same-harness #1 != automatically solved
```

The initial PrecisionMemBench posture demonstrates why this distinction is required.

### 3. Best-in-class is per defensible native metric/capability frontier

Agent Memory does not define a universal memory score.

The target is a broad portfolio of frontier-quality native metrics while preserving hard invariants.

For each qualified benchmark/profile, the evidence program SHOULD track:

- Agent Memory value;
- strongest same-harness reproduced comparator;
- published frontier separately;
- capability adequacy target;
- gap to each target;
- material regressions on previously accepted metrics.

Where multiple metrics conflict, the system seeks a non-dominated operating point.

A trade-off must be explicit rather than hidden behind a stronger aggregate.

### 4. Trustworthy bad results default to remediation

For a material result classified as:

- `frontier_but_inadequate`;
- `competitive_deficit`;
- `self_regression`;
- `architecture_gap`;
- `implementation_defect`;

the repository MUST create or bind an owning remediation issue.

The issue remains open until the deficit reaches a valid closure state.

"Known limitation" is an evidence description, not a lifecycle state.

### 5. Deficits are attributed before implementation

A remediation plan SHOULD first locate the deficit in the runtime/evaluation pipeline.

Canonical stages:

1. write interpretation / proposition extraction;
2. identity / entity / slot resolution;
3. persistence / indexing / representation;
4. candidate generation / route reachability;
5. governed admission;
6. temporal applicability / currentness;
7. relation / graph traversal;
8. ranking / fusion / reranking;
9. controller / allocation / stopping;
10. consumer packaging / context budgeting;
11. evaluator / answer / judge layer;
12. performance / scale / durability;
13. unsupported product semantics;
14. unclassified.

A result MAY have primary and secondary stages.

`unclassified` is acceptable.

Inventing a causal explanation is not.

### 6. The benchmark that discovers the defect does not dictate the implementation

A valid remediation must be defensible as a general runtime change.

The benchmark supplies pressure and acceptance evidence.

It does not define production logic.

Prohibited examples:

- phrase lists copied from benchmark failures;
- case-specific conditionals;
- hidden-label-aware routing;
- gold-aware transformations;
- adapting runtime metadata to one benchmark while withholding it from competitors;
- repeatedly tuning constants against a final test set with no frozen tuning protocol.

### 7. Remediation hypotheses are frozen before the acceptance replay

Once root-cause evidence is sufficient, the remediation plan MUST record before the final replay:

- claimed primary failure stage;
- runtime mechanism to change;
- expected affected metrics;
- expected unaffected metrics;
- likely trade-offs;
- negative controls;
- regression suites;
- comparator posture;
- stop conditions.

A score may falsify the hypothesis.

The plan must not be rewritten after the result merely to declare success.

### 8. Exact benchmark replay is necessary but not sufficient

After a remediation:

1. replay the exact frozen benchmark/profile;
2. verify the intended metric movement;
3. inspect per-case/failure-stage changes;
4. replay affected accepted benchmarks;
5. replay hard governance/invariant suites;
6. measure performance/resource movement where relevant;
7. compare same-harness competitors where the comparison remains valid.

A benchmark improvement that breaks:

- isolation;
- deletion;
- provenance;
- authority;
- durability;
- restart safety;
- historical correctness;
- another accepted core capability;

is not an unconditional success.

### 9. Previously accepted wins become regression obligations

A material accepted improvement creates a future floor or compatibility obligation.

The floor MAY be:

- exact equality for behavior-neutral successors;
- a threshold for deterministic native metrics;
- a bounded interval where legitimate variance exists;
- a hard zero-tolerance invariant;
- a latency/resource ceiling.

This turns benchmark history into cumulative product quality rather than disconnected snapshots.

### 10. Runtime incompleteness explains deficits but does not close them

During Phase B, many poor results are expected because the runtime is unfinished.

The correct process is:

```text
bad result
-> identify missing accepted tranche
-> attach evidence
-> prioritize/reorder if warranted
-> make benchmark replay part of tranche acceptance
-> implement tranche
-> replay
-> if deficit remains, re-open root-cause analysis
```

"That subsystem is not implemented yet" is a useful diagnosis.

It is not closure evidence.

### 11. Published frontier pressure remains visible

Published results are useful directional pressure but not same-harness evidence.

If a published result materially exceeds Agent Memory:

- create/maintain a `published_reference_gap`;
- qualify the protocol/system;
- reproduce it where legally/technically possible;
- promote to `competitive_deficit` only after comparison identity is defensible.

The gap remains visible while reproduction is pending.

### 12. Priority is consequence-aware

Suggested default priority classes:

#### P0

Correctness/safety/hard invariant failures:

- isolation leak;
- deletion failure;
- authority/governance escape;
- durability/integrity corruption;
- accepted baseline regression with product consequence.

#### P1

Core claimed capability deficits against same-harness frontier or severe adequacy targets:

- currentness;
- retrieval;
- precision;
- long-horizon recall;
- scale;
- reasoning/QA once evaluator identity is qualified.

#### P2

Architecture-completeness deficits with credible benchmark pressure.

#### P3

Published frontier gaps awaiting reproduction.

#### P4

Exploratory evidence gaps.

Priority MAY be changed by an explicit roadmap/owner decision.

### 13. Closure states are strict

A deficit may close only as one of:

#### frontier

Competitive and adequacy targets are satisfied and regression protection exists.

#### accepted_tradeoff

A reviewed decision accepts a non-dominated trade-off.

The sacrificed metric stays visible.

#### deliberate_non_goal

A reviewed product/architecture decision rejects the capability.

#### invalidated_evidence

The result is proven invalid/non-comparable and replaced or withdrawn.

A deficit does not close because:

- the score improved;
- another benchmark looks better;
- an implementation tranche merged;
- the gap is old;
- a competitor result is awkward;
- the runtime is incomplete.

### 14. A machine-readable deficit ledger is canonical

The repository SHOULD maintain a versioned deficit ledger with one record per material open/closed deficit.

At minimum:

```text
deficit_id
benchmark/profile/revision
evidence class
runtime baseline/system revision
native metric
metric direction
Agent Memory value
same-harness frontier
published frontier
capability adequacy target
gaps
priority
operational posture
primary/secondary failure stages
evidence refs
owning issue
architecture tranche
remediation hypothesis
negative-control refs
replay requirements
state
opened_at
closed_at
closure evidence
remaining gap
```

The benchmark UI may later project this ledger.

Engineering governance owns it first.

### 15. Deficit reconciliation is part of benchmark acceptance

An accepted benchmark import is incomplete until material results are reconciled into the deficit ledger.

The desired future automation is:

```text
accepted evidence
-> normalize
-> scorecard/dashboard
-> deficit reconciliation
-> open/update owner issues
-> UI projection
```

Automation may identify candidate deficits.

It MUST NOT autonomously decide product scope or accept a trade-off.

### 16. The loop is allowed to discover new architecture

A benchmark may reveal that the accepted architecture is incomplete.

When evidence supports that conclusion:

- create a new architecture issue/tranche;
- update dependency assumptions;
- add acceptance/replay requirements.

The benchmark roadmap therefore influences architecture.

It does not replace architectural judgment.

## Current examples

### Formal MESA M4 currentness

Agent Memory:

- new-fact rate: 0.200;
- staleness: 0.800.

Published protocol references include:

- Naive RAG new-fact 1.000;
- Letta 0.996;
- Mem0 0.900.

The per-case classifier shows:

- write interpretation succeeds;
- slot resolution succeeds;
- state-change proposal exists;
- candidate generation succeeds;
- admission succeeds;
- temporal applicability/currentness fails in 250/250 pairs.

Posture:

`architecture_gap / P1 / #671`

The remediation target is not merely "score above 0.20".

The win must be attributed to the currentness mechanism.

### LongMemEval_S turn deep recall

Agent Memory turn recall_all@50:

- Agent Memory: 0.859189;
- Mem0: 0.895 (accepted same-harness evidence).

Posture:

`competitive_deficit / P1`

Likely owner:

#673 route fusion, subject to currentness remaining correct.

### PrecisionMemBench

Agent Memory is ahead of the currently reproduced comparators on mean precision and active passes, but absolute behavior remains poor.

Posture:

`frontier_but_inadequate`

This remains open even while Agent Memory is technically the current same-harness leader.

The root cause must be attributed before assigning a runtime tranche.

### #594 natural proposition recognition

Known recall:

0.148148

with known precision:

0.800000

Posture:

`implementation_defect / P2 / #596`

This is not the formal MESA M4 bottleneck, but it remains a general natural-data capability deficit.

## Consequences

### Positive

- bad benchmark results cannot quietly disappear into documentation;
- benchmark investment directly pressures runtime quality;
- improvement cycles continue until meaningful targets are reached;
- weak comparator pools do not create false confidence;
- historical wins become protected;
- benchmark evidence and architecture remain connected;
- best-in-class becomes an operating process rather than a slogan.

### Costs

- more open deficits will remain visible;
- some benchmark results will trigger multiple runtime tranches;
- root-cause work precedes implementation;
- maintaining regression floors increases test/evidence cost;
- reaching the frontier may require architectural changes beyond the original roadmap.

These costs are expected.

## Rejected alternatives

### Record the limitation and defer indefinitely

Rejected for material claimed capabilities.

### Optimize only the benchmark where Agent Memory is currently behind

Rejected.

Accepted architecture and adequacy gaps remain relevant.

### Close once Agent Memory beats one comparator

Rejected.

A weak comparator pool is not an adequacy standard.

### One weighted leaderboard

Rejected.

It hides trade-offs and breaks benchmark-native semantics.

### Tune until the score rises

Rejected.

Without a frozen hypothesis and negative controls, that is benchmark fitting.

### Ignore published frontier values

Rejected.

They are useful pressure, but remain a distinct evidence class.

## Status and adoption

**Proposed.**

Adoption requires:

1. deficit-ledger schema;
2. initial ledger seeded from current accepted evidence;
3. validation tests;
4. linkage to #668 / benchmark import workflow;
5. at least one real remediation cycle closed through the ledger.

This ADR does not change runtime authority or memory semantics.

It governs how benchmark evidence drives engineering follow-through.
