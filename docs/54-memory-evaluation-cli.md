# Memory Evaluation CLI

Status: implemented under #524 / #527, extended with integration inspection and validation under #652  
Canonical contributor entry point: [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md)

The installed `agent-memory` command exposes a small Memory Evaluation surface without changing ordinary runtime startup or benchmark execution protocols. Nothing under `agent-memory benchmark` executes a benchmark.

## Commands

List repository-owned benchmark integrations:

```bash
agent-memory benchmark list
agent-memory benchmark list --json
```

Inspect one committed integration, including its resolved Gauntlet relationship and whether each executed evidence row is bound to its committed report by exact digest and revision:

```bash
agent-memory benchmark inspect golden-keyed-retrieval-v1
agent-memory benchmark inspect agent-memory-longmemeval-retrieval-currentness-v1 --json
```

Validate a benchmark integration descriptor you authored, without importing or executing the runner, normalizer, or integrity controls it names:

```bash
agent-memory benchmark validate-integration ./my-benchmark.json
agent-memory benchmark validate-integration ./my-benchmark.json --json
```

List frozen same-harness comparator lanes, and validate one lane file against its schema and the registered benchmark integration (no execution):

```bash
agent-memory benchmark lanes
agent-memory benchmark validate-lane reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v1.json --json
```

Validate one result against the common benchmark-run contract:

```bash
agent-memory benchmark validate result.json
agent-memory benchmark validate result.json --json
```

Compare two compatible common results:

```bash
agent-memory benchmark compare baseline.json candidate.json
agent-memory benchmark compare baseline.json candidate.json --json
```

The comparison is fail-closed. Different benchmark revisions, frozen inputs, task profiles, selections, or sample counts are refused at run level. Metric deltas are emitted only where measurement state, direction, unit, denominator, and population are compatible.

There is no overall memory-health score.

## Exit status and refusals

| Code | Meaning |
| --- | --- |
| `0` | report emitted |
| `2` | refused: malformed input, unknown integration id, incompatible comparison, unsupported contract version |

A refusal in `--json` mode is a JSON object with `valid: false`, `status: refused`, the error text, and `authority_effect: none`, so automation never has to parse stderr.

## JSON report shapes

Every report carries `schema_version` (`1.1.0` for this CLI surface), `command`, and `authority_effect: none`.

| Command | `command` value | Stable keys |
| --- | --- | --- |
| `list` | `benchmark_list` | `profile_count`, `profiles[]` (`profile_id`, `benchmark_id`, `provenance_class`, `admission_state`, `owning_issue`, `runner`, `runner_kind`, `invocation_surface`, `external_system_entry`, `credentials`, `external_evidence_status`, `external_evidence[]`, `product_findings[]`, `dimensions[]`, `gauntlet`, `description`) |
| `inspect` | `benchmark_inspect` | everything under `validate-integration` plus `profile` |
| `validate-integration` | `benchmark_validate_integration` | `valid`, `path`, `integration_id`, `integration_digest_sha256`, `contract_version`, `admission_state`, `benchmark`, `provenance_class`, `invocation_surface`, `external_system_entry`, `credentials`, `runner`, `gauntlet` (`relationship`, `profile_id`, `status`), `evidence_binding[]`, `identity_findings[]`, `mapped_dimensions[]`, `unmapped_dimensions`, `negative_control_count`, `executed: false`, `descriptor` |
| `validate` | `benchmark_validate` | `valid`, `run_id`, `run_status`, `benchmark`, `system`, `measured_dimensions[]`, `run_digest_sha256` |
| `compare` | `benchmark_compare` | `comparison_status`, `comparison_identity`, `baseline`, `candidate`, `dimensions{}` |
| `lanes` | `benchmark_lanes` | `lane_count`, `lanes[]` (`lane_id`, `status`, `owning_issue`, `frozen_on`, `benchmark_integration`, `harness_revision`, `dataset`, `input_sha256`, `evaluator_mode`, `llm_calls`, `rows[]`, `lane_digest_sha256`), `executed: false` |
| `validate-lane` | `benchmark_validate_lane` | `valid`, `path`, `lane_id`, `status`, `lane_digest_sha256`, `resolution`, `summary`, `findings[]`, `executed: false`, `lane` |

