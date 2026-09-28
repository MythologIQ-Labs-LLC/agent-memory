# Rust shadow canonical-byte qualification v1

Status: **CANDIDATE / CI NOT YET OBSERVED**  
Owner: #602  
Related determinism gap: #609

## Scope

This slice tests exact Python-to-Rust canonical byte identity for the explicitly non-floating JSON domain only:

- null;
- booleans;
- integers;
- UTF-8 strings;
- arrays;
- string-keyed objects with lexicographically sorted keys.

Frozen oracle:

`reference/fixtures/runtime-kernel/canonical-json-nonfloat-v1.tsv`

The Python side uses the current SQLite runtime `_canonical_bytes` implementation. The Rust side uses a dependency-free typed value model that cannot represent floats.

## Why floats are excluded

#602 discovered that float spelling is already inside persisted integrity state because `TypedRelation.retrieval_weight` is hashed as part of canonical SQLite relation rows.

The current Python helper inherits float spelling from CPython's JSON encoder. That is deterministic for Python, but it is not yet a language-neutral architecture contract.

#609 therefore gates any claim of persisted state/integrity parity for floating values and owns the required numeric serialization plus digest-scheme migration decision.

## Acceptance rule

PASS requires:

1. the Python runtime reproduces every frozen canonical byte string exactly;
2. the Python runtime reproduces every frozen SHA-256 digest exactly;
3. Rust independently emits identical UTF-8 bytes for the same semantic cases;
4. Rust reproduces the same SHA-256 digests;
5. no tolerance, normalization, or fixture correction is introduced after observing Rust output.

A PASS here qualifies only the non-floating canonical-byte subset. It does not qualify full persistence, integrity, checkpoint, or lifecycle parity.
