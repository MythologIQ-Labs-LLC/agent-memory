"""#774 on the qualified SQLite composition: the strict selector is reachable from the runtime
the public ``AgentMemory`` facade actually opens, not only from the JSON composition the #774
suites drive. The facade has no public entry point for it yet (contract 1.7.0); callers reach it
through ``handle.runtime`` under the runtime's serialization lock, as docs/47 requires.
"""
from __future__ import annotations

import json
import tempfile
import unittest

from agentmem_ref import AgentMemory
from agentmem_ref.runtime.runtime_composition import AsOfTarget
# #786 store identity profiles: this module drives several projects through one tenant-wide store to
# exercise the canonical adapter gates; AgentMemory.open admits that only as scope_distinct_v1, so the
# test-only tenant-wide fixture reproduces the pre-profile store (tests/_tenant_wide_fixture.py).
from tests._tenant_wide_fixture import open_tenant_wide
from tests.test_644_combined_independent import _evidence, _prop
from tests.test_776_adversarial_review import _Facade

HIST = {"mode": "historical"}


class StrictSelectorOnSQLiteFacade(_Facade):
    def open(self, scope="project:a"):
        # #786: this class drives two projects through one store (test-only tenant-wide fixture).
        return open_tenant_wide(self.root, tenant="tenant:c644", actor_id="agent:c644", scope=scope, purpose="c644")

    def _select(self, query, **kw):
        runtime = self.memory.runtime
        with runtime.serialization_lock:
            return runtime.historical_predecessor_context(query, self.memory._handle_recall_context(), budget=5, **kw)

    def test_declared_successor_promotes_its_governed_predecessor_and_survives_reopen(self):
        v1, v2, v3 = self.state_changed(values=("Oslo", "Bergen", "Turku"))
        for label in ("live", "reopened"):
            with self.subTest(label):
                out = self._select("Orrin gateway region before", successor_ref=v3)
                self.assertEqual((out.target_resolution, out.successor_ref, out.predecessor_ref), ("resolved", v3, v2))
                self.assertEqual(out.served_refs[0], v2)
                older = self._select("Orrin gateway region before", successor_ref=v2)
                self.assertEqual((older.successor_ref, older.predecessor_ref), (v2, v1))
                first = self._select("Orrin gateway region before", successor_ref=v1)
                self.assertEqual((first.target_resolution, first.predecessor_ref), ("resolved", None))
                self.reopen()

    def test_as_of_target_resolves_the_version_in_effect(self):
        v1, v2 = self.state_changed()
        created = {ref: self.memory.runtime.adapter._substrate.get_fact(ref).created_at for ref in (v1, v2)}
        out = self._select("Orrin gateway region", as_of_target=AsOfTarget("memory:a", created[v2]))
        self.assertEqual((out.successor_ref, out.predecessor_ref), (v2, v1))
        before_any = self._select("Orrin gateway region", as_of_target=AsOfTarget("memory:a", "2000-01-01T00:00:00Z"))
        self.assertEqual(before_any.target_resolution, "unresolved")

    def test_untargeted_call_serves_composed_ranking_unchanged(self):
        self.state_changed()
        self.memory.remember("memory:live", "Orrin gateway owner is Team Kite")
        out = self._select("Orrin gateway region before")
        composed = self.memory._canonical_recall("Orrin gateway region before", temporal_intent=HIST)
        self.assertEqual(out.target_resolution, "unresolved")
        self.assertEqual(list(out.served_refs), composed["admitted"][:5])

    def test_deleted_generation_is_a_barrier_on_sqlite_and_after_reopen(self):
        old = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        n1 = self.memory.remember("memory:a", "Orrin gateway region is Tromso", proposition=_prop("Tromso"))["fact_uuid"]
        n2 = self.memory.correct("memory:a", "Orrin gateway region is Narvik", evidence=_evidence(), risk_class="low",
                                 replacement_kind="state_change")["fact_uuid"]
        for label in ("live", "reopened"):
            with self.subTest(label):
                out = self._select("Orrin gateway region before", successor_ref=n2)
                self.assertEqual((out.successor_ref, out.predecessor_ref), (n2, n1))
                self.assertIsNone(self._select("Orrin gateway region before", successor_ref=n1).predecessor_ref)
                self.assertFalse(set(old) & set(out.served_refs))
                for ref in old:
                    with self.assertRaises(ValueError):
                        self._select("Orrin gateway region before", successor_ref=ref)
                self.assertNotIn("Oslo", json.dumps(out.served_refs))
                self.reopen()

    def test_other_project_cannot_target_or_learn_the_successor(self):
        v1, v2 = self.state_changed()
        self.reopen("project:b")
        for ref in (v1, v2, "ref-does-not-exist"):
            with self.subTest(ref=ref), self.assertRaises(ValueError) as caught:
                self._select("Orrin gateway region before", successor_ref=ref)
            self.assertEqual(str(caught.exception), "declared successor is not visible to this reader")
        out = self._select("Orrin gateway region", as_of_target=AsOfTarget("memory:a", "2030-01-01T00:00:00Z"))
        self.assertEqual((out.target_resolution, out.served_refs), ("unresolved", ()))


if __name__ == "__main__":
    unittest.main()
