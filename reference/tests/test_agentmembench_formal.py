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
    def _ranked(first_by, mode="current", applicability="unknown_temporal_basis", constraint=False,
                lexical=1.0, posture="explicit"):
        return {"ranking": {"ordered_before_next_by": first_by, "constraint_applied": constraint,
                            "temporal_applicability": applicability, "query_intent_mode": mode,
                            "query_intent_posture": posture, "query_intent_basis": "query_language_explicit",
                            "route_scores": {"lexical": lexical}, "route_corroboration_count": 1,
                            "exact_identity": False, "lexical_relevance_score": lexical}}

    def test_lexical_win_is_not_credited_to_currentness(self):
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-new", "f-old"], ["f-new"],
                       {"f-new": self._ranked("lexical_relevance_desc:bm25_admitted_set:lexical", lexical=2.0),
                        "f-old": self._ranked(None, lexical=1.0)})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertEqual(case["outcome"], "new_fact")
        self.assertIsNone(case["primary_stage"])
        self.assertEqual(case["win_basis"], "lexical_ordering")

    def test_newer_first_tiebreak_outside_explicit_profile(self):
        # audit iteration 1 ground 1(b): inferred (non-explicit) current intent keeps write-clock ties
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-new", "f-old"], ["f-new"],
                       {"f-new": self._ranked("temporal_order_within_query_regime", posture="inferred"),
                        "f-old": self._ranked(None, posture="inferred")})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertEqual(case["decisive_stage"], "temporal_order_within_query_regime")
        self.assertEqual(case["win_basis"], "temporal_order_tiebreak")

    def test_explicit_current_relevance_tie_is_content_identity_not_recency(self):
        # audit iteration 2 ground 1: digest order that happens to equal newer-first
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-new", "f-old"], ["f-new"],
                       {"f-new": self._ranked("temporal_order_within_query_regime"),
                        "f-old": self._ranked(None)})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertTrue(case["content_identity_tie"])
        self.assertEqual(case["win_basis"], "content_identity_tiebreak")

    def test_stale_by_content_identity_records_loss_basis(self):
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-old", "f-new"], ["f-old"],
                       {"f-old": self._ranked("explicit_current_unknown_tie_content_identity"),
                        "f-new": self._ranked(None)})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertEqual(case["outcome"], "stale")
        self.assertEqual(case["loss_basis"], "content_identity_tiebreak")

    def test_stage_vocabulary_mapping(self):
        self.assertEqual(formal._order_basis("explicit_current_exclusive_pairwise_constraint", False),
                         "currentness_mechanism")
        for stage in ("stable_constraint_topology", "base_ranking_preserved", "indistinguishable", None):
            self.assertEqual(formal._order_basis(stage, False), "undetermined")
        for stage in ("route_score_desc:lexical", "route_corroboration_count_desc", "exact_identity_desc"):
            self.assertEqual(formal._order_basis(stage, False), "lexical_ordering")

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

    def test_both_demoted_is_not_currentness_separation(self):
        demoted = sorted(formal._demoted_labels("current"))[0]
        trace = _trace(WRITES, ["f-old", "f-new"], ["f-old", "f-new"], ["f-old"],
                       {"f-old": self._ranked("lexical", applicability=demoted),
                        "f-new": self._ranked(None, applicability=demoted)})
        case = self.classify(trace, {"f-old": UNKNOWN, "f-new": UNKNOWN})
        self.assertFalse(case["conditions"]["temporal_applicability_currentness"])

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

    def test_malformed_verdict_blocks(self):
        result = formal.judged_recall([True, False, False], self.ROWS, 2, 0, malformed_verdicts=1)
        self.assertEqual(result["status"], "blocked")

    def test_other_served_model_is_non_comparable(self):
        result = formal.judged_recall([True, False, False], self.ROWS, 2, 0, served_models=["llama"],
                                      frozen_model="qwen2.5-14b-instruct")
        self.assertEqual(result["status"], "judged_non_comparable_model")
        self.assertIsNone(result["recall_at_k"])

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


