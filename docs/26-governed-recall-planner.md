# Governed Recall Planner

> Canonical requirement: [ADR-013](adr/ADR-013-governed-recall-planner-is-required.md)

## Purpose

Retrieval finds candidate memory. Governed recall decides which candidates may enter an agent's active context, under what representation, and with what warnings or restrictions.

The recall planner exists because semantic relevance is not permission.

```text
high relevance != authorized recall
```

## Core pipeline

```text
query / task
  -> requester + purpose + scope resolution
  -> candidate generation
  -> candidate normalization
  -> recall admission
  -> ranking among admitted candidates
  -> composition risk check
  -> context budgeting
  -> context assembly
  -> recall receipt / explanation
```

Candidate generation may be probabilistic. Admission and scope enforcement must be explicit and bounded.

## Discovery and traversal boundaries

The [actor/scope contract](29-actor-scope-consent-and-tenancy.md) and [isolation-domain contract](41-memory-isolation-domains-and-governed-crossing.md) govern permission to discover and traverse memory. [ADR-013](adr/ADR-013-governed-recall-planner-is-required.md) continues to govern recall admission. These are complementary boundaries, not competing admission authorities.

For a caller-supplied logical identity or a candidate used as a graph-expansion origin, retrieval planning must distinguish the following stages:

1. **Resolve and prefilter.** A logical reference is only a request to look up an identity, not proof of authorization. Check the current candidate against the caller's domain before it contributes an exact-route hit, expansion seed, provenance, or candidate budget.
2. **Recheck immediately before traversal.** A selected seed may have been revoked or become ineligible. Re-evaluate the runtime's existing domain-eligibility predicate and relevant lifecycle conditions at the operation boundary. An ineligible or missing seed must not initiate evidence-neighbor or typed-graph traversal.
3. **Collect bounded candidates.** Scope filtering must precede consumption of a limited seed budget: invalid, missing or foreign identities cannot crowd out eligible seeds. No eligible graph seed means no traversal call.
4. **Admit canonically.** Every candidate that survives discovery still passes the existing canonical admission check. Early filtering is not admission and does not grant memory authority.
5. **Return authorized evidence.** Caller-visible candidates, route counts, selection traces and provenance must not reveal an unauthorized seed or distinguish a foreign identity from an unknown one merely because of traversal side effects.

These rules apply consistently to default multi-route, query-driven and controlled recall, including typed-graph and shared-evidence paths. They describe required behavior; they do not certify that a particular revision implements it. When testing canonical admission refusals, a deliberate prefilter bypass must be labeled **admission-only** and must not be presented as a test of ordinary discovery isolation.

The implementation owners are the retrieval planners in `reference/agentmem_ref/runtime/`, using the adapter's existing domain-eligibility semantics, and their security regression tests under `reference/tests/`. Exact implementation maturity and acceptance remain governed by source revision, runtime-baseline succession and executed evidence. A security fix is not proof of better benchmark precision; benchmark interpretation remains with [BENCHMARKS.md](../BENCHMARKS.md).

## Retrieval modes

A planner may compose:

- exact identity lookup
- graph traversal
- temporal lookup
- evidence search
- semantic/vector retrieval
- procedural retrieval
- prospective-memory lookup
- policy-memory lookup
- failure-memory lookup
- source-aware retrieval

No one retrieval mode owns truth or authority.

## Candidate record

A retrieval candidate should preserve where applicable:

```text
memory_id
retrieval_method
retriever_id
retriever_version
score_type
score
uncertainty
source_scope
memory_scope
sensitivity
dispute_state
certification_state
freshness_state
provenance_refs
```

A score must identify what it means. Similarity, confidence, trust, saturation, and policy priority are not interchangeable.

## Recall admission

Before context inclusion, evaluate:

```text
requester_identity
agent_identity
tenant
purpose
memory_scope
sensitivity
destination
consent/delegation
certification/dispute state
freshness
policy_version
```

Possible outcomes:

```text
admit
admit_with_warning
admit_redacted
admit_summary_only
require_verification
require_review
quarantine
block
```

## Bounded stochastic retrieval

Candidate ordering may vary across runs.

The invariant is not identical ordering. The invariant is:

```text
blocked_candidate never becomes admitted solely through randomness
```

A stochastic ranker may choose among admitted candidates, but must not bypass admission.

