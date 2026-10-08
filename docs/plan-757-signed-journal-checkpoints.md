# #757 — Signed journal checkpoint qualification (J15–J26)

**Preregistered on 2026-10-08, before implementation.** Experimental evaluator-only work. This is a proof of a *signed chain-head binding*, not a proposition-identity solution, production issuer-verification service, temporal currentness proof, or a v7 baseline.

## Prior gap

The #757 J01–J14 journal stores proposed/withdrawn/disputed identity evidence and rejects in-process concurrent forks, but its SHA-256 chain can be rewritten and rehashed in full. Our next question is narrower than semantic identity: can a verifier, given an independently pinned public-key digest and a separately pinned **exact journal head and sequence**, detect substitution, truncation, incorrect stream, or signer/key confusion?

A cryptographic signature attests **the specific checkpoint bytes** and possession of a private key. It does not attest truth, authority, semantic property equivalence, source independence, absence of a newer journal, trustworthy time, or that a source was entitled to assert the relationship.

## Fixed contract before code

Implement a detached, domain-separated Ed25519 checkpoint in `reference/agentmem_ref/evaluation`, using the existing cryptography dependency and native public-key digest utility. The caller supplies a private key to sign the current replayed head and a key reference. Verification is offline, takes an **independently expected** stream, head and event count, and an independently supplied **exact pinned public-key digest**. All these expectations originate outside the checkpoint. Their source is not authenticated by this evaluator.

### J15–J26 preregistered invariants

- **J15:** Sign exact contract/version, stream, count, chain head, key reference and algorithm under a non-reusable domain separator.
- **J16:** Verify cryptographic signature using the supplied key without accepting embedded public keys or self-declared signer-trust status.
- **J17:** Independently specified expected stream, head and event count must match the actual replayed journal *and* signed payload; changing any binding fails.
- **J18:** Require independently supplied key-material pin, not a key or digest derived from the signed receipt, with exact key-reference match.
- **J19:** Revoked, unknown or unavailable trust roots, unverified issuer/tenant authorization, and unknown freshness **remain unestablished** even for a valid signature.
- **J20:** Valid signature and exact chain integrity cannot assert `same_property`, authorize supersession, change memory, emit active currentness, or verify signer organizational authority.
- **J21:** Reordered, omitted, shortened or rehashed journal histories fail binding to the previously pinned checkpoint head/count.
- **J22:** Signature substitution using another key, malformed signature/base64, forged key reference, alternate stream or cross-contract replay fails.
- **J23:** Signature/transcript canonicalization is deterministic and strict for all bound attributes. Do not sign raw mutable Python objects.
- **J24:** Replay corruption remains a failure even if supplied signature material looks valid; journal report is recomputed from events.
- **J25:** A checkpoint is not a durability layer; importing checkpoint material never writes a journal event or modifies any runtime state.
- **J26:** Public verifier output separates `cryptographic_status`, `head_binding_status`, `key_pin_status`, `authenticated_issuer` (always false), `semantic_identity_verified` (always false), and `authority_effect=none`.

## Independent adversarial challenges

Use opaque synthetic proposals only, **never #732/MESA scored text or gold**. Deliberately:

1. Independently pin a two-event journal, then truncate to one event.
2. Rewrite one proposal and rehash the entire chain, then show an old checkpoint does not bind.
3. Sign a different stream and try to replay it as this stream.
4. Sign with a second key, reuse or forge the first key reference/pin.
5. Corrupt signature encoding, algorithm, contract version and signed fields.
6. Supply a valid signature but a wrong externally expected count, stream or head.
7. Retain a valid historical checkpoint after adding a new event. It must not establish freshness or bind a *new* checkpoint head.
8. Change a negative resolution or its evidence while preserving an old checkpoint.
9. Verify deterministic canonical content and no mutation of the journal.
10. Leave the trust root or pin empty, revoked, unknown or self-asserted and ensure it cannot yield an authenticated issuer or memory authority.

## What is explicitly not tested or proven

This does NOT prove that two natural-language extractions refer to the same property. This is also not a certified hardware key, cross-machine trust distribution mechanism, proof of publication time, revocation oracle, issuer verification, key management service or accepted security protocol. A malicious actor who can replace both the history *and the independently pinned head/key* can still deceive the verifier.

A later v7 design must qualify actual independent issuer/authentication roots, revocation, same-property ontology, and scoped authority separately, together with frozen holdout and baseline succession. Do not import AGT/TRACE/PrismPM/UOR as required runtime dependencies merely for this test. Review the historical ancestry in `docs/research/cryptographic-proposition-identity-ancestry-2026-10-08.md`.
