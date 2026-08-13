# ADR-031: Temporal Claims Belong Inside the Cryptographic Event Commitment

- **Status:** Proposed
- **Date:** 2026-08-13
- **Related:** #262, #263, ADR-021, ADR-028, ADR-030, #232

## Context

Agent Memory already distinguishes canonical memory from derived projections, separates historical truth from current applicability, and treats external policy decisions as evidence rather than authority.

Temporal policy introduces a further integrity question: if an event is signed, should the event's temporal claims be merely adjacent metadata, or part of the exact cryptographic object that is signed?

If `event_time`, validity, stream identity, sequence, prior-event linkage, or schema identity can change without changing the signed object identity, a verifier can establish payload integrity while still accepting altered temporal meaning.

That is insufficient for governed temporal memory.

## Decision candidate

Agent Memory temporal events SHOULD use a **cryptographically committed temporal identity** in which the temporal semantics relevant to replay and ordering are part of the content-addressed object itself.

The event commitment is canonicalized deterministically and hashed. A signature covers a domain-separated representation of that content reference. Independent trusted-time evidence, when available, is attached as separate evidence over the commitment/signature digest.

```text
temporal commitment body
  payload/event identity
  event_time / observed_at / validity
  scope / stream
  sequence / previous_event_ref
  schema/profile identity
        |
        v
canonical serialization
        |
        v
content reference
        |
        v
domain-separated signature
        |
        +--> signer commitment
        |
        v
optional trusted-time witness
        |
        +--> independently witnessed existence time
        |
        v
Agent Memory currentness / PAMA
```

## Required separation

```text
content identity != signer authority
signature validity != trusted wall-clock time
trusted timestamp != semantic truth
chain continuity != lifecycle currentness
cryptographically valid event != current authority
```

## Temporal dimensions

The architecture distinguishes three time/order claims.

### Claimed time

Fields such as:

- `event_time`;
- `observed_at`;
- `valid_from`;
- `valid_to`.

Signing these fields proves the signer committed to those claims. It does not independently prove the wall clock.

### Cryptographic order

Fields such as:

- `stream_id`;
- `sequence`;
- `previous_event_ref`.

These create tamper-evident ordering within the declared stream. They do not prove no event was omitted, that no competing fork exists, or that the stream is globally canonical.

### Witnessed time

An optional external timestamp or transparency witness can establish evidence that a commitment existed by a particular time.

The witness remains an independent evidence layer. It does not make the event semantically correct, admitted, current, or authorized.

## Canonicalization and domain separation

For the JSON reference profile, RFC 8785 JCS is used to obtain deterministic bytes before SHA-256 content addressing.

The signature does not sign arbitrary raw JSON. It signs a domain-separated message derived from the exact content reference, for example:

```text
"agent-memory-temporal-event-v1\0" || content_ref
```

The normative architecture is algorithm-agile. Ed25519 is only the first reference implementation.

## UOR profile

UOR-Addr is an optional content-reference substrate.

Agent Memory MAY verify that the canonical temporal commitment has the expected UOR-Addr label under the already accepted UOR interoperability profile.

UOR remains responsible only for content identity compatibility.

It does not become:

- signing authority;
- key-management authority;
- trusted time source;
- memory admission authority;
- PAMA authority;
- lifecycle currentness authority.

## Chaining behavior

An event may commit to its predecessor:

```text
E1(sequence=1, previous=null)
E2(sequence=2, previous=E1)
E3(sequence=3, previous=E2)
```

A verifier can detect mutation/substitution of committed predecessors because downstream references change.

The chain is append-only evidence, not an automatic canonical history. Fork resolution and shared-writer coordination remain governed by existing Agent Memory architecture.

## Currentness and correction

A signed temporal event is historical evidence.

Later correction, supersession, revocation, dispute, or schema/currentness change creates new evidence. It does not rewrite the old commitment.

```text
E1 signature valid
E1 later superseded
=> E1 remains cryptographically valid historical evidence
=> E1 is not current merely because its signature still verifies
```

## Dogwood / temporal-policy relationship

A Dogwood adapter may project eligible events into a temporal trace while preserving references back to their cryptographic commitments.

Dogwood answers temporal policy questions over the derived trace. It does not become the cryptographic source of truth, trusted timestamp authority, or Agent Memory currentness authority.

ADR-030 remains responsible for whether that projection is semantically compatible/current for the exact policy consumer.

## Trusted-time evidence

RFC 3161-style timestamp evidence and transparency-log evidence are valid optional witness profiles.

A witness binds to the event commitment or signature digest and provides independently verifiable time evidence.

A missing trusted-time witness is not a signature failure. It means the system can verify signer commitment and committed order, but not independently prove wall-clock time beyond the signer's own claim.

## Acceptance evidence required

ADR-031 MUST remain Proposed until executable evidence demonstrates at least:

1. changing temporal claims changes content identity;
2. payload/schema/scope changes change content identity;
3. previous-event and sequence substitution are detected;
4. a wrong signing key is rejected;
5. signature verification binds to the exact content reference and explicit domain;
6. signer-claimed time is distinguishable from witnessed time;
7. trusted-time evidence cannot create authority/currentness;
8. valid historical signatures remain valid after supersession while currentness changes separately;
9. replay into another stream/scope is rejected by committed scope/stream identity;
10. UOR verification remains optional and `authority_effect = none`;
11. no UOR runtime is required for ordinary Agent Memory operation;
12. the chain cannot be interpreted as proof of deletion completeness or absence of omitted events;
13. a temporal-policy projection can reference committed events without requiring Dogwood semantics in core;
14. adversarial tests remain provider-neutral and pass full repository validation.

## Rejected alternatives

### Sign only the event payload

Rejected. Temporal meaning could change without invalidating the signature.

### Put an unsigned timestamp next to a signed payload

Rejected as a temporal-integrity guarantee. The timestamp could be changed independently.

### Treat a signed timestamp claim as trusted wall-clock proof

Rejected. The signer proves only its own commitment to the claimed time unless an independent witness exists.

### Make UOR the signature or trust authority

Rejected. UOR's value here is deterministic object identity, not authority.

### Treat a hash chain as canonical lifecycle truth

Rejected. A chain does not solve forks, omissions, currentness, deletion completeness, or authority.

## Initial implementation

- JSON Schema for temporal commitment evidence;
- RFC 8785 + SHA-256 reference content identity;
- Ed25519 sign/verify reference path;
- chain validation helpers;
- optional trusted-time witness binding representation;
- optional UOR compatibility evidence;
- adversarial test vectors;
- focused CI;
- wiki/visual documentation.
