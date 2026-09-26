# Cross-System Comparison Matrix

Status: canonical development-governance specification

Authority effect: none

This document defines how Agent Memory uses external benchmark evidence to answer a deceptively simple question:

> **Where does Agent Memory measure against other memory systems, and what standard should development be trying to meet?**

The answer must be evidence-driven, multidimensional, protocol-aware, and resistant to benchmark theater.

The Cross-System Comparison Matrix is therefore **not primarily a leaderboard**. It is a development-governance instrument.

Its purpose is to keep the project from doing either of the following:

1. declaring a result "good" merely because an internal score improved; or
2. chasing an external score in a way that weakens Agent Memory's architectural and governance invariants.

The matrix establishes a visible, evidence-bound goal line for every memory capability the project considers material.

---

## 1. Governing question

For each material capability, Agent Memory should be able to answer:

```text
What does Agent Memory currently demonstrate?

What is the strongest credible external standard we can compare against?

How comparable is that evidence?

Are we below, approaching, at, or above that standard?

If comparison is not yet valid, is the defect in the product or in the evidence?

What architectural constraints must remain true while closing the gap?
```

The matrix exists to make those answers explicit.

A raw benchmark score is not sufficient.

```text
score != development standard
score != authority
score != architecture
score != production readiness
```

---

## 2. The goal line is capability-specific

Agent Memory does not seek one universal competitor or one overall score.

A single external system may be excellent at retrieval and weak at deletion. Another may have excellent temporal update behavior and weak isolation. Another may dominate a benchmark because its assumptions differ from Agent Memory's product contract.

The project's target is therefore a **composite external standard**:

> For each material capability, identify the strongest credible demonstrated external behavior that is meaningfully comparable, then determine whether Agent Memory meets or exceeds that standard without violating its own governing invariants.

The external reference may therefore differ by capability.

Examples:

```text
retrieval quality           -> strongest comparable retrieval evidence
conflict/currentness        -> strongest comparable temporal-update evidence
isolation                   -> strongest comparable leakage result
deletion                    -> strongest comparable deletion evidence
durability                  -> strongest comparable recovery/integrity evidence
continual learning          -> strongest comparable continual-learning result
memory-to-action            -> strongest comparable action-grounding result
multimodal memory           -> strongest comparable multimodal result
```

The project is not trying to become Mem0, Letta, Graphiti, Hindsight, Jev, LangMem, or any other single runtime.

It is trying to meet the strongest credible standard across the capabilities it claims matter.

---

## 3. Development posture states

Every matrix row must carry a development posture.

The canonical vocabulary is:

| Posture | Meaning | Default development implication |
|---|---|---|
| `below_standard` | Credible comparable evidence shows Agent Memory materially below the strongest relevant reference. | Active remediation candidate. |
| `approaching_standard` | Agent Memory remains below the reference, but the remaining gap is bounded or statistically uncertain. | Continue evidence-backed remediation where product-relevant. |
| `at_standard` | Agent Memory is materially equivalent to the strongest credible reference for the measured capability. | Preserve by regression testing; do not optimize merely to inflate the number. |
| `above_reference` | Comparable evidence shows Agent Memory materially above the current credible external reference. | Preserve; investigate whether the result reflects a genuine capability advantage or protocol artifact. |
| `evidence_gap` | The capability matters, but protocol-matched external evidence is insufficient to determine competitive position. | Improve comparison evidence before changing architecture. |
| `field_gap` | No credible external benchmark/reference adequately measures the capability. | Qualify external alternatives first; a neutral Gauntlet-native gap suite may be justified only under Coverage Atlas rules. |
| `not_comparable` | Results exist, but corpus, scorer, protocol, projection, metric, or denominator differences prohibit ranking. | Display context separately; do not treat the score as a goal-line measurement. |
| `not_applicable` | The external capability/metric does not apply to the declared Agent Memory product profile. | Explain the product-contract difference; do not manufacture support to improve a table. |

These states are intentionally not reducible to a traffic-light score.

A weak result and a missing comparison are different defects.

