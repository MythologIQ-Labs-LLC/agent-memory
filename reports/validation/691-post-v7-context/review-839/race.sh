#!/bin/bash
# Repeat the #786 thread-race test on a tree; args: <tree-root> <label> <iterations> <log>
TREE=$1; LABEL=$2; N=$3; LOG=$4
PY=/tmp/claude-0/-home-user-agent-memory/d41e5087-c642-5965-a920-d612859a1976/scratchpad/bench/venv312-lme/bin/python
cd $TREE/reference || exit 2
pass=0; fail=0
: > $LOG
for i in $(seq 1 $N); do
  if $PY -m pytest "tests/test_786_cross_scope_write_authority.py::CompetingWriters::test_threads_racing_as_both_projects_never_move_the_owners_head" -q -p no:cacheprovider > $LOG.run 2>&1; then pass=$((pass+1)); else fail=$((fail+1)); echo "--- iteration $i FAILED" >> $LOG; grep -E "^E  |Error|Conflict" $LOG.run | head -12 >> $LOG; fi
done
echo "$LABEL tree=$(git -C $TREE rev-parse --short HEAD) iterations=$N pass=$pass fail=$fail load=$(cat /proc/loadavg | cut -d' ' -f1-3)" | tee -a $LOG
