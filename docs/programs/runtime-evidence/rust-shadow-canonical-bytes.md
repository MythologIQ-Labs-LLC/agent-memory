# Rust shadow canonical-byte evidence map

Issue: #602  
Determinism follow-on: #609

This evidence slice deliberately separates two claims:

1. **qualified candidate**: exact cross-language canonical bytes for JSON values containing no floating numbers;
2. **not yet qualified**: canonical bytes for float-bearing persisted state.

The separation exists because SQLite typed-relation row commitments include `retrieval_weight: float`, and the current Python canonical serializer inherits number spelling from CPython.

The non-floating slice is safe to qualify independently because its byte contract is explicit and fixture-bound. It cannot be generalized to float-bearing state until #609 establishes a language-neutral numeric contract and a compatible persisted-digest transition.

No runtime authority changes result from this evidence.
