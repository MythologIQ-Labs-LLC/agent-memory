# #644 combined safety receipt: independent qualification command log

These are the commands in execution order. Some symbols stand for local paths:

- `$V`: CPython 3.13.16 test venv.
- `$P312`: CPython 3.12.3 venv with `reference/requirements.txt` exactly pinned.
- `$AMB`: CPython 3.12.3 venv built from the frozen AMB lock.
- `<tree>`: an isolated `git worktree`. The trees are:
  - `cand`, the validation branch;
  - `pristine`, `de3dbe8`;
  - `rem`, `46d84ad`;
  - `v6f`, `e98e6e7`;
  - `v6main`, `3eebb6d`;
  - `orig`, `e002536`.

The raw outputs are in this directory. Every Python run either sets `PYTHONPATH=<tree>/reference` or uses `-t reference` from the tree root, and the imported module path was printed to confirm the provenance.

## Setup

```
git fetch origin
git rev-parse origin/implementation/644-combined-safety-receipt-unqualified   # de3dbe813683e417f73546bfbdd66976997bea76
git merge-base origin/main origin/implementation/644-combined-safety-receipt-unqualified   # 3eebb6d
git worktree add -b validation/644-combined-safety-receipt-independent <cand> de3dbe8
git worktree add --detach <pristine> de3dbe8 ; git worktree add --detach <v6f> e98e6e7
git fetch origin 'refs/seals/*:refs/seals/*' ; $V scripts/verify_seals.py      # 23 seals anchored and matching
```

## Phase A: from the repository root of each tree

```
for p in test_recall_observation_receipt.py test_recall_control.py test_evidence_sufficiency.py \
         test_governed_transition_witness.py test_governed_transition_integration.py \
         test_package_layout.py test_runtime_baseline_succession.py; do
  $V -m unittest discover -s reference/tests -t reference -p "$p"
done
$V -m unittest discover -s reference/tests -t reference          # logs/*_full*.tail.log
$P312 -m unittest discover -s reference/tests -t reference       # logs/*_py312.tail.log
```

## Phase B: independent adversarial tests

```
$V -m unittest discover -s reference/tests -t reference -p test_644_combined_independent.py   # pristine: logs/phaseB_before.log
$V -m unittest discover -s reference/tests -t reference -p test_644_combined_independent.py   # 46d84ad:  logs/phaseB_after.log
PYTHONPATH=<tree>/reference $V scripts/receipt_on_heldout.py <dir containing heldout_bench.py>  # {"verified":126,"false_tamper":0,"crash":0}
PYTHONPATH=reference $V reference/run_retrieval_quality_benchmark.py --agent-memory-revision <rev> --output rq_<tree>.json   # v6f vs de3dbe8: only the revision label differs
```

## Phase C: original held-out harness

The harness sha256 must be `25ce88eb…` before every run.

```
sha256sum scripts/heldout_bench.py
PYTHONPATH=<tree>/reference $V scripts/heldout_bench.py heldout/bench_<tree>.json        # trees: v6f, e002536, de3dbe8, 46d84ad
$V scripts/diag_breakdown.py heldout/bench_<tree>.json > heldout/diag_<tree>.txt
```

## Phase D: SQLite performance

Stores are built per tree. Measurement is sequential, on an idle machine.

```
PYTHONPATH=<tree>/reference $V scripts/perf644.py build <store>_<n> <n>                                # n = 1000, 3000, 10000
PYTHONPATH=<tree>/reference $V scripts/perf644.py measure <store>_<n> <n> perf/m_<tree>_<n>.json --samples 30 --cold-samples 5
$V scripts/summarize.py perf > perf/summary.md
```

## Noninterference and restart

```
PYTHONPATH=<tree>/reference $V scripts/noninterference.py out.json 0|1         # sha256 after path normalisation: 1a6b90a9… on all trees and modes
PYTHONPATH=<tree>/reference $V scripts/noninterference_receipt.py out.json 1
PYTHONPATH=<tree>/reference $V scripts/restart_probe.py none|facade_recall|planner|observer   # F12 reproduces on v6 and the candidate
PYTHONPATH=<tree>/reference $V scripts/restart_probe3.py
```

## Phase E: governance

```
$V scripts/check_runtime_baseline_equivalence.py --candidate de3dbe813683e417f73546bfbdd66976997bea76    # rc 1, logs/checker_de3dbe8.log
$V scripts/declare_runtime_baseline_changes.py --declaration reports/runtime/baseline-v7-declaration.json   # logs/declare_after.log (8 blobs)
$V scripts/check_runtime_baseline_equivalence.py --candidate 46d84adeecf7f0ec034e7ec8c356bbb3859c8e03    # TRANSITION, logs/checker_validation.log
$V scripts/validate_runtime_baseline_source.py ; $V scripts/render_runtime_baseline.py --check           # rc 0, rc 0
```

## Phase F: lanes, replays and gauntlet

```
# public gauntlet (PATH and PYTHONPATH set to the tree; the stdio adapter inherits them)
agent-memory gauntlet validate-adapter examples/gauntlet/agent-memory-runtime-baseline-v6.json
agent-memory gauntlet run --system examples/gauntlet/agent-memory-runtime-baseline-v6.json \
  --profile gauntlet-orchestration-retrieval-probe-v1 --allow-external-process --allow-destructive-reset --output-dir gauntlet/<tree>

# LongMemEval-S v6 rows (input sha256 d6f21ea9… verified)
PYTHONPATH=<tree>/reference $P312 reference/run_longmemeval.py --input longmemeval_s_cleaned.json --corpus-class external_frozen \
  --granularity session|turn --backend agent_memory --agent-memory-budget 50 --output <tree>-<g>.json
python3 scripts/lme_compare.py <dir> session|turn

# AMB PrecisionMemBench v6, agent-memory row (fixtures and input_sha256 verified; frozen AMB 03c1d0f)
$AMB scripts/amb_harness_constraints.py --amb-root <amb> --memory agent-memory --uv <uv 0.8.17> --output amb-constraints.txt ...   # sha256 8a7f4b9b…
$AMB -m pip install -c amb-constraints.txt -e <repo> -e <amb>
(cd <amb> && PRECISIONMEMBENCH_DATA_PATH=<pmb> $AMB scripts/precisionmembench_selfcheck.py)      # 77/77
GEMINI_API_KEY=retrieval-only-unused OMB_ANSWER_LLM=gemini OMB_ANSWER_MODEL=gemini-2.5-flash-lite OMB_JUDGE_LLM=gemini \
OMB_JUDGE_MODEL=gemini-2.5-flash-lite MEM0_TELEMETRY=false TIKTOKEN_CACHE_DIR=<cache> AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR=... \
PYTHONPATH=<tree>/reference $AMB reference/run_amb_external.py --amb-root <amb> -- run --dataset precisionmembench \
  --split single-turn --memory agent-memory --mode retrieval --output-dir amb/<tree> --name agent-memory-<tree>

# the five declared #644 replays: searched every origin/*644* branch; no fixture, runner or test exists
git grep -l <replay-id> <branch> -- . ':!reports/runtime/baseline-v7-declaration.json' ':!docs/*.md'   # no matches
```

**Tokenizer note.** The proxy denies `openaipublic.blob.core.windows.net`. `cl100k_base.tiktoken` was therefore rebuilt from the public Hugging Face `Xenova/gpt-4` `tokenizer.json`. It was accepted only because its sha256 equals tiktoken's pinned `223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7`. It is used only to count context tokens.
