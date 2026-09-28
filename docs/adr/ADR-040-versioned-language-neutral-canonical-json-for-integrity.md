# ADR-040: Use a versioned language-neutral canonical JSON contract for integrity commitments

- **Status:** Proposed
- **Date:** 2026-09-28
- **Related:** #609, #602, ADR-028, ADR-031, #522, #562

## Context

Agent Memory currently computes multiple integrity and restart commitments from JSON bytes produced by repeated local helpers equivalent to:

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
```

That implementation is deterministic inside the qualified Python runtime, but it is not fully language-neutral.

The #602 Rust qualification program exposed the boundary while attempting exact cross-language canonical-byte parity. Nulls, booleans, integers, strings, arrays, and ordinary string-keyed objects can be reproduced exactly from an explicit byte contract. Floating numbers are different: their spelling is inherited from CPython's JSON encoder rather than from Agent Memory doctrine.

This is already persistence-significant rather than theoretical.

`TypedRelation.retrieval_weight` is a finite `float` and SQLite canonical-state commitments hash `asdict(relation)` through the canonical-byte helper. Therefore number spelling can affect:

- typed-relation row hashes;
- bucket commitments;
- state roots;
- restart verification;
- tamper refusal;
- cross-language persistence compatibility.

The current helper also inherits Python's default handling of non-finite floats. `json.dumps` permits `NaN`, `Infinity`, and `-Infinity` unless explicitly configured otherwise. `TypedRelation.retrieval_weight` already rejects non-finite values, but generic attribute/state dictionaries can reach canonical serialization through other paths.

The problem is larger than one Rust formatter:

```text
Python implementation behavior
        !=
explicit cross-language canonical byte contract
        !=
persisted digest scheme identity
```

ADR-028 requires the normative core to remain language-neutral. ADR-031 requires deterministic content commitments. A persisted integrity format that depends on unspecified CPython formatting behavior weakens both boundaries.

## Considered standard: RFC 8785 / JCS

RFC 8785, JSON Canonicalization Scheme (JCS), is valuable prior art. It defines deterministic JSON serialization for cryptographic use, including:

- deterministic string escaping;
- finite IEEE-754 binary64 number serialization based on ECMAScript;
- recursive object-property sorting;
- rejection of invalid/non-I-JSON values.

Agent Memory SHOULD reuse its proven number-serialization principles rather than inventing an unrelated floating-point algorithm.

Agent Memory SHOULD NOT adopt JCS wholesale for existing persisted state because JCS also changes semantics outside the discovered defect:

1. JCS restricts JSON numbers to IEEE-754 binary64. Agent Memory/Python can carry exact integers beyond the binary64 exact-integer range.
2. JCS sorts object-property names by UTF-16 code units. Current Python `sort_keys=True` semantics follow Python string ordering. These differ for some non-BMP Unicode keys.
3. JCS intentionally canonicalizes numeric value rather than preserving Python's integer-vs-float spelling distinction. Existing Agent Memory hashes can distinguish `1` from `1.0`.

Changing all three at once would create a broader compatibility migration than the evidence requires.

## Decision candidate

Agent Memory SHALL define a new versioned canonical serialization profile for integrity commitments, provisionally named:

`agent-memory-canonical-json-v2`

The profile is a deterministic JSON byte format for hashing/signing/commitment purposes. It is not a general wire-format requirement and does not redefine application-level JSON semantics.

The profile SHALL preserve existing language-neutral behavior where possible and explicitly define the previously implementation-dependent numeric behavior.

### 1. Supported value domain

The canonical domain contains:

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

An implementation limitation MUST NOT become silent rounding.

### 2. Strings

Strings SHALL preserve Unicode data without normalization.

String escaping SHALL remain compatible with the current Agent Memory/Python behavior and RFC 8785 string serialization:

- `"` -> `\"`;
- `\\` -> `\\\\`;
- U+0008/U+0009/U+000A/U+000C/U+000D -> `\b`, `\t`, `\n`, `\f`, `\r`;
- other U+0000..U+001F controls -> lowercase `\u00xx` form;
- other valid Unicode scalar values emitted as UTF-8 without ASCII forcing.

No NFC/NFD or other Unicode normalization is performed.

### 3. Object-key ordering

Object keys SHALL be ordered recursively by Unicode scalar/code-point lexicographic order, preserving the current Python ordering contract for valid Unicode strings.

This deliberately does **not** adopt JCS UTF-16 code-unit ordering because doing so would create an unrelated key-order migration.

