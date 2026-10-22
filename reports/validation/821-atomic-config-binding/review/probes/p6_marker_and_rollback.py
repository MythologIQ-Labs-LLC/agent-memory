"""P6: (a) the binding file was also the facade's/doctor's 'incomplete durable state' marker; what
happens now when the SQLite database of an existing store disappears? (b) restoring only an older
copy of the database file (directory otherwise current)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
from agentmem_ref.runtime import doctor  # noqa: E402


def store():
    root = C.tmp() / "s"
    m = C.open_mem(root)
    m.remember("memory:x", "The deploy window is Thursday.")
    m.remember("memory:y", "Lunch is at noon.")
    m.close()
    return root


def main():
    # (a) database lost, everything else (config, derived/ sidecars, binding file if any) kept
    root = store()
    leftovers_before = sorted(p.name for p in root.iterdir())
    for p in root.glob("agent-memory.sqlite3*"):
        p.unlink()
    print("files after DB loss:", sorted(p.name for p in root.iterdir()), "(before:", leftovers_before, ")")
    report = doctor.diagnose(root / "runtime-config.json", state_dir=root)
    print("doctor after DB loss:", report["durable_state"].get("status"), "|", report["recovery"].get("status"),
          "|", report.get("operational_readiness"))
    res = C.try_open(root)
    print("AgentMemory.open after DB loss:", res)
    if res.startswith("OK"):
        m = C.open_mem(root)
        print("  -> recall of prior facts returns:", len(m.recall("deploy window")["returned"]),
              "(silently reinitialized as empty memory)")
        m.close()

    # (b) only the database file restored to an older copy (store closed both times)
    root = store()
    old = C.tmp() / "old.sqlite3"
    shutil.copy2(C.db(root), old)
    old_gen = C.inspect(root)["state_gen"]
    m = C.open_mem(root)
    m.forget("memory:x")
    m.remember("memory:z", "The deploy window moved to Friday.")
    m.close()
    new_gen = C.inspect(root)["state_gen"]
    shutil.copy2(old, C.db(root))
    res = C.try_open(root)
    print(f"database-only rollback gen {new_gen} -> {old_gen}: open = {res}")
    if res.startswith("OK"):
        m = C.open_mem(root)
        print("  -> forgotten fact visible again:", len(m.recall("deploy window Thursday")["returned"]) > 0)
        m.close()


if __name__ == "__main__":
    main()
