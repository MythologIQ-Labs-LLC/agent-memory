#!/bin/bash
S=/tmp/claude-0/-home-user-agent-memory/d41e5087-c642-5965-a920-d612859a1976/scratchpad; PY=$S/bench/venv312-lme/bin/python
until test -s $S/819/runs/lme-session/summary.json; do sleep 20; done
cd /home/user/agent-memory; O=$S/819/replays; rm -rf $O; mkdir -p $O/786 $O/644; export PYTHONPATH=reference
echo "head $(git rev-parse HEAD) clean_tracked=$(git status --porcelain --untracked-files=no | wc -l) $(date -u +%T)"
for r in run_786_security_replays.py run_786_security_replays_dsl2.py run_786_security_replays_dsl3.py run_786_security_replays_dsl4.py; do $PY reference/$r --all --output-dir $O/786 > $O/$r.log 2>&1; echo "$r exit=$?"; grep -E "PASS|FAIL|BLOCKED" $O/$r.log | cut -c1-100; done
$PY reference/run_644_v7_replays.py --all --output-dir $O/644 > $O/644.log 2>&1; echo "644 exit=$?"; grep -E "PASS|FAIL|BLOCKED" $O/644.log | cut -c1-100
$PY scripts/verify_786_security_replays.py --evidence-root $O/786 --reexecute --declaration reports/runtime/baseline-v7-declaration.json > $O/verify-786-reexecute.json 2>&1; echo "verify786 exit=$?"
$PY scripts/verify_644_v7_replays.py --evidence-root $O/644 --reexecute --declaration reports/runtime/baseline-v7-declaration.json > $O/verify-644-reexecute.json 2>&1; echo "verify644 exit=$?"
echo "== crash matrix"; $PY reports/validation/821-atomic-config-binding/probes/crash_window.py reference --json $O/crash-window.json > $O/crash-window.log 2>&1; echo "crash exit=$?"
echo "== done $(date -u +%T)"
