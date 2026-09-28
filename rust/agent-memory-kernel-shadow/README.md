# Agent Memory Rust shadow kernel

Status: **evaluation-only / not runtime-linked**  
Owner: #602  
Controlling architecture: ADR-028

This crate asks whether selected deterministic Agent Memory primitives can be reproduced in Rust without changing their semantics.

It is not a replacement runtime, an FFI dependency, a production package, or a declaration that Rust is the preferred implementation language.

## First slice

The initial slice shadows:

- `relevance_tokens` from `reference/agentmem_ref/runtime/ranking_policy.py`;
- `admitted_set_bm25` from the same module;
- BM25 constants `k1=1.2`, `b=0.75`;
- sorted query-term accumulation introduced by #576.

The cross-language oracle is frozen at:

`reference/fixtures/runtime-kernel/bm25-v1.tsv`

The Python runtime must reproduce every frozen token vector and IEEE-754 score bit. The Rust shadow must then reproduce the same vectors independently.

The fixture was frozen before Rust execution evidence was observed. A Rust mismatch is evidence to investigate, not permission to edit the Python oracle or loosen the fixture after the fact.

## Why score bits are strict in this slice

#576 established that floating accumulation order can change BM25's last bits and can alter true near-tie ordering. The first shadow therefore attempts exact cross-language score-bit parity on the CI platform.

If exact parity cannot be maintained across supported platforms because transcendental math differs, #602 must define a language-neutral deterministic numeric contract before a Rust kernel can be promoted. Possible future decisions include a shared deterministic math implementation or another explicitly versioned scoring representation. A tolerance chosen after seeing failures is not acceptable promotion evidence.

## Next slices, only after this one qualifies

1. time-neutral SHA-256 candidate fallback and canonical byte primitives;
2. candidate prefilter/index hot paths;
3. integrity/state primitives;
4. minimal `open -> remember -> recall -> restart` shadow lifecycle;
5. matched performance and operational comparison;
6. only then consider Python FFI or a native Rust runtime profile.

ADR-028 remains unchanged: implementation language is not doctrine.
