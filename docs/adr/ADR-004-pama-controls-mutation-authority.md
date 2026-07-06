# ADR-004: PAMA Controls Mutation Authority

## Status

Proposed

## Context

Agentic memory systems need to adapt. Adaptation requires mutation of scores, links, summaries, states, and sometimes durable memory records.

Without explicit authority, adaptive memory becomes silent self-modification.

## Decision

PAMA controls mutation authority.

Any transition that changes memory state, durable content, graph relations, promotion status, correction state, or pruning status must pass through PAMA or an equivalent authority model.

## Consequences

### Positive

- makes memory mutation auditable
- scales autonomy by risk and reversibility
- prevents unauthorized rewriting of durable memory
- gives agents a clear boundary between recall and mutation

### Negative

- requires policy design
- requires mutation metadata
- may slow down high-impact memory changes

## Authority outcomes

```text
allow
allow_with_ledger
require_review
require_external_verification
block
```

## Doctrine

Capability is not authority.

The fact that an agent can change memory does not mean it is allowed to.
