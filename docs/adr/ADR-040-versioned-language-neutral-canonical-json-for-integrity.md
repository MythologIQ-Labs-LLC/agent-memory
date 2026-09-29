# ADR-040: Use a versioned language-neutral canonical JSON contract for persisted integrity commitments

- **Status:** Accepted
- **Date:** 2026-09-28
- **Reconciled candidate:** 2026-09-29
- **Accepted:** 2026-09-29
- **Related:** #609, #602, #615, #617, #618, #619, #620, #621, #622, #623, #624, #625, #626, #627, ADR-028, ADR-031, #522, #562

## Context

Agent Memory has more than one canonicalization family, and those families participate in distinct identity and compatibility contracts.

The #609 repository inventory established:

- 219 canonicalization candidates in the scanned Python roots;
- 202 Python sorted/compact JSON call sites;
- 17 direct RFC 8785 / JCS call sites;
- 0 parse errors;
- seven Python-sorted-JSON sites in the runtime/persistence risk bucket;
- `reference/agentmem_ref/state/sqlite_substrate.py` as a proven float-bearing persisted-integrity surface because `TypedRelation.retrieval_weight` reaches row hashes and bucket/root commitments.

The existing Python-shaped persistence helper is equivalent to:

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
```

That helper is deterministic inside the qualified Python runtime, but floating-number spelling is inherited from CPython's JSON encoder rather than from an explicit language-neutral Agent Memory contract.

The #602 Rust qualification program exposed the architecture boundary. A non-Python implementation can reproduce nulls, booleans, exact integers, strings, arrays, and ordinary string-keyed objects from an explicit contract, but persisted floating-point identity cannot be claimed from CPython behavior alone.

This is persistence-significant rather than cosmetic. Number spelling can affect:

- typed-relation row hashes;
- substrate bucket commitments;
- substrate state roots;
- governance value/residual commitments when numeric extension state is present;
- restart verification;
- tamper refusal;
- migration compatibility;
- cross-language persistence conformance.

The #617 reachability qualification established three distinct consequences:

1. runtime configuration schema v1 excludes JSON `number` and `integer` domains, so raw runtime configuration is compatibility-significant but not a numeric migration target under the current schema;
2. `bmerkle-v1` is proven float-bearing through `TypedRelation.retrieval_weight`, while `Fact.attributes` and `TypedRelation.attributes` permit numeric and non-finite values by contract;
3. `gsect-v1` commits governance maps/logs/residuals whose `extension_state` contract permits numeric and non-finite values, so governance persistence requires a separately named successor whenever those bytes are recommitted under the v2 canonicalizer.

Agent Memory also already uses RFC 8785 / JCS deliberately across identity and evidence domains. Those identities are separate compatibility contracts and are not migration targets of this ADR.

The controlling distinction is:

```text
same JSON meaning
    !=
same canonicalization domain
    !=
same identity / compatibility contract
```

ADR-028 requires the normative core to remain language-neutral. ADR-031 requires deterministic content commitments. Persisted integrity that depends on unspecified CPython float formatting weakens both boundaries.

## Considered standard: RFC 8785 / JCS

RFC 8785 / JCS is strong prior art for deterministic cryptographic JSON, including finite IEEE-754 binary64 number serialization and invalid-number refusal.

Agent Memory reuses its finite-number serialization principles, but does not adopt JCS wholesale for the Python-shaped persistence domain because that would change unrelated semantics:

1. JCS restricts numbers to IEEE-754 binary64, while Agent Memory requires exact integers beyond binary64's exact-integer range where the host can preserve them;
2. JCS sorts object-property names by UTF-16 code units, while existing Python-shaped persistence ordering follows Unicode scalar/code-point ordering;
3. JCS canonicalizes numeric value rather than preserving the existing integer-versus-float byte distinction;
4. existing JCS-bound Agent Memory identities already have their own compatibility obligations and must not be conflated with persisted-state migration.

## Decision

Agent Memory defines a versioned canonical serialization profile for persisted integrity and restart commitments whose identity is currently Python-shaped:

`agent-memory-canonical-json-v2`

This profile is not the universal Agent Memory JSON format. Existing JCS-bound identities remain JCS-bound unless a separate versioned decision explicitly migrates them.

### 1. Canonicalization scheme is explicit identity

Every cryptographic or persisted identity domain MUST bind an explicit canonicalization scheme.

```text
identity domain
  -> recorded canonicalization scheme
  -> canonical bytes
  -> commitment / digest contract
