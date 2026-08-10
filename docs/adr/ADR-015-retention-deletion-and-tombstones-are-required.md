# ADR-015: Retention, Deletion, and Tombstones Are Required

## Status

Proposed

## Context

The architecture distinguishes pruning, archival, suppression, redaction, correction, crystallization, and privacy handling, but still needs one canonical retention/deletion contract tying them together.

A memory system that can remember but cannot explain deletion is not governed. It is a hoarder with APIs.

## Decision candidate

Agent Memory must define explicit retention, deletion, redaction, archival, and tombstone semantics.

Deletion is not pruning. Predicted low utility is not deletion authority. Removing the raw record is not complete deletion if summaries, embeddings, graphs, caches, or consolidated memories still retain recoverable content.

## Required distinctions

- active recall removal
- suppression
- archival retention
- tombstone retention
- redacted retention
- cryptographic deletion
- source deletion
- derived-memory deletion
- exported-memory deletion
- certification revocation
- verified full-pipeline purge

## Consequences

### Positive

- prevents silent disappearance and incomplete deletion
- supports privacy, consent, retention, and audit policy
- preserves accountability where appropriate
- makes forgetting modes explicit

### Negative

- creates tension between deletion and evidence retention
- requires dependency traversal across derived memory
- requires policy-specific verification

## Required follow-up before acceptance

Create and audit:

```text
docs/28-retention-deletion-and-tombstones.md
```

Then add deletion-residue and dependency-propagation conformance fixtures.

## Doctrine candidate

Forgetting is a governed family of operations.

Irreversible deletion requires stronger authority than reversible pruning or archival.