V2_FREEZE = formal.FREEZE_DIR / "mesa-formal-v2-freeze.json"
# The runner at 7b041a7, which the v1 freeze binds and where v1 replays run (docs/69
# "Determinism"). Hard-coded: CI checkouts are shallow, so the commit is not readable there.
V1_RUNNER_SHA256 = "58b2fced97a82d762a3cb24325af31173248431837880cd9b19b0a70ae55540c"
# docs/plan-671-evidence-v5.md E5: the classifier and its stage vocabulary are unchanged
# from 7b041a7 (sha256 of the function source, and of each tuple's JSON).
CLASSIFIER_SOURCE_SHA256 = "65961b6f37f74845b0bd01f2d9cd05c0c62631a68bf6f3986caeeb2d7f870302"
CLASSIFIER_CONSTANT_SHA256 = {
    "CURRENTNESS_STAGES": "874135506c0f447342d8f8ec959fe6c89cd4394764136ab0bb82607e732f2a5a",
    "RELEVANCE_STAGES": "86b9ab6d6fffa501ed5f6abbfe1502ec0ff8810498c50db872b64fc8e7a14a2b",
    "RELEVANCE_STAGE_PREFIXES": "05a48646e15c3dd7caf09949c509bf2e9cbca6d7b50170bfc5a2b057a4bb47d9",
    "CONTENT_TIE_STAGES": "eac20539e70b87bec3647dc712aeb661994849914cfa528be433caeb7c2817a4",
    "RECENCY_TIE_STAGES": "46d2df0501cd616010e47fdaf052f9aa801c550e4d54de66b485c5167bd9597b",
    "STAGES": "5a75cbe8fa3a94d615025ca114b993d7f5448f9b3d567c44a0746e496482fe70",
    "CLASSIFIER_VERSION": "280ce3741476a7092aff70a6ef4aee4895bace1623809c63376f9906b9ea3214",
}


class FreezeTests(unittest.TestCase):
    def test_runner_digest_matches_freeze(self):
        # The current runner executes under the v2 freeze; the v1 freeze keeps binding the
        # 7b041a7 runner, so a v1 replay on this runner is refused by design (verify_self).
        self.assertEqual(formal.sha256_file(Path(formal.__file__)), formal.load_freeze(V2_FREEZE)["runner"]["sha256"])
        self.assertEqual(formal.load_freeze()["runner"]["sha256"], V1_RUNNER_SHA256)
        with self.assertRaises(SystemExit):
            formal.verify_self(formal.load_freeze())

    def test_freeze_binds_runtime_baseline_v2_policy_and_contract(self):
        # Historical binding (#669): the v1 freeze binds the Runtime Baseline v2 runtime
        # it executed against; replays run at 7b041a7 (docs/69 "Determinism").
        baseline = json.loads((REFERENCE.parent / "reports" / "runtime" / "baseline-v2.json").read_text())
        frozen = formal.load_freeze()["agent_memory"]
        self.assertEqual(frozen["ranking_policy_version"], baseline["identity"]["ranking"]["active_policy_version"])
        self.assertEqual(frozen["public_contract_version"], baseline["identity"]["public_contract_version"])
        self.assertEqual(frozen["ranking_policy_id"], formal.observed_agent_memory_binding()["ranking_policy_id"])

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


