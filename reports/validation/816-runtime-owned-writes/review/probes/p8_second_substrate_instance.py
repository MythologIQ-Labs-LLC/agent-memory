"""P8: ownership is a flag on one SQLiteTemporalGraph instance, not a property of the store.

A second SQLiteTemporalGraph on the same database file (no runtime) plus a GovernedMemoryAdapter over it
allocates ids in autocommit on a store a runtime owns; the store then fails to reopen.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403
from agentmem_ref.state.sqlite_substrate import SQLiteTemporalGraph
from agentmem_ref.runtime.adapter import GovernedMemoryAdapter

root, m = fresh()
m.close()
g = SQLiteTemporalGraph(Path(root) / "agent-memory.sqlite3")
a = GovernedMemoryAdapter(g, TENANT)
try:
    print("second-instance adapter.mint_id():", a.mint_id(), "(not refused)")
except Exception as exc:  # noqa: BLE001
    print("refused:", type(exc).__name__)
g.close()
print("then", try_reopen(root))
