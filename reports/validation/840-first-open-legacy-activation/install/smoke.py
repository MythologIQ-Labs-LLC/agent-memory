import importlib, shutil, sys, tempfile
from pathlib import Path
import agentmem_ref
from agentmem_ref import AgentMemory
from agentmem_ref.host_activation import open_qualified_memory, UnqualifiedLegacyStoreError
canonical = importlib.import_module("agentmem_ref.api.host_activation")
alias = importlib.import_module("agentmem_ref.host_activation")
print("agentmem_ref from", agentmem_ref.__file__)
print("alias is canonical:", alias is canonical, "| open_qualified_memory is canonical:", open_qualified_memory is canonical.open_qualified_memory)
from agentmem_ref.api import surface
import inspect
print("installed _atomic_write_text uses NamedTemporaryFile:", "NamedTemporaryFile" in inspect.getsource(surface._atomic_write_text))
FX = Path(sys.argv[1]); ID = dict(tenant="tenant:legacy", actor_id="agent:legacy", scope="project:b", purpose="smoke")
with tempfile.TemporaryDirectory() as d:
    pending = Path(d) / "pending"; shutil.copytree(FX / "cross-scope", pending)
    try:
        with open_qualified_memory(pending, **ID) as m: print("FAIL: pending store activated")
    except UnqualifiedLegacyStoreError as exc: print("pending fixture refused:", type(exc).__name__)
    with AgentMemory.open(pending, **ID) as maint: print("maintenance upgrade ->", maint.upgrade_canonical_derivation()["status"])
    with open_qualified_memory(pending, **ID) as m: print("qualified fixture activated:", m.legacy_upgrade_status()["status"], "recall ok:", isinstance(m.recall("Quillon ferry berth"), dict))
    quarantined = Path(d) / "q"; shutil.copytree(FX / "shared-membership", quarantined)
    ID2 = {**ID, "scope": "shared:x", "actor_id": "agent:o"}
    with AgentMemory.open(quarantined, **ID2) as maint: print("shared-membership upgrade ->", maint.upgrade_canonical_derivation()["status"])
    try:
        with open_qualified_memory(quarantined, **ID2) as m: print("FAIL: unqualified store activated")
    except UnqualifiedLegacyStoreError: print("unqualified fixture refused")
    fresh = Path(d) / "fresh"
    with open_qualified_memory(fresh, **ID) as m: print("fresh store activated:", m.legacy_upgrade_status()["status"], "remember:", m.remember("memory:a", "hello")["committed"])
    # planted symlink on first open through the installed package
    victim = Path(d) / "victim.txt"; victim.write_text("KEEP ME"); root2 = Path(d) / "r2"; root2.mkdir(); (root2 / ".runtime-config.json.tmp").symlink_to(victim)
    with AgentMemory.open(root2) as m: pass
    print("symlink probe: victim intact:", victim.read_text() == "KEEP ME", "| config created:", (root2/"runtime-config.json").is_file(), "| mode:", oct((root2/"runtime-config.json").stat().st_mode & 0o777))
    try:
        with open_qualified_memory(fresh, tenant="", actor_id="a", scope="s") as m: print("FAIL: blank tenant accepted")
    except ValueError: print("blank tenant refused")
