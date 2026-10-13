"""#779 metric-native leaderboard falsifiers: no score laundering.

Preregistered before the read-only projection implementation. Synthetic
fixtures are not a claim about Agent Memory benchmark performance. Every
fixture carries exact run provenance because a value without a verifiable
run record is never rankable.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from agentmem_ref.evaluation.ui_frontier_leaderboard import (
    CAPABILITY_FAMILIES,
    FrontierProjectionError,
    build_frontier_leaderboard,
    validate_objectives,
)

IDENT = {
    "benchmark_id": "bench", "task_profile": "profile",
    "input_sha256": "abc123", "selection_id": "fixed",
    "sample_count": 20,
}


def run_record(run_id, system_id, kind, revision, *, started_at="2026-10-01T00:00:00+00:00",
               status="complete", ident=None):
    ident = ident or IDENT
    return {
        "run_id": run_id, "status": status,
        "benchmark": {"id": ident["benchmark_id"], "task_profile": ident["task_profile"],
                      "input_sha256": ident["input_sha256"], "dataset_id": "ds",
                      "dataset_revision": "ds-rev", "source_revision": "src", "source_url": "u"},
        "benchmark_profile_id": ident["benchmark_id"] + ":" + ident["task_profile"],
        "execution": {"selection_id": ident["selection_id"],
                      "sample_count": ident["sample_count"], "seed": 1,
                      "selection_method": "frozen", "started_at": started_at},
        "system": {"id": system_id, "kind": kind, "revision": revision,
                   "adapter_id": "adapter", "adapter_revision": "a1",
                   "configuration_digest": "cfg"},
        "evidence": [{"kind": "normalized_run", "uri": f"reports/{run_id}.json"}],
    }


def fixture(*, evidence="same_harness", direction="higher_better", am=0.7,
            peer=0.9, extra=None, peer_kind="external_memory"):
    observations = {
        "agent-memory": {"state": "measured", "value": am,
                         "direction": direction, "unit": "ratio",
                         "denominator": 20, "population": "twenty frozen trials"},
        "mem0-oss": {"state": "measured", "value": peer,
                     "direction": direction, "unit": "ratio",
                     "denominator": 20, "population": "twenty frozen trials"},
    }
    if extra:
        observations.update(extra)
    return {
        "schema_version": "1.0.0",
        "snapshot": {"id": "immutable:snapshot-01", "as_of": "2026-10-07",
                     "evidence_revision": "deadbeef", "repository_is_newer": False},
        "aggregate_score": "not_defined",
        "metrics": [{"metric_key": "bench:profile:retrieval:recall_at_5",
                     "benchmark_profile_id": "bench:profile",
                     "dimension": "retrieval", "metric_id": "recall_at_5"}],
        "published_references": [{"system": "vendor", "signals": {"x": 0.999},
                                  "eligible_for_numeric_delta": False}],
        "runs": [
            run_record("r-am", "agent-memory", "agent_memory", "am:sha"),
            run_record("r-mem0", "mem0-oss", peer_kind, "mem0:sha"),
        ],
        "comparison_sets": [{
            "comparison_set_id": "comparison:exact-frozen-20",
            "evidence_class": evidence, "comparison_state": "exact",
            "eligible_for_numeric_delta": True,
            "comparison_identity": dict(IDENT),
            "systems": [
                {"id": "agent-memory", "kind": "agent_memory",
                 "revision": "am:sha", "run_id": "r-am", "run_status": "complete"},
                {"id": "mem0-oss", "kind": peer_kind,
                 "revision": "mem0:sha", "run_id": "r-mem0", "run_status": "complete"},
            ],
            "dimensions": {"retrieval": {"rows": [{
                "metric_id": "recall_at_5", "systems": observations,
            }]}}
        }],
    }


def add_system(obj, system_id, kind, value, *, revision=None, run_id=None,
               started_at="2026-10-01T00:00:00+00:00"):
    revision = revision or f"{system_id}:sha"
    run_id = run_id or f"r-{system_id}"
    comparison = obj["comparison_sets"][0]
    comparison["systems"].append({"id": system_id, "kind": kind, "revision": revision,
                                  "run_id": run_id, "run_status": "complete"})
    comparison["dimensions"]["retrieval"]["rows"][0]["systems"][system_id] = {
        "state": "measured", "value": value, "direction": "higher_better",
        "unit": "ratio", "denominator": 20, "population": "twenty frozen trials",
    }
    obj["runs"].append(run_record(run_id, system_id, kind, revision, started_at=started_at))


def observations(obj):
    return obj["comparison_sets"][0]["dimensions"]["retrieval"]["rows"][0]["systems"]


class FrontierProjectionTests(unittest.TestCase):
    def test_higher_is_better_and_gap_to_peer(self):
        row = build_frontier_leaderboard(fixture())["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "ranked")
        self.assertEqual(row["leader"]["system_id"], "mem0-oss")
        self.assertAlmostEqual(row["gap_to_leader_native"], 0.2)
        self.assertAlmostEqual(row["gap_percentage_points"], 20.0)
        self.assertEqual(row["agent_memory"]["rank"], 2)
        self.assertEqual([x["system_id"] for x in row["ranking"]], ["mem0-oss", "agent-memory"])
        self.assertEqual(row["authority_effect"], "none")
        self.assertIsNone(row["adequacy"]["target"])
        self.assertEqual(row["competitive_state"], "behind_external")
        self.assertEqual(row["leader_state"], "sole")
        self.assertEqual(row["reasons"], [])
        self.assertTrue(all(x["provenance"]["verified"] for x in row["ranking"]))

    def test_lower_is_better_and_zero_target(self):
        for direction in ("lower_better", "zero_target"):
            with self.subTest(direction=direction):
                row = build_frontier_leaderboard(
                    fixture(direction=direction, am=0.8, peer=0.4)
                )["leaderboards"][0]
                self.assertEqual(row["leader"]["system_id"], "mem0-oss")
                self.assertAlmostEqual(row["gap_to_leader_native"], 0.4)

    def test_tie_receives_shared_rank_and_zero_measured_gap(self):
        row = build_frontier_leaderboard(fixture(am=0.7, peer=0.7))["leaderboards"][0]
        self.assertEqual(row["agent_memory"]["rank"], 1)
        self.assertEqual([x["rank"] for x in row["ranking"]], [1, 1])
        self.assertEqual(row["gap_to_leader_native"], 0.0)
        self.assertEqual(row["leader_state"], "tied")
        self.assertEqual(row["co_leaders"], ["agent-memory", "mem0-oss"])
        self.assertEqual(row["competitive_state"], "tied_leader")

    def test_alphabetically_earlier_tied_peer_is_not_a_sole_leader(self):
        obj = fixture(am=0.9, peer=0.5)
        add_system(obj, "aaa-system", "external_memory", 0.9)
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["leader_state"], "tied")
        self.assertEqual(row["co_leaders"], ["aaa-system", "agent-memory"])
        self.assertEqual(row["competitive_state"], "tied_leader")
        self.assertEqual(row["gap_to_leader_native"], 0.0)
        self.assertEqual([x["rank"] for x in row["ranking"]], [1, 1, 3])

    def test_published_reference_cannot_join_numeric_frontier(self):
        obj = fixture()
        obj["published_references"].append({
            "system": "fantastic-vendor", "signals": {"acc": 0.9999},
            "eligible_for_numeric_delta": False
        })
        out = build_frontier_leaderboard(obj)
        row = out["leaderboards"][0]
        self.assertEqual(row["leader"]["system_id"], "mem0-oss")
        self.assertEqual(len(out["published_references"]), 2)
        self.assertTrue(all(p["ranked"] is False and p["eligible_for_numeric_delta"] is False
                            for p in out["published_references"]))
        self.assertIn("fantastic-vendor", out["external_competitors"]["published_only"])
        self.assertNotIn("fantastic-vendor", out["external_competitors"]["same_harness_measured"])
        obj["comparison_sets"][0]["evidence_class"] = "published_reference"
        result = build_frontier_leaderboard(obj)
        self.assertEqual(result["leaderboards"][0]["ranking_state"], "non_comparable")
        self.assertIsNone(result["leaderboards"][0]["gap_to_leader_native"])
        self.assertIn("evidence_class:published_reference", result["leaderboards"][0]["reasons"])

    def test_same_profile_alone_is_not_an_accepted_comparison(self):
        row = build_frontier_leaderboard(fixture(evidence="same_profile"))["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "non_comparable")
        self.assertIsNone(row["leader"])
        self.assertIsNone(row["competitive_state"])

    def test_unknown_evidence_class_is_refused(self):
        row = build_frontier_leaderboard(fixture(evidence="totally_comparable"))["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "non_comparable")
        self.assertIn("unknown_evidence_class", row["reasons"])

    def test_missing_peer_is_not_zero_gap_or_certified_lead(self):
        obj = fixture()
        del observations(obj)["mem0-oss"]
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "no_peer")
        self.assertIsNone(row["gap_to_leader_native"])
        self.assertIsNone(row["leader"])
        self.assertIsNone(row["competitive_state"])
        self.assertAlmostEqual(row["agent_memory"]["value"], 0.7)

    def test_absent_agent_memory_is_unknown_not_deficit(self):
        obj = fixture()
        del observations(obj)["agent-memory"]
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "agent_memory_missing")
        self.assertIsNone(row["gap_to_leader_native"])

    def test_boolean_infinity_nan_and_blocked_are_not_scores(self):
        for bad in (True, float("inf"), float("-inf"), float("nan"), "0.9"):
            with self.subTest(bad=repr(bad)):
                row = build_frontier_leaderboard(fixture(am=bad))["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "agent_memory_missing")
                self.assertIsNone(row["gap_to_leader_native"])
        obj = fixture()
        observations(obj)["agent-memory"] = {"state": "blocked", "direction": "higher_better"}
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "agent_memory_missing")
        self.assertIsNone(row["gap_to_leader_native"])

    def test_value_present_but_state_not_measured_is_not_a_score(self):
        for state in ("blocked", "not_run", "evidence_gap", "unsupported", None):
            with self.subTest(state=state):
                obj = fixture()
                observations(obj)["mem0-oss"]["state"] = state
                row = build_frontier_leaderboard(obj)["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "no_peer")
                self.assertIsNone(row["leader"])

    def test_all_boolean_measurements_are_not_rankable_not_unmeasured(self):
        obj = fixture(am=True, peer=False)
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "not_rankable")
        self.assertIsNone(row["leader"])
        obj = fixture()
        for sid in ("agent-memory", "mem0-oss"):
            observations(obj)[sid] = {"state": "not_measured"}
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "not_measured")

    def test_ratio_out_of_range_refuses_the_whole_row(self):
        for bad in (1.5, -0.1):
            with self.subTest(bad=bad):
                row = build_frontier_leaderboard(fixture(peer=bad))["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIsNone(row["leader"])
                self.assertTrue(any(r.startswith("invalid_observation:mem0-oss") for r in row["reasons"]))

    def test_direction_and_units_mismatch_refuse_ranking(self):
        for change in (
            {"direction": "lower_better"}, {"unit": "ms"},
            {"denominator": 99}, {"population": "different trial selection"},
        ):
            with self.subTest(change=change):
                obj = fixture()
                observations(obj)["mem0-oss"].update(change)
                row = build_frontier_leaderboard(obj)["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIsNone(row["gap_to_leader_native"])
                self.assertTrue(row["reasons"])

    def test_missing_native_metadata_refuses_ranking(self):
        for change in (
            {"unit": None}, {"unit": ""}, {"population": None},
            {"population": ""}, {"denominator": None},
            {"denominator": 0}, {"denominator": -1},
            {"denominator": True}, {"denominator": float("nan")},
        ):
            with self.subTest(change=change):
                obj = fixture()
                observations(obj)["mem0-oss"].update(change)
                row = build_frontier_leaderboard(obj)["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIsNone(row["gap_to_leader_native"])
                self.assertIsNone(row["leader"])

    def test_descriptive_metric_never_ranks(self):
        row = build_frontier_leaderboard(
            fixture(direction="descriptive", am=1, peer=0)
        )["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "not_rankable")
        self.assertIsNone(row["leader"])

    def test_metric_without_comparison_set_remains_in_coverage(self):
        obj = fixture()
        obj["metrics"].append({
            "metric_key": "other:task:governance:no_leak",
            "benchmark_profile_id": "other:task",
            "dimension": "governance", "metric_id": "no_leak",
        })
        out = build_frontier_leaderboard(obj)
        unranked = [x for x in out["metric_coverage"] if x["metric_key"].startswith("other:")]
        self.assertEqual(len(unranked), 1)
        self.assertEqual(unranked[0]["state"], "no_accepted_comparison")
        self.assertEqual(unranked[0]["best_ranking_state"], "no_comparison_row")
        self.assertIsNone(unranked[0]["gap_to_leader_native"])
        self.assertEqual(out["aggregate_score"], None)

    def test_ineligible_same_harness_does_not_claim_accepted_coverage(self):
        obj = fixture()
        comparison = obj["comparison_sets"][0]
        comparison["comparison_state"] = "incompatible_protocol"
        out = build_frontier_leaderboard(obj)
        self.assertEqual(out["leaderboards"][0]["ranking_state"], "non_comparable")
        self.assertEqual(out["metric_coverage"][0]["state"], "no_accepted_comparison")
        self.assertIsNone(out["metric_coverage"][0]["gap_to_leader_native"])

    def test_missing_agent_or_peer_does_not_claim_ranked_coverage(self):
        for excluded in ("agent-memory", "mem0-oss"):
            with self.subTest(excluded=excluded):
                obj = fixture()
                del observations(obj)[excluded]
                out = build_frontier_leaderboard(obj)
                self.assertEqual(out["metric_coverage"][0]["state"], "no_accepted_comparison")

    def test_deterministic_and_does_not_change_catalog(self):
        obj = fixture()
        before = deepcopy(obj)
        a = build_frontier_leaderboard(obj)
        self.assertEqual(a, build_frontier_leaderboard(obj))
        self.assertEqual(obj, before)
        self.assertEqual(a["snapshot_id"], "immutable:snapshot-01")
        self.assertEqual(a["snapshot"]["evidence_revision"], "deadbeef")

    def test_repeated_system_run_in_same_set_refused(self):
        obj = fixture()
        obj["comparison_sets"][0]["systems"].append(deepcopy(obj["comparison_sets"][0]["systems"][0]))
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(obj)

    def test_duplicate_comparison_set_or_run_identity_refused(self):
        obj = fixture()
        obj["comparison_sets"].append(deepcopy(obj["comparison_sets"][0]))
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(obj)
        obj = fixture()
        obj["runs"].append(deepcopy(obj["runs"][0]))
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(obj)

    def test_missing_comparison_identity_never_fabricates_ranking(self):
        obj = fixture()
        obj["comparison_sets"][0]["comparison_identity"]["input_sha256"] = None
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "non_comparable")
        self.assertIn("comparison_identity_incomplete", row["reasons"])

    def test_malformed_structure_fails_closed(self):
        obj = fixture()
        del obj["comparison_sets"][0]["comparison_set_id"]
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(obj)
        obj = fixture()
        del obj["comparison_sets"][0]["dimensions"]["retrieval"]["rows"][0]["metric_id"]
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(obj)
        obj = fixture()
        obj["aggregate_score"] = 0.93
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(obj)
        obj = fixture()
        observations(obj)["ghost-system"] = dict(observations(obj)["mem0-oss"])
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(obj)

    # --- provenance -------------------------------------------------------

    def test_value_without_run_record_is_not_rankable(self):
        obj = fixture()
        obj["runs"] = [r for r in obj["runs"] if r["run_id"] != "r-mem0"]
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "non_comparable")
        self.assertIsNone(row["leader"])
        self.assertIn("provenance_missing:mem0-oss", row["reasons"])
        peer = next(s for s in row["systems_observed"] if s["system_id"] == "mem0-oss")
        self.assertFalse(peer["eligible"])

    def test_run_identity_mismatch_is_not_rankable(self):
        for field, path in (
            ("input_sha256", ("benchmark", "input_sha256")),
            ("selection_id", ("execution", "selection_id")),
            ("sample_count", ("execution", "sample_count")),
            ("task_profile", ("benchmark", "task_profile")),
            ("benchmark_id", ("benchmark", "id")),
        ):
            with self.subTest(field=field):
                obj = fixture()
                run = next(r for r in obj["runs"] if r["run_id"] == "r-mem0")
                run[path[0]][path[1]] = "something-else"
                row = build_frontier_leaderboard(obj)["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIn(f"run_identity_mismatch:mem0-oss:{field}", row["reasons"])
                self.assertIsNone(row["gap_to_leader_native"])

    def test_revision_conflict_between_set_and_run_is_not_rankable(self):
        obj = fixture()
        obj["comparison_sets"][0]["systems"][0]["revision"] = "am:other"
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "non_comparable")
        self.assertIn("run_revision_mismatch:agent-memory", row["reasons"])

    def test_incomplete_run_is_not_rankable(self):
        for status in ("failed", "partial", "running", None):
            with self.subTest(status=status):
                obj = fixture()
                next(r for r in obj["runs"] if r["run_id"] == "r-am")["status"] = status
                row = build_frontier_leaderboard(obj)["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIn("run_not_complete:agent-memory", row["reasons"])

    # --- controls versus market competitors --------------------------------

    def test_lead_over_controls_only_is_not_a_market_victory(self):
        obj = fixture(am=0.9, peer=0.5, peer_kind="lexical")
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "ranked")
        self.assertEqual(row["competitive_state"], "leading_vs_controls_only")
        self.assertEqual(row["peer_population"]["external_competitors"], [])
        self.assertEqual(row["peer_population"]["controls"], ["mem0-oss"])
        self.assertFalse(row["peer_population"]["external_competitor_ranked"])

    def test_lead_with_unmeasured_external_competitor_is_controls_only(self):
        obj = fixture(am=0.9, peer=0.5, peer_kind="lexical")
        add_system(obj, "vendor-x", "external_memory", 0.95)
        observations(obj)["vendor-x"] = {"state": "blocked", "direction": "higher_better"}
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["competitive_state"], "leading_vs_controls_only")
        self.assertEqual(row["peer_population"]["external_competitors"], ["vendor-x"])
        self.assertFalse(row["peer_population"]["external_competitor_ranked"])
        self.assertNotIn("vendor-x", [x["system_id"] for x in row["ranking"]])

    def test_control_leading_agent_memory_is_behind_control(self):
        obj = fixture(am=0.6, peer=0.5)
        add_system(obj, "bm25", "lexical", 0.8)
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["competitive_state"], "behind_control")
        self.assertEqual(row["leader"]["role"], "control")
        self.assertAlmostEqual(row["gap_to_leader_native"], 0.2)

    # --- repeated runs and chronology -------------------------------------

    def _lineage_fixture(self):
        obj = fixture(am=0.7)
        older = deepcopy(obj["comparison_sets"][0])
        older["comparison_set_id"] = "comparison:exact-frozen-20:older"
        older["comparison_identity"]["task_profile"] = "profile-old"
        older["systems"][0]["revision"] = "am:old"
        older["systems"][0]["run_id"] = "r-am-old"
        older["systems"][1]["run_id"] = "r-mem0-old"
        observations({"comparison_sets": [older]})["agent-memory"]["value"] = 0.5
        ident = dict(IDENT, task_profile="profile-old")
        obj["runs"].append(run_record("r-am-old", "agent-memory", "agent_memory", "am:old",
                                      started_at="2026-09-01T00:00:00+00:00", ident=ident))
        obj["runs"].append(run_record("r-mem0-old", "mem0-oss", "external_memory", "mem0:sha",
                                      started_at="2026-09-01T00:00:00+00:00", ident=ident))
        obj["comparison_sets"].append(older)
        return obj

    def test_repeated_agent_memory_run_marks_older_set_superseded(self):
        out = build_frontier_leaderboard(self._lineage_fixture())
        by_set = {row["comparison_set_id"]: row for row in out["leaderboards"]}
        new = by_set["comparison:exact-frozen-20"]
        old = by_set["comparison:exact-frozen-20:older"]
        self.assertEqual(old["currency"]["state"], "superseded")
        self.assertEqual(old["currency"]["superseded_by"], "comparison:exact-frozen-20")
        self.assertEqual(new["currency"]["state"], "current")
        self.assertEqual(new["currency"]["lineage_id"], old["currency"]["lineage_id"])
        self.assertEqual(old["ranking_state"], "ranked")
        self.assertEqual(out["summary"]["currency_states"]["superseded"], 1)

    def test_newer_unaccepted_evidence_is_flagged_not_ranked(self):
        obj = self._lineage_fixture()
        newer = next(c for c in obj["comparison_sets"] if c["comparison_set_id"].endswith(":older"))
        newer["evidence_class"] = "same_profile"
        for run in obj["runs"]:
            if run["run_id"] in ("r-am-old", "r-mem0-old"):
                run["execution"]["started_at"] = "2026-12-01T00:00:00+00:00"
        out = build_frontier_leaderboard(obj)
        by_set = {row["comparison_set_id"]: row for row in out["leaderboards"]}
        current = by_set["comparison:exact-frozen-20"]
        self.assertEqual(current["ranking_state"], "ranked")
        self.assertEqual(current["currency"]["state"], "newer_unaccepted_evidence")
        self.assertEqual(current["currency"]["unaccepted_sibling_revisions"], ["am:old"])
        self.assertEqual(by_set["comparison:exact-frozen-20:older"]["ranking_state"], "non_comparable")

    def test_unordered_repeated_runs_are_undetermined_not_current(self):
        obj = self._lineage_fixture()
        for run in obj["runs"]:
            if run["run_id"] == "r-am-old":
                run["execution"]["started_at"] = None
        out = build_frontier_leaderboard(obj)
        states = {row["comparison_set_id"]: row["currency"]["state"] for row in out["leaderboards"]}
        self.assertEqual(set(states.values()), {"undetermined"})

    def test_different_structural_identity_is_not_a_lineage(self):
        obj = self._lineage_fixture()
        older = next(c for c in obj["comparison_sets"] if c["comparison_set_id"].endswith(":older"))
        older["comparison_identity"]["input_sha256"] = "other-input"
        for run in obj["runs"]:
            if run["run_id"] in ("r-am-old", "r-mem0-old"):
                run["benchmark"]["input_sha256"] = "other-input"
        out = build_frontier_leaderboard(obj)
        states = {row["comparison_set_id"]: row["currency"]["state"] for row in out["leaderboards"]}
        self.assertEqual(set(states.values()), {"current"})

    # --- objectives registry ------------------------------------------------

    def _registry(self):
        return {
            "schema_version": "1.0.0",
            "claims_policy": {"universal_score": None, "authority_effect": "none"},
            "capability_groups": dict(CAPABILITY_FAMILIES),
            "objectives": [
                {"id": "B01", "group": "B", "capability": "deep recall",
                 "benchmark": "bench profile", "metric": "recall_at_5",
                 "source_kind": "ledger", "owners": [673, 644],
                 "deficit_selector": "sel-1", "release_gate": "replay"},
                {"id": "G01", "group": "G", "capability": "qa",
                 "benchmark": "LongMemEval end-to-end QA", "metric": "judged_accuracy",
                 "source_kind": "blocked", "owners": [694], "unmeasured_state": "blocked_credential"},
            ],
        }

    def test_registry_absent_degrades_cleanly_with_nine_families(self):
        out = build_frontier_leaderboard(fixture())
        self.assertEqual(out["objectives"]["state"], "absent")
        self.assertEqual(sorted(out["objectives"]["families"]), list("ABCDEFGHI"))
        self.assertEqual(out["objectives"]["items"], [])
        self.assertEqual(out["leaderboards"][0]["objectives"], [])

    def test_draft_registry_links_ownership_without_touching_rank(self):
        plain = build_frontier_leaderboard(fixture())
        out = build_frontier_leaderboard(fixture(), objectives=self._registry(),
                                         objectives_status="draft", objectives_source="pr-768")
        self.assertEqual(out["objectives"]["state"], "draft")
        self.assertEqual(out["objectives"]["source"], "pr-768")
        self.assertEqual(len(out["objectives"]["sha256"]), 64)
        self.assertEqual(sorted(out["objectives"]["families"]), list("ABCDEFGHI"))
        self.assertEqual(out["objectives"]["families_without_objective"],
                         ["A", "C", "D", "E", "F", "H", "I"])
        row = out["leaderboards"][0]
        self.assertEqual(row["objectives"], [{"id": "B01", "group": "B",
                                              "owners": ["#673", "#644"], "linkage": "label_match"}])
        items = {i["id"]: i for i in out["objectives"]["items"]}
        self.assertEqual(items["B01"]["linked_metric_keys"], [row["metric_key"]])
        self.assertEqual(items["G01"]["linked_metric_keys"], [])
        for key in ("ranking_state", "leader", "agent_memory", "gap_to_leader_native",
                    "competitive_state", "ranking"):
            self.assertEqual(row[key], plain["leaderboards"][0][key])
        self.assertIsNone(out["aggregate_score"])

    def test_registry_without_status_or_with_unknown_status_refused(self):
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(fixture(), objectives=self._registry())
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(fixture(), objectives=self._registry(),
                                       objectives_status="approved")

    def test_invalid_registry_fails_closed(self):
        bad_cases = []
        reg = self._registry(); del reg["capability_groups"]["I"]; bad_cases.append(reg)
        reg = self._registry(); reg["capability_groups"]["J"] = "extra"; bad_cases.append(reg)
        reg = self._registry(); reg["claims_policy"]["universal_score"] = 0.5; bad_cases.append(reg)
        reg = self._registry(); reg["objectives"][0]["owners"] = []; bad_cases.append(reg)
        reg = self._registry(); reg["objectives"][0]["score"] = 0.99; bad_cases.append(reg)
        reg = self._registry(); reg["objectives"].append(dict(reg["objectives"][0])); bad_cases.append(reg)
        reg = self._registry(); reg["objectives"][0]["group"] = "Z"; bad_cases.append(reg)
        bad_cases.append([])
        for index, reg in enumerate(bad_cases):
            with self.subTest(case=index):
                with self.assertRaises(FrontierProjectionError):
                    validate_objectives(reg)
                with self.assertRaises(FrontierProjectionError):
                    build_frontier_leaderboard(fixture(), objectives=reg, objectives_status="draft")


if __name__ == "__main__":
    unittest.main()
