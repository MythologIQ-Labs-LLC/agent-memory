"""Direct reproduction of the two #836-challenge findings on an unmodified tree (run with
PYTHONPATH=reference from a checkout of the tree under test). Prints what the tree does."""
import os, shutil, tempfile, threading
from pathlib import Path
from agentmem_ref import AgentMemory
from agentmem_ref.api import surface
print("helper uses NamedTemporaryFile:", "NamedTemporaryFile" in open(surface.__file__).read())
d = Path(tempfile.mkdtemp()); root = d / "runtime"; root.mkdir(); victim = d / "victim.txt"; victim.write_text("KEEP ME")
(root / ".runtime-config.json.tmp").symlink_to(victim)
m = AgentMemory.open(root); m.close()
print("B1 planted-symlink first open: victim intact:", victim.read_text() == "KEEP ME", "| symlink still present:", (root / ".runtime-config.json.tmp").is_symlink())
d2 = Path(tempfile.mkdtemp()); target = d2 / "runtime-config.json"
gate = threading.Barrier(2); orig = os.replace; names = set()
def paused_replace(src, dst):
    names.add(Path(src).name); gate.wait(timeout=10); return orig(src, dst)
surface.os.replace = paused_replace; errs = []
def w(v):
    try: surface._atomic_write_text(target, v)
    except Exception as e: errs.append(type(e).__name__)
ts = [threading.Thread(target=w, args=(c * 8192,)) for c in "AB"]; [t.start() for t in ts]; [t.join() for t in ts]
surface.os.replace = orig
print("B2 two writers at the replace boundary: errors", errs, "| distinct staging names", len(names), "| published intact", target.read_text() in ("A"*8192+"\n", "B"*8192+"\n"))
fx = Path("reference/fixtures/809-legacy-stores/cross-scope"); tgt = Path(tempfile.mkdtemp()) / "store"; shutil.copytree(fx, tgt)
m = AgentMemory.open(tgt, tenant="tenant:legacy", actor_id="agent:legacy", scope="project:b", purpose="probe")
st = m.legacy_upgrade_status(); r = m.recall("Quillon ferry berth")
print("A legacy_pending fixture through plain AgentMemory.open: status", st["status"], "legacy_facts", st["legacy_facts"], "| recall admitted", len(r["admitted"]), "| remember committed", m.remember("memory:probe", "written through the unguarded facade")["committed"])
m.close()
