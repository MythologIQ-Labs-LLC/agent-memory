# Agent Memory Gauntlet Orchestration Alpha

Status: implementation guidance for issue #558  
Contract version: `0.1.0`  
Authority effect: none

## Purpose

This document describes the first executable orchestration layer built on the
[Gauntlet System Adapter Contract](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md).

The alpha exists to prove that heterogeneous memory systems can enter a common
qualification flow without pretending that all systems expose the same architecture,
that all benchmarks share one metric, or that adapter translation creates capabilities.

The first executable profile is deliberately a **baseline/orchestration probe**. It is
not independent efficacy evidence.

## CLI

```bash
agent-memory gauntlet list
agent-memory gauntlet inspect gauntlet-orchestration-retrieval-probe-v1

agent-memory gauntlet validate-adapter fixtures/gauntlet/lexical-adapter.json

agent-memory gauntlet run \
  --system fixtures/gauntlet/lexical-adapter.json \
  --profile gauntlet-orchestration-retrieval-probe-v1 \
  --output-dir ./gauntlet-runs
```

A `stdio` manifest contains an executable startup command and therefore requires explicit
opt-in:

```bash
agent-memory gauntlet run \
  --system ./my-stdio-adapter.json \
  --profile gauntlet-orchestration-retrieval-probe-v1 \
  --allow-external-process
```

Validation never executes an adapter.

## Alpha transport boundary

Implemented:

- `in_process`, restricted to repository-trusted fixtures with
  `metadata.trusted_fixture=true`;
- persistent newline-delimited JSON `stdio`, with explicit execution opt-in and a
  per-operation response timeout.

Declared by the adapter contract but not yet executable:

- `http`.

An unsupported transport is an orchestration block, not a benchmark score.

## Destructive isolation rule

The first orchestration probe calls `reset`.

For this alpha, the orchestrator executes that profile only when the manifest declares:

```json
{
  "benchmark_isolation": {
    "strategy": "disposable_instance"
  }
}
```

This is intentionally narrower than the manifest schema. A declaration such as `tenant`,
`namespace`, `database`, or `remote_test_project` may eventually be sufficient, but the
orchestrator will not assume its teardown semantics before they are explicitly specified
and tested.

```text
declared isolation != proven safe reset boundary
```

## First probe

`gauntlet-orchestration-retrieval-probe-v1` uses three deterministic records and three
queries.

It exists to verify:

- capability negotiation;
- reset/write/recall invocation;
- transport state continuity;
- operation-envelope validation;
- explicit failure attribution;
- native-result retention;
- common Memory Evaluation normalization;
- reconstructable manifest/input identity.

Its provenance class is:

```text
baseline_or_probe
```

Therefore:

```text
probe pass != independent memory efficacy
probe score != product superiority
probe score != authority
```

The in-repository no-memory and lexical baselines intentionally produce different
retrieval results through the same orchestration contract.

## Evidence layout

Each executed run receives its own directory:

```text
<output-dir>/<run-id>/
├── adapter-manifest.json
├── native-results.json
├── normalized-run.json
└── qualification.json
```

The normalized run uses the existing Memory Evaluation common evidence contract.
Heterogeneous benchmark-native semantics remain in `native_results`; normalization does
not invent comparability.

A qualification result preserves distinctions such as:

```text
eligible
eligible_with_limitations
unsupported
invalid
blocked
complete
```

In particular:

```text
unsupported != failed
blocked != zero score
adapter failure != SUT failure
```

## Failure attribution

The orchestration boundary uses these sources where applicable:

```text
benchmark_input
benchmark_adapter
orchestrator
system_adapter
system_under_test
expected_refusal
```

Unexpected profile-runner exceptions are attributed to `benchmark_adapter`.
Transport/startup/envelope failures are attributed to `system_adapter`.
Safety or unsupported-orchestration decisions are attributed to `orchestrator`.
A valid response from the tested system may attribute its own refusal/error to
`system_under_test` or another contract-defined source.

## Security posture

`in_process` manifests can execute Python in the current process and are therefore
restricted to trusted repository fixtures.

`stdio` manifests can execute the startup command declared by the manifest. `run`
requires explicit `--allow-external-process`; `validate-adapter` does not execute it.

This alpha does not claim sandboxing of arbitrary hostile adapters.

## Explicit non-goals

This slice does not:

- freeze the canonical Agent Memory runtime adapter;
- accept ADR-039;
- create a universal memory-health score;
- flatten external benchmark protocols;
- implement the Governance Gauntlet;
- implement HTTP transport;
- treat the deterministic probe as independent benchmark evidence;
- change runtime authority or licensing.

## Next slices

Issue #559 builds the first executable Governance Gauntlet on this orchestration layer.
Issue #560 continues qualification of independent benchmark families against the
Benchmark Coverage Atlas.

The canonical Agent Memory adapter should be added only against the stable public runtime
contract rather than binding the Gauntlet to moving internal implementation details.
