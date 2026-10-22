"""Cross-tranche characterization: packaged #840 gate + #839 context delivery.

This is unqualified integrated-preview test coverage, not successor lane evidence.
The standalone #839/#840 passing logs belong to their original revision pins.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentmem_ref import AgentMemory
from agentmem_ref.host_activation import UnqualifiedLegacyStoreError, open_qualified_memory


ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT / "reference/fixtures/809-legacy-stores"
TENANT, SCOPE = "tenant:integration", "project:integration"
TEXT = "The orchard gate code is 4471."


def _identity(actor: str) -> dict:
    return dict(tenant=TENANT, actor_id=actor, scope=SCOPE, purpose="integration challenge")


class GuardedContextDelivery(unittest.TestCase):
    def test_fresh_guarded_context_delivery_receipt_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "store"
            with open_qualified_memory(root, **_identity("agent:writer")) as memory:
                written = memory.remember("memory:orchard-gate", TEXT, source_ref="evidence:owner")
                self.assertTrue(written["committed"], written)
                package = memory.recall_context("orchard gate code", max_items=3)
                self.assertEqual(package["status"], "complete")
                self.assertEqual(package["items"][0]["content"], TEXT)
                self.assertEqual(package["items"][0]["fact_ref"], written["fact_uuid"])
                events = [e for e in memory.runtime.adapter.events
                          if e.get("event_type") == "memory.context_delivery"]
                self.assertEqual(len(events), 1)
                self.assertEqual(package["audit"]["delivery_event_id"], events[0]["event_id"])
                self.assertEqual(package["audit"]["recall_event_id"], events[0]["causation_id"])
                self.assertEqual(package["audit"]["correlation_id"], events[0]["correlation_id"])
            with open_qualified_memory(root, **_identity("agent:writer")) as recovered:
                self.assertEqual(recovered.legacy_upgrade_status()["status"], "fresh")
                package = recovered.recall_context("orchard gate code", max_items=3)
                self.assertEqual([x["content"] for x in package["items"]], [TEXT])

    def test_another_authenticated_actor_gets_text_not_writer_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "store"
            with open_qualified_memory(root, **_identity("agent:writer")) as memory:
                self.assertTrue(memory.remember(
                    "memory:orchard-gate", TEXT, source_ref="private:owner-identifier"
                )["committed"])
            with open_qualified_memory(root, **_identity("agent:colleague")) as reader:
                package = reader.recall_context("orchard gate code")
                self.assertEqual([x["content"] for x in package["items"]], [TEXT])
                provenance = package["items"][0]["provenance"]
                self.assertNotIn("source_ref", provenance)
                self.assertNotIn("memory_ref", provenance)
                event = [x for x in reader.runtime.adapter.events
                         if x.get("event_type") == "memory.context_delivery"][-1]
                self.assertNotIn("private:owner-identifier", json.dumps(event))

    def test_pending_legacy_store_cannot_reach_context_delivery_through_host(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "store"
            shutil.copytree(LEGACY / "cross-scope", root)
            legacy_identity = dict(
                tenant="tenant:legacy", actor_id="agent:legacy", scope="project:b",
                purpose="integration challenge",
            )
            with patch.object(AgentMemory, "recall_context",
                              side_effect=AssertionError("unsafe content delivered")) as ctx:
                with self.assertRaises(UnqualifiedLegacyStoreError):
                    with open_qualified_memory(root, **legacy_identity):
                        self.fail("pending legacy store was handed to operational caller")
                ctx.assert_not_called()


if __name__ == "__main__":
    unittest.main()
