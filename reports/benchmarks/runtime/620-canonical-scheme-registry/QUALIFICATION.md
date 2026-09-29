# #620 canonicalization scheme registry qualification

Status: **qualification evidence / no runtime activation**  
Parent: #609  
Decision candidate: ADR-040  

## Result

The candidate registry is sufficient to express and test the compatibility identity required before migration, without changing current persistence or recovery behavior.

The controlling lookup boundary is:

```text
identity domain
+ recorded commitment scheme/prefix
+ runtime-envelope schema context
    -> exactly one canonicalization profile
    -> exactly one root/commitment contract
```

A recorded prefix alone is not sufficient identity.

## Legacy ambiguity made explicit

`sha256:` is historically reused in two distinct persistence domains:

- legacy substrate full-JSON commitment;
- legacy governance full-JSON commitment.

The two domains share a textual prefix but do not share a root contract. Registry lookup therefore remains domain-scoped and runtime-envelope-aware.

```text
substrate_state + sha256:
  -> substrate-full-json-sha256-v1

governance_state + sha256: + runtime schema 1.0.0
  -> governance-full-json-sha256-v1
```

The candidate refuses prefix-only reinterpretation across domains.

## Frozen bindings

The pre-implementation fixture freezes six bindings:

1. legacy substrate full JSON;
2. current substrate `bmerkle-v1`;
3. legacy governance full JSON;
4. current governance `gsect-v1`;
5. candidate `bmerkle-v2` using `agent-memory-canonical-json-v2`;
6. candidate `gsect-v2` using `agent-memory-canonical-json-v2`.

Existing RFC 8785/JCS evidence/security identity domains are explicitly excluded from this persistence registry.

Candidate v2 bindings are recognizable for qualification but have no accepted runtime-envelope schema and are not emittable.

## Stable refusal surface

Qualification covers stable refusals for:

- unknown scheme in a domain;
- ambiguous domain/prefix binding;
- malformed commitment shape;
- canonicalizer mismatch;
- root-contract mismatch;
- runtime-envelope schema mismatch;
- candidate activation attempt;
- any emission request through the qualification registry;
- excluded JCS identity domain.

The registry deliberately does not treat successful lookup as emission or migration permission.

## Adversarial hardening

The first resolver implementation refused `emit` only for candidate-v2 bindings. That was too weak: current/legacy bindings could still be returned from an `emit` operation, even though no persistence write occurred.

The implementation was tightened without changing the frozen fixture:

```text
candidate v2 emit
  -> candidate_activation_forbidden

current / legacy emit
  -> registry_emission_forbidden
```

This preserves the invariant:

```text
registry lookup != emission authority
```

## Mixed-generation envelope evidence

Envelope-level tests use one runtime schema context across both domains.

Runtime schema `1.1.0`:

```text
substrate bmerkle-v1       -> valid binding
governance legacy sha256:  -> runtime_schema_binding_mismatch
```

Runtime schema `1.0.0`:

```text
substrate legacy sha256: -> valid binding
governance gsect-v1      -> runtime_schema_binding_mismatch
```

Therefore independently known schemes cannot be combined into a trusted mixed-generation recovery envelope merely because each scheme exists somewhere in repository history.

## Source tether

Tests bind the frozen legacy/current fixture entries to the actual runtime constants in:

- `reference/agentmem_ref/state/sqlite_substrate.py`;
- `reference/agentmem_ref/runtime/sqlite_runtime.py`.

A change to the active legacy/current scheme names or runtime-state schema versions invalidates this qualification rather than leaving a self-consistent but stale fixture.

## Stop line

This slice does not:

- import the registry into `agentmem_ref`;
- change current recovery logic;
- change current canonical bytes;
- emit `bmerkle-v2` or `gsect-v2`;
- migrate persisted state;
- accept ADR-040;
- grant memory authority, admission, ranking, currentness, lifecycle or migration permission;
- reinterpret existing JCS identity domains;
- promote Rust into persistence or recovery.

## Next gate

The next #609 slice is **verify-old-before-recommit migration evidence**.

It must prove at minimum:

1. legacy state verifies completely before any migration write;
2. tampered legacy state refuses migration;
3. unsupported v2 values refuse without partial conversion;
4. interrupted or failed migration leaves the legacy state valid and unchanged;
5. the scheme transition is transactional and provenance-bearing;
6. v2 state verifies after commit and restart;
7. rollback and scheme-confusion attempts fail closed;
8. memory semantics, authority, scope and accepted benchmark behavior remain unchanged.
