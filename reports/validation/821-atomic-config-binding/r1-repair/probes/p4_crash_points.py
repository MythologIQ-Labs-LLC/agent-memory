"""Kill a real child (os._exit, like SIGKILL: no cleanup) at every step of the repaired
GenerationWitness.record, alone and while a second writer A holds its rename (barrier). Then a fresh
process must reopen the store; the witness must be complete and never lead the database.

usage: p4_crash_points.py <reference-dir>
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

REF = sys.argv[1]
PY = sys.executable

CHILD = textwrap.dedent(r"""
import os, sys, time
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import sqlite_runtime as sr
root, role, point, barrier = sys.argv[2:6]
W = "generation-witness.json"
m = AgentMemory.open(root, tenant="t:p4", actor_id="agent:" + role, scope="p:p4", purpose="p4")
ro, rfd, rfs, rrep = os.open, os.fdopen, os.fsync, os.replace
state = {"fd": None, "fsyncs": 0}
def is_tmp(p):
    n = os.path.basename(os.fspath(p)); return n.startswith("." + W) and n.endswith(".tmp")
def o(path, flags, *a, **k):
    fd = ro(path, flags, *a, **k)
    if is_tmp(path):
        state["fd"] = fd
        if point == "after_excl_open": os._exit(77)
    return fd
class H:
    def __init__(s, h): s.h = h
    def __enter__(s): return s
    def __exit__(s, *e): return s.h.__exit__(*e)
    def write(s, b):
        if point == "mid_write":
            s.h.write(b[: len(b) // 2]); s.h.flush(); os._exit(77)
        r = s.h.write(b)
        if point == "after_write_unflushed": os._exit(77)
        return r
    def flush(s): return s.h.flush()
    def fileno(s): return s.h.fileno()
def fd_(fd, *a, **k):
    return H(rfd(fd, *a, **k)) if fd == state["fd"] else rfd(fd, *a, **k)
def fs(fd):
    r = rfs(fd)
    if fd == state["fd"] and point == "after_file_fsync": os._exit(77)
    return r
def rep(src, dst, *a, **k):
    if os.path.basename(os.fspath(dst)) == W:
        if role == "A":
            open(os.path.join(barrier, "a-holding"), "w").close()
            t = time.monotonic() + 60
            while not os.path.exists(os.path.join(barrier, "b-done")):
                if time.monotonic() > t: raise SystemExit("barrier timeout")
                time.sleep(0.01)
        r = rrep(src, dst, *a, **k)
        if point == "after_rename": os._exit(77)
        return r
    return rrep(src, dst, *a, **k)
sr.os.open, sr.os.fdopen, sr.os.fsync, sr.os.replace = o, fd_, fs, rep
m.remember("memory:" + role, "Writer %s fact." % role)
m.close()
if point == "after_dir_fsync": os._exit(77)
""")

OPEN = textwrap.dedent(r"""
import sys
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
m = AgentMemory.open(sys.argv[2], tenant="t:p4", actor_id="agent:r", scope="p:p4", purpose="p4")
print(len(m.recall("Writer fact")["returned"]))
m.close()
""")


def seed(root):
    subprocess.run([PY, "-c", OPEN, REF, str(root)], check=True, capture_output=True)


def inspect(root):
    raw = (root / "generation-witness.json").read_bytes()
    c = sqlite3.connect(f"file:{root / 'agent-memory.sqlite3'}?mode=ro", uri=True)
    gen = c.execute("SELECT json_extract(payload_json,'$.generation') FROM runtime_state WHERE singleton=1").fetchone()[0]
    c.close()
    try:
        w = json.loads(raw)["generation"]
    except Exception:
        w = f"UNPARSEABLE {raw[:40]!r}"
    return w, gen


POINTS = ["after_excl_open", "mid_write", "after_write_unflushed", "after_file_fsync", "after_rename", "after_dir_fsync"]
bad = 0
for mode in ("alone", "B-beside-held-A"):
    for point in POINTS:
        with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(__file__))) as d:
            root = Path(d) / "store"
            barrier = Path(d) / "barrier"
            barrier.mkdir()
            seed(root)
            a = None
            if mode != "alone":
                a = subprocess.Popen([PY, "-c", CHILD, REF, str(root), "A", "none", str(barrier)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                t = time.monotonic() + 60
                while not (barrier / "a-holding").exists() and time.monotonic() < t and a.poll() is None:
                    time.sleep(0.01)
            b = subprocess.run([PY, "-c", CHILD, REF, str(root), "B", point, str(barrier)],
                               capture_output=True, text=True, timeout=120)
            (barrier / "b-done").touch()
            if a is not None:
                a.communicate(timeout=120)
            w, gen = inspect(root)
            reopen = subprocess.run([PY, "-c", OPEN, REF, str(root)], capture_output=True, text=True)
            orphans = [p.name for p in root.iterdir() if p.name.startswith(".generation-witness")]
            ok = isinstance(w, int) and w <= gen and reopen.returncode == 0
            bad += not ok
            print(f"{mode:16s} {point:22s} B_rc={b.returncode:<3d} A_rc={a.returncode if a else '-'!s:3s} "
                  f"witness={w} db={gen} reopen_rc={reopen.returncode} recalled={reopen.stdout.strip() or reopen.stderr.strip()[-150:]} "
                  f"orphans={len(orphans)} {'OK' if ok else '<-- PROBLEM'}")
print("PROBLEMS:", bad)
