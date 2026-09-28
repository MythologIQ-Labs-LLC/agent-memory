# Post-#550 Architecture Reconciliation

Status: architecture reconciliation at `main` `273722e4359c4e8f60bf4fc508788fa28a2feb3d` after #550 / PR #590. This document does not promote ADR-039; ADR-039 remains **Proposed**. It does not replace the historical evidence in `docs/57-query-conditioned-applicability.md`; it records the architecture that now exists after policy 3.1.0 and write-time proposition semantics were added.

## 1. Why this reconciliation exists

#550 added a native semantic layer between memory text and governed lifecycle behavior without changing external retrieval order on AgentMemBench or LongMemEval_S. That is architecturally important but behaviorally conservative.

The system now has two typed interpretation surfaces:

1. query-side temporal intent, used to describe what temporal regime a recall request is asking about;
2. memory-side write semantics, used to describe what a retained memory says about its proposition, cardinality, temporal aspect, and bounded self-validity.

These surfaces are evidence. Neither creates authority.

The post-#550 architecture is therefore:

```text
WRITE
memory observation
  -> explicit caller metadata
  -> bounded deterministic write-time interpretation
       proposition identity candidate
       cardinality evidence
       temporal aspect evidence
       bounded self-validity evidence
       change / coexistence / hedge / self-claim markers
  -> same-slot relation classification
       same_value | coexistence | state_change_candidate | conflict | unresolved
  -> optional governed state-change proposal
  -> existing governed lifecycle
  -> persisted fact + version-pinned semantic evidence

READ
query
  -> typed temporal intent
  -> candidate generation
  -> canonical scope/lifecycle admission
  -> contextual current-policy admission
  -> typed temporal applicability
       caller-declared validity
       interpreted self-validity as LIMIT-ONLY evidence
       unknown temporal basis
  -> relevance / route evidence
  -> deterministic staged ordering
  -> context surface
```

## 2. Load-bearing boundaries

The following remain architectural invariants:

```text
candidate retrieval != governed recall admission
ranking != recall admission
ranking != truth
relevance != currentness
staleness != irrelevance
age != staleness
recency != authority
newer != superseding
metabolic stability != temporal validity
reinforcement != currentness
interpretation != authority
classifier confidence != truth
conflict detection != mutation
proposal != application
benchmark score != doctrine
```

#550 does not change these boundaries. It adds evidence that later policies may consume under them.

## 3. Policy 3.1.0 relative to docs/57

`docs/57-query-conditioned-applicability.md` remains the historical reference profile for the 3.0.x architecture and its frozen replay evidence. Policy 3.1.0 extends its temporal applicability evidence model in one narrow way.

### 3.1 Caller-declared validity

Caller-declared `valid_from` / `valid_until` remains the strongest temporal validity source available to ranking.

It may establish both:

- applicability; and
- incompatibility with the target instant.

Caller-declared temporal metadata remains evidence, not lifecycle authority. Expiry does not itself tombstone, supersede, or reject a fact at admission.

### 3.2 Interpreted self-validity

A resolved #550 self-validity window may participate only when the caller did not declare a validity interval.

Its authority is deliberately asymmetric:

```text
interpreted self-validity may LIMIT applicability
interpreted self-validity may NOT AFFIRM applicability
```

Examples:

- `for the next two weeks` may establish that the memory is outside its own interval after the interval ends;
- `starting next month` may establish that the memory is prospectively applicable before the start;
- the same interpreted text may not declare itself positively current merely because its own interval contains the target.

This protects the self-promotion boundary discovered by the #580 gauntlet. Memory text may make a weaker claim about itself. It may not grant itself currentness authority.

Every applicability label records its basis when a basis exists:

```text
caller_declared
interpreted
unknown / none
```

### 3.3 Lexical relevance is unchanged

Policy 3.1.0 does not contain the held #583 lexical-intent separation candidate.

BM25, tokenization, sorted deterministic summation, route evidence, and the lexical query remain as they were under 3.0.1.

The version bump is required because temporal applicability behavior is externally observable even though the external benchmark corpora used for #550 produced zero changed rows.

## 4. Typed memory-side semantic carrier

#550 establishes a versioned, persisted semantic carrier for each new write.

It may contain:

- proposition identity candidate: entity / property / value;
- proposition status: known / unknown / ambiguous;
- cardinality: single-valued / multi-valued / hierarchical / unknown;
- temporal aspect: present / prospective / past-habitual plus cue evidence;
- bounded self-validity with explicit anchor provenance;
- change, coexistence, hedge, and self-claim evidence;
- same-slot relation evidence;
- governed state-change proposals.

Every interpretation records:

```text
authority_effect = none
```

A proposal may be applied only by an explicit caller through the existing governed correction path using `replacement_kind="state_change"`. The interpreter never auto-applies a proposal.

