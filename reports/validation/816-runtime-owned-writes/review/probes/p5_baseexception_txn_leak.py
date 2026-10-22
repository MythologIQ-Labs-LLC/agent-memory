"""P5: a BaseException (KeyboardInterrupt) inside a generation escapes ``transaction()``'s ``except Exception``,
so neither ROLLBACK nor COMMIT runs and the connection stays ``in_transaction``. The #816 guard keys on
``in_transaction``, so it is now open for direct adapter calls on that handle.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403


root, m = fresh()
conn = m.runtime.adapter.checkpoint_substrate()._connection


def op():
    raise KeyboardInterrupt


try:
    m.runtime.durable_runtime.run_governed_read(op)
except KeyboardInterrupt:
    print("generation interrupted by KeyboardInterrupt")
print("connection.in_transaction after interrupt:", conn.in_transaction)
try:
    r = m.runtime.adapter.governed_recall("deploy", m._handle_recall_context())
    print("direct adapter.governed_recall after interrupt: NOT refused, admitted", r.admitted)
except Exception as exc:  # noqa: BLE001
    print("direct adapter.governed_recall after interrupt: refused", type(exc).__name__)
try:
    m.recall("deploy window")
    print("facade recall after interrupt: OK")
except Exception as exc:  # noqa: BLE001
    print("facade recall after interrupt:", type(exc).__name__, exc)
m.close()
print("close then", try_reopen(root))
