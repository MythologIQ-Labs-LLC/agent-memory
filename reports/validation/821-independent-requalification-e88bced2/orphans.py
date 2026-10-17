"""RES-W2 probe: N writers each SIGKILLed just before the witness rename; count orphans, bytes, and check reopen/recall."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
TREE, N = Path(sys.argv[1]).resolve(), int(sys.argv[2])
sys.argv = [sys.argv[0], str(TREE), "/dev/null"]  # adv821 expects TREE OUT; we reuse its helpers
src = open("/home/user/eval/r821/adv821.py").read().split("\ndef run():")[0]
exec(compile(src, "adv821-helpers", "exec"))
base = tempfile.mkdtemp(prefix="orph-"); root = fresh(base, "o")
rcs = [child(root, f"K{i}", "kill_before_witness_replace", f"k{i}")["rc"] for i in range(N)]
temps = [p for p in root.iterdir() if "generation-witness" in p.name and p.name != WIT]
after = child(root, "Z", "none", "z", iters=5)
ro = reopen(root); fp = facts_present(root, [f"k{i}-0" for i in range(N)])
print(json.dumps({"head": subprocess.run(["git", "-C", str(TREE), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip(),
                  "kills": sum(1 for r in rcs if r == -9), "orphans": len(temps), "orphan_bytes": sum(p.stat().st_size for p in temps),
                  "orphans_after_5_more": len([p for p in root.iterdir() if "generation-witness" in p.name and p.name != WIT]),
                  "reopen": ro, "killed_writers_facts_committed": sum(1 for v in fp.values() if v) if isinstance(fp, dict) else fp,
                  "witness": witness_state(root)}))