class SuccessorFreezeTests(unittest.TestCase):
    """docs/plan-671-evidence-v5.md E5/E6: mesa-formal-v2 differs from v1 only where listed."""

    CHANGED = {"freeze_id", "owning_issue", "frozen_on", "status", "run_id", "adapter", "runner", "agent_memory"}
    ADDED = {"supersedes", "predictions"}

    def setUp(self):
        self.v1 = formal.load_freeze()
        self.v2 = formal.load_freeze(V2_FREEZE)

    def test_field_differences_are_exhaustive(self):
        self.assertEqual(set(self.v2) - set(self.v1), self.ADDED)
        self.assertEqual(set(self.v1) - set(self.v2), set())
        changed = {key for key in self.v1 if self.v1[key] != self.v2[key]}
        self.assertLessEqual(changed, self.CHANGED)
        for key in set(self.v1) - self.CHANGED:
            self.assertEqual(self.v2[key], self.v1[key], key)
        adapter_changed = {key for key in self.v1["adapter"] if self.v1["adapter"][key] != self.v2["adapter"][key]}
        self.assertEqual(adapter_changed, {"surface", "ranking_policy"})
        self.assertIn("contract 1.5.0", self.v2["adapter"]["surface"])
        self.assertIn("3.3.0", self.v2["adapter"]["ranking_policy"])
        memory_changed = {key for key in self.v1["agent_memory"] if self.v1["agent_memory"][key] != self.v2["agent_memory"][key]}
        self.assertEqual(memory_changed, {"runtime_tree", "ranking_policy_version", "public_contract_version"})
        self.assertEqual(set(self.v2["runner"]), {"path", "sha256"})

    def test_identity_and_supersession(self):
        self.assertEqual(self.v2["freeze_id"], "agent-memory-agentmembench-mesa-formal-v2")
        self.assertEqual(self.v2["owning_issue"], 671)
        self.assertEqual(self.v2["run_id"], "agent_memory_formal_v2_s2027_9170")
        self.assertEqual(self.v2["supersedes"], {
            "freeze_id": self.v1["freeze_id"],
            "path": str(formal.FREEZE_PATH.relative_to(formal.REPO_ROOT)),
            "sha256": formal.sha256_file(formal.FREEZE_PATH),
        })
        self.assertEqual([item["id"] for item in self.v2["deviations"]], ["D1", "D2", "D3", "D4", "D5", "D6"])

    def test_binds_runtime_baseline_v5_policy_and_contract(self):
        declaration = json.loads((REFERENCE.parent / "reports" / "runtime" / "baseline-v5-declaration.json").read_text())
        [delta] = declaration["identity_deltas"]
        self.assertEqual(self.v2["agent_memory"]["ranking_policy_version"], delta["to"])
        live = formal.observed_agent_memory_binding()
        self.assertEqual(self.v2["agent_memory"]["ranking_policy_version"], live["ranking_policy_version"])
        self.assertEqual(self.v2["agent_memory"]["public_contract_version"], live["public_contract_version"])
        self.assertEqual(self.v2["agent_memory"]["ranking_policy_id"], live["ranking_policy_id"])

    def test_predictions_are_frozen_exact_dicts(self):
        predictions = self.v2["predictions"]
        self.assertEqual(predictions["P1"], {"m4_failure_classification.outcomes": {"new_fact": 250},
                                             "phases.conflict.dual_version_rate": 0.0})
        self.assertEqual(predictions["P2"], {"m4_failure_classification.win_basis_counts": {"currentness_mechanism": 250}})
        self.assertEqual(predictions["P3"], {"m4_failure_classification.primary_stage_counts": {},
                                             "m4_failure_classification.unmet_stage_counts": {}})
        self.assertEqual(predictions["P5"], {"m4_failure_classification.upstream_consistency.consistent": True})

    def test_classifier_is_unchanged_from_7b041a7(self):
        import hashlib
        import inspect

        self.assertEqual(hashlib.sha256(inspect.getsource(formal.classify_conflict_case).encode()).hexdigest(),
                         CLASSIFIER_SOURCE_SHA256)
        for name, digest in CLASSIFIER_CONSTANT_SHA256.items():
            self.assertEqual(hashlib.sha256(json.dumps(getattr(formal, name)).encode()).hexdigest(), digest, name)
        self.assertEqual(self.v2["m4_classifier"], self.v1["m4_classifier"])

    def test_report_binding_and_profile_follow_the_selected_freeze(self):
        import inspect

        source = inspect.getsource(formal.run_formal)
        self.assertIn('"profile_id": freeze["freeze_id"]', source)
        self.assertIn("freeze_path.resolve().relative_to(REPO_ROOT)", source)
        self.assertNotIn("FREEZE_PATH", source.split('"""', 2)[2])
        judge = inspect.getsource(formal.judge_raw_report)
        self.assertIn('binding.get("path") != str(freeze_path.resolve().relative_to(REPO_ROOT))', judge)


if __name__ == "__main__":
    unittest.main()
