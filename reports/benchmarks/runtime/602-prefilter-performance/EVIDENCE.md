# #602 matched candidate-prefilter performance evidence

Status: **PASS / bounded hot-path evidence**  
Workflow: `Rust Candidate Prefilter Performance`  
Workflow run: `36487679509`  
PR: #614  
Branch head evaluated: `da8c0c84e1800f47b5ee569735322d67852922e3`  
GitHub pull-request merge checkout: `ed12562a458333353312060385e0f7824f2c56f7`  
Base main: `a24e993958d741379993341e8b3f63ed37482df3`

## Raw artifact

- artifact ID: `10999893635`
- artifact name: `rust-prefilter-performance-ed12562a458333353312060385e0f7824f2c56f7`
- artifact ZIP SHA-256: `99b050d26d3d32b4d8f9fea079586e3a920fa717a2c5946383cb1bd918c84889`
- retained raw files: comparison JSON, both Python runs, both Rust runs, execution revision, Python/Rust/Cargo versions, `uname`, and `lscpu`.

Repository-frozen comparison: `comparison.json`.

## Execution environment

- GitHub-hosted Ubuntu 24.04 runner;
- Linux `6.17.0-1022-azure` x86_64;
- 4 logical CPUs, Intel Xeon Platinum 8573C;
- Python `3.12.14`;
- rustc `1.98.1 (48a229cea 2026-09-01)`;
- cargo `1.98.1 (797e8a9bc 2026-08-05)`.

This environment identity bounds the performance claim. The semantic parity fixture remains the stronger cross-language contract evidence.

## Workload

- contract: `591_identity_first_prefilter_compute_v1`;
- 20,000 deterministic projected rows;
- 8 fixed queries;
- 8 timed iterations per run after warmup;
- 64 per-query samples per run;
- two execution orders: Python -> Rust and Rust -> Python;
- row generation excluded;
- Rust compilation excluded;
- SQLite query execution, materialization, final admission, lifecycle, governance, and FFI excluded.

## Result parity gate

All four executions produced the same ordered-result signature:

`ea2a12c19df6c059d75e768b2ebae0044547ea358f1a9033a6da56564e15b18b`

Disposition: **PASS**.

Timing is admissible only because the result signature and workload identity match.

## Matched timing

| metric | Python | Rust | relative |
| --- | ---: | ---: | ---: |
| median total | 1485.717 ms | 597.273 ms | Rust **2.488x** faster |
| median p50 query | 23.616 ms | 9.276 ms | Rust ~2.55x lower |
| median p95 query | 26.950 ms | 10.535 ms | Rust ~2.56x lower |
| projected rows examined/sec | 861,584 | 2,143,123 | Rust **2.487x** throughput |

Individual total runs were stable enough to make the direction credible:

- Python: 1496.739 ms, 1474.694 ms;
- Rust: 600.136 ms, 594.410 ms.

## Interpretation

This is the first matched evidence that Rust provides material value on an actual Agent Memory hot-path contract rather than only reproducing deterministic semantics.

It strengthens runtime candidate **B, Python facade + Rust performance/assurance kernel**, because the qualified candidate-prefilter compute path is roughly 2.49x faster under this bounded same-runner workload while preserving exact result identity.

It does **not** establish that:

- the complete Agent Memory runtime is 2.49x faster in Rust;
- SQLite candidate retrieval is 2.49x faster;
- FFI preserves this advantage;
- persistence/state/restart should move to Rust;
- native Rust runtime candidate C is preferable;
- Python should be removed.

The next meaningful performance slice must include the integration costs required to consume this kernel, especially Python↔Rust boundary overhead and the proportion of end-to-end search latency attributable to the qualified compute segment.

## Governance boundary

```text
matched hot-path speedup != full-runtime speedup
performance advantage != authority
candidate generation != recall admission
Rust kernel value != native-Rust runtime decision
benchmark evidence != migration permission
```
