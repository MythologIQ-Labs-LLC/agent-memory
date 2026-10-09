# #757 — Exact write-revision source/actor witness binding (J73–J88)

**Preregistered: 2026-10-08, before evaluator implementation.**
**Scope:** bounded evaluation-only synthetic attestation qualification; stacked *after* draft PRs #763 and #764. No production source authorization, signed trust-root distribution, semantic-identity relation, inference, currentness, PAMA or runtime change.

## General capability and threat

A structurally plausible cross-write property link can carry arbitrary textual `actor_ref`, `source_ref`, `fact_ref` and `revision_ref`. Even a signed schema or issuer policy does not establish which party actually emitted each observed write. One extractor could fabricate two apparently independent claims.

The next layer must bind **claimed provenance** to **exact, typed observation bytes**, with distinct actor/source witness roles, explicit side (older/newer) and separately supplied key-material pins. Verify the same scope, fact, revision and observation values that were evaluated by the proposition-link preflight. It must refuse substitutions, not silently fall back to unverified strings.

Each signed claim commits to its own **actor** or **source** role and to one observed write. A caller provides its claimed signer public key and separately configured expectations for that role/side/principal/key ref/key material. Four exact expected positions (older actor, older source, newer actor, newer source) must be mechanically checked before producing a *cryptographically-bound provenance candidate*.

The provision of four witnesses does **not** prove independent persons, systems, authorial control or delegated authority: an attacker can own four keys and their corresponding "independent" pins. The result MUST NOT say `origin_verified`, `issuer_authorized`, `identity_verified` or `can_supersede`.

## Preregistered invariants

| ID | Contract |
| --- | --- |
| J73 | Canonical Ed25519 transcript binds profile/version/algorithm, older/newer side, actor/source kind, claimed principal, claimed signer key ref and **all** fields of one typed observed write. |
| J74 | A detached signature verifies using a supplied public key and canonical strict base64; signature-valid alone confers no principal authority. |
| J75 | Expected key-material digest, key ref, principal ref and exact actor/source role are provided separately; any mismatch refuses. |
| J76 | The committed write must match the exact older/newer `ObservedWrite` provided to preflight, including fact/revision, scope, actor/source, property/value, cardinality/lifecycle and coexistence. |
| J77 | A witness claimed as actor must bind `observed.actor_ref`; source must bind `observed.source_ref`. Role substitution is invalid. |
| J78 | All four role/side positions are required for a full mechanical candidate; absent evidence abstains. Duplicate positions, unrecognized roles and extra witnesses refuse. |
| J79 | Existing proposition structural preflight refusal cannot be bypassed by signatures, attestation counts or claimed signer independence. |
| J80 | Canonical payloads remain bounded. Wrong typing, malformed witnesses, noncanonical signatures and after-construction tampering are refused without side effects. |
| J81 | Reordering unique witnesses cannot change the result; repeated calls are deterministic and immutable. |
| J82 | Key diversity is merely an observation and never independent corroboration of principal control. Even four attacker-owned valid signed roles remain untrusted. |
| J83 | No inference or textual/synonym matching, heuristic alias, old-value equality or benchmark-specific phrase dictionary. |
| J84 | Witnesses do not grant property ontology authority, schema grant authority, cross-write semantic identity, recall or mutation. |
| J85 | Cross-tenant, scope/purpose and stale-head preflight refusals dominate otherwise valid witness signatures. |
| J86 | Verification must allow legitimate same-actor/same-source observations but never describe repeated claims as independent evidence. |
| J87 | No changes to protected runtime, v6, #732/R6 held evidence, PAMA, journal acceptance semantics or external provider usage. |
| J88 | Every receipt explicitly states `authority_effect=none`, `principal_authenticated=false`, `origin_independence_verified=false`, `identity_verified=false`, `can_supersede=false` and `mutates_memory=false`. |

## Independent challenge families, specified before code

- Fully matching synthetic actor/source witnesses for two distinct write revisions.
- Swapped older/newer side, actor/source role, fact/revision, subject, source, actor, value, cardinality, lifecycle, tenant, purpose and scope.
- Changed key without changed pin; changed key and attacker-controlled pin; forged or malformed signature; bad transcript profile/version.
- Missing role, duplicate role and fifth forged witness.
- Unrelated same-value facts; two valid roles signed by the same key; four attacker-controlled keys that all match their own attacker-controlled pins.
- Permuted witness order, duplicate claimed origin invocation, repeated deterministic verification, immutable receipts.
- Structural refusal: stale head, cross-tenant, multi/coexistent, identical value, tombstone/dispute.
- Explicitly distinguish a cryptographic witness candidate from authenticated origin, true independent corroboration or an authorized update.

## Completion and governance

Implement only under `reference/agentmem_ref/evaluation/` plus synthetic tests and docs. Use native Ed25519/canonical JSON. No service credentials or runtime dependency. Require exact-head CI and independently generated adversarial cases before merge. Keep this as a DRAFT stacked PR until #763 and #764 are individually reviewed, merged and the branch is rebased. Keep #757 open.

**Next trust frontier after this layer:** a domain-owned, externally authenticated principal/credential delegation and revocation mechanism, real source receipt attestation, and adjudication of mistaken property-identity links. These cannot be generated merely by having one model sign four messages.
