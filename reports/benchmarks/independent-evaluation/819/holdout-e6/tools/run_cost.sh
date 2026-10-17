#!/bin/bash
# usage: run_cost.sh ARMNAME VENV SEMANTIC [OPEN_KWARGS] [RECALL_KWARGS]
set -u; REP=/home/user/eval/semantic-model
for rep in 1 2; do for N in 200 400 450 500; do
  env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u HF_TOKEN PYTHONHASHSEED=0 HF_HUB_OFFLINE=1 /home/user/eval/venv-$2/bin/python \
    /home/user/eval/tools/latency_e6.py $N $3 $REP /home/user/eval/cost/$1-$N-r$rep.json "${4:-{\}}" "${5:-{\}}" 2>/dev/null | sed "s/^/$1 r$rep /"
done; done
