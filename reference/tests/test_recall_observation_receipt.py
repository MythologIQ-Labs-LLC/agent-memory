"""#644: immutable, non-authoritative planner observation boundaries."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
import unittest

from agentmem_ref.runtime.recall_observation_receipt import (
    RouteObservation, RecallObservationReceipt, capture_recall_observation,
)


CONTROL_PLAN = {"controller_ref": "controller:v1", "controller_version": "1",
                "evidence_sufficiency_target": 1, "route_budgets": [
                    {"route_id": "lexical", "candidate_limit": 5, "anchor_limit": 0},
                ]}
REFUSALS = {"fact:private": "governed_refusal"}


def bindings(*, query="Which region?", plan=None, refusals=None,
             policy_version="policy:v1", admission_mode="current_state",
             evaluated_at="2026-10-09T12:00:00Z"):
    return {
        "query": query,
        "plan": CONTROL_PLAN if plan is None else plan,
        "refusals": REFUSALS if refusals is None else refusals,
        "policy_version": policy_version,
        "admission_mode": admission_mode,
        "evaluated_at": evaluated_at,
    }


def captured(*, query="Which region?", principal="agent:a", project="project:p",
             task="", domains=("tenant:t", "project:p")):
    candidates=["fact:private", "fact:admitted"]
    admitted=["fact:admitted"]
    ranked=["fact:admitted"]
    counts={"lexical":1, "exact_identity":0}
    routes=(RouteObservation("lexical",5,0,1,True),)
    receipt=capture_recall_observation(
        query=query, reader_domain_refs=domains, principal_ref=principal,
        project_ref=project, purpose="", task_ref=task,
        controller_ref="controller:v1", admission_policy="policy:v1",
        admission_mode="current_state", evaluated_at="2026-10-09T12:00:00Z",
        candidates=candidates, admitted=admitted, ranked=ranked,
        route_observations=routes, observed_route_counts=counts,
        plan=CONTROL_PLAN, refusals=REFUSALS,
    )
    return receipt,candidates,admitted,ranked,counts


class ImmutableRecallObservationTests(unittest.TestCase):
    def test_capture_is_immutable_defensive_and_integrity_checked(self):
        r,candidates,admitted,ranked,counts=captured()
        self.assertIsInstance(r,RecallObservationReceipt)
        self.assertTrue(r.integrity_valid())
        self.assertTrue(r.matches_mutable_result(
            candidates=candidates,admitted=admitted,ranked=ranked,
            route_counts=counts,routes_executed=("lexical",), **bindings()))
        candidates.clear()
        admitted.clear()
        ranked.clear()
        counts["lexical"]=0
        self.assertEqual(r.candidate_refs,("fact:private","fact:admitted"))
        self.assertEqual(r.admitted_refs,("fact:admitted",))
        self.assertEqual(r.observed_route_counts,(("exact_identity",0),("lexical",1)))
        self.assertFalse(r.matches_mutable_result(
            candidates=candidates,admitted=admitted,ranked=ranked,
            route_counts=counts,routes_executed=("lexical",), **bindings()))
        with self.assertRaises(FrozenInstanceError):
            r.can_stop=True
        with self.assertRaises(AttributeError):
            _ = r.__dict__
        with self.assertRaises(AttributeError):
            _ = r.routes[0].__dict__

    def test_mutated_or_missing_unselected_route_counter_is_detected(self):
        r,c,a,rank,counts=captured()
        counts["exact_identity"]=1
        self.assertFalse(r.matches_mutable_result(
            candidates=c,admitted=a,ranked=rank,route_counts=counts,
            routes_executed=("lexical",), **bindings()))
        del counts["exact_identity"]
        self.assertFalse(r.matches_mutable_result(
            candidates=c,admitted=a,ranked=rank,route_counts=counts,
            routes_executed=("lexical",), **bindings()))

    def test_malformed_mutable_route_counts_fail_closed(self):
        r, candidates, admitted, ranked, _ = captured()
        for bad_counts in (
            {"lexical": 1, "exact_identity": "invalid"},
            {"lexical": 1, 4: 0},
            {"lexical": True},
            {"lexical": -1},
            None,
        ):
            with self.subTest(counts=bad_counts):
                self.assertFalse(r.matches_mutable_result(
                    candidates=candidates, admitted=admitted, ranked=ranked,
                    route_counts=bad_counts, routes_executed=("lexical",),
                    **bindings(),
                ))

    def test_removed_candidate_and_rerank_are_detected(self):
        r,c,a,rank,counts=captured()
        c.remove("fact:private")
        self.assertFalse(r.matches_mutable_result(
            candidates=c,admitted=a,ranked=rank,route_counts=counts,
            routes_executed=("lexical",), **bindings()))
        c[:]=list(r.candidate_refs)
        rank[0]="fact:outsider"
        self.assertFalse(r.matches_mutable_result(
            candidates=c,admitted=a,ranked=rank,route_counts=counts,
            routes_executed=("lexical",), **bindings()))

    def test_changed_refusal_policy_query_or_controller_plan_is_detected(self):
        r,c,a,rank,counts=captured()
        def unchanged(**changes):
            return r.matches_mutable_result(
                candidates=c, admitted=a, ranked=rank,
                route_counts=counts, routes_executed=("lexical",),
                **bindings(**changes),
            )
        self.assertTrue(unchanged())
        altered=dict(CONTROL_PLAN)
        altered["controller_version"]="2"
        self.assertFalse(unchanged(plan=altered))
        self.assertFalse(unchanged(refusals={"fact:private":"not_a_refusal"}))
        self.assertFalse(unchanged(refusals={}))
        self.assertFalse(unchanged(query="different question"))
        self.assertFalse(unchanged(policy_version="policy:v2"))
        self.assertFalse(unchanged(admission_mode="historical_evidence"))
        self.assertFalse(unchanged(evaluated_at="2026-10-09T13:00:00Z"))

    def test_changed_binding_is_detected_even_when_membership_is_unchanged(self):
        first,*_=captured()
        second,*_=captured()
        self.assertEqual(first.content_digest,second.content_digest)
        self.assertTrue(first.integrity_valid())
        self.assertNotIn("fact:private",json.dumps(first.to_dict()))
        # No successful mutation of the result sequence is needed to reveal
        # this defect: changing a controller decision is independently checked.
        plan={**CONTROL_PLAN,"reason_codes":["forced_relevance"]}
        self.assertFalse(first.matches_mutable_result(
            candidates=list(first.candidate_refs),
            admitted=list(first.admitted_refs),
            ranked=list(first.ranked_refs),
            route_counts=dict(first.observed_route_counts),
            routes_executed=("lexical",),
            **bindings(plan=plan),
        ))

    def test_empty_query_and_blank_reader_fields_preserve_existing_inputs(self):
        r,*_=captured(query="")
        self.assertTrue(r.integrity_valid())
        self.assertFalse(r.can_stop)
        self.assertIsNone(r.state_revision)

    def test_query_reader_and_task_are_bound_but_not_trusted(self):
        r,*_=captured()
        different_query,*_=captured(query="Where does the system run?")
        different_scope,*_=captured(project="project:q")
        different_task,*_=captured(task="task:confidential")
        self.assertNotEqual(r.query_digest,different_query.query_digest)
        self.assertNotEqual(r.reader_digest,different_scope.reader_digest)
        self.assertNotEqual(r.reader_digest,different_task.reader_digest)
        canonical,*_=captured(domains=("project:p","tenant:t"))
        self.assertEqual(r.reader_digest,canonical.reader_digest)
        self.assertEqual(r.content_digest,canonical.content_digest)

    def test_receipt_does_not_export_refused_candidate_identity(self):
        r,*_=captured()
        exported=json.dumps(r.to_dict(),sort_keys=True)
        self.assertNotIn("fact:private",exported)
        self.assertIn("fact:admitted",exported)
        self.assertEqual(r.to_dict()["candidate_count"],2)
        self.assertNotIn("Which region?",exported)
        self.assertEqual(r.to_dict()["state_revision"],None)

    def test_no_stop_or_revision_can_be_forged(self):
        r,*_=captured()
        for kw in (
            {"can_stop":True},{"snapshot_attested":True},
            {"slot_closure_attested":True},{"state_revision":"revision:1"},
            {"authority_effect":"allow"},{"version":"malicious"},
            {"content_digest":"f"*64},
        ):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                replace(r,**kw)

    def test_invalid_route_work_is_refused(self):
        for values in (
            ("route",2,0,3,True),
            ("route",0,0,0,True),
            ("route",4,0,2,False),
            ("route",True,0,0,True),
            ("route",4,0,1,1),
        ):
            with self.subTest(values=values),self.assertRaises(ValueError):
                RouteObservation(*values)

    def test_invalid_membership_cannot_be_content_committed(self):
        r,*_=captured()
        for change in (
            {"admitted_refs":("fact:outside",)},
            {"ranked_refs":("fact:outside",)},
            {"candidate_refs":("fact:admitted","fact:admitted")},
        ):
            with self.subTest(change=change),self.assertRaises(ValueError):
                replace(r,**change)

    def test_content_hash_is_deterministic_and_domain_separated(self):
        r,*_=captured()
        other,*_=captured()
        self.assertEqual(r.content_digest,other.content_digest)
        self.assertEqual(len(r.content_digest),64)
        self.assertNotEqual(r.content_digest,r.query_digest)
        self.assertEqual(r.content_digest,
                         __import__("hashlib").sha256(
                             b"agent-memory/recall-observation/v1\x00" +
                             json.dumps(r._payload(),sort_keys=True,
                                        ensure_ascii=True,separators=(",",":")).encode()
                         ).hexdigest())

    def test_alias_import_is_exact_runtime_module(self):
        from agentmem_ref import recall_observation_receipt as alias
        from agentmem_ref.runtime import recall_observation_receipt as canonical
        self.assertIs(alias,canonical)


if __name__=="__main__":
    unittest.main()
