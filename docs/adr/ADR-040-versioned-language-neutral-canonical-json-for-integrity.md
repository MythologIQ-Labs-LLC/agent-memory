# ADR-040: Use a versioned language-neutral canonical JSON contract for persisted integrity commitments

- **Status:** Proposed
- **Date:** 2026-09-28
- **Related:** #609, #602, PR #615, ADR-028, ADR-031, #522, #562

## Context

Agent Memory currently has more than one canonicalization family.

The #609 inventory in PR #615 found **219** canonicalization candidates in the scanned Python roots:

- **202** calls using Python sorted compact JSON;
- **17** direct RFC 8785 / JCS calls;
- **0** parse errors.

This matters because canonicalization is already part of several distinct identity contracts. The repository is not merely repeating one accidental helper everywhere.

### Python-sorted JSON family

Several runtime and persistence surfaces use helpers equivalent to:

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
```

That implementation is deterministic inside the qualified Python runtime, but floating-number spelling is inherited from CPython's JSON encoder rather than an explicit Agent Memory cross-language contract.

The #602 Rust qualification program exposed the boundary while attempting exact byte parity. Nulls, booleans, exact integers, strings, arrays, and ordinary string-keyed objects can already be reproduced exactly from an explicit byte contract. Floating values are the unresolved part.

This is persistence-significant rather than theoretical.

`TypedRelation.retrieval_weight` is a finite `float`, and SQLite canonical-state commitments hash typed-relation rows through `sqlite_substrate.py::_row_hash(...)`. Therefore host-dependent number spelling can affect:

- typed-relation row hashes;
- bucket commitments;
- state roots;
- restart verification;
- tamper refusal;
- cross-language persistence compatibility.

PR #615 manually classified the seven Python-sorted-JSON call sites in the runtime/persistence risk bucket. The directly proven float-bearing persisted-integrity surface is `reference/agentmem_ref/state/sqlite_substrate.py`. Other runtime/restart helpers remain compatibility-significant, but several bind typed string/integer/boolean material and must not be declared float-bearing merely because they share a helper shape.

### Existing RFC 8785 / JCS family

The same inventory found 17 direct `rfc8785.dumps(...)` call sites. They include identity or evidence surfaces for approvals, reusable grants, contextual recall, MCP/A2A interaction evidence, external evidence, enforcement evidence, runtime-trace correlation, temporal commitments, security findings, and related records.

Those uses are already deliberate canonicalization contracts. They are **not** automatically migration targets for this ADR.

The resulting architecture boundary is:

```text
same JSON meaning
    !=
same canonicalization domain
    !=
same identity / compatibility contract
```

ADR-028 requires the normative core to remain language-neutral. ADR-031 requires deterministic content commitments. A persisted integrity format that depends on unspecified CPython float formatting weakens both boundaries, but fixing that defect does not grant permission to rewrite unrelated JCS-bound identities.

## Considered standard: RFC 8785 / JCS

RFC 8785, JSON Canonicalization Scheme (JCS), is strong prior art for deterministic cryptographic JSON, including finite IEEE-754 binary64 number serialization and invalid-number refusal.

Agent Memory SHOULD reuse its proven finite-number serialization principles rather than inventing an unrelated floating-point algorithm.

Agent Memory SHOULD NOT adopt JCS wholesale for the existing Python-sorted persistence domain because JCS changes semantics outside the discovered defect:

1. JCS restricts numbers to IEEE-754 binary64, while Agent Memory/Python can carry exact integers beyond binary64's exact-integer range.
2. JCS sorts object-property names by UTF-16 code units; current Python sorting follows Unicode code-point ordering, which differs for some non-BMP keys.
3. JCS canonicalizes numeric value rather than preserving the current integer-versus-float byte distinction.
4. Existing JCS-bound Agent Memory identities already have their own compatibility obligations and should not be conflated with a new persistence scheme.

## Decision candidate

Agent Memory SHALL define a new versioned canonical serialization profile specifically for **persisted integrity and restart commitments whose identity is currently Python-shaped**, provisionally named:

`agent-memory-canonical-json-v2`

The profile is not the universal Agent Memory JSON format. It is not a requirement that all current JCS-bound evidence identities migrate to it.

### 1. Canonicalization scheme is explicit identity

Every cryptographic or persisted identity domain SHALL bind an explicit canonicalization scheme.

```text
identity domain
  -> recorded canonicalization scheme
  -> canonical bytes
  -> commitment/digest