```text
performance gap != evidence gap
```

---

## 4. Comparability classes

A development posture may only be assigned after the external comparison itself is classified.

The canonical comparability classes are:

### `exact`

Direct ranking is allowed.

Required characteristics include, where applicable:

```text
same benchmark/profile revision
same canonical corpus/input identity
same selection/subset semantics
same scorer/evaluator semantics
same metric definition
same denominator
same top-k / result-cardinality semantics
same relevant protocol assumptions
```

Environment or implementation language may differ where the benchmark is explicitly designed to tolerate that difference.

### `compatible`

Comparison is useful but must carry an explicit caveat.

Examples:

- same dataset and metric but a documented execution/runtime difference;
- same benchmark protocol with a minor implementation variation proven not to alter metric semantics;
- upstream and Gauntlet re-expression that have been differentially validated for the relevant phases.

Compatible evidence may guide development, but claims must preserve the caveat.

### `related`

The results concern the same benchmark family or capability but are not rank-comparable.

Examples:

```text
retrieval recall vs final QA accuracy
exact-source recall vs LLM-judged recall
same dataset with a different context projection
same benchmark name with a different scorer
different result-cardinality rules
```

Related evidence may be shown for context. It may not establish `below_standard`, `at_standard`, or `above_reference` by itself.

### `non_comparable`

The evidence is too different, incomplete, or weakly bound to support a meaningful cross-system comparison.

Historical metadata may remain recorded, but it must not be presented as a competitive result.

---

## 5. Evidence provenance classes

Comparability and trust are separate axes.

Every external result should also identify its provenance, such as:

```text
maintainer_replayed
independently_published
reproducible_external_artifact
community_reproducible_submission
vendor_reproducible_submission
self_reported
historical_metadata
```

A perfectly matching protocol with only a self-reported aggregate score is weaker evidence than a complete independent artifact.

Conversely, a meticulously reproduced result using a materially different protocol remains non-comparable.

Trust does not repair protocol mismatch.

Protocol match does not repair missing evidence.

---

## 6. Required matrix fields

At minimum, every canonical comparison row should identify:

```text
capability family
benchmark/profile
metric
Agent Memory result
Agent Memory revision
external reference system
external result
external system revision/version where known
benchmark/dataset revision
input digest where known
comparability class
evidence provenance
confidence / statistical interval where available
development posture
architectural constraints
known caveats
recommended next action
```

Where several external systems establish the reference range, preserve them rather than collapsing the row to one convenient competitor.

---

## 7. Architectural constraints remain above the goal line

The matrix creates development pressure. It does not become architecture authority.

Agent Memory must not close a benchmark gap by violating governing doctrine.

Examples:

```text
recency != truth
ranking != recall admission
similarity != authority
classifier output != permission
benchmark score != authority
candidate retrieval != governed recall admission
decay != falsity
temporal applicability != lifecycle authority
```

Therefore a matrix row should record relevant non-negotiable constraints.

Example:

```text
Capability: conflict/currentness
Agent Memory: below comparable external references

Constraint while remediating:
- do not make newer == true
- do not infer supersession merely to improve the benchmark
- preserve historical truth/state-change semantics
- preserve governed correction and authority boundaries
- ranking may not become mutation/admission authority
```

The acceptable target is therefore:

```text
external performance standard
        +
Agent Memory architectural invariants
        =
valid development target
```

A competitor's strong result may reveal a product gap without making the competitor's mechanism acceptable.

---

## 8. How the matrix governs prioritization

The matrix should inform issue priority alongside security, correctness, user impact, and product commitments.

Conceptually, remediation pressure grows with:

```text
capability importance
x magnitude of credible external gap
x confidence in comparability
x product relevance
```

This is a decision framework, not a required numeric formula.

### High-confidence performance gap

When Agent Memory is clearly below a protocol-matched external standard:

1. classify the gap;
2. inspect mechanism before changing architecture;
3. open or prioritize bounded remediation;
4. replay the same frozen comparison after the change;
5. update the matrix.

