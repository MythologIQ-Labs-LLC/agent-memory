"""Fail-closed tests for the optional, explicitly head-only MCP lifecycle tool."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge import HostConfig, LocalMemoryBridge


class FakeRuntime:
    def __init__(self, head="fact:head", outcome=None):
        self.head = head
        self.outcome = outcome if outcome is not None else {"committed": True}
        self.calls = []

    def history(self, key):
        self.calls.append(("history", key))
        return {"history": {"current_fact_uuid": self.head}}

    def forget(self, key, **kwargs):
        self.calls.append(("forget", key, kwargs))
        return self.outcome


class HeadTombstoneTests(unittest.TestCase):
    def setUp(self):
        self.memory = FakeRuntime()
        self.opens = []
        @contextmanager
        def open_memory(root, **kwargs):
            self.opens.append((root, kwargs))
            yield self.memory
        self.bridge = LocalMemoryBridge(
            HostConfig(Path("/tmp/mcp-tombstone-test"), "tenant:one", "actor:one", "project:one"),
            open_memory,
        )

    def _run_enabled(self, key="memory:editor", fact="fact:head"):
        with patch.dict(os.environ, {"AGENT_MEMORY_MCP_ALLOW_HEAD_TOMBSTONE": "enabled"}):
            return self.bridge.tombstone_head(key, fact)

    def test_host_gate_refuses_without_open(self):
        with patch.dict(os.environ, {"AGENT_MEMORY_MCP_ALLOW_HEAD_TOMBSTONE": ""}):
            with self.assertRaises(ValueError):
                self.bridge.tombstone_head("memory:editor", "fact:head")
        self.assertEqual(self.opens, [])

    def test_invalid_arguments_refuse_before_open(self):
        for key, fact in [("", "fact:head"), ("memory:editor", ""), (" " * 4, "fact:head"), ("x" * 161, "fact:head")]:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self._run_enabled(key, fact)
        self.assertEqual(self.opens, [])

    def test_foreign_absent_and_stale_heads_have_same_public_result(self):
        responses = []
        for visible in (None, "fact:other"):
            self.memory = FakeRuntime(head=visible)
            responses.append(self._run_enabled())
            self.assertEqual(self.memory.calls, [("history", "memory:editor")])
        self.assertEqual(responses[0], responses[1])
        self.assertFalse(responses[0]["committed"])
        self.assertEqual(responses[0]["status"], "unavailable_or_changed")
        self.assertNotIn("fact:other", repr(responses))

    def test_prunes_only_the_visible_head_without_permanent_delete(self):
        result = self._run_enabled()
        self.assertTrue(result["committed"])
        self.assertEqual(result["status"], "head_tombstoned")
        self.assertFalse(result["permanent"])
        self.assertTrue(result["head_only"])
        self.assertFalse(result["older_generations_checked"])
        self.assertIn("not permanent deletion", result["warning"])
        self.assertEqual(self.memory.calls, [
            ("history", "memory:editor"),
            ("forget", "memory:editor", {"permanent": False}),
        ])
        self.assertNotIn("fact:head", repr(result))

    def test_governed_refusal_is_not_reported_as_success(self):
        self.memory.outcome = {"committed": False, "refusal": "requires_review"}
        result = self._run_enabled()
        self.assertFalse(result["committed"])
        self.assertEqual(result["status"], "governed_refusal")
        self.assertNotIn("requires_review", repr(result))


if __name__ == "__main__":
    unittest.main()