```

A caller MUST NOT select a serializer merely by importing a convenience helper whose current output happens to match another domain.

Legacy Python-shaped persistence domains remain verifiable under their recorded legacy byte rules for the supported compatibility window.

### 2. V2 supported value domain

The v2 persistence profile supports:

- `null`;
- booleans;
- exact integers;
- finite IEEE-754 binary64 floating values;
- Unicode strings;
- arrays;
- objects with string keys.

Implementations MUST reject rather than silently coerce:

- `NaN`;
- positive or negative infinity;
- duplicate object keys at a parsing boundary;
- non-string object keys;
- invalid Unicode scalar data;
- integer values an implementation cannot preserve exactly.

Implementation limits MUST NOT become silent rounding, stringification, truncation, normalization, or field dropping.

### 3. Strings

Strings preserve Unicode data without normalization.

Escaping remains compatible with the language-neutral portion of the current Python persistence contract:

- `"` -> `\"`;
- `\\` -> `\\\\`;
- U+0008/U+0009/U+000A/U+000C/U+000D -> `\b`, `\t`, `\n`, `\f`, `\r`;
- other U+0000..U+001F controls -> lowercase `\u00xx` form;
- other valid Unicode scalar values are emitted as UTF-8 without ASCII forcing.

No Unicode normalization is performed.

### 4. Object-key ordering

V2 object keys are ordered recursively by Unicode scalar/code-point lexicographic order.

This deliberately does not adopt JCS UTF-16 code-unit ordering. Non-ASCII and non-BMP key ordering are part of the frozen conformance vectors.

### 5. Integers

Integers serialize as exact base-10 mathematical integers:

- no leading `+`;
- no leading zeros except `0`;
- negative values use one leading `-`;
- no exponent notation;
- no conversion through binary64.

The normative contract is exact integer value, not host integer width.

A runtime that cannot preserve an integer exactly MUST refuse it at the canonicalization boundary.

### 6. Floating values

Floating values are finite IEEE-754 binary64 values.

The qualified algorithm uses RFC 8785 / ECMAScript shortest-roundtrip binary64 formatting as the base spelling with Agent Memory type-preservation rules:

1. negative zero serializes distinctly as `-0.0`;
2. a floating token with neither decimal point nor exponent receives `.0`, so float identity remains distinct from integer identity;
3. exponent notation uses lowercase `e` and the normalized form frozen by the accepted vector source.

Examples:

```text
integer 1   -> 1
float   1.0 -> 1.0
float  -0.0 -> -0.0
```

The normative byte contract is the accepted 44-case canonical-v2 vector source qualified by #618 and reproduced independently by Python and Rust in #619.

Host-native float formatting is not a conforming substitute.

### 7. Integrity scheme versioning

Canonicalization identity is part of persisted integrity identity at the recorded commitment/root contract boundary.

A commitment computed from v2 canonical bytes MUST NOT carry a legacy scheme identifier.

The qualified successor identities are:

```text
bmerkle-v1 -> bmerkle-v2

gsect-v1  -> gsect-v2
```

The `bmerkle-v2` and `gsect-v2` candidate bindings resolve to `agent-memory-canonical-json-v2` plus separately named v2 root contracts.

Scheme identity is required at the externally recorded commitment contract. The architecture does not require decorative version strings inside every lower-level row hash, entry hash, or intermediate digest when the enclosing root contract already unambiguously binds the canonicalizer and construction algorithm.

Maintained row/bucket/entry indexes remain derived evidence. Canonical persisted rows and the recorded root contract remain the verification source.

The runtime MUST refuse scheme/canonicalizer/root/schema confusion in both directions.

### 8. Compatibility registry

Recorded persistence identity resolves through an explicit domain-scoped registry:

```text
domain
  + recorded scheme / commitment shape
  + runtime-envelope context
      -> canonicalization profile
      -> root contract
      -> allowed operation
```

The registry MUST NOT resolve by digest prefix alone because legacy `sha256:` commitments exist in more than one persistence domain.

The qualified registry preserves:

- legacy substrate full-JSON verification;
- `bmerkle-v1` verification;
- legacy governance full-JSON verification;
- `gsect-v1` verification;
- qualification-only inspection of `bmerkle-v2`;
- qualification-only inspection of `gsect-v2`;
- explicit exclusion of existing JCS identity domains.

