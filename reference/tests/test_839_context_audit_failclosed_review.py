"""Adversarial review probes for #839 context delivery audit integrity.

Preregistered *expected* fail-closed behavior on exactly 2f9ce22b.
Tests are intentionally red on the source head until the audit boundaries
are repaired. No product code, baseline, schema or accepted evidence changed.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref import AgentMemory
from agentmem_ref.api import context_package, surface


TENANT = "tenant:839-audit-integrity"
SCOPE = "project:839-audit-integrity"
TEXT = "The laboratory gate is painted coral."


def delivery_events(handle: AgentMemory) -> list[dict]:
    return [
        e for e in handle.runtime.adapter.events
        if e.get("event_type") == context_package.DELIVERY_EVENT_TYPE
    ]


class AuditCommitOrdering(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="agent-memory-839-")
        self.root = Path(self.temp.name)
        self.memory = AgentMemory.open(
            self.root, tenant=TENANT, actor_id="agent:owner",
            scope=SCOPE, purpose="post-v7 audit integrity probe",
        )
        self.assertTrue(self.memory.remember("memory:gate", TEXT)["committed"])

    def tearDown(self) -> None:
        if not self.memory.closed:
            self.memory.close()
        self.temp.cleanup()

    def test_rejected_final_package_cannot_leave_a_durable_delivery_receipt(self) -> None:
        """Fault in the *post-audit* schema validation should not claim delivery.

        The current code writes and durably commits the audit, *then* runs
        receipts.validate(PACKAGE_SCHEMA, package). Patch just that schema name
        so the final validation fails. No package reaches the caller.
        """
        self.assertEqual(delivery_events(self.memory), [])
        with mock.patch.object(
            context_package, "PACKAGE_SCHEMA", "missing-839-intentional-schema.json"
        ):
            with self.assertRaises(Exception):
                self.memory.recall_context("laboratory gate coral")

        # The receipt must not claim delivery for a failed call, in memory
        # or across a process restart. A recall-only audit can remain.
        self.assertEqual(delivery_events(self.memory), [],
                         "delivery audit committed before the package passed validation")
        self.memory.close()
        self.memory = AgentMemory.open(
            self.root, tenant=TENANT, actor_id="agent:owner",
            scope=SCOPE, purpose="post-v7 audit integrity probe",
        )
        self.assertEqual(delivery_events(self.memory), [])

    def test_missing_recall_event_must_not_be_synthesized_as_bound_delivery(self) -> None:
        """A content receipt claiming recall linkage must cite an actual recall event.

        The current delivery_event() accepts recall_event=None and substitutes
        its own event id as correlation_id, leaving recall_bound=false.
        Merely returning an audit id is not binding to a source recall.
        """
        with mock.patch.object(surface, "_first_recall_event_since", return_value=None):
            with self.assertRaises(Exception):
                self.memory.recall_context("laboratory gate coral")

        self.assertEqual(delivery_events(self.memory), [],
                         "unbound audit receipt must not claim delivered content")

    def test_normal_delivery_still_binds_recall_and_survives_reopen(self) -> None:
        """Positive control prevents refusal of all content as a false security fix."""
        package = self.memory.recall_context("laboratory gate coral")
        self.assertEqual([i["content"] for i in package["items"]], [TEXT])
        (receipt,) = delivery_events(self.memory)
        recalls = [e for e in self.memory.runtime.adapter.events
                   if e.get("event_type") == "memory.recall"]
        self.assertTrue(recalls)
        self.assertEqual(receipt.get("causation_id"), recalls[-1]["event_id"])
        self.assertTrue(receipt["payload"]["recall_bound"])
        self.assertEqual(package["audit"]["delivery_event_id"], receipt["event_id"])
        self.memory.close()
        self.memory = AgentMemory.open(
            self.root, tenant=TENANT, actor_id="agent:owner",
            scope=SCOPE, purpose="post-v7 audit integrity probe",
        )
        self.assertEqual(delivery_events(self.memory)[0]["event_id"], receipt["event_id"])


if __name__ == "__main__":
    unittest.main()
