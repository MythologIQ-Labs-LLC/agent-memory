# ADR-031: Temporal claims require deterministic content commitments

- **Status:** Proposed
- **Date:** 2026-08-13
- **Related:** #258, ADR-021, ADR-028, ADR-030

## Context

Agent Memory needs to preserve more than an event payload. Some retained events carry temporal meaning whose later mutation would materially change what happened:

- claimed event time;
- observation time;
- validity interval;
- stream/scope identity;
- predecessor or causal-order references;
- domain-schema identity under which the event was interpreted.

Signing only a payload and attaching time/order metadata afterward leaves those temporal claims outside the cryptographic commitment.

Conversely, putting a timestamp inside a signed object does not make the timestamp trustworthy. It proves only that the signer committed to that temporal claim.

Current standards reinforce a layered model:

- RFC 8785 supports deterministic canonical bytes for hashing/signing;
- RFC 3161 separates trusted timestamp evidence from the object being timestamped;
- RFC 9052 separates signature/data-origin evidence from application semantics;
- RFC 9942 and RFC 9943 separate signed statements from verifiable inclusion/consistency receipts;
- Sigstore bundles similarly compose signature verification material with transparency/timestamp evidence.

Agent Memory already has an optional UOR-Addr v0.2.0 content-reference profile proving cross-language JSON content identity while preserving `authority_effect = none`.

## Decision candidate

Adopt a **layered temporal commitment model**.

Temporal claims whose mutation must create a different historical event identity belong inside a deterministic content commitment.

Signer attestation, ordering evidence, and external time/transparency evidence remain separate evidence layers bound to that exact commitment.

```text
TemporalCommitment
  deterministic content identity
        |
        v
SignerAttestation
  who endorsed the exact commitment
        |
        v
optional ExternalWitnessEvidence
  existence / inclusion / consistency / freshness
        |
        v
Agent Memory trust/currentness/PAMA evaluation
```

## Core invariant

> **Cryptography may make a temporal claim tamper-evident without making the claim true, current, trusted, complete, or authorized.**

```text
content identity != signature
signature != trusted time
trusted time != event occurrence time
predecessor chain != complete global history
cryptographic validity != memory authority
```

## Temporal commitment

A commitment profile must define deterministic serialization/addressing and the exact fields included in the historical commitment.

The generic shape may include:

```text
profile identity
canonical event payload/reference
temporal claims
ordering profile + predecessor refs
scope / isolation ref
domain-schema identity
projection/profile identity where applicable
```

Changing any committed field produces a different content identity.

The canonical doctrine does not require one content-address implementation.

The initial optional interoperability profile may use the existing UOR-Addr v0.2.0 JSON realization.

## UOR boundary

UOR may answer:

> **What exact canonical temporal object is being referenced?**

UOR does not answer:

- who signed it;
- whether the signing key is trusted;
- whether a claimed time is accurate;
- whether the event is current;
- whether history is complete;
- whether a mutation/action is authorized.

Ordinary Agent Memory conformance does not require a UOR runtime.

## Signer attestation

The signer attests to a domain-separated transcript binding at least:

```text
attestation profile/version
content-reference profile
content_ref
```

The signing algorithm and key-identification mechanism are implementation/profile concerns.

The first reference evidence may use Ed25519 through the existing Python `cryptography` dependency. That choice is not normative doctrine.

Key trust, rotation, revocation, and authorization are evaluated separately from historical signature validity.

A signature may remain cryptographically valid after the signer loses current authority.

## Claimed time versus witnessed time

A signed temporal commitment may contain a claimed `event_time` or `observed_at`.

A valid signature proves only that the signer committed to those values.

An independent time/transparency profile may bind separate evidence to the commitment or signer attestation, for example:

- RFC 3161 timestamp token;
- SCITT/COSE receipt;
- Sigstore-style transparency evidence;
- another deployment-specific witness.

Witness evidence must state exactly what it proves.

```text
witnessed existence by T
!= event occurred at T
```

## Ordering evidence

A strictly serialized stream may commit to:

```text
stream_ref
sequence
predecessor_ref
```

or another declared equivalent.

This makes local order tamper-evident because changing the predecessor/order fields changes the descendant commitment identity.

However:

```text
hash/predecessor chain
!= proof of completeness or non-equivocation by itself
```