```

Existing RFC 8785/JCS-bound domains remain JCS-bound unless a separate versioned migration explicitly changes their contract.

Legacy Python-sorted persistence domains remain verifiable under their legacy byte rules for the supported migration window.

A caller MUST NOT select a serializer merely by importing a convenience helper whose current output happens to match another domain.

### 2. V2 supported value domain

The v2 persistence profile contains:

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

Implementation limits MUST NOT become silent rounding.

### 3. Strings

Strings SHALL preserve Unicode data without normalization.

Escaping SHALL remain compatible with the current Python persistence bytes where those bytes are already language-neutral:

- `"` -> `\"`;
- `\\` -> `\\\\`;
- U+0008/U+0009/U+000A/U+000C/U+000D -> `\b`, `\t`, `\n`, `\f`, `\r`;
- other U+0000..U+001F controls -> lowercase `\u00xx` form;
- other valid Unicode scalar values emitted as UTF-8 without ASCII forcing.

No Unicode normalization is performed.

### 4. Object-key ordering

V2 object keys SHALL be ordered recursively by Unicode scalar/code-point lexicographic order, preserving the current Python persistence ordering for valid Unicode strings.

This deliberately does **not** adopt JCS UTF-16 code-unit ordering, because doing so would expand the migration beyond the numeric defect.

The ordering rule MUST be tested with non-ASCII and non-BMP keys.

### 5. Integers

Integers SHALL serialize as exact base-10 mathematical integers:

- no leading `+`;
- no leading zeros except `0`;
- negative values use one leading `-`;
- no exponent notation;
- no conversion through binary64.

The normative contract is exact integer value, not host integer width.

A runtime that cannot preserve an integer exactly MUST refuse it at the canonicalization boundary.

### 6. Floating values

Floating values SHALL be finite IEEE-754 binary64 values.

The candidate algorithm SHALL use RFC 8785 / ECMAScript shortest-roundtrip binary64 formatting as prior art, with Agent Memory type-preservation rules that must be qualified before acceptance:

1. negative zero serializes distinctly as `-0.0`;
2. a floating token with neither decimal point nor exponent receives `.0`, so float identity remains distinct from integer identity.

Examples:

```text
integer 1   -> 1
float   1.0 -> 1.0
float  -0.0 -> -0.0
```

Exponent notation SHALL use lowercase `e` and the frozen normalized exponent form.

The exact binary64 vectors MUST be frozen before either Python or Rust candidate implementation is accepted. If the type-preserving extension proves materially fragile or less interoperable than expected, this ADR returns for ruling rather than silently adopting host formatting.

### 7. Integrity scheme versioning

Canonicalization version is part of persisted integrity identity.

A commitment computed from v2 bytes MUST NOT carry a legacy scheme identifier.

At minimum, affected SQLite commitment schemes SHALL advance explicitly, for example:

```text
bmerkle-v1  -> bmerkle-v2
```

Whether `gsect-v1` requires a new canonicalization-bearing version depends on the final reachability classification. A scheme MUST advance only when its committed byte domain actually changes; version numbers are not decorative confetti.

The runtime MUST refuse scheme/canonicalizer confusion in both directions.

### 8. Legacy verification remains supported

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

### 9. Migration is verify-before-recommit

Migration SHALL:

1. open state under its recorded legacy scheme;
2. verify the full legacy commitment;
3. refuse migration if legacy verification fails;
4. decode only the verified logical state;
5. validate every value against the v2 domain;
6. compute v2 commitments from that logical state;
7. commit the scheme transition transactionally;
8. record migration provenance;
9. restart and independently verify the new scheme.

Migration MUST NOT rewrite memory semantics, lifecycle state, identifiers, timestamps, ordering, authority, or user payloads.

Interrupted or failed migration MUST leave the legacy state valid and unchanged.

### 10. Unsupported legacy values

If verified legacy state contains a value that cannot be represented by v2, migration MUST fail closed with an explicit compatibility result.

Examples include non-finite floats or values outside an implementation's exact supported domain.

Unsupported payload remediation is a separate governed operation, not an implicit side effect of canonicalization migration.

### 11. Canonicalizer registry, not universal serializer

V2 SHOULD be implemented through an explicit versioned canonicalization API or registry.

The repository MUST NOT converge every identity surface onto v2 merely because centralization is convenient.

A conforming implementation should make scheme choice visible, for example conceptually:

```text
canonicalize(profile="legacy-python-json-v1", value=...)
canonicalize(profile="agent-memory-canonical-json-v2", value=...)
canonicalize(profile="rfc8785-jcs", value=...)
```

Exact API spelling is non-normative. The rule is that identity-bearing callers bind a named scheme and that a local convenience serializer cannot silently become a new canonical contract.

## Integrity-scheme consequences

The current SQLite verifier already distinguishes commitment schemes and verifies canonical state before trusting maintained indexes. That pattern remains the migration precedent:

```text
recorded scheme
  -> matching canonicalizer + root algorithm
  -> verification from canonical state
  -> maintained index trusted/rebuilt only after verification
```

Canonical rows/state remain the verification source. Maintained indexes remain derived data.

