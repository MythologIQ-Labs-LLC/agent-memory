"""validation(#776 @ 5d90965): independent review of the transitive deleted-provenance traversal.

Each test states an invariant of `_derives_from_deleted`; a failure is a finding against
the exact SHA, recorded before any repair.
"""
from __future__ import annotations

import time
import unittest

from tests.test_644_combined_independent import _prop
from tests.test_776_adversarial_review import _Facade

HIST = {"mode": "historical"}


class TransitiveTraversal(_Facade):
    def admitted(self, query):
        return set(self.memory.recall(query, temporal_intent=HIST)["admitted"])

    def next_ref(self, ahead=1):
        # Deterministic ids: the n-th next fact id, used only to build forward/cyclic provenance.
        ids = self.memory.runtime.adapter._ids
        return f"ref-{ids._next + ahead:04d}" if hasattr(ids, "_next") else None

    def test_cycle_without_deletion_terminates_and_stays_admitted(self):
        a = self.memory.remember("memory:ca", "Cycle note alpha about the gateway", evidence_refs=("memory-free:x",))["fact_uuid"]
        b = self.memory.remember("memory:cb", "Cycle note beta about the gateway", evidence_refs=(a,))["fact_uuid"]
        # a <- b already; make the graph cyclic through a third fact citing b and cited by itself
        c = self.memory.remember("memory:cc", "Cycle note gamma about the gateway", evidence_refs=(b, a))["fact_uuid"]
        self.assertTrue({a, b, c} <= self.admitted("cycle note gateway"))

    def test_self_and_mutual_reference_with_deletion_is_refused(self):
        old, _ = self.state_changed()
        x = self.memory.remember("memory:x", "Derived x: region was Oslo", evidence_refs=(old, "external:doc-1"))["fact_uuid"]
        y = self.memory.remember("memory:y", "Derived y: see x", evidence_refs=(x, "external:doc-2"))["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertFalse({x, y} & self.admitted("Derived region Oslo see"))

    def test_unknown_provenance_is_not_deletion(self):
        live = self.memory.remember("memory:u", "Unknown provenance note about the gateway",
                                    evidence_refs=("ref-9999", "external:ticket-7"))["fact_uuid"]
        self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertIn(live, self.admitted("Unknown provenance note gateway"))

    def _order_scenario(self, root, future):
        from agentmem_ref import AgentMemory
        from tests.test_644_combined_independent import _evidence
        m = AgentMemory.open(root, tenant="tenant:c644", actor_id="agent:c644", scope="project:a", purpose="c644")
        q = "Orrin gateway region"
        old = m.remember("memory:a", f"{q} is Oslo", proposition=_prop("Oslo"))["fact_uuid"]
        m.correct("memory:a", f"{q} is Bergen", evidence=_evidence(), risk_class="low", replacement_kind="state_change")
        m.forget("memory:a")
        a = m.remember("memory:fwd", "Forward note citing a later digest about the gateway",
                       evidence_refs=(future,))["fact_uuid"]
        look = lambda mem: a in mem.recall("Forward note gateway digest", temporal_intent=HIST)["admitted"]
        before = look(m)  # evaluated and memoised before the late write
        late = m.remember("memory:late", "Late digest: the gateway region was Oslo", evidence_refs=(old,))["fact_uuid"]
        live = look(m)
        m.close()
        m = AgentMemory.open(root, tenant="tenant:c644", actor_id="agent:c644", scope="project:a", purpose="c644")
        fresh = look(m)
        m.close()
        return late, before, live, fresh

    def test_decision_does_not_depend_on_query_order(self):
        # A fact whose provenance becomes tainted WITHOUT a new deletion (a later write
        # deriving from an already-deleted version) must be refused whether or not it was
        # evaluated (memoised) before that write. Deterministic ids: a discovery pass learns
        # the late fact's id, the replay cites it before it exists.
        import tempfile
        with tempfile.TemporaryDirectory() as d1:
            late_id, *_ = self._order_scenario(d1 + "/m", "external:placeholder")
        with tempfile.TemporaryDirectory() as d2:
            late, before, live, fresh = self._order_scenario(d2 + "/m", late_id)
        self.assertEqual(late, late_id)
        self.assertEqual(live, fresh, f"stale memo: before={before} live={live} fresh={fresh}")
        self.assertFalse(fresh)

    def test_recreated_generation_derivations_are_live_old_ones_refused(self):
        old, new = self.state_changed()
        d_old = self.memory.remember("memory:dold", "Derived from old generation: region Oslo",
                                     evidence_refs=(old,))["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        again = self.memory.remember("memory:a", "Orrin gateway region is Turku", proposition=_prop("Turku"))["fact_uuid"]
        d_new = self.memory.remember("memory:dnew", "Derived from new generation: region Turku",
                                     evidence_refs=(again,))["fact_uuid"]
        d_new2 = self.memory.remember("memory:dnew2", "Second-hop from new generation: Turku",
                                      evidence_refs=(d_new,))["fact_uuid"]
        got = self.admitted("Derived generation region Oslo Turku second-hop")
        self.assertNotIn(d_old, got)
        self.assertTrue({again, d_new, d_new2} <= got)

    def test_deep_chain_is_bounded_in_cost(self):
        old, _ = self.state_changed()
        prev = old
        chain = []
        for i in range(300):
            prev = self.memory.remember(f"memory:deep{i}", f"deep chain link {i}", evidence_refs=(prev,))["fact_uuid"]
            chain.append(prev)
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        start = time.perf_counter()
        got = self.admitted("deep chain link")
        self.assertLess(time.perf_counter() - start, 5.0)
        self.assertFalse(set(chain) & got)


class LegacyCheckpointDerivation(unittest.TestCase):
    def test_legacy_tombstone_without_lineage_field_still_taints_derivations_after_restart(self):
        from tests.test_776_adversarial_review import KILN, _Store
        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        d1 = h.runtime.retain(h.proposal("d1", 0, evidence_refs=(old,)), "Kiln digest one: cone 6 glaze").fact_uuid
        d2 = h.runtime.retain(h.proposal("d2", 0, evidence_refs=(d1,)), "Kiln digest two: cone 6 glaze").fact_uuid
        h.prune("kiln")
        for record in h.adapter._tombstones.values():
            record.pop("deleted_fact_uuids", None)
        h.runtime.durable_runtime.checkpoint()
        recovered = h.recovered()
        self.assertTrue(all("deleted_fact_uuids" not in r for r in recovered.adapter._tombstones.values()))
        result = h.recall("Kiln digest cone 6 glaze", runtime=recovered)
        self.assertFalse({old, d1, d2} & set(result.admitted))


if __name__ == "__main__":
    unittest.main()
