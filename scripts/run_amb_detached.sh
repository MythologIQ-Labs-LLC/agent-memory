#!/bin/bash
# usage: run-amb-detached.sh EVIDENCE_DIR MEMORY [--set-env K=V ...]
# Runs the reviewed AMB evidence wrapper fully detached (survives the executor's tool timeouts),
# with AWS_* removed from the environment, and writes EVIDENCE_DIR.done with the wrapper's exit code.
ev="$1"; mem="$2"; shift 2
cd /home/user/ext-exec
env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN nice -n 5 python3 scripts/run_amb_local_evidence.py \
  --amb-root /tmp/agent-memory-benchmark --python /tmp/am-bench/graphiti-amb-venv/bin/python --evidence-dir "$ev" \
  --set-env TIKTOKEN_CACHE_DIR=/tmp/am-bench/tiktoken-cache --set-env HF_HUB_OFFLINE=1 --set-env PYTHONHASHSEED=0 "$@" \
  -- run --dataset precisionmembench --split single-turn --memory "$mem" --mode retrieval > "$ev.wrapper.log" 2>&1
echo $? > "$ev.done"
