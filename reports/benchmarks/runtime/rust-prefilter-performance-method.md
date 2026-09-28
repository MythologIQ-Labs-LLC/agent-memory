# Rust candidate-prefilter matched performance method

Status: **method frozen / result pending CI**  
Owner: #602  
Qualified semantic surface: #591 identity-first pre-materialization candidate prefilter

## Question

Does the already-qualified Rust shadow materially improve the compute cost of the #591 candidate-prefilter hot path relative to the current Python semantics on the same runner and workload?

This is not a full Agent Memory runtime benchmark.

## Frozen workload

Each implementation independently builds the same 20,000 projected rows outside the timing window.

Each row contains only the fields available to the #591 pre-materialization path:

- UUID;
- selected-group boolean;
- identity-eligibility boolean;
- fact text.

The row content and flags are deterministic formulas, not random data.

Eight fixed queries exercise common overlap, numeric tokens, duplicate query terms, punctuation, and a no-hit query.

Each implementation warms all eight queries once, then runs eight timed iterations of all queries for 64 per-query samples.

## Parity gate before performance interpretation

Both implementations compute a SHA-256 signature over every query's ordered `(uuid, score_bits)` result set.

Four executions are collected in one GitHub Actions job:

```text
Python -> Rust
sleep
Rust -> Python
```

All four result signatures and workload identities must match exactly. Any mismatch is a conformance failure and invalidates the timing comparison.

## Timing scope

Included:

- candidate tokenization;
- group/identity boolean filtering;
- lexical set overlap;
- score computation;
- deterministic score-desc / UUID ordering.

Excluded:

- row/workload generation;
- Rust compilation;
- SQLite query execution;
- fact materialization;
- canonical admission;
- lifecycle/governance work;
- FFI/binding overhead.

Therefore a speedup here is evidence about one bounded compute kernel, not the complete runtime.

## Reported metrics

For each implementation:

- median total elapsed time across the two execution orders;
- median p50 query time;
- median p95 query time;
- median projected rows examined per second;
- individual total times for order-sensitivity inspection.

Relative evidence:

- Rust total-time speedup multiple;
- Rust throughput multiple.

No fixed promotion threshold is declared before the first evidence run. The result informs #602 but cannot by itself select runtime candidate B/C/D.

## Governance

```text
hot-path speedup != full-runtime speedup
microbenchmark win != rewrite authority
candidate generation != recall admission
result parity failure -> timing result invalid
implementation language != doctrine
```
