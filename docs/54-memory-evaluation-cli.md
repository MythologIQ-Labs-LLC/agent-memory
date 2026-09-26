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

The registry contains the repository's accepted external benchmark profiles. Each profile lists its external evidence variants and their status separately:

| profile | owning issue | variant | status |
| --- | --- | --- | --- |
| `swe-context-bench-lite-external-retrieval-v1` | #467 | protocol-comparable Lite (99 queries / 100 gold edges) | **blocked** on the exact frozen projection and selection provenance |
| `agent-memory-longmemeval-retrieval-currentness-v1` | #516 | LongMemEval_S cleaned, full 500 questions | **complete** (#536; input sha256 `d6f21ea9…c442`; Agent Memory `f73b872`) |
| | | LongMemEval_M cleaned | not run |
| | | upstream model-judged QA | not run |
| `agent-memory-agentmembench-memdialogue-operational-v1` | #517 | MemDialogue v2 at upstream defaults | **complete** (#533; input sha256 `33632710…ca2a6`; Agent Memory `03197cd`) |
| | | upstream LLM-judged retrieval recall | not run |
| | | M6 LLM portability | not run |

Registry metadata is descriptive. `runner_ready` or `implemented_bounded_profile` does not mean an external run exists. A `complete` entry is bound to a committed report: a test checks that each report's input SHA-256 and Agent Memory revision match the registry. A profile listing never upgrades synthetic evidence into external evidence.

## Execution stays profile-specific

This CLI does not pretend heterogeneous memory benchmarks have one universal execution command. Current profile runners retain their own protocol-specific arguments, including:

```text
reference/run_swe_context_bench_harness.py
reference/run_longmemeval.py
reference/run_agentmembench.py
```

A future common execution layer is appropriate only where a real system-adapter contract can preserve each benchmark's native semantics without reducing them to the least interesting common denominator.

## Dependency boundary

The installed `agent-memory` entry point is `agentmem_ref.console:main`. It routes `benchmark ...` to `agentmem_ref.evaluation.cli` and every other command to the runtime CLI. The runtime layer (`agentmem_ref/runtime/cli.py`) never imports the evaluation package, and the package-layout test enforces this.

## Authority boundary

```text
benchmark list != external evidence
benchmark validation != benchmark quality
benchmark comparison != memory authority
benchmark score != recall admission
benchmark score != mutation authority
```

All CLI evidence reports retain `authority_effect: none`.
