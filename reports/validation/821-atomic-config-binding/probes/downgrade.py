#!/usr/bin/env python3
"""#821 M21 / A10: a pre-#821 runtime opening stores a #821 runtime wrote.

Usage: ``python3 downgrade.py <candidate>/reference <pre-821>/reference``

Case ``new``: a store created and written only by the candidate (row-bound, no file).
Case ``migrated``: the byte-frozen coherent legacy store, opened by the candidate, which publishes
one generation (the row); the legacy file still binds the generation before.
Case ``unmigrated``: the coherent legacy store opened and closed by the candidate without any
generation: still a legacy store, which the pre-#821 runtime must still open.
Each child prints one JSON line; the old runtime must fail closed on ``new`` and ``migrated``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

TENANT, SCOPE = "tenant:821-legacy", "project:821-legacy"

WRITE = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, sys.argv[1])
    from agentmem_ref import AgentMemory
    m = AgentMemory.open(sys.argv[2], tenant=%r, actor_id="agent:legacy", scope=%r, purpose="821")
    if sys.argv[3] == "write":
        m.remember("memory:deploy", "The deploy window is Thursday.")
    m.close()
    """
) % (TENANT, SCOPE)

OPEN = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    from agentmem_ref import AgentMemory
    try:
        m = AgentMemory.open(sys.argv[2], tenant=%r, actor_id="agent:legacy", scope=%r, purpose="821")
    except Exception as exc:
        print(json.dumps({"outcome": "failed_closed", "error": f"{type(exc).__name__}: {exc}"}))
    else:
        print(json.dumps({"outcome": "recovered", "generation": m.runtime.durable_runtime.recovery_evidence.base_generation}))
        m.close()
    """
) % (TENANT, SCOPE)


def run(script: str, *args: str) -> str:
    done = subprocess.run([sys.executable, "-c", script, *args], capture_output=True, text=True, timeout=120)
    if done.returncode:
        raise SystemExit(done.stderr)
    return done.stdout.strip()


def main() -> int:
    candidate, old = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    fixture = candidate / "fixtures" / "821-legacy-stores" / "coherent"
    results = {}
    with tempfile.TemporaryDirectory() as folder:
        new = Path(folder) / "new"
        run(WRITE, str(candidate), str(new), "write")
        results["new"] = json.loads(run(OPEN, str(old), str(new)))
        migrated = Path(folder) / "migrated"
        shutil.copytree(fixture, migrated)
        run(WRITE, str(candidate), str(migrated), "write")
        results["migrated"] = json.loads(run(OPEN, str(old), str(migrated)))
        unmigrated = Path(folder) / "unmigrated"
        shutil.copytree(fixture, unmigrated)
        run(WRITE, str(candidate), str(unmigrated), "open-only")
        results["unmigrated"] = json.loads(run(OPEN, str(old), str(unmigrated)))
    ok = (results["new"]["outcome"] == "failed_closed" and results["migrated"]["outcome"] == "failed_closed"
          and results["unmigrated"]["outcome"] == "recovered")
    print(json.dumps({"results": results, "a10_holds": ok}, indent=1, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
