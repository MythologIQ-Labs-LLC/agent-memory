#!/bin/bash
# Replacement queue (23:45Z): C6-sem keeps running untouched (pid 920/921, started 23:18Z by run_lme.sh).
# C4-sem now runs beside it; the two lexical runs follow in parallel once both semantic runs end.
set -u
DATA=/home/user/eval/data/longmemeval_s_cleaned.json
echo "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442  $DATA" | sha256sum -c || exit 1
finalize() { # name rc
  if [ "$2" -eq 0 ] && python3 -c "import json,sys;json.load(open(sys.argv[1]))" /home/user/eval/evidence/$1.json.partial 2>/dev/null; then
    mv /home/user/eval/evidence/$1.json.partial /home/user/eval/evidence/$1.json; echo "$1 done $(date -u +%FT%TZ)"
  else echo "$1 FAILED rc=$2 $(date -u +%FT%TZ)"; fi
}
run() { # name venv worktree semantic_mode
  cd /home/user/eval/am-$3
  free=$(df --output=avail -k /home/user | tail -1); if [ "$free" -lt 3000000 ]; then echo "$1 SKIPPED low disk ${free}k"; return; fi
  env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u HF_TOKEN PYTHONHASHSEED=0 HF_HUB_OFFLINE=1 \
    AGENT_MEMORY_REPRESENTATION_DIR=/home/user/eval/semantic-model \
    /home/user/eval/venv-$2/bin/python /home/user/eval/tools/run_logged.py /home/user/eval/evidence/$1 \
    /home/user/eval/venv-$2/bin/python reference/run_longmemeval.py --backend agent_memory --input $DATA \
    --corpus-class external_frozen --granularity session --granularity turn \
    --agent-memory-semantic-retrieval $4 --output /home/user/eval/evidence/$1.json.partial
  finalize $1 $?
}
run c4-sem-lme500 c4 c4 required &
C4=$!
while kill -0 920 2>/dev/null; do sleep 30; done
rc=$(python3 -c "import json;print(json.load(open('/home/user/eval/evidence/c6-sem-lme500.exec.json'))['exit_status'])" 2>/dev/null || echo 99)
finalize c6-sem-lme500 $rc
wait $C4
run c6-off-lme500 c6 c6 off &
run c4-def-lme500 c4 c4 off &
wait
echo lme-queue-done
