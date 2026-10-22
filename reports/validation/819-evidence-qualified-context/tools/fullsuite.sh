#!/bin/bash
S=/tmp/claude-0/-home-user-agent-memory/d41e5087-c642-5965-a920-d612859a1976/scratchpad; PY=$S/bench/venv312-lme/bin/python
until grep -q "== done" $S/819/replays-run.log 2>/dev/null; do sleep 20; done
cd /home/user/agent-memory; export PYTHONPATH=reference
echo "head $(git rev-parse HEAD) $(date -u +%T)"
$PY -m pytest reference/tests -q -p no:cacheprovider --junitxml=$S/819/full-suite.xml > $S/819/full-suite.log 2>&1; echo "exit=$?"
tail -n 15 $S/819/full-suite.log
echo "== done $(date -u +%T)"
