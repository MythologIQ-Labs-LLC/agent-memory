# ADR-008: Memory Threat Model Is Required

## Status

Proposed

## Context

The doctrine already defines trap classes such as access-spam and confidently-wrong memory. Those are necessary, but not sufficient.

A governed memory system also faces broader threats:

- memory poisoning
- recursive self-citation
- source spoofing
- provenance stripping
- unauthorized mutation
- stale policy retention
- cross-user leakage
- overbroad context assembly
- malicious correction
- poisoned code graph evidence

Without a threat model, conformance becomes too narrow and the system can appear safe while failing under adversarial memory pressure.

## Decision

Agent Memory must include a formal memory threat model.

The threat model will define threat classes, affected components, detection strategies, mitigations, and required conformance fixtures.

## Consequences

### Positive

- expands safety beyond current trap classes
- gives PAMA and certification concrete adversarial cases
- improves conformance fixture design
- clarifies memory-specific security risks

### Negative

- adds additional documentation and fixture burden
- may require implementation repos to expose more audit and provenance data

## Required follow-up

Create and maintain:

```text
docs/15-memory-threat-model.md
```

The threat model should link to:

- PAMA governance
- certification and crystallization
- source trust and reputation
- governed recall
- privacy and sensitivity classification
- conformance fixtures

## Doctrine

A memory system is not trustworthy unless it defines how memory can be attacked.
