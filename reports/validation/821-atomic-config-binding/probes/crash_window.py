#!/usr/bin/env python3
"""#821 crash-window reproduction: kill a real process at each publication boundary.

Usage: ``python3 crash_window.py <reference-dir> [--json OUT]``

For every interruption point a child process opens a facade-owned SQLite store, commits one
fact (the "prior coherent generation"), installs one crash hook and attempts a second governed
write. The hook ends the process with ``os._exit(77)``: no ``finally``, no ``close()``, no atexit,
so nothing the process had not already handed to the OS survives. The parent then:

1. reads the durable state through an independent SQLite connection (runtime-state generation,
   journal tail generation, whether the second fact is present, the in-transaction binding row
   if the schema has one) and the configuration-binding file (its bound base generation);
2. reopens the store through the public facade and records the outcome verbatim.

The same script runs unchanged against the frozen #816 head and the #821 candidate: hooks that
name a seam a checkout does not have are reported as ``not_applicable``. Process death models a
crash of the writing process; power-loss durability is argued separately in the README.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

TENANT = "tenant:821"
SCOPE = "project:821"
CRASH = 77

# Each hook is installed in the child just before the second (or, for create_*, the first) write.
HOOKS = {
    # inside the generation's open transaction, after its journal row: nothing is committed yet
    "pre_commit": """
        from agentmem_ref.state import sqlite_substrate as s
        original = s.SQLiteTemporalGraph.append_runtime_journal
        def hook(self, *a, **k):
            original(self, *a, **k)
            os._exit(CRASH)
        s.SQLiteTemporalGraph.append_runtime_journal = hook
    """,
    # immediately after the SQLite COMMIT of the generation returns, before anything else runs
    "post_commit": """
        from contextlib import contextmanager
        from agentmem_ref.state import sqlite_substrate as s
        original = s.SQLiteTemporalGraph.transaction
        @contextmanager
        def hook(self):
            with original(self):
                yield
            os._exit(CRASH)
        s.SQLiteTemporalGraph.transaction = hook
    """,
    # file protocol (#816 and earlier): binding temp file written and fsynced, rename not done
    "mid_bind_file": """
        from agentmem_ref.runtime import configured_restart as c
        def hook(path, value):  # _atomic_json_write up to, not including, its os.replace
            temporary = path.with_name(f".{path.name}.tmp")
            with temporary.open("wb") as handle:
                handle.write(c._canonical_bytes(value) + b"\\n")
                handle.flush()
                os.fsync(handle.fileno())
            os._exit(CRASH)
        c._atomic_json_write = hook
    """,
    # in-transaction protocol (#821): binding row written inside the open generation, before COMMIT
    "mid_bind_row": """
        from agentmem_ref.state import sqlite_substrate as s
        original = getattr(s.SQLiteTemporalGraph, "write_runtime_configuration_binding", None)
        if original is None:
            print("NOT_APPLICABLE"); sys.stdout.flush(); os._exit(0)
        def hook(self, *a, **k):
            original(self, *a, **k)
            os._exit(CRASH)
        s.SQLiteTemporalGraph.write_runtime_configuration_binding = hook
    """,
    # after the whole operation (commit and any binding publication) returned to the caller
    "post_bind": """
        AFTER_WRITE = True
    """,
}

CHILD = textwrap.dedent(
    """
    import os, sys
    sys.path.insert(0, sys.argv[1])
    CRASH = {crash}
    AFTER_WRITE = False
    from agentmem_ref import AgentMemory
    root, phase = sys.argv[2], sys.argv[3]
    if phase == "steady":
        m = AgentMemory.open(root, tenant={tenant!r}, actor_id="agent:a", scope={scope!r}, purpose="821")
        assert m.remember("memory:x", "The deploy window is Thursday.")["committed"]
    {hook}
    if phase == "steady":
        m.remember("memory:y", "Lunch is at noon.")
    else:
        m = AgentMemory.open(root, tenant={tenant!r}, actor_id="agent:a", scope={scope!r}, purpose="821")
    if AFTER_WRITE:
        os._exit(CRASH)
    print("COMPLETED_WITHOUT_CRASH")
    """
)


def _durable_state(root: Path) -> dict:
    db = root / "agent-memory.sqlite3"
    state: dict = {"database_present": db.exists()}
    binding_file = root / "configuration-binding.json"
    state["binding_file_present"] = binding_file.exists()
    if binding_file.exists():
        try:
            state["binding_file_base_generation"] = json.loads(binding_file.read_text())["base"]["generation"]
        except Exception as exc:  # noqa: BLE001 - recorded, not interpreted
            state["binding_file_base_generation"] = f"unreadable: {exc!r}"
    witness = root / "generation-witness.json"
    state["witness_generation"] = json.loads(witness.read_text())["generation"] if witness.exists() else None
    leftovers = sorted(p.name for p in root.iterdir() if p.name.startswith(".configuration-binding"))
    state["binding_temp_files"] = leftovers
    if not db.exists():
        return state
    connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        row = connection.execute(
            "SELECT json_extract(payload_json, '$.generation') FROM runtime_state WHERE singleton = 1"
        ).fetchone() if "runtime_state" in tables else None
        state["runtime_state_generation"] = None if row is None else row[0]
        row = connection.execute("SELECT MAX(generation) FROM runtime_journal").fetchone() if "runtime_journal" in tables else None
        state["journal_tail_generation"] = None if row is None else row[0]
        state["facts"] = connection.execute("SELECT COUNT(*) FROM facts").fetchone()[0] if "facts" in tables else 0
        if "runtime_configuration_binding" in tables:
            row = connection.execute(
                "SELECT generation FROM runtime_configuration_binding WHERE singleton = 1"
            ).fetchone()
            state["binding_row_generation"] = None if row is None else row[0]
        else:
            state["binding_row_generation"] = "no_table"
    finally:
        connection.close()
    return state


def _reopen(reference: Path, root: Path) -> dict:
    script = textwrap.dedent(
        f"""
        import json, sys
        sys.path.insert(0, {str(reference)!r})
        from agentmem_ref import AgentMemory
        try:
            m = AgentMemory.open({str(root)!r}, tenant={TENANT!r}, actor_id="agent:b", scope={SCOPE!r}, purpose="821")
        except Exception as exc:
            print(json.dumps({{"outcome": "failed_closed", "error": type(exc).__name__ + ": " + str(exc)}}))
            raise SystemExit(0)
        recovered = m.runtime.durable_runtime.recovery_evidence
        out = {{
            "outcome": "recovered",
            "base_generation": recovered.base_generation,
            "recovery_posture": recovered.recovery_posture,
            "deploy_returned": len(m.recall("deploy window")["returned"]),
            "lunch_returned": len(m.recall("lunch noon")["returned"]),
        }}
        m.close()
        print(json.dumps(out))
        """
    )
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        return {"outcome": "reopen_process_error", "stderr": done.stderr[-2000:]}
    return json.loads(done.stdout.strip().splitlines()[-1])


def run_point(reference: Path, point: str, phase: str) -> dict:
    hook = textwrap.indent(textwrap.dedent(HOOKS[point]).strip(), "")
    child = CHILD.format(crash=CRASH, tenant=TENANT, scope=SCOPE, hook=hook)
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder) / "store"
        started = time.time()
        done = subprocess.run(
            [sys.executable, "-c", child, str(reference), str(root), phase],
            capture_output=True, text=True, timeout=120,
        )
        record = {
            "point": point,
            "phase": phase,
            "child_exit": done.returncode,
            "crashed": done.returncode == CRASH,
            "child_stdout": done.stdout.strip()[-400:],
            "child_stderr": done.stderr.strip()[-800:],
            "crash_unix_time": round(time.time(), 3),
            "elapsed_s": round(time.time() - started, 3),
        }
        if "NOT_APPLICABLE" in done.stdout:
            record["result"] = "not_applicable"
            return record
        if "COMPLETED_WITHOUT_CRASH" in done.stdout:
            record["hook"] = "never_reached: the seam is not on this checkout's publication path"
        record["durable_state"] = _durable_state(root) if root.exists() else {"database_present": False}
        record["reopen"] = _reopen(reference, root) if root.exists() else {"outcome": "no_store"}
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference")
    parser.add_argument("--json")
    args = parser.parse_args()
    reference = Path(args.reference).resolve()
    head = subprocess.run(["git", "-C", str(reference), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(reference), "status", "--porcelain", "--", "agentmem_ref"],
                           capture_output=True, text=True).stdout.strip()
    results = []
    for phase, points in (("steady", list(HOOKS)), ("create", ["pre_commit", "post_commit", "mid_bind_file", "mid_bind_row"])):
        for point in points:
            results.append(run_point(reference, point, phase))
    report = {"revision": head, "runtime_tree_dirty": bool(dirty), "python": sys.version.split()[0],
              "sqlite": sqlite3.sqlite_version, "results": results}
    for item in results:
        state = item.get("durable_state", {})
        reopen = item.get("reopen", {})
        print(f"{item['phase']:7} {item['point']:14} crashed={item['crashed']!s:5} "
              f"state_gen={state.get('runtime_state_generation')} journal_gen={state.get('journal_tail_generation')} "
              f"file_gen={state.get('binding_file_base_generation', '-')} row_gen={state.get('binding_row_generation', '-')} "
              f"witness={state.get('witness_generation', '-')} "
              f"facts={state.get('facts', '-')} -> {item.get('result') or reopen.get('outcome')} "
              f"{'(hook never reached) ' if item.get('hook') else ''}"
              f"{reopen.get('error', '') or (reopen.get('base_generation'), reopen.get('deploy_returned'), reopen.get('lunch_returned'))}")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"revision {head} runtime_tree_dirty={bool(dirty)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
