# ADR-012: Privacy and Sensitivity Classification Is Required

## Status

Proposed

## Context

Agentic memory systems may store or recall personal, organizational, security, financial, health, credential, code, policy, or public information.

A memory system that cannot classify sensitivity cannot reliably decide what may be stored, recalled, summarized, exported, shared, corrected, or deleted.

Local-first storage helps, but it is not enough. A locally stored sensitive memory can still be recalled into the wrong context, shared with the wrong agent, or preserved beyond its intended scope. Humanity, against all odds, continues to invent new ways to mishandle data.

## Decision

Privacy and sensitivity classification must be a first-class component.

The component should influence storage, retention, recall, context assembly, PAMA authority, certification, export, and deletion behavior.

## Consequences

### Positive

- prevents overbroad recall
- improves PAMA risk classification
- supports local-first and encrypted memory boundaries
- enables conformance tests for cross-user leakage and unsafe context assembly
- makes retention and deletion policy enforceable

### Negative

- requires sensitivity taxonomy
- may require implementation-specific classifiers
- may reduce recall convenience when sensitivity is unclear

## Required classes

At minimum, the system should support sensitivity classes for:

- public
- personal
- organizational
- security-sensitive
- credential or secret
- financial
- health or wellbeing
- code or IP-sensitive
- policy or compliance
- restricted or consent-bound

## Required follow-up

Create and maintain:

```text
docs/19-privacy-and-sensitivity-classifier.md
```

## Doctrine

A memory cannot be safely recalled until the system knows the sensitivity boundary it belongs to.
