#!/bin/bash
# args: <tree> <label>; runs the probe at several contention levels and 4 concurrent copies for load
TREE=$1; LABEL=$2; S=/tmp/claude-0/-home-user-agent-memory/d41e5087-c642-5965-a920-d612859a1976/scratchpad
PY=$S/bench/venv312-lme/bin/python; cd $TREE/reference || exit 2; export PYTHONPATH=.
echo "== $LABEL tree=$(git -C $TREE rev-parse --short HEAD) $(date -u +%T)"
echo "-- test-shaped (3 threads x 5 writes) x 100 rounds, single process"; $PY $S/r839/race_probe.py 3 5 100
echo "-- 3x5 x 40 rounds, 4 concurrent processes (CPU oversubscribed)"; for k in 1 2 3 4; do $PY $S/r839/race_probe.py 3 5 40 > $S/r839/stress-$LABEL-$k.txt 2>&1 & done; wait; cat $S/r839/stress-$LABEL-*.txt | grep -E "TOTAL|round" | head -20
echo "-- 8 threads x 10 writes x 30 rounds, single process"; $PY $S/r839/race_probe.py 8 10 30
echo "== $LABEL done $(date -u +%T) load=$(cut -d' ' -f1-3 /proc/loadavg)"
