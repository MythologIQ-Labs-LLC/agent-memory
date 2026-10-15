# Erratum: Cognee subset50 preregistration names the wrong contender (2026-10-15)

Reported in #811 ([first finding](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/811#issuecomment-6192667723), [follow-up](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/811#issuecomment-6195875473)). The original file is kept unchanged as the historical pre-run record. This note corrects it, and neither file is edited retroactively.

## What is wrong

`preregistration.json` in this directory is a byte-identical copy of `817-jev-mem/subset50/preregistration.json` (Git blob `f6ebd32a`). It was copied in at 05:18:55 UTC, before the first Cognee question ran. Two of its fields are wrong for this directory:

- `backend: "jev_mem_laya"` should be `"cognee_gliner_local"`.
- `external_backend: ["longmemeval_jev_mem_bridge:install_longmemeval_jev_mem_backend"]` should be `["longmemeval_cognee_bridge:install_longmemeval_cognee_backend"]`.

The executor made a copying error. Nothing was tampered with.

## What it does and does not affect

**Selection and input are correct, and enforced.** The file's `question_ids` (50, list hash `5266568e…7339`) and input SHA-256 `d6f21ea9…a3442` are the ones every Cognee execution used.

`reference/run_longmemeval_resumable.py` refuses to run if either the `question_ids` or the input SHA-256 differs from the preregistration. It does **not** compare the `backend` fields, which is why the error went unnoticed at run time.

**The rows are Cognee's:**

- The rows file is named by the driver from `--backend`: `session.cognee_gliner_local.rows.jsonl`. `RETRIEVERS["cognee_gliner_local"]` is registered only by `longmemeval_cognee_bridge`.
- Each of the 37 rows present at 16:53 UTC (first finished 06:48:13, last 16:28:04) carries fields that only the Cognee bridge emits: `remember_status`, `returned_entry_kinds` and `question_isolated`. All have `capability: retrieval_only`, `llm_calls: 0` and no `runtime_error`.
- The surviving launch record, `cognee-subset50-session-1792061525.exec.json` (started 10:52:05 UTC), has argv `--backend cognee_gliner_local --external-backend longmemeval_cognee_bridge:install_longmemeval_cognee_backend`. It ended with exit status −9, a memory-cgroup OOM kill (dmesg) caused by co-scheduled benchmark processes. It was resumed with the same launcher at 16:52 UTC.
- The three earlier launches have no exec record; their stdout is Cognee's own table-setup logging.
- Every launch uses `/tmp/am-bench/tools/run_cognee_subset.sh`, whose arguments are fixed.

**Status consequence.** The preregistration was an acceptance condition, and it misidentifies the contender. These rows therefore stay **candidate/exploratory** and cannot be promoted, even once all 50 are complete.

## Correction going forward

`../subset50-gen2/preregistration.json` was written by the driver's own `--preregister-only` at 2026-10-15T16:53:44Z, before any gen-2 question ran.

| Field | Value |
| --- | --- |
| `backend` | `cognee_gliner_local` |
| `external_backend` | the Cognee bridge |
| Planes | session and turn |
| Selection | same 50 questions, list hash `5266568e…7339` |
| Input | same SHA-256 |
| Cognee configuration | unchanged: 1.6.4 `f154b32`, local GLiNER, no LLM, bridge 0.1.1 |

That generation is the independently repeated run needed for any qualified Cognee LongMemEval evidence. It runs in its own output directory and never appends to these rows. This gen-2 preregistration was written after partial gen-1 Cognee results were visible. Nothing in the Cognee configuration, adapter or selection changed in response.
