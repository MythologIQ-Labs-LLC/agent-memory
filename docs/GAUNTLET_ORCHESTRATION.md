# Agent Memory Gauntlet Orchestration Alpha

Status: executable orchestration layer (#558, #559, #571, #637, #652)  
Contributor entry point: [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md)  
Contract version: `0.1.0`  
Authority effect: none

## Purpose

This document describes the executable orchestration layer built on the
[Gauntlet System Adapter Contract](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md).

The alpha exists to prove that heterogeneous memory systems can enter a common
qualification flow without pretending that all systems expose the same architecture,
that all benchmarks share one metric, or that adapter translation creates capabilities.

The executable profiles are deliberately bounded:

- `gauntlet-orchestration-retrieval-probe-v1` is `baseline_or_probe` evidence;
- `golden-keyed-retrieval-v1` is `baseline_or_probe` evidence bound to the benchmark integration of the same id (the benchmark-author golden path);
- `governance-isolation-deletion-alpha-v1` is `gauntlet_native_gap` evidence;
- `durability-recovery-alpha-v1` is `gauntlet_native_gap` evidence.

None is independent external efficacy evidence. Every profile declares `benchmark_integration` (`null` for Gauntlet-native suites and probes) and `kind`; `registry.validate_registry_relationships()` refuses a profile whose kind differs from the descriptor it binds and a profile that claims an external class without binding any descriptor. The orchestrator additionally refuses a runner whose returned `profile_kind` differs from the registered kind, and records the bound integration id as a top-level `benchmark_integration` field in `qualification.json` (`null` for Gauntlet-native suites).

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

The alpha uses the generalized refusal code `destructive_operation_opt_in_required` for
missing destructive-operation consent. Its message identifies whether the reset-only flag
is sufficient or the broader operations flag is required.

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

Repository-trusted in-process fixtures may execute destructive operations only against
explicit benchmark-owned disposable state. `trusted_fixture=true` is an execution-trust
classification, not evidence that the underlying memory system supplies a governance
capability natively.

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

The evaluator contains positive and negative composed fixtures plus a real Agent Memory
contestant through the public `AgentMemory` facade. The real-system adapter translates
neutral operations only and deliberately refuses to manufacture a cross-tenant claim for
the single-tenant local composition.

See [Governance Gauntlet Alpha](GOVERNANCE_GAUNTLET_ALPHA.md) for case-level semantics,
negative controls, the real-system capability posture, and claims intentionally reported
as blocked until neutral lifecycle/evidence-injection contracts exist.

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

- accept ADR-039;
- create a universal memory-health or governance score;
- flatten external benchmark protocols;
- implement HTTP transport;
- treat probe or Gauntlet-native evidence as independent external validation;
- change runtime authority, naming, or licensing.

The Agent Memory governance contestant is a bounded conformance adapter for the stabilized
public facade. It is not a precedent for binding future external adapters to Agent Memory
internals.

## Open work

#559 (governance alpha), #571 (first durability/recovery slice), #637 (external contestant golden path), and #652 (contributor contracts) are closed with CI evidence.

Still open at the orchestration boundary:

- a neutral evidence-bearing / review-gated mutation envelope, without which `DUR-COR-001` (durable correction) and the governance claims that need evidence injection remain visibly `unsupported` or `blocked` rather than simulated;
- crash/process-kill recovery, checkpoint reconstruction, concurrency/stale-writer, and migration cases for durability;
- `http` transport;
- binding an external benchmark integration (LongMemEval or AgentMemBench) to a `gauntlet_profile_runner` for the same-harness comparator work (#640).
