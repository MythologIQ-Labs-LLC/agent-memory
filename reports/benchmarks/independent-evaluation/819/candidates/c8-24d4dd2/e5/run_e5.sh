#!/bin/bash
# e5 eight-arm matrix (arms fixed in holdout-e5/ARMS-ADDENDUM.md, commit 8f217f08). Sequential; one arm at a time.
set -u
cd /home/user/eval/holdout-e5
sha256sum -c SHA256SUMS || exit 1
echo "$(sha256sum run_rp.py)" ; mkdir -p results
REP=/home/user/eval/semantic-model
steal() { awk '/^cpu /{print $9, $2+$3+$4+$5+$6+$7+$8+$9}' /proc/stat; }
arm() { # name venv semantic wrapper
  s0=$(steal)
  free=$(df --output=avail -k /home/user | tail -1); [ "$free" -lt 2000000 ] && { echo "$1 SKIPPED low disk"; return; }
  S=""; [ "$3" != off ] && S="--semantic $3 --representation-dir $REP"
  env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u HF_TOKEN PYTHONHASHSEED=0 HF_HUB_OFFLINE=1 \
    /home/user/eval/venv-$2/bin/python /home/user/eval/tools/run_logged.py results/$1 \
    /home/user/eval/venv-$2/bin/python $4 cases.json results/$1.json.partial $S
  rc=$?; s1=$(steal); echo "$1 steal_ticks=$(( ${s1% *} - ${s0% *} ))/$(( ${s1#* } - ${s0#* } ))"
  if [ $rc -eq 0 ]; then mv results/$1.json.partial results/$1.json; echo "$1 done $(tail -1 results/$1.log)"; else echo "$1 FAILED rc=$rc"; fi
}
arm c4-def      c4 off      harness.py
arm c4-sem-rs   c4 required harness.py
arm c4-sem-rp   c4 required run_rp.py
arm c6-sem-rs   c6 required harness.py
arm c6-sem-rp   c6 required run_rp.py
arm c8-sem-rs   c8 required harness.py
arm c8-sem-rp   c8 required run_rp.py
arm c8-off      c8 off      harness.py
arm c8-sem-rs-rep2 c8 required harness.py
echo e5-done
