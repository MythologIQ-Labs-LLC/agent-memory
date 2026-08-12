# Framework Lifecycle / Checkpoint Interoperability Profile

Status: V0.1 reference profile for #189.

This profile defines the minimum Agent Memory-facing seam for stateful agent frameworks that expose runs, workflow/session state, checkpoints, retries, resumes, or related runtime events.

The first reference host is Microsoft Agent Framework (MAF) Python `1.13.0`, tag `python-1.13.0`, pinned source commit `e39a8a2e79c8c8987a0b9082d3ccb8665734b897`.

MAF is a reference host, not a required Agent Memory runtime or canonical storage layer.

## Core boundary

```text
framework persisted state
!= Agent Memory admitted durable memory

retry
!= new durable mutation authority

checkpoint rewind
!= permission to roll back current Agent Memory state

session / workflow history
!= canonical memory by default
```

Framework runtime state may be useful as execution state, evidence, a memory candidate, or explicit non-memory. The classification must be explicit.

## Generic lifecycle seam

A V0.1 framework event may preserve:

```text
framework identity / version / pinned source
run / workflow / session reference
checkpoint and previous-checkpoint reference
event type
persistence classification
Agent Memory action / proposal identity
PAMA / decision receipt reference
composition / approval / execution reference when present
runtime trace-correlation reference when present
scope / tenant / project opaque references
Agent Memory state reference
idempotency key
evidence references
```

The generic contract does not copy framework conversation history, checkpoint blobs, prompts, tool payloads, or arbitrary framework metadata into canonical memory.

## Checkpoint ordering

The MAF `WorkflowCheckpoint` source at the pinned release carries both `previous_checkpoint_id` and `iteration_count`. MAF explicitly documents that `iteration_count` is not guaranteed unique, particularly around human-in-the-loop checkpoints, and that checkpoint ordering is defined by checkpoint lineage and timestamp rather than iteration count alone.

Agent Memory therefore treats explicit lineage as the V0.1 checkpoint relation signal:

```text
resume checkpoint == latest checkpoint -> current
resume checkpoint is an ancestor of latest -> stale
known checkpoint on another lineage -> divergent
missing/incomplete lineage -> unknown
```

A stale, divergent, or unknown framework checkpoint does not gain rollback authority over newer canonical Agent Memory state.

## Retry and idempotency

A framework retry or resume may re-enter the same application code after Agent Memory already committed a durable mutation.

V0.1 binds the mutation attempt to a stable idempotency key and the original decision receipt:

```text
same idempotency key + same receipt -> replay / reuse receipt
same idempotency key + different receipt -> conflict
new key -> new governed proposal required
```

The framework runtime does not decide whether repeated execution is a new authorized memory mutation.

## Persistence classification

Every framework persistence event uses one of:

- `execution_state`: state retained only to continue/recover execution;
- `evidence`: runtime state retained as evidence about what happened;
- `memory_candidate`: state that may be proposed through normal Agent Memory admission;
- `explicit_non_memory`: state that must not be treated as Agent Memory.

None of these classifications establishes admission by itself, including `memory_candidate`.

## Scope binding

When a framework event is correlated to an Agent Memory action, expected action/input/scope/tenant/project references are compared deterministically. Missing or mismatched fields remain mismatch evidence rather than being repaired through timing, names, semantic similarity, or checkpoint adjacency.

## Trace correlation

Runtime trace correlation from the #185 profile is optional evidence.

```text
trace available -> additional correlation evidence
trace unavailable -> governance/decision/checkpoint evidence remains valid
trace absent -> not proof that execution did not occur
```

## First-host behavioral proof

The pinned MAF comparator uses the real `agent-framework-core==1.13.0` package with `WorkflowCheckpoint` and `InMemoryCheckpointStorage`. It does not require an LLM or cloud service.

The comparator proves a bounded lifecycle:

1. real MAF checkpoints round-trip through framework storage;
2. two checkpoints may share an iteration count while lineage distinguishes current from stale;
3. Agent Memory commits one governed mutation;
4. a governed recall admits the current scoped memory;
5. retry recovers the original receipt and does not duplicate the durable mutation;
6. a PAMA-denied mutation remains uncommitted;
7. loading an older MAF checkpoint does not roll back newer Agent Memory state;
8. cross-scope recall is not admitted;
9. missing trace correlation does not erase governance evidence.

## Privacy and minimization

Default to stable identifiers, opaque scope refs, digests, receipt refs, checkpoint refs, and classifications.

Do not persist raw framework messages, prompts, hidden reasoning, complete checkpoint state, provider credentials, or full tool payloads merely to establish lifecycle correlation.

## V0.1 non-claims

V0.1 does not claim:

- MAF checkpoints are Agent Memory;
- checkpoint persistence proves lifecycle satisfaction;
- framework retry creates new authority;
- framework HITL history is reusable approval authority;
- trace success proves semantic authorization;
- a single framework proves the seam is universal;
- MAF is a required dependency for Agent Memory core/reference use.

## Failure behavior

- stale/unknown checkpoint lineage does not silently restore older memory state;
- retry after a known committed mutation reuses the bound receipt rather than committing again;
- a denied mutation remains denied even if framework execution continues;
- cross-scope context does not inherit memory merely because the framework run/checkpoint is valid;
- trace backend unavailability preserves explicit evidence gaps without widening authority.

## Rollback / removal

The framework adapter and comparator are optional. Removing MAF support leaves canonical Agent Memory state, receipts, and lifecycle semantics interpretable because framework-specific checkpoint fields exist only in the adapter/evidence layer.

## Follow-on gate

After the MAF V0.1 lifecycle is stable, test the same Agent Memory-facing lifecycle contract against a materially different host such as LangGraph. If that second host exposes a real semantic incompatibility, return to the generic contract before adding adapter-specific exceptions.
