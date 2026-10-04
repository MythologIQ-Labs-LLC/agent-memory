# Jev-Mem implementation harvest — source characterization

Issue: #644  
Status: source characterization / preimplementation harvest evidence  
Upstream: `libingzheren/Jev-Mem`  
Frozen upstream revision: `7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44`  
Upstream license: MIT  
Agent Memory posture: implementation ancestry; no required runtime dependency

## Purpose

This document records the first source-level characterization of Jev-Mem mechanisms that may be useful to Agent Memory.

The governing question is not whether Jev-Mem is generally good. It is:

> Which concrete mechanisms improve Agent Memory when placed behind Agent Memory's existing identity, provenance, lifecycle, recall-admission, PAMA, currentness, and evidence boundaries?

A mechanism is not accepted merely because it appears in Jev-Mem or because Jev-Mem reports strong benchmark results. Every harvested mechanism must survive Agent Memory's own falsification and benchmark process.

## Rights boundary

Jev-Mem's repository `LICENSE` is MIT and permits use, modification, merger, publication, distribution, sublicensing, and sale subject to preserving the copyright and permission notice.

Its `NOTICE` states that Jev-Mem is derived from MAGMA and that the upstream MIT license/original notice are preserved. It also states that Jev and the TypeSafe SDK are external software/services with their own terms and that LoCoMo/LongMemEval datasets are not redistributed.

Therefore:

```text
Jev-Mem MIT source
    -> eligible for direct adaptation with required notice preservation

Jev / TypeSafe / Laya / model weights / datasets
    -> separate rights and dependency review

MIT permission
    !=
Agent Memory architectural authority
```

The default harvest strategy is native/provider-neutral implementation. Direct code reuse remains allowed when it is the superior engineering choice and its attribution/notice obligations are preserved.

## Source-level mechanism map

| ID | Jev-Mem mechanism | Source | Agent Memory disposition | Initial priority |
|---|---|---|---|---|
| JH-01 | overlapping memory-type scores | `memory/jev_mem_policies.py`, `memory/jev_questions.py` | harvest estimator contract; do not import retention authority | medium |
| JH-02 | bounded write-time relation candidate search | `memory/jev_mem_policies.py::find_candidates` | benchmark against identity-first/materialized native path | medium |
| JH-03 | typed semantic/causal/entity relation questions | `memory/jev_questions.py::relation_questions` | harvest estimator decomposition where native graph evidence benefits | medium |
| JH-04 | query-conditioned route-needs vector | `memory/jev_questions.py::routing_questions` | high-value harvest; generalize beyond four graph views | high |
| JH-05 | bounded graph-budget allocator | `memory/jev_mem_policies.py::allocate_graph_budgets` | native reimplementation candidate; expand to heterogeneous routes | high |
| JH-06 | retrieval call/deadline budget | `memory/jev_client.py::CallBudget` | harvest budget ownership model | high |
| JH-07 | evidence-sufficiency adaptive stopping | `memory/jev_questions.py::stopping_questions`, `memory/jev_mem_retrieval.py` | high-value harvest; pair with consumer budget | very high |
| JH-08 | traversal-value decomposition | `memory/jev_questions.py::traversal_questions` | harvest typed factors; reject mandatory weighted scalar | high |
| JH-09 | beam/depth/node/edge bounded traversal | `memory/jev_mem_retrieval.py` | harvest bounded-search posture | high |
| JH-10 | non-destructive consolidation vocabulary | `memory/jev_questions.py::consolidation_questions`, `memory/memory_builder.py::consolidate` | map into native metabolism/proposal lifecycle | very high |
| JH-11 | backend-neutral controller shape (Jev/Laya) | `memory/jev_client.py`, `memory/laya_backend.py` | harvest provider-neutral interface, not dependency | high |
| JH-12 | typed probability vs categorical outputs | `memory/jev_client.py::ProbabilityResult` | harvest validation/typing discipline | high |
| JH-13 | decision cache keyed by full operation/state/question/backend | `memory/jev_client.py` | investigate for bounded estimator cache | medium |
| JH-14 | audit telemetry for routing/budgets/stopping | `memory/jev_mem_retrieval.py`, `DecisionLog` | harvest and generalize | very high |
| JH-15 | read/write controller ablations | CLI/benchmark paths | copy evaluation discipline, not benchmark shortcuts | high |
| JH-16 | final selected-evidence handoff to System Two | retrieval + answer formatter | extend into consumer-aware memory package contract | very high |

