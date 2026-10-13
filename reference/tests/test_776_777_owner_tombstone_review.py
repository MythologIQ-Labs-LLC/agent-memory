"""review(#776, #777): owner-scoped tombstone visibility on the public history surface.

Independent review of the integrated candidate. The #777 projection made a governed-deleted
memory read as *unknown* even to the scope that deleted it, which contradicts docs/44
(``history`` returns ``tombstoned``) and fails the frozen durability profile (DUR-DEL-001:
``tombstone_retained``). The reconciled contract: a reader who could have read the deleted
head learns one boolean, ``tombstoned``; it never receives a deleted-generation identifier,
timestamp, event or value. A reader outside that scope learns nothing, byte-identically to a
memory that never existed. Each test states an invariant.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace

from agentmem_ref import AgentMemory, policy
from agentmem_ref.verification import TRANSITION_VERIFIER, VerifierRegistry
from tests.qualified_fixtures import corpus_for, rule
from tests.test_644_combined_independent import _evidence, _prop
from tests.test_776_adversarial_review import _Facade
from tests.test_runtime_composition import _proposal

HIST = {"mode": "historical"}


def _serial(value) -> str:
    return json.dumps(value, sort_keys=True)


def _blank(fact_text=False):
    out = {"current_fact_uuid": None, "state_version": 0, "tombstoned": False, "events": []}
    if fact_text:
        out["rejected_values"] = []
    return out


class OwnerTombstoneVisibility(_Facade):
    def _deleted_ids(self, memory="memory:a"):
        canonical = self.memory._canonical_history(memory)["history"]
        return {e.get("fact_uuid") for e in canonical["events"] if e.get("fact_uuid")} | {
            canonical["current_fact_uuid"]} - {None}

    def test_owner_reads_tombstoned_with_no_identifier_before_and_after_restart(self):
        ids = self.state_changed()  # Oslo -> Bergen (state change)
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        for label in ("live process", "after restart"):
            with self.subTest(label):
                out = self.memory.history("memory:a")
                record = out["history"]
                self.assertTrue(record["tombstoned"])
                self.assertIsNone(record["current_fact_uuid"])
                self.assertEqual(record["events"], [])
                self.assertGreater(record["state_version"], 0)
                serial = _serial(out)
                for fact_uuid in ids:
                    self.assertNotIn(fact_uuid, serial)
                self.assertNotIn("Oslo", serial)
                self.assertNotIn("Bergen", serial)
                self.reopen()

    def test_other_project_cannot_distinguish_deleted_from_never(self):
        self.state_changed()
        self.memory.remember("memory:live", "Orrin gateway owner is Team Kite")
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:b")
        deleted = self.memory.history("memory:a")
        never = self.memory.history("memory:never")
        self.assertEqual(_serial(deleted), _serial(never))
        self.assertEqual(deleted["history"], _blank())
        # a value probe reveals nothing either
        probe = self.memory.history("memory:a", fact_text="Orrin gateway region is Oslo")["history"]
        self.assertEqual(probe, _blank(fact_text=True))
        # the live memory of the other project is equally unknown here
        self.assertEqual(self.memory.history("memory:live")["history"], _blank())

    def test_recreated_memory_shows_only_the_live_generation_then_its_own_deletion(self):
        old_ids = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        version_after_first_delete = self.memory.history("memory:a")["history"]["state_version"]
        again = self.memory.remember("memory:a", "Orrin gateway region is Turku", proposition=_prop("Turku"))
        self.assertTrue(again["committed"], again)
        record = self.memory.history("memory:a")["history"]
        self.assertEqual(record["current_fact_uuid"], again["fact_uuid"])
        self.assertFalse(record["tombstoned"])
        self.assertNotIn("memory.delete", {e["event_type"] for e in record["events"]})
        self.assertFalse(set(old_ids) & {e.get("fact_uuid") for e in record["events"]})
        # deleting the new generation reads as tombstoned again; the version only advances
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        record = self.memory.history("memory:a")["history"]
        self.assertTrue(record["tombstoned"])
        self.assertIsNone(record["current_fact_uuid"])
        self.assertGreater(record["state_version"], version_after_first_delete)
        serial = _serial(self.memory.history("memory:a"))
        for fact_uuid in (*old_ids, again["fact_uuid"]):
            self.assertNotIn(fact_uuid, serial)

    def test_history_is_independent_of_prior_queries_and_cache_state(self):
        ids = self.state_changed()
        self.assertEqual(self.memory.history("memory:never")["history"], _blank())
        before = self.memory.history("memory:a")["history"]
        self.assertEqual(before["current_fact_uuid"], ids[-1])
        self.memory.recall("Orrin gateway region", temporal_intent=HIST)
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        first = self.memory.history("memory:a")
        self.memory.recall("Orrin gateway region", temporal_intent=HIST)
        second = self.memory.history("memory:a")
        self.reopen()
        third = self.memory.history("memory:a")
        self.assertEqual(_serial(first), _serial(second))
        self.assertEqual(_serial(first), _serial(third))
        self.assertTrue(first["history"]["tombstoned"])

    def test_deleted_fact_identifier_is_not_a_memory(self):
        ids = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        for fact_uuid in ids:
            with self.subTest(fact_uuid=fact_uuid):
                out = self.memory.history(fact_uuid)
                self.assertEqual(out["history"], _blank())
                self.assertNotIn(fact_uuid, _serial({k: v for k, v in out.items() if k != "history"}) )

    def test_derived_memory_citing_a_deleted_source_never_exposes_the_source(self):
        ids = self.state_changed()
        derived = self.memory.remember("memory:d", "Orrin gateway deploy window follows the region",
                                       evidence_refs=(ids[-1],))
        self.assertTrue(derived["committed"], derived)
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        recalled = self.memory.recall("Orrin gateway deploy window", temporal_intent=HIST)
        self.assertNotIn(derived["fact_uuid"], recalled["admitted"])
        for payload in (recalled, self.memory.history("memory:d"), self.memory.history("memory:a")):
            serial = _serial(payload)
            for fact_uuid in ids:
                self.assertNotIn(fact_uuid, serial)
            self.assertNotIn("Oslo", serial)
            self.assertNotIn("Bergen", serial)
        # the deletion itself is visible to its owner, the derived memory's taint is not a deletion
        self.assertTrue(self.memory.history("memory:a")["history"]["tombstoned"])
        self.assertFalse(self.memory.history("memory:d")["history"]["tombstoned"])

    def test_recall_by_logical_reference_is_indistinguishable_out_of_scope(self):
        self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:b")
        deleted = self.memory.recall("Orrin gateway region", logical_memory_refs=("memory:a",), temporal_intent=HIST)
        never = self.memory.recall("Orrin gateway region", logical_memory_refs=("memory:never",), temporal_intent=HIST)
        for view in (deleted, never):
            view.get("recall_control", {}).get("usage", {}).pop("elapsed_ms", None)
        self.assertEqual(_serial(deleted).replace("memory:a", "memory:never"), _serial(never))


class PermanentDeletionVisibility(unittest.TestCase):
    """Permanent deletion erases the content; the owner still learns the memory is tombstoned."""

    TENANT, PROJECT = "tenant:c644", "project:a"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name + "/m"
        self.registry = VerifierRegistry()
        self._verifiers = []
        self.registry.register(TRANSITION_VERIFIER, lambda item: any(v(item) for v in self._verifiers))

    def open(self, scope=PROJECT):
        return AgentMemory.open(self.root, tenant=self.TENANT, actor_id="agent:c644", scope=scope,
                                purpose="c644", verifier_registry=self.registry)

    def purge(self, memory_handle, memory):
        corpus = corpus_for(rule(rule_id=f"rule:777r:{memory}:purge", target=memory,
                                 criterion="permanent-deletion", from_state="current", to_values=("deleted",)))
        self._verifiers.append(corpus.verifier())
        proposal = replace(_proposal(f"proposal:777r:{memory}:purge", operation="permanent_deletion",
                                     project_ref=self.PROJECT),
                           target_reference=memory, review_satisfied=True, approval_refs=("approval:dpo",),
                           reversibility="irreversible")
        with memory_handle.runtime.serialization_lock:
            out = memory_handle.runtime.delete_current(
                proposal, evidence=corpus.evidence_for(target_reference=memory, criterion="permanent-deletion",
                                                       pre_state="current", proposed_value="deleted"))
        self.assertTrue(out.committed, out)
        return out

    def test_owner_reads_tombstoned_and_no_byte_of_content_survives_in_public_reads(self):
        memory = self.open()
        first = memory.remember("memory:a", "Orrin gateway region is Oslo", proposition=_prop("Oslo"))
        second = memory.correct("memory:a", "Orrin gateway region is Bergen", evidence=_evidence(),
                                risk_class="low", replacement_kind="state_change")
        self.assertTrue(first["committed"] and second["committed"], (first, second))
        self.purge(memory, "memory:a")
        for label in ("live process", "after restart"):
            with self.subTest(label):
                record = memory.history("memory:a")["history"]
                self.assertTrue(record["tombstoned"])
                self.assertIsNone(record["current_fact_uuid"])
                self.assertEqual(record["events"], [])
                recalled = memory.recall("Orrin gateway region", temporal_intent=HIST)
                serial = _serial([memory.history("memory:a"), recalled,
                                  memory.history("memory:a", fact_text="Orrin gateway region is Oslo")])
                for token in (first["fact_uuid"], second["fact_uuid"], "Oslo", "Bergen"):
                    self.assertNotIn(token, serial)
                self.assertIsNone(memory.write_semantics(first["fact_uuid"]))
                self.assertIsNone(memory.write_semantics(second["fact_uuid"]))
                memory.close()
                memory = self.open()
        memory.close()
        other = self.open("project:b")
        self.assertEqual(_serial(other.history("memory:a")), _serial(other.history("memory:never")))
        other.close()


if __name__ == "__main__":
    unittest.main()


class NoDeletionProjectionIsIdentity(_Facade):
    """With no governed deletion the public projection is the canonical document (#777 cost)."""

    def test_scrub_without_withholding_equals_the_general_path(self):
        from agentmem_ref.api import surface
        value = {"a": [("x", "y"), {"b": ("c",), "d": [1, 2, (3, 4)]}], "e": ("f",), "g": "h", "i": None}
        self.assertEqual(surface._scrub(value, surface._never), surface._scrub(value, lambda v: False))
        self.assertEqual(surface._scrub(value, surface._never), surface._normalize(value))
        self.assertIsNot(surface._scrub(value, surface._never)["a"], value["a"])

    def test_public_recall_equals_canonical_recall_until_a_deletion_exists(self):
        self.state_changed()
        self.memory.remember("memory:live", "Orrin gateway owner is Team Kite")
        self.assertFalse(self.memory.runtime.adapter.has_governed_deletions())
        public = self.memory.recall("Orrin gateway", temporal_intent=HIST)
        canonical = self.memory._canonical_recall("Orrin gateway", temporal_intent=HIST)
        self.assertEqual(public["public_projection"]["deleted_lineage"], "withheld")
        volatile = {"decision_id", "receipt_id", "evaluated_at", "receipt_ref", "correlation_id", "timestamp", "elapsed_ms"}

        def stable(value):  # each recall mints its own receipt id and clock reading
            if isinstance(value, dict):
                return {k: stable(v) for k, v in value.items() if k not in volatile}
            if isinstance(value, (list, tuple)):
                return [stable(v) for v in value]
            return value

        for key in ("candidates", "admitted", "admissions", "returned", "return_policy", "candidate_policy"):
            self.assertEqual(_serial(stable(public[key])), _serial(stable(canonical[key])), key)
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertTrue(self.memory.runtime.adapter.has_governed_deletions())
        public = self.memory.recall("Orrin gateway", temporal_intent=HIST)
        canonical = self.memory._canonical_recall("Orrin gateway", temporal_intent=HIST)
        self.assertLess(len(public["candidates"]), len(canonical["candidates"]))
