"""Formal AgentMemBench/MESA runner (#694): frozen classifier, diagnostics and adapter.

These tests never run the MESA workloads; they use synthetic traces and
non-benchmark text, so they cannot be used to fit the adapter to scores.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REFERENCE))

import run_agentmembench_formal as formal  # noqa: E402


def _trace(writes, candidates, admitted, returned, decisions=None):
    return {"writes": writes, "candidates": candidates, "admitted": admitted, "returned": returned,
            "decisions": decisions or {}}


def _write(text, uuid, committed=True):
    return {"text": text, "fact_uuid": uuid if committed else None, "committed": committed}


def _sem(entity, prop, value, relations=()):
    return {"proposition": {"status": "known", "entity": entity, "property": prop, "value": value},
            "relations": list(relations)}


UNKNOWN = {"proposition": {"status": "unknown", "basis": "none"}, "relations": []}
WRITES = [_write("The user lives in OLD_location_0000.", "f-old"),
          _write("The user now lives in NEW_location_0000.", "f-new")]


class ClassifierTests(unittest.TestCase):
    def classify(self, trace, semantics):
        return formal.classify_conflict_case(0, "OLD_location_0000", "NEW_location_0000", trace, semantics)

    def test_stale_with_unknown_propositions_is_write_interpretation(self):
        lexical = {"ranking": {"ordered_before_next_by": "lexical_relevance_desc", "constraint_applied": False,
                               "temporal_applicability": "unknown_temporal_basis"}}
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-old", "f-new"], ["f-old"],
                       {"f-old": lexical, "f-new": lexical})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertEqual(case["outcome"], "stale")
        self.assertEqual(case["primary_stage"], "write_interpretation")
        self.assertEqual(case["unmet_stages"][0], "write_interpretation")
        self.assertIn("ranking_fusion", case["unmet_stages"])
        self.assertIsNone(case["win_basis"])

    def test_missing_candidate_precedes_later_stages(self):
        trace = _trace(WRITES, ["f-old"], ["f-old"], ["f-old"])
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertEqual(case["primary_stage"], "candidate_generation")

    def test_refused_write_is_write_admission(self):
        writes = [WRITES[0], _write("The user now lives in NEW_location_0000.", "f-new", committed=False)]
        case = self.classify(_trace(writes, ["f-old"], ["f-old"], ["f-old"]), {"f-old": UNKNOWN})
        self.assertEqual(case["primary_stage"], "write_admission")

    def test_known_different_slots_is_identity(self):
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-old", "f-new"], ["f-old"])
        sems = {"f-old": _sem("user", "live in", "old"), "f-new": _sem("user", "move to", "new")}
        self.assertEqual(self.classify(trace, sems)["primary_stage"], "identity_slot_resolution")

    def test_same_slot_without_state_change_is_supersession_reasoning(self):
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-old", "f-new"], ["f-old"])
        rel = {"other_fact_uuid": "f-old", "classification": "conflict", "basis": "x"}
        sems = {"f-old": _sem("user", "live in", "old"), "f-new": _sem("user", "live in", "new", [rel])}
        case = self.classify(trace, sems)
        self.assertEqual(case["primary_stage"], "conflict_supersession_reasoning")
        self.assertEqual(case["relation"]["classification"], "conflict")

    @staticmethod
    def _ranked(first_by, mode="current", applicability="unknown_temporal_basis", constraint=False):
        return {"ranking": {"ordered_before_next_by": first_by, "constraint_applied": constraint,
                            "temporal_applicability": applicability, "query_intent_mode": mode}}

    def test_lexical_win_is_not_credited_to_currentness(self):
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-new", "f-old"], ["f-new"],
                       {"f-new": self._ranked("lexical_relevance_desc:bm25_admitted_set:lexical"),
                        "f-old": self._ranked(None)})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertEqual(case["outcome"], "new_fact")
        self.assertIsNone(case["primary_stage"])
        self.assertEqual(case["win_basis"], "lexical_ordering")

    def test_newer_first_tiebreak_is_reported_as_such(self):
        # audit ground 1(b): a win decided by temporal_order_within_query_regime
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-new", "f-old"], ["f-new"],
                       {"f-new": self._ranked("temporal_order_within_query_regime"),
                        "f-old": self._ranked(None)})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertEqual(case["decisive_stage"], "temporal_order_within_query_regime")
        self.assertEqual(case["win_basis"], "temporal_order_tiebreak")

    def test_uncontested_win_is_not_currentness(self):
        # audit ground 1(a): old fact not admitted, new labelled not_evaluated
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-new"], ["f-new"],
                       {"f-new": self._ranked(None, applicability="not_evaluated")})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertFalse(case["old_admitted"])
        self.assertEqual(case["win_basis"], "uncontested")

    def test_constraint_win_is_currentness(self):
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-new", "f-old"], ["f-new"],
                       {"f-new": self._ranked("lexical_relevance_desc", constraint=True),
                        "f-old": self._ranked(None, constraint=True)})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertEqual(case["win_basis"], "currentness_mechanism")

    def test_demoted_old_fact_satisfies_currentness_condition(self):
        demoted = sorted(formal._demoted_labels("current"))[0]
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-old", "f-new"], ["f-old"],
                       {"f-old": self._ranked("lexical", applicability=demoted), "f-new": self._ranked(None)})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertTrue(case["conditions"]["temporal_applicability_currentness"])

    def test_explicit_termination_relation_satisfies_interpretation_and_slot(self):
        rel = {"other_fact_uuid": "f-old", "classification": "state_change_candidate", "basis": "explicit_termination:no longer",
               "proposal": {}}
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-old", "f-new"], ["f-old"],
                       {"f-old": self._ranked("lexical"), "f-new": self._ranked(None)})
        sems = {"f-old": _sem("user", "live in", "old"), "f-new": dict(UNKNOWN, relations=[rel])}
        case = self.classify(trace, sems)
        self.assertEqual(case["primary_stage"], "temporal_applicability_currentness")

    def test_stage_order_is_frozen(self):
        freeze = formal.load_freeze()
        self.assertEqual(list(formal.STAGES), freeze["m4_classifier"]["stages_in_order"])
        self.assertEqual(formal.CLASSIFIER_VERSION, freeze["m4_classifier"]["version"])


class DiagnosticsTests(unittest.TestCase):
    DETAILS = [
        {"event_type": "A", "memory": "Likes tea.", "reference_answer": "Tea", "retrieved": ["Likes tea."]},
        {"event_type": "A", "memory": "Uses vim.", "reference_answer": "emacs", "retrieved": ["Uses vim."]},
        {"event_type": "B", "memory": "Lives in Oslo.", "reference_answer": "Oslo", "retrieved": []},
    ]

    def test_rates(self):
        diag = formal.retrieval_diagnostics(self.DETAILS)
        self.assertAlmostEqual(diag["answer_substring_hit_rate"], 1 / 3)
        self.assertAlmostEqual(diag["source_text_hit_rate"], 2 / 3)
        self.assertAlmostEqual(diag["empty_retrieval_rate"], 1 / 3)
        self.assertEqual(diag["answer_substring_hit_rate_by_event_type"], {"A": 0.5, "B": 0.0})
        self.assertEqual(diag["diagnostics_version"], formal.load_freeze()["deterministic_diagnostics"]["version"])

    def test_empty_details_are_not_zero(self):
        self.assertEqual(formal.retrieval_diagnostics([]), {"records": 0})

    def test_linked_only_projection_removes_text(self):
        records = [{"text": "Likes tea."}, {"text": "Uses vim."}]
        rows = [{"index": 0, "event_type": "A", "source_id": "s0", "hit": None,
                 "memory": "Likes tea.", "query": "q", "reference_answer": "Tea",
                 "retrieved": ["Likes tea.", "unrelated"]}]
        out = formal.linked_only_details(rows, records)
        rendered = json.dumps(out)
        self.assertNotIn("Likes tea", rendered)
        self.assertEqual(out[0]["retrieved"][0]["selected_record_index"], 0)
        self.assertIsNone(out[0]["retrieved"][1]["selected_record_index"])


class AdapterTests(unittest.TestCase):
    def test_budget_trace_and_semantics_snapshot(self):
        adapter = formal.AgentMemoryFormalAdapter()
        try:
            adapter.phase_label = "conflict"
            adapter.add("The user's favourite drink is coffee.", "conflict_00000")
            adapter.add("The user's favourite drink is tea.", "conflict_00000")
            adapter.add("An unrelated note about drinks.", "other_user")
            returned = adapter.search("What is the user's favourite drink?", "conflict_00000", 1)
            self.assertLessEqual(len(returned), 1)
            self.assertEqual(adapter.traces, {})  # digesting is deferred out of the timed call
            other = adapter.search("drinks", "other_user", 5)
            self.assertNotIn("The user's favourite drink is tea.", other)
            adapter.phase_label = "isolation"
            adapter.reset()
            trace = adapter.traces["conflict"][0]
            self.assertEqual(trace["limit"], 1)
            self.assertEqual(len(trace["writes"]), 2)
            self.assertTrue(set(trace["returned"]) <= set(trace["admitted"]) <= set(trace["candidates"]))
            self.assertEqual(len(adapter.traces["conflict"]), 1)
            self.assertEqual(adapter.tallies["conflict"]["recall_calls"], 2)
            self.assertEqual(len([k for k in adapter.write_semantics if k.startswith("conflict:")]), 2)
        finally:
            adapter.close()

    def test_delete_tombstones_through_facade(self):
        adapter = formal.AgentMemoryFormalAdapter()
        try:
            ids = adapter.add("The user's locker code is ZX-41.", "u1")
            self.assertTrue(any("ZX-41" in text for text in adapter.search("locker code", "u1", 5)))
            adapter.delete(ids)
            self.assertFalse(any("ZX-41" in text for text in adapter.search("locker code", "u1", 5)))
        finally:
            adapter.close()


class JudgeTests(unittest.TestCase):
    ROWS = [{"retrieved": ["a"]}, {"retrieved": []}, {"retrieved": ["b"]}]

    def test_every_non_empty_row_parsed_yields_recall(self):
        result = formal.judged_recall([True, False, False], self.ROWS, parsed_responses=2, request_failures=1)
        self.assertEqual(result["status"], "judged")
        self.assertAlmostEqual(result["recall_at_k"], 1 / 3)

    def test_any_exhausted_row_blocks_never_zero(self):
        result = formal.judged_recall([False, False, False], self.ROWS, parsed_responses=0, request_failures=6)
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["recall_at_k"])

    def test_raw_must_match_committed_digests(self):
        raw = {"phases": {"retrieval": {"details": [{"index": 0, "retrieved": ["x"]}]}}}
        good = {"phases": {"retrieval": {"details": [{"retrieved": [{"sha256": formal.sha256_text("x")}]}]}}}
        bad = {"phases": {"retrieval": {"details": [{"retrieved": [{"sha256": formal.sha256_text("y")}]}]}}}
        formal.verify_raw_against_committed(raw, good)
        with self.assertRaises(SystemExit):
            formal.verify_raw_against_committed(raw, bad)


class FreezeTests(unittest.TestCase):
    def test_runner_digest_matches_freeze(self):
        freeze = formal.load_freeze()
        self.assertEqual(formal.sha256_file(Path(formal.__file__)), freeze["runner"]["sha256"])

    def test_freeze_binds_current_runtime_policy_and_contract(self):
        binding = formal.observed_agent_memory_binding()
        frozen = formal.load_freeze()["agent_memory"]
        for key in ("ranking_policy_id", "ranking_policy_version", "public_contract_version"):
            self.assertEqual(binding[key], frozen[key])

    def test_deviations_are_registered(self):
        ids = [item["id"] for item in formal.load_freeze()["deviations"]]
        self.assertEqual(ids, ["D1", "D2", "D3", "D4", "D5", "D6"])

    def test_arguments_are_upstream_defaults(self):
        formal.verify_arguments(formal.load_freeze())
        self.assertEqual(formal.UPSTREAM_DEFAULT_ARGUMENTS, formal.load_freeze()["arguments"])
        args = formal.load_freeze()["arguments"]
        self.assertEqual(
            args,
            {"data": "data/memdialogue_v2.jsonl", "retrieval_records": 1000, "group_size": 10,
             "conflict_pairs": 250, "isolation_users": 100, "isolation_facts": 5, "deletion_records": 200,
             "concurrency_records": 200, "workers": "1,4,8,16", "scales": "100,1000",
             "scale_read_queries": 200, "top_k": 5, "seed": 2027, "warmup_writes": 5},
        )

    def test_m6_is_not_comparable_never_pass(self):
        axis = formal.load_freeze()["axis_plan"]["M6_llm_portability"]
        self.assertEqual(axis["expected_class"], "not_comparable")


if __name__ == "__main__":
    unittest.main()
