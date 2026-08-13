# Cryptographically Committed Temporal Event Identity

Status: research under #262. Implementation evidence is tracked by #263.

## Research question

Should an Agent Memory temporal event commit its temporal claims into the cryptographic object identity itself, rather than treating time as mutable metadata adjacent to an otherwise signed payload?

The answer from the current evidence is **yes, with strict separation of responsibilities**.

## Three temporal proofs

The architecture must distinguish:

1. **claimed time**: what the event states about event time, observation time, and validity;
2. **cryptographic order**: where the event sits in a committed stream/chain;
3. **independently witnessed time**: external evidence that a commitment existed by a particular time.

These are not interchangeable.

```text
signed(event_time = T)
!= proof that wall-clock time was T
```

A signature proves that the signer committed to the exact temporal claim. Trusted wall-clock evidence requires an independent witness such as an RFC 3161 timestamp authority or equivalent transparency-log evidence.

## Existing standards

### RFC 8785

JSON Canonicalization Scheme exists specifically to produce an invariant JSON representation suitable for hashing/signing. It is an appropriate provider-neutral canonicalization primitive for a JSON temporal commitment.

### Ed25519

The reference implementation can use Ed25519 as a narrow signing algorithm because the repository already depends on `cryptography`. The normative contract must remain algorithm-agile.

### RFC 3161 and transparency logs

Trusted timestamp evidence is separate from the event signature. A TSA signs evidence over a digest and can establish an independently verifiable time claim. Transparency systems such as Sigstore likewise distinguish artifact/signature identity from signed time/inclusion evidence.

### DSSE lesson

DSSE/in-toto reinforces domain separation: payload type/domain should be authenticated with the payload so signatures cannot be replayed across semantic contexts. Agent Memory should therefore sign a domain-separated temporal content reference, not raw ambiguous bytes.

## UOR bearing

Agent Memory already has an accepted optional UOR-Addr profile proving deterministic content-reference compatibility without importing authority.

This is directly relevant, but UOR's role is narrow:

```text
UOR/content address -> what exact temporal object?
signature           -> who committed to it?
time witness         -> when can existence be independently established?
Agent Memory         -> what does it mean now?
```

The temporal commitment may be compatible with the existing UOR-Addr JSON realization. UOR does not become the signing authority, trust root, lifecycle authority, or PAMA authority.

## Proposed temporal commitment body

The content-addressed object should commit at minimum:

```text
profile/version
event payload digest or typed payload
event type
event_time
observed_at
valid_from / valid_to
scope or stream identity
sequence
previous_event_ref
source/domain schema identity
projection/profile identity where derived
```

The content reference is computed over the canonical commitment body. The signature signs a domain-separated representation of that content reference.

## Chain semantics

A previous-event reference and monotonic sequence create tamper-evident order:

```text
E1
E2(previous = E1, sequence = 2)
E3(previous = E2, sequence = 3)
```

Removing, inserting, or substituting events changes downstream commitments when the chain is verified.

This proves committed order, not complete history. Forks, missing tails, parallel streams, and unobserved events remain possible unless a stronger append-only witness/consensus model is used.

## Currentness remains separate

A cryptographically valid historical event may later be superseded, revoked, corrected, disputed, or outside valid/current time.

```text
signature valid
+
chain valid
+
time witness valid
!= current authority
```

Currentness and PAMA remain separate Agent Memory evidence/consequence layers.

## Dogwood relationship

Dogwood may consume a derived temporal trace containing references to cryptographically committed Agent Memory events. The trace need not carry the full cryptographic envelope if the adapter preserves bindings to the canonical commitment evidence.

Dogwood temporal evaluation then answers policy questions over the projected trace. It does not redefine the cryptographic chain, event currentness, or canonical memory history.

## Adversarial cases

The implementation evidence should demonstrate at least:

1. changing `event_time` changes the content reference and breaks the old signature;
2. changing `observed_at` changes the commitment;
3. changing `valid_from`/`valid_to` changes the commitment;
4. changing payload changes the commitment;
5. changing schema identity changes the commitment;
6. changing scope/stream identity changes the commitment;
7. previous-event substitution is detectable;
8. sequence substitution is detectable;
9. signature from a different key is rejected;
10. valid signature with no external timestamp remains only signer-claimed time;
11. an external timestamp binds the content/signature digest without creating memory authority;
12. replay of a valid signed event into a different stream/scope is rejected because scope/stream is committed;
13. valid historical event whose currentness is revoked remains cryptographically valid but not current;
14. UOR/content-address verification remains `authority_effect = none`;
15. signature verification remains `authority_effect = none`;
16. a temporal chain does not by itself prove deletion completeness or absence of omitted events.

## Decision

The problem is independently falsifiable from ADR-030 and justifies a separate ADR candidate.

ADR-030 asks whether a projection is semantically compatible/current for an external policy consumer.

The new decision asks whether temporal claims should be inside the cryptographically committed event identity and how signer/time/order evidence remain separated from currentness and authority.

## Sources / evidence pins

- UOR-Addr Agent Memory profile: `UOR-Foundation/uor-addr@d78f82f26034880e91b1d54c21900a33ab73f695`, release v0.2.0.
- UOR Framework research pin: `UOR-Foundation/UOR-Framework@51c01382200b0179d6640b07e9c8119364ab69a1`.
- RFC 8785 JSON Canonicalization Scheme.
- RFC 3161 Time-Stamp Protocol.
- in-toto/DSSE envelope principles.
- Sigstore signed timestamp / transparency evidence model.

## Stop lines

- content identity is not authority;
- signature validity is not authority;
- a signer-claimed timestamp is not trusted wall-clock proof;
- external trusted-time evidence is not semantic truth;
- a chain is not lifecycle currentness;
- a chain is not deletion completeness;
- UOR remains optional and does not become a core runtime dependency.
