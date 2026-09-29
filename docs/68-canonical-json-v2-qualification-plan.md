# Canonical JSON v2 qualification plan

Status: **pre-implementation qualification plan**  
Owner: #609  
Decision candidate: ADR-040  
Consumer: #602 Rust runtime qualification

## Purpose

Freeze the evidence and migration requirements for a language-neutral **persistence/integrity** serializer before Python or Rust implementation is allowed to define the answer by accident.

This plan no longer assumes that Agent Memory should have one universal canonical JSON scheme. PR #615 proved the repository already contains multiple deliberate canonicalization families.

## Current defect boundary

The #609 inventory found 219 canonicalization candidates in the scanned Python roots:

- 202 Python sorted/compact JSON call sites;
- 17 direct RFC 8785/JCS call sites;
- 0 parse errors.

Seven Python-sorted-JSON sites fall into the runtime/persistence discovery bucket. Manual classification identifies `reference/agentmem_ref/state/sqlite_substrate.py` as the currently proven float-bearing persisted-integrity surface because `TypedRelation.retrieval_weight` participates in row hashes and bucket/root commitments.

The existing Python helper is deterministic in CPython but delegates floating-number spelling to CPython's JSON encoder. Any non-Python runtime therefore needs an explicit byte contract for the affected persistence domain.

Existing JCS-bound identity/evidence surfaces are not migration targets merely because v2 exists.

## External prior art

RFC 8785 / JCS is the primary prior-art reference for cryptographic JSON canonicalization and finite IEEE-754 binary64 shortest-roundtrip serialization.

Agent Memory does not propose wholesale JCS adoption for the Python-shaped persistence domain. JCS constrains integers to the I-JSON/binary64 domain and sorts keys by UTF-16 code units, which would broaden the migration beyond the discovered defect.

JCS serializes positive and negative IEEE zero as `0`. Agent Memory's candidate v2 profile instead proposes preserving integer/float lexical identity, including a distinct `-0.0`. That is an Agent Memory persistence rule, not JCS compliance, and must be independently qualified.

## Freeze order

The following order is mandatory:

```text
architecture candidate
  -> canonicalization-family inventory
  -> consequence / reachability classification
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

No implementation result may revise expected bytes in place. A correction after freeze requires a new vector version and explicit provenance.

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
- object keys where Unicode scalar ordering differs from RFC 8785/JCS UTF-16 code-unit ordering;
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

Expected values are identified by their IEEE-754 binary64 bit patterns, not by host-language decimal literals alone.

Must include:

- +0.0;
- -0.0;
- 1.0 and -1.0;
- smallest positive/negative subnormal;
- maximum finite positive/negative binary64;
- values on both sides of fixed-vs-exponent thresholds;
- values requiring shortest-roundtrip decisions;
- integral binary64 values that JCS/ECMAScript would spell without a decimal point;
- representative ordinary fractional values;
- exponent sign and leading-zero normalization cases.

The expected finite-number base spelling is the RFC 8785 / ECMAScript shortest-roundtrip representation. The candidate type-preserving extension then applies:

1. binary64 negative zero -> `-0.0`;
2. if the finite float base token contains neither `.` nor `e`, append `.0`.

The frozen fixture must record the bit pattern, expected numeric token, and expected complete canonical JSON bytes.

## Vector set D: invalid numeric domain

Both implementations must refuse before emitting commitment bytes:

- NaN;
- +Infinity;
- -Infinity.

The fixture records these as refusal cases, not string tokens.

## Vector set E: type distinctions

The contract must explicitly prove byte distinctions for:

```text
0       vs 0.0
0.0     vs -0.0
1       vs 1.0
2^53 integer vs the corresponding binary64 value
```

The current ADR-040 candidate requires distinct canonical bytes wherever logical input type differs.

## Canonicalization-domain inventory

PR #615 supplies the first repository-wide family inventory and manual runtime/persistence classification.

For each migration-relevant identity surface the final evidence must record:

- serializer/canonicalization family;
- consequence class;
- reachable value types;
- float/non-finite reachability;
- arbitrary payload reachability;
- recorded scheme/version;
- migration requirement;
- legacy-verification requirement.

Remaining reachability work is specifically required for generic raw runtime configuration and restart/checkpoint durable envelopes. Helper shape alone is not proof of float reachability.

## Existing JCS domains

Direct RFC 8785/JCS identities discovered by #615 remain bound to JCS unless separately versioned.

```text
existing JCS identity
    !=
automatic v2 migration target
```

The v2 implementation may share infrastructure with a JCS implementation, but scheme selection must remain explicit.

## Integrity scheme transition

Existing scheme names must never be reinterpreted under new bytes.

`bmerkle-v1` is directly implicated because float-bearing canonical row bytes participate in its substrate commitments. A successor identity such as `bmerkle-v2` is therefore expected if ADR-040 is accepted.

Other schemes, including `gsect-v1`, advance **only if** final reachability analysis proves that their committed byte domain changes. Version bumps are evidence-bearing compatibility boundaries, not synchronization theater.

For every affected scheme the design evidence must prove:

```text
legacy scheme -> exactly one legacy canonicalizer/root contract
v2 scheme     -> exactly one v2 canonicalizer/root contract
```

Scheme/canonicalizer confusion must fail closed.

## Migration cases

Required positive cases:

1. valid legacy state verifies under the legacy serializer and scheme;
2. logical state is decoded only after verification;
3. v2 representability validation passes;
4. v2 row/index/root material is computed;
5. migration commits transactionally;
6. restart independently verifies the new scheme;
7. memory lifecycle/admission/ranking behavior is unchanged.

Required negative cases:

- tampered legacy state refuses migration;
- wrong recorded scheme refuses verification;
- unsupported/non-finite legacy value refuses migration;
- injected failure before commit leaves legacy state valid;
- rollback does not leave mixed old/new index rows;
- legacy bytes are never checked with v2 rules;
- v2 bytes are never accepted under a legacy scheme name;
- an existing JCS-bound evidence identity is never rewritten as v2 merely because migration code is running.

## Cross-language acceptance

Python and Rust consume the same frozen semantic vectors and independently emit identical bytes and SHA-256 digests.

Binary64 comparison is exact. No numeric tolerance applies because this is serialization identity, not numerical analysis.

The two implementations must not share the same formatting implementation through FFI for the qualification run; independence is part of the evidence.

## Governance stop lines

```text
serializer implementation != canonical doctrine
same helper shape != same identity domain
existing JCS identity != v2 migration target
byte equality != truth
successful migration != authority change
new scheme != permission to discard legacy evidence
Rust parity != Rust runtime promotion
```

ADR-040 remains Proposed until the frozen vectors, remaining reachability classification, two independent implementations, scheme map, migration evidence, and regression evidence are all reviewed.
