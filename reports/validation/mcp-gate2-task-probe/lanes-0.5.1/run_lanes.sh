#!/bin/bash
S=/tmp/claude-0/-home-user-agent-memory/d41e5087-c642-5965-a920-d612859a1976/scratchpad
R=$S/gate2/runs-0.5.1; PY=$S/bench/venv312-lme/bin/python
cd /home/user/agent-memory
echo "head $(git rev-parse HEAD) selector $(git hash-object reference/agentmem_ref/api/context_selection.py) start $(date -u +%T)"
$PY -I $S/819/lib/lme_paired.py --plane session --input $S/bench/inputs/lme/longmemeval_s_cleaned.json --out $R/lme-session > $R/lme-session.log 2>&1 & P1=$!
$PY -I $S/819/lib/lme_paired.py --plane turn --input $S/bench/inputs/lme/longmemeval_s_cleaned.json --out $R/lme-turn > $R/lme-turn.log 2>&1 & P2=$!
$PY -I $S/819/lib/locomo_paired.py $S/bench/external/amb/data/locomo/locomo10 /home/user/agent-memory $R/locomo > $R/locomo.log 2>&1; echo "locomo exit=$? $(date -u +%T)"
$PY -I $S/819/lib/locomo_adversarial.py $S/819/external/locomo-raw/locomo10.json $S/bench/external/amb/data/locomo/locomo10 /home/user/agent-memory $R/locomo-adversarial > $R/locomo-adversarial.log 2>&1; echo "locomo-adversarial exit=$? $(date -u +%T)"
$PY -I $S/819/lib/scale_paired.py /home/user/agent-memory $R/scale-1000.json 1000 > $R/scale-1000.log 2>&1; echo "scale-1000 exit=$? $(date -u +%T)"
wait $P1; echo "lme-session exit=$? $(date -u +%T)"; wait $P2; echo "lme-turn exit=$? $(date -u +%T)"
$PY -I $S/819/lib/scale_paired.py /home/user/agent-memory $R/scale-19000.json 19000 > $R/scale-19000.log 2>&1; echo "scale-19000 exit=$? $(date -u +%T)"
echo "== done $(date -u +%T)"
