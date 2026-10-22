"""P10 (amendment 1): kill a real child process at every point around the generation witness:
inside GenerationWitness.record (temp written / renamed, before the directory fsync), between
COMMIT and the witness write, at create (witness gen 0 before the database exists, and the gen-1
witness), and on a legacy store's first migrating generation. Invariant: the witness never leads
the database, and every store that committed a generation reopens to exactly that generation."""
from __future__ import annotations

import json
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
from agentmem_ref.runtime import sqlite_runtime as R
from agentmem_ref.state import sqlite_substrate as S
root, phase, point, nth, tenant, scope = sys.argv[2:8]
nth = int(nth); X = 77
calls = {"n": 0}
W = R.GenerationWitness
orig_record = W.record
def record(self, generation, digest):
    calls["n"] += 1
    if calls["n"] != nth:
        return orig_record(self, generation, digest)
    if point == "w_before":
        os._exit(X)
    payload = R._canonical_bytes({"schema": R.GENERATION_WITNESS_SCHEMA, "generation": int(generation), "journal_record_digest": digest}) + b"\n"
    tmp = self.path.with_name(f".{self.path.name}.tmp")
    with tmp.open("wb") as h:
        h.write(payload); h.flush(); os.fsync(h.fileno())
    if point == "w_tmp":
        os._exit(X)
    os.replace(tmp, self.path)
    if point == "w_renamed":
        os._exit(X)
    orig_record(self, generation, digest)
    if point == "w_after":
        os._exit(X)
W.record = record
if point == "post_commit":
    orig = S.SQLiteTemporalGraph.transaction
    @contextmanager
    def hook(self):
        with orig(self):
            yield
        if calls.get("armed"):
            os._exit(X)
    S.SQLiteTemporalGraph.transaction = hook
    if phase == "create": calls["armed"] = True
m = AgentMemory.open(root, tenant=tenant, actor_id="agent:a", scope=scope, purpose="rev")
calls["n"] = 0 if phase != "create" else calls["n"]
if phase != "create":
    calls["armed"] = True
    if phase in ("remember", "migrate"): m.remember("memory:new", "Lunch is at noon.")
    elif phase == "recall": m.recall("deploy window")
    elif phase == "snapshot": m.runtime.durable_runtime.persist_visibility_snapshot("op:w", {"operation": {"required_projection_ids": []}})
m.close()
print("completed")
""")


def witness(root):
    p = Path(root) / "generation-witness.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())["generation"]
    except Exception as e:  # noqa
        return f"bad:{e}"


def seed(root, phase):
    if phase == "migrate":
        shutil.copytree(LEGACY, root)
        return "tenant:821-legacy", "project:821-legacy"
    if phase != "create":
        m = C.open_mem(root); m.remember("memory:x", "The deploy window is Thursday."); m.close()
    return C.TENANT, C.SCOPE


CASES = [("create", p, n) for p in ("w_before", "w_tmp", "w_renamed", "w_after") for n in (1, 2)] + [("create", "post_commit", 99)]
CASES += [(ph, p, 1) for ph in ("remember", "recall", "snapshot", "migrate") for p in ("post_commit", "w_before", "w_tmp", "w_renamed", "w_after")]


def main():
    bad = 0
    for phase, point, nth in CASES:
        root = C.tmp() / "s"
        tenant, scope = seed(root, phase)
        done = subprocess.run([sys.executable, "-c", CHILD, str(REF), str(root), phase, point, str(nth), tenant, scope],
                              capture_output=True, text=True, timeout=180)
        i = C.inspect(root)
        w = witness(root)
        st = i["state_gen"]
        leads = isinstance(w, int) and (st is None or w > st)
        reopen = C.try_open(root, tenant=tenant, scope=scope)
        problems = []
        if leads:
            problems.append("WITNESS LEADS DB")
        if st is not None and st >= 1 and not reopen.startswith(f"OK gen={st}"):
            problems.append("committed store not recoverable")
        if done.returncode not in (0, 77):
            problems.append(f"child rc={done.returncode}: {done.stderr[-300:]}")
        if problems:
            bad += 1
        tmp_left = (Path(root) / ".generation-witness.json.tmp").exists()
        print(f"{phase:9s} {point:12s} call#{nth:<2d} rc={done.returncode:<3d} db={i['db']!s:5s} state={st} row={i['row_gen']} "
              f"file={i['file_gen']} witness={w} tmp_left={tmp_left} reopen: {reopen[:120]}"
              + ("  <-- " + "; ".join(problems) if problems else ""))
    print(f"PROBLEMS: {bad}")


if __name__ == "__main__":
    main()