`gauntlet.status` for an integration is one of `not_applicable`, `eligible`, `bound`, `profile_missing`, or `binding_invalid`. `identity_findings` lists source/input identity facts an operator must know before treating a result as comparable (for example "no static input digest: comparability is established per run").

## Registry

The registry is the set of committed descriptors in `reference/agentmem_ref/evaluation/integrations/`, validated against `schemas/memory-benchmark-integration.schema.json` on every load. `list` is a projection of those descriptors; no benchmark identity is restated in Python.

| integration | class | state | variant | status |
| --- | --- | --- | --- | --- |
| `swe-context-bench-lite-external-retrieval-v1` (#467) | `external_adapted` | blocked | protocol-comparable Lite (99 queries / 100 gold edges) | **blocked** on the exact frozen projection and selection provenance |
| `agent-memory-longmemeval-retrieval-currentness-v1` (#516) | `external_adapted` | evidence_partial | LongMemEval_S cleaned, full 500 questions | **complete** (#536; input sha256 `d6f21ea9…c442`; Agent Memory `f73b872`) |
| | | | LongMemEval_M cleaned | **complete** (input sha256 `9d79e552…495f`; Agent Memory `409098f`) |
| | | | upstream model-judged QA | not run |
| `agent-memory-agentmembench-memdialogue-operational-v1` (#517) | `external_adapted` | evidence_partial | MemDialogue v2 at upstream defaults | **complete** (#533; input sha256 `33632710…ca2a6`; Agent Memory `03197cd`) |
| | | | upstream LLM-judged retrieval recall | not run |
| | | | M6 LLM portability | not run |
| `golden-keyed-retrieval-v1` (#652) | `baseline_or_probe` | evidence_complete | lexical baseline integrity controls | **complete** (contributor demonstration; excluded from the portfolio scorecard) |
| `amb-precisionmembench-retrieval-v1` (#601 / #640) | `external_independent` | evidence_partial | lane row agent-memory (control) | **complete** (run 37349431401; Agent Memory `703be5b`; `reports/benchmarks/amb/…/agent-memory-703be5ba1c7e/`) |
| | | | lane row bm25 (baseline) | **complete** (run 37349435243; AMB `03c1d0f`; `…/bm25-703be5ba1c7e/`) |
| | | | lane row mem0-explicit (comparator, Mem0 OSS 2.2.1) | **complete** (run 37351804149; mem0 `94c3fe9`; `…/mem0-explicit-b38d91631169/`) |
| | | | lane row hindsight | **blocked** on a benchmark-agnostic provider configuration |

Registry metadata is descriptive. A `complete` entry is bound to a committed report: `check_evidence_binding()` resolves the entry's `report_binding` paths inside the report and refuses a mismatch, and the registry tests run that check for every committed descriptor. A listing never upgrades synthetic or probe evidence into external evidence; the provenance class travels with the row.

## Execution stays benchmark-specific

This CLI does not pretend heterogeneous memory benchmarks have one universal execution command. Each descriptor names its runner and the runner's kind:

```text
reference/run_swe_context_bench_harness.py            repository_script
reference/run_longmemeval.py                          repository_script
reference/run_agentmembench.py                        repository_script
agentmem_ref.evaluation.benchmark_golden_keyed_retrieval:run_golden_keyed_retrieval
                                                      gauntlet_profile_runner (agent-memory gauntlet run)
```

A `gauntlet_profile_runner` is the one shape that can be executed against any system implementing the Gauntlet adapter contract; the descriptor's `gauntlet.relationship` says whether a benchmark has one, could have one, or should never have one.

## Dependency boundary

The installed `agent-memory` entry point is `agentmem_ref.console:main`. It routes `benchmark ...` to `agentmem_ref.evaluation.cli`, `gauntlet ...` to `agentmem_ref.evaluation.gauntlet_cli`, and every other command to the runtime CLI. The runtime layer never imports the evaluation package; the package-layout test and `test_runtime_import_remains_independent_from_evaluation` enforce this.

## Authority boundary

```text
benchmark list != external evidence
integration validation != benchmark quality
benchmark validation != benchmark quality
benchmark comparison != memory authority
benchmark score != recall admission
benchmark score != mutation authority
```

All CLI evidence reports retain `authority_effect: none`.
