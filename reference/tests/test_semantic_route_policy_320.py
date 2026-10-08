"""Ranking policy 3.2.0 and the facade's semantic route (#669).

The semantic route is ordering-subordinate: it adds candidates, but it never counts
toward corroboration, never moves a lexical score, and orders only after every
relevance and temporal stage. With no semantic hit, 3.2.0 orders exactly as 3.1.2.
"""

from __future__ import annotations

import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import representation_onnx  # noqa: E402
from agentmem_ref.runtime.ranking_policy import PostAdmissionRankingPolicy  # noqa: E402
from agentmem_ref.runtime.runtime_composition import (  # noqa: E402
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    MULTI_ROUTE_RANKING_POLICY,
    SHARED_EVIDENCE_ROUTE,
    RetrievalRouteHit,
)
from agentmem_ref.runtime.temporal_intent import resolve_intent  # noqa: E402
from agentmem_ref.runtime.temporal_order_constraints import ExplicitCurrentConstrainedRankingPolicy  # noqa: E402
from agentmem_ref.runtime.vector_retrieval import SEMANTIC_VECTOR_ROUTE, VectorRepresentationSpec  # noqa: E402
from agentmem_ref.state.substrate import Fact  # noqa: E402

# The pre-#669 multi-route policy, reconstructed with 3.1.2's route order, as the
# equivalence oracle.
POLICY_312 = ExplicitCurrentConstrainedRankingPolicy(
    policy_id="multi-route-default",
    route_score_order=(SEMANTIC_VECTOR_ROUTE, SHARED_EVIDENCE_ROUTE, LEXICAL_ROUTE),
    exact_identity_route=EXACT_IDENTITY_ROUTE,
    lexical_route=LEXICAL_ROUTE,
    lexical_relevance="bm25_admitted_set",
    version="3.1.2",
)

FACTS = {
    "f1": Fact("f1", "The user currently lives in Lisbon.", "t", created_at="2026-01-01T00:00:01Z"),
    "f2": Fact("f2", "The user has moved and now lives in Porto.", "t", created_at="2026-01-01T00:00:02Z"),
    "f3": Fact("f3", "The user lives near the river.", "t", created_at="2026-01-01T00:00:03Z"),
    "f4": Fact("f4", "Relocation paperwork for the new apartment.", "t", created_at="2026-01-01T00:00:04Z"),
    "f5": Fact("f5", "Housing contract signed in the north.", "t", created_at="2026-01-01T00:00:05Z"),
}


def _lex(ref: str, score: float = 1.0) -> RetrievalRouteHit:
    return RetrievalRouteHit(route_id=LEXICAL_ROUTE, candidate_ref=ref, raw_score=score)


def _sem(ref: str, score: float) -> RetrievalRouteHit:
    return RetrievalRouteHit(route_id=SEMANTIC_VECTOR_ROUTE, candidate_ref=ref, raw_score=score)


QUERIES = [
    "Where does the user currently live?",
    "Where does the user live?",
    "Where did the user live before?",
    "user lives",
]


def _rank(policy, hits, query):
    by_ref: dict[str, list] = {}
    for hit in hits:
        by_ref.setdefault(hit.candidate_ref, []).append(hit)
    return policy.rank(list(by_ref), by_ref, FACTS.get, query=query, intent=resolve_intent(query, None))


