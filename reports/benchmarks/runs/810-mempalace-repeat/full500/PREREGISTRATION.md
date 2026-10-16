# MemPalace 3.11.0 LongMemEval-S full 500: independent-host repeat (#810, review item G)

**Status: preregistered before execution. Candidate, not reviewed.** It is a repeat of the external lane's
`reports/benchmarks/runs/mempalace/full500` (`claude/810-external-exec-no-ci` @ `8887bbe`). It does not
replace that run, and it does not restart or modify the external lane's work.

`preregistration.json` was written by `reference/run_longmemeval_resumable.py --preregister-only` at
2026-10-16T01:40:30Z (sha256 `f35fdd54…385e`). Every field except `registered_at` is identical to the
original run's preregistration:

- input `longmemeval_s_cleaned.json`, sha256 `d6f21ea9…a3442`;
- selection `all`, 500 questions, ID-list sha256 `7d738ae585fd4014c9d231088ff824864fded501adc07b0e08c2b97a28210c03`;
- planes `session` then `turn`;
- backend `mempalace_default_local` via `longmemeval_mempalace_bridge:install_longmemeval_mempalace_backend`.

## Pinned identity, the same as the original

| Item | Pin |
|---|---|
| Evaluator | `reference/run_longmemeval.py`, blob `6b9c237` (unchanged) |
| Driver | `reference/run_longmemeval_resumable.py`, blob `4df24e1` |
| Adapter | `reference/longmemeval_mempalace_bridge.py` 0.1.0-candidate, blob `ea86213`, taken from `8887bbe` unmodified |
| Product | MemPalace 3.11.0, tag commit `602d796c699cabba2971982cd9dccbbf46abfe79` (MIT), non-editable install; the bridge hash-checks the installed package tree at startup |
| Environment | Python 3.13.16. The installed distributions match `../../mempalace/mempalace-venv-freeze.txt` (`8887bbe`) byte for byte |
| Embedder | ChromaDB ONNX all-MiniLM-L6-v2, archive sha256 `913d7300…16ec3`; the per-file hashes match `model-pins.txt`. One embedding thread, offline |
| LLM | none. The process runs as an unprivileged user with an empty environment and no credentials (`env -i`) |
| Isolation | fresh palace, config dir, HOME and MCP server per question, deleted after the search (the bridge's own behaviour) |

The synthetic smoke for both planes, run before preregistration on this host, had 0 failures.

## What will be compared, fixed now

1. **The native summaries** for both planes against the original run. Reported: recall_all@{5,10,50} and ndcg_any@10.
2. **Per-question agreement on the 419 scored questions**: the number of questions whose recall_all@{5,10,50} differ, and the number whose ranked lists differ.
   - MemPalace runs a vector search followed by a fixed 0.6/0.4 vector/BM25 rerank. Both steps are expected to be deterministic for a fixed model and input, but this is not assumed.
   - Every difference is reported. None is explained away after the fact.
3. **Re-pairing against frozen Agent Memory** with this run's rows: exact McNemar, and a paired bootstrap at 10,000 resamples with seed 0. The aim is to show whether the reviewed posture (`competitive deficit`) depends on which MemPalace run is used.

The two runs are never averaged or pooled. If they disagree, both are reported, and the original remains the reviewed row.

## Execution

- Runs concurrently with the Letta full-500 run on the same 4-vCPU host.
- Wall-clock and latency figures are therefore **not comparable** to the original run's, and are reported only as observed.
- After a container restart, the resumable driver continues from the committed rows. It checks the input sha and question ids on resume.
