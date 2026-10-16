"""Real-process stress: several writer processes record the witness concurrently while the parent
SIGKILLs them at random moments (with the witness window widened by random sleeps). Afterwards and
periodically, a fresh process must recover the store; the witness must be readable, <= the
database generation, and name the database's own journal digest.

usage: p2_kill_stress.py <reference-dir> <seconds> <writers> <seed>
"""
import json
import os
import random
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REF, SECONDS, WRITERS, SEED = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
PY = sys.executable

WRITER = r'''
import os, random, sys, time
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import sqlite_runtime as sr
root, ident = sys.argv[2], sys.argv[3]
rng = random.Random(os.getpid())
real_replace, real_fdopen = sr.os.replace, sr.os.fdopen
def replace(src, dst, *a, **k):
    if os.path.basename(os.fspath(dst)) == "generation-witness.json":
        time.sleep(rng.random() * 0.03)
    return real_replace(src, dst, *a, **k)
def fdopen(fd, *a, **k):
    h = real_fdopen(fd, *a, **k)
    time.sleep(rng.random() * 0.02)
    return h
sr.os.replace = replace
sr.os.fdopen = fdopen
import pathlib
real_popen = pathlib.Path.open
def popen(self, *a, **k):
    h = real_popen(self, *a, **k)
    if self.name.startswith(".generation-witness") and self.name.endswith(".tmp"):
        time.sleep(rng.random() * 0.02)
    return h
pathlib.Path.open = popen
i = 0
while True:
    i += 1
    try:
        m = AgentMemory.open(root, tenant="tenant:s", actor_id="agent:" + ident, scope="project:s", purpose="s")
        try:
            m.remember("memory:%s-%d" % (ident, i), "Writer %s fact %d." % (ident, i))
        finally:
            m.close()
    except Exception as e:
        msg = str(e)
        if "witness" in msg or "behind" in msg or "continue the history" in msg:
            print("WITNESS-REFUSAL", type(e).__name__, msg, flush=True)
            sys.exit(3)
        print("other-error", type(e).__name__, msg[:200], flush=True)
        time.sleep(0.01)
'''

CHECK = r'''
import sys, json
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
m = AgentMemory.open(sys.argv[2], tenant="tenant:s", actor_id="agent:check", scope="project:s", purpose="s")
d = m.runtime.durable_runtime
print(json.dumps({"gen": d.recovery_evidence.generation if hasattr(d.recovery_evidence, "generation") else None}))
m.close()
'''


def witness_vs_db(root):
    w = json.loads((root / "generation-witness.json").read_bytes())
    c = sqlite3.connect(f"file:{root / 'agent-memory.sqlite3'}?mode=ro", uri=True)
    try:
        gen = c.execute("SELECT json_extract(payload_json,'$.generation') FROM runtime_state WHERE singleton=1").fetchone()[0]
        j = c.execute("SELECT payload_json FROM runtime_journal WHERE generation=?", (w["generation"],)).fetchone()
    finally:
        c.close()
    ok = w["generation"] <= gen and (w["generation"] == 0 or (j and json.loads(j[0])["record_digest"] == w["journal_record_digest"]))
    return w["generation"], gen, ok


def main():
    rng = random.Random(SEED)
    with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(__file__))) as d:
        root = Path(d) / "store"
        subprocess.run([PY, "-c", CHECK, REF, str(root)], check=True, capture_output=True)
        procs = {}
        kills = refusals = checks = lags = 0
        logs = []
        deadline = time.monotonic() + SECONDS
        n = 0
        while time.monotonic() < deadline:
            for k in range(WRITERS):
                p = procs.get(k)
                if p is None or p.poll() is not None:
                    if p is not None:
                        out = p.stdout.read()
                        if "WITNESS-REFUSAL" in out:
                            refusals += 1
                            logs.append(out[-600:])
                    n += 1
                    procs[k] = subprocess.Popen([PY, "-c", WRITER, REF, str(root), f"w{n}"],
                                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            time.sleep(rng.random() * 0.4)
            victim = procs[rng.randrange(WRITERS)]
            if victim.poll() is None:
                victim.send_signal(signal.SIGKILL)
                victim.wait()
                kills += 1
            if rng.random() < 0.15:
                wg, dg, ok = witness_vs_db(root)
                checks += 1
                lags += wg < dg
                if not ok:
                    print("BAD WITNESS", wg, dg)
        for p in procs.values():
            p.send_signal(signal.SIGKILL)
            p.wait()
            out = p.stdout.read()
            if "WITNESS-REFUSAL" in out:
                refusals += 1
                logs.append(out[-600:])
        final = subprocess.run([PY, "-c", CHECK, REF, str(root)], capture_output=True, text=True)
        wg, dg, ok = witness_vs_db(root)
        orphans = sorted(p.name for p in root.iterdir() if p.name.startswith(".generation-witness"))
        print(json.dumps({"seed": SEED, "kills": kills, "spawned": n, "witness_refusals_in_writers": refusals,
                          "mid_checks": checks, "mid_lags": lags, "final_recover_rc": final.returncode,
                          "final_stderr_tail": final.stderr[-400:], "final_witness_gen": wg, "final_db_gen": dg,
                          "final_witness_ok": ok, "orphan_temporaries": len(orphans),
                          "orphan_sample": orphans[:3]}, indent=1))
        for l in logs[:3]:
            print("LOG:", l)


main()