## JH-01 — overlapping memory types

Jev-Mem evaluates `episodic`, `semantic`, `procedural`, and `preference` as independent probabilities. A memory may therefore participate in more than one cognitive role.

This aligns with Agent Memory's existing doctrine that one logical experience may participate in multiple specialized representations.

### Harvest

Create a provider-neutral typed classification result that can supply evidence to the Cognitive Mesh and specialized-memory projection logic.

### Do not import

Jev-Mem combines admission factors into a retention score. Agent Memory must not allow an estimator score to become silent retention/deletion/lifecycle authority.

```text
classification evidence -> proposal / projection eligibility
classification evidence != permission
```

## JH-02 — bounded write-time candidate discovery

`find_candidates` combines vector similarity, shared entities, keyword overlap, and temporal proximity to bound the set of existing observations considered for relationship judgments.

Agent Memory already has stronger identity-first materialization behavior in some proposition paths, so this is not an automatic replacement.

### Hypothesis

A heterogeneous candidate prefilter may improve relation discovery for graph-oriented representations where exact proposition identity is absent or intentionally broader.

### Required experiment

Compare:

1. identity-first only;
2. vector-only;
3. entity/keyword/time heuristic;
4. bounded hybrid;

against relation recall, false relation pressure, wall time, and candidate materialization cost.

## JH-03 — typed relation judgments

Jev-Mem separates:

- semantic relationship;
- forward causal relationship;
- reverse causal relationship;
- inferred shared entity identity.

It handles deterministic temporal sequence/proximity outside the learned controller.

That separation is attractive. Agent Memory should preserve deterministic/native evidence where available and use controller estimates only for relations that genuinely require estimation.

## JH-04 — query-conditioned route needs

Jev-Mem asks independent questions for semantic, temporal, causal and entity retrieval need, plus multi-hop need and recency importance.

The useful mechanism is not the exact six-field ontology. It is the idea that route activation and route budget are **query-conditioned typed evidence** rather than a fixed always-search-everything policy.

Agent Memory should generalize this to eligible representation families such as:

```text
exact identity
lexical
vector
entity graph
temporal graph
causal graph
procedural memory
episodic history
semantic/current state
file/document evidence
other qualified projection routes
```

Currentness must remain separate from recency.

## JH-05 — bounded route-budget allocation

Jev-Mem uses an explicit total graph budget, activation threshold, minimum per-active-graph budget, proportional allocation, and largest-remainder rounding. Retrieval additionally bounds depth, beam width, nodes, edges, decision calls, and latency.

This is excellent ancestry for Agent Memory because it turns `search more` into an inspectable resource decision.

The exact allocator is simple enough to reimplement natively rather than copy, unless exact upstream parity is useful for an ablation.

Agent Memory should evolve the abstraction from `graph budget` to `route/representation budget`.

## JH-06 — one outer controller budget

Jev-Mem's `CallBudget` owns maximum decision calls and a hard deadline. Nested SDK retries are disabled so hidden provider retry behavior cannot silently violate the retrieval budget.

This should be harvested.

Desired Agent Memory contract:

```text
controller_budget
    maximum_decisions
    deadline
    decisions_used
    cache_hits
    fallback/refusal events
```

Provider-specific retry behavior must be subordinate to that outer budget.

## JH-07 — evidence sufficiency and adaptive stopping

This is one of the highest-value mechanisms.

Jev-Mem separately evaluates:

```text
evidence_sufficient
continue_useful
missing_evidence
contradiction
```

The retrieval controller then distinguishes several terminal conditions:

```text
evidence_sufficient
further_retrieval_unhelpful
max_latency
max_controller_calls
max_nodes
max_depth
graph_budget_exhausted
max_edges
frontier_exhausted
no_evidence
```

This is significantly better than treating every `top_k` result as equally complete.

### Agent Memory extension

Sufficiency should eventually depend on three things:

```text
task/query requirements
+ available governed evidence
+ consumer effective context/capability budget
```

A stop caused by evidence sufficiency must never be conflated with a stop caused by resource exhaustion.

## JH-08 — traversal-value decomposition

Jev-Mem's expansion scoring uses separately estimated components for:

- vector similarity;
- answer relevance;
- relation usefulness;
- new information;
- corroboration/support.