The ordering rule is part of the canonical profile and MUST be tested with non-ASCII and non-BMP keys.

### 4. Integers

Integers SHALL serialize as exact base-10 mathematical integers:

- no leading `+`;
- no leading zeros except `0`;
- negative values use one leading `-`;
- no exponent notation;
- no conversion through binary64.

The normative contract is exact integer value, not a specific host integer width.

A runtime that cannot preserve an integer exactly MUST refuse the value at the canonicalization boundary rather than round it.

### 5. Floating values

Floating values SHALL be finite IEEE-754 binary64 values.

The candidate number algorithm SHALL use RFC 8785 / ECMAScript shortest-roundtrip serialization as its base, with two Agent Memory type-preservation rules:

1. negative zero SHALL serialize as `-0.0`;
2. if the shortest-roundtrip token contains neither a decimal point nor exponent marker, append `.0` so a floating value remains distinguishable from an integer in canonical bytes.

Examples of the intended distinction:

```text
integer 1   -> 1
float   1.0 -> 1.0
float  -0.0 -> -0.0
```

Exponent notation SHALL use lowercase `e` and the base shortest-roundtrip algorithm's normalized exponent form.

The exact floating vectors MUST be frozen before either Python or Rust implementation is accepted.

If qualification demonstrates that the type-preserving extension is materially harder or less interoperable than expected, ADR-040 MUST return for ruling rather than silently falling back to host formatting.

### 6. Canonical profile identity

Canonicalization version is part of integrity identity.

A digest computed from `agent-memory-canonical-json-v2` bytes MUST NOT be labeled as a legacy digest scheme.

At minimum, SQLite commitment schemes SHALL advance explicitly, for example:

```text
bmerkle-v1  -> bmerkle-v2
gsect-v1    -> gsect-v2
```

The exact final names may differ, but version identity MUST be visible in the recorded commitment.

The runtime MUST NOT interpret a legacy commitment under v2 canonical bytes or a v2 commitment under legacy bytes.

### 7. Legacy verification remains supported

Existing persisted state remains valid evidence if it verifies under the exact legacy canonicalization and digest scheme that originally committed it.

Legacy verification SHALL remain read/verification-capable for the supported migration window.

```text
legacy bytes
  -> legacy scheme verification
  -> verified logical state
  -> explicit migration eligibility
  -> v2 canonical bytes
  -> v2 commitment
```

A v2 implementation MUST NOT recompute legacy state with v2 bytes and declare the legacy digest invalid.

### 8. Migration is verify-before-recommit

Migration SHALL follow this order:

1. open state under the recorded legacy scheme;
2. verify the full legacy commitment from canonical rows/state;
3. refuse migration if legacy verification fails;
4. decode the verified logical state;
5. validate that every value is representable under v2;
6. compute v2 row hashes/indexes/roots from the logical state;
7. commit the scheme transition transactionally;
8. record migration provenance sufficient to distinguish migrated state from newly created v2 state;
9. after restart, verify the v2 commitment independently from canonical rows.

Migration MUST NOT be an opportunity to rewrite memory semantics, lifecycle state, identifiers, timestamps, ordering, authority, or user payloads.

### 9. Unsupported legacy values

If verified legacy state contains a value that cannot be represented by v2, migration MUST fail closed with an explicit compatibility result.

Examples include:

- non-finite floating values in generic attributes;
- invalid Unicode data;
- implementation-specific numeric values outside the receiving runtime's exact domain.

The system MUST preserve the verified legacy state rather than partially migrating it.

Remediation of unsupported legacy payloads is a separate governed operation.

### 10. Shared canonicalizer

The repository currently contains repeated private `_canonical_bytes` helpers across state, runtime, API, migration, and benchmark/evidence tooling.

A v2 implementation SHOULD centralize canonical serialization behind one versioned module/API rather than copying the algorithm again.

Callers SHALL request or bind a canonicalization profile explicitly where persisted or cryptographic identity depends on it.

A local convenience serializer MUST NOT silently become a new canonical scheme.

## Integrity-scheme consequences

The current SQLite canonical-state verifier already distinguishes recorded digest schemes and verifies legacy/full-JSON versus bucketed commitments separately. That existing pattern is the migration precedent.

V2 should preserve the same principle:

```text
recorded scheme
  -> choose matching canonicalizer + root algorithm
  -> full verification from canonical state
  -> trust/rebuild maintained index only after verification
```

The maintained digest index remains derived data. Canonical rows/state remain the verification source.

## Rust qualification consequence

