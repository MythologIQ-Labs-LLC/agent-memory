# System Composition Boundaries

## Purpose

This document defines how the larger Agent Memory architecture composes from separate systems without collapsing their responsibilities.

The goal is to make the architecture feel like one coherent system while preserving the boundaries that make it implementable, governable, and testable.

Composition is also where uncertainty can become dangerous: an estimate produced safely by one component can become an unauthorized consequence if another component consumes it without preserving meaning, scope, uncertainty, or policy state.

## Composition model

Agent Memory is a composed system.

```text
Agent Memory
  = Identity
  + Evidence
  + Reality Graphs
  + Lifecycle
  + Saturation and Decay
  + Governance
  + Certification
  + Runtime Memory
  + Context Assembly
  + Correction and Dispute
  + Conformance
```

This is one concept at the architecture level and many components at the implementation level.

## System boundary

The system boundary includes any component that participates in governed memory state transition or governed memory admission.

A component is inside Agent Memory if it answers at least one of these questions:

1. What is this memory object?
2. Why is this memory supported?
3. What does the system estimate about this memory?
4. How should this memory be scored or routed?
5. What state is this memory in?
6. Who may mutate, share, prune, or delete this memory?
7. Can this memory become durable?
8. May this memory enter the current agent context?
9. How is this memory corrected, disputed, or pruned?
10. How is memory behavior tested?

## Outside the system boundary

A tool is outside the core Agent Memory system when it only consumes outputs without influencing memory state or admission.

Examples:

- a UI that only displays certified memory
- an analytics dashboard that reads conformance reports
- a documentation site that mirrors doctrine files
- an LLM prompt template that consumes an already-governed context package and cannot mutate state

These can be integrations, but not core components.

## Canonical component contracts

### Identity contract

Input:

```text
artifact
```

Output:

```text
stable identity or address
```

Guarantees:

- deterministic resolution where required
- no lifecycle decision
- no truth claim
- no confidence-weighted identity substitution

### Evidence contract

Input:

```text
identity, observation, source reference
```

Output:

```text
evidence record, provenance, confidence or uncertainty signal
```

Guarantees:

- source traceability
- witness record
- estimator/method provenance when evidence is inferred
- no permanence decision by evidence alone

### Reality graph contract

Input:

```text
evidence records, domain artifacts
```

Output:

```text
graph nodes, graph edges, relation confidence, provenance
```

Guarantees:

- domain structure
- deterministic and inferred relations remain distinguishable
- confidence and source separation
- material disagreement remains visible
- no mutation authority by graph confidence alone

### Lifecycle contract

Input:

```text
memory unit, event, score, policy signal, transition proposal
```

Output:

```text
validated transition proposal or committed state-transition record
```

Guarantees:

- proposal and commit remain distinct
- state machine alignment
- transition metadata
- no unauthorized mutation
- policy and state snapshot can be reconstructed for consequential commits

### Saturation and decay contract

Input:

```text
memory unit, fibers, interaction history, pressure
```

Output:

```text
sigma, decay profile, candidate routing signal, uncertainty metadata
```

Guarantees:

- calibrated scoring where used for consequential routing
- score semantics are declared
- calibration scope and version are preserved
- trap-class resistance
- no truth or permission claim

### Governance contract

Input:

```text
requested mutation, memory state, risk, evidence, actor, reversibility, estimator outputs, uncertainty
```

Output:

```text
PAMA outcome and permitted action set
```

Guarantees:

- finite authority decision
- deterministic or formally bounded outcome for committed inputs and policy snapshot
- audit requirement
- no factual confirmation by authority alone
- missing authority-critical inputs are not guessed

### Action-selection contract

Input:

```text
permitted action set, planner state, runtime objective
```

Output:

```text
selected permitted action
```

Guarantees:

- deterministic or stochastic selection is allowed only inside the permitted set
- blocked actions are not selectable
- selection mode can be recorded when consequential

### Certification contract

Input:

```text
candidate memory, evidence, authority outcome, verification material
```

Output:

```text
certification status, scope, certificate reference
```

Guarantees:

- durable transition confirmation
- scoped certification
- certificate binds to relevant policy/evidence context
- correction remains possible

### Runtime memory contract

Input:

```text
memory units, graph relations, context request, policy constraints
```

Output:

```text
retrieval candidates, admitted memory, assembled context, operational memory view
```

Guarantees:

- candidate generation may be probabilistic
- scope, tenancy, sensitivity, dispute, and policy constraints apply before admission
- user or agent usable memory
- no hidden durable mutation

### Correction and dispute contract

Input:

```text
contradiction, user correction, failed verification, expired source
```

Output:

```text
dispute proposal, correction proposal, demotion, reconciliation, or pruning action
```

Guarantees:

