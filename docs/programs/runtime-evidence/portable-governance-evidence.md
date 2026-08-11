# P4.5a portable memory governance evidence

Status: **Executable reference profile**. This work provides evidence toward proposed ADR-021; it does not accept ADR-020, ADR-021, or ADR-022 and does not raise the repository conformance level.

Parent implementation issue: #63.

## Purpose

P4.5a exports a small, content-free projection of an Agent Memory governance decision so another process can verify integrity and correlate runtime behavior without receiving the raw memory, hidden reasoning, or a signing secret.

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

A valid signature never manufactures PAMA permission. A valid runtime action never proves lifecycle satisfaction.

## Portable evidence v1

Schema: `../../../schemas/portable-governance-evidence.schema.json`.

The v1 projection contains:

- evidence type and version
- canonicalization profile
- issuer ID, key ID, and signature algorithm
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
- signature

It intentionally does **not** contain:

- raw memory content
- hidden reasoning
- the full canonical decision receipt
- tenant/project/domain display names when an opaque reference is sufficient
- a generic `valid: true` field
- a private signing key or shared verification secret

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

The Ed25519 signature covers every evidence field except the `authentication` object itself.

## Reference trust profile

The first executable profile is **Ed25519**, implemented with the Python `cryptography` package.

The additional dependency is intentional. A symmetric HMAC profile would let a verifier forge evidence because verification requires possession of the signing secret; that fails the independent-verification premise of #63. Ed25519 lets the issuer retain the private key while independent verifiers receive only the public trust key.

The profile demonstrates:

- deterministic canonicalization
- issuer/key binding
- public-key verification
- key-validity windows
- key rotation with historical verification
- revocation/distrust timing
- tamper detection
- detached verification after canonical content is no longer supplied

It still does **not** invent:

- a universal PKI
- cross-organization trust discovery
- production key storage
- remote key distribution
- certificate semantics
- automatic online revocation infrastructure

Those are later trust-profile concerns, not memory semantics.

Historical evidence remains verifiable after key rotation when the verifier retains the historical public key and that key was valid at evidence issuance time. A key revoked before issuance cannot produce acceptable new evidence.

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
- execution time
- execution-time authority continuity

Wrong action catches replay against another execution. Wrong policy/authority references expose stale or mismatched decision state. Wrong domain catches an isolation-boundary mismatch without requiring raw domain contents. Execution before the signed decision is rejected.

If execution is observed but execution-time authority continuity is unknown, runtime authorization is reported as `unverifiable`, not optimistically permitted.

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

`binding_failures` is intentionally explicit because a verifier needs to distinguish tampering, unknown trust, replay, stale policy, stale authority, temporal mismatch, and wrong isolation domain rather than flattening them into the same red light.

## Executed vectors

`../../../reference/tests/test_portable_evidence.py` covers:

- deterministic canonicalization
- float rejection
- schema validation of emitted evidence
- successful receipt/action/policy/authority/domain binding
- no raw canonical receipt or memory content in the portable projection
- signature tamper detection
- unknown/untrusted issuer
- replay against a different `action_ref`
- stale/wrong policy reference
- stale/wrong authority-state reference
- wrong source isolation domain
- execution preceding the signed decision
- fail-closed execution when authority continuity is unknown
- valid denial plus unauthorized runtime execution
- authorized deletion with residual lifecycle state
- detached verification after canonical content is unavailable
- wrong canonical receipt
- historical public-key verification across key rotation
- rejection of evidence newly issued after key revocation

Run:

```bash
python -m pip install jsonschema cryptography
python -m unittest discover -s reference/tests -t reference
python scripts/validate_schemas.py
```

## What this slice proves

P4.5a now has an executable substrate-independent boundary for content-free, independently verifiable governance evidence. It demonstrates that Agent Memory can sign and independently check the binding among a canonical receipt reference, decision-time governance state, isolation-domain references, and a runtime action while preserving lifecycle outcome as a separate semantic dimension.

The implementation also demonstrates the core deletion distinction:

```text
valid evidence of authorized deletion != proof of forgetting
```

A correctly signed, authorized, correctly executed delete may still carry `lifecycle_satisfaction = residual`.

## What remains unproven

This slice does not yet prove:

- Agent Manifest checkpoint/delta correlation (P4.5b)
- TRACE/AgenTrust external action-evidence interoperability (P4.5c)
- production key storage or remote trust-anchor discovery
- external revocation infrastructure
- multi-implementation interoperability
- runtime-enforcement composition with AGT or another policy peer
- ADR acceptance or a higher conformance level

Those remain later evidence gates rather than assumptions smuggled into a successful unit test.
