# ADR-005: CodeGenome Is the Code Reality Substrate

## Status

Proposed

## Context

CodeGenome models codebases as content-addressed, multi-layer reality graphs. It includes syntax, semantic, flow, process, runtime, SCIP, LSP, provenance, and confidence overlays.

This makes it a domain reality graph for software artifacts, not a general memory runtime by itself.

## Decision

CodeGenome is the canonical code reality substrate.

It should provide evidence, graph relations, provenance, confidence, and impact traversal for code artifacts consumed by agentic memory systems.

## Consequences

### Positive

- preserves CodeGenome as a strong domain substrate
- allows memory systems to consume code reality without reimplementing code understanding
- separates code confidence from memory durability

### Negative

- requires mapping between code graph nodes and memory units
- requires careful treatment of stale code artifacts

## Required boundary

```text
CodeGenome confidence supports evidence.
It does not automatically grant memory permanence.
```

## Doctrine

CodeGenome tells the agent what is structurally true about code.

The memory lifecycle decides how that knowledge persists and changes over time.
