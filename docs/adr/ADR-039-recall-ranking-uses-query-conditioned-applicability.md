# ADR-039: Recall ranking uses query-conditioned applicability over typed relevance and temporal evidence

**Status**: Proposed (2026-09-25)  
**Doctrine review**: #544  
**Related product evidence**: #531, #537, #538  
**Related doctrine**: ADR-011, ADR-013, ADR-020, ADR-022, ADR-023, ADR-030, ADR-031, ADR-035  
**Primary documents**: `docs/03-scoring-and-decay.md`, `docs/18-temporal-causality-layer.md`, `docs/21-forgetting-consolidation-and-memory-metabolism.md`, `docs/24-determinism-probability-and-governed-uncertainty.md`, `docs/26-governed-recall-planner.md`

## Decision summary

Agent Memory will treat **relevance**, **temporal applicability**, **metabolic/stability evidence**, and **authority/admission** as semantically distinct classes of evidence that participate in different stages of recall.

The canonical post-admission ordering concept is **query-conditioned applicability**, not a universal relevance score, recency score, relevance-versus-currentness contest, or `relevance + recency` scalar.

The controlling shape is:

```text
query
  -> query interpretation
       semantic / task / entity intent
       temporal intent
       expected recall shape
  -> candidate discovery
  -> governed recall admission
  -> admitted candidate set
  -> typed evidence evaluation
       relevance evidence R(q,m)
       temporal applicability T(q,m)
       optional metabolic/stability evidence M(m)
       route / relation / provenance evidence
  -> explicit versioned applicability policy F(q,R,T,M,...)
  -> ordered or structured recall set
```

The dimensions may interact under query-specific policy, but they are not interchangeable and must remain inspectable after the final ordering decision.

In particular:

```text
ranking != recall admission
ranking != truth
relevance != permission
recency != authority
newer != true
newer != superseding
metabolic stability != temporal validity
reinforcement != currentness
historical != stale-by-definition
similarity != applicability
benchmark score != doctrine authority
```

This ADR does not require one universal numerical ranking function. A conforming implementation may use staged, lexicographic, constrained, normalized, learned, probabilistic, or hybrid ordering internally, provided it preserves the typed evidence boundaries, deterministic/governed constraints that apply to the profile, inspectability, and the non-compensation rules in this decision.

---

## Context

Agent Memory has always carried several architectural separations that are individually correct but were not yet composed into one complete ranking doctrine.

ADR-011 and `docs/18-temporal-causality-layer.md` require the system to distinguish event time, observation time, valid time, transaction time, decision time, supersession time, and expiry. A memory can be historically correct while no longer current. A current-state query should not prefer stale evidence merely because it is semantically closer.

ADR-013 and `docs/26-governed-recall-planner.md` separate candidate discovery from governed admission and ranking. Relevance is not permission. Candidate generation can be probabilistic; scope, tenancy, currentness requirements, dispute state, tombstones, sensitivity, and other hard boundaries remain governed.

The cognitive-metabolism work further distinguishes saturation, reinforcement, contradiction pressure, half-life, consolidation candidacy, and pruning pressure from truth and authority. Time-sensitive metabolic influence is not the same concept as the valid-time semantics of a proposition.

The first public benchmark-gauntlet cycle exposed the missing composition rule.

### Benchmark evidence that forced the question

AgentMemBench wrote an old fact and a newer contradictory fact as independent observations, then asked for the current value. The pre-remediation Agent Memory runtime ranked the newer fact first in zero of the 250 conflict cases. LongMemEval_S independently showed that Agent Memory often retrieved both older and newer evidence but ordered stale evidence ahead of the latest applicable evidence.

The first bounded remediation introduced an explicit post-admission ranking policy and replaced the accidental stable-ID anti-recency tie-break with temporal ordering among otherwise equal candidates.

That change produced a deliberately informative mixed result:

- AgentMemBench current-fact success improved materially;
- LongMemEval_S latest-gold-first ordering improved materially;
- some ordinary retrieval metrics regressed because newer, equally relevant **non-gold** memories moved ahead of older gold evidence when the query was not actually asking for the newest state.

The observed failure was not simply “too little recency.” It was that temporal evidence was being applied without sufficiently explicit query temporal intent.

That result falsifies two simplistic models:

```text
Model A: relevance always dominates recency
Model B: newest should win whenever relevance is close
```

It also challenges the framing of relevance and currentness as opposing scalar scores whose weights must be tuned until one appropriately overpowers the other.

The architectural question is therefore broader:

> How should a governed memory system combine semantic/task relevance, temporal applicability, lifecycle/metabolic evidence, and route evidence into useful recall without erasing the different meanings of those signals or allowing one kind of evidence to launder another?

---

## Problem statement

A retrieval system eventually has to make a selection or ordering decision. That implementation fact creates a recurring temptation to convert every signal into a number and sum the numbers.

For Agent Memory, that temptation is dangerous because the inputs do not answer the same question.

Examples:

```text
semantic similarity:
  "How much does this content resemble the query?"

logical identity:
  "Is this the exact memory/proposition/entity the query identifies?"

temporal applicability:
  "Does this claim apply to the time or interval the query is asking about?"

metabolic strength:
  "How established, reinforced, disputed, neglected, or decayed is this retained memory?"

scope/admission:
  "Is this memory permitted to influence this recall at all?"
```

Treating these as homogeneous terms causes at least six classes of architectural error:

1. a temporally impossible memory can win because its semantic similarity is high enough;
2. a semantically irrelevant recent memory can win because it is newer;
3. a highly reinforced historical fact can be mistaken for the current state;
4. a recent unverified observation can be mistaken for truth because “freshness” boosts it;
5. an inadmissible candidate can gain influence if authority becomes just another ranking feature;
6. benchmark-specific score improvement can become a de facto doctrine change without an explicit architectural decision.

