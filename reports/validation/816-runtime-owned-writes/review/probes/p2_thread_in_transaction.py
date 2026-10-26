"""P2: the guard keys on ``connection.in_transaction``, which is per connection, not per lock owner.

Thread A runs a supported generation (durable_runtime.run_governed_read) and pauses inside it.
Thread B, NOT holding the serialization lock, calls adapter.governed_recall directly. Case 1: A commits.
Case 2: A's operation raises (rollback). Reports whether B was refused, and what became durable.
"""
import sys, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403


def run(a_fails: bool):
    root, m = fresh()
    adapter = m.runtime.adapter
    inside, release = threading.Event(), threading.Event()
    out = {}

    def op():
        inside.set()
        release.wait(5)
        if a_fails:
            raise RuntimeError("A's operation fails -> rollback")
        return "A done"

    def thread_a():
        try:
            out["a"] = m.runtime.durable_runtime.run_governed_read(op)
        except Exception as exc:  # noqa: BLE001
            out["a"] = f"raised {exc}"

    t = threading.Thread(target=thread_a)
    t.start()
    inside.wait(5)
    try:
        r = adapter.governed_recall("deploy", m._handle_recall_context())
        out["b"] = f"NOT refused; decision ids {sorted(d['decision_id'] for d in r.decisions.values())}"
    except Exception as exc:  # noqa: BLE001
        out["b"] = f"refused {type(exc).__name__}"
    release.set()
    t.join()
    # what is durable now?
    events = adapter.export_checkpoint_state()["events"]
    recall_events = [e for e in events if e.get("event_type", "").startswith("memory.recall")]
    nxt = m.runtime.recall("deploy", m._handle_recall_context())  # next supported generation
    nxt_ids = sorted(d["decision_id"] for d in nxt.decisions.values())
    m.close()
    print(f"A {'fails' if a_fails else 'commits'}: A={out['a']!r}; B (unlocked direct adapter call during A's txn): {out['b']}; "
          f"recall events in live adapter after A: {len(recall_events)}; next supported recall decision ids {nxt_ids}; {try_reopen(root)}")


run(False)
run(True)
