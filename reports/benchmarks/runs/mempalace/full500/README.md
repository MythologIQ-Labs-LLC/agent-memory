# MemPalace 3.11.0 (default local, through its own MCP tools): full 500-question LongMemEval-S, both planes (#810)

**Status: candidate.** This is a self-run and has not been independently reviewed or accepted.
It was preregistered before execution, and `preregistration.json` is byte-identical after the
run.

It measures MemPalace as an agent's local verbatim memory, through its documented
`mempalace_add_drawer` / `mempalace_search` tools. It is **not** MemPalace's published raw
ChromaDB benchmark figure.

## Results

These are the native summaries (`{plane}.mempalace_default_local.summary.json`). All 500 questions
completed on both planes, with 419 scored. There were 0 runtime failures, 0 ingestion failures and
0 out-of-corpus results.

| Plane | recall_all@5 | recall_all@10 | recall_all@50 | ndcg_any@10 |
|---|---:|---:|---:|---:|
| session | 0.881 | 0.940 | 1.000 | 0.915 |
| turn | 0.668 | 0.804 | 0.943 | 0.729 |

### Paired against frozen Agent Memory

All systems are compared on the same 419 scored questions. Sources are
`paired-vs-controls-and-hindsight.{plane}.json`, with budget curves and cost in
`profile.{plane}.json`. The paired script reproduces the native summaries exactly.

| Plane, metric | Agent Memory | MemPalace | W / L / T | Exact McNemar | Δ mean [95% paired bootstrap] |
|---|---:|---:|---|---:|---|
| session @5 | 0.823 | 0.881 | 29 / 5 / 385 | 3.9e-5 | +0.057 [+0.031, +0.084] |
| session @10 | 0.893 | 0.940 | 22 / 2 / 395 | 3.6e-5 | +0.048 [+0.026, +0.072] |
| turn @5 | 0.601 | 0.668 | 36 / 8 / 375 | 2.5e-5 | +0.067 [+0.038, +0.098] |
| turn @10 | 0.723 | 0.804 | 37 / 3 / 379 | 2e-8 | +0.081 [+0.053, +0.110] |

recall_all@10 for multi-session questions:

| Plane | Agent Memory | MemPalace | Hindsight |
|---|---:|---:|---:|
| session | 0.810 | 0.884 | 0.942 |
| turn | 0.537 | 0.620 | 0.711 |

## Execution: two segments around a container restart

- **Segment 1.** It ran from 14:02:16Z until the container restart, after turn row 349, which
  finished at 20:36:54Z. Its recorder was killed with the container, so it has no exec record
  and no measured peak RSS. Its native logs are `mempalace-500.stdout` and
  `mempalace-500.stderr.gz`.
- **Segment 2.** It was resumed with the same driver, backend, input and selection at 20:40:05Z.
  The frozen preregistration check refuses any other selection. It completed turn rows 350–500.
  `mempalace-500-resume1.exec.json`: exit 0, 5,286 s, peak RSS 706 MiB, run as `benchrun` with no
  credentials.
- **Rows before the restart are unchanged.** All 849 rows written before the restart parsed as
  complete records. Session rows are byte-identical to the copy committed before the restart.
- **Combined record.** `mempalace-500.exec-combined.json` combines the two segments for the #808
  manifests (`{plane}.mempalace_default_local.manifest.json`). Its wall time excludes the restart
  gap, and its peak RSS is segment 2 only.
- **Environment:** `../mempalace-venv-freeze.txt`. Model pins: `../model-pins.txt`.
