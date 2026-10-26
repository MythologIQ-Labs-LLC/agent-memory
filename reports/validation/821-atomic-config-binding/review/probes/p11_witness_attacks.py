"""P11 (amendment 1): try to defeat or abuse the generation witness (W1-W4), check it never causes
acceptance, and check that recovery, close() and doctor never write it."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
from agentmem_ref.runtime import doctor  # noqa: E402
from agentmem_ref.runtime import sqlite_runtime as R  # noqa: E402

WN = "generation-witness.json"


def store(n=2, root=None, text="fact"):
    root = root or C.tmp() / "s"
    m = C.open_mem(root)
    for k in range(n):
        m.remember(f"memory:{text}{k}", f"{text} number {k} deploy")
    m.close()
    return root


def wit(root):
    p = Path(root) / WN
    return json.loads(p.read_text()) if p.exists() and p.is_file() else (None if not p.exists() else "dir")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12] if Path(p).is_file() else None


def line(name, root, expect=None, **kw):
    res = C.try_open(root, **kw)
    v = "ACCEPTED" if res.startswith("OK") else "REFUSED"
    mark = "" if expect is None or v == expect else f"  <-- UNEXPECTED (expected {expect})"
    print(f"{name:70s} {v:8s} {res[:160]}{mark}")
    return res


def main():
    # W1: older copy of the same database
    root = store(1); old = C.tmp() / "old.db"; shutil.copy2(C.db(root), old)
    store(2, root, "more"); shutil.copy2(old, C.db(root))
    line("W1 older copy of own DB", root, "REFUSED")

    # W1 defeated by deleting the witness (documented residual)
    (root / WN).unlink(); line("  ... same, witness deleted (documented residual)", root, "ACCEPTED")

    # backup_to copy restored over a live dir
    root = store(1); m = C.open_mem(root); bk = C.tmp() / "bk" / "agent-memory.sqlite3"
    m.runtime.durable_runtime.base.backup_to(bk); m.remember("memory:after", "after backup"); m.close()
    shutil.copy2(bk, C.db(root)); line("backup_to copy restored over the live dir", root, "REFUSED")

    # fork with the same history prefix, then diverged, at the same generation
    a = store(1); b = C.tmp() / "b"; shutil.copytree(a, b)
    ma = C.open_mem(a); ma.remember("memory:fa", "fork A"); ma.close()
    mb = C.open_mem(b); mb.remember("memory:fb", "fork B"); mb.close()
    shutil.copy2(C.db(b), C.db(a)); line("W2 same-prefix fork, same generation", a, "REFUSED")
    # fork B ahead
    mb = C.open_mem(b); mb.remember("memory:fb2", "fork B 2"); mb.close()
    shutil.copy2(C.db(b), C.db(a)); line("W2 same-prefix fork, fork ahead by one", a, "REFUSED")
    # identical deterministic forks
    a = store(1); b = C.tmp() / "b2"; shutil.copytree(a, b)
    for r in (a, b):
        m = C.open_mem(r); m.remember("memory:same", "identical act"); m.close()
    shutil.copy2(C.db(b), C.db(a)); line("fork with byte-identical history (indistinguishable)", a)

    # another store's DB, same tenant, higher generation
    a = store(1); b = store(3, text="other")
    shutil.copy2(C.db(b), C.db(a)); line("W2 another store's DB at a higher generation", a, "REFUSED")
    a = store(3); b = store(1, text="other")
    shutil.copy2(C.db(b), C.db(a)); line("W1 another store's DB at a lower generation", a, "REFUSED")

    # witness at generation 0 (create) + foreign DB
    a = C.tmp() / "s"; a.mkdir(parents=True)
    b = store(2, text="other")
    (a / WN).write_text(json.dumps({"schema": R.GENERATION_WITNESS_SCHEMA, "generation": 0, "journal_record_digest": ""}))
    shutil.copy2(b / "runtime-config.json", a / "runtime-config.json"); shutil.copy2(C.db(b), C.db(a))
    line("witness gen 0 + any foreign DB (no protection at gen 0)", a)

    # W3 malformed variants
    for label, value in (("generation true", True), ("generation 2.0", 2.0), ("generation -1", -1), ("generation '2'", "2")):
        root = store(2); w = wit(root); w["generation"] = value; (root / WN).write_text(json.dumps(w))
        line(f"W3 witness {label}", root, "REFUSED")
    root = store(2); (root / WN).write_text("{"); line("W3 witness not JSON", root, "REFUSED")
    root = store(2); (root / WN).unlink(); (root / WN).mkdir()
    res = line("witness path is a directory", root, "REFUSED")
    try:
        rep = doctor.diagnose(root / "runtime-config.json", state_dir=root)
        print("   doctor with witness-as-directory:", rep["recovery"].get("status"), rep["recovery"].get("detail", "")[:100])
    except Exception as e:  # noqa
        print(f"   doctor with witness-as-directory RAISED {type(e).__name__}: {e}  <-- doctor crashes instead of failed_closed")

    # witness ahead of a legitimate store (forged) -> refuses only
    root = store(2); w = wit(root); w["generation"] = 99; (root / WN).write_text(json.dumps(w))
    line("forged witness far ahead (refuse-only)", root, "REFUSED")
    # forged witness that 'agrees' cannot make a bad DB acceptable
    root = store(2); c = sqlite3.connect(C.db(root)); c.execute(f"UPDATE {C.TABLE} SET payload_json='x'"); c.commit(); c.close()
    line("matching witness + corrupt row (witness never accepts)", root, "REFUSED")

    # W4 via open, create and doctor
    root = store(2)
    for p in root.glob("agent-memory.sqlite3*"):
        p.unlink()
    line("W4 DB deleted, witness kept: open", root, "REFUSED")
    print("   files after refused open:", sorted(p.name for p in root.iterdir()))
    rep = doctor.diagnose(root / "runtime-config.json", state_dir=root)
    print("   doctor:", rep["durable_state"].get("status"), rep["recovery"].get("status"))
    # witness deleted too -> re-created as empty (documented residual)
    (root / WN).unlink(); line("  ... and witness deleted too (residual: reinitialized)", root)

    # recovery / close / doctor / posture never write the witness
    root = store(2)
    before = (sha(root / WN), (root / WN).stat().st_mtime_ns)
    m = C.open_mem(root); m.posture(); m.close()
    doctor.diagnose(root / "runtime-config.json", state_dir=root)
    after = (sha(root / WN), (root / WN).stat().st_mtime_ns)
    print(f"{'recovery+posture+close+doctor leave the witness untouched':70s} {before == after}")

    # legacy store: open (no generation) writes no witness
    lr = C.tmp() / "leg"; shutil.copytree(REF / "fixtures" / "821-legacy-stores" / "coherent", lr)
    m = C.open_mem(lr, tenant="tenant:821-legacy", scope="project:821-legacy"); m.close()
    print(f"{'legacy store open+close writes no witness':70s} {not (lr / WN).exists()}")

    # in-process: KeyboardInterrupt and OSError inside the witness write after COMMIT
    for exc in (OSError("disk"), KeyboardInterrupt()):
        root = store(1); m = C.open_mem(root)
        with mock.patch.object(R.GenerationWitness, "record", side_effect=exc):
            try:
                r = m.remember("memory:k", "committed despite witness failure")
                out = f"returned committed={r.get('committed')}"
            except BaseException as e:  # noqa
                out = f"raised {type(e).__name__}"
        cur = m.runtime.durable_runtime.generation_witness_current
        i, w = C.inspect(root), wit(root)["generation"]
        m.remember("memory:k2", "next"); w2 = wit(root)["generation"]; m.close()
        print(f"{'witness write ' + type(exc).__name__ + ' after COMMIT':70s} {out}; state={i['state_gen']} witness={w} "
              f"current_flag={cur}; next gen rewrote witness={w2}; reopen={C.try_open(root)[:40]}")


if __name__ == "__main__":
    main()
