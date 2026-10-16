"""#819 C8: C7's rank fusion with an explicit cost budget, and the restated temporal invariant.

Fail-first tests, preregistered in ``reports/benchmarks/memory-quality/819-c8/PREREGISTRATION-C8.md``.
The ranking constants are C7's. C8 changes only cost:
- fusion reuses the similarities the semantic route already computed for this query;
- ``ranked_prefix`` runs the ranking policy once, because the 3.4.0 base order only feeds
  relevance-sufficient selection.

Tests marked FAIL-FIRST fail on C7 ``d05bf2b1``; the others hold on C6, C7 and C8.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentmem_ref.runtime import vector_retrieval  # noqa: E402
from agentmem_ref.runtime.temporal_order_constraints import ExplicitCurrentCrossFactRankingPolicy  # noqa: E402
from test_c7_rank_fusion import BOILER, BOILER_FACTS, BOILER_SIMS, _Store, _TableRepresentation  # noqa: E402


def _counting(original):
    calls = []

    def wrapper(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    return wrapper, calls


class FusionCost(_Store):
    def setUp(self) -> None:
        super().setUp()
        _TableRepresentation.TABLE = {BOILER: {BOILER_FACTS[ref]: value for ref, value in BOILER_SIMS.items()}}
        self.memory = self.open()
        self.seed(self.memory, BOILER_FACTS)

    def test_each_pool_memory_is_scored_once_per_recall(self):  # FAIL-FIRST
        original = vector_retrieval.NativeVectorCandidateRetriever._cosine
        calls = []

        def counting(_self, left, right):
            calls.append(1)
            return original(left, right)

        with mock.patch.object(vector_retrieval.NativeVectorCandidateRetriever, "_cosine", counting):
            ranked, result = self.ranked(self.memory, BOILER)
        self.assertEqual(len(ranked), len(BOILER_FACTS))  # every memory is in the route's pool and admitted
        fusion = {d["ranking_evidence"]["fusion"]["status"] for d in result["admissions"].values() if "rank_position" in d}
        self.assertEqual(fusion, {"applied"})
        self.assertEqual(len(calls), len(BOILER_FACTS))

    def test_ranked_prefix_ranks_once_and_relevance_sufficient_twice(self):  # FAIL-FIRST
        wrapper, calls = _counting(ExplicitCurrentCrossFactRankingPolicy.rank)
        with mock.patch.object(ExplicitCurrentCrossFactRankingPolicy, "rank", wrapper):
            self.memory.recall(BOILER, budget=10, return_selection="ranked_prefix")
            ranked_prefix_calls = len(calls)
            self.memory.recall(BOILER, budget=10)
        self.assertEqual(ranked_prefix_calls, 1)
        self.assertEqual(len(calls) - ranked_prefix_calls, 2)


class TemporalStagesStayAboveFusion(_Store):
    def test_an_ended_statement_ranks_below_its_successor_under_declared_current_intent(self):
        query = "Where is the shed key?"
        old, new = "The shed key is with Malcolm, shed key holder for the shed.", "Spare key: hook inside the gate."
        _TableRepresentation.TABLE = {query: {old: 0.90, new: 0.30}}
        memory = self.open()
        written_old = memory.remember("memory:old", old, valid_from="2024-01-01T00:00:00Z", valid_until="2026-01-01T00:00:00Z")
        written_new = memory.remember("memory:new", new, valid_from="2026-01-01T00:00:00Z")
        self.assertTrue(written_old["committed"] and written_new["committed"])
        for selection in ("ranked_prefix", "relevance_sufficient"):
            result = memory.recall(query, budget=10, return_selection=selection, temporal_intent={"mode": "current", "reference_time": "2026-10-16T00:00:00Z"})
            admitted = result["admitted"]
            self.assertLess(admitted.index(written_new["fact_uuid"]), admitted.index(written_old["fact_uuid"]), selection)


if __name__ == "__main__":
    unittest.main()
