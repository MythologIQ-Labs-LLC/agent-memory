"""Reviewer fail-first test: fusion must not reverse an order decided by the temporal stage.

Run from a tree's reference/ directory:  python -m pytest <this file> -q   (with REVIEW_TREE=<tree>)
Uses the C7 test's deterministic table representation; on C6 (no fusion) it uses the same table
via a local copy, so the test runs on both heads.
"""
import math, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

TREE = Path(os.environ["REVIEW_TREE"]).resolve()
sys.path.insert(0, str(TREE / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import representation_onnx  # noqa: E402
from agentmem_ref.runtime.vector_retrieval import VectorRepresentationSpec  # noqa: E402

D = 8
class Table:
    TABLE = {}
    spec = VectorRepresentationSpec(representation_ref="test:rv-table", representation_version="1.0.0",
                                    config_digest="sha256:" + "ab" * 32, dimensions=D, deterministic_rebuild=True)
    def __init__(self, model_dir=None): pass
    def embed(self, text):
        qs = sorted(self.TABLE)
        v = [1.0 if q == text else 0.0 for q in qs] if text in self.TABLE else [self.TABLE[q].get(text, 0.0) for q in qs]
        rem = 1.0 - sum(c * c for c in v)
        return tuple(v + [0.0] * (D - 1 - len(v)) + [math.sqrt(max(rem, 0.0))])

Q = "Who is my manager?"
OLD, NEW = "My manager is Joanna Pike.", "My manager is Rahul Mehta."   # identical BM25 against Q

class TemporalStageNotReversed(unittest.TestCase):
    def run_case(self, intent, selection):
        Table.TABLE = {Q: {OLD: 0.70, NEW: 0.60}}   # the older statement is slightly closer in embedding space
        with mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", Table), tempfile.TemporaryDirectory() as tmp:
            with AgentMemory.open(tmp, tenant="t:rv", actor_id="a:rv", scope="s:rv", purpose="rv", semantic_retrieval="required") as m:
                for i, t in enumerate(["The boiler is serviced in May.", "We walk the dog at seven."]):
                    m.remember(f"memory:f{i}", t)
                old = m.remember("memory:old", OLD, valid_from="2023-01-01T00:00:00Z")["fact_uuid"]
                new = m.remember("memory:new", NEW, valid_from="2025-06-01T00:00:00Z")["fact_uuid"]
                r = m.recall(Q, budget=1, return_selection=selection, temporal_intent=intent, reference_time="2026-10-16T00:00:00Z")
                ev = {u: r["admissions"][u]["ranking_evidence"] for u in (old, new)}
                self.assertEqual(ev[old]["temporal_applicability"], ev[new]["temporal_applicability"])  # both applicable
                self.assertEqual(ev[old]["lexical_relevance_score"], ev[new]["lexical_relevance_score"])  # BM25 tie
                return r["admitted"].index(new) < r["admitted"].index(old), r["returned"] == [new]

    def test_declared_current_newer_first_ranked_prefix(self):
        self.assertEqual(self.run_case({"mode": "current"}, "ranked_prefix"), (True, True))

    def test_declared_current_newer_first_relevance_sufficient(self):
        self.assertEqual(self.run_case({"mode": "current"}, "relevance_sufficient"), (True, True))

    def test_as_of_after_both_starts_latest_first(self):
        self.assertEqual(self.run_case({"mode": "as_of", "target_start": "2026-01-01T00:00:00Z"}, "ranked_prefix"), (True, True))

    def test_language_current_newer_first(self):
        Table.TABLE = {}
        global Q
        q0 = Q
        Q = "Who is my manager now?"
        try:
            self.assertEqual(self.run_case(None, "ranked_prefix"), (True, True))
        finally:
            Q = q0

if __name__ == "__main__":
    unittest.main()
