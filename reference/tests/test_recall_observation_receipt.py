"""#644: immutable, non-authoritative planner observation boundaries."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
import unittest

from agentmem_ref.runtime.recall_observation_receipt import (
    RouteObservation, RecallObservationReceipt, capture_recall_observation,
)


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
    )
    return receipt,candidates,admitted,ranked,counts


class ImmutableRecallObservationTests(unittest.TestCase):
    def test_capture_is_immutable_defensive_and_integrity_checked(self):
        r,candidates,admitted,ranked,counts=captured()
        self.assertIsInstance(r,RecallObservationReceipt)
        self.assertTrue(r.integrity_valid())
        self.assertTrue(r.matches_mutable_result(
            candidates=candidates,admitted=admitted,ranked=ranked,
            route_counts=counts,routes_executed=("lexical",)))
        candidates.clear()
        admitted.clear()
        ranked.clear()
        counts["lexical"]=0
        self.assertEqual(r.candidate_refs,("fact:private","fact:admitted"))
        self.assertEqual(r.admitted_refs,("fact:admitted",))
        self.assertEqual(r.observed_route_counts,(("exact_identity",0),("lexical",1)))
        self.assertFalse(r.matches_mutable_result(
            candidates=candidates,admitted=admitted,ranked=ranked,
            route_counts=counts,routes_executed=("lexical",)))
        with self.assertRaises(FrozenInstanceError):
            r.can_stop=True

    def test_mutated_or_missing_unselected_route_counter_is_detected(self):
        r,c,a,rank,counts=captured()
        counts["exact_identity"]=1
        self.assertFalse(r.matches_mutable_result(
            candidates=c,admitted=a,ranked=rank,route_counts=counts,
            routes_executed=("lexical",)))
        del counts["exact_identity"]
        self.assertFalse(r.matches_mutable_result(
            candidates=c,admitted=a,ranked=rank,route_counts=counts,
            routes_executed=("lexical",)))

    def test_removed_candidate_and_rerank_are_detected(self):
        r,c,a,rank,counts=captured()
        c.remove("fact:private")
        self.assertFalse(r.matches_mutable_result(
            candidates=c,admitted=a,ranked=rank,route_counts=counts,
            routes_executed=("lexical",)))
        c[:]=list(r.candidate_refs)
        rank[0]="fact:outsider"
        self.assertFalse(r.matches_mutable_result(
            candidates=c,admitted=a,ranked=rank,route_counts=counts,
            routes_executed=("lexical",)))

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
                             b"agent-memory/recall-observation/v1\\x00" +
                             json.dumps(r._payload(),sort_keys=True,
                                        ensure_ascii=True,separators=(",",":")).encode()
                         ).hexdigest())

    def test_alias_import_is_exact_runtime_module(self):
        from agentmem_ref import recall_observation_receipt as alias
        from agentmem_ref.runtime import recall_observation_receipt as canonical
        self.assertIs(alias,canonical)


if __name__=="__main__":
    unittest.main()