The system therefore needs a retrieval ontology in which typed evidence may be combined into one decision without becoming one meaning.

---

## Definitions

### Query

A **query** is the recall request plus the contextual information needed to interpret it. It is not limited to raw user text.

Where available, query context may include:

```text
request text
requester / agent identity
purpose
scope / tenant / project
current clock / reference time
explicit as-of time
active task or plan
expected answer shape
logical memory refs
entity refs
policy requirements
```

### Candidate

A **candidate** is a memory or derived memory artifact surfaced by one or more retrieval routes before final governed admission and ordering.

Candidate discovery does not establish applicability, currentness, truth, or authority.

### Admitted candidate

An **admitted candidate** is a candidate that has crossed the canonical governed recall-admission boundary for the current requester, purpose, scope, destination, lifecycle/currentness posture, and policy context.

Admission answers whether a memory **may influence** the recall. It does not answer how useful it is.

### Relevance evidence

**Relevance evidence** describes the relationship between a query and a memory along one or more semantic, logical, task, entity, causal, relational, provenance, procedural, or retrieval-route dimensions.

Relevance is not defined as one universal scalar.

A conceptual representation is:

```text
R(q,m) = {
  lexical_relation,
  semantic_relation,
  logical_identity_relation,
  entity_relation,
  task_relation,
  causal_relation,
  provenance_relation,
  procedural_relation,
  graph_relation,
  route_evidence,
  ...
}
```

An implementation may normalize some or all of these into comparable quantities, but normalization is an implementation claim that must identify what comparability means and what information is lost.

### Temporal evidence

**Temporal evidence** records temporal properties of a memory or its underlying proposition/event.

Relevant fields may include:

```text
event_time
observation_time
valid_from
valid_until
transaction_time / recorded_at
superseded_at
expiry_time
decision_time
source time
witnessed time
```

These clocks are not interchangeable.

### Query temporal intent

**Query temporal intent** describes the time relationship requested by the query.

The first canonical vocabulary is:

```text
current
as_of
historical
atemporal_or_unspecified
prospective
```

This vocabulary may later be extended, but each extension must preserve compatibility semantics.

#### `current`

The query asks for the presently applicable state relative to a reference clock.

Examples:

```text
Where does Kevin work now?
What is the current deployment endpoint?
Which plan is active?
```

#### `as_of`

The query asks for the state applicable at a specific instant or bounded interval.

Examples:

```text
Where did Kevin work on 2024-10-01?
What policy was active when decision D was made?
What did the configuration say immediately before the migration?
```

#### `historical`

The query seeks past evidence or chronology but may not specify one exact instant.

Examples:

```text
How did this architecture evolve?
What approaches did we try before the current one?
What happened during the outage?
```

#### `atemporal_or_unspecified`

The query does not establish that newer or older evidence should be preferred.

Examples:

```text
What did I write about memory half-life?
Which ideas influenced this architecture?
What examples explain governed recall?
```

“Unspecified” must not silently mean “current” unless the policy explicitly justifies that default for the query class and records the inference.

#### `prospective`

The query asks about future-valid intent, plans, commitments, predictions, or prospective memory.

Examples:

```text
What am I supposed to do next week?
Which migration is scheduled for Monday?
What outcome did we predict for the next release?
```

### Temporal-intent confidence and evidence

Temporal intent may be explicit or inferred.

A useful implementation shape is:

```text
TemporalIntent {
  mode
  target_time_or_interval
  confidence_or_posture
  evidence
  interpreter_ref
  interpreter_version
}
```

A deterministic parser may establish explicit phrases such as `as of 2026-09-01`. A classifier or LLM may infer unstated intent. Inferred intent remains estimator output and does not acquire authority.

When temporal intent is materially uncertain, implementations should prefer preserving ambiguity, surfacing multiple plausible temporal candidates, or using a conservative fallback rather than fabricating a high-confidence current-state interpretation.

### Temporal applicability

**Temporal applicability** is the relationship between query temporal intent and the validity/temporal evidence of a memory.

It is not raw recency and not merely a timestamp difference.

Conceptually:

```text
T(q,m) = relation(
  query temporal target,
  memory validity interval,
  event/observation/transaction evidence,
  supersession/correction state
)
```

Possible descriptive outcomes may include:

```text
applicable
partially_applicable
historically_applicable
prospectively_applicable
outside_target_interval
unknown_temporal_basis
conflicting_temporal_evidence
```

A profile may represent these with richer typed structures rather than this exact enumeration.

### Currentness

**Currentness** is one special case of temporal applicability: whether a claim is presently applicable for a current-state query under the declared reference clock and currentness rules.

Currentness is therefore not a universal property independent of query context.

The statement:

```text
memory X is current
```

is shorthand for something closer to:

```text
memory X is applicable to the relevant current-state interpretation
under the governing valid-time/supersession/currentness semantics
```

### Metabolic/stability evidence

**Metabolic/stability evidence** describes persistence and influence characteristics such as saturation, reinforcement, contradiction pressure, time since meaningful use, decay weight, consolidation pressure, and retention/pruning candidacy.

It does not establish temporal validity.

Examples:

```text
old + highly reinforced historical fact
  -> may remain metabolically strong
  -> may remain historically correct
  -> may be inapplicable to a current-state query

new + weakly supported observation
  -> may be temporally current
  -> may be metabolically weak
  -> may still be the best evidence for current state
  -> is not automatically true merely because it is recent
```

### Query-conditioned applicability

**Query-conditioned applicability** is the final retrieval concept introduced by this ADR.

It answers:

> Given an already admitted candidate, the interpreted query, the candidate’s typed relevance evidence, temporal applicability, metabolic/stability evidence where relevant, route/provenance evidence, and the requested recall shape, how should this candidate participate in the returned context?

Applicability is a **decision over typed evidence**, not a new claim that all evidence has become one scalar quantity.

---

## Decision

### 1. Relevance and temporal applicability are distinct typed evidence dimensions