This decomposition is more interesting than its final weighted average.

Agent Memory should harvest the factors but preserve typed evidence where possible. In particular, the Jev-Mem retrieval path adds a recency influence into the traversal score. Agent Memory must not import that as currentness or authority.

Potential Agent Memory ordering evidence:

```text
route-native relevance
information gain / novelty
relation usefulness
corroboration
query/task requirement coverage
```

Whether these become lexicographic stages, constrained edges, or another explicit policy must be benchmarked.

## JH-09 — bounded traversal

Jev-Mem's retrieval loop is operationally disciplined:

- bounded anchors;
- bounded node set;
- bounded edges examined;
- bounded graph budgets;
- bounded depth;
- bounded beam width;
- bounded controller calls;
- bounded latency;
- explicit stopping reason.

Agent Memory should preserve this spirit for every adaptive/heterogeneous retrieval implementation.

Adaptive must not mean unbounded.

## JH-10 — consolidation vocabulary

Jev-Mem evaluates each candidate pair for:

```text
redundant
contradiction
obsolete
link
```

and separately chooses one representation posture:

```text
keep_separate
merge
promote
uncertain
```

It preserves raw evidence and performs summary creation only after a merge/promotion decision.

This aligns strongly with Agent Memory's metabolism doctrine and #227.

### Strong harvest candidates

- separate relationship/evidence classification from representation decision;
- preserve `uncertain` as a first-class safe result;
- preserve raw observations after consolidation;
- make merged/promoted representations derived and provenance-linked;
- benchmark information loss before allowing promotion/consolidation to become routine.

### Agent Memory must remain stricter

`obsolete` is estimator evidence. It is not automatic supersession authority.

## JH-11 / JH-12 — provider-neutral typed controller interface

Jev-Mem's controller layer supports Jev and local Laya through the same decision pipeline. Its `ProbabilityResult` keeps binary-proposition probabilities distinct from categorical `Choice` outputs. Choice results are validated for exact option coverage, finite normalized probabilities, and selected-choice consistency.

This should inform an Agent Memory estimator contract.

Desired property:

```text
same typed estimator request
    -> deterministic backend
    -> local model backend
    -> hosted model backend
    -> future learned controller
```

with backend identity, model identity, usage, cache state and failure state always inspectable.

No backend owns Agent Memory consequence authority.

## JH-13 — deterministic decision caching

Jev-Mem hashes operation + backend/model + state + typed questions and caches the complete validated result.

This deserves qualification for Agent Memory, especially for repeated planning/sufficiency decisions.

Required concerns:

- cache identity must include all semantically relevant policy/controller versions;
- cached estimator evidence cannot outlive a policy/model/config boundary silently;
- caching must never turn stale estimator output into authority;
- privacy/scope-sensitive state must not leak through shared caches.

## JH-14 — decision observability

Jev-Mem exposes a strong retrieval trace:

```text
route/graph needs
allocated budgets
budget used
nodes visited
edges examined
controller calls
controller cache hits
retrieval depth
depth limit
latency
stopping decision
stopping scores
fallback events
top-k returned
```

Agent Memory should generalize this to heterogeneous memory routes and consumer delivery.

Future Agent Memory trace should also include:

```text
consumer profile / capability reference
nominal context budget
effective memory-package budget
package representation
bytes/tokens selected
bytes/tokens omitted
continuation handles
compression / projection provenance
```

## JH-15 — ablation discipline

Jev-Mem supports independent write-control and read-control ablations. This is valuable because it allows the contribution of controller behavior to be isolated.

Every Agent Memory harvest slice should have a baseline-off profile.

Example:

```text
adaptive_routing = off/on
adaptive_budgeting = off/on
adaptive_stopping = off/on
consumer_projection = off/on
consolidation_controller = off/on
```

No mechanism should be accepted merely because the combined system score improved.

## JH-16 — System-Two handoff and consumer-aware extension

Jev-Mem selects a bounded evidence set and formats it for the answer model. Its current implementation is primarily query/category aware, not deeply consumer-capability aware.

Agent Memory should treat Jev-Mem as ancestry and extend the concept.

```text
canonical retained evidence
    -> candidate generation
    -> governed admission
    -> adaptive route planning
    -> evidence sufficiency
    -> consumer-aware projection
    -> memory package
    -> agent
    -> optional bounded continuation / expansion
```

