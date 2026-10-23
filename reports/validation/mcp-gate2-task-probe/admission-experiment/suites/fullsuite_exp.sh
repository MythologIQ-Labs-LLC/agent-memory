#!/bin/bash
# usage: fullsuite_exp.sh FLAG OUT -- full reference suite at the experiment head, own venv first on PATH
F=$1; O=$2; T=/home/user/eval/g2/wt-exp; VE=/home/user/eval/g2/venv-exp; mkdir -p $O
unset AGENT_MEMORY_REPRESENTATION_DIR AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION
[ "$F" = content_term ] && export AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION=content_term
cd $T; echo "head $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l) flag=$F start $(date -u +%T)" > $O/identity.txt
PATH=$VE/bin:$PATH PYTHONPATH=$T/reference OMP_NUM_THREADS=2 $VE/bin/python -m pytest -q -p no:cacheprovider reference/tests > $O/full-suite.log 2>&1
echo "rc=$? end $(date -u +%T) dirty_after=$(git status --porcelain | wc -l)" >> $O/identity.txt