Agent Memory MUST NOT define relevance and temporal applicability as two competing meanings of one scalar score.

A runtime MAY produce scalar sub-scores for individual retrieval methods, but each scalar MUST retain an explicit score type and interpretation where it influences consequential ranking.

Examples:

```text
cosine similarity != lexical overlap
lexical overlap != logical identity
logical identity != temporal applicability
temporal applicability != metabolic strength
metabolic strength != authority
```

### 2. The final recall decision is query-conditioned

There is no canonical universal ranking order such as:

```text
relevance first, then recency
```

or:

```text
recency first, then relevance
```

or:

```text
0.7 * relevance + 0.3 * recency
```

Instead, the applicability policy MUST be conditioned on the interpreted query, including temporal intent and expected recall shape where they materially affect selection.

### 3. Temporal applicability is interval/relationship semantics, not a recency bonus

The system MUST distinguish time coordinates where the source supports them.

At minimum, a conforming implementation claiming temporal applicability MUST NOT silently treat `created_at`, `valid_at`, `event_time`, `transaction_time`, and `last_meaningful_use` as equivalent.

Raw age MAY be used as a weak heuristic in a profile that declares it, but raw age alone is not canonical currentness evidence.

### 4. Some evidence relationships are non-compensatory

A ranking policy MUST be able to express cases where one dimension cannot compensate for another.

Example:

```text
query: "Who is the current CEO?"

candidate A:
  semantic identity: exact
  valid_until: 2021

candidate B:
  semantic identity: strong
  valid_from: 2025
  valid_until: open
```

If the temporal basis is sufficiently established, candidate A MUST NOT regain current-state applicability merely because its semantic score is numerically higher.

This does not mean temporal applicability always acts as a hard filter. The rule is query-conditioned. An atemporal or historical query may legitimately prefer A.

### 5. Relevance and time may interact without being collapsed

This ADR rejects a false orthogonality claim.

Temporal relationships can themselves be semantically relevant.

Examples:

```text
What happened immediately after the migration?
What did we believe before decision D?
Which warning preceded the outage?
What changed between version A and version B?
```

In these cases, time is part of the query’s semantic relation. A policy MAY therefore use interaction features such as temporal proximity, interval overlap, sequence relation, or before/after relation.

The requirement is that those interaction features remain explainable as temporal-semantic evidence rather than disappearing into an unexplained universal score.

### 6. Authority/admission remains outside applicability ranking

Governed recall admission MUST remain a controlling stage before applicability ordering.

The canonical relationship is:

```text
candidate discovery
  -> governed admission
  -> applicability ranking/structure among admitted candidates
```

An inadmissible candidate MUST NOT become influential because it has excellent semantic or temporal fit.

A ranking policy MUST NOT assign authority, broaden scope, repair a tombstone, reverse a dispute refusal, establish consent, or convert an unauthorized crossing into an admitted memory.

### 7. Metabolism may inform influence but cannot define temporal truth

Metabolic evidence MAY influence ranking or context budgeting under a declared policy, especially for atemporal associative recall, long-term retention prioritization, consolidation-aware retrieval, or activation budgeting.

But:

```text
decay_weight != valid_time
reinforcement != currentness
saturation != truth
crystallization != permanent applicability
```

A memory can be old and highly stable, new and weakly supported, historically valid but currently superseded, or current but uncertain.

### 8. Independent later writes do not silently establish supersession

The currentness failure exposed by independent observations does not authorize a generic rule that a later value replaces an earlier one.

Potential contradiction/supersession detection MUST consider where applicable:

```text
proposition identity
entity identity
predicate/property identity
scope
cardinality semantics
valid interval
evidence of incompatibility
source/evidence quality
existing supersession/correction links
```

Examples that MUST NOT be automatically treated as contradiction merely because values differ:

```text
"Kevin likes coffee"
"Kevin likes tea"

"Kevin works at Acme Labs"
"Kevin works at Globex"

"Kevin lives in Maryland"
"Kevin lives in Stevensville"
```

Conflict detection may produce evidence, a conflict candidate, or a governed supersession/correction proposal. It MUST NOT silently mutate canonical history solely because the later write appears newer or different.

### 9. Recall need not always produce one winner

The applicability policy MUST support the possibility that the correct result is a structured set rather than one highest-ranked memory.

Expected recall shapes MAY include:

```text
current_state
historical_state
as_of_state
timeline
state_transition
conflict_set
comparison_set
supporting_evidence_set
prospective_commitments
```

Examples:

```text
"How did this architecture change?"
  -> timeline or state-transition result

"What changed about the deployment endpoint?"
  -> previous state + new state + transition evidence

"What are the competing explanations?"
  -> conflict/comparison set
```

A system that always collapses these cases to one winner may lose exactly the temporal or epistemic structure the user asked for.

### 10. Final ordering may be scalar, lexicographic, staged, constrained, probabilistic, or learned

This ADR deliberately does not prescribe one mathematical form.

A conforming policy MAY use:

- lexicographic ordering;
- staged filters plus ranking;
- Pareto-style or dominance rules;
- normalized score fusion;
- learned ranking;
- probabilistic selection among admissible candidates;
- deterministic rules for some query classes and learned rules for others;
- hybrid structured selection.

However, the policy MUST preserve:

```text
source feature identity
policy/version identity
query temporal-intent posture
admission boundary
reconstructable explanation at the declared evidence level
no hidden authority effect
```

If a scalar is emitted, it is an implementation convenience, not a claim that the underlying evidence is ontologically one quantity.

---

## Query interpretation contract

### Required principle

Ranking quality is bounded by query interpretation quality.

A runtime that cannot distinguish:

```text
"What is true now?"
```

from:

```text
"What was true then?"
```

cannot safely repair the problem by tuning a global recency weight.

### Minimal temporal-intent output

A first reference contract SHOULD expose at least:

