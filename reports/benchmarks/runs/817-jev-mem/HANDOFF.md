# Jev-Mem LongMemEval-S execution: CUDA host handoff (#817)

**Status: candidate execution, not reviewed or accepted.** This file lets someone continue the Jev-Mem run on a CUDA host. The cloud VM run is CPU-only and too slow to finish the subset or the full set in one session.

## Why a GPU host is needed

The CPU cost was measured on the session VM: 4 vCPUs, 15 GiB RAM, no GPU.

| Measurement | Value |
| --- | --- |
| Laya checkpoint | `convaiinnovations/laya` root, ModernBERT-large encoder, `max_len` 512 |
| Laya decisions per ingested item | 2 at the start of a question, rising with graph size (one typing call plus batched relation calls over up to 10 candidates) |
| CPU seconds per Laya forward pass, fp32, 4 threads | about 6 |
| Ingest per item on real LongMemEval-S sessions | 2 s for the first item, rising to 28 s by the sixth |
| Session-plane items per question | 47.7 mean, 23,867 across 500 questions |
| Turn-plane items per question | 244.8 mean, 122,416 across 500 questions |

On this VM one session-plane question takes on the order of 20 minutes or more, so the 50-question subset needs most of a day. The full 500 questions on both planes is weeks of CPU. The completed CPU rows are kept in `subset50/` and are valid evidence for the questions they cover.

## Numeric configuration differs by device

`laya.Agent` runs in **fp32 on CPU** and in the checkpoint's `amp_dtype` **bf16 on CUDA** with compute capability 8 or higher. It uses fp16 on older GPUs. Decisions can differ at the margin.

- Record the device and dtype for every run.
- **Never merge CPU rows and GPU rows into one aggregate.**
- To extend the CPU rows, rerun the CPU questions on the GPU so the whole selection uses one configuration.

## Reproduce

Use Linux or WSL2 with an NVIDIA driver, Python 3.12, git and about 12 GB free disk. No API keys are needed, and none may be present.

```bash
# 1. Sources, pinned
git clone https://github.com/libingzheren/Jev-Mem.git /tmp/jev-mem-source
git -C /tmp/jev-mem-source checkout --detach 7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44
git clone https://github.com/MythologIQ-Labs-LLC/agent-memory.git /tmp/am
git -C /tmp/am checkout claude/817-jev-mem-execution-no-ci   # this branch

# 2. Isolated environment (CUDA torch from PyPI)
python3.12 -m venv /tmp/jev-venv && . /tmp/jev-venv/bin/activate
pip install -e '/tmp/jev-mem-source[laya]' -r /tmp/am/reference/requirements.txt
pip freeze > jev-venv-freeze.txt   # compare with subset50/jev-venv-freeze.txt

# 3. Models at immutable revisions, then run offline
export HF_HOME=/tmp/jev-hf
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("convaiinnovations/laya", revision="7b928d828b7b0e022f929d9bd2e44165aa270148",
    allow_patterns=["config.json","model.safetensors","encoder/*","tokenizer/*","rl_agent_config.json","rl_agent_api.py","rl_common.py","README.md"])
snapshot_download("sentence-transformers/all-MiniLM-L6-v2", revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41")
PY
# laya.load() has no revision argument: point refs/main at the pinned revisions
printf 7b928d828b7b0e022f929d9bd2e44165aa270148 > $HF_HOME/hub/models--convaiinnovations--laya/refs/main
printf 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 > $HF_HOME/hub/models--sentence-transformers--all-MiniLM-L6-v2/refs/main
sha256sum $HF_HOME/hub/models--convaiinnovations--laya/snapshots/*/model.safetensors
#   expect 891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 JEV_MEM_SOURCE_ROOT=/tmp/jev-mem-source PYTHONHASHSEED=0
unset OPENAI_API_KEY TYPESAFE_API_KEY HF_TOKEN AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY GH_TOKEN GITHUB_TOKEN

# 4. Frozen input
curl -fL --retry 3 https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json -o /tmp/lme_s.json
echo 'd6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442  /tmp/lme_s.json' | sha256sum -c -

# 5. Adapter tests, synthetic smoke, then the preregistered subset (resumable; rerun the same command to continue)
cd /tmp/am
python -m unittest discover -s reference/tests -t reference -p 'test_817_jev_mem_bridge.py' -v
python reference/run_longmemeval.py --external-backend longmemeval_jev_mem_bridge:install_longmemeval_jev_mem_backend \
  --backend jev_mem_laya --backend agent_memory --backend lexical_overlap \
  --input reference/fixtures/benchmarks/longmemeval/synthetic.json --corpus-class synthetic --max-questions 3 \
  --granularity session --granularity turn --output /tmp/jev-smoke.json
for G in session turn; do
  python reference/run_longmemeval_resumable.py --input /tmp/lme_s.json \
    --expected-sha256 d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442 \
    --subset-size 50 --granularity $G --backend jev_mem_laya \
    --external-backend longmemeval_jev_mem_bridge:install_longmemeval_jev_mem_backend \
    --out reports/benchmarks/runs/817-jev-mem/subset50-cuda
done
# finalize (same flags plus --finalize) writes <plane>.jev_mem_laya.summary.json
```

The driver refuses to run if the selection or input digest differs from `preregistration.json`, which commits question-ID list hash `5266568e...7339`. For the full set, use a new `--out` directory and omit `--subset-size`. The driver then preregisters all 500 questions before running any of them.

## Checks before reporting a number

- `failures.runtime_failure_count` must be 0. Otherwise report the errors, not the score. A process exit code of 0 is not enough.
- Every row must show `laya_write.fallback_events == []`, `laya_read.fallback_events == []` and `jev_read.controller == "jev-mem"`. The adapter already refuses MAGMA fallback.
- `unmapped_result_count` must be 0. Ranked IDs come only from node `metadata.doc_id`.
- Agent Memory, lexical and Mem0 controls must use the identical selection, with `question_ids_sha256` `5266568e...`.
- Report retrieval metrics only, using the runner's denominators: scored questions exclude `_abs` and no-user-target rows. These are not LoCoMo QA or official LongMemEval QA scores.