## Rust qualification consequence

#602 may continue qualifying deterministic primitives and hot paths that do not depend on unresolved float-bearing persistence.

Already admissible evidence includes:

- tokenization/ranking primitives;
- SHA-256 primitives;
- non-floating canonical-byte parity;
- identity-first candidate prefilter parity;
- matched hot-path performance that does not claim persisted-state equivalence.

Blocked from promotion until #609 is resolved:

- Rust ownership of float-bearing persisted integrity;
- restart/checkpoint compatibility claims over affected schemes;
- cross-language tamper verification over affected state;
- migration of canonical SQLite state to a Rust-owned state runtime.

## Evidence requirements for acceptance

ADR-040 SHALL remain Proposed until all of the following exist.

### 1. Canonicalization-domain inventory

PR #615 establishes the repository-level family inventory and a first manual consequence map:

- 202 Python-sorted-JSON candidates;
- 17 direct RFC 8785/JCS candidates;
- seven runtime/persistence-risk Python sites;
- `sqlite_substrate.py` proven float-bearing.

Still required before acceptance:

- raw runtime-configuration float/non-finite reachability proof;
- restart/checkpoint durable-envelope reachability classification;
- explicit mapping of which commitment scheme binds which canonicalization profile.

### 2. Frozen language-neutral vectors

Freeze before candidate implementation:

- strings/control escaping;
- Unicode/non-BMP key ordering;
- exact integers including values beyond 2^53;
- representative binary64 values around exponent thresholds;
- integral floats;
- negative zero;
- subnormals and boundary values;
- NaN/Infinity refusal.

### 3. Independent Python and Rust implementations

Both implementations consume the same frozen vectors and must reproduce exact bytes and digests. No tolerance and no post-hoc fixture rewriting.

### 4. Legacy migration evidence

Required cases include:

- valid legacy state verifies before migration;
- tampered legacy state refuses migration;
- unsupported legacy values refuse without partial conversion;
- interrupted migration preserves valid legacy state;
- v2 state verifies after commit and restart;
- rollback/scheme confusion fails safely.

### 5. Scheme versioning

Old and new commitments cannot be confused, and each recorded scheme resolves to exactly one canonicalization/root contract.

### 6. Regression evidence

Retain/correct/forget/history/currentness behavior, scope/tenant isolation, admission/ranking, and accepted benchmark outcomes remain unchanged except for explicitly measured serialization/performance effects.

## Rejected alternatives

### Keep CPython JSON formatting as cross-language doctrine

Rejected as the target because implementation behavior would become architecture by accident.

### Adopt RFC 8785/JCS wholesale for persistence

Rejected because it unnecessarily changes integer and key-order semantics. Existing JCS-bound domains remain legitimate and separate.

### Replace all existing JCS identities with v2

Rejected. Existing JCS-bound evidence/security identities have their own compatibility contracts. #609 does not grant migration authority over them.

### One universal canonical serializer for the repository

Rejected. Different identity domains may legitimately use different explicit canonicalization schemes. Centralized implementation is useful only when scheme identity remains visible.

### Serialize all numbers as strings

Rejected because it changes ordinary JSON types and would ripple through schemas/consumers.

### Ignore float identity because hashes are implementation-local

Rejected because persisted commitments participate in restart verification, tamper detection, migration, and cross-language conformance.

### Recompute old commitments using v2 bytes

Rejected because it would reinterpret historical evidence under a different byte contract.

## Consequences

### Positive

- persistence bytes become explicit architecture rather than CPython behavior;
- Rust and future runtimes can qualify persistence honestly;
- non-finite behavior becomes fail-closed;
- migration is scheme-aware and evidence-preserving;
- existing JCS evidence domains remain stable;
- canonicalization-family boundaries become auditable rather than accidental.

### Costs

- an explicit persistence migration must be implemented and tested;
- legacy verification code remains necessary for a compatibility window;
- binary64 canonicalization requires careful cross-language vectors;
- exact integers require receiving runtimes to preserve value rather than round;
- the repository must maintain more than one named canonicalization profile where identity contracts legitimately differ.

## Non-goals

ADR-040 does not:

- make Rust the preferred runtime;
- change memory authority, PAMA, lifecycle, ranking, or currentness;
- require v2 or JCS as Agent Memory's general wire format;
- normalize Unicode;
- equate digest equality with truth or authority;
- migrate state merely because a new profile exists;
- migrate existing JCS-bound identities without their own versioned decision.

## Decision status

**Proposed.**

PR #615 materially narrows the scope, but #609 still owns the frozen numeric vectors, value-domain reachability proofs, scheme map, migration evidence, and independent Python/Rust parity required before a maintainer ruling.

#602 consumes the result for state/runtime parity. It cannot accept this ADR merely by showing that Rust can reproduce candidate bytes.
