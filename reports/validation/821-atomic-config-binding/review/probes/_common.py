"""Shared helpers for the #821 adversarial probes. Each probe: python3 pN.py <reference dir>."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

TENANT = "tenant:rev"
SCOPE = "project:rev"
TABLE = "runtime_configuration_binding"


def ref() -> Path:
    path = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(path))
    return path


def db(root) -> Path:
    return Path(root) / "agent-memory.sqlite3"


def inspect(root) -> dict:
    root = Path(root)
    out = {"db": db(root).exists(), "file_gen": None, "state_gen": None, "journal_gen": None, "row_gen": None,
           "row_payload_gen": None, "table": False}
    f = root / "configuration-binding.json"
    if f.exists():
        try:
            out["file_gen"] = json.loads(f.read_text())["base"]["generation"]
        except Exception as e:  # noqa
            out["file_gen"] = f"unreadable:{e}"
    if not out["db"]:
        return out
    c = sqlite3.connect(db(root))
    try:
        try:
            r = c.execute("SELECT json_extract(payload_json,'$.generation') FROM runtime_state WHERE singleton=1").fetchone()
            out["state_gen"] = None if r is None else r[0]
            r = c.execute("SELECT max(generation) FROM runtime_journal").fetchone()
            out["journal_gen"] = r[0]
        except sqlite3.DatabaseError as e:
            out["state_gen"] = f"err:{e}"
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone():
            out["table"] = True
            r = c.execute(f"SELECT generation, json_extract(payload_json,'$.base.generation') FROM {TABLE}").fetchone()
            if r:
                out["row_gen"], out["row_payload_gen"] = r
    finally:
        c.close()
    return out


def tables(root, exclude=()) -> dict:
    c = sqlite3.connect(db(root))
    try:
        names = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {n: sorted(map(tuple, c.execute(f"SELECT * FROM {n}").fetchall()), key=repr) for n in names if n not in exclude}
    finally:
        c.close()


def tables_digest(root, exclude=()) -> str:
    return hashlib.sha256(repr(tables(root, exclude)).encode()).hexdigest()[:16]


def open_mem(root, tenant=TENANT, scope=SCOPE, actor="agent:a"):
    from agentmem_ref import AgentMemory
    return AgentMemory.open(root, tenant=tenant, actor_id=actor, scope=scope, purpose="rev")


def try_open(root, **kw) -> str:
    """Reopen in a fresh child process; return 'OK gen=..' or the refusal."""
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]);\n"
        "from agentmem_ref import AgentMemory\n"
        "try:\n"
        "    m = AgentMemory.open(sys.argv[2], tenant=sys.argv[3], actor_id='agent:r', scope=sys.argv[4], purpose='rev')\n"
        "    d = m.runtime.durable_runtime\n"
        "    print('OK gen=%s scheme=%s' % (d.base.recovery_evidence.generation, getattr(d, 'binding_scheme', '-')))\n"
        "    m.close()\n"
        "except Exception as e:\n"
        "    print('REFUSED %s: %s' % (type(e).__name__, e))\n"
    )
    done = subprocess.run([sys.executable, "-c", code, sys.argv[1], str(root), kw.get("tenant", TENANT), kw.get("scope", SCOPE)],
                          capture_output=True, text=True, timeout=180)
    return (done.stdout.strip() or done.stderr.strip()[-400:])


def has_row_protocol() -> bool:
    from agentmem_ref.state import sqlite_substrate as s
    return hasattr(s.SQLiteTemporalGraph, "write_runtime_configuration_binding")


def tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="rev821-"))
