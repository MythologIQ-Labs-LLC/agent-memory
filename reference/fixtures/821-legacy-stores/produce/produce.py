#!/usr/bin/env python3
"""Produce the #821 byte-frozen legacy stores with the frozen #816 runtime.

Usage: ``python3 produce.py <d2fc9782 checkout>/reference <fixture dir>``

``coherent``: open, remember two facts, close. Its binding file binds the last generation.
``stranded``: open, remember one fact, then a second remember whose process is killed
immediately after the SQLite COMMIT (the #821 window): generation N+1 committed, the binding
file still binds N. The killed process leaves its WAL; a plain ``sqlite3`` connection (no Agent
Memory code) is opened and closed afterwards so the commit is checkpointed into the database
file, which changes no logical row.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

TENANT = "tenant:821-legacy"
SCOPE = "project:821-legacy"

WRITER = textwrap.dedent(
    """
    import os, sys
    sys.path.insert(0, sys.argv[1])
    from contextlib import contextmanager
    from agentmem_ref import AgentMemory
    from agentmem_ref.state import sqlite_substrate as s
    m = AgentMemory.open(sys.argv[2], tenant=%r, actor_id="agent:legacy", scope=%r, purpose="821 legacy fixture")
    assert m.remember("memory:deploy", "The deploy window is Thursday.")["committed"]
    if sys.argv[3] == "stranded":
        original = s.SQLiteTemporalGraph.transaction
        @contextmanager
        def crash_after_commit(self):
            with original(self):
                yield
            os._exit(77)
        s.SQLiteTemporalGraph.transaction = crash_after_commit
    assert m.remember("memory:lunch", "Lunch is at noon.")["committed"]
    m.close()
    """
) % (TENANT, SCOPE)


def main() -> int:
    reference, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    revision = subprocess.run(["git", "-C", str(reference), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    stores = {}
    for name, expected_exit in (("coherent", 0), ("stranded", 77)):
        root = out / name
        if root.exists():
            shutil.rmtree(root)
        done = subprocess.run([sys.executable, "-c", WRITER, str(reference), str(root), name], capture_output=True, text=True)
        if done.returncode != expected_exit:
            raise SystemExit(f"{name}: exit {done.returncode}: {done.stderr}")
        plain = sqlite3.connect(root / "agent-memory.sqlite3")  # checkpoint the WAL, nothing else
        generation = plain.execute("SELECT json_extract(payload_json, '$.generation') FROM runtime_state").fetchone()[0]
        plain.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        plain.close()
        for leftover in root.glob("agent-memory.sqlite3-*"):
            raise SystemExit(f"{name}: unexpected leftover {leftover.name}")
        bound = json.loads((root / "configuration-binding.json").read_text())["base"]["generation"]
        stores[name] = {
            "state_generation": generation,
            "binding_file_generation": bound,
            "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir())},
        }
    manifest = {
        "owning_issue": 821,
        "status": "frozen",
        "tenant": TENANT,
        "scope": SCOPE,
        "produced_by": {"revision": revision, "python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
                        "how": "python3 produce/produce.py <checkout>/reference <fixture dir>"},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "note": "Consumers copy a store before opening it (a generation may be published).",
        "stores": stores,
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps(stores, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
