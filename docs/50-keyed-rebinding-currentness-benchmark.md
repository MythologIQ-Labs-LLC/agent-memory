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
  -> check every previously superseded fact identity
  -> midpoint close/reopen
  -> continue corrections
  -> verify matched controls
  -> wrong-scope recall probe
  -> final close/reopen
  -> verify current facts, history, state versions, and configuration binding
```

Stable logical identity is the benchmark key. Corrections create new current fact identities while prior identities remain historical rather than becoming current again.

## Measurements

The report intentionally keeps four dimensions separate.

### Quality

- qualified correction commit rate;
- current fact retrieval rate;
- stale fact candidate rate;
- stale fact admission rate;
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
- stale/superseded currentness violations;
- explicit `authority_effect = none` for retrieval evidence.

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
rebound key -> current value advances, stale identities stay historical
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

The existing Long Horizon Memory Benchmark workflow runs the exact PR revision and uploads the resulting JSON artifact. The benchmark fails only on structural/currentness/governance/recovery invariants, never on wall-clock latency.