```text
mode
reference_time
start_time / end_time where applicable
explicit_vs_inferred posture
confidence/posture where inferred
interpreter identity/version
evidence refs or parse evidence
```

### Explicit versus inferred temporal intent

Explicit query language SHOULD dominate inferred defaults when unambiguous.

Examples:

```text
"as of 2025-03-01"
"before the migration"
"currently"
"next week"
```

may be resolved deterministically when the required referenced event/time is known.

When language is ambiguous, the system MAY use a classifier, LLM, heuristic, task context, or host-supplied intent. Any probabilistic inference MUST remain labeled as inference.

### Uncertain intent

A low-confidence temporal-intent estimate SHOULD NOT automatically trigger strong temporal exclusion unless the profile explicitly declares that behavior and the consequence is acceptable.

Possible strategies include:

- use atemporal ordering;
- return both likely-current and historically relevant evidence;
- surface an ambiguity marker;
- preserve multiple candidate interpretations;
- ask for clarification at an application layer when consequence warrants it.

This ADR does not require interactive clarification from the memory subsystem itself.

---

## Relevance evidence model

### Relevance is relational, not intrinsic

A memory does not possess one context-free relevance value.

Relevance is a relationship between a memory and a query/task/context.

The same memory may be highly relevant to one question and useless to another.

### Relevance dimensions

Implementations SHOULD preserve route-native evidence where available, such as:

```text
lexical overlap / lexical retrieval score
vector similarity
exact logical identity
entity identity
shared provenance/evidence relation
graph/path relationship
causal relationship
task or procedure match
policy relation
predictive/counterfactual relation
human pin / explicit requested memory
```

### Score comparability

Scores from different routes MUST NOT be assumed comparable merely because they are floating-point values.

If an implementation combines them numerically, the policy MUST declare the normalization/calibration assumption and version.

For example:

```text
cosine 0.82
BM25 13.4
relational confidence 0.7
route count 3
```

cannot be meaningfully summed without an explicit transformation and evidence that the transformation supports the intended ranking behavior.

### Route count

Being retrieved by multiple routes can be useful evidence of robust discoverability, but route count MUST NOT become truth, authority, or an automatic dominance rule.

Highly correlated routes may simply repeat the same underlying evidence.

---

## Temporal applicability model

### Multiple clocks

The model MUST preserve distinctions among clocks when they materially affect correctness.

#### Event time

When the underlying event occurred.

#### Observation time

When the system observed the event.

#### Valid time

When the proposition applies.

#### Transaction time

When Agent Memory committed the record.

#### Supersession/correction time

When current-state interpretation changed.

#### Expiry/review time

When evidence or policy requires re-evaluation.

#### Last meaningful use

A metabolism-specific clock that MAY affect decay/influence but MUST NOT be silently substituted for proposition validity.

### Intervals, not just points

Temporal applicability often requires interval reasoning.

Example:

```text
A: "office closes at 5 PM"
   valid_from = 2025-01-01
   valid_until = open

B: "office closes at 3 PM today due to weather"
   valid_from = 2026-09-25 00:00
   valid_until = 2026-09-25 23:59
```

For a query on 2026-09-25, B may be applicable.
For a query on 2026-09-26, A may again be applicable.

A “newest wins” rule cannot represent this.

### Unknown temporal evidence

Absence of valid-time metadata is not proof of timelessness.

A policy MUST define the fallback posture for unknown temporal basis.

Possible postures include:

- retain candidate but lower temporal confidence;
- avoid strong temporal preference;
- require corroboration for consequential current-state use;
- use transaction time only as declared weak fallback;
- expose `unknown_temporal_basis` in explanation.

### Overlapping validity

Two memories can both be temporally applicable.

This can occur because:

- the property is multi-valued;
- scopes differ;
- sources disagree;
- one is a more specific refinement of another;
- both are active policies in different domains;
- uncertainty prevents declaring one canonical.

Temporal overlap alone does not establish contradiction.

---

## Applicability policy semantics

### Stage model

A recommended conceptual profile is:

```text
1. interpret query
2. discover candidates
3. govern admission
4. determine requested recall shape
5. evaluate temporal applicability
6. evaluate multidimensional relevance
7. evaluate optional metabolic/stability influence
8. evaluate interaction features
9. construct ordered or structured recall set
10. emit explanation/evidence
```

This ordering is conceptual, not a required implementation call sequence. Efficient systems may compute features earlier or lazily so long as forbidden candidates do not gain downstream influence and the resulting semantics are equivalent.

### Non-compensation policy

Some query classes require constraints rather than bonuses.

Examples:

#### Current-state lookup

When explicit valid-time evidence establishes that a candidate is not applicable now, semantic similarity MUST NOT rescue it as the canonical current answer.

It may still appear as historical/supporting context if the recall shape permits that.

#### As-of lookup

Evidence valid outside the requested interval MUST NOT become the canonical as-of state merely because it is newer.

#### Atemporal research recall

Recency SHOULD NOT automatically dominate semantically stronger older material.

#### Prospective recall

Past-valid evidence SHOULD NOT displace an explicit future commitment merely because the past evidence is more reinforced.

### Dominance versus exclusion

The policy SHOULD distinguish:

```text
not canonical for requested state
```

from:

```text
not useful at all
```

Historical evidence can remain highly useful even when it is not the canonical current answer.

This distinction supports structured recall and explanation.

---

## Relationship to conflict, correction, and supersession

### Ranking is not state mutation

Applicability ranking may reveal that one memory appears to be the current-state answer. That observation does not by itself mutate the lifecycle of another memory.

### Conflict candidate

A system MAY detect a potential conflict such as:

```text
same entity
same apparently single-valued property
incompatible values
overlapping validity
```

and produce a conflict/supersession proposal.

That proposal is evidence for the existing conflict/lifecycle/PAMA path.

### Cardinality semantics

Conflict detection SHOULD distinguish properties that are naturally:

```text
single-valued
multi-valued
set-valued
hierarchical / refinement-compatible
scope-dependent
unknown cardinality
```

A later observation with a different value does not prove replacement unless the proposition semantics support replacement.

### Correction versus supersession

This ADR preserves the existing distinction:

```text
supersession:
  earlier value may have been valid, later state now applies

correction:
  earlier value was wrong or incomplete for its claimed scope/time
```

Ranking MUST NOT erase that difference.

---

## Relationship to memory metabolism

### Why metabolism is separate

Memory half-life and reinforcement answer a different family of questions:

```text
How strongly should this retained memory persist or influence retrieval?
How established or repeatedly useful is it?
Has contradiction pressure reheated or weakened it?
Should it be consolidated, archived, reviewed, or pruned?
```

Temporal applicability answers:

```text
Does this proposition apply to the time the query is asking about?
```

### Permitted interaction

Metabolic evidence MAY be used as a ranking feature when the query and profile justify it.

For example, among several atemporal memories with similar semantic fit, independently corroborated and successfully reused memory may deserve stronger influence than access-spam junk.

### Forbidden inference

Metabolic evidence MUST NOT silently establish:

- valid-from or valid-until time;
- correction;
- supersession;
- truth;
- admission authority;
- permission to delete;
- permission to certify.

---

## Relationship to governance and authority

Authority is not a ranking coordinate.

The system MUST preserve:

```text
candidate usefulness
        !=
permission to influence cognition
```

The final applicability system operates on the admitted set.

If an implementation computes ranking features before admission for efficiency, those computations MUST NOT create visible influence, leakage, or authorization side effects from candidates that are later refused.

Examples of non-ranking governance include:

- tenant isolation;
- project/task scope;
- consent/delegation;
- sensitivity and destination policy;
- tombstone/deletion state;
- governed currentness refusal when already established canonically;
- dispute/certification posture;
- crossing authority.

No weighted score may “outvote” these rules.

---

## Structured recall shapes

### Rationale

Single ranked lists are insufficient for some temporal and epistemic questions.

### Minimum conceptual shapes

#### `current_state`

Return the best currently applicable candidate(s), optionally with historical/supporting context.

#### `as_of_state`

Return the candidate(s) applicable at the requested instant/interval.

#### `historical_state`

Return historically relevant evidence without implying present applicability.

#### `timeline`

Return ordered states/events across time.

#### `state_transition`

Return previous state, transition evidence, and new state where available.

#### `conflict_set`

Return competing admitted claims with preserved dispute/currentness/evidence posture.

#### `comparison_set`

Return multiple candidates intentionally for comparison rather than forcing a winner.

#### `prospective_commitments`

Return future-valid commitments, intentions, plans, or predictions with appropriate uncertainty/status.

### Ranking within structured shapes

Each shape may have its own ordering policy.

For example, a timeline naturally orders by the relevant event/valid-time relation after semantic filtering, while a current-state answer may prioritize current validity and then discriminate among applicable candidates using relevance/evidence quality.

---

## Determinism, probability, and inspectability

### Deterministic core requirement

This ADR does not require every relevance estimate or temporal-intent interpretation to be deterministic.

It does require the architecture to distinguish probabilistic estimates from deterministic/governed consequences.

A conforming reference profile SHOULD be able to reproduce a ranking decision from:

```text
query interpretation evidence
admitted candidate set
candidate feature/evidence records
ranking/applicability policy id + version
configuration/calibration identity
reference clock / temporal target
```

where the profile claims deterministic replay.

### Learned rankers

A learned ranker MAY implement applicability ordering provided:

- it receives only candidates permitted by the admission boundary or otherwise cannot leak refused candidate influence;
- the input feature classes remain identifiable;
- temporal intent and temporal evidence remain distinguishable from generic semantic similarity;
- model/version/calibration identity is recorded;
- the model cannot mutate lifecycle or authority merely through ranking;
- benchmark success does not automatically promote the model to doctrine.

### Explanation

For consequential recall, the system SHOULD be able to explain at least:

1. why the memory was a candidate;
2. why it was admitted;
3. what temporal intent was used;
4. which temporal evidence made it applicable, inapplicable, or uncertain;
5. which relevance relationships materially affected ordering;
6. whether metabolic/stability evidence affected ordering;
7. which applicability-policy version produced the final structure/order;
8. why a semantically stronger candidate may have been demoted for temporal incompatibility;
9. why a newer candidate may have been demoted because the query was historical/atemporal;
10. whether the result is canonical current state, historical context, disputed evidence, or another recall shape.

---

## Reference implementation direction

This section is guidance for the first Agent Memory implementation profile. It is not a requirement that all implementations use the same classes or field names.

### Query intent

A useful first type may resemble:

```text
QueryInterpretation
  semantic_intent / query text
  temporal_intent
  reference_time
  temporal_interval
  temporal_intent_posture
  temporal_intent_evidence
  expected_recall_shape
  interpreter_ref
  interpreter_version
```

### Candidate evidence

A useful admitted-candidate evidence record may resemble:

```text
ApplicabilityEvidence
  memory_ref
  admission_ref
  route_evidence[]
  relevance_features{}
  temporal_evidence{}
  temporal_applicability
  metabolic_evidence{}
  interaction_features{}
  policy_ref
  policy_version
  authority_effect = none
```

### Policy output

A useful policy output may resemble:

```text
ApplicabilityDecision
  memory_ref(s)
  recall_shape
  rank / group / role
  canonical_current_answer = true|false|not_claimed
  historical_context = true|false
  applicability_reasons[]
  uncertainty/posture
  policy_ref
  policy_version
  authority_effect = none
```

These names are illustrative. The important requirement is semantic separation and reconstructability.

---

## Migration from the current ranking policy

### Current state at proposal time

The benchmark-remediation branch introduced an explicit `PostAdmissionRankingPolicy` that uses temporal evidence to break ties among candidates otherwise equal on relevance stages.

