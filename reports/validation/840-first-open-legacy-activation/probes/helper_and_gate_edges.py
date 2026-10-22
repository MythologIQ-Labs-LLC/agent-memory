"""Edge probes of #840's helper and host gate at the tree under test (PYTHONPATH=reference)."""
import os, shutil, tempfile
from pathlib import Path
from agentmem_ref import AgentMemory
from agentmem_ref.api import surface
from agentmem_ref.host_activation import open_qualified_memory, UnqualifiedLegacyStoreError
d = Path(tempfile.mkdtemp()); target = d / "runtime-config.json"; orphan = d / ".runtime-config.json.abc12345.tmp"; orphan.write_text("ORPHAN")
surface._atomic_write_text(target, "NEW"); print("C1 another writer's orphan temp untouched:", orphan.read_text() == "ORPHAN")
d = Path(tempfile.mkdtemp()); root = d / "r"; root.mkdir(); victim = d / "victim"; victim.write_text("KEEP"); (root / "runtime-config.json").symlink_to(victim)
try: AgentMemory.open(root).close(); print("C2 planted final-path symlink: opened")
except Exception as exc: print("C2 planted final-path symlink to a non-config file: refused", type(exc).__name__, "| victim intact:", victim.read_text() == "KEEP")
d = Path(tempfile.mkdtemp()); root = d / "r"; root.mkdir(); (root / "runtime-config.json").symlink_to(d / "nowhere"); AgentMemory.open(root).close()
print("C3 dangling final-path symlink replaced by a regular file:", (root / "runtime-config.json").is_file() and not (root / "runtime-config.json").is_symlink(), "| dangling target created:", (d / "nowhere").exists())
d = Path(tempfile.mkdtemp()); target = d / "runtime-config.json"
class Boom(str):
    def endswith(self, *a): raise OSError("write failed")
try: surface._atomic_write_text(target, Boom("x"))
except OSError: print("C4 mid-write failure: target exists", target.exists(), "| temps left", list(d.glob(".*")))
d = Path(tempfile.mkdtemp()); target = d / "runtime-config.json"; old = os.umask(0o022); surface._atomic_write_text(target, "x"); os.umask(old)
print("C5 published mode under umask 022:", oct(target.stat().st_mode & 0o777))
fx = Path("reference/fixtures/809-legacy-stores/cross-scope"); tgt = Path(tempfile.mkdtemp()) / "s"; shutil.copytree(fx, tgt)
ID = dict(tenant="tenant:legacy", actor_id="agent:legacy", scope="project:b", purpose="p")
try:
    with open_qualified_memory(tgt, **ID): pass
except UnqualifiedLegacyStoreError: print("C6 gate refuses the pending fixture")
with AgentMemory.open(tgt, **ID) as m: print("C6 plain open still admits it: recall admitted", len(m.recall("Quillon ferry berth")["admitted"]), "| any handle may self-migrate ->", m.upgrade_canonical_derivation()["status"])
try:
    with open_qualified_memory(tgt, tenant="tenant:other", actor_id="agent:x", scope="project:b"): print("C7 FAIL")
except Exception as exc: print("C7 foreign tenant on the qualified store refused by the runtime:", type(exc).__name__)
with tempfile.TemporaryDirectory() as dd:
    try:
        with open_qualified_memory(Path(dd) / "n", **ID) as m: h = m; raise KeyboardInterrupt
    except KeyboardInterrupt: print("C8 handle closed after BaseException inside the gate:", h.closed)