Registry lookup is compatibility evidence, not authority. It does not grant migration permission, memory authority, admission, ranking, lifecycle/currentness, or emission rights.

### 9. Candidate schemes remain non-emittable until a separate production gate

ADR acceptance defines the architecture. It does not activate candidate persistence.

Until a separate production cutover explicitly authorizes otherwise:

- `bmerkle-v2` remains `candidate_not_emittable`;
- `gsect-v2` remains `candidate_not_emittable` / unsupported by production runtime envelope schemas;
- ordinary production recovery does not accept the qualification-only v2 envelope;
- automatic migration during recovery is forbidden.

### 10. Legacy verification remains supported

Existing persisted state remains valid evidence if it verifies under the exact serializer and commitment scheme that originally created it.

```text
legacy bytes
  -> legacy verification
  -> verified logical state
  -> explicit migration eligibility
  -> v2 bytes
  -> v2 commitment
```

A v2 implementation MUST NOT recompute historical state with v2 bytes and then label the old commitment invalid.

### 11. Migration is verify-old-before-recommit

Canonicalization migration follows this order:

1. open state under its recorded legacy scheme;
2. resolve the exact legacy binding;
3. verify the full legacy substrate commitment;
4. verify the full legacy governance commitment;
5. verify the bound journal and runtime envelope;
6. reconstruct verified logical state;
7. validate every reachable value against the v2 domain;
8. construct candidate v2 commitments from verified logical state before any migration write;
9. reverify the disposable copy immediately before mutation;
10. begin one SQLite `BEGIN IMMEDIATE` transaction on the disposable verified copy;
11. recheck source generation, commitments, history, and preserved runtime identity inside the transaction;
12. rewrite affected identity-bearing persisted JSON to exact v2 bytes;
13. rebuild candidate derived integrity material;
14. recompute candidate roots and require exact equality with the phase-3 candidate anchors;
15. require pre/post decoded logical-state digest identity;
16. write durable migration provenance;
17. write the qualification-only candidate runtime envelope and transition journal record;
18. verify candidate material before the single commit;
19. commit once;
20. close migration handles;
21. reopen the candidate independently and read-only;
22. verify exact v2 bytes, roots, derived indexes, journal, envelope, provenance, preserved identity, and logical-state anchor;
23. emit final qualification success only as non-authoritative evidence.

No durable migration write is allowed before the transaction or after its commit.

### 12. Migration preserves semantics, not legacy serialization bytes

Successful migration intentionally rewrites affected persisted JSON byte representations.

Therefore the preservation invariant is not `all payload bytes remain unchanged`.

Migration MUST preserve decoded logical and semantic state, including:

- memory identifiers;
- timestamps;
- facts, episodes, and typed relations;
- retain/correct/forget/history/currentness state;
- scope and tenant state;
- authority and admission state;
- ranking inputs and ordering semantics;
- governance events and visibility state;
- runtime profile identity;
- interpretation identity;
- substrate operational identity;
- historical journal records prior to the candidate transition record.

Canonicalization migration MUST NOT become a governed payload remediation operation.

### 13. Historical journal and preserved runtime identity are external migration anchors

Phase-3 qualification evidence MUST externally bind the source state required to prove preservation across recommit.

At minimum it binds:

- verified source journal tail record digest;
- a deterministic digest over ordered historical journal SQL generation plus exact raw stored `payload_json` bytes;
- historical journal row count;
- runtime profile identity;
- `interpretation_digest`;
- `substrate_identity`;
- pre-migration logical-state digest;
- target substrate commitment;
- target governance commitment.

Phase 4 rechecks those anchors inside the migration transaction.

Phase 5 compares the independently reopened candidate against the phase-3 external anchors. Candidate-derived values cannot establish their own historical or runtime-identity authority.

The candidate runtime envelope and final transition journal record use exact frozen key sets. Missing or unexpected fields refuse.

The SQL journal generation column MUST equal the generation encoded in its payload.

### 14. Durable migration provenance is evidence, not authority

Phase-4 migration provenance is written in the same transaction as the candidate state and binds, at minimum:

- source runtime generation/schema;
- source substrate/governance binding identities and commitments;
- target substrate/governance binding identities and commitments;
- accepted canonical-vector source;
- scheme-registry source;
- migration implementation identity;
- migration transaction generation;
- pre/post logical-state digests;
- transaction outcome.

