# Memory Evaluation CLI

Status: profile discovery and evidence utilities under #524 / #527.

The installed `agent-memory` command exposes a small Memory Evaluation surface without changing ordinary runtime startup or benchmark execution protocols.

## Commands

List repository-owned profiles:

```bash
agent-memory benchmark list
agent-memory benchmark list --json
```

Validate one report against the common benchmark-run contract:

```bash
agent-memory benchmark validate result.json
agent-memory benchmark validate result.json --json
```

Compare two compatible common reports:

```bash
agent-memory benchmark compare baseline.json candidate.json
agent-memory benchmark compare baseline.json candidate.json --json
```

The comparison is fail-closed. Different benchmark revisions, frozen inputs, task profiles, selections, or sample counts are refused at run level. Metric deltas are emitted only where measurement state, direction, unit, denominator, and population are compatible.

There is no overall memory-health score.

## Profile registry

The initial registry contains the repository's established external benchmark profiles:

- `swe-context-bench-lite-external-retrieval-v1`, owned by #467;
- `agent-memory-longmemeval-retrieval-currentness-v1`, implemented through #516.

Registry metadata is descriptive. `runner_ready` does not mean an external run exists, and a profile listing never upgrades synthetic evidence into external evidence.

SWE-ContextBench remains explicit that protocol-comparable external evidence is blocked on the exact frozen projection and selection provenance required by #467.

LongMemEval is registered as an implemented bounded profile. The registry does not assert a full external dataset result merely because the runner exists.

## Execution stays profile-specific

This CLI does not pretend heterogeneous memory benchmarks have one universal execution command. Current profile runners retain their own protocol-specific arguments, including:

```text
reference/run_swe_context_bench_harness.py
reference/run_longmemeval.py
```

A future common execution layer is appropriate only where a real system-adapter contract can preserve each benchmark's native semantics without reducing them to the least interesting common denominator.

## Authority boundary

```text
benchmark list != external evidence
benchmark validation != benchmark quality
benchmark comparison != memory authority
benchmark score != recall admission
benchmark score != mutation authority
```

All CLI evidence reports retain `authority_effect: none`.
