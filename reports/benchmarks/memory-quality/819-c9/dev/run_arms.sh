#!/usr/bin/env bash
# Runs diagnose_c9.py for each arm on each set, in parallel. Usage: run_arms.sh <out-dir> <arm>... where arm = name:worktree:semantic:selection
set -u
HERE=$(cd "$(dirname "$0")" && pwd); MQ=$(cd "$HERE/../.." && pwd); OUT=$1; shift; mkdir -p "$OUT"
declare -A SETS=([c8set]=$MQ/819-c8/dev/c8-scenarios.json [c7set]=$MQ/819-c7/dev/c7-scenarios.json
  [c6diag]=$MQ/819-c6/dev/diag-scenarios.json [c5dev]=$MQ/819-c6/dev/c5-dev-scenarios.json [gen]=$MQ/819-c6/review/gen.json)
[ -n "${C9_SETS:-}" ] && eval "SETS=(${C9_SETS})"
for arm in "$@"; do IFS=: read -r name wt sem sel <<<"$arm"
  for s in "${!SETS[@]}"; do
    python3 "$HERE/diagnose_c9.py" "$wt/reference" "$sem" "$sel" "${SETS[$s]}" --budget "${BUDGET:-5}" --output "$OUT/$name-$s.json" > "$OUT/$name-$s.log" 2>&1 &
  done
done
wait
