import importlib, inspect, shutil, sys, tempfile
from pathlib import Path
from unittest import mock
import agentmem_ref
from agentmem_ref import AgentMemory
from agentmem_ref.api import context_package, surface
from agentmem_ref.core import receipts
from agentmem_ref.host_activation import open_qualified_memory, UnqualifiedLegacyStoreError
print("agentmem_ref from", agentmem_ref.__file__)
print("aliases canonical:", importlib.import_module("agentmem_ref.host_activation") is importlib.import_module("agentmem_ref.api.host_activation"), importlib.import_module("agentmem_ref.context_package") is context_package)
print("installed writer exclusive:", "NamedTemporaryFile" in inspect.getsource(surface._atomic_write_text), "| packaged context schema:", (receipts._packaged_schemas() / "api-context-package.schema.json").exists())
FX = Path(sys.argv[1]); ID = dict(tenant="t:i", actor_id="agent:w", scope="p:i", purpose="installed smoke")
with tempfile.TemporaryDirectory() as d:
    root = Path(d) / "fresh"
    with open_qualified_memory(root, **ID) as m:
        m.remember("memory:a", "Installed smoke: the kettle is in the left cupboard.", source_ref="user:me")
        pkg = m.recall_context("where is the kettle", max_items=3); receipts.validate("api-context-package.schema.json", pkg)
        ev = [e for e in m.runtime.adapter.events if e["event_type"] == "memory.context_delivery"]
        print("guarded recall_context:", pkg["status"], [i["content"] for i in pkg["items"]], "audit keys", sorted(pkg["audit"]), "receipts", len(ev), "bound", ev[0]["causation_id"] == pkg["audit"]["recall_event_id"])
        with mock.patch.object(context_package, "PACKAGE_SCHEMA", "missing.json"):
            try: m.recall_context("kettle"); print("A NOT RAISED")
            except Exception as exc: print("A faulted final validation raised", type(exc).__name__)
        with mock.patch.object(surface, "_first_recall_event_since", return_value=None):
            try: m.recall_context("kettle"); print("B NOT RAISED")
            except surface.ContextDeliveryUnboundError: print("B unbound recall raised ContextDeliveryUnboundError")
        print("receipts after faults", len([e for e in m.runtime.adapter.events if e["event_type"] == "memory.context_delivery"]))
    with open_qualified_memory(root, tenant="t:i", actor_id="agent:colleague", scope="p:i", purpose="smoke") as c:
        pkg = c.recall_context("where is the kettle"); item = pkg["items"][0]
        print("colleague: text delivered", bool(item["content"]), "| memory_ref/source_ref hidden:", "memory_ref" not in item["provenance"] and "source_ref" not in item["provenance"], "| receipts after reopen", len([e for e in c.runtime.adapter.events if e["event_type"] == "memory.context_delivery"]))
    pending = Path(d) / "pending"; shutil.copytree(FX / "cross-scope", pending); LID = dict(tenant="tenant:legacy", actor_id="agent:legacy", scope="project:b", purpose="smoke")
    try:
        with open_qualified_memory(pending, **LID) as m: print("FAIL pending activated")
    except UnqualifiedLegacyStoreError: print("pending fixture refused by the gate")
    with AgentMemory.open(pending, **LID) as plain: print("plain open of the pending fixture still delivers context:", plain.recall_context("Quillon ferry berth")["status"])
    with AgentMemory.open(pending, **LID) as maint: print("maintenance upgrade ->", maint.upgrade_canonical_derivation()["status"])
    with open_qualified_memory(pending, **LID) as m: print("qualified fixture: recall_context", m.recall_context("Quillon ferry berth")["status"])
    q = Path(d) / "q"; shutil.copytree(FX / "shared-membership", q); QID = {**LID, "scope": "shared:x", "actor_id": "agent:o"}
    with AgentMemory.open(q, **QID) as maint: print("shared-membership upgrade ->", maint.upgrade_canonical_derivation()["status"])
    try:
        with open_qualified_memory(q, **QID) as m: print("FAIL unqualified activated")
    except UnqualifiedLegacyStoreError: print("unqualified fixture refused by the gate")
    victim = Path(d) / "victim"; victim.write_text("KEEP"); r2 = Path(d) / "r2"; r2.mkdir(); (r2 / ".runtime-config.json.tmp").symlink_to(victim)
    with AgentMemory.open(r2): pass
    print("symlink probe victim intact:", victim.read_text() == "KEEP", "| mode", oct((r2 / "runtime-config.json").stat().st_mode & 0o777))
