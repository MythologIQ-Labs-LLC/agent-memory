"""#816 behaviour probe: each unsupported path, then close and reopen. Prints one line per case."""
import subprocess, sys, tempfile, textwrap
ref = sys.argv[1]
sys.path.insert(0, ref)
from agentmem_ref import AgentMemory

def opened(root, actor="agent:a"):
    return AgentMemory.open(root, tenant="tenant:t", actor_id=actor, scope="project:a", purpose="probe")

OTHER = textwrap.dedent("""
    import sys; sys.path.insert(0, sys.argv[1])
    from agentmem_ref import AgentMemory
    m = AgentMemory.open(sys.argv[2], tenant="tenant:t", actor_id="agent:b", scope="project:a", purpose="probe")
    assert m.remember("memory:y", "Lunch is at noon.")["committed"]; m.close()
""")

def run(name, between, *, other_process=False):
    root = tempfile.mkdtemp(prefix="816p-")
    m = opened(root)
    m.remember("memory:x", "The deploy window is Thursday.")
    if other_process:
        subprocess.run([sys.executable, "-c", OTHER, ref, root], check=True)
    try:
        between(m); call = "call returned"
    except Exception as exc:
        call = f"call raised {type(exc).__name__}"
    m.close()
    try:
        m2 = opened(root, "agent:c"); n = len(m2.recall("deploy window lunch noon")["returned"]); m2.close(); out = f"reopen OK ({n} returned)"
    except Exception as exc:
        out = f"reopen FAILED {type(exc).__name__}: {exc}"
    print(f"{name:44s} | {call:40s} | {out}")

ctx = lambda m: m._handle_recall_context()
run("control: no call", lambda m: None)
run("control: facade recall", lambda m: m.recall("deploy window"))
run("adapter.governed_recall (issue #816)", lambda m: m.runtime.adapter.governed_recall("deploy", ctx(m)))
run("adapter.mint_id", lambda m: m.runtime.adapter.mint_id())
run("adapter.now", lambda m: m.runtime.adapter.now())
run("base SQLite runtime governed_recall", lambda m: m.runtime.durable_runtime.base.governed_recall("deploy", ctx(m)))
run("stale handle, other process wrote; direct", lambda m: m.runtime.adapter.governed_recall("lunch", ctx(m)), other_process=True)
run("stale handle, other process wrote; facade", lambda m: m.recall("lunch"), other_process=True)
