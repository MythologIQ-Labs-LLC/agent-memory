"""validation(#776 adoption cc13930): deleted content must not survive through derivation chains.

Counterexample recorded before any code change: a memory whose provenance is a fact
derived from a deleted earlier version (two hops) is admitted by public recall and its
write semantics are readable. One-hop derivation is already refused.
"""
from __future__ import annotations

import json
import unittest

from tests.test_644_combined_independent import _evidence, _prop
from tests.test_776_adversarial_review import _Facade


class TransitiveDerivation(_Facade):
    def _chain(self):
        old, _ = self.state_changed()
        d1 = self.memory.remember("memory:d1", "Digest one: the gateway region used to be Oslo",
                                  evidence_refs=(old,))["fact_uuid"]
        d2 = self.memory.remember("memory:d2", "Digest two: earlier the gateway region was Oslo",
                                  evidence_refs=(d1,))["fact_uuid"]
        d3 = self.memory.remember("memory:d3", "Digest three: a summary says the region was Oslo",
                                  evidence_refs=(d2,))["fact_uuid"]
        return old, d1, d2, d3

    def recalled(self):
        return self.memory.recall("gateway region Oslo digest", temporal_intent={"mode": "historical"})

    def test_derivations_of_a_deleted_version_are_refused_at_every_hop(self):
        old, d1, d2, d3 = self._chain()
        self.assertTrue({d1, d2, d3} <= set(self.recalled()["admitted"]))  # visible before deletion
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        recalled = self.recalled()
        for ref in (d1, d2, d3):
            with self.subTest(ref=ref):
                self.assertNotIn(ref, recalled["admitted"])
                self.assertIsNone(self.memory.write_semantics(ref))
        self.assertNotIn("Oslo", json.dumps(recalled["admitted"]))

    def test_transitive_refusal_survives_restart(self):
        _, d1, d2, d3 = self._chain()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen()
        self.assertFalse({d1, d2, d3} & set(self.recalled()["admitted"]))

    def test_derivations_of_live_memories_are_unaffected(self):
        live = self.memory.remember("memory:live", "Orrin gateway owner is Team Kite",
                                    proposition=_prop("Team Kite", attribute="owner"))["fact_uuid"]
        e1 = self.memory.remember("memory:e1", "Digest: Orrin gateway owner Team Kite", evidence_refs=(live,))["fact_uuid"]
        e2 = self.memory.remember("memory:e2", "Digest of digest: gateway owner Team Kite", evidence_refs=(e1,))["fact_uuid"]
        self._chain()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        recalled = self.memory.recall("gateway owner Team Kite digest")
        self.assertTrue({e1, e2} <= set(recalled["admitted"]))


if __name__ == "__main__":
    unittest.main()
