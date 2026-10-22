"""Both processes pass the database-exists check, then both call the fresh-store creator.
Reports the outcome distribution and the recovered root's state over N rounds (default 12)."""
import os, sys, subprocess, tempfile, time, collections
from pathlib import Path
worker = '''
import sys, time
from pathlib import Path
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import sqlite_composition as sc
root = Path(sys.argv[1]); name = sys.argv[2]
real_create = sc.SQLiteConfiguredCompositionRuntime.create.__func__
def gated_create(cls, *a, **k):
    (root / ("create-ready-" + name)).write_text("ready")
    while not (root / "create-go").exists(): time.sleep(0.002)
    return real_create(cls, *a, **k)
sc.SQLiteConfiguredCompositionRuntime.create = classmethod(gated_create)
try:
    m = AgentMemory.open(root)
except Exception as exc:
    print("REFUSED:" + type(exc).__name__ + ":" + str(exc)[:120])
else:
    try: print("OPENED committed=" + str(m.remember("memory:" + name, "written by " + name)["committed"]))
    finally: m.close()
'''
env = dict(os.environ, PYTHONPATH="reference"); dist = collections.Counter(); post = collections.Counter()
for r in range(int(sys.argv[1]) if len(sys.argv) > 1 else 12):
    root = Path(tempfile.mkdtemp()) / "runtime"; root.mkdir()
    ps = [subprocess.Popen([sys.executable, "-c", worker, str(root), n], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) for n in "AB"]
    while not all((root / f"create-ready-{n}").exists() for n in "AB"): time.sleep(0.005)
    (root / "create-go").write_text("go")
    outs = [p.communicate(timeout=60) for p in ps]
    dist[tuple(sorted(o[0].strip() for o in outs))] += 1
    from agentmem_ref import AgentMemory
    m = AgentMemory.open(root); present = [n for n in "AB" if m.history(f"memory:{n}")["history"]["current_fact_uuid"]]; st = m.legacy_upgrade_status()["status"]; m.close()
    post[("reopen OK", st, "survivors=" + "".join(present))] += 1
    leftovers = sorted(p.name for p in root.iterdir() if p.name.startswith(".runtime-config"))
    if leftovers: print("leftover temps:", leftovers)
print("outcomes:"); [print(" ", v, k) for k, v in dist.items()]
print("post-conditions:"); [print(" ", v, k) for k, v in post.items()]
