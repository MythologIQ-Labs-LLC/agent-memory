# Temporal Event Commitment Profile

Status: reference profile under #263. ADR-031 remains Proposed until executable acceptance evidence passes.

## Purpose

Bind temporal meaning into exact event identity before signing.

```text
claimed temporal object
  -> NFC + RFC 8785 canonical bytes
  -> SHA-256 content reference
  -> domain-separated signature
  -> optional independent time witness
```

## Separation of proofs

- content reference: what exact temporal object?
- signature: who committed to that exact object?
- time witness: when can existence be independently established?
- Agent Memory currentness/PAMA: what may it mean or authorize now?

None of these silently implies another.

## Committed fields

The reference profile commits event type, payload digest, event time, observation time, optional validity interval, scope, stream, sequence, previous-event reference, source-schema identity, and optional projection profile/version.

Changing any committed field creates a different content reference.

## Chaining

`sequence` and `previous_event_ref` create tamper-evident ordering inside one declared stream and scope. The chain does not prove that history is complete, that no fork exists, or that deletion is complete.

## Signature

The reference implementation uses Ed25519 and signs:

```text
agent-memory-temporal-event-v1\0 || commitment_ref
```

Ed25519 is an implementation profile, not normative doctrine. The architecture is algorithm-agile.

## Trusted time

Without an external witness, a valid signature proves only signer commitment to the claimed temporal object.

An RFC 3161 or transparency-log witness may bind the exact signature reference and provide independently verifiable time evidence. Witness verification still has `authority_effect = none`.

## UOR

The temporal realization is compatible with the accepted optional UOR-Addr JSON profile shape:

```text
UAX15 NFC + RFC 8785 JCS + SHA-256
```

UOR verifies content identity compatibility only. It is not the signing authority, time source, lifecycle authority, or PAMA authority, and ordinary Agent Memory operation does not require a UOR runtime.

## Dogwood / temporal policy

A temporal-policy adapter may project eligible events into a derived trace while retaining references to these commitments. Dogwood policy evaluation remains downstream evidence. ADR-030 separately determines whether that projection is semantically current for the target policy contract.

## Evidence

- `reference/agentmem_ref/temporal_event_commitment.py`
- `reference/tests/test_temporal_event_commitment.py`
- `schemas/temporal-event-commitment.schema.json`
- `docs/research/cryptographically-committed-temporal-event-identity.md`
- ADR-031