Consumer constraints may affect retrieval budget and representation shape, but never truth, authority, canonical retention, or deletion.

## Direct-code-adaptation candidates

Direct copying is **not** assumed to be best merely because MIT permits it.

### Likely native reimplementation

- `CallBudget` concept: tiny and architecture-specific enough to implement natively;
- largest-remainder route budget allocator: simple algorithm, reimplement with Agent Memory route vocabulary;
- typed routing/stopping result schemas: define in Agent Memory's own contracts;
- audit record shape: implement against Agent Memory evidence conventions.

### Worth deeper direct-code review

- Jev-Mem's strict controller response validation and cache-key construction;
- bounded retrieval-loop control flow and stop-reason enumeration;
- selected consolidation negative controls / tests;
- backend-neutral estimator adapter tests;
- budget/deadline/retry tests.

If any substantial source is copied/adapted, add the required MIT attribution/notice before merge.

## Explicit rejection / caution list

### Do not import Jev-Mem admission authority

Jev-Mem can reject an observation based on a weighted admission score. Agent Memory's lifecycle/retention semantics are independently governed. The score may be useful evidence, never consequence authority.

### Do not import recency as currentness

Jev-Mem's traversal score can incorporate recency importance. Agent Memory has already established stronger relevance/currentness separation. Recency may be useful for search economics or query intent but cannot establish temporal applicability.

### Do not import benchmark answer heuristics as memory architecture

`answer_formatter.py` contains LoCoMo/category-oriented prompt and normalization logic. Some context-shaping lessons may be useful, but benchmark-specific QA prompts are not generic memory behavior.

### Do not import reference-aware best-of-N evaluation behavior

The Jev-Mem README itself warns that inherited best-of-N selection can bias accuracy. Agent Memory should retain its independent evaluator integrity posture.

### Do not import MAGMA fallback as governance fallback

Jev-Mem can fall back to MAGMA when the controller is unavailable. Agent Memory may fall back from an optional estimator to a separately qualified deterministic planner, but never from a failed authority/governance decision to an ungoverned path.

## First implementation targets

The first harvest implementation should **not** modify recall ranking or lifecycle consequences.

Recommended sequence:

```text
1. provider-neutral controller request/result contract
2. budget + deadline contract
3. route-needs / budget proposal in shadow mode
4. sufficiency / stopping proposal in shadow mode
5. retrieval trace + ablations
6. frozen benchmark evidence
7. only then consider runtime activation
```

In parallel:

```text
consumer capability profile
    +
memory-package budget contract
    +
progressive disclosure / continuation design
```

should be specified so adaptive stopping does not optimize only for a fixed top-k.

## Benchmark obligations

At minimum, harvest evaluation should measure separately:

### Retrieval / task quality

- recall@k;
- precision@k;
- MRR / first relevant rank;
- evidence coverage;
- contradiction coverage;
- multi-hop completion;
- downstream task/answer quality under a frozen answer model where applicable.

### Search economics

- candidate routes activated;
- nodes/edges inspected;
- traversal depth;
- controller decisions;
- controller cache hits;
- controller/model tokens;
- retrieval latency;
- total task latency.

### Consumer utilization

- memory-package tokens;
- omitted-but-expandable evidence;
- task accuracy by memory-package budget;
- task accuracy by consumer/model profile;
- performance of one-shot versus progressive disclosure.

### Governance

- wrong-scope disclosure count;
- authority laundering count;
- stale/superseded-as-current count;
- deleted/tombstoned influence count;
- estimator-caused mutation count;
- provenance loss count.

No combined scalar may hide failure in a governance dimension.

## Initial disposition

Jev-Mem should now be treated as **high-value, licensed implementation ancestry**.

The highest-yield mechanisms are:

1. evidence-sufficiency/adaptive stopping;
2. query-conditioned route and budget planning;
3. non-destructive consolidation decision vocabulary;
4. explicit retrieval budgets and bounded traversal;
5. typed provider-neutral decision outputs;
6. decision observability and ablation discipline;
7. consumer-aware delivery as an Agent Memory extension of Jev-Mem's focused System-Two handoff.

The main areas where Agent Memory should deliberately diverge are authority, currentness/recency semantics, retention consequences, benchmark-specific QA formatting, and any required dependency on Jev/TypeSafe/MAGMA/Laya.
