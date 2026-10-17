"""#819 C9: corroborated-rank sufficiency (selection policy 2.4.0).

Fail-first tests, preregistered in ``reports/benchmarks/memory-quality/819-c9/PREREGISTRATION-C9.md``.

C8 decides sufficiency on the 3.4.0 order, so a memory that fusion ranks highly is withheld whenever
its BM25 relevance is below the floor. 2.4.0 credits such a memory only when three independent
conditions hold:
- it has positive topical relevance (``below_relative_floor``, never ``no_informative_term_match``);
- the fused order places it above the lowest memory already selected;
- its dense similarity is at least the lowest similarity among the selected primary evidence.

Dense similarity is therefore never the only evidence, and it is compared only with evidence
selection already justified. Tests marked FAIL-FIRST fail on C8 ``24d4dd26``; the others are
false-positive and safety controls that hold on both heads.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_c7_rank_fusion import BOILER, BOILER_FACTS, _Store, _TableRepresentation, _evidence  # noqa: E402

RESTAURANT = "What is the Boston restaurant I know?"
RESTAURANT_FACTS = {
    "memory:guide": "Boston restaurant I know: the Boston restaurant from the food blog.",
    "memory:home1": "I live in Boston.",
    "memory:home2": "I moved to Denver last month.",
    "memory:f": "The kettle needs descaling.",
    "memory:decoy": "The waiter at the noodle bar was very friendly.",
}


def _residence(value, *, change=False, replaces=None):
    proposition = {"subject": "user", "attribute": "residence", "value": value,
                   "assertion": "change" if change else "state", "cardinality": "single"}
    if replaces:
        proposition["replaces_value"] = replaces
    return proposition


class _Selection(_Store):
    def table(self, query: str, facts: dict[str, str], sims: dict[str, float]) -> None:
        _TableRepresentation.TABLE = {query: {facts[ref]: value for ref, value in sims.items()}}

    def basis(self, result: dict) -> dict[str, str]:
        return {self.refs[u]: (d.get("return_selection") or {}).get("basis")
                for u, d in result["admissions"].items() if u in self.refs}

    def seed_restaurant(self, memory, guide_similarity: float) -> None:
        self.table(RESTAURANT, RESTAURANT_FACTS, {"memory:guide": guide_similarity, "memory:home1": 0.60,
                                                  "memory:home2": 0.20, "memory:f": 0.05, "memory:decoy": 0.70})
        for ref, observed, proposition in (("memory:guide", "2025-01-01", None),
                                           ("memory:home1", "2025-01-01", _residence("Boston")),
                                           ("memory:home2", "2025-06-01", _residence("Denver", change=True, replaces="Boston")),
                                           ("memory:f", "2025-01-01", None),
                                           ("memory:decoy", "2025-01-01", None)):
            kwargs = {"proposition": proposition} if proposition else {}
            outcome = memory.remember(ref, RESTAURANT_FACTS[ref], source_ref="user:u", observed_at=observed, **kwargs)
            self.assertTrue(outcome["committed"], outcome)
            self.refs[outcome["fact_uuid"]] = ref


class CorroboratedRecovery(_Selection):
    def test_topical_memory_fused_above_and_as_similar_as_the_evidence_is_returned(self):  # FAIL-FIRST
        # Restates C7's test_fusion_does_not_make_a_below_floor_memory_sufficient (preregistered change):
        # 'serviced' has topical relevance below the floor, fusion places it above 'manual' (the only
        # selected memory), and it is more similar to the query than 'manual'.
        self.table(BOILER, BOILER_FACTS, {"memory:serviced": 0.35, "memory:f1": 0.30, "memory:f2": 0.25, "memory:manual": 0.10})
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        result = memory.recall(BOILER, budget=10)
        returned = self.ids(result["returned"])
        self.assertEqual(self.basis(result)["memory:serviced"], "corroborated_rank")
        self.assertIn("memory:serviced", returned)
        self.assertIn("memory:manual", returned)
        self.assertLess(returned.index("memory:serviced"), returned.index("memory:manual"))  # fused order kept
        for ref in ("memory:f1", "memory:f2"):  # no topical match: dense similarity alone is not evidence
            self.assertNotIn(ref, returned)
        self.assertEqual(result["return_policy"]["corroborated_rank_count"], 1)
        self.assertEqual(result["return_policy"]["policy_version"], "2.4.0")

    def test_a_recovered_state_brings_its_lifecycle_successor(self):  # FAIL-FIRST
        memory = self.open()
        self.seed_restaurant(memory, guide_similarity=0.10)
        result = memory.recall(RESTAURANT, budget=10)
        basis, returned = self.basis(result), self.ids(result["returned"])
        self.assertEqual(basis["memory:home1"], "corroborated_rank")
        self.assertEqual(basis["memory:home2"], "lifecycle_successor")
        self.assertIn("memory:home1", returned)
        self.assertIn("memory:home2", returned)
        self.assertNotIn("memory:f", returned)


class FalsePositiveControls(_Selection):
    def test_a_memory_without_topical_match_stays_withheld_at_the_top_cosine(self):
        # f1 has the highest cosine (below the route's proposal floor, so no route proposes it).
        self.table(BOILER, BOILER_FACTS, {"memory:f1": 0.39, "memory:manual": 0.10, "memory:serviced": 0.05, "memory:f2": 0.02})
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        result = memory.recall(BOILER, budget=10)
        self.assertEqual(self.basis(result)["memory:f1"], "no_informative_term_match")
        self.assertNotIn("memory:f1", self.ids(result["returned"]))

    def test_a_topical_memory_less_similar_than_the_evidence_stays_withheld(self):
        self.table(BOILER, BOILER_FACTS, {"memory:manual": 0.50, "memory:serviced": 0.35, "memory:f1": 0.30, "memory:f2": 0.25})
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        result = memory.recall(BOILER, budget=10)
        self.assertEqual(self.basis(result)["memory:serviced"], "below_relative_floor")
        self.assertEqual(self.ids(result["returned"]), ["memory:manual"])

    def test_a_topical_memory_fused_below_the_selected_evidence_stays_withheld(self):
        memory = self.open()
        self.seed_restaurant(memory, guide_similarity=0.30)
        result = memory.recall(RESTAURANT, budget=10)
        admitted, returned = self.ids(result["admitted"]), self.ids(result["returned"])
        self.assertGreater(admitted.index("memory:home1"), admitted.index("memory:guide"))
        self.assertEqual(self.basis(result)["memory:home1"], "below_relative_floor")
        self.assertNotIn("memory:home1", returned)
        self.assertNotIn("memory:home2", returned)

    def test_a_recall_with_no_topical_evidence_still_abstains(self):
        facts = {"memory:f1": BOILER_FACTS["memory:f1"], "memory:f2": BOILER_FACTS["memory:f2"],
                 "memory:f3": "The hallway needs a new rug."}
        self.table(BOILER, facts, {"memory:f1": 0.39, "memory:f2": 0.38, "memory:f3": 0.37})
        memory = self.open()
        self.seed(memory, facts)
        result = memory.recall(BOILER, budget=10)
        self.assertEqual(result["returned"], [])
        self.assertTrue(result["return_policy"]["abstained"])


class SafetyControls(_Selection):
    def test_declared_current_intent_keeps_the_temporal_order(self):
        # An ended-window statement stays admitted under current intent (ranked below the valid one, as
        # on C4-C8); fusion is skipped for time-ordering intents, so 2.4.0 cannot reorder or add.
        query = "Where is the spare boiler key kept?"
        facts = {"memory:key-old": "The spare boiler key was kept in the meter cupboard.",
                 "memory:key-new": "The spare key now hangs in the boiler cupboard by the stairs, next to the boiler manual for the boiler.",
                 "memory:f1": BOILER_FACTS["memory:f1"]}
        self.table(query, facts, {"memory:key-old": 0.60, "memory:key-new": 0.20, "memory:f1": 0.10})
        memory = self.open()
        for ref, text, window in (("memory:key-old", facts["memory:key-old"], {"valid_from": "2024-01-01T00:00:00Z", "valid_until": "2026-01-01T00:00:00Z"}),
                                  ("memory:key-new", facts["memory:key-new"], {"valid_from": "2026-01-01T00:00:00Z"}),
                                  ("memory:f1", facts["memory:f1"], {})):
            self.refs[memory.remember(ref, text, **window)["fact_uuid"]] = ref
        result = memory.recall(query, budget=10, temporal_intent={"mode": "current", "reference_time": "2026-10-17T00:00:00Z"})
        returned = self.ids(result["returned"])
        self.assertEqual(returned[0], "memory:key-new")
        self.assertNotIn("corroborated_rank", self.basis(result).values())
        self.assertEqual(result["return_policy"].get("corroborated_rank_count", 0), 0)

    def test_superseded_forgotten_and_other_scope_memories_are_never_returned(self):
        facts = dict(BOILER_FACTS)
        facts["memory:old-date"] = "The boiler was due a service in May."
        facts["memory:dropped"] = "The boiler engineer said the service might slip."
        self.table(BOILER, {**facts, "memory:theirs": "Their boiler was serviced last week by GasCo.",
                            "memory:new-date": "The boiler service date moved to 3 March."},
                   {"memory:old-date": 0.90, "memory:dropped": 0.85, "memory:theirs": 0.95, "memory:new-date": 0.20,
                    "memory:manual": 0.10, "memory:serviced": 0.05, "memory:f1": 0.02, "memory:f2": 0.01})
        other = self.open(scope="user:c9-other")
        other.remember("memory:theirs", "Their boiler was serviced last week by GasCo.")
        other.close()
        memory = self.open()
        self.seed(memory, facts)
        self.assertTrue(memory.correct("memory:old-date", "The boiler service date moved to 3 March.", evidence=_evidence())["committed"])
        self.assertTrue(memory.forget("memory:dropped", evidence=_evidence())["committed"])
        result = memory.recall(BOILER, budget=10)
        blob = json.dumps(result)
        for text in ("due a service in May", "might slip", "GasCo"):
            self.assertNotIn(text, blob)


class RouteOff(_Selection):
    semantic = "off"

    def test_route_off_selection_is_unchanged(self):
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        result = memory.recall(BOILER, budget=10)
        self.assertEqual(self.basis(result)["memory:serviced"], "below_relative_floor")
        self.assertEqual(self.ids(result["returned"]), ["memory:manual"])
        self.assertNotIn("corroborated_rank", self.basis(result).values())


if __name__ == "__main__":
    unittest.main()