- conflict interpretation may remain probabilistic
- consequence is governed
- old state is preserved
- correction is ledgered
- disputed memory is blocked from canonical use

### Conformance contract

Input:

```text
fixtures, implementation behavior, report data
```

Output:

```text
conformance result, calibration metrics, failure report
```

Guarantees:

- trap-class checks
- uncertainty and calibration transparency
- component and composition boundaries are testable
- stochastic systems are judged against invariants, not identical sampled outputs

## Cross-component handoff record

When one component passes consequential memory information to another, the handoff should preserve where applicable:

```text
memory_id
source_component
target_component
handoff_reason
state_snapshot
signal_type
signal_semantics
signal_value
estimator_ref
estimator_version
calibration_ref
uncertainty_summary
evidence_refs
policy_refs
policy_version
authority_refs
permitted_action_set
certification_refs
ledger_ref
timestamp
```

Not every handoff requires every field. A receiving component must not infer omitted authority, scope, or certainty.

## Handoff invariants

Across adapters and service boundaries:

1. identity must not become probabilistic accidentally
2. confidence must not become certification
3. relevance must not become access permission
4. utility must not become deletion authority
5. saturation must not become factual truth
6. disagreement must not vanish through undocumented averaging
7. estimator version must not be confused with policy version
8. a blocked action must remain blocked downstream
9. stochastic action selection must remain within the permitted action set
10. committed consequences must remain auditable after the handoff chain completes

## Composition-specific failure modes

### Semantic type erasure

```text
confidence=0.92 -> receiving service treats 0.92 as approval probability
```

Mitigation: preserve score semantics and estimator provenance.

### Boolean coercion of uncertainty

```text
sensitivity classifier: uncertain -> API field: sensitive=false
```

Mitigation: support abstention/unknown or enforce a conservative policy state.

### Authority leakage

```text
retriever recommends delete -> storage service interprets recommendation as authorization
```

Mitigation: require explicit governance outcome and permitted action set.

### Scope laundering

```text
cross-tenant memory -> summary service removes tenant metadata -> context assembler treats summary as local
```

Mitigation: scope and provenance must survive synthesis.

### Stale authorization

```text
PAMA allow at state S1 -> state changes to S2 -> old allow reused for commit
```

Mitigation: bind authority to state snapshot, policy version, and requested action.

### Unsafe composition

```text
memory A safe alone
memory B safe alone
A + B creates prohibited instruction or inference
```

Mitigation: apply read-time/composition governance and test multi-memory fixtures.

### Deterministic wrapper fallacy

```text
probabilistic score -> deterministic threshold -> therefore safe
```

Mitigation: preserve uncertainty and calibrate the consequential decision boundary.

## Composition anti-patterns

### Monolith collapse

Wrong:

```text
Vault owns identity, truth, scoring, certification, and correction.
```

Correct:

```text
Vault hosts runtime memory and calls identity, scoring, governance, and certification boundaries.
```

### Graph absolutism

Wrong:

```text
The graph says it, therefore memory is canonical.
```

Correct:

```text
The graph provides evidence and relations. Certification decides durable state.
```

### Score absolutism

Wrong:

```text
Sigma is high, therefore crystallize.
```

Correct:

```text
Sigma is high, therefore propose candidacy and evaluate authority plus certification.
```

### Relevance absolutism

Wrong:

```text
This memory is the best semantic match, therefore inject it.
```

Correct:

```text
This memory is a retrieval candidate. Recall-time governance still applies scope, sensitivity, dispute, and policy filters.
```

### Product-local doctrine

Wrong:

```text
COREFORGE defines memory differently from EvolveAI and CodeGenome.
```

Correct:

```text
Each repo implements its slice while referencing shared doctrine boundaries.
```

## Integration posture

Use typed adapters between components.

Do not use implicit shared assumptions.

Recommended adapters:

- identity adapter
- evidence adapter
- graph adapter
- lifecycle proposal adapter
- scoring / estimator adapter
- PAMA adapter
- action-set adapter
- certification adapter
- runtime memory adapter
- recall-admission adapter
- conformance adapter

Adapters that carry consequential estimates should document both data schema and semantic contract.

## Composition conformance

At least these end-to-end paths should be tested:

```text
semantic retrieval -> scope filter -> context admission
confidence estimator -> PAMA -> transition commit
saturation estimator -> candidate proposal -> certification
sensitivity classifier -> sharing policy -> export
utility estimator -> retention policy -> prune/delete decision
conflict detector -> dispute policy -> correction/reconciliation
multi-memory retrieval -> composition policy -> context assembly
```

Tests should inject uncertainty and disagreement at the seams, not only inside individual components.

## System rule

Agent Memory is unified by contracts, not by repository location.

The concepts should be segmented by responsibility, then recomposed through governed, typed handoffs.

A safe component is necessary. A safe composition is the actual requirement.
