# External Trust and Attestation Evidence Normalization Profile

## Status

Reference V0.1 implementation profile for issue #180.

## Purpose

This profile defines the smallest vendor-neutral boundary for accepting external identity, trust, attestation, decision, enforcement, execution, runtime, or delegation evidence as an Agent Memory evidence candidate without importing peer authority.

The core invariants are:

```text
payload parsed
!= signature / claim verified
!= claim current
!= claim applicable to this subject/action/scope
!= Agent Memory authority
```

and:

```text
verified identity
!= memory authority

valid attestation
!= semantic correctness

policy / decision evidence
!= enforcement evidence

execution evidence
!= lifecycle obligation satisfaction
```

The normalizer exists to preserve those distinctions in executable form.

## Layering

```text
peer-specific record
  -> peer adapter / verifier result
  -> vendor-neutral external evidence normalizer
  -> Agent Memory evidence candidate
  -> normal provenance / scope / lifecycle / PAMA handling
```

The reference implementation begins at the adapter/verifier-result boundary. It does not parse arbitrary peer wire formats and does not perform peer cryptography itself.

That split is intentional. A peer adapter may understand peer vocabulary and wire details. Canonical Agent Memory evidence semantics must not.

## Pinned V0.1 reference peer

TRACE is the first reference comparator because the repository already has executable TRACE/cMCP evidence work and an exact release pin.

V0.1 recognizes only this pinned source tuple as supported evidence input:

```text
peer:                TRACE
TRACE SDK:           agentrust-trace==0.8.0
TRACE release ref:   671f2a8b22f1c995798a0c6d711b4b0b77dad4c7
reference contract:  TRACE action-receipt verification / external action-evidence surface
```

This reuses the existing P4.5c pin documented in `docs/programs/runtime-evidence/trace-action-evidence.md`.

TRACE remains a comparator. It is not a required Agent Memory runtime dependency and does not define Agent Memory vocabulary.

A different TRACE version, release ref, or unsupported peer is preserved as source metadata but receives `applicability.status = unsupported` until a later implementation explicitly validates that version.

## Adapter/verifier input boundary

The normalizer consumes a bounded result containing the facts needed for evidence interpretation, including:

```text
parse_status
source_peer
source_version
source_release_ref
record_ref
evidence_digest
adapter_id / adapter_version
issuer_id / signer_id
verifier_id
verification_status
verification_method
claim_type
claim_scope
subject_ref
tenant_ref
resource_ref
action_ref
runtime_ref
configuration_ref
policy_ref
decision_ref / decision_disposition
enforcement_posture
execution_posture
attestation_mode
delegation_ref
issued_at / expires_at
revocation_status / revocation_evidence_ref
evidence_refs
explicit limitations / non-claims
```

The input is not automatically durable state. It is material supplied to the normalizer by a peer-specific adapter or verifier.

Unknown peer-only fields are ignored. In particular, a peer cannot widen Agent Memory authority by adding fields that resemble:

```text
pama_outcome
permitted_actions
lifecycle_state
trust_score
```

Those fields do not enter the normalized output.

## Normalized evidence candidate

Schema:

`schemas/external-evidence-normalized.schema.json`

Reference implementation:

`reference/agentmem_ref/external_evidence.py`

The normalized candidate contains distinct surfaces for:

```text
source provenance
issuer / signer identity
verification state
claim identity and scope
freshness
revocation
current-context applicability
stable evidence digest / references
explicit interpretation non-claims
```

The V0.1 interpretation block is deliberately fixed:

```json
{
  "authority_effect": "none",
  "memory_authority": "not_established",
  "semantic_correctness": "not_established",
  "lifecycle_satisfaction": "not_established"
}
```

A consumer that needs to make an Agent Memory mutation decision must still use normal Agent Memory provenance, trust, scope, lifecycle, and PAMA logic. The normalized evidence candidate is evidence input, never a bypass token.

## Verification state

Verification remains explicit:

```text
verified
failed
unknown
not_performed
unavailable
```

Schema-valid or successfully parsed evidence is never promoted to `verified` by the normalizer.

A failed verification produces an invalid applicability result.

Unknown, not-performed, or unavailable verification produces insufficient evidence rather than optimistic acceptance.

## Freshness and revocation

Freshness and revocation are independent dimensions.

Freshness:

```text
current
expired
not_yet_valid
```

Revocation:

```text
not_revoked
revoked
unknown
```

Expired or revoked evidence is stale even when its historical signature remains valid.

Unknown revocation state remains unknown and prevents V0.1 from reporting the evidence as fully applicable.

Historical evidence may remain reconstructable after expiry or revocation. That historical reconstructability is not current authority.

## Applicability

The normalizer compares evidence binding against the current Agent Memory context supplied by the consumer.

V0.1 supports:

```text
applicable
mismatch
stale
unsupported
insufficient_evidence
invalid
```

At minimum, the current context can bind:

