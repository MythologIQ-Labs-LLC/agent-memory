"""Provider failure during recall (after a successful open), auto and required. usage: probe_failure.py <tree>"""
import json, sys, tempfile
from pathlib import Path
from unittest import mock
tree = Path(sys.argv[1]).resolve(); sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import representation_onnx
from agentmem_ref.runtime.vector_retrieval import VectorRepresentationSpec
class Flaky:
    spec = VectorRepresentationSpec(representation_ref="test:flaky", representation_version="1", config_digest="sha256:" + "cd" * 32, dimensions=4, deterministic_rebuild=True)
    fail = False
    def __init__(self, d=None): pass
    def embed(self, text):
        if Flaky.fail: raise representation_onnx.RepresentationUnavailable("inference failed")
        return (0.5, 0.5, 0.5, 0.5)
class NaN(Flaky):
    def embed(self, text): return (float("nan"),) * 4
mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", Flaky).start()
for mode in ("auto", "required"):
    with tempfile.TemporaryDirectory() as tmp, AgentMemory.open(tmp, tenant="t:f", actor_id="a", scope="u:f", purpose="p", semantic_retrieval=mode) as m:
        w = m.remember("x", "The deploy window is Thursday.")
        Flaky.fail = True
        try:
            r = m.recall("deploy window"); out = {"returned_ok": r["returned"] == [w["fact_uuid"]]}
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}"[:120]}
        Flaky.fail = False
        print(json.dumps({"tree": tree.name, "mode": mode, "query-time failure": out}))
mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", NaN).start()
with tempfile.TemporaryDirectory() as tmp, AgentMemory.open(tmp, tenant="t:f", actor_id="a", scope="u:f", purpose="p", semantic_retrieval="auto") as m:
    m.remember("x", "The deploy window is Thursday.")
    try: print(json.dumps({"tree": tree.name, "nan vectors": m.recall("deploy window")["returned"] != []}))
    except Exception as e: print(json.dumps({"tree": tree.name, "nan vectors error": f"{type(e).__name__}: {e}"[:120]}))