#602 may continue qualifying deterministic primitives that do not depend on unresolved float-bearing persisted bytes.

Allowed while ADR-040/#609 is unresolved:

- tokenization/ranking primitives;
- SHA-256 byte digest primitives;
- non-floating canonical JSON subset;
- identity-first candidate prefilter/index primitives;
- matched performance work that does not claim persisted-state equivalence.

Blocked from promotion until this decision is resolved:

- Rust persistence/integrity parity for float-bearing rows;
- restart/checkpoint compatibility claims that rely on canonical float bytes;
- cross-language tamper-verification claims over affected state;
- migration of canonical SQLite state to a Rust-owned runtime.

## Evidence requirements for acceptance

ADR-040 SHALL remain Proposed until all of the following exist:

1. **Canonical-domain inventory**
   - every persisted/cryptographic `_canonical_bytes` surface is inventoried;
   - float reachability and arbitrary payload reachability are classified.

2. **Frozen language-neutral vectors**
   - strings/control escaping;
   - Unicode/non-BMP key ordering;
   - exact integers including values beyond binary64's exact integer range;
   - representative binary64 values near exponent thresholds;
   - integral floats;
   - negative zero;
   - subnormals and boundary values where practical;
   - explicit NaN/Infinity refusal vectors.

3. **Independent Python and Rust implementations**
   - both consume the same frozen vectors;
   - byte identity and digest identity are exact;
   - no tolerance or post-hoc fixture rewriting.

4. **Legacy migration evidence**
   - valid legacy state verifies before migration;
   - tampered legacy state refuses migration;
   - v2 state verifies after migration and restart;
   - interrupted/rolled-back migration leaves the legacy state valid and unchanged;
   - unsupported legacy values fail closed without partial conversion.

5. **Digest-scheme versioning**
   - old and new commitment identifiers cannot be confused;
   - maintained indexes are rebuilt/validated under the correct scheme;
   - no recorded digest silently changes meaning.

6. **Regression evidence**
   - retain/correct/forget/history/currentness behavior unchanged;
   - scope/tenant/isolation unchanged;
   - candidate/admission/ranking unchanged;
   - benchmark scores unchanged except for explicitly measured serialization/performance effects.

## Rejected alternatives

### Keep CPython JSON formatting as the cross-language doctrine

Rejected as the target because implementation behavior would become architecture by accident and ADR-028 portability would be weakened.

A Rust formatter could be engineered to mimic CPython, but that would qualify one implementation emulation rather than establish an implementation-neutral contract.

### Adopt RFC 8785/JCS wholesale

Rejected as the default candidate because it unnecessarily changes integer-domain and object-key-order semantics in addition to fixing float serialization.

JCS remains normative prior art for finite binary64 shortest-roundtrip formatting and invalid-number refusal.

### Serialize all numbers as strings

Rejected for the core profile because it changes ordinary JSON value types and would ripple into schemas and consumers.

Tagged numeric strings may remain appropriate for optional domains that require decimal/bignum semantics beyond this profile.

### Ignore float byte identity because hashes are implementation-local

Rejected because persisted commitments participate in restart verification, tamper detection, migration, and cross-language conformance. They are not ephemeral implementation details.

### Recompute old commitments using the new canonicalizer

Rejected because it would reinterpret historical evidence under a different byte contract and could misclassify valid state as tampered.

## Consequences

### Positive

- canonical bytes become explicit architecture rather than Python behavior;
- Rust and future runtimes can qualify persistence honestly;
- non-finite numeric behavior becomes fail-closed;
- migration is scheme-aware and evidence-preserving;
- legacy state remains verifiable;
- repeated serializer implementations can converge on one versioned module;
- cryptographic/integrity claims become easier to audit and reproduce.

### Costs

- another explicit persistence migration must be implemented and tested;
- legacy verification code must remain available for a compatibility window;
- binary64 canonicalization requires careful cross-language test vectors;
- exact arbitrary integers require runtimes to preserve values rather than casually passing through floating representations;
- canonicalization becomes an API/versioning concern instead of a private helper.

## Non-goals

ADR-040 does not:

- make Rust the preferred runtime;
- change memory authority, PAMA, lifecycle, ranking, or currentness semantics;
- require JCS as the general Agent Memory wire format;
- normalize Unicode;
- make digest equality equivalent to truth or authority;
- migrate state merely because a new canonical profile exists.

## Decision status

**Proposed.**

#609 owns qualification and migration evidence. #602 consumes the result for cross-language runtime parity but cannot accept this ADR merely by reproducing candidate vectors.
