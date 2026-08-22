# Agent Memory Runtime Adapter

A bounded, host-neutral ESM adapter for governed runtime recall and correction/supersession.

It exists to let a runtime host consume Agent Memory doctrine without copying memory semantics into the host. It is intentionally not a complete Agent Memory implementation.

## What this adapter owns

- exact actor/project/task scope validation;
- recall admission after candidate loading;
- rejection of unknown-scope, foreign-scope, disputed, and superseded memory;
- explicit `authority_effect: "none"` on recall;
- correction as an append-only replacement plus supersession linkage;
- evidence and authority requirements for committed correction;
- idempotent correction handoff;
- stale-state refusal.

## What the storage port owns

The host supplies three persistence methods:

```text
load(scope)
lookupIdempotency(scope, idempotencyKey)
commitCorrection(scope, transaction)
```

`commitCorrection` must atomically enforce `expected_revision`, persist the replacement memory and correction event, retain prior history, and bind the idempotency key to the resulting receipt.

A storage implementation that sees an old `expected_revision` must fail with:

```js
{ code: 'STALE_REVISION' }
```

The adapter converts that to the semantic `stale_state` refusal.

For the QOR Agent Cloudflare proving ground, the storage port will be implemented by a scoped SQLite Durable Object. That Cloudflare implementation belongs to QOR Agent, not this repository.

## Recall

```js
const result = await memory.recall({
  scope: {
    actor_id: 'actor:one',
    project_id: 'project:alpha',
    task_id: 'task:release-marker',
  },
  policy_version: 'policy-v1',
  purpose: 'release_target_recall',
});
```

The result separates `admitted` and `rejected` candidates and reports the storage `revision` and `checkpoint`. Candidate relevance does not grant execution authority, standing permission, or a consumer policy verdict.

## Correction

```js
const receipt = await memory.correct({
  scope,
  memory_id: 'memory-original',
  idempotency_key: 'correction:123',
  policy_version: 'policy-v1',
  evidence_refs: ['evidence:user-correction'],
  authority_refs: ['authority:human-confirmed'],
  replacement: {
    kind: 'correction',
    value_ref: 'value:main',
  },
});
```

The prior memory remains historical. The replacement carries `supersedes: [prior_memory_id]`, and active recall rejects the superseded record.

## Doctrine boundary

This package implements the bounded seam described by:

- `docs/34-adapter-contracts.md` runtime memory adapter;
- `docs/34-adapter-contracts.md` correction and dispute adapter;
- the repository's scope, tenancy, authority, and historical-truth distinctions.

It does not implement PAMA, standing authorization, a general retrieval engine, ranking, embeddings, a production approval system, or a universal durable store.

Tracks `MythologIQ-Labs-LLC/agent-memory#333` and the pre-cloud route in `MythologIQ-Labs-LLC/Myth-Tech-Forge#262`.
