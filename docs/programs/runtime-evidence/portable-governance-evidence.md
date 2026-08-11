# P4.5a portable memory governance evidence

Status: **Executable reference profile**. This work provides evidence toward proposed ADR-021; it does not accept ADR-020, ADR-021, or ADR-022 and does not raise the repository conformance level.

Parent implementation issue: #63.

## Purpose

P4.5a exports a small, content-free projection of an Agent Memory governance decision so another process can verify integrity and correlate runtime behavior without receiving the raw memory or taking ownership of Agent Memory semantics.

The ownership boundary remains:

```text
canonical Agent Memory receipt
        |
        | content-free projection
        v
portable governance evidence
        |
        | independent observations
        v
verifier result
```

The canonical receipt remains authoritative. The portable object is evidence about it, not a replacement for it.

## Non-escalation invariant

The verifier deliberately emits four separate outcome dimensions:

```text
evidence integrity/binding
governance disposition
runtime execution
lifecycle satisfaction
```

Therefore all of these are representable without contradiction:

```text
valid evidence + denied + unauthorized execution
valid evidence + committed + executed as authorized + residual
valid evidence + committed + executed as authorized + satisfied
```

A valid authentication result never manufactures PAMA permission. A valid runtime action never proves lifecycle satisfaction.

## Portable evidence v1

Schema: `schemas/portable-governance-evidence.schema.json`.

The v1 projection contains:

- evidence type and version
- canonicalization profile
- issuer ID, key ID, and authentication algorithm
- issuance time
- runtime `action_ref`
- memory action class/name
- SHA-256 reference to the canonical decision receipt
- governance disposition
- policy reference
- decision-time authority-state reference
- decision time
- privacy-safe scope reference
- optional source/destination isolation-domain references
- optional domain-authorization-state reference
- before/after state references
- lifecycle result
- authentication tag

It intentionally does **not** contain:

- raw memory content
- hidden reasoning
- the full canonical decision receipt
- tenant/project/domain display names when an opaque reference is sufficient
- a generic `valid: true` field

Low-entropy tenant, user, project, repository, and isolation-domain names should not be converted to plain unsalted hashes and treated as private. Callers should supply opaque IDs or keyed/privacy-preserving references where disclosure would matter.

## Canonicalization

`agent-memory-canonical-json-v1` is:

- UTF-8 JSON
- object keys sorted lexicographically
- no insignificant whitespace
- non-ASCII text preserved
- floating-point values prohibited

The float prohibition is intentional. Cross-runtime numeric canonicalization is not necessary for this first contract and should not be smuggled in as an accidental interoperability claim.

The canonical receipt reference is:

```text
sha256:<hex sha256 of canonical receipt JSON>
```

The portable object's authentication covers every evidence field except the `authentication` object itself.

## Reference trust profile

The first executable profile is `HMAC-SHA256` using Python's standard library.

This is a deliberately small **symmetric trust-domain profile**. It demonstrates deterministic canonicalization, issuer/key binding, trust configuration, key validity windows, rotation, distrust/revocation timing, tamper detection, and detached verification without adding a crypto dependency to the reference implementation.

It does **not** provide:

- public verifiability
- asymmetric issuer identity
- non-repudiation
- a universal PKI
- cross-organization trust discovery

Those are future profile concerns. The wire contract names the algorithm explicitly so a later Ed25519 or other asymmetric profile can be introduced without redefining memory semantics.

Historical evidence remains verifiable after key rotation when the verifier retains the historical trust key and the key was valid at evidence issuance time. A key revoked before issuance cannot produce acceptable new evidence.

## Receipt resolution and forgetting

A verifier can operate in three relevant states:

`resolved`
: The canonical receipt is available and its canonical hash matches the signed reference.

`detached`
: The canonical content is not supplied, but the portable evidence remains cryptographically verifiable. This is the reference path for content-bearing canonical state that was legitimately pruned while content-free verification evidence remains.

`mismatch`
: A supplied canonical receipt does not match the signed receipt reference.

Detached verification is not proof that deleted memory content still exists. Conversely, inability to resolve pruned content is not automatically invalid evidence.

## Binding checks

The reference verifier can compare signed evidence to independently observed runtime facts:

- action reference
- policy reference
- authority-state reference
- source isolation domain
- destination isolation domain
- execution-time authority continuity

Wrong action catches replay against another execution. Wrong policy/authority references expose stale or mismatched decision state. Wrong domain catches an isolation-boundary mismatch without requiring raw domain contents.

If an execution time is supplied but execution-time authority continuity is unknown, runtime authorization is reported as `unverifiable`, not optimistically permitted.

## Machine-readable result taxonomy

`verify_evidence()` returns:

```json
{
  "evidence_integrity": "valid | invalid | unverifiable",
  "binding_failures": [],
  "receipt_resolution": "resolved | detached | mismatch | unresolved",
  "governance_disposition": "permitted | denied | deferred | review_required | committed | unverifiable",
  "runtime_execution": "executed_as_authorized | not_executed | execution_mismatch | unauthorized_execution | unverifiable",
  "lifecycle_satisfaction": "satisfied | residual | incomplete | unverifiable | not_applicable"
}
```

`binding_failures` is intentionally explicit because a verifier needs to distinguish tampering, unknown trust, replay, stale policy, stale authority, and wrong isolation domain rather than flattening them into the same red light.

## Executed vectors

`reference/tests/test_portable_evidence.py` covers:

- deterministic canonicalization
- float rejection
- successful receipt/action/policy/authority/domain binding
- no raw canonical receipt or memory content in the portable projection
- tamper detection
- unknown/untrusted issuer
- replay against a different `action_ref`
- stale/wrong policy reference
- stale/wrong authority-state reference
- wrong source isolation domain
- valid denial plus unauthorized runtime execution
- authorized deletion with residual lifecycle state
- detached verification after canonical content is unavailable
- wrong canonical receipt
- historical verification across key rotation
- rejection of evidence newly issued after key revocation

Run:

```bash
python -m unittest discover -s reference/tests -t reference
python scripts/validate_schemas.py
```

## What this slice proves

P4.5a now has an executable substrate-independent boundary for content-free portable governance evidence. It demonstrates that Agent Memory can authenticate and independently check the binding among a canonical receipt reference, decision-time governance state, isolation-domain references, and a runtime action while preserving lifecycle outcome as a separate semantic dimension.

The implementation also demonstrates the core deletion distinction:

```text
valid evidence of authorized deletion != proof of forgetting
```

A signed, correctly executed delete may still carry `lifecycle_satisfaction = residual`.

## What remains unproven

This slice does not yet prove:

- Agent Manifest checkpoint/delta correlation (P4.5b)
- TRACE/AgenTrust external action-evidence interoperability (P4.5c)
- asymmetric or publicly verifiable trust
- production key storage or remote key discovery
- external revocation infrastructure
- multi-implementation interoperability
- runtime-enforcement composition with AGT or another policy peer
- ADR acceptance or a higher conformance level

Those remain later evidence gates rather than assumptions smuggled into a successful unit test.
