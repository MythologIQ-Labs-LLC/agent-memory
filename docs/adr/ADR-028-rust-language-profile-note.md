# ADR-028 qualification note: Rust shadow evidence

This note is informational. It does not modify ADR-028 status or decision text.

As of the #602 qualification program, Rust has independently reproduced selected deterministic Agent Memory primitives from frozen cross-language oracles:

- relevance tokenization;
- admitted-set BM25 ordering/score bits on the qualified Ubuntu CI profile;
- UTF-8 SHA-256 digest vectors.

The active canonical-byte slice also exposed a language-neutral determinism gap in floating-number serialization for persisted integrity commitments. That gap is tracked by #609 and must be resolved before Rust can claim persistence/integrity parity where float-bearing rows are committed.

The evidence therefore continues to support ADR-028's original posture: implementation language is subordinate to explicit behavioral contracts, and Rust promotion requires demonstrated value without weakening deterministic/governed semantics.
