# ADR-015: Retention, Deletion, and Tombstones Are Required

## Status

Proposed

## Context

The architecture defines pruning, correction, dispute, crystallization, privacy classification, and governed recall. It does not yet define a complete retention and deletion model.

A memory system that can remember but cannot explain deletion is not governed. It is a hoarder with APIs.

Memory may need to be:

- retained for audit
- removed from active recall
- tombstoned
- deleted from local storage
- deleted from exported artifacts
- retained in redacted form
- excluded from future context assembly

These are different operations and must not be collapsed.

## Decision

Agent Memory must define explicit retention, deletion, and tombstone semantics.

Deletion is not the same as pruning. Pruning removes active recall. Tombstoning preserves a record that something existed and why it was removed. Deletion removes content according to policy, sensitivity, consent, or legal requirement.

## Consequences

### Positive

- prevents silent disappearance of memory
- supports privacy and retention policy
- preserves accountability when appropriate
- distinguishes active recall from storage retention
- supports local-first and user-controlled memory products

### Negative

- requires policy-specific retention rules
- may create tension between audit preservation and deletion requirements
- requires careful handling of derived memories and compiled summaries

## Required distinctions

The architecture must distinguish:

- active recall removal
- archival retention
- tombstone retention
- redacted retention
- source deletion
- derived-memory deletion
- exported-memory deletion
- certification revocation

## Required follow-up

Create and maintain:

```text
docs/23-retention-deletion-and-tombstones.md
```

## Doctrine

Forgetting is a governed operation.

A memory system must explain not only why it remembers, but why and how it forgets.
