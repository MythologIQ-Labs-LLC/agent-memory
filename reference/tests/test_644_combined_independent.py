"""validation(#644): independent adversarial checks of the combined receipt + indexed audit.

Local validation branch only. Each assertion states an intended invariant; a
failure here is a finding against the exact candidate SHA, not a test to relax.
"""
from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest
from collections.abc import Mapping

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.recall_control import ControlledRecallPlanner, DeterministicRecallController
from agentmem_ref.runtime import typed_proposition as typed
from agentmem_ref.runtime.adapter import DECLARED_TEMPORAL_KEY
from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
from agentmem_ref.runtime.recall_observation_receipt import (
    RecallObservationReceipt,
    capture_recall_observation,
)
from agentmem_ref.runtime.temporal_intent import parse_time

SUBJECT, ATTRIBUTE = "Orrin gateway", "region"
SLOT = typed.typed_slot(SUBJECT, ATTRIBUTE)
QUERY = f"{SUBJECT} {ATTRIBUTE}"
PARAPHRASE = "Since last week the zone moved to Lisbon"


def _prop(value, subject=SUBJECT, attribute=ATTRIBUTE, **flags):
    return {"subject": subject, "attribute": attribute, "value": value,
            "assertion": flags.pop("assertion", "state"),
            "cardinality": flags.pop("cardinality", "single"), "flags": flags}


def _evidence(scope="project:a", tenant="tenant:c644"):
    skill = pm.SkillArtifact(
        skill_id="skill:c644", version=1, purpose="c644", scope=scope,
        isolation_domain_refs=(tenant, scope), required_isolation_domain_refs=(tenant, scope),
        procedure_markdown="# v\nok", provenance_refs=("evidence:c644",))
    return pm.evidence_for(skill)


def _temporal_obstacle(fact) -> bool:
    """The candidate's declared per-fact temporal rule (doc 81), restated independently."""
    declared = (fact.attributes or {}).get(DECLARED_TEMPORAL_KEY) or {}
    if declared.get("valid_until"):
        return True
    if not declared.get("valid_from"):
        return False
    starts, recorded = parse_time(declared.get("valid_from")), parse_time(fact.created_at)
    return starts is None or recorded is None or starts > recorded


def full_scan_census(adapter, slots, admitted_refs, context):
    """Oracle: e002536's all_facts enumeration with the same per-fact predicates."""
    counters = {slot: {"eligible_unretrieved": 0, "qualified_counter_evidence": 0,
                       "declared_temporal_boundary": 0} for slot in sorted(slots)}
    for fact in adapter._substrate.all_facts():
        if fact.is_transaction_expired or adapter._admission_refusal(fact, context) is not None:
            continue
        stored = adapter.write_semantics(fact.uuid, context)
        record = stored.get("typed_proposition") if isinstance(stored, dict) else None
        if not isinstance(record, dict) or record.get("slot") not in counters:
            continue
        slot = record["slot"]
        if _temporal_obstacle(fact):
            counters[slot]["declared_temporal_boundary"] += 1
        if (record.get("basis") != typed.CALLER_DECLARED or stored.get("typed_ineligible_reasons")
                or not isinstance(record.get("flags"), dict) or any(record["flags"].values())):
            counters[slot]["qualified_counter_evidence"] += 1
        if fact.uuid not in admitted_refs:
            counters[slot]["eligible_unretrieved"] += 1
    return counters


class _Base(unittest.TestCase):
    tenant = "tenant:c644"

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = self._dir.name + "/m"
        self.memory = self.open()

    def tearDown(self):
        self.memory.close()
        self._dir.cleanup()

    def open(self, scope="project:a", tenant=None):
        return AgentMemory.open(self.root, tenant=tenant or self.tenant, actor_id="agent:c644",
                                scope=scope, purpose="c644")

    def reopen(self, scope="project:a"):
        self.memory.close()
        self.memory = self.open(scope)

    def planner(self):
        return ControlledRecallPlanner(self.memory.runtime.adapter, controller=DeterministicRecallController())

    def recall(self, query=QUERY, logical_memory_refs=()):
        planner = self.planner()
        context = self.memory._handle_recall_context()
        result = self.memory.runtime.durable_runtime.run_governed_read(
            lambda: planner.recall(query, context, logical_memory_refs=logical_memory_refs))
        return planner, context, result

    def observe(self, planner, context, result, slots=(SLOT,)):
        return self.memory.runtime.durable_runtime.run_governed_read(
            lambda: planner.observe_persisted_typed_coverage(
                result, context, needs=tuple(CoverageNeed(slot) for slot in slots)))

    def seed_conflict(self):
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        self.memory.remember("memory:b", f"{QUERY} is Bergen", proposition=_prop("Bergen"))


