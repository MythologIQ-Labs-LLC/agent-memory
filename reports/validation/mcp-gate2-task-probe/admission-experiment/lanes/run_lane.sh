#!/bin/bash
# usage: run_lane.sh KIND(session|turn|scale1000|scale19000) FLAG TREE VENV OUTDIR
set -u
K=$1; F=$2; T=$3; VE=$4; O=$5; V=$VE/bin/python
TOOLS=$T/reports/validation/819-evidence-qualified-context/tools
unset AGENT_MEMORY_REPRESENTATION_DIR AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION
[ "$F" = content_term ] && export AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION=content_term
mkdir -p $O; echo "lane $K flag $F head $(git -C $T rev-parse HEAD) dirty=$(git -C $T status --porcelain | wc -l) selector=$(git -C $T rev-parse HEAD:reference/agentmem_ref/api/context_selection.py | cut -c1-8) start $(date -u +%T)" > $O/identity.txt
export PATH=$VE/bin:$PATH OMP_NUM_THREADS=1
case $K in
  session|turn) $V -I $TOOLS/lme_paired.py --plane $K --input /home/user/eval/data/longmemeval_s_cleaned.json --runtime $T --out $O > $O/run.log 2>&1 ;;
  locomo) $V -I /home/user/eval/g2/tools/locomo_paired.py /home/user/eval/g2/external/amb/data/locomo/locomo10 $T $O > $O/run.log 2>&1 ;;
  scale*) $V -I /home/user/eval/g2/tools/scale_paired.py $T $O/scale.json ${K#scale} > $O/run.log 2>&1 ;;
esac
echo "rc=$? end $(date -u +%T)" >> $O/identity.txt
