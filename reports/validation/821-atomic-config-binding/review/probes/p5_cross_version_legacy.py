"""P5: cross-revision behaviour and the frozen legacy stores.

usage: p5_cross_version_legacy.py <writer reference> <reader reference>
Stores are written by the writer revision (in a child process) and opened by the reader revision
(in another child process). Also exercises the #821 and #809 frozen fixtures with the writer.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

WRITER = Path(sys.argv[1]).resolve()
READER = Path(sys.argv[2]).resolve()
FIX821 = WRITER / "fixtures" / "821-legacy-stores"
FIX809 = WRITER / "fixtures" / "809-legacy-stores"

OPEN = textwrap.dedent(r"""
import sys, json
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
root, tenant, scope, action = sys.argv[2:6]
try:
    m = AgentMemory.open(root, tenant=tenant, actor_id="agent:p5", scope=scope, purpose="rev")
except Exception as e:
    print("REFUSED %s: %s" % (type(e).__name__, e)); sys.exit(0)
d = m.runtime.durable_runtime
info = "OK gen=%s scheme=%s" % (d.base.recovery_evidence.generation, getattr(d, "binding_scheme", "-"))
if action == "write":
    m.remember("memory:p5", "Cross-version fact.")
    info += " -> wrote gen=%s" % d.base.recovery_evidence.generation
elif action == "recall":
    m.recall("anything")
    info += " -> recall gen=%s" % d.base.recovery_evidence.generation
m.close()
print(info)
""")


def run(ref, root, tenant, scope, action="none"):
    out = subprocess.run([sys.executable, "-c", OPEN, str(ref), str(root), tenant, scope, action],
                         capture_output=True, text=True, timeout=180)
    return (out.stdout.strip() or out.stderr.strip()[-300:])


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def files(root: Path) -> dict:
    return {p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file()}


def main():
    sys.path.insert(0, str(WRITER))
    print(f"writer={WRITER.parent.name} reader={READER.parent.name}")
    T, S = C.TENANT, C.SCOPE
    # A10: a store created and advanced by the writer, opened by the reader
    root = C.tmp() / "s"
    print("writer create+write:", run(WRITER, root, T, S, "write"))
    snap = C.tables_digest(root)
    print("reader opens writer store:", run(READER, root, T, S))
    print("reader attempts write:", run(READER, root, T, S, "write"))
    print("  db unchanged by reader:", C.tables_digest(root) == snap, C.inspect(root))
    print("writer reopens:", run(WRITER, root, T, S))

    # legacy coherent fixture: writer migrates it, reader opens
    for name in ("coherent", "stranded"):
        if not (FIX821 / name).exists():
            print(f"fixture 821/{name} not present at writer revision")
            continue
        root = C.tmp() / name
        shutil.copytree(FIX821 / name, root)
        lt, ls = "tenant:821-legacy", "project:821-legacy"
        f0, t0 = files(root), C.tables_digest(root)
        print(f"[821/{name}] writer open only:", run(WRITER, root, lt, ls),
              "| tables unchanged:", C.tables_digest(root) == t0, "| binding file unchanged:",
              files(root).get("configuration-binding.json") == f0.get("configuration-binding.json"))
        print(f"[821/{name}] writer open again:", run(WRITER, root, lt, ls), "| tables unchanged:", C.tables_digest(root) == t0)
        print(f"[821/{name}] writer recall:", run(WRITER, root, lt, ls, "recall"), C.inspect(root))
        print(f"[821/{name}]   legacy file unchanged:", files(root).get("configuration-binding.json") == f0.get("configuration-binding.json"))
        t1 = C.tables_digest(root)
        print(f"[821/{name}] reader opens migrated:", run(READER, root, lt, ls), "| unchanged:", C.tables_digest(root) == t1)
        print(f"[821/{name}] writer reopens:", run(WRITER, root, lt, ls))

    # #809 frozen v7 stores
    for name in ("cross-scope", "forward-reference", "shared-membership"):
        root = C.tmp() / name
        shutil.copytree(FIX809 / name, root)
        lt, ls = "tenant:legacy", "project:a"
        t0, f0 = C.tables_digest(root), files(root)
        r1 = run(WRITER, root, lt, ls)
        same = C.tables_digest(root) == t0
        r2 = run(WRITER, root, lt, ls, "recall")
        i = C.inspect(root)
        lf = files(root).get("configuration-binding.json") == f0.get("configuration-binding.json")
        r3 = run(READER, root, lt, ls)
        r4 = run(WRITER, root, lt, ls)
        print(f"[809/{name}] open: {r1} | open wrote nothing: {same} | recall: {r2} | {i} | legacy file unchanged: {lf} | reader: {r3} | writer reopen: {r4}")


if __name__ == "__main__":
    main()
