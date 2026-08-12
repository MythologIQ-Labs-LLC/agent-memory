# ADR-024: Shared Memory Writes Require Pre-Write Claims

Status: Proposed

Date: 2026-08-12

## Context

Issues #137 and #138 identify durable memory mutation as more than a retrieval problem. Shared agent memory must answer both what becomes memory and who may change durable state.

In multi-agent systems, uncoordinated writes can create silent overwrites, stale updates, authority laundering, and conflict resolution after the damage has already been committed. The existing repository doctrine already includes PAMA mutation authority, conflict resolution, temporal causality, audit events, and concurrency evidence. This ADR makes the pre-write coordination requirement explicit.

## Decision

Shared durable memory writes require a pre-write claim, lock, lease, compare-and-swap guard, single-writer queue, transactional reservation, or equivalent coordination mechanism before durable state changes.

The coordination mechanism must bind the actor, task, scope, proposed mutation class, authority basis, timestamp, and expiration or validity behavior before commit.

Conflicting writes must fail closed or route into conflict resolution before commit. The system must not rely on post-hoc cleanup as the primary protection against unauthorized or conflicting shared-state mutation.

Failed, rejected, expired, superseded, or unauthorized claims remain governance evidence.

## Rationale

Shared memory is trust infrastructure. Trustworthy mutation requires deciding authority and conflict boundaries before durable state changes, not after competing agents have already overwritten each other.

This ADR does not require a specific distributed locking primitive. Different runtimes may use leases, transactions, compare-and-swap, optimistic concurrency, queue ownership, or database-native locks. The architectural requirement is that durable mutation is coordinated and auditable before commit.

## Consequences

### Positive

- Concurrent writers have an explicit coordination boundary.
- Conflict resolution happens before durable mutation.
- Stale and unauthorized claims become testable negative paths.
- Audit trails include both successful and failed write attempts.
- PAMA can evaluate mutation authority against a bounded claim rather than an already-mutated state.

### Negative

- Implementations must manage claim expiry and abandoned work.
- Systems must avoid deadlock, stale locks, and over-broad claims.
- Claim granularity becomes an architectural decision.
- Runtime adapters need evidence formats for both successful and failed claims.

## Implementation notes

A conforming implementation should record at least:

- claim identifier;
- actor identity;
- task or operation identifier;
- memory scope or affected record set;
- requested mutation class;
- authority basis;
- timestamp and expiry or lease terms;
- current claim status;
- conflict disposition;
- commit receipt or rejection reason.

The claim must be narrow enough to prevent accidental broad authority and durable enough to support audit review.

## Validation and acceptance

This ADR should not advance beyond Proposed until the repository includes evidence for:

- a successful shared-memory write using a valid pre-write claim;
- a rejected concurrent write against the same scope;
- a stale or expired claim that cannot commit;
- an unauthorized claim that fails closed;
- audit evidence preserving successful and failed claim outcomes;
- documentation showing how the mechanism composes with PAMA, conflict resolution, temporal causality, and observability.

## Related

- #137
- #138
- #143
- ADR-004: PAMA Controls Mutation Authority
- ADR-010: Conflict Resolution Is a Separate Component
- ADR-011: Temporal Causality Is Required for Memory Evolution
- ADR-017: Memory Observability and Audit Events Are Required
- ADR-020: Probabilistic Discovery, Deterministic Governance