That was a correct bounded fix for the accidental anti-recency stable-ID behavior and produced measurable currentness improvement.

It also demonstrated the limitation of universal temporal fallback because newer non-gold evidence can displace older relevant evidence on non-currentness questions.

### Migration principle

ADR-039 does not require reverting the tie-break immediately.

Instead, the next profile SHOULD evolve from:

```text
relevance stages
  -> universal temporal tie-break
  -> stable id
```

into:

```text
query interpretation
  -> relevance + temporal applicability evidence
  -> query-conditioned applicability policy
  -> stable deterministic fallback when the policy cannot discriminate
```

### Backward evidence compatibility

Benchmark artifacts produced under the prior ranking policy MUST remain interpretable by policy/version identity.

Do not overwrite frozen before-state evidence.

---

## Conformance and adversarial cases

Acceptance of this ADR requires executable evidence beyond prose because the decision was motivated by a benchmark-observed implementation failure.

The exact fixture format is implementation-defined, but the following cases are mandatory for the Agent Memory reference profile before acceptance.

### C1. Current state beats historical exact-match when validity is known

```text
old memory:
  exact semantic identity
  valid_until = T1

new memory:
  strong semantic identity
  valid_from = T2 > T1

query:
  explicit current-state
  reference time > T2
```

Expected:

- new memory is canonical current answer;
- old memory may remain historical context;
- old memory cannot regain canonical status merely through higher lexical/vector similarity.

### C2. Historical query prefers historically applicable evidence

Use the same memory pair.

Query:

```text
as_of between old.valid_from and old.valid_until
```

Expected:

- old memory is canonical as-of answer;
- newer memory does not win merely because it is newer.

### C3. Atemporal semantic query resists irrelevant recency

Two memories are similarly or equally scored by one retrieval route. The newer memory is semantically less useful under richer evidence.

Expected:

- no universal recency preference forces the newer memory first;
- policy explanation records atemporal/unspecified temporal posture.

### C4. Temporary exception interval

```text
A: ordinary rule, open-ended validity
B: temporary exception, one-day validity
```

Expected:

- B wins during its valid interval for a current query;
- A becomes current again after B expires without needing A to be reinserted as “newer.”

### C5. Multiple clocks disagree

A record is observed late but valid earlier; another is recorded earlier but valid later.

Expected:

- applicability uses declared valid/event semantics appropriate to the query;
- transaction time does not silently substitute for valid time.

### C6. Unknown temporal basis

Candidate has strong semantic evidence but no valid-time metadata.

Expected:

- policy follows declared unknown-time posture;
- absence of metadata is not treated as timeless truth;
- explanation exposes temporal uncertainty.

### C7. Metabolic strength cannot resurrect stale current state

Old memory is highly saturated/reinforced.
New memory is weakly reinforced but canonically valid now.

Expected:

- old memory does not become canonical current answer because of metabolic strength;
- metabolic evidence may affect supporting-context ordering only under declared policy.

### C8. Newness cannot establish truth

New observation conflicts with older certified evidence but has weak/uncertain source support and no canonical supersession.

Expected:

- recency alone does not certify or mutate state;
- current-state ranking posture reflects the available canonical/currentness evidence and uncertainty;
- conflict may be surfaced or proposed for governance.

### C9. Multi-valued property does not auto-supersede

```text
Kevin likes coffee
Kevin likes tea
```

Expected:

- both may remain applicable;
- later write does not silently supersede earlier write.

### C10. Hierarchical refinement does not auto-conflict

```text
Kevin lives in Maryland
Kevin lives in Stevensville
```

Expected:

- both may be simultaneously valid at different specificity levels;
- applicability/relevance can prefer one depending on query granularity.

### C11. Multi-employer case

```text
Kevin works at Acme Labs
Kevin works at Globex
```

Expected:

- property cardinality/scope prevents false contradiction;
- query such as “primary employer” requires additional semantics, not blind latest-write replacement.

### C12. Wrong-scope perfect match remains refused

A wrong-tenant candidate has perfect semantic and temporal fit.

Expected:

```text
admitted = false
rank influence = zero
```

### C13. Historical timeline returns several states

Query requests evolution/history.

Expected:

- result is a structured timeline or equivalent;
- system does not collapse the answer to newest state only.

### C14. State transition preserves both states

Query asks “what changed?”

Expected:

- previous and new states plus transition evidence are returned where available;
- current-state preference does not erase historical transition context.

### C15. Temporal relation is semantic evidence

Query asks “what happened immediately before X?”

Expected:

- temporal proximity/ordering participates directly in relevance/applicability;
- architecture does not force strict independence between semantic and temporal dimensions.

### C16. Low-confidence temporal intent

Ambiguous query produces uncertain temporal intent.

Expected:

- policy follows conservative ambiguity posture;
- low-confidence inference does not silently become a hard current-state exclusion.

### C17. Explicit as-of overrides inferred current default

Expected:

- explicit query time controls;
- inferred “current” default cannot override explicit evidence.

### C18. Prospective memory

Future-valid commitment exists alongside current/historical state.

Expected:

- prospective query returns future-valid commitment;
- current query does not present future commitment as current fact.

### C19. Deterministic replay

For a deterministic profile and fixed query interpretation/candidate evidence/policy version/reference clock, repeated execution produces identical structured ordering.

### C20. Policy-version evidence

Changing applicability policy version changes evidence identity/reporting even when the final order happens to remain the same.

### C21. No benchmark-specific branching

Runtime policy contains no dataset IDs, benchmark question-type names, or benchmark-specific lexical phrases.

### C22. Relevance improvement can beat a newer distractor on atemporal query

A newer distractor and older semantically exact memory are both admitted.

Expected:

- older memory may rank first under atemporal intent;
- system proves it is not simply using recency as universal fallback.

### C23. Temporally impossible semantic near-match cannot dominate current query

