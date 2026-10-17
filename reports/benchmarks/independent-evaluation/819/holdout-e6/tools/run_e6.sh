#!/bin/bash
# e6 arms (PREREGISTRATION.md). usage: run_e6.sh NAME VENV SEMANTIC [OPEN_KWARGS] [RECALL_KWARGS]
set -u
cd /home/user/eval/holdout-e6 && sha256sum -c --quiet SHA256SUMS || exit 1
REP=/home/user/eval/semantic-model; N=$1; V=$2; S=$3; OK=${4:-'{}'}; RK=${5:-'{}'}
cd /home/user/eval/am-$V
env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u HF_TOKEN PYTHONHASHSEED=0 HF_HUB_OFFLINE=1 \
  /home/user/eval/venv-$V/bin/python /home/user/eval/tools/run_logged.py /home/user/eval/e6-results/$N \
  /home/user/eval/venv-$V/bin/python /home/user/eval/holdout-e6/harness.py /home/user/eval/holdout-e6/cases.json \
  /home/user/eval/e6-results/$N.json.partial --semantic $S --representation-dir $REP --open-kwargs "$OK" --recall-kwargs "$RK"
rc=$?; [ $rc -eq 0 ] && mv /home/user/eval/e6-results/$N.json.partial /home/user/eval/e6-results/$N.json && echo "$N done $(date -u +%FT%TZ)" || echo "$N FAILED rc=$rc"
