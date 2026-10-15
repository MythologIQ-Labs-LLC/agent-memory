# Mem0 OSS 2.2.1 explicit: independent repeat of the 50-question LongMemEval-S subset (#640, #810)

**Result: identical to the original run, row by row, on both planes.**

| Comparison | Plane | Questions compared | Differing |
|---|---|---:|---:|
| `../subset50/mem0-50.json.gz` vs this repeat | session | 50 / 50 | 0 |
| `../subset50/mem0-50.json.gz` vs this repeat | turn | 50 / 50 | 0 |

The comparison ran under `scripts/compare_longmemeval_rows.py --scope exact`. It checks
`metrics`, `status`, `runtime_error`, `ranked_top`, `gold` and `question_type`; the output is in
`repeat-vs-original.{plane}.json`.

## How the repeat differs from the original run

- **Driver.** The repeat used `reference/run_longmemeval_resumable.py`, with the same subset seed
  and 50 ids, so that a restart loses at most one question. The original used the one-shot
  `reference/run_longmemeval.py`. Both write `score_record` rows from the same evaluator.
- **Offline.** The repeat set `HF_HUB_OFFLINE=1`. The embedder
  `sentence-transformers/multi-qa-MiniLM-L6-cos-v1@b207367…` was taken from the cached pinned
  revision.
- **Unchanged.** Mem0 2.2.1 explicit (`infer=False`), with the Qdrant local store, the bridge and
  `PYTHONHASHSEED=0`.
- **Execution.** Run as `benchrun` with no credentials (`mem0-50.exec.json`): exit 0, 4,979 s,
  peak RSS 1,125 MiB.

## Attempts that produced no rows (kept for audit)

- **Lost to the container restart.** A one-shot repeat ran for about 6 hours. It writes its
  output only at the end, so nothing was produced. Its logs had no rows to keep.
- **Launch failed: missing HF home.** The original run's `HF_HOME` cache directory no longer
  existed, so offline model loading failed before any question ran.
- **Launch failed: CA bundle.** The default `SSL_CERT_FILE` was unreadable to the unprivileged
  user. An import that builds an SSL context failed before any question ran. Fixed by pointing
  the CA variables at a readable copy.

Their exec records and stderr tails are in `failed-launches/`.
