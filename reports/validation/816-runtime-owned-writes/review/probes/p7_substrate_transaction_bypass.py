"""P7: the guard accepts any open SQLite transaction, not a runtime generation.

``substrate.transaction()`` (public on SQLiteTemporalGraph, reached via adapter.checkpoint_substrate()) opens
BEGIN IMMEDIATE and COMMITs without publishing a generation. A governed act inside it passes the #816
guard, commits the advanced id counter, and the store no longer reopens: the original #816 failure.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403

root, m = fresh()
sub = m.runtime.adapter.checkpoint_substrate()
try:
    with sub.transaction():
        r = m.runtime.adapter.governed_recall("deploy", m._handle_recall_context())
    print("governed_recall inside substrate.transaction(): NOT refused, committed; admitted", r.admitted)
except Exception as exc:  # noqa: BLE001
    print("refused:", type(exc).__name__)
m.close()
print("close then", try_reopen(root))
