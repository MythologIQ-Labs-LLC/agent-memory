"""P7 (A7): a deterministic sequence of governed acts; print a digest of every table except the
binding row, plus the runtime_state / journal payloads, so base and candidate outputs can be
diffed. Any difference outside runtime_configuration_binding is a digest/journal change."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()


def main():
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else C.tmp() / "s"
    m = C.open_mem(root)
    m.remember("memory:a", "The deploy window is Thursday.")
    m.remember("memory:b", "Lunch is at noon.")
    m.recall("deploy window")
    out = {}
    for label, call in (
        ("correct", lambda: m.correct("memory:a", "The deploy window is Friday.")),
        ("dispute", lambda: m.dispute("memory:b")),
        ("forget", lambda: m.forget("memory:b")),
    ):
        try:
            r = call()
            out[label] = {k: r.get(k) for k in ("committed", "stage", "refusal") if isinstance(r, dict)}
        except Exception as e:  # noqa
            out[label] = f"{type(e).__name__}: {e}"
    d = m.runtime.durable_runtime
    d.persist_visibility_snapshot("op:p7", {"operation": {"required_projection_ids": []}})
    m.runtime.adapter.set_shared_domain_members("domain:p7", ("agent:a",))
    d.checkpoint()
    m.recall("Friday")
    m.close()
    print("acts:", json.dumps(out, sort_keys=True))
    c = sqlite3.connect(C.db(root))
    names = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for n in names:
        rows = sorted(map(tuple, c.execute(f"SELECT * FROM {n}").fetchall()), key=repr)
        print(f"table {n:34s} rows={len(rows):4d} sha={hashlib.sha256(repr(rows).encode()).hexdigest()[:16]}")
    state = json.loads(c.execute("SELECT payload_json FROM runtime_state").fetchone()[0])
    print("state substrate_digest:", state["substrate_digest"])
    print("state governance_digest:", state["governance_digest"])
    print("state journal_record_digest:", state["journal_record_digest"])
    print("state keys:", sorted(state))
    tail = json.loads(c.execute("SELECT payload_json FROM runtime_journal ORDER BY generation DESC LIMIT 1").fetchone()[0])
    print("journal tail keys:", sorted(tail), "schema", tail.get("schema_version"))
    c.close()


if __name__ == "__main__":
    main()
