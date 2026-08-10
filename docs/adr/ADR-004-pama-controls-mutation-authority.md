# ADR-004: PAMA Controls Mutation Authority

## Status

Accepted

## Context

Agentic memory systems need to adapt. Adaptation requires mutation of scores, links, summaries, states, and sometimes durable memory records.

Without explicit authority, adaptive memory becomes silent self-modification.

## Decision

PAMA controls mutation authority, or an implementation must provide an equivalent explicit authority model conforming to the same doctrine.

Any consequential transition that changes memory state, durable content, graph relations, promotion status, correction state, pruning/deletion state, sharing scope, or certification status must pass through that authority boundary.

Probabilistic or learned components may estimate confidence, trust, relevance, sensitivity, contradiction, utility, or risk. They may not grant themselves authority from those estimates.

## Consequences

### Positive

- makes memory mutation auditable
- scales autonomy by risk and reversibility
- prevents unauthorized rewriting of durable memory
- gives agents a clear boundary between inference and mutation

### Negative

- requires policy design
- requires mutation metadata
- may slow down high-impact memory changes

## Authority outcomes

Typical outcomes include:

```text
allow
allow_with_ledger
require_review
require_external_verification
block
```

Implementations may add bounded outcomes such as `abstain`, `quarantine`, or `collect_more_evidence` when their consequence semantics are explicit.

## Acceptance scope

Accepted establishes explicit mutation authority as canonical doctrine. It does not require one PAMA codebase or claim runtime enforcement exists in every implementation.

## Doctrine

Capability is not authority.

Confidence is not authority.

The fact that an agent can change memory does not mean it is allowed to.