## Disputed memory

Disputed memory may be useful as evidence that disagreement exists.

It must not be silently presented as canonical.

Possible treatment:

- exclude from ordinary canonical recall
- include with explicit disputed status
- surface competing claims together
- trigger conflict-resolution workflow

## Historical memory

Temporal queries must distinguish:

```text
current state
state at time T
historically true but superseded state
incorrect state later corrected
```

A current-state query should not prefer a stale memory merely because it is semantically closer.

## Derived state after source deletion or tombstoning

A derived summary, projection, graph fact, cache entry, or similar artifact may remain physically discoverable after one of its source memories is pruned, deleted, or tombstoned. Candidate discovery does not make that derived artifact valid current evidence.

When the derivation basis includes a source that current lifecycle policy treats as tombstoned or deleted, ordinary current-state recall must fail closed unless a governed revalidation/rebuild path has independently established a new valid basis.

```text
tombstoned source
  -> derived artifact may still be a retrieval candidate
  -> ordinary admission rejects current use
  -> revalidation / rebuild requires its own governed evidence
```

This is separate from residue detection. A deletion sweep may identify undeclared residue for cleanup; recall admission independently prevents that residue from influencing current context while it remains reachable.

The reference refusal `derived_from_tombstoned_source` expresses this boundary. It is not a requirement that every implementation use that exact string, but conformance evidence must identify the equivalent blocking reason and stage.

## Sensitivity and destination

Recall policy should consider where the assembled context is going:

- local deterministic tool
- local model
- external model provider
- another agent
- human UI
- external API

Storage permission does not imply universal context permission.

## Composition risk

Individually admissible memories may create unsafe context when combined.

The planner should support policy checks for:

- reconstruction of secrets
- conflicting instructions
- unsafe instruction chains
- scope interaction
- aggregate sensitivity
- poisoned multi-memory patterns

## Context budget

Context pressure creates a second selection problem after admission.

Budget policy may use probabilistic utility estimates, but it should preserve hard requirements such as:

- must-include policy constraints
- required warnings
- active correction/dispute state
- critical procedural prerequisites

Do not let a utility score evict the only memory that explains why an action is prohibited.

## Recall explanations

For consequential recall, the system should be able to answer:

1. Why was this memory a candidate?
2. Which retrieval method produced it?
3. Why was it admitted?
4. Which policy version applied?
5. Was it redacted, summarized, or transformed?
6. What uncertainty or dispute state was preserved?
7. Why were stronger-scoring candidates blocked, if applicable?

## Failure modes

- similarity overrides tenancy
- ranking occurs before hard admission and leaks blocked candidates
- disputed memory appears canonical
- summaries erase scope/sensitivity
- stale memory outranks current memory
- derived state whose source was tombstoned remains admissible merely because the derived object itself was not tombstoned
- stochastic ranker can sample prohibited content
- context budgeting drops required governance state
- several safe memories compose into unsafe context

## Conformance cases

### Wrong-tenant perfect match

```text
semantic_score = 1.0
tenant_match = false
expected: blocked
```

### Disputed high-relevance memory

Expected: excluded from canonical recall or included with explicit dispute semantics.

### Derived residue from tombstoned source

Expected:

```text
candidate_discovered == true
admitted == false
current_context_surface == false
downstream_influence == false
blocking_reason == derived-from-tombstoned-source equivalent
```

The artifact's continued physical presence is evidence of residue, not evidence of current validity.

### Uncertain sensitivity

Expected: high-consequence external disclosure does not treat uncertainty as non-sensitive.

### Stochastic ordering

Run multiple trials.

Expected: admitted ordering may vary; prohibited candidate inclusion rate remains zero.

### Unsafe composition

Expected: individually admitted candidates may still be blocked or transformed at composition time.

### Historical query

Expected: time-scoped query can retrieve superseded historical truth without replacing current state.

## Interface sketch

```text
plan_recall(request) -> candidate_plan
admit(candidate, request, policy) -> admission_decision
rank(admitted_candidates, request) -> ordered_candidates
check_composition(candidates, request, policy) -> composition_decision
assemble(candidates, budget, policy) -> governed_context
explain(recall_id) -> recall_receipt
```

## Doctrine

Retrieval estimates usefulness.

Recall admission enforces permission.

Context assembly is a governed memory operation, not a vector-search side effect.
