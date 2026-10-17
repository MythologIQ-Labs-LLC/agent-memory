#!/bin/bash
# Post-LME sequential probes: fusion-boundary cost (two repetitions) and deterministic ties.
set -u; cd /home/user/eval/probes; mkdir -p out-c8; REP=/home/user/eval/semantic-model
for rep in 1 2; do for N in 200 400 450 500 520; do for sel in relevance_sufficient ranked_prefix; do for arm in "c6 required" "c8 required" "c4 required"; do set -- $arm
  PYTHONHASHSEED=0 /home/user/eval/venv-$1/bin/python latency_boundary.py $N $2 $sel $REP out-c8/lb-$1-$N-$sel-r$rep.json 2>/dev/null | sed "s/^/$1 r$rep /"
done; done; done; done
for arm in "c6 required" "c8 required"; do set -- $arm; for sel in relevance_sufficient ranked_prefix; do
  PYTHONHASHSEED=0 /home/user/eval/venv-$1/bin/python tie_probe.py $2 $sel $REP out-c8/tie-$1-$sel.json 2>/dev/null | sed "s/^/tie $1 $sel /"
done; done
echo probes-done
