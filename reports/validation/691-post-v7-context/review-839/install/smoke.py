import agentmem_ref, hashlib, tempfile
from pathlib import Path
from unittest import mock
from agentmem_ref import AgentMemory
from agentmem_ref.api import context_package, surface
from agentmem_ref.core import receipts
print("agentmem_ref from", agentmem_ref.__file__)
print("package version", context_package.PACKAGE_VERSION)
with tempfile.TemporaryDirectory() as d:
    m = AgentMemory.open(Path(d), tenant="t:i", actor_id="agent:i", scope="p:i", purpose="installed smoke")
    m.remember("memory:a", "Installed smoke: the kettle is in the left cupboard.", source_ref="user:me")
    pkg = m.recall_context("where is the kettle", max_items=3)
    receipts.validate("api-context-package.schema.json", pkg)
    ev = [e for e in m.runtime.adapter.events if e["event_type"] == "memory.context_delivery"]
    print("status", pkg["status"], "content", [i["content"] for i in pkg["items"]], "audit keys", sorted(pkg["audit"]), "receipts", len(ev), "bound", ev[0]["payload"]["recall_bound"], ev[0]["causation_id"] == pkg["audit"]["recall_event_id"])
    # #839 A: a rejected final package leaves no receipt
    with mock.patch.object(context_package, "PACKAGE_SCHEMA", "missing-839.json"):
        try: m.recall_context("where is the kettle"); print("A: NOT RAISED")
        except Exception as exc: print("A raised", type(exc).__name__)
    print("A receipts after fault", len([e for e in m.runtime.adapter.events if e["event_type"] == "memory.context_delivery"]))
    # #839 B: no recall event -> refusal, no receipt
    with mock.patch.object(surface, "_first_recall_event_since", return_value=None):
        try: m.recall_context("where is the kettle"); print("B: NOT RAISED")
        except surface.ContextDeliveryUnboundError as exc: print("B raised ContextDeliveryUnboundError")
    print("B receipts after fault", len([e for e in m.runtime.adapter.events if e["event_type"] == "memory.context_delivery"]))
    m.close()
    m = AgentMemory.open(Path(d), tenant="t:i", actor_id="agent:i", scope="p:i", purpose="installed smoke")
    print("receipts after reopen", len([e for e in m.runtime.adapter.events if e["event_type"] == "memory.context_delivery"]))
    m.close()
