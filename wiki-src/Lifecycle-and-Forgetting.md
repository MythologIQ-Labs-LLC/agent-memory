# Lifecycle and Forgetting

Memory should have a history. Agent Memory therefore treats persistence, consolidation, revision, and forgetting as explicit lifecycle behavior rather than invisible side effects of a storage engine.

## Seven memory functions

```text
ENCODE → RETAIN → CONSOLIDATE → RETRIEVE → REVISE → FORGET → INHERIT
```

Each function asks a different architectural question.

| Function | Question |
|---|---|
| Encode | What experience becomes a memory candidate? |
| Retain | What crosses a persistence boundary? |
| Consolidate | What can be generalized, summarized, proceduralized, or modeled? |
| Retrieve | What retained state is relevant now? |
| Revise | How do correction, contradiction, and supersession change memory? |
| Forget | What should decay, suppress, archive, redact, tombstone, or delete? |
| Inherit | What may pass to a successor agent, team, or generation? |

## Lifecycle state is explicit

A compact view:

```text
Transient → Observed → Linked → Reinforced
                    ↓
Candidate → Pending verification → Crystallized
                                  ↓
                          Operational reuse
                                  ↓
                          Stale / Disputed
                                  ↓
                    Corrected → Reconciled
                                  ↓
                       Archived / Pruned
                                  ↓
                             Tombstoned
```

Not every memory traverses every state. The requirement is that consequential transitions remain explicit, scoped, authorized, and auditable.

## Forgetting is not one operation

Agent Memory distinguishes:

- decay
- suppression
- interference management
- deprioritization
- pruning
- archival
- compression
- semanticization
- supersession
- redaction
- tombstoning
- cryptographic deletion
- full-pipeline purge
- specialized model unlearning

Those operations differ in reversibility, evidence requirements, downstream effects, and authority.

## Utility does not grant deletion authority

```text
predicted low utility → forgetting candidate
predicted low utility != irreversible deletion authority
```

A model can recommend deletion. It does not gain permission to destroy durable evidence merely because the recommendation is confident.

## Derived state matters

Deleting one canonical record may leave behind:

- summaries
- embeddings and indexes
- graph edges
- caches
- exported copies
- consolidated semantic memories
- derived procedures
- telemetry or audit material

A deletion guarantee is only as strong as the propagation boundary it actually controls.

## Correction is not erasure

Agent Memory prefers preserved history over silent overwrite.

```text
stale != false
superseded != corrected
historically true != currently true
```

When evidence changes, the architecture should preserve what was known, what changed, why it changed, and which newer state supersedes the old one.

## Canonical sources

- Lifecycle state machine: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/02-lifecycle-state-machine.md
- Forgetting and consolidation: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/21-forgetting-consolidation-and-memory-metabolism.md
- Retention, deletion, tombstones: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/28-retention-deletion-and-tombstones.md
- Recovery and replay: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/31-recovery-rollback-and-replay.md

## Next

- **[Security and Privacy](Security-and-Privacy)** for deletion residue and lifecycle attack surfaces
- **[Conformance and Evidence](Conformance-and-Evidence)** for proving lifecycle behavior