A verifier that needs stronger history claims must have an appropriate anchor, authoritative head, consistency proof, coordinator receipt, or verifiable-data-structure receipt.

## Concurrent / multi-writer history

Core must not impose a fake total order over concurrent writers.

A profile may instead use:

- multiple causal predecessor refs;
- shared-write coordination receipts;
- external ordered-log/VDS receipts;
- coordinator-issued sequence evidence.

The profile must state which ordering property it proves.

This ADR does not replace shared-memory pre-write coordination or PAMA.

## Corrections and currentness

A signed historical commitment is append-only evidence.

Later correction, revocation, dispute, or supersession creates new governed evidence/currentness rather than rewriting the signed object.

```text
E1 signed historical commitment
E2 correction/supersession references E1
currentness(E1) -> no longer current
```

Cryptographic immutability does not waive retention/deletion obligations for known copies, signatures, receipts, or projections.

## Policy projection

A temporal/policy consumer such as Dogwood may receive a derived projection carrying only the verified claims it needs.

```text
Agent Memory temporal commitment
!= Dogwood trace entry
```

A cryptographically valid event may still be stale, revoked, superseded, out of scope, or non-authoritative for current policy.

ADR-030 compatibility/currentness still applies before consequential policy use.

## Authority boundary

Every layer has `authority_effect = none` unless a separate Agent Memory authority evaluation explicitly says otherwise.

Neither a content-reference match, valid digital signature, predecessor chain, trusted timestamp, inclusion receipt, nor transparency receipt independently establishes:

- memory admission;
- factual truth;
- current applicability;
- human approval;
- reusable grant;
- PAMA permission;
- enforcement/execution.

## Acceptance evidence required

ADR-031 MUST remain Proposed until executable evidence demonstrates at least:

1. payload mutation changes commitment identity;
2. temporal-claim mutation changes commitment identity;
3. predecessor/order mutation changes commitment identity;
4. schema/profile mutation changes commitment identity;
5. a signature is bound to the exact commitment/profile and fails after reference mutation;
6. a valid signature over a false/future claimed time remains distinguishable from trusted-time evidence;
7. an unknown/untrusted signer can remain cryptographically valid without gaining authority;
8. a required predecessor missing/cross-scope is detected;
9. a fork is represented as a fork rather than silently flattened;
10. a linear predecessor chain is not reported as complete/non-equivocating without an anchor/receipt;
11. later correction/currentness change does not rewrite the signed historical commitment;
12. UOR/content identity cannot satisfy PAMA;
13. external witness evidence with the wrong subject is rejected;
14. witness time is not relabeled as event occurrence time;
15. optional UOR unavailability fails only that optional profile path;
16. at least one exact-pinned UOR-Addr v0.2.0 temporal-object comparator proves the generic contract without importing UOR authority semantics into core.

## Rejected alternatives

### Sign the event payload and leave time/order outside the commitment

Rejected. Material temporal claims could change without invalidating the signature binding.

### Treat a signed timestamp as trusted wall-clock time

Rejected. The signer proves commitment to the claimed value, not clock truth.

### Make UOR the signing or authority system

Rejected. UOR content identity is useful precisely because it can remain narrower than signer trust and Agent Memory authority.

### Treat a predecessor hash chain as a complete global ledger

Rejected. Without an anchor/consistency/non-equivocation mechanism, a chain alone cannot prove the verifier has the unique complete history.

### Require a single timestamp/transparency provider

Rejected. External witness services are optional profiles behind a generic verified-evidence boundary.

### Rewrite old signed events when corrected

Rejected. Corrections and currentness remain append-only governance evidence.

## Initial implementation

The first executable slice should be Python-first and provider-neutral:

1. temporal commitment schema;
2. signer-attestation schema;
3. external-witness-evidence schema;
4. deterministic reference builder/verifier;
5. Ed25519 reference profile for evidence only;
6. optional exact-pinned UOR-Addr v0.2.0 address function;
7. linear-stream ordering profile with explicit completeness non-claim;
8. adversarial test vectors and focused CI artifact;
9. no production TSA, SCITT service, Dogwood integration, or UOR core dependency in this slice.

## Related

- #67
- #258
- ADR-021
- ADR-022
- ADR-024
- ADR-028
- ADR-030
- `docs/profiles/uor-addr-content-reference-profile.md`
- `docs/research/cryptographic-temporal-commitments.md`
