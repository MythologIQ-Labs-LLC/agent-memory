# Independent review: Agent Memory on frozen AMB, PrecisionMemBench single-turn (15/77)

Scope: repo HEAD 810cf05 (bridge, guard and runner blobs are identical to b9a9307, the evaluated revision; only a test docstring changed after it), AMB 03c1d0f. Nothing under review was modified.

Checks I ran myself:
- Re-ran `agent-memory` and `bm25` through `scripts/run_amb_local_evidence.py` into `review/rerun-*`. Both exited 0, and both match the committed rep1/bm25 results with 0 differences.
- Ran an isolation and k probe against the real AMB `Document` and dataset (`review/isolation_probe.py`).
- Ran comparator mutation tests (`review/mut_*.json`).
- Re-hashed every committed blob.
- Recomputed every README metric.

**Bottom line:** 15/77 is a faithful score from AMB's own scorer. I found no oracle or leak path. The remaining issues are README accuracy and blind spots in the tooling.

## 1. Adapter correctness: PASS

- The runtime only ever receives `content`, `observed_at=timestamp`, a hashed logical id and a hashed scope (`amb_agent_memory_bridge.py:259-271`).
  - `context`, which carries `beliefId=…`, and the scope `tags` stay in the bridge's side index. Their only use is echoing them back on the returned `Document` (`:99-108`, `:336-346`).
  - `retrieve()` never receives `gold_ids` or `meta` (base.py:47).
  - `query_timestamp` is echoed in raw output and not used (`:358-359`). PMB never sets it anyway.
- I grepped `agentmem_ref` runtime code for belief ids and dataset names: no benchmark-specific paths.
- **k is honoured.** The bridge passes `budget=k` to the facade's `apply_return_budget` and does no truncation or re-ranking of its own (`:317`, `:327-346`).
  - The probe returned 2 docs at k=2 and 1 doc at k=1, out of 3 admitted.
  - In the evidence, every case has `retrieved_count <= retrieval_limit` except `budget-zero-graceful-empty`. That is AMB's behaviour, not the bridge's: `retrieval.py:34` turns 0 into 20 via `or 20`, and the scorer ignores retrieval when cap=0.
- **Low:** returned fact UUIDs that are not in the index are silently dropped (`:331-335`). They are recorded only in `raw["unmapped_admitted"]`, which is misnamed (they are *returned*, not admitted). AMB discards `raw_response` (runner.py:267, `raw_response=None`), so a drop would leave no trace in the evidence.
- **Low:** re-ingesting the same document creates a second fact UUID (probe: index grew from 35 to 36). This has no effect on a single-ingest run.

## 2. Evaluator identity: PASS

- The AMB checkout is at 03c1d0f with an empty `git status --porcelain`; only `.datasets/` and `__pycache__` are ignored.
- All 7 recorded scoring blobs equal `git rev-parse HEAD:<path>`.
- The venv imports `memory_bench` from `/tmp/agent-memory-benchmark/src` (editable install).
- `git diff 50b30a7 03c1d0f` on runner, retrieval mode, precisionmembench, models and base is empty.
- The guard patches only `cli._resolve_gemini_key`, `cli.get_answer_llm` and `runner.GeminiJudge`.
  - For `task_type == "retrieval"`, the runner goes straight to `dataset.score_retrieval` (runner.py:222-227).
  - `judge_llm` is only read for non-retrieval or non-coding tasks (:375, :451).
  - Under the guard, any judge use raises, so it fails closed.
- Guarded and stock-CLI outputs are identical for both providers (0 differences).
- **Low:** `requested_mode()` returns the *first* `--mode` (`amb_retrieval_no_llm.py:53-57`), but Typer uses the *last*. `--mode retrieval --mode rag` would install the guard on a rag run. Judging still fails closed, but the answer path then gets `llm=None`.

## 3. Data isolation: PASS (low notes)

- **Isolation is real but logical.** All users share one SQLite store and one tenant, and each user gets a distinct hashed `scope` that the runtime enforces at candidate generation.
  - Probe with test-user and the other-user belief's own text as the query: 32 candidates, and `b-other-user-leak-check` was not among them.
  - The same query as other-user returns it.
  - brand-new-user returns 0.
- **No state carried over between runs.**
  - The evidence script refuses an existing directory (`run_amb_local_evidence.py:118`).
  - Every run gets a fresh output and `_store` directory, with `reset=not skip_ingestion` (that is, True).
  - This matters because AMB's `_save` merges with any previous file at the same path (runner.py:494).
- **Fixtures match the pins.**
  - The sha256 of both fixtures matches the README and the lane pins.
  - Each result's `query`, `scope` and `expect` equal the fixture, in the same order.
