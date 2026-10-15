"""#777 preregister public read-projection privacy controls, not audit deletion.

These tests are intentionally expected to FAIL before a distinct authorized
public diagnostic contract. Do not weaken #776 canonical admission or strip
immutable pruning/audit evidence to make them pass.
"""
from __future__ import annotations

import json

from tests.test_776_adversarial_review import _Facade
from tests.test_typed_propositions import TEXT, PROP


class PublicDeletedIdentifiersNotExposed(_Facade):
    def test_recall_candidates_and_refusals_do_not_enumerate_deleted_fact_ids(self):
        old, new = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        response = self.memory.recall(
            "Orrin gateway region Oslo Bergen",
            temporal_intent={"mode": "historical"},
        )
        self.assertNotIn(old, json.dumps(response, sort_keys=True))
        self.assertNotIn(new, json.dumps(response, sort_keys=True))
        self.assertEqual(response["admitted"], [])

    def test_recall_redaction_survives_restart(self):
        old, new = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen()
        response = self.memory.recall(
            "Orrin gateway region Oslo Bergen",
            temporal_intent={"mode": "historical"},
        )
        serial = json.dumps(response, sort_keys=True)
        self.assertNotIn(old, serial)
        self.assertNotIn(new, serial)

    def test_surviving_fact_write_semantics_does_not_name_deleted_relations(self):
        deleted = self.memory.remember(
            "memory:ra", TEXT["room_old"], proposition=PROP["room_old"],
        )["fact_uuid"]
        live = self.memory.remember(
            "memory:rb", TEXT["room_new"], proposition=PROP["room_new"],
        )["fact_uuid"]
        before = self.memory.write_semantics(live)
        # Verify this actually exercises a governed cross-fact relation.
        self.assertIn(deleted, json.dumps(before, sort_keys=True))
        self.assertTrue(self.memory.forget("memory:ra")["committed"])
        after = self.memory.write_semantics(live)
        self.assertIsInstance(after, dict)
        self.assertNotIn(deleted, json.dumps(after, sort_keys=True))
        self.assertNotIn("memory:ra", json.dumps(after, sort_keys=True))
        self.assertIsNone(self.memory.write_semantics(deleted))

    def test_unrelated_live_provenance_is_preserved(self):
        live = self.memory.remember(
            "memory:live", "Orrin gateway monitoring owner is Team Kite",
        )["fact_uuid"]
        derived = self.memory.remember(
            "memory:live-digest", "Digest: Team Kite owns Orrin monitoring",
            evidence_refs=(live,),
        )["fact_uuid"]
        self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        result = self.memory.recall("Team Kite Orrin monitoring digest")
        self.assertIn(derived, result["admitted"])
        self.assertIn(live, result["admitted"])
        self.assertIn(derived, json.dumps(result))


if __name__ == "__main__":
    import unittest
    unittest.main()