### Evidence gap

When peer evidence is not protocol-comparable:

1. do **not** infer that the product is behind;
2. improve or reproduce the external comparison first;
3. preserve the unknown state until the evidence supports a posture change.

### At or above standard

When a capability already meets the strongest credible comparison:

1. preserve it with regression tests;
2. avoid spending engineering effort to inflate a saturated metric;
3. shift attention toward meaningful gaps.

This is one of the primary purposes of the matrix: prevent both premature victory and pointless optimization.

---

## 9. Initial evidence-backed posture

The table below is an **initial governance snapshot**, not a universal leaderboard.

It records only comparisons currently supported strongly enough to be useful.

| Capability | Agent Memory evidence | External reference | Comparability | Initial posture | Notes |
|---|---|---|---|---|---|
| Cross-user isolation | AgentMemBench: `cross_user_leak_rate = 0.000` | Naive RAG, Mem0, LangMem, Graphiti, Letta all report `0.000` in the formal AgentMemBench artifact | compatible/exact for deterministic phase | `at_standard` | Preserve zero leakage. Lower than zero is not a product roadmap. |
| Audited deletion | AgentMemBench: `1.000` | Naive RAG `1.000`, Mem0 `1.000`, Graphiti `1.000`, Letta `1.000`, LangMem `0.500` | compatible/exact for deterministic phase | `at_standard` | Agent Memory's result is governed tombstone deletion in this profile; permanent erasure remains a distinct contract. |
| Independent-write conflict/currentness | AgentMemBench policy 3.0.0 / shipped relevance: new-fact `0.20`, stale `0.80` | Naive RAG `1.000`, Letta `0.996`, Mem0 `0.900`, LangMem `0.680`, Graphiti `0.004` | compatible/exact for deterministic phase | `below_standard` | Material gap, but remediation may not collapse recency into truth or invent supersession. |
| AgentMemBench retrieval | exact-source recall@5 `0.899` | Upstream formal systems report LLM-judged Recall@5 | related | `evidence_gap` | Same benchmark family but different retrieval metric semantics. Do not rank `.899` against upstream judged recall. |
| LongMemEval_S retrieval | session recall_all@5 `0.823`; turn recall_all@10 `0.723` under shipped BM25 relevance | Multiple systems publish LongMemEval results, generally with answer-generation/judge protocols rather than this retrieval profile | related | `evidence_gap` | Strong internal/external-workload evidence, insufficient current protocol match for a peer ranking. |
| SWE-ContextBench Lite | canonical Agent Memory 100-edge run pending | research metadata: GPT-4.1-mini and Jev BM25; historical Jin Agent Memory run incomplete-provenance | currently non-comparable | `evidence_gap` | Exact redacted 300-task projection and batch/distractor provenance are required before ranking. |
| Concurrency correctness | shared-handle operation success `1.0` after #530 | formal upstream systems contain concurrency evidence | compatible only after metric/environment normalization | `evidence_gap` | Correctness is established; a cross-system throughput ranking is not yet normalized. |
| Durability / integrity | extensive native recovery, attestation, tamper and migration evidence | no qualified external benchmark currently supplies a comparable broad durability/integrity surface | none | `field_gap` | #571 owns neutral Gauntlet specification work; do not call native evidence external superiority evidence. |
| Governance / authority laundering | Governance Gauntlet alpha exists with real Agent Memory contestant | broad credible cross-system population not yet established | none | `field_gap` | This is a likely differentiating capability, but the field lacks a qualified comparative standard today. |

This snapshot is expected to evolve as LongMemEval_M, external benchmark integrations, and additional Gauntlet contestants produce stronger evidence.

---

## 10. LongMemEval_M handling

LongMemEval_M must not automatically become a competitive ranking merely because the run is large and expensive.

When the run completes:

1. freeze the Agent Memory result and exact profile identity;
2. identify published external systems that used the same corpus/profile;
3. inspect whether their evaluation measured retrieval, final answer quality, or another target;
4. classify each candidate comparison as `exact`, `compatible`, `related`, or `non_comparable`;
5. update this matrix only where the comparison supports a legitimate posture change.