class Policy320Tests(unittest.TestCase):
    def test_route_off_orders_exactly_as_312(self):
        hits = [_lex("f1", 0.5), _lex("f2", 0.4), _lex("f3", 0.3)]
        for query in QUERIES:
            with self.subTest(query=query):
                new_order, new_ev = _rank(MULTI_ROUTE_RANKING_POLICY, hits, query)
                old_order, old_ev = _rank(POLICY_312, hits, query)
                self.assertEqual(new_order, old_order)
                for ref in new_order:
                    for key in ("lexical_relevance_score", "ordered_before_next_by", "temporal_applicability",
                                "constraint_applied", "route_corroboration_count"):
                        self.assertEqual(new_ev[ref].get(key), old_ev[ref].get(key), (ref, key))

    def test_semantic_only_candidates_leave_lexical_scores_byte_identical(self):
        lexical = [_lex("f1"), _lex("f2"), _lex("f3")]
        widened = lexical + [_sem("f4", 0.9), _sem("f5", 0.8), _sem("f1", 0.7)]
        for query in QUERIES:
            with self.subTest(query=query):
                base_order, base_ev = _rank(MULTI_ROUTE_RANKING_POLICY, lexical, query)
                order, ev = _rank(MULTI_ROUTE_RANKING_POLICY, widened, query)
                for ref in ("f1", "f2", "f3"):
                    self.assertEqual(repr(ev[ref]["lexical_relevance_score"]),
                                     repr(base_ev[ref]["lexical_relevance_score"]), ref)
                    self.assertEqual(ev[ref]["route_corroboration_count"], 1, ref)
                self.assertEqual([ref for ref in order if ref in {"f1", "f2", "f3"}], base_order)
                self.assertNotIn("lexical_relevance_score", ev["f4"])

    def test_semantic_orders_only_after_temporal_stages(self):
        order, ev = _rank(MULTI_ROUTE_RANKING_POLICY, [_lex("f1"), _sem("f4", 0.5), _sem("f5", 0.9)], "user lives")
        self.assertEqual(order[0], "f1")  # any lexical relevance outranks similarity
        self.assertEqual(order[1:], ["f5", "f4"])  # similarity orders the remaining ties
        self.assertEqual(ev["f5"]["ordered_before_next_by"], "route_score_desc_subordinate:semantic_vector")
        self.assertEqual(ev["f5"]["subordinate_route_scores"], {SEMANTIC_VECTOR_ROUTE: 0.9})

    def test_identity_records_subordinate_and_scope(self):
        identity = MULTI_ROUTE_RANKING_POLICY.identity()
        self.assertEqual(identity["policy_version"], "3.4.0")  # #671/#732: 3.4.0 keeps 3.2.0 semantics here (identity only)
        self.assertEqual(identity["subordinate_routes"], [SEMANTIC_VECTOR_ROUTE])
        self.assertEqual(identity["lexical_relevance_statistics_scope"], "admitted_set_primary_routes")
        stages = identity["stages"]
        self.assertLess(stages.index("temporal_order_within_query_regime"),
                        stages.index("route_score_desc_subordinate:semantic_vector"))
        self.assertNotIn("route_score_desc:semantic_vector", stages)

    def test_empty_subordinate_routes_keep_base_identity_byte_identical(self):
        base = PostAdmissionRankingPolicy(policy_id="x", route_score_order=("lexical",), exact_identity_route="e",
                                          lexical_route="lexical", lexical_relevance="bm25_admitted_set")
        identity = base.identity()
        self.assertNotIn("subordinate_routes", identity)
        self.assertEqual(identity["lexical_relevance_statistics_scope"], "admitted_set")
        self.assertEqual(identity["policy_version"], "3.1.1")

    def test_subordinate_route_cannot_also_order(self):
        with self.assertRaises(ValueError):
            dataclasses.replace(MULTI_ROUTE_RANKING_POLICY, subordinate_routes=(LEXICAL_ROUTE,))

    def test_pre_temporal_key_stops_at_subordinate_stage(self):
        policy = ExplicitCurrentConstrainedRankingPolicy(
            policy_id="none-regime", route_score_order=(LEXICAL_ROUTE,), exact_identity_route=EXACT_IDENTITY_ROUTE,
            temporal_regime="none", subordinate_routes=(SEMANTIC_VECTOR_ROUTE,),
        )
        intent = resolve_intent("x", None)
        a = policy.evidence("a", [_lex("a", 0.5), _sem("a", 0.9)], FACTS["f1"], intent)
        b = policy.evidence("b", [_lex("b", 0.5), _sem("b", 0.1)], FACTS["f2"], intent)
        self.assertEqual(policy._pre_temporal_key(a, intent), policy._pre_temporal_key(b, intent))


