#!/bin/bash
# Runs C6 and C8 side by side (symmetric contention), two repetitions per configuration.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=2 AGENT_MEMORY_REPRESENTATION_DIR=$PWD/../representation
PY=$PWD/../sem-venv/bin/python3
for cfg in "200 relevance_sufficient" "200 ranked_prefix" "1000 relevance_sufficient" "1000 ranked_prefix" "500 relevance_sufficient --shared-word" "500 ranked_prefix --shared-word" "520 relevance_sufficient --shared-word"; do
  for rep in 1 2; do
    $PY tools/perf.py c6 $cfg > /tmp/claude-0/-home-user-agent-memory/d36426e4-2c3f-5d02-b5a0-991ea8f96c90/scratchpad/review-c8/tools/out/p6.tmp 2>&1 &
    $PY tools/perf.py c8 $cfg > /tmp/claude-0/-home-user-agent-memory/d36426e4-2c3f-5d02-b5a0-991ea8f96c90/scratchpad/review-c8/tools/out/p8.tmp 2>&1
    wait
    echo "rep$rep $(cat tools/out/p6.tmp)"; echo "rep$rep $(cat tools/out/p8.tmp)"
  done
done
for rep in 1 2; do $PY tools/perf.py c8 200 relevance_sufficient --no-reuse | sed "s/^/rep$rep /"; done
