import sys, time, unittest
sys.path.insert(0, sys.argv[1])
from dataclasses import replace
from agentmem_ref import policy
from tests.test_runtime_composition import _context, _plan, _proposal
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
import tempfile
from pathlib import Path
root = Path(tempfile.mkdtemp())
rt = ConfiguredCompositionRuntime.create(root, tenant="tenant-acme", plan=_plan())
marks = {10, 100, 500, 1000, 2000}
for i in range(1, 2001):
    p = replace(_proposal(f"p:{i}", operation="promotion"), target_reference=f"memory:{i}")
    assert rt.retain(p, f"note {i} about pump station {i}").committed
    d = replace(_proposal(f"d:{i}", operation="pruning", review_satisfied=True, approval_refs=("a",)), target_reference=f"memory:{i}", target_class=policy.M1, proposed_strength="tentative")
    s = time.perf_counter(); assert rt.delete_current(d).committed; dt = time.perf_counter() - s
    if i in marks:
        print(f"tombstones={i:5d} prune={dt*1e3:7.1f} ms substrate+governance={sum(f.stat().st_size for f in root.rglob('*') if f.is_file())/1e6:6.2f} MB", flush=True)