A larger dataset does not repair scorer mismatch.

---

## 11. SWE-ContextBench Lite handling

The historical Jin result (`1.00 / 0.06 / 0.10`) remains useful historical metadata, not a canonical current-runtime comparison.

The current blocker is evidence identity, not runner capability.

A rank-comparable Agent Memory result requires the frozen research-note-compatible input, including:

```text
300 historical task projections
99 related/new issues
100 gold relationship edges
exact multi-gold handling
exact batch/distractor selection
exact query/context projection
exact scorer
exact result-cardinality semantics
input hashes
system/runner revision binding
```

Until those inputs are recovered, the correct matrix state is `evidence_gap`, not `below_standard` or `above_reference`.

---

## 12. Relationship to the Gauntlet

The Cross-System Comparison Matrix is a consumer of Gauntlet and external benchmark evidence.

It does not replace:

- benchmark-native reports;
- the Benchmark Coverage Atlas;
- Memory Evaluation normalized evidence;
- Governance Gauntlet results;
- future Durability & Integrity Gauntlet results.

Conceptually:

```text
external benchmark / Gauntlet run
        |
        v
raw benchmark-native evidence
        |
        v
normalized evidence
        |
        v
comparability classification
        |
        v
Cross-System Comparison Matrix
        |
        v
development posture / goal line
```

The matrix may identify a coverage gap. It may not manufacture evidence to fill that gap.

---

## 13. Relationship to future community results

If external developers eventually run Gauntlet profiles and submit evidence, comparable results should only enter the canonical matrix after validation against the exact profile/corpus/scorer contract.

The future submission model should preserve:

```text
system under test may vary
canonical workload may not

score submission != evidence
validated evidence bundle -> eligible comparison
```

Repository/package separation of the Gauntlet is explicitly **deferred**. The current priority is benchmark quality, evidence quality, and development-governance value inside Agent Memory.

The Gauntlet should nevertheless maintain neutral boundaries so later external distribution does not require redesigning benchmark semantics.

---

## 14. Update rule for implementation and benchmark work

Material benchmark/remediation work should state whether it changes the Cross-System Comparison Matrix.

Recommended PR/issue closeout questions:

```text
Did this work change a cross-system posture?

If yes:
- which capability row changed?
- what evidence supports the change?
- what is the comparability class?
- did any architectural constraint change? (normally: no)

If no:
- what evidence or capability did the work add?
- does it reduce an evidence gap or field gap?
```

A matrix posture must not change because a maintainer prefers the new result.

It changes because the bound evidence changed.

---

## 15. Machine-readable backing

The long-term canonical source should be machine-readable evidence from which the human matrix can be generated.

A future backing artifact may resemble:

```text
reports/benchmarks/cross-system-comparison.json
```

It should contain references, not hand-copied claims, to the underlying evidence artifacts.

The generated/documentation layer should make it difficult to create contradictory values between benchmark reports and the comparison matrix.

This specification does not require that generator to exist before the governance model is adopted.

---

## 16. Non-goals

The Cross-System Comparison Matrix is not:

- one universal memory score;
- a marketing leaderboard;
- proof that the highest benchmark score is the best architecture;
- permission to tune against test questions;
- permission to weaken governance for retrieval gains;
- a requirement that every external runtime implement Agent Memory semantics;
- a replacement for benchmark-native evidence;
- a production-readiness certification;
- a claim that Agent Memory must beat every competitor on every metric.

---

## 17. Canonical development principle

The project should be able to answer, at any meaningful point in development:

> **For every capability we claim to care about, what is the strongest credible external standard, where do we currently stand against it, how certain are we that the comparison is valid, and what remains before we consider that capability competitive?**

If the repository cannot answer that question, the absence itself is an evidence gap that should be visible in the matrix.

The purpose is not to guarantee that Agent Memory always wins.

The purpose is to prevent the project from losing without knowing it, winning without proving it, or stopping before the evidence says the solution is good enough.
