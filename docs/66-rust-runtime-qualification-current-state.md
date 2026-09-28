# Rust runtime qualification current state

Status: **ACTIVE / SHADOW ONLY**  
Owner: #602  
Architecture: ADR-028 remains Accepted and unchanged.

Agent Memory has not moved to Rust. The qualified production/reference runtime remains Python.

Current accepted Rust-shadow evidence:

- exact `relevance_tokens` parity on frozen vectors;
- exact admitted-set BM25 IEEE-754 score-bit parity on the qualified Ubuntu CI profile;
- exact UTF-8 SHA-256 parity on frozen vectors.

Current candidate evidence:

- exact canonical JSON byte parity for the explicitly non-floating domain.

A new cross-language determinism gap was discovered during this work: persisted SQLite integrity commitments can contain `TypedRelation.retrieval_weight` floats, while the current canonical byte helper inherits floating-number spelling from CPython's JSON encoder. Issue #609 now owns the language-neutral numeric serialization and migration decision.

Therefore the active runtime direction remains:

```text
Python public/reference runtime
        |
        +--> Rust shadow deterministic primitives
                 |
                 +--> prove exact parity first
                 +--> benchmark matched hot paths later
                 +--> no FFI/runtime promotion without evidence
```

The preferred hypothesis remains a Python facade with a Rust performance/assurance kernel **only if** later matched measurements show material value. A wholesale rewrite is not authorized.

Next admissible #602 work while #609 is open:

1. finish non-floating canonical-byte qualification;
2. qualify candidate prefilter/index hot paths that do not depend on unresolved persisted numeric bytes;
3. define matched performance workloads;
4. keep state/integrity and restart-lifecycle Rust promotion gated on #609 where float-bearing canonical bytes are involved.
