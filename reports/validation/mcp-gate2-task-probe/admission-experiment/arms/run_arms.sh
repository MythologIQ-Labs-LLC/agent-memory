#!/bin/bash
# usage: run_arms.sh TREE VENV OUT LABEL FLAG(off|content_term)
set -u
T=$1; VENV=$2; O=$3; L=$4; F=$5; V=$VENV/bin/python
SP=$($V -c "import site; print(site.getsitepackages()[0])"); echo "$T/reference" > $SP/agentmem-tree.pth
mkdir -p $O; cd $T
unset AGENT_MEMORY_REPRESENTATION_DIR AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION
[ "$F" = content_term ] && export AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION=content_term
echo "label $L head $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l) selector=$(git rev-parse HEAD:reference/agentmem_ref/api/context_selection.py | cut -c1-8) flag=$F $(date -u +%FT%TZ)" | tee $O/identity-$L.txt
P=reports/validation/mcp-gate2-task-probe
$V integrations/agent-memory-mcp/quality_probe.py --max-items 5 --out $O/dev-default-$L.json > $O/dev-default-$L.log 2>&1; echo "dev default rc=$?"
$V integrations/agent-memory-mcp/quality_probe.py --max-items 5 --selectivity --out $O/dev-selective-$L.json > $O/dev-selective-$L.log 2>&1; echo "dev selective rc=$?"
for c in postfreeze:$P/phase5/task_cases_postfreeze.json disjoint:$P/admission-experiment/task_cases_disjoint.json; do
  name=${c%%:*}; file=${c#*:}; [ -f "$file" ] || { echo "skip $name (no cohort at this head)"; continue; }
  for r in extractive onnx-squad; do for s in default selective; do
    flag=""; [ $s = selective ] && flag=--selectivity
    $V integrations/agent-memory-mcp/task_eval.py --cases $file --out $O/task-$name-$r-$s-$L.json --answerer $r --model-dir /home/user/eval/g2/reader $flag > $O/task-$name-$r-$s-$L.log 2>&1; echo "task $name $r $s rc=$?"
  done; done
done
echo "dirty_after=$(git status --porcelain | wc -l)" | tee -a $O/identity-$L.txt
