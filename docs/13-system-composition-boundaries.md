# System Composition Boundaries

## Purpose

This document defines how the larger Agent Memory architecture composes from separate systems without collapsing their responsibilities.

The goal is to make the architecture feel like one coherent system while preserving the boundaries that make it implementable.

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

The system boundary includes any component that participates in governed memory state transition.

A component is inside Agent Memory if it answers at least one of these questions:

1. What is this memory object?
2. Why is this memory supported?
3. How should this memory be scored or routed?
4. What state is this memory in?
5. Who may mutate this memory?
6. Can this memory become durable?
7. How is this memory used by an agent?
8. How is this memory corrected, disputed, or pruned?
9. How is memory behavior tested?

## Outside the system boundary

A tool is outside the core Agent Memory system when it only consumes outputs without influencing memory state.

Examples:

- a UI that only displays certified memory
- an analytics dashboard that reads conformance reports
- a documentation site that mirrors doctrine files
- an LLM prompt template that consumes retrieved memory but cannot mutate state

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

- deterministic resolution where possible
- no lifecycle decision
- no truth claim

### Evidence contract

Input:

```text
identity, observation, source reference
```

Output:

```text
evidence record, provenance, confidence signal
```

Guarantees:

- source traceability
- witness record
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
- confidence and source separation
- no mutation authority by graph confidence alone

### Lifecycle contract

Input:

```text
memory unit, event, score, policy signal
```

Output:

```text
state transition proposal or state transition record
```

Guarantees:

- state machine alignment
- transition metadata
- no unauthorized mutation

### Saturation and decay contract

Input:

```text
memory unit, fibers, interaction history, pressure
```

Output:

```text
sigma, decay profile, candidate routing signal
```

Guarantees:

- calibrated scoring where used for durable decisions
- trap-class resistance
- no truth claim

### Governance contract

Input:

```text
requested mutation, memory state, risk, evidence, actor, reversibility
```

Output:

```text
PAMA outcome
```

Guarantees:

- authority decision
- audit requirement
- no factual confirmation by authority alone

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
- correction remains possible

### Runtime memory contract

Input:

```text
memory units, graph relations, context request, policy constraints
```

Output:

```text
retrieved memory, assembled context, operational memory view
```

Guarantees:

- scope-aware recall
- user or agent usable memory
- no hidden durable mutation

### Correction and dispute contract

Input:

```text
contradiction, user correction, failed verification, expired source
```

Output:

```text
dispute record, correction record, demotion, reconciliation, or pruning
```

Guarantees:

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
- calibration transparency
- implementation boundaries are testable

## Cross-component handoff record

When one component passes memory to another, the handoff should preserve:

```text
memory_id
source_component
target_component
handoff_reason
state_before
state_after_if_changed
evidence_refs
policy_refs
authority_refs
certification_refs
ledger_ref
timestamp
```

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

Use adapters between components.

Do not use implicit shared assumptions.

Recommended adapters:

- identity adapter
- evidence adapter
- graph adapter
- lifecycle adapter
- scoring adapter
- PAMA adapter
- certification adapter
- runtime memory adapter
- conformance adapter

## System rule

Agent Memory is unified by contracts, not by repository location.

The concepts should be segmented by responsibility, then recomposed through governed handoffs.
