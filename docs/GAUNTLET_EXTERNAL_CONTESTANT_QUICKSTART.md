# Agent Memory Gauntlet: External Contestant Quickstart

Status: public entrant guidance for issue #637  
Contract version: `0.1.0`  
Authority effect: none

## Goal

This is the shortest supported path for a memory-system author to enter the Agent Memory Gauntlet without importing Agent Memory runtime code or learning Agent Memory's internal governance model.

The example proves this boundary:

```text
your memory system
  -> thin system adapter
  -> Gauntlet stdio contract
  -> capability negotiation
  -> benchmark/profile execution
  -> benchmark-native evidence
  -> normalized, coverage-aware evidence
```

The adapter is a translation boundary, not a place to manufacture capabilities the system does not have.

```text
adapter translation != system capability
unsupported != failed
derived != native
benchmark score != authority
```

## 1. Install the Gauntlet CLI

From a checkout of this repository:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell, activate the environment with the normal PowerShell virtual-environment activation command instead of the POSIX `.` command.

Confirm the CLI:

```bash
agent-memory gauntlet list
```

## 2. Start from the self-contained example

The repository includes:

```text
examples/gauntlet/minimal_stdio_adapter.py
examples/gauntlet/minimal-stdio-adapter.json
```

`minimal_stdio_adapter.py` uses only the Python standard library. It does not import `agentmem_ref` or the Agent Memory runtime. The example is deliberately a tiny lexical memory so the contract remains visible.

The adapter process reads one JSON request envelope per line from stdin and writes exactly one JSON response envelope per line to stdout.

For a real system, replace only the system-specific calls behind these operations:

```text
describe
health
reset
remember
recall
```

Do not implement `correct`, `forget`, `history`, `checkpoint`, or `recover` unless the system really exposes semantics that can be declared honestly as `native`, `mapped`, or `derived`.

## 3. Validate the manifest without executing it

```bash
agent-memory gauntlet validate-adapter examples/gauntlet/minimal-stdio-adapter.json
```

Validation checks contract/schema consistency. It does not launch the external process.

A manifest binds at least:

- exact system identity and revision;
- exact adapter identity and revision;
- transport;
- declared capabilities and support classes;
- benchmark isolation strategy;
- authority effect.

For real comparison evidence, replace example identities with exact package, release, commit, build, configuration, model, backend, or other revision identifiers needed to reconstruct the system actually tested.

## 4. Inspect a profile before execution

```bash
agent-memory gauntlet inspect gauntlet-orchestration-retrieval-probe-v1
```

Inspection shows which capabilities and support classes the profile accepts.

A retrieval-only entrant does not need to pretend it supports lifecycle or governance features merely to run retrieval pressure.

## 5. Run the credential-free retrieval probe

The example uses a stdio child process, so execution requires explicit opt-in. The profile also resets benchmark-owned disposable state, so reset requires a separate destructive-operation opt-in.

```bash
agent-memory gauntlet run \
  --system examples/gauntlet/minimal-stdio-adapter.json \
  --profile gauntlet-orchestration-retrieval-probe-v1 \
  --allow-external-process \
  --allow-destructive-reset \
  --output-dir ./gauntlet-runs
```

Those flags are intentionally separate:

```text
permission to execute a manifest command
  !=
permission to mutate/reset benchmark state
```

A destructive profile that can issue operations beyond reset requires the broader `--allow-destructive-operations` boundary where documented by that profile.

Never point a destructive Gauntlet profile at production state. Use a disposable process, namespace, database, tenant, container, or test project whose destruction is explicitly authorized.

## 6. Read the evidence package

A completed run creates a revision-bound directory beneath the selected output root:

```text
<output-dir>/<run-id>/
├── adapter-manifest.json
├── native-results.json
├── normalized-run.json
└── qualification.json
```

Read them as different evidence layers:

- `adapter-manifest.json` binds the contestant and adapter identity;
- `native-results.json` preserves profile-native observations and semantics;
- `normalized-run.json` exposes dimensions eligible for the common Memory Evaluation contract;
- `qualification.json` records negotiation, coverage, limitations, unsupported surfaces, blockers, and final run posture.

Normalization does not make heterogeneous systems magically equivalent. Native evidence remains available precisely because flattening meaningful differences would make the comparison easier to read and less true, a classic software achievement.

## 7. Support classes

Declare each capability honestly:

| Support | Meaning |
| --- | --- |
| `native` | The tested system directly implements the semantic capability. |
| `mapped` | The adapter translates to an equivalent native capability without adding material semantics. |
| `derived` | Adapter/composition logic materially contributes to the capability. |
| `unsupported` | This system/configuration does not provide it. |
| `unknown` | Support cannot currently be established truthfully. |

A profile may accept only some support classes for a required capability.

Never convert `unsupported`, `unknown`, or `blocked` into score zero unless the benchmark's own protocol defines that outcome as task failure.

## 8. Error attribution

The Gauntlet keeps infrastructure and SUT outcomes separate. Failure sources include:

```text
benchmark_input
benchmark_adapter
orchestrator
system_adapter
system_under_test
expected_refusal
```

Examples:

- child process cannot start -> `system_adapter`;
- adapter emits malformed JSON -> `system_adapter`;
- profile cannot safely perform an operation -> `orchestrator`;
- the real system returns a valid error/refusal -> `system_under_test` or profile-defined expected refusal;
- benchmark input itself is invalid -> `benchmark_input`.

Adapter bugs must not become bad scores for the tested memory system.

## 9. Adapting a real system

A useful adapter should stay boring.

For each requested operation:

1. validate/parse the Gauntlet request;
2. translate only the fields your system supports;
3. invoke the public/supported system interface;
4. preserve native identifiers/output as evidence where safe;
5. return the common response envelope;
6. expose unsupported semantics rather than emulating them invisibly.

Do not feed benchmark question IDs, gold labels, expected answers, or hidden evaluator state into ingestion or ranking.

Do not add a vector index, tenant filter, correction ledger, temporal reranker, or deletion tracker in the adapter and then report the resulting behavior as a native capability of the contestant.

## 10. Moving beyond the probe

The retrieval probe is transport/orchestration evidence, not a market-quality result.

Use `agent-memory gauntlet list` and `inspect` to identify profiles applicable to the system's real capabilities. Independent benchmark profiles retain their own protocol, inputs, metrics, and evidence class. Gauntlet-native profiles remain visibly different from independent external evidence.

Before publishing a comparative result, bind:

- system/revision/configuration;
- adapter revision;
- benchmark/profile/input digest;
- retrieval/context budget;
- model/embedder/judge identity where applicable;
- execution environment where performance is reported;
- raw artifacts;
- failures, unsupported surfaces, and limitations.

There is intentionally no universal memory-health score.

## Related contracts

- `docs/GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`
- `docs/GAUNTLET_ORCHESTRATION.md`
- `schemas/gauntlet-system-adapter.schema.json`
- `schemas/gauntlet-operation-envelope.schema.json`
- issue #637
