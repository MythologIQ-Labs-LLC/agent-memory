# #757 — Independently pinned issuer-policy and revocation qualification (J42–J56)

**Preregistered 2026-10-08 before implementation.** Evaluation-only continuation of merged PR #762. Neither a trusted root-distribution service nor a runtime authorization API. No R6/#732 benchmark data or v6 runtime changes.

## General capability

A signed property registry demonstrates that an Ed25519 key committed to a particular schema. It does not demonstrate that the key's holder was entitled to publish that schema. A separately administered policy may explicitly bind key material to schema, revision and tenant/scope/purpose, and withdraw that binding after compromise or error. The *actual transport and authority of the policy pin* remain outside this evaluator.

The fixture is a canonical, bounded, immutable **issuer-policy snapshot**, containing a policy identity/revision, exact one-to-one grants, revoked public-key digests and invalidated schema revisions. Each grant binds one issuer key reference and exact Ed25519 public-key digest to a schema identity/revision and tenant/scope/purpose. There are no wildcards, learned synonyms, guessed authorities, transitive aliases or default-allows. The caller supplies a separately expected policy identity/revision/content digest. A matching pin makes this a **policy-matched candidate** but does not establish that the pin was legitimately distributed. The user of the module remains responsible for externally authenticated policy distribution, access control, freshness and audit durability.

## Invariants fixed before code

| ID | Necessary property |
| --- | --- |
| J42 | Exact typed, bounded, immutable policy snapshot; canonical serialization and domain-separated digest bind every grant, policy identity/revision, key and revocation. |
| J43 | Policy pin, policy identity and revision must be separately expected and compared. No self-reported pin is authority. |
| J44 | Grants are exact matches on schema identity/revision, tenant, scope, purpose, issuer key reference and public-key material digest. No wildcards or subset matching. |
| J45 | Absence of an exact grant abstains; policy mismatch, malformed or stale independent expectations refuse. |
| J46 | Explicit revocation of key material or registry schema/revision overrides an otherwise valid signed registry and matching grant. |
| J47 | Conflicting/duplicate grants, duplicate revocations, noncanonical ordering, wrong types and unbounded payloads refuse construction. |
| J48 | Signed property-registry verification and structural preflight from #762 remain necessary, with no positive semantic verdict. |
| J49 | Revocation never erases historical receipts, rewrites memory or silently reroutes a revoked identity to another key. |
| J50 | A revised/corrected policy necessarily changes digest and revision. A stale independently pinned policy must not auto-upgrade or auto-accept new grants. |
| J51 | Actor/source/subject provenance, ontology correctness, real-world currentness, issuer legitimacy and tenant authority are separate unsolved gates. |
| J52 | Tests include a forged but fully consistent policy + attacker-owned pin. Its match demonstrates only mechanism consistency, not legitimate authentication. |
| J53 | Exact-value collisions and changed language/text can neither authorize a property link nor bypass the independent schema mapping. |
| J54 | Repeated runs and reordered input claims yield stable output; all records and results remain read-only evaluation artifacts. |
| J55 | No inference model, external service, new scorer, R6 holdout, #732 extractor, PAMA, lifecycle or baseline-v6 imports/mutations. |
| J56 | Every result explicitly has `issuer_authorized=false`, `identity_verified=false`, `can_supersede=false`, `authority_effect=none` and `mutates_memory=false`. |

## Negative controls, independently defined

Opaque IDs only, not existing benchmark utterances: positive exact pre-authorized key/schema/scope candidate; swapped signing key; unrelated schema; policy pin substitution; stale policy revision; missing grant; retired/revoked grant; revoked key; invalidated schema revision; claim on different tenant/scope/purpose/subject; different property mapping with the same value; structural lifecycle/cardinality refusal; duplicate grant and malformed policy; forged/consistently repinned policy; replacement of a previously matching pinned policy by a corrected one. Do not count these as an empirical score or tune runtime semantics to pass cases.

## Completion and governance

Deliver in `reference/agentmem_ref/evaluation/` with adjacent synthetic tests. The only positive status is `policy_matched_candidate`, which **never** licenses an identity-link acceptance, state change or currentness update. Independent adversarial review and exact-head CI must pass before merge. This does not close #757. Production remains blocked on authenticated trust-root/policy distribution, policy freshness/rollback prevention, source/actor evidence, subject identity, false-link corrections, dispute lineage and the explicitly approved runtime-baseline successor.
