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

from mcp import Client

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
                # Reconnecting the harness must recover the same durable store.
                async with Client(module.mcp, raise_exceptions=True) as client:
                    recovered = _result(
                        await client.call_tool("memory_get", {"key": "memory:preferred_editor"}),
                        "evidence",
                    )
                    self.assertTrue(any(
                        "Neovim" in item["content"] for item in recovered["evidence"]
                    ), recovered)

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