```text
subject_ref
scope
tenant_ref
resource_ref
action_ref
```

When the current context requires a binding and the evidence omits it, V0.1 reports a mismatch rather than assuming equivalence.

Examples:

```text
verified signature + wrong scope       -> mismatch
verified signature + wrong tenant      -> mismatch
verified signature + wrong action      -> mismatch
verified + expired                      -> stale
verified + revoked                      -> stale
unknown verification                    -> insufficient_evidence
failed verification                     -> invalid
unsupported TRACE version               -> unsupported
exact/current/verified/not-revoked      -> applicable
```

`applicable` means the evidence is applicable as evidence to the supplied context. It does not mean the underlying memory action is authorized.

## Claim-layer separation

The normalized claim may preserve independently supplied references or postures for:

```text
decision
enforcement
execution
runtime / configuration
identity / attestation
delegation
```

The normalizer does not manufacture missing layers.

For example, a valid decision record with no enforcement or execution claim remains decision evidence only. A runtime/configuration attestation remains evidence about runtime/configuration identity and does not become semantic correctness.

## Privacy and minimization

V0.1 defaults to stable references and digests.

The normalized output does not require:

- raw prompts;
- raw memory content;
- full tool payloads;
- complete peer attestation bundles;
- peer signatures when a stable evidence digest/reference is sufficient for custody or later verification;
- peer-only authority vocabulary.

The source record remains independently referencable through `record_ref` and `evidence_digest` when policy permits retention or retrieval.

## Deployment profiles

### L: local / single-user / offline

The normalizer has no network requirement. A local caller may supply static or pre-verified adapter results. Unknown verification remains unknown rather than being silently upgraded because the deployment is local.

### T: team / multi-tenant

`subject_ref`, `scope`, and `tenant_ref` remain explicit. Cross-tenant evidence mismatches fail deterministically.

### E: enterprise

The verifier identity and verification method are explicit, allowing external attestation or identity services to supply verifier results without becoming mandatory core dependencies.

### H: high assurance

Peer/release version, verifier identity, freshness, revocation, exact context binding, evidence digest, and explicit non-claims remain reconstructable.

### X: cross-organization

Cross-organization delegation semantics are not a V0.1 completion target. A `delegation_ref` may be preserved as evidence, but it does not create delegated Agent Memory authority.

## Required negative paths

The executable fixture matrix covers:

- verified evidence with wrong scope;
- cross-tenant mismatch;
- wrong action binding;
- expired evidence;
- revoked evidence;
- unknown verification;
- verifier unavailable;
- failed verification;
- unknown revocation state;
- unsupported TRACE version;
- unsupported peer claim type;
- decision evidence without enforcement/execution claims;
- peer-only fields attempting to inject PAMA, lifecycle, or trust-score semantics;
- malformed/unparsed peer evidence;
- missing required current-context binding.

Fixture:

`fixtures/external-evidence-normalization-matrix.json`

Tests:

`reference/tests/test_external_evidence.py`

## What V0.1 proves

Within the bounded reference implementation and fixtures, V0.1 demonstrates that:

- external trust/attestation evidence enters through an explicit vendor-neutral normalization boundary;
- TRACE version and release provenance remain reconstructable;
- parsing, verification, freshness, revocation, and applicability remain distinct;
- verified evidence cannot itself create Agent Memory authority;
- wrong-scope and cross-tenant evidence cannot become applicable silently;
- decision evidence is not upgraded into enforcement/execution evidence;
- runtime/configuration attestation does not establish semantic correctness;
- raw peer payloads are unnecessary for the normalized candidate;
- unknown peer fields cannot widen PAMA or mutate canonical lifecycle state;
- removing the peer adapter leaves the normalized evidence contract understandable as generic evidence metadata.

## What V0.1 does not prove

V0.1 does not prove:

- that TRACE or another peer is universally trustworthy;
- production key discovery, rotation, revocation, or trust-anchor policy;
- semantic correctness of an attested claim;
- Agent Memory mutation authorization;
- downstream enforcement merely because a decision exists;
- physical execution merely because an attestation exists;
- correction, deletion, forgetting, or other lifecycle obligation satisfaction;
- cross-organization delegation authority;
- compatibility with future TRACE versions or other peers;
- a need for a TRACE core-schema change.

## Rollback / disable behavior

The normalizer and all peer adapters are optional evidence surfaces.

Disabling or removing the TRACE adapter does not invalidate canonical Agent Memory records. Existing normalized records remain understandable through the vendor-neutral schema and retain their source/version/reference metadata.

No canonical memory object requires TRACE-only vocabulary to remain interpretable.

## Follow-on gate

Only after this V0.1 boundary is stable should a second materially different peer be added. cMCP or Agent Manifest are reasonable next comparators because their evidence semantics differ enough to test whether the generic contract actually generalizes.

A second peer should expose real incompatibilities before this profile gains additional canonical fields. Speculative breadth is not evidence.
