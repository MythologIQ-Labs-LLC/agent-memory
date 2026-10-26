"""P14 (d0d2a97): failure of the gen-0 witness write inside generation 1, and whether N4
(witness >= 1 requires a binding row) can strand a legitimately migrated legacy store."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
from agentmem_ref.runtime import sqlite_runtime as R  # noqa: E402

LEGACY = REF / "fixtures" / "821-legacy-stores" / "coherent"
LT, LS = "tenant:821-legacy", "project:821-legacy"
W = "generation-witness.json"


def main():
    # gen-0 witness write fails inside generation 1 (OSError and KeyboardInterrupt)
    for exc in (OSError("read-only"), KeyboardInterrupt()):
        root = C.tmp() / "s"
        with mock.patch.object(R.GenerationWitness, "record", side_effect=exc):
            try:
                C.open_mem(root).close(); out = "create succeeded"
            except BaseException as e:  # noqa
                out = f"create raised {type(e).__name__}"
        i = C.inspect(root)
        print(f"gen-0 witness write {type(exc).__name__}: {out}; db={i['db']} state={i['state_gen']} "
              f"witness={(root / W).exists()} | retry open: {C.try_open(root)[:110]}")

    # legacy migration: witness write fails (OSError) / interrupted after COMMIT
    for exc in (OSError("disk"), KeyboardInterrupt()):
        root = C.tmp() / "leg"; shutil.copytree(LEGACY, root)
        m = C.open_mem(root, tenant=LT, scope=LS)
        with mock.patch.object(R.GenerationWitness, "record", side_effect=exc):
            try:
                m.recall("deploy"); out = "recall returned"
            except BaseException as e:  # noqa
                out = f"raised {type(e).__name__}"
        i = C.inspect(root)
        m.close()
        r1 = C.try_open(root, tenant=LT, scope=LS)
        m = C.open_mem(root, tenant=LT, scope=LS); m.recall("deploy"); m.close()
        r2 = C.try_open(root, tenant=LT, scope=LS)
        print(f"legacy migration, witness write {type(exc).__name__}: {out}; state={i['state_gen']} row={i['row_gen']} "
              f"witness={(root / W).exists()} | reopen: {r1[:60]} | after next gen: {r2[:60]}")

    # N4 must not misfire: legacy store, migrate, then drop the table (attack) vs. a clean migrated store
    root = C.tmp() / "leg2"; shutil.copytree(LEGACY, root)
    m = C.open_mem(root, tenant=LT, scope=LS); m.recall("deploy"); m.close()
    print("migrated legacy store reopen:", C.try_open(root, tenant=LT, scope=LS)[:70])
    import sqlite3
    c = sqlite3.connect(C.db(root)); c.execute(f"DROP TABLE {C.TABLE}"); c.commit(); c.close()
    import json
    rec = json.loads((root / "configuration-binding.json").read_text())
    print("  drop table (file lags) with witness:", C.try_open(root, tenant=LT, scope=LS)[:150])

    # N4 closes drop-table + forged file on a new store
    root = C.tmp() / "s"
    m = C.open_mem(root); m.remember("memory:x", "seed"); m.close()
    c = sqlite3.connect(C.db(root))
    g, p = c.execute(f"SELECT generation, payload_json FROM {C.TABLE}").fetchone(); p = json.loads(p)
    c.execute(f"DROP TABLE {C.TABLE}"); c.commit(); c.close()
    leg = {k: v for k, v in p.items() if k not in ("binding_protocol", "tenant", "record_digest")}
    leg["base"] = {k: v for k, v in p["base"].items() if k != "journal_record_digest"}
    (root / "configuration-binding.json").write_text(json.dumps(leg))
    print("drop table + forged legacy file, witness present:", C.try_open(root)[:150])
    (root / W).unlink()
    print("  ... witness also deleted (residual):", C.try_open(root)[:80])


if __name__ == "__main__":
    main()
