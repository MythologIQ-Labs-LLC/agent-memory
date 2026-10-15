"""P13: KeyboardInterrupt inside persist_visibility_snapshot's checkpoint. The transaction rolls back
(dc7d3f3f), but ``except Exception`` does not undo the in-memory snapshot, so the next generation publishes
a snapshot whose own generation never committed."""
import sys
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403

root, m = fresh()
base = m.runtime.durable_runtime.base
real = type(base)._persist_unlocked
def interrupted(self):
    raise KeyboardInterrupt
with mock.patch.object(type(base), "_persist_unlocked", interrupted):
    try:
        m.runtime.durable_runtime.persist_visibility_snapshot("op:int", {"operation": {"required_projection_ids": []}})
    except KeyboardInterrupt:
        print("persist_visibility_snapshot interrupted; generation", gen(m))
print("in-memory has op:int after rollback:", "op:int" in base.visibility_snapshots)
m.recall("deploy window")
m.close()
m2 = opened(root)
print("after next facade op + reopen, recovered visibility ops:", sorted(m2.runtime.durable_runtime.base.visibility_snapshots))
m2.close()
