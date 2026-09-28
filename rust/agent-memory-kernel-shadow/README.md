# Agent Memory Rust shadow kernel

Status: **evaluation-only / not runtime-linked**  
Owner: #602  
Controlling architecture: ADR-028

This crate asks whether selected deterministic Agent Memory primitives can be reproduced in Rust without changing their semantics.

It is not a replacement runtime, an FFI dependency, a production package, or a declaration that Rust is the preferred implementation language.

## Current bounded slice

The shadow currently covers:

- `relevance_tokens` from `reference/agentmem_ref/runtime/ranking_policy.py`;
- `admitted_set_bm25` from the same module;
- BM25 constants `k1=1.2`, `b=0.75`;
- sorted query-term accumulation introduced by #576;
- UTF-8 SHA-256 digest reproduction against Python `hashlib` vectors.

Cross-language oracles are frozen at:

- `reference/fixtures/runtime-kernel/bm25-v1.tsv`;
- `reference/fixtures/runtime-kernel/sha256-v1.tsv`.

The Python runtime must reproduce the frozen vectors first. The Rust shadow then reproduces the same vectors independently.

The fixtures are frozen before their corresponding Rust execution evidence is observed. A Rust mismatch is evidence to investigate, not permission to edit the Python oracle or loosen the fixture after the fact.

The SHA-256 implementation is dependency-free for this evidence slice so the result is not coupled to third-party crate resolution. It is not a recommendation to ship hand-rolled cryptography in a production Rust runtime. Any promoted runtime would use a reviewed cryptographic implementation behind the already-qualified byte contract.

## Why BM25 score bits are strict

#576 established that floating accumulation order can change BM25's last bits and can alter true near-tie ordering. The shadow therefore attempts exact cross-language score-bit parity on the CI platform.

The first qualification run at `6d4b6de` passed: Python and Rust reproduced every frozen token vector and every BM25 IEEE-754 score bit exactly on the Ubuntu CI profile, including the exact-tie case. That is evidence for portability on the qualified platform, not yet a cross-platform guarantee.

If later platforms cannot preserve exact parity because transcendental math differs, #602 must define a language-neutral deterministic numeric contract before a Rust kernel can be promoted. A tolerance chosen after seeing failures is not acceptable promotion evidence.

## Next slices, only after deterministic primitives qualify

1. canonical byte/serialization primitives under an explicit cross-language contract;
2. candidate prefilter/index hot paths;
3. integrity/state primitives;
4. minimal `open -> remember -> recall -> restart` shadow lifecycle;
5. matched performance and operational comparison;
6. only then consider Python FFI or a native Rust runtime profile.

ADR-028 remains unchanged: implementation language is not doctrine.
