# Scope-distinct successor AMB lane: local execution at `2f4b8a1b`

Lane `amb-precisionmembench-retrieval-v7-scope-distinct-v1` (digest `7ebbe01d…`). This execution grants nothing:
`authority_effect: none`, `acceptance: not_granted`.

## Execution identity

| Item | Value |
|---|---|
| Executed revision | `2f4b8a1b103bafb8a405b76f0924f9b2c6872283`, run from a clean detached worktree |
| Protected runtime tree | `reference/agentmem_ref` = `975b09412b096a9eac4a92478e7d3a39700ba5d9` |
| Runtime Baseline checker | `TRANSITION` v6 → v7, 28 declared blobs, contract `1.6.0` → `1.8.0` |
| Declaration blob | `981108866e45a46b9e96ab283517324d6349e586` |
| Source blobs, raw-byte hashed and equal to the lane pins | bridge 0.5.0 `535da278…`, runner `f2ff518e…`, Mem0 bridge `ce41b1f5…` |
| AMB harness | `03c1d0f1…`, `verify_amb_checkout` passed, PrecisionMemBench self-check 77/77 |
| Fixtures | `input_sha256` `caf5869b…`; the importer re-hashed them from the pinned URLs |
| Selection | full: `query_limit 0`, no return cap, retrieval mode, no model |

## How it ran

The rows ran in a local cloud container, not a GitHub-hosted runner. The run ids `local-amb-v7sd-*` are not GitHub
run ids, so the importer's `workflow_run.url` does not resolve.

`run_amb_row_sd.sh` mirrors `amb-competitive.yml` for this lane id:

- the successor `LANE_FILE`;
- raw-byte source blob checks;
- `run_amb_external_scope_distinct.py`;
- `bridge_blobs` taken from the lane `source_blobs`.

Environments:

- Python 3.12.3 with `uv 0.8.17`, built under constraints from `scripts/amb_harness_constraints.py`;
- the mem0-explicit row adds `mem0ai==2.2.1` and removes fastembed;
- package lists are in `pip-freeze-*.txt`;
- tiktoken `cl100k_base` comes from litellm's vendored copy (sha256 `223921b7…`), because the session's network policy
  denies its download host.

## Results

The evidence was imported by `scripts/import_amb_lane_evidence.py` into
`reports/benchmarks/amb/amb-precisionmembench-retrieval-v7-scope-distinct-v1/`.

| Row | Strict passes | Precision | Recall | vs accepted v6 (every field except timing and run name) |
|---|---|---|---|---|
| agent-memory (control) | 15/77 | 0.1806 | 0.9535 | 77/77 equal |
| bm25 | 8/77 | 0.0536 | 0.9651 | 77/77 equal |
| mem0-explicit | 10/77 | 0.1049 | 1.0 | 77/77 equal |

`parity.json`, from `scripts/check_amb_scope_distinct_v7_parity.py` at `7ad7936d`:

- verdict **EQUAL**;
- 77/77 cases and 73/73 cross-fact records;
- 4 no-recall cases, 0 limited.

That checker was hardened in `7ad7936d` from the independent review's findings, before any candidate output was read.

## Still open

The checker cannot verify provenance: a deliberately perturbed copy of v6 would still pass. Acceptance needs this
lane executed by the hosted `amb-competitive.yml` workflow, with the run's `head_sha`, inputs, conclusion and
artifact digest checked on GitHub.
