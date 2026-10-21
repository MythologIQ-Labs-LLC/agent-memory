"""R8: two real writer processes, frozen code path unmodified except fault injection at the OS boundary.
A: remember -> COMMIT -> GenerationWitness.record writes+fsyncs the shared tmp, then is delayed 1.5s
   before os.replace (models descheduling).
B: started 0.5s later: remember -> COMMIT -> record opens the shared tmp 'wb' (truncating A's inode)
   and is SIGKILLed before writing (models a crash in that window; ENOSPC on write is equivalent).
A then renames the truncated inode over the witness. Parent reopens.  usage: python r8.py <tree>"""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
T = sys.argv[1]; PY = sys.executable
O = dict(tenant="tenant:r8", actor_id="agent:r8", scope="project:r8", purpose="r8 probe")
CHILD = r'''
import os, sys, json, time, signal, pathlib
sys.path.insert(0, sys.argv[1] + "/reference")
from agentmem_ref import AgentMemory
root, role, O = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
if role == "A":
    real = os.replace
    def rep(src, dst, *a, **k):
        if str(dst).endswith("generation-witness.json"): time.sleep(1.5)
        return real(src, dst, *a, **k)
    os.replace = rep
else:
    real_open = pathlib.Path.open
    def op(self, mode="r", *a, **k):
        h = real_open(self, mode, *a, **k)
        if self.name == ".generation-witness.json.tmp" and "w" in mode: os.kill(os.getpid(), signal.SIGKILL)
        return h
    pathlib.Path.open = op
with AgentMemory.open(root, **O) as m:
    m.remember("memory:" + role, role + " fact")
'''
SEED = r'''
import sys, json
sys.path.insert(0, sys.argv[1] + "/reference")
from agentmem_ref import AgentMemory
try:
    with AgentMemory.open(sys.argv[2], **json.loads(sys.argv[3])) as m:
        if len(sys.argv) > 4: m.remember("memory:seed", "seed fact")
        print(json.dumps({"opens": True, "hits": {q: len(m.recall(q)["returned"]) for q in ("seed", "A fact", "B fact")}}))
except Exception as e:
    print(json.dumps({"opens": False, "error": type(e).__name__ + ": " + str(e)[:200]}))
'''
with tempfile.TemporaryDirectory() as t:
    root = Path(t) / "s"
    subprocess.run([PY, "-c", SEED, T, str(root), json.dumps(O), "seed"], capture_output=True)
    a = subprocess.Popen([PY, "-c", CHILD, T, str(root), "A", json.dumps(O)], stderr=subprocess.PIPE)
    time.sleep(0.5)
    b = subprocess.run([PY, "-c", CHILD, T, str(root), "B", json.dumps(O)], capture_output=True)
    a.wait()
    w = root / "generation-witness.json"
    print(json.dumps({"A_rc": a.returncode, "B_rc": b.returncode, "witness_bytes": w.stat().st_size}))
    r = subprocess.run([PY, "-c", SEED, T, str(root), json.dumps(O)], capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1])
    w.unlink()   # the operator remedy
    r = subprocess.run([PY, "-c", SEED, T, str(root), json.dumps(O)], capture_output=True, text=True)
    print(json.dumps({"after_operator_removes_witness": json.loads(r.stdout.strip().splitlines()[-1])}))
