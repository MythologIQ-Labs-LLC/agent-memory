# Keyed Rebinding and Stale-Value Resistance Benchmark

Status: implementation/evaluation slice for #483 under harvest closeout #470.

## Purpose

Agent Memory already proves individual correction/currentness, restart recovery, governed recall, and history behavior. This benchmark adds a different pressure: repeated corrections to the same stable logical keys over several rounds while matched control keys remain unchanged.

The workload was motivated by one bounded lesson identified during the current UOR-R4 review:

```text
exact logical key
  -> versioned values
  -> repeated rebinding / overwrite pressure
  -> matched controls
  -> explicit stale-value measurement
```

The inspected source revision is:

```text
UOR-Foundation/uor-r4
552d847d49fb263966165004b835f2f53cccaae1
```

The repository was recorded as MIT at that revision. This benchmark independently synthesizes the evaluation pressure. It copies no UOR-R4 code, schema text, geometric model, or distinctive documentation expression.

## Executed path

The runner is:

`reference/run_keyed_rebinding_benchmark.py`

It uses only the public Agent Memory facade and the qualified local SQLite profile:

```text
AgentMemory.open
  -> remember deterministic rebinding keys
  -> remember matched controls
  -> attempt one unqualified correction
  -> repeat qualified correction rounds
  -> governed recall after every correction
  -> measure every previously superseded fact identity at candidate and admission layers
  -> midpoint close/reopen
  -> continue corrections
  -> verify matched controls
  -> wrong-scope recall probe
  -> final close/reopen
  -> verify current facts, history, state versions, and configuration binding
```

Stable logical identity is the benchmark key. Corrections create new current fact identities while prior identities remain historical rather than becoming current again.

## Candidate generation is not current admission

The first executable run caught an important benchmark mistake rather than an Agent Memory defect. The initial benchmark assumed a superseded fact must never appear in candidate generation. That is stronger than Agent Memory's architecture and would make historical evidence artificially undiscoverable.

The actual invariant is:

```text
historical / superseded fact
  -> MAY remain discoverable as candidate evidence
  -> MUST retain stale/currentness metadata
  -> MUST NOT be admitted as current context
```

This follows the existing boundary:

```text
candidate generation != governed final admission
```

The benchmark therefore keeps `stale_fact_candidate_rate` as a diagnostic measurement. It does not turn candidate presence into a conformance failure. `stale_fact_admission_rate == 0` is the load-bearing currentness gate.

Changing retrieval to hide all historical candidates merely to make a benchmark green would erase useful provenance and teach the test the wrong architecture. The benchmark was corrected instead.

## Measurements

The report intentionally keeps four dimensions separate.

### Quality

- qualified correction commit rate;
- current fact retrieval rate;
- stale fact candidate rate, diagnostic only;
- stale fact admission rate, currentness gate;
- matched-control stability rate;
- history preservation rate.

A stale fact is measured by its exact superseded fact identity, not by whether an old query phrase happens to retrieve the new current value for the same logical key.

### Performance

- update latency observations;
- recall latency observations;
- total wall time;
- persistent state bytes.

Timing is observational and is not a conformance gate.

### Governance

- whether an unqualified correction silently committed;
- wrong-scope admission count;
- stale/superseded currentness violations at final admission;
- explicit `authority_effect = none` for retrieval evidence;
- explicit statement that candidate presence itself has no authority effect.

### Recovery

- restart count;
- current fact mismatches after restart;
- configuration digest stability;
- final current fact identity, state version, and event count for each rebinding key.

No aggregate health score is emitted.

## Why matched controls matter

A system can appear to handle rebinding correctly simply because every key is being rewritten and nothing stable is checked. The benchmark therefore seeds the same number of unchanged control keys as rebinding keys.

A passing run must show both:

```text
rebound key -> current value advances; stale identities may remain historical candidates but never regain current admission
control key -> original current value remains stable
```

That distinction is useful beyond any one external research project. It prevents a correction benchmark from rewarding indiscriminate churn.

## Architecture boundary

This work does not adopt UOR-R4 as a runtime or geometry model.

```text
external research lesson
  -> benchmark pressure
  -> native Agent Memory APIs
  -> existing PAMA mutation governance
  -> existing governed recall admission
```

It does not change identity doctrine, mutation authority, recall authority, or the accepted Agent Memory architecture.

## Non-claims

A passing result does not establish:

- UOR geometric-memory claims;
- public benchmark parity with another system;
- answer-generation quality;
- learned retrieval control;
- distributed persistence behavior;
- production 1.0 readiness.

The benchmark is one native evaluation improvement harvested from external research pressure while preserving Agent Memory ownership and governance boundaries.

## Local execution

```bash
PYTHONPATH=reference python reference/run_keyed_rebinding_benchmark.py \
  --agent-memory-commit 0123456789abcdef0123456789abcdef01234567 \
  --output keyed-rebinding-memory.json
```

The existing Long Horizon Memory Benchmark workflow runs the exact PR revision and uploads the resulting JSON artifact. The benchmark fails on currentness, governance, structural, matched-control, and recovery invariants. Historical candidate visibility and wall-clock latency remain diagnostic observations rather than authority or conformance gates.
