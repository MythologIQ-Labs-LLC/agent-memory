# MemPalace on AMB PrecisionMemBench single-turn (all 77 cases): 9/77

**Status: candidate.** This is a self-run, unreviewed result. It is not accepted and is not an
official AMB leaderboard entry. It was preregistered before execution (`PREREGISTRATION.md`,
`preregistration.json`, pushed at `de01780` before the run started).

## Result (AMB native scoring, run 1)

| System (same harness, protocol A, no LLM) | Correct | Active | Structural | Trivially empty | Mean precision | Mean recall | Mean memories returned | Paired vs Agent Memory (wins/losses, exact McNemar) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Agent Memory (reviewed, `1df28f8`) | **15/77** | 4/43 | 6/25 | 5/9 | 0.181 | 0.954 | 8.9 | — |
| Mem0 OSS explicit (lane v4 evidence) | 10/77 | 0/43 | — | — | 0.105 | 1.000 | 8.0 | +1 / −6, p = 0.125 |
| **MemPalace 3.11.0 (this run)** | **9/77** | **0/43** | **6/25** | **3/9** | **0.056** | **1.000** | **18.1** | **+0 / −6, p = 0.031** |
| BM25 (AMB built-in, reviewed) | 8/77 | 0/43 | 5/25 | 3/9 | 0.054 | 0.965 | 18.3 | +0 / −7, p = 0.016 |

Per-category passes and failure reasons are in `paired-vs-cohort.json`, and native per-case
outcomes are in `rep1/single-turn.json`.

MemPalace passes no active case. 68 of its 68 failures include an unexpected belief, because it
returns almost the full budget for every query. Agent Memory's lead comes from Alias resolution
(3/23 against 0/23) and Fuzzy matching (3/7 against 0/7). Both systems pass nothing in Scope
disambiguation, Supersession, Type routing, Relation expansion or Counter-signal retrieval.

## Repeatability

Run 2 was a fresh full rerun. It is identical to run 1 case by case, including raw provider
responses, with 0 differences (`rep1-vs-rep2.json`, from `scripts/compare_amb_runs.py`).

## Launch refused before any case

The first launch is kept in `launch-refused-aws-env/`. It stopped in `prepare` before ingesting
or scoring anything, because the bridge refuses any inference or cloud credential. The reviewed
evidence wrapper (`scripts/run_amb_local_evidence.py`) removes LLM keys but not `AWS_*`, and the
host exports AWS keys. Runs 1 and 2 were launched with `env -u AWS_ACCESS_KEY_ID -u
AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN`. Their `execution-identity.json` records no
credentials in the child. The wrapper was left unchanged, because its blob is part of the
preregistration. Adding `AWS_*` to its removal list is a recommended follow-up.

## Identity and reproduction

- **Harness and inputs:** AMB `03c1d0f` and fixtures `35659b3b…` / `09e99f08…`.
- **Guard and wrapper:** both unchanged from `1df28f8`.
- **Bridge:** `reference/amb_mempalace_bridge.py` 0.1.0-candidate.
- **Product:** MemPalace 3.11.0 at `602d796c`. Its installed tree is hash-checked in its own
  interpreter, with the environment in `../mempalace-venv-freeze.txt`.
- **Embedder:** the MiniLM ONNX model pinned in `../model-pins.txt`.
- **AMB process environment:** `../../812-graphiti/graphiti-amb-venv-freeze.txt`, which is AMB's
  own lock plus graphiti-core and agent-memory-reference, with no locked version changed.
- **Run cost:** wall time 41 s, peak RSS 1,042 MiB for the whole AMB CLI process.
- **Raw stores:** the palace binaries (`_store`) are not committed. Every file AMB wrote is
  sha256-listed in each `execution-identity.json`.

```bash
env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
python scripts/run_amb_local_evidence.py --amb-root <AMB 03c1d0f> --python <AMB env python> \
  --evidence-dir <dir> --set-env TIKTOKEN_CACHE_DIR=<pinned tiktoken cache> --set-env HF_HUB_OFFLINE=1 \
  --set-env PYTHONHASHSEED=0 --set-env MEMPALACE_PYTHON=<mempalace venv python> \
  --set-env MEMPALACE_BENCH_MODEL_DIR=<pinned MiniLM dir> \
  -- run --dataset precisionmembench --split single-turn --memory mempalace-local --mode retrieval
```
