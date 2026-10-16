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
import tempfile
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


class TimeOrderedIntentsKeepTheTemporalOrder(_Store):
    """Review finding 1 (blocking, C8 review): two still-valid conflicting statements tied on BM25.

    Under 3.4.0 the temporal order stage puts the newer first. Fusion sits above that stage, so a
    slightly closer older statement would win. C8 skips fusion for intents that order by time.
    FAIL-FIRST on 69611b3f; holds on C6.
    """

    QUERY, OLD, NEW = "Who is my manager?", "My manager is Joanna Pike.", "My manager is Rahul Mehta."

    def case(self, query, intent, selection):
        _TableRepresentation.TABLE = {query: {self.OLD: 0.70, self.NEW: 0.60}}
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        memory = self.open(root=Path(folder.name))
        for index, text in enumerate(["The boiler is serviced in May.", "We walk the dog at seven."]):
            memory.remember(f"memory:f{index}", text)
        old = memory.remember("memory:old", self.OLD, valid_from="2023-01-01T00:00:00Z")["fact_uuid"]
        new = memory.remember("memory:new", self.NEW, valid_from="2025-06-01T00:00:00Z")["fact_uuid"]
        kwargs = {"temporal_intent": intent} if intent else {}
        result = memory.recall(query, budget=1, return_selection=selection, **kwargs)
        evidence = {u: result["admissions"][u]["ranking_evidence"] for u in (old, new)}
        self.assertEqual(evidence[old].get("lexical_relevance_score"), evidence[new].get("lexical_relevance_score"))
        self.assertLess(result["admitted"].index(new), result["admitted"].index(old))
        self.assertEqual(result["returned"], [new])
        return evidence

    def test_declared_current_newer_first_both_selections(self):  # FAIL-FIRST
        for selection in ("ranked_prefix", "relevance_sufficient"):
            evidence = self.case(self.QUERY, {"mode": "current", "reference_time": "2026-10-16T00:00:00Z"}, selection)
        self.assertNotEqual((evidence[next(iter(evidence))].get("fusion") or {}).get("status"), "applied")

    def test_as_of_after_both_starts_latest_first(self):  # FAIL-FIRST
        self.case(self.QUERY, {"mode": "as_of", "reference_time": "2026-01-01T00:00:00Z",
                               "target_start": "2026-01-01T00:00:00Z"}, "ranked_prefix")

    def test_now_in_the_question_newer_first(self):  # FAIL-FIRST
        self.case("Who is my manager now?", None, "ranked_prefix")


if __name__ == "__main__":
    unittest.main()
