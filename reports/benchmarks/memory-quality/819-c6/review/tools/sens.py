"""usage: sens.py min_best margin k_single k_set out.json  (C6 tree, gen.json, semantic required)"""
import runpy, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "cand" / "reference"))
from agentmem_ref.runtime import vector_retrieval as vr
mb, mg, ks, kset, out = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
vr.RankBoundedProposalPolicy.__init__.__defaults__ = (mb, mg, ks, kset)
sys.argv = ["harness.py", str(here.parent / "cand"), str(here.parent / "gen.json"), "required", out]
runpy.run_path(str(here / "harness.py"), run_name="__main__")
