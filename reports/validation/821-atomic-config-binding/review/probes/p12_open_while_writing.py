"""P12: one process commits generations in a loop; another repeatedly opens the store (and runs
doctor). Counts refusals by diagnostic. Recovery reads the database first and the witness later,
so a commit (plus its witness write) in between can look like 'database behind the witness'."""
from __future__ import annotations

import collections
import subprocess
import sys
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()

WRITER = textwrap.dedent(r"""
import sys, time
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
m = AgentMemory.open(sys.argv[2], tenant="tenant:rev", actor_id="agent:w", scope="project:rev", purpose="rev")
end = time.time() + float(sys.argv[3]); k = 0
while time.time() < end:
    m.remember("memory:w%d" % k, "writer fact %d" % k); k += 1
m.close(); print(k)
""")

READER = textwrap.dedent(r"""
import sys, time, collections
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import doctor
end = time.time() + float(sys.argv[3]); seen = collections.Counter()
root = sys.argv[2]
while time.time() < end:
    try:
        m = AgentMemory.open(root, tenant="tenant:rev", actor_id="agent:r", scope="project:rev", purpose="rev")
        m.close(); seen["OK"] += 1
    except Exception as e:
        seen["open " + type(e).__name__ + ": " + str(e)[:70]] += 1
    rep = doctor.diagnose(root + "/runtime-config.json", state_dir=root)
    seen["doctor " + rep["recovery"]["status"] + " " + str(rep["recovery"].get("detail", ""))[:70]] += 1
for k, v in sorted(seen.items()): print(v, k)
""")


def main():
    root = C.tmp() / "s"
    m = C.open_mem(root)
    for k in range(3):
        m.remember(f"memory:s{k}", f"seed {k}")
    m.close()
    secs = "12"
    w = subprocess.Popen([sys.executable, "-c", WRITER, str(REF), str(root), secs], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(0.5)
    r = subprocess.run([sys.executable, "-c", READER, str(REF), str(root), str(float(secs) - 1)], capture_output=True, text=True, timeout=120)
    wo, we = w.communicate(timeout=120)
    print("writer generations:", wo.strip(), we.strip()[-200:])
    print(r.stdout.strip(), r.stderr.strip()[-300:])
    print("final reopen:", C.try_open(root))


if __name__ == "__main__":
    main()
