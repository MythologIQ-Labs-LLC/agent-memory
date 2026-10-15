"""#816 reproduction probe: adapter-level governed_recall on a facade-owned SQLite handle."""
import sys, tempfile, json
sys.path.insert(0, sys.argv[1])
from agentmem_ref.api.surface import AgentMemory
from agentmem_ref.runtime.restart_runtime import RuntimeRecoveryError

def opened(root):
    return AgentMemory.open(root, tenant="tenant:t", actor_id="agent:a", scope="project:a", purpose="probe")

def case(name, between):
    root = tempfile.mkdtemp(prefix="816-")
    m = opened(root)
    r = m.remember("memory:x", "The deploy window is Thursday")
    assert r["committed"], r
    try:
        between(m); note = ""
    except Exception as exc:
        note = f"[call refused: {type(exc).__name__}] "
    m.close()
    try:
        m2 = opened(root); m2.close(); out = "reopen OK"
    except RuntimeRecoveryError as exc:
        out = f"RuntimeRecoveryError: {exc}"
    print(f"{name:40s} {note}{out}")

case("control: nothing", lambda m: None)
case("control: facade recall", lambda m: m.recall("deploy window"))
case("defect: adapter.governed_recall", lambda m: m.runtime.adapter.governed_recall("deploy window", m._handle_recall_context()))
case("defect then facade recall", lambda m: (m.runtime.adapter.governed_recall("deploy window", m._handle_recall_context()), m.recall("deploy window")))