# ---------------------------------------------------------------- receipt capture and tamper detection

class ReceiptCapture(_Base):
    def test_fresh_results_verify_across_route_shapes(self):
        """No false tamper on untampered results: empty, lexical, exact-identity, refused, budgeted."""
        self.seed_conflict()
        self.memory.remember("memory:c", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertTrue(self.memory.forget("memory:c")["committed"])
        for query, refs in ((QUERY, ()), ("nothing matches this", ()), (QUERY, ("memory:a",)),
                            ("", ("memory:a", "memory:b", "memory:missing")), (QUERY * 20, ())):
            with self.subTest(query=query[:20], refs=refs):
                _, _, result = self.recall(query, refs)
                self.assertIsInstance(result.observation_receipt, RecallObservationReceipt)
                self.assertTrue(result.observation_unchanged())

    def test_receipt_survives_planner_return_unchanged_by_caller_lists(self):
        """Capture is a defensive copy: the receipt keeps the planner-time view."""
        self.seed_conflict()
        _, _, result = self.recall()
        admitted = tuple(result.recall.admitted)
        result.recall.admitted.clear()
        self.assertEqual(result.observation_receipt.admitted_refs, admitted)
        self.assertFalse(result.observation_unchanged())

    def test_every_bound_field_mutation_is_detected(self):
        self.seed_conflict()
        self.memory.remember("memory:c", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertTrue(self.memory.forget("memory:c")["committed"])
        mutations = {
            "candidates_drop": lambda r: r.recall.candidates.pop(),
            "candidates_add": lambda r: r.recall.candidates.append("ref-9999"),
            "admitted_drop": lambda r: r.recall.admitted.pop(),
            "ranked_swap": lambda r: r.recall.ranked_admitted.reverse(),
            "route_count_zero": lambda r: r.route_candidate_counts.update({k: 0 for k in r.route_candidate_counts}),
            "route_count_new_key": lambda r: r.route_candidate_counts.update({"extra": 0}),
            "routes_executed": lambda r: setattr(r.recall, "routes_executed", ()),
            "query": lambda r: setattr(r.recall, "query", "other"),
            "refusal_reason": lambda r: r.recall.refusals.update({k: "x" for k in r.recall.refusals}),
            "refusal_drop": lambda r: r.recall.refusals.clear(),
            "policy": lambda r: setattr(r.recall, "policy_version", "forged"),
            "mode": lambda r: setattr(r.recall, "admission_mode", "historical_evidence"),
            "evaluated_at": lambda r: setattr(r.recall, "evaluated_at", "2001-01-01T00:00:00Z"),
            "plan": lambda r: setattr(r, "plan", dataclasses.replace(
                r.plan, evidence_sufficiency_target=r.plan.evidence_sufficiency_target + 1)),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                _, _, result = self.recall()
                self.assertTrue(result.recall.refusals, "scenario needs a refused candidate")
                self.assertTrue(result.observation_unchanged())
                mutate(result)
                self.assertFalse(result.observation_unchanged())

    def test_unbound_v6_stop_signal_mutation(self):
        """FINDING probe: evidence_sufficiency_met / stop_reason are outside the receipt."""
        self.seed_conflict()
        _, _, result = self.recall()
        result.evidence_sufficiency_met = not result.evidence_sufficiency_met
        result.stop_reason = "evidence_target_met"
        self.assertTrue(result.observation_unchanged(),
                        "documented scope: the v6 count signal is not receipt-bound")

    def test_unkeyed_receipt_can_be_recomputed_by_caller(self):
        """Content hash is change detection, not attestation: a caller can re-mint it."""
        self.seed_conflict()
        planner, context, result = self.recall()
        result.recall.admitted.pop()
        result.recall.ranked_admitted[:] = [r for r in result.recall.ranked_admitted if r in result.recall.admitted]
        self.assertFalse(result.observation_unchanged())
        old = result.observation_receipt
        forged = capture_recall_observation(
            query=result.recall.query, reader_domain_refs=tuple(context.target_domain_refs),
            principal_ref=context.principal_ref, project_ref=context.project_ref, purpose=context.purpose,
            task_ref=context.task_ref, controller_ref=old.controller_ref, admission_policy=old.admission_policy,
            admission_mode=old.admission_mode, evaluated_at=old.evaluated_at,
            candidates=result.recall.candidates, admitted=result.recall.admitted,
            ranked=result.recall.ranked_admitted, route_observations=old.routes,
            observed_route_counts=result.route_candidate_counts, plan=result.plan.to_dict(),
            refusals=result.recall.refusals)
        result.observation_receipt = forged
        self.assertTrue(result.observation_unchanged())
        self.assertFalse(forged.can_stop)
        self.assertIsNone(forged.state_revision)

    def test_receipt_never_claims_signature_revision_closure_or_authority(self):
        self.seed_conflict()
        _, _, result = self.recall()
        receipt = result.observation_receipt
        public = receipt.to_dict()
        self.assertEqual((public["state_revision"], public["snapshot_attested"], public["slot_closure_attested"],
                          public["can_stop"], public["authority_effect"]), (None, False, False, False, "none"))
        for forged in ({"can_stop": True}, {"snapshot_attested": True}, {"slot_closure_attested": True},
                       {"state_revision": "rev-1"}, {"authority_effect": "stop"}):
            with self.subTest(forged=forged):
                with self.assertRaises(ValueError):
                    dataclasses.replace(receipt, **forged)
        text = json.dumps(public).lower()
        for word in ("signature", "signed", "attested\": true", "verified"):
            self.assertNotIn(word, text)

    def test_public_serialization_hides_refused_and_hidden_identities(self):
        self.seed_conflict()
        self.memory.remember("memory:c", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertTrue(self.memory.forget("memory:c")["committed"])
        self.memory.close()
        other = self.open("project:b")
        other.remember("memory:z", f"{QUERY} is Gdansk", proposition=_prop("Gdansk"))
        other.close()
        self.memory = self.open()
        _, _, result = self.recall()
        hidden = set(result.recall.candidates) - set(result.recall.admitted)
        self.assertTrue(hidden)
        text = json.dumps(result.observation_receipt.to_dict())
        for ref in hidden:
            self.assertNotIn(ref, text)
        self.assertEqual(result.observation_receipt.to_dict()["candidate_count"], len(result.recall.candidates))


class ReceiptMalformedInputs(_Base):
    def _check(self, result):
        try:
            return result.observation_unchanged()
        except Exception as exc:  # the invariant: fail closed WITHOUT an uncaught exception
            self.fail(f"uncaught {type(exc).__name__}: {exc}")

    def test_receipt_method_rejects_hostile_mappings_directly(self):
        self.seed_conflict()
        _, _, result = self.recall()

        class Exploding(Mapping):
            def __getitem__(self, key): raise RuntimeError("boom")
            def __iter__(self): raise RuntimeError("boom")
            def __len__(self): return 1

        rec = result.recall
        base = dict(candidates=rec.candidates, admitted=rec.admitted, ranked=rec.ranked_admitted,
                    route_counts=result.route_candidate_counts, routes_executed=rec.routes_executed,
                    query=rec.query, plan=result.plan.to_dict(), refusals=rec.refusals,
                    policy_version=rec.policy_version, admission_mode=rec.admission_mode,
                    evaluated_at=rec.evaluated_at)
        self.assertTrue(result.observation_receipt.matches_mutable_result(**base))
        for key in ("route_counts", "refusals", "plan"):
            with self.subTest(field=key):
                try:
                    outcome = result.observation_receipt.matches_mutable_result(**{**base, key: Exploding()})
                except Exception as exc:
                    self.fail(f"uncaught {type(exc).__name__}")
                self.assertFalse(outcome)

    def test_malformed_counters_and_mappings_fail_closed(self):
        self.seed_conflict()

        class Exploding(Mapping):
            def __getitem__(self, key): raise RuntimeError("boom")
            def __iter__(self): raise RuntimeError("boom")
            def __len__(self): return 1

        deep: list = []
        node = deep
        for _ in range(5000):
            node.append([])
            node = node[0]
        cases = {
            "counts_none": lambda r: setattr(r, "route_candidate_counts", None),
            "counts_list": lambda r: setattr(r, "route_candidate_counts", [("lexical", 1)]),
            "counts_bool": lambda r: r.route_candidate_counts.update({k: True for k in r.route_candidate_counts}),
            "counts_negative": lambda r: r.route_candidate_counts.update({k: -1 for k in r.route_candidate_counts}),
            "counts_float": lambda r: r.route_candidate_counts.update({k: 1.0 for k in r.route_candidate_counts}),
            "counts_int_key": lambda r: r.route_candidate_counts.update({1: 1}),
            "counts_exploding": lambda r: setattr(r, "route_candidate_counts", Exploding()),
            "refusals_none": lambda r: setattr(r.recall, "refusals", None),
            "refusals_exploding": lambda r: setattr(r.recall, "refusals", Exploding()),
            "candidates_none": lambda r: setattr(r.recall, "candidates", None),
            "candidates_int": lambda r: setattr(r.recall, "candidates", 7),
            "query_bytes": lambda r: setattr(r.recall, "query", b"q"),
            "plan_object": lambda r: setattr(r, "plan", object()),
            "recall_none": lambda r: setattr(r, "recall", None),
            "receipt_garbage": lambda r: setattr(r, "observation_receipt", "garbage"),
            "deep_refusals": lambda r: setattr(r.recall, "refusals", {"x": deep}),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                _, _, result = self.recall()
                mutate(result)
                self.assertFalse(self._check(result))


# ---------------------------------------------------------------- receipt x indexed audit interaction

class CompoundObservation(_Base):
    def test_observer_on_tampered_result_does_not_report_clean_coverage(self):
        """A report over a result whose receipt no longer matches must not read as clean."""
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        planner, context, result = self.recall()
        baseline = self.observe(planner, context, result)
        self.assertEqual(baseline.diagnosis, "coverage_observed_unattested")
        result.route_candidate_counts.update({k: 0 for k in result.route_candidate_counts})
        self.assertFalse(result.observation_unchanged())
        tampered = self.observe(planner, context, result)
        self.assertEqual(tampered.continuation_proposal, "continue_if_permitted")
        self.assertNotEqual(tampered.diagnosis, "coverage_observed_unattested",
                            "observer ignores a receipt mismatch and reports clean coverage")

    def test_observer_without_receipt_does_not_report_clean_coverage(self):
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        planner, context, result = self.recall()
        result.observation_receipt = None
        report = self.observe(planner, context, result)
        self.assertNotEqual(report.diagnosis, "coverage_observed_unattested")

    def test_census_detects_competitor_hidden_by_tampering_even_with_forged_receipt(self):
        self.seed_conflict()
        planner, context, result = self.recall()
        competitor = result.recall.admitted[-1]
        for field in (result.recall.admitted, result.recall.ranked_admitted, result.recall.candidates):
            field.remove(competitor)
        report = self.observe(planner, context, result)
        self.assertEqual(report.continuation_proposal, "continue_if_permitted")
        self.assertNotIn(report.diagnosis, ("coverage_observed_unattested", "mechanical_coverage_observed"))

    def test_never_any_positive_stop(self):
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        self.memory.remember("memory:b", f"{QUERY} confirmed Oslo", proposition=_prop("Oslo"))
        planner, context, result = self.recall()
        report = self.observe(planner, context, result)
        self.assertTrue(report.mechanical_coverage_met)
        self.assertEqual(report.continuation_proposal, "continue_if_permitted")
        self.assertFalse(report.to_dict()["stop_attested"])
        self.assertEqual(report.to_dict()["authority_effect"], "none")


# ---------------------------------------------------------------- indexed census vs full-store scan

class CensusEquivalence(_Base):
    def _populate(self):
        m = self.memory
        m.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        m.remember("memory:b", PARAPHRASE, proposition=_prop("Lisbon"))
        m.remember("memory:c", f"{QUERY} may be Bergen", proposition=_prop("Bergen", hedged=True))
        m.remember("memory:d", f"{QUERY} was Riga", proposition=_prop("Riga"),
                   valid_from="2019-01-01", valid_until="2019-06-01")
        m.remember("memory:e", f"{QUERY} will be Turku", proposition=_prop("Turku"), valid_from="2099-01-01")
        m.remember("memory:f", f"{QUERY} is Tallinn")
        doomed = m.remember("memory:g", "Gateway zone reported as Vilnius", proposition=_prop("Vilnius"))
        m.remember("memory:h", "Gateway zone reported as Kaunas", proposition=_prop("Kaunas"))
        self.assertTrue(m.forget("memory:h")["committed"])
        self.assertTrue(m.dispute("memory:g", fact_uuid=doomed["fact_uuid"], evidence=_evidence(),
                                  risk_class="low", evidence_refs=("evidence:x",))["committed"])
        for i in range(25):
            m.remember(f"memory:n{i}", f"Noise {i} colour is shade {i}",
                       proposition=_prop(f"s{i}", subject=f"Noise {i}", attribute="colour"))
        m.close()
        other = self.open("project:b")
        other.remember("memory:z", "Gateway zone moved to Gdansk", proposition=_prop("Gdansk"))
        other.close()
        self.memory = self.open()
        self.assertTrue(self.memory.correct("memory:a", f"{QUERY} is Oslo North", evidence=_evidence(),
                                            risk_class="low", replacement_kind="state_change")["committed"])

    def _assert_equivalent(self, label):
        slots = (SLOT, typed.typed_slot("Noise 3", "colour"), typed.typed_slot("Absent", "slot"))
        planner, context, result = self.recall()
        adapter = self.memory.runtime.adapter
        for admitted in (tuple(result.recall.admitted), (), tuple(result.recall.admitted)[:1]):
            with self.subTest(phase=label, admitted=len(admitted)):
                indexed = adapter.current_typed_slot_obstacles(tuple(sorted(slots)), admitted, context)
                self.assertEqual(indexed, full_scan_census(adapter, slots, set(admitted), context))
        return adapter.current_typed_slot_obstacles((SLOT,), (), context)[SLOT]

    def test_index_equals_full_scan_through_lifecycle_and_restart(self):
        self._populate()
        before = self._assert_equivalent("populated")
        self.assertEqual(before, {"eligible_unretrieved": 4, "qualified_counter_evidence": 1,
                                  "declared_temporal_boundary": 2})
        self.reopen()
        self.assertEqual(self._assert_equivalent("after_restart"), before)
        self.memory.remember("memory:k", "Gateway zone now Kiel", proposition=_prop("Kiel"))
        self.assertEqual(self._assert_equivalent("write_after_restart")["eligible_unretrieved"], 5)
        self.assertTrue(self.memory.forget("memory:k")["committed"])
        self.assertEqual(self._assert_equivalent("forget_after_restart"), before)

    def test_other_project_reader_sees_only_its_own_slot_members(self):
        self._populate()
        self.reopen("project:b")
        _, context, _ = self.recall()
        counts = self.memory.runtime.adapter.current_typed_slot_obstacles((SLOT,), (), context)[SLOT]
        self.assertEqual(counts["eligible_unretrieved"], 1)
        self._assert_equivalent("project_b")

    def test_cross_tenant_rows_in_shared_sqlite_are_never_counted(self):
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        competitor = self.memory.remember("memory:x", PARAPHRASE, proposition=_prop("Lisbon"))
        substrate = self.memory.runtime.adapter._substrate
        fact = substrate.get_fact(competitor["fact_uuid"])
        self.assertTrue(self.memory.forget("memory:x")["committed"])
        substrate.write_fact(dataclasses.replace(fact, uuid="xt-foreign-1", group_id="tenant:other"))
        substrate.write_fact(dataclasses.replace(fact, uuid="xt-unscoped-1"))  # same tenant, no registered scope
        adapter = self.memory.runtime.adapter
        adapter._semantic_slot_index = None  # force a rebuild that enumerates the raw rows
        _, context, _ = self.recall()
        counts = adapter.current_typed_slot_obstacles((SLOT,), (), context)[SLOT]
        self.assertEqual(counts["eligible_unretrieved"], 1)  # memory:a only; both raw rows refused
        self.assertEqual(adapter._admission_refusal(substrate.get_fact("xt-foreign-1"), context), "out_of_scope")
        self.assertEqual(adapter._admission_refusal(substrate.get_fact("xt-unscoped-1"), context), "unknown_scope")
        self.assertEqual(adapter.current_typed_slot_obstacles((SLOT,), (), context),
                         full_scan_census(adapter, (SLOT,), set(), context))

    def test_unavailable_or_corrupt_enumeration_fails_closed(self):
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        planner, context, result = self.recall()
        adapter = self.memory.runtime.adapter
        index = adapter._semantic_index()
        index["{not json"] = {"ref-x": {}}
        with self.assertRaises(RuntimeError):
            adapter.current_typed_slot_obstacles((SLOT,), (), context)
        del index["{not json"]
        substrate = adapter._substrate
        substrate.all_facts = None
        try:
            with self.assertRaises(RuntimeError):
                adapter.current_typed_slot_obstacles((SLOT,), (), context)
        finally:
            del substrate.all_facts
        original = type(adapter).current_typed_slot_obstacles
        try:
            type(adapter).current_typed_slot_obstacles = None
            with self.assertRaises(Exception):
                self.observe(planner, context, result)
        finally:
            type(adapter).current_typed_slot_obstacles = original


# ---------------------------------------------------------------- temporal metadata

class TemporalMetadata(_Base):
    def _diagnosis(self):
        planner, context, result = self.recall()
        return self.observe(planner, context, result).diagnosis

    def test_future_valid_from_is_an_obstacle(self):
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"), valid_from="2099-01-01")
        self.assertEqual(self._diagnosis(), "declared_temporal_boundary_unresolved")

    def test_expired_valid_until_is_an_obstacle(self):
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"),
                             valid_from="2019-01-01", valid_until="2019-06-01")
        self.assertEqual(self._diagnosis(), "declared_temporal_boundary_unresolved")

    def test_past_valid_from_is_not_an_obstacle(self):
        self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"), valid_from="2001-01-01")
        self.assertEqual(self._diagnosis(), "coverage_observed_unattested")

    def test_invalid_temporal_metadata_is_refused_or_conservative(self):
        for bad in ("not-a-date", "2020-13-45", "2020-01-01T25:00:00Z"):
            with self.subTest(valid_from=bad):
                try:
                    out = self.memory.remember(f"memory:{bad}", f"{QUERY} is Oslo", proposition=_prop("Oslo"),
                                               valid_from=bad)
                except (ValueError, TypeError):
                    continue
                if out.get("committed"):
                    self.assertNotEqual(self._diagnosis(), "coverage_observed_unattested")


# ---------------------------------------------------------------- no mutation, restart

class NoStateEffects(_Base):
    def test_capture_and_observation_change_no_state_and_survive_restart(self):
        self.seed_conflict()
        adapter = self.memory.runtime.adapter
        substrate = adapter.checkpoint_substrate()
        planner, context, result = self.recall()
        digest, events = substrate.state_digest(), len(adapter.events)
        report = self.observe(planner, context, result).to_dict()
        result.observation_unchanged()
        result.observation_receipt.to_dict()
        planner.observe_governed_transition_witnesses(result, context)
        self.assertEqual((substrate.state_digest(), len(adapter.events)), (digest, events))
        self.reopen()
        planner, context, again = self.recall()
        self.assertTrue(again.observation_unchanged())
        self.assertEqual(self.observe(planner, context, again).to_dict(), report)
        self.assertEqual(again.observation_receipt.admitted_refs, result.observation_receipt.admitted_refs)


if __name__ == "__main__":
    unittest.main()
