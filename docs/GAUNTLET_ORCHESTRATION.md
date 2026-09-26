# Agent Memory Gauntlet Orchestration Alpha

Status: implementation guidance for issues #558 and #559  
Contract version: `0.1.0`  
Authority effect: none

## Purpose

This document describes the executable orchestration layer built on the
[Gauntlet System Adapter Contract](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md).

The alpha exists to prove that heterogeneous memory systems can enter a common
qualification flow without pretending that all systems expose the same architecture,
that all benchmarks share one metric, or that adapter translation creates capabilities.

The first executable profiles are deliberately bounded:

- `gauntlet-orchestration-retrieval-probe-v1` is `baseline_or_probe` evidence;
- `governance-isolation-deletion-alpha-v1` is `gauntlet_native_gap` evidence.

Neither is independent external efficacy evidence.

## CLI

```bash
agent-memory gauntlet list
agent-memory gauntlet inspect gauntlet-orchestration-retrieval-probe-v1
agent-memory gauntlet inspect governance-isolation-deletion-alpha-v1

agent-memory gauntlet validate-adapter fixtures/gauntlet/lexical-adapter.json

agent-memory gauntlet run \
  --system fixtures/gauntlet/lexical-adapter.json \
  --profile gauntlet-orchestration-retrieval-probe-v1 \
  --output-dir ./gauntlet-runs
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

## Execution and destructive-operation consent

A `stdio` manifest contains executable startup content and therefore requires:

```text
--allow-external-process
```

Destructive operations are a separate consent boundary.

Profiles declare which operations are destructive and, where appropriate, which claimed
capability activates them. For example:

```text
retrieval probe:
    reset -> always active

governance alpha:
    reset  -> always active
    forget -> active only when deletion is positively claimed
```

A non-fixture adapter must declare:

```json
{
  "benchmark_isolation": {
    "strategy": "disposable_instance"
  }
}
```

That declaration is necessary evidence but is **not itself permission**.

The narrow compatibility flag:

```text
--allow-destructive-reset
```

is sufficient only when `reset` is the sole active destructive operation.

A profile that may issue another destructive operation, such as `forget`, requires:

```text
--allow-destructive-operations
```

So an external governance-alpha run that claims deletion normally requires:

```bash
agent-memory gauntlet run \
  --system ./my-governance-adapter.json \
  --profile governance-isolation-deletion-alpha-v1 \
  --allow-external-process \
  --allow-destructive-operations
```

Controlling invariants:

```text
declared isolation != proven safe destructive boundary
manifest claim != destructive-operation consent
claimed deletion != permission to delete arbitrary state
```

## Retrieval orchestration probe

`gauntlet-orchestration-retrieval-probe-v1` uses three deterministic records and three
queries.

It verifies:

- capability negotiation;
- reset/write/recall invocation;
- transport state continuity;
- operation-envelope validation;
- explicit failure attribution;
- native-result retention;
- common Memory Evaluation normalization;
- reconstructable manifest/input identity.

Its provenance class is `baseline_or_probe`.

```text
probe pass != independent memory efficacy
probe score != product superiority
probe score != authority
```

The in-repository no-memory and lexical baselines intentionally produce different
retrieval results through the same orchestration contract.

## Governance alpha

`governance-isolation-deletion-alpha-v1` executes claim-driven synthetic cases for tenant
and scope isolation, foreign-cardinality non-disclosure, deletion, and selected authority-
laundering pressure.

Its provenance class is `gauntlet_native_gap`.

See [Governance Gauntlet Alpha](GOVERNANCE_GAUNTLET_ALPHA.md) for case-level semantics,
negative controls, blocked claims, and the remaining real-system gate for issue #559.

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
Heterogeneous profile-native semantics remain in `native_results`; normalization does not
invent comparability.

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
governance case failure != harness execution failure
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

The alpha does not claim sandboxing of arbitrary hostile adapters.

System and adapter identifiers are schema-constrained before they can participate in run
paths, preventing manifest-controlled path traversal through run identity.

## Explicit non-goals

The orchestration alpha does not:

- freeze the canonical Agent Memory runtime adapter;
- accept ADR-039;
- create a universal memory-health or governance score;
- flatten external benchmark protocols;
- implement HTTP transport;
- treat probe or Gauntlet-native evidence as independent external validation;
- change runtime authority, naming, or licensing.

## Next slices

Issue #559 remains open until a real memory system runs the governance protocol in addition
to the composed evaluator controls.

Issue #560 continues qualification of independent benchmark families against the
Benchmark Coverage Atlas.

The canonical Agent Memory adapter should be added only against the stable public runtime
contract rather than binding the Gauntlet to moving internal implementation details.
