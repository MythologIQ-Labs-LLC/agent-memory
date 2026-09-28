# Canonical JSON v2 qualification plan

Status: **pre-implementation qualification plan**  
Owner: #609  
Decision candidate: ADR-040  
Consumer: #602 Rust runtime qualification

## Purpose

Freeze the evidence and migration requirements for a language-neutral integrity serializer before Python or Rust implementation is allowed to define the answer by accident.

## Current defect boundary

The existing canonical helper is deterministic in CPython but delegates floating-number spelling to CPython's JSON encoder. Float-bearing `TypedRelation` rows participate in SQLite integrity commitments, so this behavior is already part of persisted state identity.

The problem is not limited to Rust. Any non-Python runtime needs an explicit byte contract, and existing Python state needs a versioned migration path if that contract changes.

## External prior art

RFC 8785 / JCS is the primary prior-art reference for cryptographic JSON canonicalization and finite IEEE-754 binary64 shortest-roundtrip serialization.

Agent Memory does not propose wholesale JCS adoption. JCS also constrains integers to the I-JSON/binary64 domain and sorts keys by UTF-16 code units, which would broaden the migration beyond the defect discovered by #602.

JCS serializes both positive and negative IEEE zero as `0`. Verified RFC 8785 errata additionally recommends rejecting parsed `-0` because the sign is lost by canonicalization. Agent Memory's candidate v2 profile instead proposes preserving the host-independent distinction between integer `0`, float `0.0`, and float `-0.0`. That is an explicit Agent Memory rule and must be qualified independently rather than called JCS compliance.

## Freeze order

The following order is mandatory:

```text
architecture candidate
  -> case inventory
  -> expected-byte vectors frozen from the stated contract
  -> vector review
  -> independent Python implementation
  -> independent Rust implementation
  -> exact cross-language comparison
  -> migration implementation
  -> restart/tamper/rollback evidence
  -> ADR acceptance ruling
```

No implementation result may be used to revise expected bytes in place. Any correction after freeze requires a new vector version and an explicit reason.

## Vector set A: literals, strings and key ordering

Must include:

- null / true / false;
- empty string;
- quote and reverse-solidus escaping;
- all predefined control escapes;
- at least one remaining U+0000..U+001F escape requiring lowercase `\\u00xx`;
- BMP Unicode;
- non-BMP Unicode;
- canonically equivalent but byte-distinct Unicode strings proving no normalization;
- object keys where Unicode scalar ordering differs from UTF-16 code-unit ordering;
- nested object/array recursion.

## Vector set B: exact integers

Must include:

- 0, 1, -1;
- values around 2^53;
- values beyond IEEE-754 exact-integer range;
- large positive and negative integers within the repository's intended practical limits;
- explicit refusal evidence for an implementation that cannot preserve a supplied integer exactly.

Integers never pass through binary64 merely to serialize them.

## Vector set C: finite binary64 floats

Expected values must be defined from binary64 bit patterns, not decimal source strings alone.

Must include:

- +0.0;
- -0.0;
- 1.0 and -1.0;
- smallest positive/negative subnormal;
- maximum finite positive/negative binary64;
- values on both sides of fixed-vs-exponent thresholds;
- values requiring shortest-roundtrip tie decisions;
- integral binary64 values that would serialize without a decimal point under ECMAScript/JCS;
- representative ordinary fractional values;
- exponent sign and leading-zero normalization cases.

ADR-040's candidate type-preserving extension must be visible in expected bytes. In particular, float values must not silently collapse to integer lexical form.

## Vector set D: invalid numeric domain

Both implementations must refuse:

- NaN;
- +Infinity;
- -Infinity.

Refusal must occur before commitment bytes are emitted.

## Vector set E: type distinctions

The contract must explicitly prove whether these pairs are byte-distinct:

```text
0       vs 0.0
0.0     vs -0.0
1       vs 1.0
2^53    integer vs binary64 representation
```

The current ADR-040 candidate requires these distinctions where the logical input type differs.

## Canonical surface inventory

Before implementation promotion, every repeated `_canonical_bytes`-style surface must be classified as one of:

- persisted integrity identity;
- runtime journal/checkpoint identity;
- configuration binding;
- API/receipt digest;
- benchmark/evidence-only utility;
- non-normative convenience serialization.

For each surface record:

- reachable value types;
- float reachability;
- arbitrary attribute/payload reachability;
- recorded scheme/version if any;
- migration requirement;
- whether legacy verification must remain available.

## Integrity scheme transition

The candidate migration must not redefine existing names.

At minimum, design evidence must demonstrate distinct old/new identities equivalent to:

```text
bmerkle-v1 -> bmerkle-v2
gsect-v1   -> gsect-v2
```

The exact names are part of the implementation review, but the old identifiers remain bound to old canonical bytes forever.

## Migration cases

Required positive cases:

1. valid legacy state verifies under the legacy serializer;
2. logical state is decoded only after verification;
3. v2 representability validation passes;
4. v2 row/index/root material is computed;
5. migration commits transactionally;
6. restart verifies the new scheme independently;
7. memory lifecycle/admission/ranking behavior is unchanged.

Required negative cases:

- tampered legacy state refuses migration;
- wrong recorded scheme refuses verification;
- unsupported/non-finite legacy value refuses migration;
- injected failure before commit leaves legacy state valid;
- rollback does not leave mixed v1/v2 index rows;
- v1 bytes are never checked with v2 rules;
- v2 bytes are never accepted under a v1 scheme name.

## Cross-language acceptance

Python and Rust must consume the same frozen semantic vectors and independently emit identical bytes and SHA-256 digests.

For binary64 vectors, comparison is exact. No numeric tolerance applies because this is a serialization contract, not a numerical-analysis metric.

## Governance stop lines

```text
serializer implementation != canonical doctrine
byte equality != truth
successful migration != authority change
new scheme != permission to discard legacy evidence
Rust parity != Rust runtime promotion
```

ADR-040 remains Proposed until the frozen vectors, two independent implementations, migration evidence, and regression evidence are all reviewed.