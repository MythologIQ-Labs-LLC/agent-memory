"""P9: a refused direct planner recall on a semantic-enabled handle still writes derived sidecar vectors
(the vector route runs before admission, and admission is where the guard fires). Uses the #802 offline provider.
"""
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403
sys.path.insert(0, str(Path(REF)))
from unittest import mock
from agentmem_ref.runtime import representation_onnx
from tests.test_802_semantic_cache_deletion import _OfflineRepresentation

import tempfile
root = tempfile.mkdtemp(prefix="816s-")
with mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _OfflineRepresentation):
    m = AgentMemory.open(root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="probe",
                         semantic_retrieval="required")
    assert m.remember("memory:d", "The dog is Biscuit.")["committed"]
    path = m.semantic_retrieval_posture()["store"]["path"]
    count = lambda: sqlite3.connect(path).execute("SELECT COUNT(*) FROM vectors").fetchone()[0]  # noqa: E731
    before = count()
    try:
        m.runtime.recall_planner.recall("dog", m._handle_recall_context())
        print("direct planner recall: NOT refused")
    except Exception as exc:  # noqa: BLE001
        print("direct planner recall: refused", type(exc).__name__)
    print(f"sidecar vector rows before={before} after refusal={count()}")
    m.close()
    print("close then", try_reopen(root) if False else "skip")
