#!/bin/bash
# C8 LongMemEval-S 500 (default selection; runner 6b9c2373 has no return-selection option). Sequential.
set -u
DATA=/home/user/eval/data/longmemeval_s_cleaned.json
echo "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442  $DATA" | sha256sum -c || exit 1
run() { cd /home/user/eval/am-c8
  free=$(df --output=avail -k /home/user | tail -1); [ "$free" -lt 3000000 ] && { echo "$1 SKIPPED low disk"; return; }
  env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u HF_TOKEN PYTHONHASHSEED=0 HF_HUB_OFFLINE=1 AGENT_MEMORY_REPRESENTATION_DIR=/home/user/eval/semantic-model \
    /home/user/eval/venv-c8/bin/python /home/user/eval/tools/run_logged.py /home/user/eval/evidence/$1 \
    /home/user/eval/venv-c8/bin/python reference/run_longmemeval.py --backend agent_memory --input $DATA \
    --corpus-class external_frozen --granularity session --granularity turn --agent-memory-semantic-retrieval $2 \
    --output /home/user/eval/evidence/$1.json.partial
  rc=$?; if [ $rc -eq 0 ] && python3 -c "import json,sys;json.load(open(sys.argv[1]))" /home/user/eval/evidence/$1.json.partial; then
    mv /home/user/eval/evidence/$1.json.partial /home/user/eval/evidence/$1.json; echo "$1 done $(date -u +%FT%TZ)"; else echo "$1 FAILED rc=$rc"; fi; }
run c8-sem-lme500 required
run c8-off-lme500 off
echo lme-c8-done
