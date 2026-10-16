# MemPalace 3.11.0 LongMemEval-S full 500: independent-host repeat, both planes (#810, review item G)

**Status: candidate. Executed as preregistered** (`PREREGISTRATION.md`, committed in `7ab93db8` before the first question ran).
`preregistration.json` is byte-identical after the run (sha256 `f35fdd54…385e`).

This repeat reproduces the external lane's `reports/benchmarks/runs/mempalace/full500`
(`claude/810-external-exec-no-ci` @ `8887bbe`) **exactly**. It closes the review's "MemPalace has no LongMemEval repeat"
evidence gap. It does not replace the original, which remains the reviewed row, and the two runs are never averaged or pooled.

## Result 1: per-question agreement with the original (`repeat-vs-original.json`)

| Plane | Questions | Status differs | Ranked lists differ (all 500) | recall_all@5 / @10 / @50 differ (419 scored) | Native summaries identical* |
|---|---:|---:|---:|---|---|
| session | 500 | 0 | **0** | 0 / 0 / 0 | yes |
| turn | 500 | 0 | **0** | 0 / 0 / 0 | yes |

\* Compared: `aggregate`, `by_question_type`, `currentness`, `failures` and `question_count_completed`. Only the timing fields differ.

MemPalace's path is deterministic for a fixed model and input. That covers chroma vector search over MiniLM ONNX on one thread, then a 0.6/0.4 vector/BM25 rerank.
This held across:
- a different host process tree and user (`hsbench`, not `benchrun`);
- 8 execution segments separated by container restarts;
- a concurrent Letta run on the same host.

## Result 2: re-paired against frozen Agent Memory, using this run's rows

There are 419 scored questions; W/L counts questions where exactly one side is fully correct. The p-values are exact McNemar; the intervals are paired bootstrap Δ (MemPalace − Agent Memory, 10,000 resamples, seed 0).

| Plane, metric | Agent Memory | MemPalace | MemPalace W / L | p | Δ [95% CI] |
|---|---:|---:|---|---:|---|
| session @5 | 0.823 | 0.881 | 29 / 5 | 3.86e-5 | +0.057 [+0.031, +0.084] |
| session @10 | 0.893 | 0.940 | 22 / 2 | 3.59e-5 | +0.048 [+0.026, +0.072] |
| turn @5 | 0.601 | 0.668 | 36 / 8 | 2.54e-5 | +0.067 [+0.036, +0.098] |
| turn @10 | 0.723 | 0.804 | 37 / 3 | 1.95e-8 | +0.081 [+0.053, +0.110] |
| turn @50 | 0.859 | 0.943 | 36 / 1 | 5.53e-10 | +0.084 [+0.057, +0.112] |

These are the original README's figures. The rows are identical, so the posture for Agent Memory against MemPalace does not depend on which MemPalace run is used: it is a significant `competitive deficit` on both planes.

## Execution

| Item | Value |
|---|---|
| Command | `reference/run_longmemeval_resumable.py … --granularity session --granularity turn --backend mempalace_default_local --out …`. This is the same argv as the original, except for paths. Finalized with `--finalize` (`execution/finalize.*`) |
| User and environment | unprivileged `hsbench`, `env -i`, offline (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`), `PYTHONHASHSEED=0`, no credentials (`secrets_present` all false) |
| Segments | 8 driver invocations, 2026-10-16 01:41Z → 18:47Z, logs in `execution/mempalace-500-*.stdout`. Seven were ended by container reclamation while the session was idle. Each resumed from the committed rows; the driver checks the input sha and question ids on resume. Scratch palaces left by questions interrupted mid-run were deleted before resuming, and those questions re-ran from scratch. Only the last segment (14:06Z → 18:47Z, 4.7 h, exit 0, peak RSS 714 MiB) has an exec record, because the recorder of each killed segment died with it |
| Concurrency | ran alongside the Letta full-500 run on the same 4-vCPU host. Timings are reported only as observed and are not comparable to the original's |
| Observed medians, repeat vs original | session: ingest 12.6 s vs 12.5 s, recall 157 ms vs 179 ms; turn: ingest 33.5 s vs 42.1 s, recall 150 ms vs 206 ms |
| Failures | 0 runtime, 0 ingestion, 0 out-of-corpus, on both planes |

**Reproduce the comparison:**

```
python3 scripts/mempalace_repeat_compare.py \
  --repeat reports/benchmarks/runs/810-mempalace-repeat/full500 \
  --original <8887bbe>/reports/benchmarks/runs/mempalace/full500 \
  --controls <8887bbe>/reports/benchmarks/runs/controls/full500/controls-500.json.gz \
  --out repeat-vs-original.json
```

## Limits

- This is still a self-run on this branch, so it is **pending independent review**.
- It confirms reproducibility, not validity: the original's caveats carry over unchanged:
  - it is not MemPalace's published raw-ChromaDB 96.6% R@5 figure;
  - chunked drawers can occupy several of the top-50 places;
  - retrieval-only, no QA.
