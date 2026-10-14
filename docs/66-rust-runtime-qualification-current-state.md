# Rust runtime qualification (revision-bound #602 snapshot)

**Status:** Rust shadow evidence only; **no qualified production Rust runtime**. This page was initially written while #609 remained open and now records the later architecture decision separately.  
**Owner:** [#602](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/602) (open).  
**Architecture:** ADR-028 is Accepted. [ADR-040](adr/ADR-040-versioned-language-neutral-canonical-json-for-integrity.md) is **Accepted** at the doctrine layer; [#609](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/609) is **closed**. Doctrine acceptance does not enable production persistence.

Agent Memory has **not** moved to Rust. The qualified public/reference runtime remains Python. Check the [runtime baseline register](../reports/runtime/baseline-register.json) for the exact currently published runtime revision rather than inferring production readiness from this Rust-shadow note.

## Original Rust-shadow evidence

At the original #602 snapshot boundary, the demonstrated parity covered:

- exact `relevance_tokens` parity on frozen vectors;
- exact admitted-set BM25 IEEE-754 score-bit parity on the qualified Ubuntu profile;
- exact UTF-8 SHA-256 parity on frozen vectors;
- candidate canonical JSON byte parity for an explicitly non-floating domain.

These are **bounded shadow/determinism results**, not parity for the full persisted-state, correction, deletion, or restart path. The original gap was float-bearing SQLite commitments, including `TypedRelation.retrieval_weight`, which depend on CPython's JSON floating-number spelling under legacy schemes.

## #609 / ADR-040 disposition

Issue #609 completed its architecture qualification and closed after the canonicalization inventory, 44 frozen v2 vectors, independent Python/Rust parity, compatibility registry/refusal cases, verify-old-before-recommit migration evidence, and the maintainer's Accepted ADR-040 ruling. The exact evidence and decision lineage remains with [#609](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/609) and [ADR-040](adr/ADR-040-versioned-language-neutral-canonical-json-for-integrity.md).

**Acceptance is architectural, not activation.** Until separately qualified and authorized:

- `bmerkle-v2` and `gsect-v2` remain candidate/non-emittable persistence identities;
- ordinary runtime recovery must continue to verify legacy identities with their original rules;
- automatic migration, candidate-envelope acceptance in production, and replacing the existing serializer are not authorized;
- Rust cannot assume persisted-integrity, state ownership, or restart-lifecycle parity solely because language-neutral canonical bytes were qualified.

## Executable direction for #602

```text
qualified Python public/reference runtime
    |
    +--> independently qualified Rust shadow primitives
             |
             +--> exact frozen parity for bounded operations
             +--> matched performance / resource measurements
             +--> separate production authorization for FFI or persisted-state ownership
```

A Python facade with a Rust performance/assurance kernel remains a hypothesis **only if** matched workload evidence shows material value. A wholesale rewrite is not authorized by either #609 closure or ADR-040 acceptance. Current implementation priorities and blocker state belong to the live [#602](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/602) issue, not this historical status page.
