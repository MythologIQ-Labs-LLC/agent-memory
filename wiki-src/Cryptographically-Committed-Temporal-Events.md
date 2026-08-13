# Cryptographically Committed Temporal Events

A temporal event can be signed without proving very much about time. Agent Memory therefore treats **temporal identity**, **signer commitment**, **trusted time**, and **current authority** as separate evidence layers.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/temporal-event-commitment-light.svg">
  <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/temporal-event-commitment.svg" alt="Flow from an Agent Memory temporal event through canonicalization and content addressing, digital signature, optional independent time witness, currentness and PAMA evaluation, and finally a derived temporal-policy projection. The diagram emphasizes that content identity, signature validity, witnessed time, and current authority are distinct claims.">
</picture>

## The core idea

The time fields are inside the cryptographic commitment.

```text
payload + event_time + observed_at + validity
+ scope + stream + sequence + previous event
+ schema identity
        |
        v
canonical temporal object
        |
        v
content reference
        |
        v
signature
```

If somebody changes the event time, stream, sequence, predecessor, schema, scope, or payload digest, the content reference changes and the old signature no longer applies.

That is stronger than signing a payload and attaching an editable timestamp beside it.

## Three different temporal claims

### Claimed time

The signed object can state when the event happened, when it was observed, and when it is valid.

A valid signature proves the signer committed to those claims. It does **not** independently prove the wall clock.

### Cryptographic order

A stream can chain events using `sequence` and `previous_event_ref`.

```text
E1
E2(previous=E1)
E3(previous=E2)
```

Mutation or substitution breaks downstream linkage. The chain still does not prove that no event was omitted, that no fork exists, or that every copy was deleted.

### Witnessed time

An independent timestamp authority or transparency log may attest that the exact signed commitment existed by a particular time.

This creates stronger time evidence, but still does not make the event true, current, admitted, or authorized.

## UOR's role

UOR is useful here because the accepted optional UOR-Addr profile gives Agent Memory a language-neutral way to compare exact content identity.

```text
UOR/content reference -> what exact temporal object?
signature              -> who committed to it?
time witness            -> when was existence independently witnessed?
Agent Memory            -> what does it mean now?
```

UOR does not become a signing authority, key manager, clock, lifecycle authority, or PAMA authority.

## Currentness stays separate

A historical event can remain cryptographically valid forever while becoming irrelevant or invalid for current action.

```text
signature valid
chain valid
trusted timestamp valid
        !=
currently applicable memory
```

Correction, supersession, revocation, dispute, scope changes, and schema/currentness changes remain ordinary Agent Memory lifecycle evidence.

## Dogwood relationship

Dogwood or another temporal-policy engine can consume a derived event trace that refers back to these cryptographic commitments.

The responsibilities remain separated:

```text
Agent Memory committed event history
        |
        v
ADR-030 compatible temporal projection
        |
        v
Dogwood temporal trace / policy
        |
        v
external policy-decision evidence
```

Dogwood does not become the canonical history store. Agent Memory does not become Dogwood's policy engine.

## Why the signature has a domain

The reference implementation signs a domain-separated message:

```text
agent-memory-temporal-event-v1\0 || commitment_ref
```

This prevents the same signature bytes from being casually reinterpreted as a different kind of signed statement.

The first reference implementation uses Ed25519. The architecture itself is algorithm-agile.

## Evidence boundaries

Hard invariants:

```text
content identity != authority
signature validity != authority
signed time != trusted time
trusted time != semantic truth
chain continuity != complete history
chain continuity != deletion completeness
cryptographic validity != currentness
```

## Canonical references

- `docs/adr/ADR-031-temporal-claims-belong-inside-cryptographic-event-commitment.md`
- `docs/profiles/temporal-event-commitment-profile.md`
- `docs/research/cryptographically-committed-temporal-event-identity.md`
- `reference/agentmem_ref/temporal_event_commitment.py`
- `schemas/temporal-event-commitment.schema.json`
- [Temporal Policy and Governed Memory](Temporal-Policy-and-Governed-Memory)
- [Governance Projection](Governance-Projection)