The phase-4 durable transaction outcome is only:

`committed_pending_restart_verification`

Final `committed` exists only after phase-5 close/reopen qualification and is not written back into the runtime database by phase 5.

Provenance cannot make an invalid root, journal, envelope, or logical state valid.

### 15. Failed migration cannot leave partial candidate state

If old-state verification fails, v2 value-domain validation fails, an injected phase-4 fault occurs, or candidate verification fails before commit, migration fails closed.

The architecture invariant is:

```text
failed migration
    -> no accepted partial candidate state
    -> legacy committed state remains recoverable under its recorded scheme
```

The qualification evidence proves, for the tested SQLite path:

- primary database bytes remain unchanged across injected rollback boundaries;
- relevant table contents are unchanged;
- the migration-provenance table is absent after rollback;
- no pending/non-empty WAL remains after rollback;
- the old scheme requalifies successfully.

This evidence does not claim universal byte identity for every possible SQLite sidecar such as SHM. The normative requirement is durable committed-state atomicity and recoverability, not cosmetic filesystem-byte equality for non-authoritative sidecars.

### 16. Unsupported legacy values fail closed

If verified legacy state contains a value that cannot be represented by v2, migration MUST fail before the migration transaction with an explicit compatibility result.

Examples include non-finite floats or values outside an implementation's exact supported domain.

Unsupported payload remediation is a separate governed operation, not an implicit side effect of canonicalization migration.

### 17. Production recovery exclusion must be specific and isolated

Qualification MUST NOT prove production exclusion by handing the canonical qualification candidate to a writable production runtime.

The qualified proof:

1. creates a second disposable SQLite backup of the candidate;
2. invokes ordinary production recovery only against that backup;
3. requires the exact refusal reason `unsupported SQLite runtime state schema`;
4. rejects unrelated recovery errors as insufficient evidence of the intended boundary.

The low-level candidate verifier remains read-only and has no production-recovery route.

### 18. Canonicalizer registry, not universal serializer

V2 SHOULD be exposed through an explicit versioned canonicalization API or registry.

The repository MUST NOT converge every identity surface onto v2 merely because centralization is convenient.

Conceptually:

```text
canonicalize(profile="legacy-python-json-v1", value=...)
canonicalize(profile="agent-memory-canonical-json-v2", value=...)
canonicalize(profile="rfc8785-jcs", value=...)
```

Exact API spelling is non-normative. Identity-bearing callers bind a named scheme; a local convenience serializer cannot silently become a canonical contract.

## Integrity-scheme consequences

The persistence verifier follows this model:

```text
recorded domain + scheme
  -> matching canonicalizer + root algorithm
  -> verification from canonical persisted state
  -> maintained index checked/rebuilt as derived evidence
```

The architecture explicitly separates:

```text
canonicalization profile != commitment algorithm
successful verification != migration permission
migration provenance != commitment verification
scheme transition != memory semantic change
registry lookup != authority
```

## Rust qualification consequence

The #619 Rust implementation establishes independent byte/digest/refusal parity for `agent-memory-canonical-json-v2`.

That evidence does not assign persistence ownership to Rust.

#602 may consume the accepted architecture for future runtime-profile evaluation, but Rust persistence promotion requires its own evidence and decision. In particular, ADR acceptance does not by itself authorize:

- Rust ownership of SQLite persisted integrity;
- Rust restart/checkpoint compatibility claims as production runtime behavior;
- Rust-owned migration of canonical SQLite state;
- Python/Rust FFI or binding architecture.

## Qualification evidence for acceptance

All acceptance evidence required by the original proposal is now present.

### 1. Canonicalization-domain inventory and reachability — established

- PR #615: canonicalization family inventory and consequence classification.
- PR #617: runtime-configuration, substrate, and governance numeric reachability plus scheme impact.

### 2. Frozen language-neutral vectors — established

- #616 froze the source vector fixture before candidate implementation.
- PR #618 accepted the unchanged 44-case source as the conformance oracle and pinned its Git blob identity.

### 3. Independent Python and Rust implementations — established

- PR #619 reproduces the accepted success/refusal vectors exactly in independent Python and Rust candidates.
- Successful cases require exact UTF-8 bytes and SHA-256 digest parity.

### 4. Scheme versioning and compatibility registry — established

