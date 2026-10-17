# External lanes with `unspecified_intent_currentness` off and on (#819 lane 5)

Local runs only (no hosted CI). The candidate runtime is the one at `027da33`/`5b2cb39`; the
runs were taken at `2c6e990` (AMB) and recorded `f53d06a` (LongMemEval; the runner reads `HEAD`
at the end of a run, and `f53d06a` added only report files). Neither runner nor bridge was
edited: `with_open_option.py` patches `AgentMemory.open` to pass the option and counts
activations, then runs the unchanged script.

## Result: no effect on either lane

The activation never fired, because neither adapter declares typed propositions.

| Lane | Off | On | Reference | Activation fired | Typed propositions written |
|---|---|---|---|---:|---:|
| AMB PrecisionMemBench single-turn, retrieval | 15/77, P 0.1806, R 0.9535 | identical | accepted v6 lane: identical | 0 / 73 recalls | 0 / 35 |
| LongMemEval-S 500, session | R_all@5 0.823389, nDCG@5 0.863142 | identical | `main` `38f6a7d`: identical; parity-v4: identical | 0 / 500 | 0 |
| LongMemEval-S 500, turn | R_all@5 0.601432, nDCG@5 0.648611 | identical | `main` `38f6a7d`: identical | 0 / 500 | 0 |

### AMB (`amb-precisionmembench/`)

- Frozen AMB `03c1d0f`; bridge blob `3d9ccb3`, the same as the accepted v6 lane.
- Integrity self-check passes: 77/77, precision and recall 1.00.
- Off, on and accepted v6 are identical on all 77 cases: pass/fail, relevant beliefs and the returned context text.
- The `cross-fact.jsonl` sidecar is byte-identical across off, on and v6.

### LongMemEval-S (`longmemeval-s/`)

- Input: `longmemeval_s_cleaned.json`, sha256 `d6f21ea9…`, the same file as the accepted lanes. All 500 questions; the upstream-replicated scorer.
- **Off vs unmodified `main` `38f6a7d`** (separate worktree, no wrapper): every row identical at both granularities, timing aside.
- **On vs off**: ranked results, admitted counts and all metrics are identical for every question. The only differing field is the `cross_fact` diagnostic in 2 session rows and 304 turn rows.
  - With the option on, the guards now evaluate under unspecified intent and log refusals. At turn level: `relation_not_state_change` 1278 and `change_evidence_not_assertive:1` 7, against 55 and 2 with it off.
  - No fact was limited (`limited_count` 0 everywhere).
  - No relation reached the new typed-only check (`unspecified_intent_requires_typed_relation` 0).
- Against the latest accepted parity-v4 (`f5a79d23`):
  - Session: every row is identical.
  - Turn: ranked results and turn metrics are identical. 56 rows differ in the supplementary `turn_to_session` metric. Off, on and `main` all differ identically, so that difference predates this candidate.

## Departures from the accepted lane environments

- Python 3.13, not 3.12.
- The AMB venv installs the lane's exported constraints from PyPI without `pip install -e` of the checkout. AMB is imported from `src/` exactly as the bridge does.
- pip reported `agentrust-trace` wanting pydantic ≥ 2.13.5 against the locked 2.12.5. The bridge does not use it.
- The proxy blocks the host `tiktoken` downloads `cl100k_base` from. The same file was taken from a HuggingFace copy and verified against tiktoken's pinned sha256 `223921b7…`, then served from `TIKTOKEN_CACHE_DIR`.
- AMB is given the workflow's inert `GEMINI_API_KEY=retrieval-only-unused`. Retrieval mode makes no LLM calls.
