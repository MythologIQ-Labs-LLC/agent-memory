#!/usr/bin/env bash
# usage: cmp_lme.sh <backend> <plane> <run_id>
set -euo pipefail
B=/tmp/claude-0/-home-user-agent-memory/df091f7c-0b03-5d12-806d-4c56a896fc2c/scratchpad/bench
cd $B/../lane-wt
O=$(ls -d $B/runs/lme/$3/longmemeval-lane-*)
python3 $B/scripts/compare_lme.py reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v6/$1-$2-24048d55e26d $O/$2-$1.json $2 $1 $B/comparisons/compare-lme-$1-$2.json > /dev/null
python3 - $B/comparisons/compare-lme-$1-$2.json <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
keys=["ranked_top_equal","metrics_equal","cross_fact_equal","differing_count","complete50_v6","complete50_v7","required_v6","required_v7","scored_v7","statuses_v7","runtime_errors_v7","aggregate_equal","by_question_type_equal","currentness_equal","cross_fact_summary_equal","governance_equal","lost_complete","lost_required_evidence","gained_complete","gained_required_evidence"]
print({k:d[k] for k in keys})
m=d["headline_v7"]["metrics"][d["plane"]]; print({k:m[k] for k in ("ndcg_any@10","recall_all@10","recall_all@50","recall_any@10")})
print("timing_v7",d["timing_v7"]); print("timing_v6",d["timing_v6"])
PY