- #620 / PR #621 freeze and execute the domain-scoped scheme registry.
- Legacy schemes remain byte-exactly verifiable.
- Candidate `bmerkle-v2` and `gsect-v2` are inspect-only and non-emittable.
- Wrong-domain, unknown, canonicalizer/root/schema confusion, mixed-generation, and emission attempts fail closed.

### 5. Verify-old-before-recommit migration — established

- #623 freezes the phases 1-5 migration contract.
- #624 proves phases 1-3 old-state verification, v2 validation, candidate construction, and source isolation.
- #625 / PR #626 proves phases 4-5 transaction, rollback, restart, tamper, preservation-anchor, and production-exclusion behavior.
- PR #626 merged as `387f728e43681c44a7cc9edc8818d2ce56246640` from reviewed head `19d97d809576e23ed8278d8d4d788f550628a575`.

### 6. Regression evidence — established

The exact reviewed #626 head passed the complete PR workflow matrix: 42/42 successful.

Required lanes include retrieval quality, operational memory, long-horizon memory, metabolism, restart-safe runtime, SQLite production substrate, authority/governance evidence, canonical-v2 preflight/transaction qualification, and doctrine validation.

No accepted behavioral change is hidden behind the serialization/integrity migration.

## Rejected alternatives

### Keep CPython JSON formatting as cross-language doctrine

Rejected because implementation behavior must not become architecture by accident.

### Adopt RFC 8785/JCS wholesale for persistence

Rejected because it unnecessarily changes exact-integer and object-key-order semantics. Existing JCS-bound identities remain legitimate and separate.

### Replace all existing JCS identities with v2

Rejected. Existing JCS-bound evidence/security identities have their own compatibility contracts.

### One universal canonical serializer for the repository

Rejected. Different identity domains may legitimately use different explicit canonicalization schemes.

### Serialize all numbers as strings

Rejected because it changes ordinary JSON types and would ripple through schemas and consumers.

### Ignore float identity because hashes are implementation-local

Rejected because persisted commitments participate in restart verification, tamper detection, migration, and cross-language conformance.

### Recompute old commitments using v2 bytes

Rejected because it would reinterpret historical evidence under a different byte contract.

### Require version tags inside every internal hash layer

Rejected as a universal requirement. The qualified architecture binds canonicalization and construction identity at the recorded domain/root contract, while internal maintained hashes remain derived material verified under that contract. A lower-level layer may be separately versioned when its compatibility contract actually requires it.

## Consequences

### Positive

- persisted integrity bytes become explicit architecture rather than CPython behavior;
- Rust and future runtimes can qualify canonicalization honestly;
- non-finite behavior is fail-closed;
- migration is scheme-aware and evidence-preserving;
- historical journal/runtime identity preservation is externally anchored;
- existing JCS evidence domains remain stable;
- canonicalization-family boundaries become auditable;
- migration evidence cannot self-authorize by internal consistency alone.

### Costs

- more than one named canonicalization profile must remain supported where identity contracts differ;
- legacy verification remains necessary for a compatibility window;
- binary64 canonicalization requires cross-language conformance vectors;
- exact integers require receiving runtimes to preserve value rather than round;
- production activation requires a separate cutover decision and compatibility plan;
- migration qualification carries explicit history/runtime-identity anchor evidence.

## Non-goals

ADR-040 does not:

- activate `bmerkle-v2` or `gsect-v2` in production;
- authorize automatic migration during ordinary recovery;
- remove legacy verification;
- teach ordinary production recovery to accept qualification-only envelopes;
- make Rust the preferred runtime;
- promote Rust into persistence/restart ownership;
- change memory authority, lifecycle, ranking, currentness, scope, tenant, identifiers, timestamps, or semantic payload values;
- require v2 or JCS as Agent Memory's general wire format;
- normalize Unicode;
- equate digest equality with truth or authority;
- migrate existing JCS-bound identities without their own versioned decision.

## Activation boundary

Architecture acceptance and production activation are separate decisions:

```text
ADR-040 acceptance
  != production activation
  != automatic migration
  != candidate-scheme emission
  != legacy verifier removal
  != Rust persistence promotion
```

A production cutover must be authorized through a separate gate that defines supported migration timing, recovery compatibility, rollout/rollback behavior, and operational ownership.

## Decision status

**Accepted.**

Accepted by maintainer ruling on 2026-09-29 after #627 reconciliation and exact-head review/CI of PR #628. This acceptance establishes the architecture only; the activation boundary above remains controlling.