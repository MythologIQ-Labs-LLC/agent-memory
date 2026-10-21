"""P3: the owner hook (configuration-binding write) fails AFTER the SQLite commit.

(a) persist_visibility_snapshot through the config-bound runtime: the base runtime's own
    ``except Exception: self.visibility_snapshots = previous`` now wraps the hook, so a binding
    failure rolls back the in-memory snapshot although SQLite committed it. The next generation
    then silently drops a committed visibility obligation.
(b) facade remember with a binding failure (pre-existing window; for comparison).
"""
import sys
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403
from agentmem_ref.runtime import configured_restart


def committed_visibility(root):
    import json, sqlite3
    c = sqlite3.connect(f"file:{Path(root) / 'agent-memory.sqlite3'}?mode=ro", uri=True)
    try:
        row = c.execute("SELECT payload_json FROM runtime_state").fetchone()
        gen = json.loads(row[0])["generation"]
        # governance residual carries visibility snapshots
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        hit = []
        for t in tables:
            for r in c.execute(f"SELECT * FROM {t}"):
                if any(isinstance(v, str) and "op:probe" in v for v in r):
                    hit.append(t)
        return gen, sorted(set(hit))
    finally:
        c.close()


def boom(*a, **k):
    raise OSError("simulated binding write failure (ENOSPC)")


# (a)
root, m = fresh()
dr = m.runtime.durable_runtime
real = configured_restart.ConfigBindingStore.checkpoint
with mock.patch.object(configured_restart.ConfigBindingStore, "checkpoint", boom):
    try:
        dr.persist_visibility_snapshot("op:probe", {"operation": {"required_projection_ids": []}})
        print("(a) persist_visibility_snapshot returned")
    except OSError as exc:
        print(f"(a) persist_visibility_snapshot raised {exc}")
print(f"(a) after failure: SQLite committed gen/tables containing op:probe = {committed_visibility(root)}; "
      f"in-memory base.visibility_snapshots has op:probe: {'op:probe' in dr.base.visibility_snapshots}")
m.recall("deploy window")  # next supported generation, binding works again
print(f"(a) after next facade op: committed = {committed_visibility(root)}; in-memory has op:probe: "
      f"{'op:probe' in dr.base.visibility_snapshots}")
m.close()
m2 = opened(root)
print(f"(a) reopened: recovered visibility ops = {sorted(m2.runtime.durable_runtime.base.visibility_snapshots)}")
m2.close()

# (b)
root, m = fresh()
with mock.patch.object(configured_restart.ConfigBindingStore, "checkpoint", boom):
    try:
        m.remember("memory:y", "Lunch is at noon.")
        print("(b) remember returned")
    except OSError as exc:
        print(f"(b) remember raised {exc}")
m.close()
print(f"(b) close then {try_reopen(root)}")
