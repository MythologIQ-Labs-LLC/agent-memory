"""OpenAI-compatible shim with tool calling, for LLM-based memory comparators on local llama.cpp (#813, #810).

This extends ``graphiti_llamacpp_shim.py``, which keeps its schema translation, per-item
embeddings and call log, with the tool-call parsing used in the MemoryArena reproduction
(``serving/hermes_proxy.py``):

* Qwen2.5 writes tool calls as Hermes ``<tool_call>{json}</tool_call>`` text when the server
  renders the model's own chat template. For a chat request that carries ``tools``, the shim
  converts that text into OpenAI ``tool_calls`` and sets ``finish_reason = "tool_calls"``. This
  is what vLLM's ``--tool-call-parser hermes`` does.
* When llama-cpp-python already returned structured ``tool_calls`` (forced ``tool_choice``), they
  pass through unchanged.

Requests without ``tools`` are handled exactly as in ``graphiti_llamacpp_shim.py``.

Usage: ``python llamacpp_hermes_tools_shim.py PORT LLM_URL EMBED_URL LOG_PATH``.
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from http.server import ThreadingHTTPServer

from graphiti_llamacpp_shim import make_handler

TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)


def _parse_call(text: str):
    for candidate in (text, text[1:], text[1:-1]) if text.startswith("{{") else (text,):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "name" in value:
            return value
    return None


def convert(message: dict) -> tuple[dict, int]:
    """Hermes ``<tool_call>`` text -> OpenAI ``tool_calls``; nothing else in the message changes."""
    if message.get("tool_calls"):
        return message, 0
    content = message.get("content") or ""
    calls = []
    for raw in TOOL_CALL.findall(content):
        parsed = _parse_call(raw.strip())
        if parsed is None:
            continue
        arguments = parsed.get("arguments", {})
        calls.append({"id": "call_" + uuid.uuid4().hex[:24], "type": "function",
                      "function": {"name": parsed["name"],
                                   "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments)}})
    if calls:
        rest = TOOL_CALL.sub("", content).strip()
        message = dict(message, content=rest or None, tool_calls=calls)
    return message, len(calls)


def make_tools_handler(llm_url: str, embed_url: str, log_path: str):
    base = make_handler(llm_url, embed_url, log_path)

    class ToolsHandler(base):
        def _forward(self, method, data):
            status, payload = super()._forward(method, data)
            if status != 200 or method != "POST" or not self.path.rstrip("/").endswith("/chat/completions") or not data:
                return status, payload
            if not json.loads(data).get("tools"):
                return status, payload
            body = json.loads(payload)
            for choice in body.get("choices", []):
                choice["message"], parsed = convert(choice.get("message") or {})
                if parsed:
                    choice["finish_reason"] = "tool_calls"
            return status, json.dumps(body).encode()

    return ToolsHandler


if __name__ == "__main__":
    port, llm, embed, log = int(sys.argv[1]), sys.argv[2].rstrip("/"), sys.argv[3].rstrip("/"), sys.argv[4]
    ThreadingHTTPServer(("127.0.0.1", port), make_tools_handler(llm, embed, log)).serve_forever()
