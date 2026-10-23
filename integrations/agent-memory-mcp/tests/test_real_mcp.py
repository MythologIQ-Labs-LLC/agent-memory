"""Real SDK and real SQLite facade: agent-harness contract smoke (no mocks).

Requires: pip install -e . 'mcp>=2,<3'
Run from repo root:
  python -m unittest discover -s integrations/agent-memory-mcp/tests -p 'test_real_mcp.py' -v
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("agent_memory_mcp_consumer", HERE / "server.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _result(result, field):
    if result.is_error:
        raise AssertionError(f"MCP tool failed: {result.content!r}")
    body = result.structured_content
    if isinstance(body, dict) and field in body:
        return body
    if isinstance(body, dict) and isinstance(body.get("result"), dict):
        return body["result"]
    raise AssertionError(f"MCP result missing expected field {field!r}: {result!r}")


class ActualMcpConsumerLoop(unittest.IsolatedAsyncioTestCase):
    async def test_real_store_exact_retrieve_find_and_reconnect(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "my-memory"
            env = {
                "AGENT_MEMORY_MCP_ROOT": str(root),
                "AGENT_MEMORY_MCP_TENANT": "tenant:mcp-smoke",
                "AGENT_MEMORY_MCP_ACTOR": "agent:mcp-smoke",
                "AGENT_MEMORY_MCP_SCOPE": "project:mcp-smoke",
            }
            with patch.dict(os.environ, env):
                async with Client(module.mcp, raise_exceptions=True) as client:
                    saved = _result(
                        await client.call_tool("memory_remember", {
                            "key": "memory:preferred_editor",
                            "text": "The editor I use for code is Neovim.",
                        }),
                        "committed",
                    )
                    self.assertTrue(saved["committed"], saved)
                    exact = _result(
                        await client.call_tool("memory_get", {"key": "memory:preferred_editor"}),
                        "evidence",
                    )
                    self.assertTrue(any(
                        "Neovim" in item["content"] for item in exact["evidence"]
                    ), exact)
                    found = _result(
                        await client.call_tool("memory_find", {
                            "question": "Which editor do I use for code?",
                            "max_items": 5,
                        }),
                        "evidence",
                    )
                    self.assertTrue(any(
                        "Neovim" in item["content"] for item in found["evidence"]
                    ), found)
                    self.assertFalse(found["answer_generated"])
                    self.assertEqual(found["profile"], "all_returned")
                    # A similar or nonexistent key must never return a
                    # nearby memory as an exact-key lookup success.
                    absent = _result(await client.call_tool("memory_get", {
                        "key": "memory:preferred_editors",
                    }), "evidence")
                    self.assertEqual(absent["lookup_status"], "not_found_or_unavailable")
                    self.assertEqual(absent["evidence"], [])
                    self.assertNotIn("Neovim", repr(absent))
                # Reconnecting the harness must recover the same durable store.
                async with Client(module.mcp, raise_exceptions=True) as client:
                    recovered = _result(
                        await client.call_tool("memory_get", {"key": "memory:preferred_editor"}),
                        "evidence",
                    )
                    self.assertTrue(any(
                        "Neovim" in item["content"] for item in recovered["evidence"]
                    ), recovered)

    async def test_selectivity_declines_are_visible_with_their_grounding(self):
        """Policy 0.5.0 through the real server: a returned third-person memory about another
        named subject that shares no content term with the question is declined, listed under
        ``unavailable`` with state ``omitted_selection``, its reason and what grounded the
        absence; without the opt-in the same memory is delivered. The recall is unchanged."""
        with tempfile.TemporaryDirectory() as temp:
            env = {
                "AGENT_MEMORY_MCP_ROOT": str(Path(temp) / "store"),
                "AGENT_MEMORY_MCP_TENANT": "tenant:mcp-select",
                "AGENT_MEMORY_MCP_ACTOR": "agent:mcp-select",
                "AGENT_MEMORY_MCP_SCOPE": "project:mcp-select",
            }
            with patch.dict(os.environ, env):
                async with Client(module.mcp, raise_exceptions=True) as client:
                    for key, text in (
                        ("memory:printer", "The office printer is a Brother HL-L2400D. Its toner is TN830."),
                        ("memory:liora-canoe", "Liora's canoe is teal. The hull was inspected on Tuesday."),
                    ):
                        saved = _result(await client.call_tool("memory_remember", {"key": key, "text": text}), "committed")
                        self.assertTrue(saved["committed"], saved)
                    question = {"question": "What model is the office printer?", "max_items": 5}
                    plain = _result(await client.call_tool("memory_find", question), "evidence")
                    self.assertEqual(plain["profile"], "all_returned")
                    self.assertEqual({e["memory_ref"] for e in plain["evidence"]}, {"memory:printer", "memory:liora-canoe"})
                    self.assertIsNone(plain["selection_policy_version"])
                    selective = _result(await client.call_tool("memory_find", {
                        **question, "experimental_selectivity": True}), "evidence")
                    self.assertEqual(selective["profile"], "evidence_qualified")
                    self.assertEqual([e["memory_ref"] for e in selective["evidence"]], ["memory:printer"])
                    self.assertEqual(selective["selection_assessment"], "evidence_delivered")
                    self.assertEqual(selective["selection_policy_version"], "0.5.0")
                    declined = [u for u in selective["unavailable"] if u["state"] == "omitted_selection"]
                    self.assertEqual(len(declined), 1, selective["unavailable"])
                    self.assertEqual(declined[0]["reason"], "no_query_term_evidence")
                    self.assertEqual(declined[0]["absence_grounding"], "fact_subject_absent")
                    self.assertEqual(declined[0]["fact_subjects"], ["liora"])
                    self.assertEqual(declined[0]["query_subjects"], [])
                    self.assertNotIn("teal", json.dumps(selective))
                    self.assertFalse(selective["answer_generated"])

    async def test_separately_configured_project_cannot_read_other_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "my-memory"
            env = {
                "AGENT_MEMORY_MCP_ROOT": str(root),
                "AGENT_MEMORY_MCP_TENANT": "tenant:two-scopes",
                "AGENT_MEMORY_MCP_ACTOR": "agent:owner",
                "AGENT_MEMORY_MCP_SCOPE": "project:private",
            }
            with patch.dict(os.environ, env):
                async with Client(module.mcp, raise_exceptions=True) as client:
                    saved = _result(await client.call_tool("memory_remember", {
                        "key": "memory:private:editor",
                        "text": "The private editor choice is Neovim.",
                    }), "committed")
                    self.assertTrue(saved["committed"])
            with patch.dict(os.environ, {**env, "AGENT_MEMORY_MCP_SCOPE": "project:other"}):
                async with Client(module.mcp, raise_exceptions=True) as client:
                    result = _result(await client.call_tool("memory_get", {
                        "key": "memory:private:editor",
                    }), "evidence")
                    self.assertEqual(result["evidence"], [])
                    self.assertNotIn("Neovim", repr(result))

    async def test_real_stdio_subprocess_reconnects_to_durable_memory(self):
        # An in-process Client(mcp) verifies the protocol API, but does not
        # prove that a harness can start a subprocess or communicate over
        # JSON-RPC stdio. This control covers the actual user-visible path.
        with tempfile.TemporaryDirectory() as temp:
            env = {
                "AGENT_MEMORY_MCP_ROOT": str(Path(temp) / "store"),
                "AGENT_MEMORY_MCP_TENANT": "tenant:stdio",
                "AGENT_MEMORY_MCP_ACTOR": "agent:stdio",
                "AGENT_MEMORY_MCP_SCOPE": "project:stdio",
            }
            params = StdioServerParameters(
                command=sys.executable, args=[str(HERE / "server.py")], env=env,
            )
            async with Client(params) as client:
                tools = await client.list_tools()
                self.assertEqual(
                    {tool.name for tool in tools.tools},
                    {"memory_remember", "memory_get", "memory_find"},
                )
                created = _result(await client.call_tool("memory_remember", {
                    "key": "memory:agent:editor",
                    "text": "Our agent writes Python using Neovim.",
                }), "committed")
                self.assertTrue(created["committed"], created)
                queried = _result(await client.call_tool("memory_find", {
                    "question": "Which editor does our agent use for Python?",
                    "max_items": 5,
                }), "evidence")
                self.assertTrue(any(
                    "Neovim" in item["content"] for item in queried["evidence"]
                ), queried)
            # Spawn an entirely new process: tests OS-level persistence, not
            # just reopening an in-memory MCP object on the same interpreter.
            async with Client(params) as reconnected:
                recovered = _result(await reconnected.call_tool("memory_get", {
                    "key": "memory:agent:editor",
                }), "evidence")
                self.assertTrue(any(
                    "Neovim" in item["content"] for item in recovered["evidence"]
                ), recovered)

    async def test_same_key_rewrite_is_visible_not_silently_merged(self):
        # Real runtime semantics: a second explicit write under one key moves the head but
        # leaves the first fact current and findable. The harness must be able to tell.
        with tempfile.TemporaryDirectory() as temp:
            env = {
                "AGENT_MEMORY_MCP_ROOT": str(Path(temp) / "store"),
                "AGENT_MEMORY_MCP_TENANT": "tenant:rewrite",
                "AGENT_MEMORY_MCP_ACTOR": "agent:rewrite",
                "AGENT_MEMORY_MCP_SCOPE": "project:rewrite",
            }
            with patch.dict(os.environ, env):
                async with Client(module.mcp, raise_exceptions=True) as client:
                    first = _result(await client.call_tool("memory_remember", {
                        "key": "memory:editor", "text": "The owner writes Python in Neovim.",
                    }), "committed")
                    second = _result(await client.call_tool("memory_remember", {
                        "key": "memory:editor", "text": "The owner writes Python in VS Code.",
                    }), "committed")
                    self.assertTrue(first["committed"] and second["committed"], (first, second))
                    got = _result(await client.call_tool("memory_get", {"key": "memory:editor"}), "evidence")
                    self.assertEqual(got["lookup_status"], "found", got)
                    self.assertEqual([e["content"] for e in got["evidence"]], ["The owner writes Python in VS Code."])
                    # the counter is the runtime's state counter, not a version count: only its
                    # presence and type are contracted, never its meaning
                    self.assertIsInstance(got["key_state_version"], int, got)
                    self.assertIs(got["earlier_generations_enumerated"], False, got)
                    self.assertIn("not a count of written versions", got["caveat"])
                    self.assertTrue(got["evidence"][0]["latest_for_key"], got)
                    found = _result(await client.call_tool("memory_find", {
                        "question": "Which editor does the owner use for Python?", "max_items": 5,
                    }), "evidence")
                    by_text = {e["content"]: e for e in found["evidence"]}
                    self.assertIn("The owner writes Python in VS Code.", by_text, found)
                    self.assertTrue(by_text["The owner writes Python in VS Code."]["latest_for_key"])
                    older = by_text.get("The owner writes Python in Neovim.")
                    if older is not None:  # the earlier generation may still be retrieved
                        self.assertFalse(older["latest_for_key"], older)
                        self.assertIn("memory:editor", found["non_head_keys"], found)
                    else:
                        self.assertEqual(found["non_head_keys"], [])
                # the markers must survive a restart of the server (fresh in-process client)
                async with Client(module.mcp, raise_exceptions=True) as client:
                    again = _result(await client.call_tool("memory_get", {"key": "memory:editor"}), "evidence")
                    self.assertEqual([e["content"] for e in again["evidence"]], ["The owner writes Python in VS Code."])
                    self.assertTrue(again["evidence"][0]["latest_for_key"], again)
                    found = _result(await client.call_tool("memory_find", {
                        "question": "Which editor does the owner use for Python?", "max_items": 5,
                    }), "evidence")
                    for item in found["evidence"]:
                        self.assertEqual(item["latest_for_key"], item["content"] == "The owner writes Python in VS Code.", item)

    async def test_missing_host_configuration_is_tool_error_not_success(self):
        with patch.dict(os.environ, {}, clear=True):
            async with Client(module.mcp, raise_exceptions=True) as client:
                result = await client.call_tool("memory_find", {
                    "question": "Which editor do I use?"
                })
                self.assertTrue(result.is_error, result)
                self.assertIsNone(result.structured_content)
                message = repr(result.content)
                self.assertIn("host configuration", message.lower())
                self.assertNotIn("Traceback", message)

    async def test_malformed_tool_input_cannot_set_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {
                "AGENT_MEMORY_MCP_ROOT": str(Path(temp) / "store"),
                "AGENT_MEMORY_MCP_TENANT": "tenant:private",
                "AGENT_MEMORY_MCP_ACTOR": "agent:private",
                "AGENT_MEMORY_MCP_SCOPE": "project:private",
            }
            with patch.dict(os.environ, env):
                async with Client(module.mcp, raise_exceptions=True) as client:
                    result = await client.call_tool("memory_find", {
                        "question": "notes",
                        "max_items": 10000,
                    })
                    self.assertTrue(result.is_error, result)
                    # Parameters not advertised in the tool's schema must not
                    # be interpreted as a trusted scope or tenant override.
                    tools = await client.list_tools()
                    find = next(t for t in tools.tools if t.name == "memory_find")
                    exposed = set((find.input_schema or {}).get("properties", {}))
                    self.assertFalse({"tenant", "scope", "actor", "root"} & exposed)


if __name__ == "__main__":
    unittest.main()
