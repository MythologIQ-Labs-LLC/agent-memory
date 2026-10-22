"""#691 content-delivery audit receipt (``memory.context_delivery``).

A ``memory.recall`` event proves that identifiers were recalled; it does not prove that memory
text was delivered. ``AgentMemory.recall_context()`` therefore records one delivery receipt per
call, through the runtime's transactional seam, bound to the recall event (correlation and
causation) and to the admission decisions of the returned facts, naming only identifiers the
recall already returned to the caller and never the text. If the receipt cannot be recorded,
no content is delivered.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.api import surface
from agentmem_ref.api.context_package import DELIVERY_EVENT_TYPE, delivery_event, package_digest
from agentmem_ref.api.surface import ContextDeliveryUnboundError
from agentmem_ref.core import receipts
from agentmem_ref.memory import procedural_memory as pm

TENANT = "tenant:691-audit"
SCOPE = "project:691-audit"
TEXT = "The orchard gate code is 4471."
PRIVATE_SOURCE = "actor:writer-private"


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:691-audit", version=1, purpose="audit lifecycle", scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:test",),
    )
    return pm.evidence_for(skill)


def _delivery_events(memory):
    return [e for e in memory.runtime.adapter.events if e.get("event_type") == DELIVERY_EVENT_TYPE]


def _recall_events(memory):
    return [e for e in memory.runtime.adapter.events if e.get("event_type") == "memory.recall"]


class _Store(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory(prefix="agent-memory-691-audit-")
        self.root = Path(self._dir.name)
        self.memory = self.open()

    def tearDown(self):
        if not self.memory.closed:
            self.memory.close()
        self._dir.cleanup()

    def open(self, actor="agent:writer", scope=SCOPE):
        return AgentMemory.open(self.root, tenant=TENANT, actor_id=actor, scope=scope, purpose="audit test")

    def reopen(self, **kwargs):
        self.memory.close()
        self.memory = self.open(**kwargs)


class Receipt(_Store):
    def test_one_receipt_per_delivery_bound_to_the_recall_and_its_decisions(self):
        self.memory.remember("memory:gate", TEXT, source_ref=PRIVATE_SOURCE)
        self.memory.remember("memory:other", "The orchard is watered on Mondays.")
        self.assertEqual(_delivery_events(self.memory), [])
        package = self.memory.recall_context("orchard gate code", max_items=5)
        (event,) = _delivery_events(self.memory)
        recall = _recall_events(self.memory)[-1]
        receipts.validate("memory-audit-event.schema.json", event)
        self.assertEqual(event["correlation_id"], recall["correlation_id"])
        self.assertEqual(event["causation_id"], recall["event_id"])
        self.assertEqual(event["principal"], "agent:writer")
        self.assertEqual(event["component"], "public-facade")
        self.assertEqual(package["audit"], {"delivery_event_id": event["event_id"], "recall_event_id": recall["event_id"],
                                            "correlation_id": recall["correlation_id"]})
        payload = event["payload"]
        self.assertEqual(payload["actor_binding"], "host_declared")
        self.assertEqual(payload["project_ref"], SCOPE)
        self.assertEqual(payload["package_status"], package["status"])
        self.assertEqual(set(payload["outcomes"]), set(package["recall"]["returned"]))
        self.assertEqual(payload["recall_decision_ids"],
                         {item["fact_ref"]: item["provenance"]["admission_decision_id"] for item in package["items"]})
        for item in package["items"]:
            outcome = payload["outcomes"][item["fact_ref"]]
            self.assertEqual(outcome["state"], item["state"])
            self.assertEqual(outcome["content_sha256"], item["provenance"]["content_sha256"])
            self.assertEqual(outcome["delivered_chars"], len(item["content"]))
        self.assertEqual(payload["delivered_count"], len(package["items"]))
        self.assertEqual(payload["package_sha256"], package_digest(package))
        self.assertTrue(payload["recall_bound"])

    def test_receipt_carries_no_text_and_no_private_provenance(self):
        self.memory.remember("memory:gate", TEXT, source_ref=PRIVATE_SOURCE)
        self.reopen(actor="agent:colleague")
        package = self.memory.recall_context("orchard gate code", max_items=5)
        self.assertEqual([i["content"] for i in package["items"]], [TEXT])
        (event,) = _delivery_events(self.memory)
        dumped = json.dumps(event)
        for needle in (TEXT, "4471", PRIVATE_SOURCE, "memory:gate", "agent:writer"):
            self.assertNotIn(needle, dumped)
        self.assertEqual(event["principal"], "agent:colleague")
        # the digest of the delivered fact's source text, as the package's provenance carries it
        self.assertIn(hashlib.sha256(TEXT.encode()).hexdigest(), dumped)

    def test_plain_recall_and_refused_calls_record_no_delivery(self):
        self.memory.remember("memory:gate", TEXT)
        self.memory.recall("orchard gate code")
        self.assertEqual(_delivery_events(self.memory), [])
        before = len(self.memory.runtime.adapter.events)
        with self.assertRaises(TypeError):
            self.memory.recall_context("orchard", project_ref="project:other")
        with self.assertRaises(ValueError):
            self.memory.recall_context("orchard", max_items=0)
        self.assertEqual(len(self.memory.runtime.adapter.events), before)

    def test_receipt_survives_restart_and_is_not_a_history_record(self):
        self.memory.remember("memory:gate", TEXT)
        package = self.memory.recall_context("orchard gate code")
        self.reopen()
        (event,) = _delivery_events(self.memory)
        self.assertEqual(event["event_id"], package["audit"]["delivery_event_id"])
        # history() is the memory-scoped audit view; delivery receipts span a recall, not a memory
        self.assertNotIn(DELIVERY_EVENT_TYPE, json.dumps(self.memory.history("memory:gate")))

    def test_states_are_recorded_for_empty_truncated_exhausted_and_unresolved_packages(self):
        package = self.memory.recall_context("nothing remembered yet")
        self.assertEqual(package["status"], "empty")
        self.assertEqual(_delivery_events(self.memory)[-1]["payload"]["returned_count"], 0)
        long_text = "Orchard notes: " + "prune the apple trees in late winter. " * 30
        self.memory.remember("memory:long", long_text)
        for i in range(3):
            self.memory.remember(f"memory:n{i}", f"Orchard note {i}: mulch the beds.")
        package = self.memory.recall_context("orchard", max_items=4, max_chars_per_item=60, max_total_chars=100)
        payload = _delivery_events(self.memory)[-1]["payload"]
        self.assertEqual(payload["package_status"], package["status"])
        self.assertIn(package["status"], {"truncated", "budget_exhausted"})
        for item in package["items"]:
            outcome = payload["outcomes"][item["fact_ref"]]
            self.assertEqual(outcome["state"], item["state"])
            if item["state"] == "omitted_budget":
                self.assertNotIn("content_sha256", outcome)
            if item["state"] == "truncated":
                self.assertLess(outcome["delivered_chars"], item["provenance"]["content_chars"])
        self.assertEqual(payload["budget"]["max_total_chars"], 100)
        # unresolved: resolution fails after the recall succeeded
        adapter = self.memory.runtime.adapter
        original = adapter.memory_ref_of
        adapter.memory_ref_of = lambda uuid: (_ for _ in ()).throw(RuntimeError("disk read failed"))
        try:
            package = self.memory.recall_context("orchard note", max_items=2)
        finally:
            adapter.memory_ref_of = original
        self.assertEqual(package["status"], "partial_unresolved")
        payload = _delivery_events(self.memory)[-1]["payload"]
        self.assertEqual(payload["delivered_count"], 0)
        for outcome in payload["outcomes"].values():
            self.assertEqual(outcome, {"state": "unresolved", "reason": "content_read_failed"})

    def test_deleted_lineage_identifiers_never_enter_a_receipt(self):
        old = self.memory.remember("memory:gate", TEXT)["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:gate", evidence=_evidence())["committed"])
        self.memory.remember("memory:other", "The orchard gate is painted green.")
        package = self.memory.recall_context("orchard gate")
        self.assertNotIn(old, json.dumps(package))
        for event in _delivery_events(self.memory):
            self.assertNotIn(old, json.dumps(event))
            self.assertNotIn("4471", json.dumps(event))

    def test_unrecordable_receipt_delivers_nothing_and_leaves_the_store_usable(self):
        self.memory.remember("memory:gate", TEXT)
        durable = self.memory.runtime.durable_runtime
        original = durable.run_governed_read

        def failing(operation):
            raise RuntimeError("audit journal unavailable")

        durable.run_governed_read = failing
        try:
            with self.assertRaises(RuntimeError):
                self.memory.recall_context("orchard gate code")
        finally:
            durable.run_governed_read = original
        self.assertEqual(_delivery_events(self.memory), [])
        # lock released, store consistent, delivery works again and is recorded
        package = self.memory.recall_context("orchard gate code")
        self.assertEqual([i["content"] for i in package["items"]], [TEXT])
        self.assertEqual(len(_delivery_events(self.memory)), 1)
        self.assertTrue(self.memory.remember("memory:after", "Another orchard note.")["committed"])

    def test_receipt_rolls_back_with_its_generation(self):
        # a failure inside the seam, after the event was appended, must not leave the receipt behind
        self.memory.remember("memory:gate", TEXT)
        durable = self.memory.runtime.durable_runtime
        original = durable.run_governed_read

        def append_then_fail(operation):
            def wrapped():
                operation()
                raise RuntimeError("generation could not be published")
            return original(wrapped)

        durable.run_governed_read = append_then_fail
        try:
            with self.assertRaises(RuntimeError):
                self.memory.recall_context("orchard gate code")
        finally:
            durable.run_governed_read = original
        self.assertEqual(_delivery_events(self.memory), [])
        self.reopen()
        self.assertEqual(_delivery_events(self.memory), [])
        package = self.memory.recall_context("orchard gate code")
        self.assertEqual(len(_delivery_events(self.memory)), 1)
        self.assertEqual(package["audit"]["delivery_event_id"], _delivery_events(self.memory)[0]["event_id"])

    # #839 review A/B: the receipt is the last thing to happen, and only ever bound to a real recall.

    def test_receipt_is_appended_only_after_the_final_package_validates(self):
        self.memory.remember("memory:gate", TEXT)
        adapter = self.memory.runtime.adapter
        original = receipts.validate
        seen: list[str] = []

        def spy(schema_name, document):
            seen.append(schema_name)
            if schema_name == "api-context-package.schema.json":
                self.assertIn("audit", document)  # the complete output, audit block included
                self.assertEqual([e for e in adapter.events if e.get("event_type") == DELIVERY_EVENT_TYPE], [])
            return original(schema_name, document)

        with unittest.mock.patch.object(receipts, "validate", spy):
            package = self.memory.recall_context("orchard gate code")
        self.assertIn("api-context-package.schema.json", seen)
        self.assertEqual(len(_delivery_events(self.memory)), 1)
        self.assertEqual(package["audit"]["delivery_event_id"], _delivery_events(self.memory)[0]["event_id"])

    def test_missing_recall_event_refuses_delivery_without_a_receipt(self):
        self.memory.remember("memory:gate", TEXT)
        with unittest.mock.patch.object(surface, "_first_recall_event_since", return_value=None):
            with self.assertRaises(ContextDeliveryUnboundError):
                self.memory.recall_context("orchard gate code")
        self.assertEqual(_delivery_events(self.memory), [])
        with self.assertRaises(ValueError):
            delivery_event({}, {"items": []}, None, event_id="ref-x", timestamp="2026-01-01T00:00:00Z", recall_event=None)
        with self.assertRaises(ValueError):
            delivery_event({}, {"items": []}, None, event_id="ref-x", timestamp="2026-01-01T00:00:00Z",
                           recall_event={"event_id": "ref-y"})  # no correlation to inherit: nothing is synthesised
        package = self.memory.recall_context("orchard gate code")  # the store is usable and delivery resumes
        self.assertEqual([i["content"] for i in package["items"]], [TEXT])
        (event,) = _delivery_events(self.memory)
        self.assertEqual(event["causation_id"], _recall_events(self.memory)[-1]["event_id"])


class FailClosed(_Store):
    """#839 Phase 3: every way the receipt could be wrong, in memory and after reopening the store.
    A refusal never leaves a receipt; a receipt is only ever bound to the recall that authorised
    the identifiers it names; ordinary delivery keeps working afterwards."""

    def _refused(self, exc_type, query="orchard gate code"):
        before = len(self.memory.runtime.adapter.events)
        with self.assertRaises(exc_type):
            self.memory.recall_context(query)
        self.assertEqual(_delivery_events(self.memory), [])
        return before

    def _still_delivers(self):
        package = self.memory.recall_context("orchard gate code")
        self.assertEqual([i["content"] for i in package["items"]], [TEXT])
        events = _delivery_events(self.memory)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["causation_id"], package["audit"]["recall_event_id"])
        self.reopen()
        self.assertEqual([e["event_id"] for e in _delivery_events(self.memory)], [events[0]["event_id"]])

    def _real_recall_event(self):
        n = len(self.memory.runtime.adapter.events)
        self.memory.recall("orchard gate code")
        return next(e for e in self.memory.runtime.adapter.events[n:] if e["event_type"] == "memory.recall")

    def test_malformed_recall_event_is_refused(self):
        self.memory.remember("memory:gate", TEXT)
        real = self._real_recall_event()
        for defect in ({"event_type": "memory.commit"}, {"event_id": ""}, {"correlation_id": None},
                       {"principal": "agent:someone-else"}, {"payload": {**real["payload"], "project_ref": "project:other"}},
                       {"payload": {**real["payload"], "outcomes": {}}},
                       {"payload": {**real["payload"], "outcomes": {k: "refused" for k in real["payload"]["outcomes"]}}}):
            with unittest.mock.patch.object(surface, "_first_recall_event_since", return_value={**real, **defect}):
                self._refused(ContextDeliveryUnboundError)
        self.reopen()
        self.assertEqual(_delivery_events(self.memory), [])
        self._still_delivers()

    def test_another_actors_recall_event_is_refused(self):
        self.memory.remember("memory:gate", TEXT)
        self.reopen(actor="agent:colleague")
        foreign = self._real_recall_event()
        self.reopen(actor="agent:writer")
        with unittest.mock.patch.object(surface, "_first_recall_event_since", return_value=foreign):
            self._refused(ContextDeliveryUnboundError)
        self._still_delivers()

    def test_event_append_failure_leaves_no_receipt(self):
        self.memory.remember("memory:gate", TEXT)
        adapter = self.memory.runtime.adapter

        class Refusing(list):
            def append(self, item):
                raise RuntimeError("journal append failed")

        broken = Refusing(adapter.events)
        with unittest.mock.patch.object(adapter, "events", broken):
            self._refused(RuntimeError)
        self.reopen()
        self.assertEqual(_delivery_events(self.memory), [])
        self._still_delivers()

    def test_persistence_failure_rolls_the_receipt_back_and_restarts_clean(self):
        self.memory.remember("memory:gate", TEXT)
        durable = self.memory.runtime.durable_runtime
        sqlite_runtime = getattr(durable, "base", durable)  # the SQLite generation publisher

        def failing():
            raise OSError("disk full while publishing the generation")

        with unittest.mock.patch.object(sqlite_runtime, "_persist_unlocked", failing):
            self._refused(OSError)
        # governance restored from the last published generation: no receipt, store consistent
        self.assertEqual(_delivery_events(self.memory), [])
        self.reopen()
        self.assertEqual(_delivery_events(self.memory), [])
        self.assertTrue(self.memory.remember("memory:after", "The greenhouse thermostat reads 18 degrees.")["committed"])
        self._still_delivers()

    def test_invalid_completed_package_with_audit_identifiers_is_refused(self):
        self.memory.remember("memory:gate", TEXT)
        original = receipts.validate

        def reject_with_audit(schema_name, document):
            if schema_name == context_package_schema() and "audit" in document:
                raise ValueError("completed package rejected")
            return original(schema_name, document)

        with unittest.mock.patch.object(receipts, "validate", reject_with_audit):
            self._refused(ValueError)
        self.reopen()
        self.assertEqual(_delivery_events(self.memory), [])
        self._still_delivers()

    def test_repeated_deliveries_have_unique_ids_and_distinct_recalls(self):
        self.memory.remember("memory:gate", TEXT)
        packages = [self.memory.recall_context("orchard gate code") for _ in range(5)]
        events = _delivery_events(self.memory)
        self.assertEqual(len(events), 5)
        self.assertEqual(len({e["event_id"] for e in events}), 5)
        self.assertEqual(len({e["causation_id"] for e in events}), 5)
        self.assertEqual([e["event_id"] for e in events], [p["audit"]["delivery_event_id"] for p in packages])
        recall_ids = {e["event_id"] for e in _recall_events(self.memory)}
        self.assertTrue(all(e["causation_id"] in recall_ids for e in events))
        self.reopen()
        self.assertEqual([e["event_id"] for e in _delivery_events(self.memory)], [p["audit"]["delivery_event_id"] for p in packages])

    def test_shadow_recall_control_binds_to_the_executed_recall(self):
        self.memory.remember("memory:gate", TEXT)
        self.memory.close()
        self.memory = AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:writer", scope=SCOPE,
                                       purpose="audit test", recall_control="shadow")
        n = len(self.memory.runtime.adapter.events)
        package = self.memory.recall_context("orchard gate code")
        new = self.memory.runtime.adapter.events[n:]
        self.assertEqual([e["event_type"] for e in new], ["memory.recall", DELIVERY_EVENT_TYPE])
        self.assertEqual(new[1]["causation_id"], new[0]["event_id"])
        self.assertEqual(package["audit"]["recall_event_id"], new[0]["event_id"])

    def test_other_project_receipt_names_nothing_of_this_project(self):
        self.memory.remember("memory:gate", TEXT, source_ref=PRIVATE_SOURCE)
        self.reopen(scope="project:691-other")
        package = self.memory.recall_context("orchard gate code")
        self.assertEqual(package["status"], "empty")
        (event,) = _delivery_events(self.memory)
        self.assertEqual((event["payload"]["returned_count"], event["payload"]["outcomes"]), (0, {}))
        self.assertEqual(event["payload"]["project_ref"], "project:691-other")
        for needle in (TEXT, "4471", PRIVATE_SOURCE, "memory:gate", SCOPE):
            self.assertNotIn(needle, json.dumps(event))


def context_package_schema():
    from agentmem_ref.api import context_package
    return context_package.PACKAGE_SCHEMA


if __name__ == "__main__":
    unittest.main()