class _Fixture:
    spec = VectorRepresentationSpec(
        representation_ref="agent-memory:test-semantic-fixture",
        representation_version="1.0.0",
        config_digest="sha256:" + "cd" * 32,
        dimensions=3,
        deterministic_rebuild=True,
    )

    def __init__(self, model_dir=None) -> None:
        self.calls = 0

    def embed(self, text: str) -> tuple[float, ...]:
        self.calls += 1
        lowered = text.lower()
        return (1.0 if ("pet" in lowered or "dog" in lowered) else 0.0, 1.0 if "budget" in lowered else 0.0, 0.1)


class FacadeSemanticTests(unittest.TestCase):
    def _seed(self, memory):
        memory.remember("memory:a", "The user's dog is called Biscuit.")
        memory.remember("memory:b", "Finance approved the quarterly budget.")

    def test_default_is_off_and_identical_to_explicit_off(self):
        a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
        with AgentMemory.open(a) as default, AgentMemory.open(b, semantic_retrieval="off") as off:
            self._seed(default)
            self._seed(off)
            self.assertEqual(default.semantic_retrieval_posture()["status"], "disabled")
            self.assertEqual(default.recall("What pet does the user have?")["admitted"],
                             off.recall("What pet does the user have?")["admitted"])
        self.assertFalse((Path(a) / "derived").exists())

    def test_required_without_model_raises_and_auto_records_reason(self):
        empty = tempfile.mkdtemp()
        with self.assertRaises(representation_onnx.RepresentationUnavailable):
            AgentMemory.open(tempfile.mkdtemp(), semantic_retrieval="required", representation_dir=empty)
        with AgentMemory.open(tempfile.mkdtemp(), semantic_retrieval="auto", representation_dir=empty) as memory:
            posture = memory.semantic_retrieval_posture()
            self.assertEqual(posture["status"], "disabled")
            self.assertTrue(posture["reason"].startswith("unavailable"))

    def test_invalid_mode_is_refused(self):
        with self.assertRaises(ValueError):
            AgentMemory.open(tempfile.mkdtemp(), semantic_retrieval="on")

    def test_enabled_route_widens_candidates_through_admission(self):
        root = tempfile.mkdtemp()
        with mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _Fixture):
            with AgentMemory.open(root, semantic_retrieval="required") as memory:
                self._seed(memory)
                result = memory.recall("Which pet?")
                routes = {ref: [hit["route_id"] for hit in decision["route_provenance"]]
                          for ref, decision in result["admissions"].items()}
                semantic = [ref for ref, ids in routes.items() if SEMANTIC_VECTOR_ROUTE in ids]
                self.assertEqual(len(semantic), 1)
                self.assertIn(semantic[0], result["admitted"])
                provenance = [hit for hit in result["admissions"][semantic[0]]["route_provenance"]
                              if hit["route_id"] == SEMANTIC_VECTOR_ROUTE][0]
                self.assertEqual(provenance["representation_config_digest"], _Fixture.spec.config_digest)
                self.assertEqual(provenance["authority_effect"], "none")
                posture = memory.semantic_retrieval_posture()
                self.assertEqual(posture["status"], "enabled")
                self.assertEqual(posture["store"]["rows"], 2)
                memory.recall("Which pet?")
                self.assertEqual(memory.semantic_retrieval_posture()["store"]["rows_written_since_open"], 2)
                self.assertEqual(memory.verify_semantic_store()["mismatched"], [])

    def test_out_of_scope_facts_are_never_semantic_candidates(self):
        root = tempfile.mkdtemp()
        with mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _Fixture):
            with AgentMemory.open(root, semantic_retrieval="required") as memory:
                domains = [memory.tenant, "project:other"]
                memory.remember("memory:x", "The user's dog is called Biscuit.",
                                overrides={"scope": "project:other", "project_ref": "project:other",
                                           "isolation_domain_refs": domains,
                                           "required_isolation_domain_refs": domains})
                result = memory.recall("Which pet?")
                self.assertEqual(result["candidates"], [])


if __name__ == "__main__":
    unittest.main()
