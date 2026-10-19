#!/bin/bash
# Independent re-qualification of one #821 tree. usage: qualify.sh WORKTREE LABEL
set -u
export PYTHONPATH=$1/reference
export PATH=/home/user/eval/venv-neutral/bin:$PATH
T=$1; L=$2; O=/home/user/eval/r821/q-$L; mkdir -p $O; PY=/home/user/eval/venv-neutral/bin/python
REC=/home/user/eval/am-821-frozen/reports/validation/816-runtime-owned-writes/security-replays-e13d8c58
cd $T
echo "head $(git rev-parse HEAD) tree $(git rev-parse HEAD:reference) dirty_before=$(git status --porcelain | wc -l)" | tee $O/identity.txt
# focused
for t in test_821_atomic_config_binding test_816_runtime_owned_writes; do
  env -u AGENT_MEMORY_REPRESENTATION_DIR $PY -m unittest discover -s reference/tests -t reference -p "$t.py" > $O/$t.log 2>&1; echo "$t rc=$? $(tail -1 $O/$t.log)" | tee -a $O/summary.txt
done
# replays (outside the tree)
R=$O/replays; rm -rf $R; mkdir -p $R
$PY reference/run_786_security_replays.py --all --output-dir $R/run_786_security_replays > $O/replay-v2.log 2>&1; echo "replays v2 rc=$?" | tee -a $O/summary.txt
$PY reference/run_786_security_replays_dsl2.py --all --output-dir $R/run_786_security_replays_dsl2 > $O/replay-v3.log 2>&1; echo "replays dsl2 rc=$?" | tee -a $O/summary.txt
$PY reference/run_786_security_replays_dsl3.py --all --output-dir $R/run_786_security_replays_dsl3 > $O/replay-dsl3.log 2>&1; echo "replays dsl3 rc=$?" | tee -a $O/summary.txt
python3 - "$R" "$REC" <<'PYEOF' | tee -a $O/summary.txt
import json, sys, pathlib
mine, rec = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for m in sorted(mine.rglob("manifest.json")):
    j = json.load(open(m)); r = rec / m.relative_to(mine)
    ref = json.load(open(r))["observations_sha256"] if r.exists() else None
    print(f'replay {j["replay_id"]:58} {j["verdict"]:5} src={j["source_commit"][:8]} obs={j["observations_sha256"][:12]} vs816={"IDENTICAL" if ref == j["observations_sha256"] else ("DIFFERENT" if ref else "no-record")}')
PYEOF
# implementer's crash-window probe, run by the reviewer
$PY /home/user/eval/am-821-frozen/reports/validation/821-atomic-config-binding/probes/crash_window.py reference --json $O/crash-window.json > $O/crash-window.log 2>&1; echo "crash_window rc=$? $(tail -2 $O/crash-window.log | tr '\n' ' ')" | tee -a $O/summary.txt
# reviewer's adversarial suite
$PY /home/user/eval/r821/adv821.py $T $O/adv821.json --reps 3 > $O/adv821.log 2>&1; echo "adv821 rc=$? $(tail -1 $O/adv821.log)" | tee -a $O/summary.txt
# full suite, without and with the pinned model
env -u AGENT_MEMORY_REPRESENTATION_DIR OMP_NUM_THREADS=2 $PY -m unittest discover -s reference/tests -t reference > $O/full-nomodel.log 2>&1; echo "full-nomodel rc=$? $(tail -1 $O/full-nomodel.log) $(grep -E '^Ran ' $O/full-nomodel.log)" | tee -a $O/summary.txt
AGENT_MEMORY_REPRESENTATION_DIR=/home/user/eval/semantic-model OMP_NUM_THREADS=2 $PY -m unittest discover -s reference/tests -t reference > $O/full-model.log 2>&1; echo "full-model rc=$? $(tail -1 $O/full-model.log) $(grep -E '^Ran ' $O/full-model.log)" | tee -a $O/summary.txt
grep -E "^(FAIL|ERROR):" $O/full-nomodel.log | sort > $O/full-nomodel.failures; grep -E "^(FAIL|ERROR):" $O/full-model.log | sort > $O/full-model.failures
echo "dirty_after=$(git status --porcelain | wc -l)" | tee -a $O/identity.txt
echo qualify-done