Pre-#550 facts remain uninterpreted unless a future explicit migration defines how they are to be interpreted. Runtime upgrades must not silently reinterpret historical writes.

## 5. Query-side intent and memory-side aspect are different evidence

The #583 HOLD established that temporal words such as `currently`, `planning to`, and `going to` can be both query-intent cues and meaningful memory content.

The architecture therefore distinguishes:

```text
query temporal intent evidence
!=
memory temporal aspect evidence
!=
lexical relevance evidence
```

A redesigned #583 must preserve this distinction.

The memory-side aspect marker is a required semantic carrier for future #583 work, but it is not ranking authority and does not itself boost a candidate.

The query-side consumed-span contract still needs calibration under #585 before temporal intent cues can be safely removed from lexical relevance.

## 6. Admission and purpose limitation

Canonical `GovernedMemoryAdapter` admission owns the hard retained-memory boundaries that are currently implemented there:

- tenant;
- isolation domains and required compartments;
- shared-space membership;
- project;
- task;
- tombstone / supersession / dispute lifecycle checks.

Purpose is carried in write and recall context, but current-purpose restriction is intentionally layered through the contextual recall-admission profile after canonical admission.

```text
substrate retrieval
  -> canonical admission
  -> contextual current-policy admission
  -> context surface
```

The contextual layer may tighten canonical admission and may fail closed when configured as required. It may never resurrect a candidate refused by canonical admission.

An older adapter comment saying `project/task/purpose gates continue below` is descriptive drift: the canonical helper itself enforces project/task, while current-purpose re-evaluation belongs to the contextual layer. The architecture is compositional rather than one monolithic scope gate.

## 7. What #550 did not change

#550 did not:

- automatically supersede independent writes;
- make interpreted proposition identity authoritative;
- infer universal property cardinality from a domain ontology;
- grant memory text truth or currentness authority;
- remove temporal query cues from lexical relevance;
- solve unknown-basis ordering (#584);
- calibrate ambiguous `now/currently` query language (#585);
- model exception/override precedence (#586);
- change governed historical state-change semantics (#549);
- change durable dispute semantics (#582).

External replay at the #550 reviewed runtime produced:

- AgentMemBench: zero non-timing differences and all 2,051 search orders unchanged on seeds 0 and 1;
- LongMemEval_S: 3,000 / 3,000 rows identical with zero rank differences;
- no governance or failure deltas.

The primary observed cost was performance: populating fact attributes exposed eager attribute decoding during candidate generation. That is tracked by #591 and is substrate work, not a reason to remove typed semantics.

## 8. Remaining architecture versus implementation work

The remaining work is not one undifferentiated architecture problem.

### Implementation / optimization

- **#591:** candidate generation should avoid full fact/attribute materialization before eligibility is established. Preferred direction: scope-first or two-phase candidate materialization, with lazy decoding as an implementation technique where useful.

### Interpreter calibration

- **#585:** distinguish unambiguous temporal intent spans (`Where do I live now?`) from discourse/content uses (`Now, explain the plan.`), with typed source spans and no authority effect.

### Ranking-policy decision

- **#584:** define the defensible relationship between affirmed applicability, unknown temporal basis, and known temporal incompatibility under explicit current intent, without newest-wins or a scalar relevance-plus-recency shortcut.

### Relevance / intent seam

- **#583:** redesign only after #550 and #585 evidence exists. A candidate may remove a query cue from lexical relevance only if doing so does not erase the candidate memory's typed temporal meaning or regress external retrieval/currentness.

### New semantic relation

- **#586:** exception/override precedence is the remaining item that likely requires a genuinely new native semantic relation such as `exception_to` / `overrides`, bounded by interval, scope, provenance, and governance. It should not be smuggled into recency ranking.

## 9. Recommended sequencing from this boundary

```text
post-#550 architecture reconciliation
    -> #591 candidate-generation performance
    -> source-anchored / proposition-quality benchmark tranche
    -> canonical current benchmark dashboard
    -> #585 query-intent span calibration
    -> redesigned #583
    -> #580 replay
    -> #584 policy ruling
    -> RC1 declaration decision
    -> #586 / broader semantic relations unless evidence pulls it earlier
```

ADR-039 remains Proposed through this sequence. In particular, #584 asks an unresolved ordering question that should be answered before doctrine promotion.

## 10. RC posture

The post-#550 result supports continuing implementation and qualification rather than reopening the entire architecture.

Agent Memory now has a coherent separation between:

- write-time semantic interpretation;
- governed lifecycle authority;
- query temporal intent;
- canonical recall admission;
- contextual current-policy admission;
- temporal applicability;
- relevance/ranking;
- deterministic explanation/provenance.

The next objective is to harden and measure these seams, not to replace them.