# Failure Memory Closeout Notes

Issue: #471
Parent harvest closeout: #470

This file intentionally tracks the final closeout delta separately from the initial native-failure-memory implementation note while #471 remains open.

## Proven in PR #473

The native failure-memory implementation now includes:

- stable logical failure identity;
- typed immutable revisions;
- explicit recurrence evidence;
- correction, dispute, retraction, and history;
- ordinary Cognitive Mesh + PAMA commit authority;
- non-authoritative similarity/severity/recurrence evidence;
- bounded restart-safe owner checkpoint/recovery through `CheckpointedFailureMemory`;
- restart proof that recurrence/currentness survives recovery;
- restart proof that retracted/tombstoned failure state does not regain current influence;
- fail-closed restore when owner state references a durable fact that is absent;
- a revision-bound native failure-memory benchmark that reports quality, performance, and governance separately.

The generic standalone `FailureMemory` revision owner remains process-local. The restart-safe claim is intentionally bounded to the explicit `CheckpointedFailureMemory` composition through `ComposedRestartSafeRuntime`.

## Evidence boundary

The bounded benchmark does not claim that remembering a failure automatically prevents a future downstream action. Agent Memory emits governed memory evidence. The downstream action path remains separately governed and is not simulated by this benchmark.

The benchmark therefore reports `avoided_repeated_failure.status = not_measured` rather than inventing an outcome claim.

## Remaining closeout defect

Before #471 can close, typed recall isolation must be made explicit for the shared-runtime case.

`FailureMemory.recall_active()` currently delegates through the generic Cognitive Mesh recall helper. That helper is intentionally generic and can represent an admitted fact by its fact UUID when the specialized memory owner has no object mapping for it. A failure-memory API must instead fail closed on admitted facts that are not owned by the failure-memory form.

Required remediation:

```text
adapter governed recall
    -> admitted facts
    -> failure-memory ownership/type filter
    -> current failure revision check
    -> disputed/retracted check
    -> contextual admission
    -> active failure refs only
```

An unrelated semantic/epistemic fact admitted by the shared adapter must never appear as active failure guidance merely because it matched the text query.

This is an implementation-isolation defect, not an authority expansion. PAMA and recall admission remain load-bearing.
