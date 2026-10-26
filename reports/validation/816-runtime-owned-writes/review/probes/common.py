"""Shared helpers for the #816 adversarial probes. Usage: import with REF=<worktree>/reference on sys.path."""
import hashlib, json, sqlite3, sys, tempfile
from pathlib import Path

REF = sys.argv[1]
sys.path.insert(0, REF)
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api import contract  # noqa: E402

TENANT, SCOPE = "tenant:p", "project:p"


def opened(root, actor="agent:a", scope=SCOPE):
    return AgentMemory.open(root, tenant=TENANT, actor_id=actor, scope=scope, purpose="probe")


def fresh():
    root = tempfile.mkdtemp(prefix="816r-")
    m = opened(root)
    assert m.remember("memory:x", "The deploy window is Thursday.")["committed"]
    return root, m


def rows(root):
    uri = f"file:{Path(root) / 'agent-memory.sqlite3'}?mode=ro"
    c = sqlite3.connect(uri, uri=True)
    try:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {t: sorted(map(tuple, c.execute(f"SELECT * FROM {t}").fetchall()), key=repr) for t in tables}
    finally:
        c.close()


def gov(m):
    s = m.runtime.adapter.export_checkpoint_state()
    return hashlib.sha256(json.dumps(s, sort_keys=True, default=str).encode()).hexdigest()[:16]


def gov_state(m):
    return m.runtime.adapter.export_checkpoint_state()


def diff_keys(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def gen(m):
    return m.runtime.durable_runtime.base._observed_generation


def try_reopen(root, actor="agent:c"):
    try:
        m2 = opened(root, actor)
        m2.close()
        return "reopen OK"
    except Exception as exc:  # noqa: BLE001
        return f"reopen FAILED {type(exc).__name__}: {exc}"
