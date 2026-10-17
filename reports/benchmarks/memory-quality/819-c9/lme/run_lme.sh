#!/bin/bash
# LongMemEval-S 500, both planes, semantic route required, default selection; the evaluator's C8 protocol.
set -u
S=/tmp/claude-0/-home-user-agent-memory/de46b9be-9dfb-5f73-acc8-bb6406f9dc14/scratchpad
DATA=$S/lme/longmemeval_s_cleaned.json
echo "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442  $DATA" | sha256sum -c || exit 1
run() { (cd $S/wt/$1 && env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u HF_TOKEN PYTHONHASHSEED=0 HF_HUB_OFFLINE=1 \
  python3 reference/run_longmemeval.py --backend agent_memory --input $DATA --corpus-class external_frozen \
  --granularity session --granularity turn --agent-memory-semantic-retrieval required \
  --output $S/lme/$1-sem-lme500.json > $S/lme/$1.log 2>&1; echo "$1 rc=$? $(date -u +%FT%TZ)") }
run c8 & run c9 & wait
echo lme-done