A semantically excellent but expired candidate competes with a weaker but valid current candidate.

Expected:

- valid candidate is canonical current answer where temporal evidence is sufficiently established.

### C24. Disputed current evidence remains disputed

Temporal applicability does not remove dispute semantics.

Expected:

- candidate can be temporally applicable and disputed simultaneously;
- result does not present dispute as canonical certainty.

### C25. Corrected record differs from superseded record

Expected:

- correction semantics and supersession semantics remain distinguishable in structured recall/history;
- applicability policy does not flatten both into “old.”

---

## Benchmark obligations

### Dimension separation

Benchmark reporting SHOULD keep at least the following dimensions separate where measured:

```text
relevance / retrieval quality
temporal applicability / currentness
reasoning or QA outcome
governance / authority containment
efficiency
reproducibility
```

No universal “memory quality” score is introduced by this ADR.

### Before/after replay

For benchmark-discovered ranking defects, the relevant frozen workload SHOULD be replayed before closure where practical.

The evidence must record:

- exact runtime revision;
- exact dataset revision/digest;
- applicability/ranking policy id/version;
- query-intent interpreter id/version;
- configuration;
- improvements;
- regressions;
- unchanged dimensions;
- known unmeasured dimensions.

### Cross-benchmark promotion

A ranking policy SHOULD NOT be promoted merely because it improves one benchmark aggregate.

Stronger evidence includes:

- targeted adversarial fixtures;
- improvement on the defect-reproducing benchmark;
- no unacceptable regression on orthogonal query classes;
- corroboration across more than one benchmark family where practical;
- preservation of governance and temporal semantics.

### Benchmark ontology is not product ontology

Terms such as `knowledge-update`, `temporal-reasoning`, or benchmark-specific question classes may inform evaluation analysis. They MUST NOT automatically become runtime ontology or doctrine.

---

## Security and governance considerations

### Scope leakage through pre-ranking

Performance optimizations that compute relevance before admission must not expose forbidden candidate content, counts, timing side channels beyond the declared threat model, or rank influence.

### Temporal poisoning

An attacker may attempt to inject recent false observations so a naive recency model displaces established evidence.

This ADR reduces that risk by refusing `newer == true` semantics and preserving source/evidence/governance posture separately.

### Reinforcement poisoning

Repeated accesses or synthetic corroboration may attempt to increase metabolic influence.

Metabolism remains bounded and cannot establish valid-time truth or authority.

### Intent-classification poisoning

If a learned component interprets temporal intent, adversarial wording may shift `atemporal` to `current` or vice versa.

Consequential profiles should retain interpreter identity/version and uncertainty and test adversarial temporal-language cases.

### Authority laundering through applicability

A candidate with perfect applicability still cannot cross scope, tenancy, consent, sensitivity, deletion, or other governance barriers.

---

## Alternatives considered

### Alternative A: Relevance always dominates currentness

Rejected.

This reproduces the benchmark-observed stale-current-state failure. A historical exact lexical match can incorrectly outrank the currently applicable fact.

### Alternative B: Currentness/recency always dominates relevance

Rejected.

The first remediation replay already demonstrated regressions when newer non-gold evidence displaced older relevant evidence on non-currentness questions.

### Alternative C: Universal weighted sum

Example:

```text
rank = a * semantic + b * recency + c * stability
```

Rejected as canonical doctrine.

A profile may experiment with a weighted model, but no universal weights can safely represent query classes where temporal incompatibility is non-compensatory or irrelevant.

### Alternative D: Treat temporal applicability as admission

Rejected as a universal rule.

Some temporally non-current memories are valid historical evidence and should remain admissible for historical, comparison, explanation, or transition queries.

Canonical lifecycle currentness refusals may still be admission concerns under existing doctrine. This ADR distinguishes that governed state from query-specific applicability ordering.

### Alternative E: Always infer supersession from latest conflicting write

Rejected.

Different values may be compatible, multi-valued, scoped, hierarchical, disputed, or wrong. Supersession is a governed lifecycle conclusion, not a timestamp heuristic.

### Alternative F: Let metabolism solve currentness

Rejected.

Half-life, saturation, and reinforcement govern persistence/influence, not proposition valid-time semantics.

### Alternative G: Return only one best memory

Rejected as universal doctrine.

Timeline, transition, conflict, and comparison queries require structured multi-memory recall.

### Alternative H: Leave behavior implementation-specific with no doctrine

Rejected.

The benchmark-gauntlet exposed that seemingly harmless tie-break behavior can become a product-wide temporal policy. Without doctrine, accidental implementation detail becomes architecture by inertia.

---

## Consequences

### Positive

- prevents relevance/currentness from becoming a false zero-sum contest;
- explains why recency improves current-state queries while harming some atemporal queries;
- makes temporal intent an explicit part of retrieval semantics;
- preserves historical truth while improving current-state behavior;
- provides a principled home for UOR/EvolveAI-derived metabolic concepts without confusing them with valid-time currentness;
- enables richer timeline/transition/conflict recall;
- improves explainability because ranking evidence retains typed meaning;
- reduces risk that benchmark-specific heuristics become product doctrine;
- provides a stable architectural target for #538 and future learned ranking work.

### Costs

- query interpretation becomes a first-class subsystem rather than an implicit assumption;
- ranking evidence becomes richer and more expensive to compute/store;
- temporal metadata quality becomes more important;
- unknown/missing valid-time evidence must be handled explicitly;
- benchmarking becomes more dimensional and less leaderboard-friendly;
- some queries may legitimately return multiple memories rather than one easy winner;
- future APIs may need to expose recall-shape and explanation metadata.

### Compatibility

This ADR is designed to be compatible with the existing governed-recall and temporal-causality architecture.

It narrows and clarifies ranking semantics; it does not weaken PAMA, tenancy, deletion, dispute, source-rights, or other governance rules.

