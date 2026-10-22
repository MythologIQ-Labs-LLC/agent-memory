"""P4: stale handles, two handles in one process, threads, a second SQLiteTemporalGraph instance,
and two processes writing (and being killed) concurrently on one store."""
from __future__ import annotations

import random
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict  # noqa: E402
from agentmem_ref.state import sqlite_substrate as S  # noqa: E402


def show(name, ok, detail=""):
    print(f"{'HELD ' if ok else 'FAIL '} {name}: {detail}")


def two_handles_one_process():
    root = C.tmp() / "s"
    a = C.open_mem(root, actor="agent:a")
    a.remember("memory:x", "seed")
    b = C.open_mem(root, actor="agent:b")
    b.remember("memory:y", "from b")
    snap = C.tables(root)
    try:
        a.remember("memory:z", "stale a")
        show("stale in-process handle refused", False, "stale handle committed")
    except RuntimeCheckpointConflict as e:
        show("stale in-process handle refused", C.tables(root) == snap, str(e))
    a.close(); b.close()
    i = C.inspect(root)
    show("row==state after two-handle race", i["row_gen"] == i["state_gen"], str(i))
    show("reopen", C.try_open(root).startswith("OK"), C.try_open(root))


def threads_on_one_handle():
    root = C.tmp() / "s"
    m = C.open_mem(root)
    errors = []

    def work(n):
        for k in range(8):
            try:
                m.remember(f"memory:t{n}-{k}", f"thread {n} fact {k}")
                m.recall("fact")
            except Exception as e:  # noqa
                errors.append(repr(e))
    ts = [threading.Thread(target=work, args=(n,)) for n in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    m.close()
    i = C.inspect(root)
    show("4 threads x 8 writes on one handle", not errors and i["row_gen"] == i["state_gen"], f"errors={errors[:2]} {i}")


def other_thread_cannot_write_row_during_generation():
    root = C.tmp() / "s"
    m = C.open_mem(root)
    m.remember("memory:x", "seed")
    substrate = m.runtime.adapter.checkpoint_substrate()
    result = {}
    gate, release = threading.Event(), threading.Event()

    def op():
        gate.set(); release.wait(5)
        return m.runtime.adapter  # noqa

    def intruder():
        gate.wait(5)
        try:
            substrate.write_runtime_configuration_binding(99, {"forged": True})
            result["r"] = "WROTE"
        except Exception as e:  # noqa
            result["r"] = type(e).__name__
        release.set()
    t = threading.Thread(target=intruder); t.start()
    m.runtime.durable_runtime.run_governed_read(op)
    t.join()
    m.close()
    i = C.inspect(root)
    show("other thread during an open generation cannot write the row",
         result.get("r") == "UngovernedDurableWrite" and i["row_gen"] == i["state_gen"], f"{result} {i}")


def second_substrate_instance():
    root = C.tmp() / "s"
    m = C.open_mem(root)
    m.remember("memory:x", "seed")
    other = S.SQLiteTemporalGraph(C.db(root))
    try:
        with other.transaction():
            other.write_runtime_configuration_binding(99, {"forged": True})
        r = "WROTE"
    except Exception as e:  # noqa
        r = type(e).__name__
    show("second SQLiteTemporalGraph instance (no capability) refused", r == "UngovernedDurableWrite", r)
    # a second instance can still self-issue a capability: the storage layer stays privileged (#816)
    cap = other.require_runtime_generations()
    try:
        with other.transaction(), other.generation_opened(cap):
            other.write_runtime_configuration_binding(99, {"forged": True})
        r = "WROTE"
    except Exception as e:  # noqa
        r = type(e).__name__
    other.close()
    m.close()
    res = C.try_open(root)
    show("self-issued capability on a 2nd instance writes a forged row -> recovery refuses", res.startswith("REFUSED"),
         f"write={r}; reopen={res[:120]}")


WRITER = textwrap.dedent(r"""
import os, sys, random
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict, RuntimeRecoveryError
root, seed = sys.argv[2], int(sys.argv[3])
rng = random.Random(seed)
for attempt in range(6):
    try:
        m = AgentMemory.open(root, tenant=sys.argv[4], actor_id="agent:w%d" % seed, scope=sys.argv[5], purpose="rev")
    except Exception as e:
        print("OPENFAIL", type(e).__name__, e); sys.exit(3)
    try:
        for k in range(rng.randint(1, 4)):
            m.remember("memory:w%d-%d-%d" % (seed, attempt, k), "writer %d fact %d %d" % (seed, attempt, k))
            if rng.random() < 0.25:
                os._exit(77)
    except RuntimeCheckpointConflict:
        pass
    m.close()
""")


def two_processes_with_kills():
    root = C.tmp() / "s"
    m = C.open_mem(root); m.remember("memory:x", "seed"); m.close()
    rng = random.Random(821)
    openfail = []
    for rnd in range(6):
        procs = [subprocess.Popen([sys.executable, "-c", WRITER, str(REF), str(root), str(rng.randint(0, 10**6)), C.TENANT, C.SCOPE],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(3)]
        for p in procs:
            out, err = p.communicate(timeout=300)
            if p.returncode == 3 or "Traceback" in err:
                openfail.append((p.returncode, out.strip()[-200:], err.strip()[-300:]))
        i = C.inspect(root)
        if i["row_gen"] != i["state_gen"]:
            openfail.append(("SPLIT", i))
    res = C.try_open(root)
    i = C.inspect(root)
    show("3 concurrent writer processes x 6 rounds with random os._exit", not openfail and res.startswith("OK"),
         f"final={i} reopen={res[:80]} failures={openfail[:3]}")


def main():
    if not C.has_row_protocol():
        print("(base revision: row-specific checks skipped)")
        two_handles_one_process(); threads_on_one_handle(); two_processes_with_kills()
        return
    two_handles_one_process()
    threads_on_one_handle()
    other_thread_cannot_write_row_during_generation()
    second_substrate_instance()
    two_processes_with_kills()


if __name__ == "__main__":
    main()
