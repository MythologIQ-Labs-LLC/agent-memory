#!/bin/bash
# LongMemEval-S 500, runner blob 6b9c2373. usage: run_lme.sh NAME VENV SEMANTIC
set -u
DATA=/home/user/eval/data/longmemeval_s_cleaned.json
echo "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442  $DATA" | sha256sum -c --quiet || exit 1
cd /home/user/eval/am-$2
[ "$(git hash-object reference/run_longmemeval.py)" = 6b9c237380f1d527e564161c2dac7fe32ada0ef9 ] || { echo "runner blob differs"; exit 1; }
env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u HF_TOKEN PYTHONHASHSEED=0 HF_HUB_OFFLINE=1 AGENT_MEMORY_REPRESENTATION_DIR=/home/user/eval/semantic-model \
  /home/user/eval/venv-$2/bin/python /home/user/eval/tools/run_logged.py /home/user/eval/evidence/$1 \
  /home/user/eval/venv-$2/bin/python reference/run_longmemeval.py --backend agent_memory --input $DATA \
  --corpus-class external_frozen --granularity session --granularity turn --agent-memory-semantic-retrieval $3 \
  --output /home/user/eval/evidence/$1.json.partial
rc=$?; [ $rc -eq 0 ] && mv /home/user/eval/evidence/$1.json.partial /home/user/eval/evidence/$1.json && echo "$1 done $(date -u +%FT%TZ)" || echo "$1 FAILED rc=$rc"
