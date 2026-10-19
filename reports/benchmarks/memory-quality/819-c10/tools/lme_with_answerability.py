"""run_longmemeval.py with semantic_answerability injected into AgentMemory.open (evaluation-only).

    lme_with_answerability.py <runtime_root> <mode> -- <run_longmemeval args>
One verified scorer is shared across opens (load time only; numerics unchanged).
"""
import runpy, sys
from pathlib import Path
root, mode = Path(sys.argv[1]).resolve(), sys.argv[2]
args = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, str(root / "reference"))
from agentmem_ref.api.surface import AgentMemory
from agentmem_ref.runtime import answerability_onnx as ao
if mode != "off":
    scorer = ao.OnnxAnswerabilityScorer()
    ao.OnnxAnswerabilityScorer = lambda model_dir=None, **kw: scorer
    real = AgentMemory.open.__func__
    def patched(cls, *a, **kw):
        if kw.get("semantic_retrieval") == "required":
            kw["semantic_answerability"] = mode
        return real(cls, *a, **kw)
    AgentMemory.open = classmethod(patched)
sys.argv = [str(root / "reference/run_longmemeval.py")] + args
runpy.run_path(sys.argv[0], run_name="__main__")
