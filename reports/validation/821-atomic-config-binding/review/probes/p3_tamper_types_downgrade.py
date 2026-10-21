"""P3: tampered rows, odd SQLite storage types, view/table substitution, downgrade to the legacy
file path, and legacy-file + row combinations. Each case reports ACCEPTED or REFUSED and whether
recovery changed any byte of the database (it must not)."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
LEGACY = REF / "fixtures" / "821-legacy-stores" / "coherent"
T = C.TABLE


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def seal(p):
    m = {k: v for k, v in p.items() if k != "record_digest"}
    return {**m, "record_digest": "sha256:" + hashlib.sha256(canon(m)).hexdigest()}


def fresh():
    root = C.tmp() / "s"
    m = C.open_mem(root)
    m.remember("memory:x", "The deploy window is Thursday.")
    m.close()
    return root


def migrated():
    root = C.tmp() / "s"
    shutil.copytree(LEGACY, root)
    m = C.open_mem(root, tenant="tenant:821-legacy", scope="project:821-legacy")
    m.recall("deploy")
    m.close()
    return root


def row(root):
    with sqlite3.connect(C.db(root)) as c:
        g, p = c.execute(f"SELECT generation, payload_json FROM {T}").fetchone()
    return g, json.loads(p)


def sql(root, *stmts):
    c = sqlite3.connect(C.db(root))
    for s, *args in stmts:
        c.execute(s, *args)
    c.commit()
    c.close()


def legacy_from_row(p):
    rec = {k: v for k, v in p.items() if k not in ("binding_protocol", "tenant", "record_digest")}
    rec["base"] = {k: v for k, v in p["base"].items() if k != "journal_record_digest"}
    return rec


def case(name, root, expect, **kw):
    before = C.tables_digest(root)
    res = C.try_open(root, **kw)
    after = C.tables_digest(root)
    verdict = "ACCEPTED" if res.startswith("OK") else "REFUSED"
    note = "" if before == after else "  <-- recovery CHANGED the database"
    mark = "" if verdict == expect else f"  <-- UNEXPECTED (expected {expect})"
    print(f"{name:62s} {verdict:8s} {res[:150]}{note}{mark}")


def main():
    if not C.has_row_protocol():
        print("no row protocol at this revision; probe targets the candidate")
        return
    r = fresh(); g, p = row(r)
    sql(r, (f"UPDATE {T} SET generation = ?", (str(g),)))
    case("generation column bound as TEXT (INTEGER affinity coerces)", r, "ACCEPTED")

    r = fresh(); g, p = row(r)
    sql(r, (f"UPDATE {T} SET generation = ?", (float(g),)))
    case("generation column stored as REAL (same value)", r, "ACCEPTED")

    r = fresh(); g, p = row(r)
    sql(r, (f"UPDATE {T} SET payload_json = ?", (canon(p),)))
    case("payload_json stored as BLOB (same bytes)", r, "ACCEPTED")

    r = fresh(); g, p = row(r)
    sql(r, (f"DROP TABLE {T}",), (f"CREATE TABLE {T} (singleton INTEGER, generation INTEGER, payload_json TEXT)",),
        (f"INSERT INTO {T} VALUES (1, ?, NULL)", (g,)))
    case("payload_json NULL (rebuilt table)", r, "REFUSED")

    r = fresh(); g, p = row(r)
    sql(r, (f"DROP TABLE {T}",), (f"CREATE TABLE {T} (singleton INTEGER, generation INTEGER, payload_json TEXT)",),
        (f"INSERT INTO {T} VALUES (1, ?, ?)", (g, json.dumps(p))), (f"INSERT INTO {T} VALUES (2, 999, 'junk')",))
    case("extra singleton=2 junk row (rebuilt table)", r, "ACCEPTED")

    r = fresh(); g, p = row(r)
    sql(r, (f"UPDATE {T} SET payload_json = ?", (json.dumps(seal({**p, "extra": "x"})),)))
    case("resealed row with an extra field (forger)", r, "ACCEPTED")

    r = fresh(); g, p = row(r)
    q = dict(p); q["base"] = {k: v for k, v in p["base"].items() if k != "journal_record_digest"}
    sql(r, (f"UPDATE {T} SET payload_json = ?", (json.dumps(seal(q)),)))
    case("resealed row without journal_record_digest", r, "REFUSED")

    r = fresh(); g, p = row(r)
    q = dict(p); q.pop("tenant")
    sql(r, (f"UPDATE {T} SET payload_json = ?", (json.dumps(seal(q)),)))
    case("resealed row without tenant", r, "REFUSED")

    r = fresh(); g, p = row(r)
    sql(r, (f"DROP TABLE {T}",))
    case("DROP TABLE on a #821-created store (no legacy file)", r, "REFUSED")

    r = fresh(); g, p = row(r)
    sql(r, (f"DROP TABLE {T}",), (f"CREATE VIEW {T} AS SELECT 1 AS singleton, {g} AS generation, 'x' AS payload_json",))
    case("table replaced by a VIEW", r, "REFUSED")

    r = fresh(); g, p = row(r)
    sql(r, (f"DROP TABLE {T}",))
    (r / "configuration-binding.json").write_text(json.dumps(legacy_from_row(p)))
    case("DOWNGRADE: drop table + forge legacy file from row content", r, "ACCEPTED")

    r = fresh(); g, p = row(r)
    (r / "configuration-binding.json").write_text("{garbage")
    case("valid row + garbage legacy file", r, "ACCEPTED")

    r = migrated(); g, p = row(r)
    sql(r, (f"DROP TABLE {T}",))
    case("migrated store: DROP TABLE (legacy file lags)", r, "REFUSED")

    r = C.tmp() / "s"; shutil.copytree(LEGACY, r)
    sql(r, (f"CREATE TABLE {T} (singleton INTEGER PRIMARY KEY CHECK (singleton = 1), generation INTEGER NOT NULL, payload_json TEXT NOT NULL)",),
        (f"INSERT INTO {T} VALUES (1, 3, '{{not json')",))
    case("legacy store (file verifies) + corrupt injected row: no fallback", r, "REFUSED", tenant="tenant:821-legacy", scope="project:821-legacy")

    r = C.tmp() / "s"; shutil.copytree(LEGACY, r)
    sql(r, (f"CREATE TABLE {T} (singleton INTEGER PRIMARY KEY CHECK (singleton = 1), generation INTEGER NOT NULL, payload_json TEXT NOT NULL)",))
    case("legacy store + empty binding table (file verifies)", r, "ACCEPTED", tenant="tenant:821-legacy", scope="project:821-legacy")

    r = fresh(); g, p = row(r)
    sql(r, (f"DELETE FROM {T}",))
    (r / "configuration-binding.json").write_text(json.dumps(legacy_from_row(p)))
    case("DOWNGRADE: delete row + forge legacy file (table kept)", r, "ACCEPTED")

    # mutation attempts on a living handle: does publish() trust an unsealed previous row?
    r = fresh(); g, p = row(r)
    m = C.open_mem(r)
    sql(r, (f"UPDATE {T} SET payload_json = ?", (json.dumps({"plan_digest": p["plan_digest"]}),)))
    try:
        m.remember("memory:y", "Lunch is at noon.")
        live = "publish accepted an unsealed/garbage previous row and overwrote it"
    except Exception as e:  # noqa
        live = f"publish refused: {type(e).__name__}: {e}"
    m.close()
    print(f"{'live handle, previous row replaced by {plan_digest} only':62s} {live}")
    case("  -> reopen after that", r, "ACCEPTED")


if __name__ == "__main__":
    main()
