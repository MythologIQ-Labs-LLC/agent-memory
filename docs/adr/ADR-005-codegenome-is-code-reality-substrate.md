# ADR-005: CodeGenome Is a Code-Domain Reality Source and First-Party Ancestry

## Status

Accepted; refined by [ADR-036](ADR-036-same-owner-components-are-first-party-modules.md)

## Context

CodeGenome models codebases as content-addressed, multi-layer reality graphs. It includes syntax, semantic, flow, process, runtime, SCIP, LSP, provenance, confidence, and impact/traversal mechanisms.

This makes CodeGenome valuable first-party implementation ancestry and a specialized code-domain reality source. It does **not** make CodeGenome the permanent runtime owner of Agent Memory's generic graph, vector, relational, causal, provenance, or retrieval machinery.

The original version of this ADR called CodeGenome the canonical code-reality substrate in the implementation map. That was a useful transition model while Agent Memory's native implementation was less mature. ADR-036 and the canonical ownership reconciliation now make the destination explicit.

## Decision

**Agent Memory owns the Code Reality Graph contract and generic memory/reality-graph machinery.**

CodeGenome has two valid relationships to that architecture:

1. **first-party implementation ancestry and test/evidence source** whose proven mechanisms may be harvested into native Agent Memory modules; and
2. **optional code-domain observation source** that may continue to supply code-specific identity, structure, evidence, freshness, relations, and impact information.

The boundary is:

```text
CodeGenome code-domain observations
        |
        v
Agent Memory Code Reality Graph / Cognitive Mesh

CodeGenome mechanisms
        |
        v
inspect / validate / harvest where useful
        |
        v
native Agent Memory graph / retrieval / evaluation machinery
```

CodeGenome is therefore not required to run for Agent Memory to possess generic graph memory, semantic/vector retrieval, causal traversal, provenance handling, or memory evaluation.

## Consequences

### Positive

- preserves CodeGenome's strong code-domain expertise without making it a foundational runtime dependency;
- allows Agent Memory to harvest proven embedding, traversal, provenance, impact, and experiment-loop mechanisms natively;
- allows code reality to remain specialized rather than promoting a code ontology into the universal Cognitive Mesh;
- makes downstream Agent Memory deployments viable without a CodeGenome runtime when code-domain observations are not required;
- preserves the ability to consume CodeGenome as a specialized evidence producer when code intelligence is useful.

### Negative

- Agent Memory must implement and maintain native generic graph/retrieval machinery rather than delegating it indefinitely;
- code-domain adapters must distinguish CodeGenome-specific observations from Agent Memory-native memory semantics;
- migration requires explicit currentness and identity mapping where historical CodeGenome-derived state is absorbed.

## Required boundary

```text
CodeGenome confidence supports evidence.
It does not automatically grant memory permanence, certification, or authority.

CodeGenome code-domain specialization
        !=
Agent Memory generic memory machinery
```

Inferred graph relations should preserve estimator/method provenance and uncertainty when material to downstream decisions.

A CodeGenome-derived mechanism adopted into this repository is named for the Agent Memory contract it implements under ADR-036, not exposed as a permanent provider dependency merely because CodeGenome implemented it first.

## Acceptance scope

Accepted establishes CodeGenome's code-domain and first-party-ancestry relationship to Agent Memory.

It does **not** claim:

- that every CodeGenome capability is required by Agent Memory;
- that CodeGenome owns Agent Memory's generic graph, vector, retrieval, provenance, or evaluation machinery;
- that CodeGenome must be present at runtime for ordinary Agent Memory operation; or
- that implementation ancestry promotes capability maturity without native evidence.

## Doctrine

CodeGenome can tell Agent Memory a great deal about **code**.

Agent Memory owns what it means to **remember, retrieve, govern, relate, correct, forget, and evaluate memory**.
