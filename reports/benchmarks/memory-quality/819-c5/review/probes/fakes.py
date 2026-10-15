"""Offline fake-provider harness (same technique as reference/tests/test_c5_low_overlap_selection.py).

Usage from a probe: fakes.setup(worktree); then fakes.Store(table, provider_cls=...)."""
import math, sys, tempfile
from pathlib import Path
from unittest import mock

TENANT, SCOPE = "tenant:fk", "user:fk"


def setup(worktree):
    sys.path.insert(0, str(Path(worktree) / "reference"))
    global AgentMemory, representation_onnx, VectorRepresentationSpec, pm
    from agentmem_ref import AgentMemory
    from agentmem_ref.runtime import representation_onnx
    from agentmem_ref.runtime.vector_retrieval import VectorRepresentationSpec
    from agentmem_ref.memory import procedural_memory as pm


def table_provider(table, dims=8):
    spec = VectorRepresentationSpec(representation_ref="test:fk", representation_version="1.0.0",
                                    config_digest="sha256:" + "fk" * 32, dimensions=dims, deterministic_rebuild=True)

    class Table:
        calls = []
        def __init__(self, model_dir=None):
            self.spec = spec
        def embed(self, text):
            Table.calls.append(text)
            queries = sorted(table)
            if text in table:
                v = [1.0 if q == text else 0.0 for q in queries]
            else:
                v = [table[q].get(text, 0.0) for q in queries]
            rem = 1.0 - sum(c * c for c in v)
            v += [0.0] * (dims - 1 - len(v)) + [math.sqrt(max(rem, 0.0))]
            return tuple(v)
    return Table


class Store:
    def __init__(self, provider_cls, semantic="required"):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", provider_cls)
        self.patch.start()
        self.m = AgentMemory.open(Path(self.tmp.name), tenant=TENANT, actor_id="agent:fk", scope=SCOPE,
                                  purpose="probe", semantic_retrieval=semantic)
        self.refs = {}

    def seed(self, facts):
        for ref, text in facts.items():
            out = self.m.remember(ref, text)
            assert out["committed"], out
            self.refs[out["fact_uuid"]] = ref

    def recall(self, q, budget=10, sel="relevance_sufficient"):
        res = self.m.recall(q, budget=budget, return_selection=sel)
        return res, [self.refs.get(u, u) for u in res["returned"]]

    def close(self):
        self.m.close(); self.patch.stop(); self.tmp.cleanup()
