"""#777 independent adversarial tests for the public deleted-lineage read projection.

Authored before the implementation. Canonical admission and internal audit records must
be unchanged; only ordinary caller-facing projections withhold deleted-generation
identifiers. Live provenance must stay visible.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace

from agentmem_ref import AgentMemory, policy
from tests.test_644_combined_independent import _evidence, _prop
from tests.test_776_adversarial_review import KILN, S, _Facade, _Store
from tests.test_runtime_composition import TENANT, _context

HIST = {"mode": "historical"}
POLICY = {"policy_id": "public-deleted-lineage-redaction", "policy_version": "1.0.0", "deleted_lineage": "withheld"}


def _serial(value):
    return json.dumps(value, sort_keys=True, default=str)


class RecallProjection(_Facade):
    def test_exact_identity_route_with_named_deleted_memory_is_indistinguishable_from_unknown(self):
        old, new = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        deleted = self.memory.recall("", logical_memory_refs=("memory:a",), temporal_intent=HIST)
        unknown = self.memory.recall("", logical_memory_refs=("memory:never",), temporal_intent=HIST)
        for key in ("candidates", "admitted", "admissions", "returned"):
            self.assertEqual(deleted.get(key), unknown.get(key), key)
        self.assertNotIn(old, _serial(deleted))
        self.assertNotIn(new, _serial(deleted))

    def test_response_carries_the_versioned_projection_policy(self):
        self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        out = self.memory.recall("Orrin gateway region", temporal_intent=HIST)
        self.assertEqual(out["public_projection"], POLICY)

    def test_derived_from_deleted_facts_are_withheld_but_live_derivations_keep_provenance(self):
        old, _ = self.state_changed()
        tainted = self.memory.remember("memory:t", "Digest: gateway region used to be Oslo",
                                       evidence_refs=(old,))["fact_uuid"]
        live = self.memory.remember("memory:l", "Gateway owner is Team Kite",
                                    proposition=_prop("Team Kite", attribute="owner"))["fact_uuid"]
        derived = self.memory.remember("memory:ld", "Digest: gateway owner Team Kite",
                                       evidence_refs=(live,))["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        out = self.memory.recall("gateway digest region owner Team Kite Oslo", temporal_intent=HIST)
        serial = _serial(out)
        self.assertNotIn(tainted, serial)
        self.assertNotIn(old, serial)
        self.assertNotIn("logical_memory_deleted", serial)
        self.assertNotIn("derived_from_deleted_logical_memory", serial)
        self.assertTrue({live, derived} <= set(out["admitted"]))
        self.assertIn(derived, out["admissions"])

    def test_partial_deletion_withholds_only_that_version(self):
        old, new = self.state_changed(values=("Oslo", "Bergen", "Turku"))[1:], None
        v2, v3 = old
        adapter = self.memory.runtime.adapter
        # governed deletion of the superseded middle version through the runtime
        proposal = self.memory._proposal(target_reference="memory:a", operation="pruning",
                                         current_strength="reinforced", proposed_strength="archived",
                                         reversibility="reversible", risk_class="low")
        from agentmem_ref.api import contract
        out = self.memory.runtime.durable_runtime.governed_delete(contract.proposal_from_envelope(proposal), v2)
        self.assertTrue(out.committed, out)
        recalled = self.memory.recall("Orrin gateway region", temporal_intent=HIST)
        self.assertNotIn(v2, _serial(recalled))
        self.assertIn(v3, recalled["admitted"])

    def test_recreated_memory_id_is_visible_and_old_generation_withheld(self):
        old, new = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        again = self.memory.remember("memory:a", "Orrin gateway region is Turku", proposition=_prop("Turku"))["fact_uuid"]
        out = self.memory.recall("", logical_memory_refs=("memory:a",), temporal_intent=HIST)
        serial = _serial(out)
        self.assertIn(again, out["admitted"])
        self.assertNotIn(old, serial)
        self.assertNotIn(new, serial)

    def test_permanent_deletion_and_restart(self):
        old, new = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen()
        out = self.memory.recall("Orrin gateway region Oslo Bergen", temporal_intent=HIST)
        self.assertNotIn(old, _serial(out))

    def test_deleted_only_match_is_indistinguishable_from_never_existed(self):
        # Same query, two stores: one where the matching memory was deleted, one where it
        # never existed. Ordinary recall (with and without shadow recall control) must be
        # identical, including stop reasons and counts.
        for shadow in ("off", "shadow"):
            with self.subTest(recall_control=shadow):
                views = []
                for deleted in (True, False):
                    root = tempfile.mkdtemp() + "/m"
                    m = AgentMemory.open(root, tenant="tenant:c644", actor_id="agent:c644", scope="project:a",
                                         purpose="c644", recall_control=shadow)
                    m.remember("memory:keep", "Lighthouse rota is posted weekly")
                    if deleted:
                        m.remember("memory:a", "Orrin gateway region is Oslo", proposition=_prop("Oslo"))
                        self.assertTrue(m.forget("memory:a")["committed"])
                    view = m.recall("Orrin gateway region Oslo", temporal_intent=HIST)
                    if view.get("recall_control"):  # controller wall-clock only; computed from the query
                        view["recall_control"]["usage"].pop("elapsed_ms", None)
                    views.append(view)
                    m.close()
                self.assertEqual(_serial(views[0]), _serial(views[1]))


class HistoryProjection(_Facade):
    def _blank(self):
        return {"current_fact_uuid": None, "state_version": 0, "tombstoned": False, "events": []}

    def test_other_project_handle_cannot_learn_existence_or_deletion(self):
        self.state_changed()
        self.memory.remember("memory:live", "Orrin gateway owner is Team Kite")
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:b")
        self.assertEqual(self.memory.history("memory:a")["history"], self._blank())
        self.assertEqual(self.memory.history("memory:live")["history"], self._blank())
        self.assertEqual(self.memory.history("memory:never")["history"], self._blank())

    def test_same_project_deleted_memory_reads_as_unknown(self):
        self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertEqual(self.memory.history("memory:a")["history"], self._blank())
        rejected = self.memory.history("memory:a", fact_text="Orrin gateway region is Oslo")["history"]
        self.assertEqual(rejected.get("rejected_values", []), [])

    def test_recreated_memory_history_shows_only_the_live_generation(self):
        self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        again = self.memory.remember("memory:a", "Orrin gateway region is Turku")["fact_uuid"]
        record = self.memory.history("memory:a")["history"]
        self.assertEqual(record["current_fact_uuid"], again)
        self.assertFalse(record["tombstoned"])
        self.assertNotIn("memory.delete", {e["event_type"] for e in record["events"]})
        self.assertTrue(record["events"])

    def test_live_memory_history_unchanged(self):
        out = self.memory.remember("memory:live", "Orrin gateway owner is Team Kite")
        record = self.memory.history("memory:live")["history"]
        self.assertEqual(record["current_fact_uuid"], out["fact_uuid"])
        self.assertIn("memory.commit", {e["event_type"] for e in record["events"]})


class GraphProjection(unittest.TestCase):
    def test_graph_paths_through_a_deleted_version_are_not_reported(self):
        from agentmem_ref.recall_control import (ControlledRecallPlanner, NativeTypedGraphCandidateRetriever,
                                                 RecallControlPlan, RecallRouteBudget, TYPED_GRAPH_ROUTE)
        from agentmem_ref.runtime_composition import EXACT_IDENTITY_ROUTE, LEXICAL_ROUTE, SHARED_EVIDENCE_ROUTE
        from tests.test_typed_graph_retrieval import _FixedController, _relation

        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
        tail = h.chain("shelf", [("The glaze shelf holds test tiles.", None)])[0]
        sub = h.adapter.checkpoint_substrate()
        sub.write_relation(replace(_relation("r1", seed, old), group_id=TENANT))
        sub.write_relation(replace(_relation("r2", old, tail), group_id=TENANT))
        sub.write_relation(replace(_relation("r3", seed, tail, weight=0.5), group_id=TENANT))
        h.prune("kiln")
        plan = RecallControlPlan(controller_ref="t", controller_version="1", route_budgets=(
            RecallRouteBudget(LEXICAL_ROUTE, 0), RecallRouteBudget(EXACT_IDENTITY_ROUTE, 1),
            RecallRouteBudget(TYPED_GRAPH_ROUTE, 8), RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0)))
        planner = ControlledRecallPlanner(h.adapter, controller=_FixedController(plan),
                                          graph_retriever=NativeTypedGraphCandidateRetriever())
        result = planner.recall("", _context(), logical_memory_refs=("memory:776r:studio",))
        self.assertIn(tail, result.recall.admitted)  # live neighbour still reachable
        for ref, hit in result.graph_candidate_hits.items():
            self.assertNotIn(old, hit.path_refs, ref)
            self.assertNotEqual(ref, old)
        self.assertIn(tail, result.graph_candidate_hits)
        self.assertEqual(result.graph_candidate_hits[tail].path_refs, (seed, tail))
        # canonical refusal (internal) is unchanged
        self.assertEqual(result.recall.refusals.get(old), "logical_memory_deleted")


class ModuleLevelRecall(unittest.TestCase):
    def test_stage_recall_withholds_deleted_identifiers(self):
        from agentmem_ref.api import contract, surface
        h = _Store(self)
        old, new = h.chain("kiln", KILN)
        h.prune("kiln")
        ctx = {"contract_version": contract.CONTRACT_VERSION, "target_domain_refs": list(_context().target_domain_refs),
               "principal_ref": _context().principal_ref, "project_ref": _context().project_ref,
               "purpose": _context().purpose}
        out = surface.recall(h.adapter, "kiln firing schedule glaze", ctx)
        self.assertNotIn(old, _serial(out))
        self.assertNotIn(new, _serial(out))
        self.assertEqual(out["public_projection"], POLICY)


class SurvivingRelationProjection(_Facade):
    def test_relation_dropped_but_stored_semantics_unchanged(self):
        from tests.test_typed_propositions import PROP, TEXT
        deleted = self.memory.remember("memory:ra", TEXT["room_old"], proposition=PROP["room_old"])["fact_uuid"]
        live = self.memory.remember("memory:rb", TEXT["room_new"], proposition=PROP["room_new"])["fact_uuid"]
        stored_before = _serial(self.memory.runtime.adapter._substrate.get_fact(live).attributes)
        self.assertTrue(self.memory.forget("memory:ra")["committed"])
        after = self.memory.write_semantics(live)
        self.assertEqual(after["relations"], [])
        self.assertEqual(after.get("relation_count"), 0)
        self.assertEqual(_serial(self.memory.runtime.adapter._substrate.get_fact(live).attributes), stored_before)
        self.assertIn(deleted, stored_before)  # immutable audit evidence retained internally

    def test_live_relation_is_preserved(self):
        from tests.test_typed_propositions import PROP, TEXT
        a = self.memory.remember("memory:ra", TEXT["room_old"], proposition=PROP["room_old"])["fact_uuid"]
        b = self.memory.remember("memory:rb", TEXT["room_new"], proposition=PROP["room_new"])["fact_uuid"]
        self.assertIn(a, _serial(self.memory.write_semantics(b)["relations"]))


if __name__ == "__main__":
    unittest.main()
