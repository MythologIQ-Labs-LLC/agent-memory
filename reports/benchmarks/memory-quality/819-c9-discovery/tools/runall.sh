#!/bin/bash
# usage: runall.sh <outdir> <fixture...> ; arms from $ARMS (e.g. "c4:off c4:required c6:required c9:required")
S=/tmp/claude-0/-home-user-agent-memory/9337443a-e21a-59de-997c-30d45d2d8610/scratchpad
out=$1; shift; mkdir -p $out
for f in "$@"; do b=$(basename $f .json); for arm in $ARMS; do r=${arm%%:*}; m=${arm#*:}; echo "$r $m $f $out/$r-$m-$b"; done; done |
  xargs -P 4 -L 1 sh -c '/tmp/claude-0/venv/bin/python '$S'/tools/harness.py /tmp/claude-0/wt/$0 $2 $3.json --sem $1 > $3.log 2>&1'
cat $out/*.log