- **Low:** the isolation case is weak. It passes even though 9 unrelated beliefs are returned, and BM25 passes it too. "Cross-user isolation 1/1" shows only that the leak is absent.
- **Low:** fixture hashing ignores `PRECISIONMEMBENCH_DATA_PATH`, and the scorer-affecting `AMB_PMB_RETURN_CAP` is neither cleared nor recorded. Post hoc, `meta.return_cap` is absent and the embedded cases match the fixture, so this run was unaffected.

## 4. Output integrity: CONCERN (minor)

- **Hashes all agree.**
  - All 46 `sha256.txt` entries equal `git show HEAD:` blobs.
  - Every committed `outputs_sha256` entry matches.
  - The CSVs match the JSON (correct and judge_reason, 77/77).
- **Numbers that match exactly:**
  - accuracy, pass-type counts, precision and recall
  - per-category results and the four blank queries
  - p50 and max latency, ingest time, wall time and RSS in MiB
  - store size (668 KiB) and the tiktoken hash
  - Hindsight's 66/77, 33/43, 0.8481 and 1.0
- **Medium:** the p95 figures use the lowest-valued method (numpy `lower`/`nearest`, rank 69 of 73), and the README doesn't say so. For rep1, 25.5 ms is reported; linear gives 26.4 and nearest-rank gives 27.7.
- **Medium:** "guarded vs unmodified CLI … (raw provider responses included)" is vacuous. AMB always writes `raw_response=None`, and I counted 0 non-null.
- **Low:** "Agent Memory increment … about 6 MiB" is within run-to-run noise. stock-cli bm25 reached 1,356,720 KiB, which is higher than agent-memory rep1 at 1,352,276. The underlying difference is 5.3 MiB.
- **Low:** "harness revision … the same" as Hindsight is not literally true. Hindsight was published at 50b30a7, though the scoring files are unchanged since then. "Directly comparable" is strong given that Hindsight receives `retrieval_filter` (scope, state and name tags); the README does disclose this.
- **Low:** `_store` outputs for rep2, smoke and stock-cli are listed in `outputs_sha256` but were not committed, so they can't be verified. The `HF_HUB_OFFLINE` override isn't mentioned in the README.
- There is no leaderboard overclaim; the README states clearly that this is a self-run.

## 5. Failure handling: CONCERN

- **These behave correctly:**
  - Provider exceptions propagate out of `asyncio.gather` (no per-case catch, and retries only on transient strings), so the run aborts with no final file in batch mode.
  - A refused write raises (`bridge:272-276`).
  - `wait4` and `waitstatus_to_exitcode` record the exit code faithfully, and the script returns it.
  - A blank query is short-circuited by AMB, and the bridge returns [] for one anyway.
- **Medium (comparator blind spots, confirmed by mutation):**
  - `.get()` treats a missing key as equal to `None`. I deleted `score` from all 77 cases and the summary `category`: 0 differences reported.
  - Duplicate `query_id`s collapse in the dict. A verdict flip on the duplicate was hidden, although the run was still flagged by the membership check.
  - `cases_compared` reports only the left file's count.
- **Medium:** the README's reproduce command (`unittest discover … test_amb_*.py`) silently skips all 6 pytest-style bridge tests. It ran 16 tests, none from `test_amb_agent_memory_bridge.py`. Under pytest the two files under review pass (12 tests).
- **Low:** the AMB dirty check uses `--untracked-files=no`. Scorer blobs are hashed *after* the run. Credential stripping covers only 6 variable names.

## Recommended fixes

1. In `compare_amb_runs.py`, distinguish a missing key from `None` (use a sentinel), reject duplicate `query_id`s, and report counts for both sides.
2. In the README, state the p95 method or switch to nearest-rank or linear. Drop "(raw provider responses included)". Remove the 6 MiB increment claim or back it with repeated runs. Say "same scorer blobs (Hindsight published at 50b30a7)".
3. Fix the reproduce command to use `pytest` (or convert the bridge tests to unittest).
4. In the evidence script, clear or record `AMB_PMB_RETURN_CAP`, `PRECISIONMEMBENCH_DATA_PATH` and `AGENT_MEMORY_AMB_*`. Hash fixtures from the path AMB actually resolves. Include untracked files in the dirty check. Hash blobs before the run as well as after.
5. In the bridge, fail or log to a sidecar on unmapped returned facts, and rename the field to `unmapped_returned`.
6. In the guard, reject repeated `--mode`, or read the last occurrence to match Typer.
7. Commit or drop the `_store` hashes for the non-rep1 runs so the manifest can be verified.