The explicit temporal tie-break introduced during #538 remains valid evidence and may remain as a fallback in a compatible profile where temporal intent warrants it.

---

## Known limitations and unresolved questions

This ADR intentionally leaves several implementation questions open for evidence rather than pretending prose has solved them.

### Temporal-intent interpreter

Open questions:

- deterministic parser versus classifier versus LLM versus hybrid;
- default behavior for unspecified intent;
- confidence calibration;
- interaction with host/application context;
- multilingual temporal language.

### Property/cardinality semantics

Conflict detection needs knowledge of whether a property is single-valued, multi-valued, hierarchical, or scope-dependent.

The canonical representation for those semantics is not decided here.

### Score calibration

The policy for comparing route-native relevance evidence remains an empirical design area. This ADR requires explicit semantics, not one normalization method.

### Missing temporal metadata

Different deployments may have radically different valid-time coverage. The best fallback for incomplete temporal evidence remains profile-specific and must be benchmarked.

### Learned applicability

A learned ranker may outperform handcrafted policy but introduces explainability, drift, reproducibility, and poisoning concerns. Acceptance of ADR-039 does not qualify any learned model.

### Efficiency

Richer applicability evaluation may increase per-query cost. #522 and future performance work remain responsible for keeping candidate generation and ranking operationally viable.

### Distributed clocks

Clock skew, distributed observation, delayed ingestion, and external witness time complicate temporal semantics. ADR-031 provides deterministic commitment boundaries but does not solve every distributed temporal-ordering problem.

---

## Non-goals

ADR-039 does not:

- define truth as newest evidence;
- define truth as highest relevance;
- define one universal ranking score;
- make recency an authority signal;
- make metabolism a currentness engine;
- silently auto-supersede independent writes;
- replace correction/supersession doctrine;
- replace governed recall admission;
- define a universal ontology for every predicate/property;
- require an LLM for query interpretation;
- require learned ranking;
- require deterministic candidate ordering in every future profile;
- require every query to expose temporal language explicitly;
- collapse benchmark dimensions into one score;
- claim benchmark superiority;
- solve distributed consensus or clock synchronization;
- prescribe UI behavior for ambiguity resolution.

---

## Acceptance gate

ADR-039 SHOULD remain Proposed until the reference repository demonstrates all of the following.

### Doctrine completeness

- [ ] `docs/18-temporal-causality-layer.md` is aligned with query-conditioned temporal applicability rather than raw recency.
- [ ] `docs/26-governed-recall-planner.md` is aligned with typed relevance + temporal applicability + structured recall.
- [ ] metabolism docs explicitly preserve `metabolic strength != temporal validity`.
- [ ] terminology is added to the canonical glossary.
- [ ] no canonical document still implies a universal relevance-versus-recency contest.

### Reference implementation evidence

- [ ] query temporal intent is explicitly represented in the reference recall path;
- [ ] applicability/ranking policy identity and version are inspectable;
- [ ] explicit current/as-of/historical/atemporal/prospective semantics are represented or the first bounded subset is clearly declared;
- [ ] temporal applicability distinguishes valid/event/transaction semantics where required;
- [ ] authority remains `none` for ranking/applicability evidence;
- [ ] unknown temporal basis is represented rather than silently treated as current/timeless;
- [ ] structured recall demonstrates at least one non-single-winner shape such as timeline, transition, or conflict set;
- [ ] no later-write auto-supersession shortcut is introduced.

### Adversarial conformance evidence

- [ ] C1-C25 above are covered directly or through equivalent documented fixtures;
- [ ] wrong-scope perfect matches remain refused;
- [ ] highly reinforced stale evidence cannot become canonical current state solely through metabolism;
- [ ] recent false/uncertain evidence cannot become truth solely through recency;
- [ ] atemporal queries resist irrelevant temporal preference;
- [ ] historical/as-of queries resist newest-wins behavior;
- [ ] explicit temporal intent overrides inferred defaults;
- [ ] ambiguity posture is tested.

### Benchmark evidence

- [ ] AgentMemBench currentness/conflict workload is replayed on the applicability candidate;
- [ ] frozen LongMemEval_S is replayed on the applicability candidate;
- [ ] before/after reports preserve relevance and temporal/currentness dimensions separately;
- [ ] improvements and regressions are both reported;
- [ ] no benchmark-specific runtime branch exists;
- [ ] the candidate does not merely improve latest-first ordering by causing unacceptable non-currentness retrieval regressions;
- [ ] at least one orthogonal benchmark or adversarial suite demonstrates behavior outside the benchmark family that motivated the decision.

### Architecture review

- [ ] #544 records an adversarial review after implementation evidence exists;
- [ ] unresolved contradictions with ADR-011/013/020/023/030/031/035 are either resolved or explicitly documented;
- [ ] maintainers perform an explicit Proposed -> Accepted ruling rather than allowing implementation merge to imply acceptance.

---

## Falsification conditions

This ADR should be narrowed, superseded, or rejected if evidence demonstrates that one or more core claims are materially wrong.

Examples include:

1. a simpler universal scalar policy consistently matches or exceeds query-conditioned applicability across current, historical, atemporal, and prospective workloads without semantic/governance regressions;
2. explicit temporal-intent modeling adds operational complexity without measurable retrieval/currentness benefit across representative workloads;
3. structured recall proves unnecessary because downstream generation reliably reconstructs transitions/conflicts from ordinary ranked lists without evidence loss;
4. typed feature preservation proves too expensive for the intended product boundary and no bounded evidence profile can retain reconstructability;
5. the proposed separation creates contradictions with stronger accepted authority/currentness doctrine that cannot be reconciled.

The burden is empirical and architectural, not stylistic.

---

## Decision rationale in one sentence

**Agent Memory should decide recall applicability by relating a query to admitted memory across typed semantic and temporal evidence, not by making relevance and recency compete as if they were interchangeable quantities.**
