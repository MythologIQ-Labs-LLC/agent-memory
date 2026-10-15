"""P1: kill a real child process (os._exit) at every boundary of one generation, across phases.

Invariant checked: after any kill, either the state generation is bound by a row of the same
generation, or (no row) by a legacy file of the same generation; and a fresh reopen recovers
exactly the committed generation. Create-before-first-commit is the documented exception.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
LEGACY = REF / "fixtures" / "821-legacy-stores" / "coherent"

CHILD = textwrap.dedent(r"""
import os, sys
sys.path.insert(0, sys.argv[1])
from contextlib import contextmanager
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import sqlite_runtime as R, configured_restart as CR, restart_runtime as RR
from agentmem_ref.state import sqlite_substrate as S
root, phase, point, tenant, scope = sys.argv[2:7]
X = 77
def after(cls, name):
    orig = getattr(cls, name)
    def hook(*a, **k):
        orig(*a, **k); os._exit(X)
    setattr(cls, name, hook)
def before(cls, name):
    def hook(*a, **k):
        os._exit(X)
    setattr(cls, name, hook)
def install():
    if point == "after_state": after(S.SQLiteTemporalGraph, "write_runtime_state")
    elif point == "after_journal": after(S.SQLiteTemporalGraph, "append_runtime_journal")
    elif point == "binder_entry":
        if hasattr(R, "SQLiteConfigBindingStore"): before(R.SQLiteConfigBindingStore, "publish")
        else: return "n/a"
    elif point == "after_row":
        if hasattr(S.SQLiteTemporalGraph, "write_runtime_configuration_binding"): after(S.SQLiteTemporalGraph, "write_runtime_configuration_binding")
        else: return "n/a"
    elif point == "before_commit": before(RR.CheckpointableGovernedMemoryAdapter, "mark_governance_published")
    elif point == "post_commit":
        orig = S.SQLiteTemporalGraph.transaction
        @contextmanager
        def hook(self):
            with orig(self):
                yield
            os._exit(X)
        S.SQLiteTemporalGraph.transaction = hook
    elif point == "in_published": before(R.SQLiteRestartSafeRuntime, "_published")
    elif point == "owner_callback":
        if hasattr(R, "checkpoint_evidence"):
            def hook(*a, **k): os._exit(X)
            R.checkpoint_evidence = hook
        else:
            before(CR.ConfigBindingStore, "checkpoint")
    elif point == "mid_file":
        orig = CR._atomic_json_write
        def hook(path, value):
            with path.with_name(f".{path.name}.tmp").open("wb") as h:
                h.write(CR._canonical_bytes(value)); h.flush(); os.fsync(h.fileno())
            os._exit(X)
        CR._atomic_json_write = hook
    return "ok"
if phase == "create":
    if install() == "n/a": print("n/a"); sys.exit(0)
m = AgentMemory.open(root, tenant=tenant, actor_id="agent:a", scope=scope, purpose="rev")
if phase != "create":
    if install() == "n/a": print("n/a"); sys.exit(0)
    d = m.runtime.durable_runtime
    if phase in ("remember", "migrate"): m.remember("memory:new", "Lunch is at noon.")
    elif phase == "recall": m.recall("deploy window")
    elif phase == "snapshot": d.persist_visibility_snapshot("op:rev", {"operation": {"required_projection_ids": []}})
    elif phase == "forget": m.forget("memory:x")
    elif phase == "direct_base": d.base.checkpoint()
if point == "post_op": os._exit(X)
m.close()
print("completed")
""")

POINTS = ["after_state", "after_journal", "binder_entry", "after_row", "before_commit", "post_commit",
          "in_published", "owner_callback", "mid_file", "post_op"]
PHASES = ["create", "remember", "recall", "snapshot", "forget", "direct_base", "migrate"]


def seed(root: Path, phase: str):
    if phase == "migrate":
        shutil.copytree(LEGACY, root)
        return "tenant:821-legacy", "project:821-legacy"
    if phase != "create":
        m = C.open_mem(root)
        m.remember("memory:x", "The deploy window is Thursday.")
        m.close()
    return C.TENANT, C.SCOPE


def main():
    import os
    bad = 0
    print(f"row protocol present: {C.has_row_protocol()}")
    for phase in PHASES:
        for point in POINTS:
            root = C.tmp() / "s"
            tenant, scope = seed(root, phase)
            before = C.inspect(root)
            done = subprocess.run([sys.executable, "-c", CHILD, str(REF), str(root), phase, point, tenant, scope],
                                  capture_output=True, text=True, timeout=180)
            if done.stdout.strip() == "n/a":
                continue
            killed = done.returncode == 77
            after = C.inspect(root)
            st, row, fg = after["state_gen"], after["row_gen"], after["file_gen"]
            if st is None:
                coherent = "no-state"
            elif row is not None:
                coherent = "row==state" if (row == st and after["row_payload_gen"] == st) else f"SPLIT row={row} state={st}"
            else:
                coherent = "file==state" if fg == st else f"SPLIT file={fg} state={st}"
            reopened = C.try_open(root, tenant=tenant, scope=scope)
            ok_reopen = reopened.startswith(f"OK gen={st}")
            flag = ""
            if coherent.startswith("SPLIT") or (st is not None and not ok_reopen):
                flag = "  <-- VIOLATION"
                bad += 1
            if done.returncode not in (0, 77):
                flag += f"  child rc={done.returncode} {done.stderr[-300:]!r}"
            print(f"{phase:12s} {point:15s} killed={killed!s:5s} before_gen={before['state_gen']} after: state={st} "
                  f"journal={after['journal_gen']} row={row} file={fg} [{coherent}] reopen: {reopened}{flag}")
    print(f"VIOLATIONS: {bad}")


if __name__ == "__main__":
    main()
