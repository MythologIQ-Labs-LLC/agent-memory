"""Unit checks for the thin MCP/AgentMemory adapter, no sandbox network."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge import HostConfig, LocalMemoryBridge


class FakeMemory:
    calls: list

    def __init__(self, calls):
        self.calls = calls

    def remember(self, key, text, **kwargs):
        self.calls.append(("remember", key, text, kwargs))
        return {"committed": True, "fact_uuid": "fact:qualified-1", "stage": "commit"}

    def recall_context(self, question, **kwargs):
        self.calls.append(("recall_context", question, kwargs))
        return {
            "status": "complete",
            "items": [
                {
                    "state": "resolved",
                    "content": "Our editor is Neovim.",
                    "fact_ref": "fact:qualified-1",
                    "provenance": {"memory_ref": "memory:editor", "currentness": "current_state"},
                },
                {"state": "omitted_selection", "fact_ref": "fact:distractor",
                 "reason": "subject_mismatch"},
            ],
            "selection": {"assessment": "evidence_delivered"},
        }


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.closes = []
        self.config = HostConfig(Path("/tmp/agent-mcp-test"), "tenant:a", "agent:local", "project:local")

        @contextmanager
        def opener(path, **kwargs):
            self.calls.append(("open", path, kwargs))
            try:
                yield FakeMemory(self.calls)
            finally:
                self.closes.append("closed")

        self.bridge = LocalMemoryBridge(self.config, opener)

    def test_save_calls_real_facade_contract_and_closes(self):
        result = self.bridge.remember("memory:editor", "Our editor is Neovim.")
        self.assertEqual(result["fact_ref"], "fact:qualified-1")
        self.assertTrue(result["committed"])
        self.assertIn(("remember", "memory:editor", "Our editor is Neovim.",
                       {"source_ref": "mcp:agent-observation"}), self.calls)
        self.assertEqual(self.closes, ["closed"])
        opened = self.calls[0]
        self.assertEqual(opened[2]["tenant"], "tenant:a")
        self.assertEqual(opened[2]["scope"], "project:local")

    def test_refused_write_is_not_reported_as_remembered(self):
        refusal = {
            "committed": False,
            "fact_uuid": None,
            "stage": "commit",
            "outcome": "refuse",
            "refusal": "governed_write_refused",
        }
        with patch.object(FakeMemory, "remember", return_value=refusal):
            outcome = self.bridge.remember("memory:refused", "Unverified assertion.")
        self.assertFalse(outcome["committed"])
        self.assertIsNone(outcome["fact_ref"])
        self.assertEqual(outcome["refusal"], "governed_write_refused")
        self.assertEqual(self.closes, ["closed"])

    def test_find_returns_bounded_untrusted_evidence_not_a_generated_answer(self):
        result = self.bridge.find("preferred editor", max_items=3)
        self.assertEqual(result["evidence_count"], 1)
        self.assertFalse(result["answer_generated"])
        self.assertFalse(result["answerability_verified"])
        self.assertEqual(result["evidence"][0]["trust"], "untrusted_memory_text")
        self.assertEqual(result["unavailable"][0]["reason"], "subject_mismatch")
        args = [v for v in self.calls if v[0] == "recall_context"][0][2]
        self.assertEqual(args["consumer_profile"], "all_returned")
        self.assertEqual(args["max_items"], 3)
        self.assertEqual(self.closes, ["closed"])

    def test_selectivity_is_explicit_opt_in(self):
        self.bridge.find("preferred editor", experimental_selectivity=True)
        args = [v for v in self.calls if v[0] == "recall_context"][0][2]
        self.assertEqual(args["consumer_profile"], "evidence_qualified")

    def test_exact_key_uses_governed_logical_memory_ref(self):
        self.bridge.get("memory:editor")
        args = [v for v in self.calls if v[0] == "recall_context"][0][2]
        self.assertEqual(args["logical_memory_refs"], ("memory:editor",))
        self.assertEqual(args["max_items"], 8)

    def test_exact_get_does_not_launder_similar_but_wrong_memory(self):
        # Governed recall is a multi-route candidate source. Even when
        # logical_memory_refs contains the requested key, the wrapper must
        # verify actual source provenance and not return an adjacent fact.
        def wrong_fact(self_, query, **kwargs):
            return {
                "status": "complete",
                "items": [
                    {"fact_ref": "fact:other", "state": "resolved",
                     "content": "The editor is Vim.",
                     "provenance": {"memory_ref": "memory:other",
                                    "source_ref": "mcp:agent-observation"}},
                    {"fact_ref": "fact:withheld", "state": "unresolved",
                     "reason": "withheld"},
                ],
            }

        with patch.object(FakeMemory, "recall_context", wrong_fact):
            response = self.bridge.get("memory:editor")
        self.assertEqual(response["lookup_status"], "not_found_or_unavailable")
        self.assertEqual(response["evidence"], [])
        self.assertEqual(response["evidence_count"], 0)
        self.assertEqual(response["unavailable"], [])
        self.assertNotIn("Vim", repr(response))
        self.assertNotIn("fact:other", repr(response))

    def test_exact_get_returns_only_correct_key_in_mixed_results(self):
        def mixed(self_, query, **kwargs):
            return {
                "status": "complete",
                "items": [
                    {"fact_ref": "fact:other", "state": "resolved",
                     "content": "Vim", "provenance": {"memory_ref": "memory:other"}},
                    {"fact_ref": "fact:matching", "state": "resolved",
                     "content": "Neovim", "provenance": {"memory_ref": "memory:editor"}},
                ],
            }

        with patch.object(FakeMemory, "recall_context", mixed):
            response = self.bridge.get("memory:editor")
        self.assertEqual(response["lookup_status"], "found")
        self.assertEqual([item["content"] for item in response["evidence"]], ["Neovim"])
        self.assertNotIn("Vim", repr(response))

    def test_invalid_request_never_opens_store(self):
        for bad in ("", " ", "x" * 161):
            with self.subTest(bad=bad[:3]), self.assertRaises(ValueError):
                self.bridge.get(bad)
        with self.assertRaises(ValueError):
            self.bridge.find("query", max_items=True)
        with self.assertRaises(ValueError):
            self.bridge.remember("memory:ok", "x" * 4001)
        self.assertFalse(self.calls)

    def test_missing_host_claims_fail_closed(self):
        with patch.dict(os.environ, {
            "AGENT_MEMORY_MCP_ROOT": "/tmp/agent-memory-dev",
            "AGENT_MEMORY_MCP_TENANT": "tenant:a",
            "AGENT_MEMORY_MCP_ACTOR": "agent:local",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "SCOPE"):
                HostConfig.from_environment()

    def test_relative_root_rejected(self):
        with patch.dict(os.environ, {
            "AGENT_MEMORY_MCP_ROOT": "./relative",
            "AGENT_MEMORY_MCP_TENANT": "tenant:a",
            "AGENT_MEMORY_MCP_ACTOR": "agent:local",
            "AGENT_MEMORY_MCP_SCOPE": "project:local",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "absolute"):
                HostConfig.from_environment()

    def test_symlinked_root_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            real = Path(temporary) / "real"
            real.mkdir()
            link = Path(temporary) / "link"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlink privilege unavailable: {error}")
            with patch.dict(os.environ, {
                "AGENT_MEMORY_MCP_ROOT": str(link),
                "AGENT_MEMORY_MCP_TENANT": "tenant:a",
                "AGENT_MEMORY_MCP_ACTOR": "agent:local",
                "AGENT_MEMORY_MCP_SCOPE": "project:local",
            }, clear=True):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    HostConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
