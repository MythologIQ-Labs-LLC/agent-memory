"""P9: (a) base runtime driven directly with a visibility snapshot the plan does not allow;
(b) an injected failure during the first (migrating) generation of a legacy store;
(c) two legacy handles in one process; (d) concurrent create race from two processes;
(e) a bare SQLiteRestartSafeRuntime (no binder) publishing on a config-bound store."""
from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
LEGACY = REF / "fixtures" / "821-legacy-stores" / "coherent"
LT, LS = "tenant:821-legacy", "project:821-legacy"
from agentmem_ref.state import sqlite_substrate as S  # noqa: E402
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict  # noqa: E402


def a_base_driven_bad_snapshot():
    root = C.tmp() / "s"
    m = C.open_mem(root)
    m.remember("memory:x", "seed")
    d = m.runtime.durable_runtime
    try:
        d.base.persist_visibility_snapshot("op:bad", {"operation": {"required_projection_ids": ["no-such-projection"]}})
        r = "committed"
    except Exception as e:  # noqa
        r = f"{type(e).__name__}: {e}"
    m.close()
    print("(a) base-driven snapshot outside the plan:", r, "| reopen:", C.try_open(root)[:140], "|", C.inspect(root))


def b_legacy_migration_failure():
    if not LEGACY.exists() or not C.has_row_protocol():
        print("(b) n/a"); return
    root = C.tmp() / "s"; shutil.copytree(LEGACY, root)
    m = C.open_mem(root, tenant=LT, scope=LS)
    orig = S.SQLiteTemporalGraph.write_runtime_configuration_binding

    def boom(self, *a, **k):
        orig(self, *a, **k)
        raise KeyboardInterrupt
    with mock.patch.object(S.SQLiteTemporalGraph, "write_runtime_configuration_binding", boom):
        try:
            m.recall("deploy")
        except KeyboardInterrupt:
            pass
    i1 = C.inspect(root)
    m.recall("deploy")
    i2 = C.inspect(root)
    m.close()
    print("(b) legacy first generation interrupted:", i1, "| then:", i2, "| reopen:", C.try_open(root, tenant=LT, scope=LS))


def c_two_legacy_handles():
    if not LEGACY.exists():
        print("(c) n/a"); return
    root = C.tmp() / "s"; shutil.copytree(LEGACY, root)
    h1 = C.open_mem(root, tenant=LT, scope=LS, actor="agent:1")
    h2 = C.open_mem(root, tenant=LT, scope=LS, actor="agent:2")
    h1.recall("deploy")
    snap = C.tables_digest(root)
    try:
        h2.recall("deploy"); r = "h2 published"
    except RuntimeCheckpointConflict as e:
        r = f"h2 conflict: {e}"
    h1.close(); h2.close()
    print("(c) two legacy handles:", r, "| unchanged by h2:", C.tables_digest(root) == snap, "|", C.inspect(root),
          "| reopen:", C.try_open(root, tenant=LT, scope=LS))


RACE = textwrap.dedent(r"""
import sys, time
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
t0 = float(sys.argv[3])
while time.time() < t0: pass
try:
    m = AgentMemory.open(sys.argv[2], tenant="tenant:rev", actor_id="agent:race", scope="project:rev", purpose="rev")
    m.remember("memory:r", "race " + sys.argv[4]); m.close(); print("OK")
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:120])
""")


def d_create_race():
    import time
    outcomes = {}
    for trial in range(6):
        root = C.tmp() / "s"
        t0 = time.time() + 1.5
        ps = [subprocess.Popen([sys.executable, "-c", RACE, str(REF), str(root), str(t0), str(k)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for k in range(3)]
        res = [p.communicate(timeout=120)[0].strip() or "crash" for p in ps]
        final = C.try_open(root)
        key = (tuple(sorted(res)), final[:90])
        outcomes[key] = outcomes.get(key, 0) + 1
    for (res, final), n in outcomes.items():
        print(f"(d) create race x{n}: children={list(res)} | reopen: {final}")


def e_bare_base_runtime():
    from agentmem_ref.runtime.sqlite_runtime import SQLiteRestartSafeRuntime
    from agentmem_ref.runtime.configured_restart import _profile_from_plan
    root = C.tmp() / "s"
    m = C.open_mem(root); m.remember("memory:x", "seed")
    plan = m.runtime.durable_runtime.plan
    m.close()
    bare = SQLiteRestartSafeRuntime.recover(root, profile=_profile_from_plan(plan))
    bare.checkpoint(); bare.close()
    print("(e) bare base runtime published on a config-bound store:", C.inspect(root), "| reopen:", C.try_open(root)[:140])


if __name__ == "__main__":
    a_base_driven_bad_snapshot()
    b_legacy_migration_failure()
    c_two_legacy_handles()
    d_create_race()
    e_bare_base_runtime()
