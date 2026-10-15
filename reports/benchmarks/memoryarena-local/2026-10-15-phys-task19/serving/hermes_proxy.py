"""OpenAI-compatible shim in front of a llama.cpp server serving Qwen2.5 with its own chat template.

Qwen2.5 emits tool calls as Hermes-style ``<tool_call>{json}</tool_call>`` text. This shim
converts them into OpenAI ``tool_calls`` (what vLLM's ``--tool-call-parser hermes`` does) and
forwards the client's ``max_completion_tokens`` as ``max_tokens`` (llama.cpp ignores the former).
Nothing else in the request or response is changed. Every call is appended to a JSONL log.
"""

import json
import re
import sys
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "http://127.0.0.1:8080"
TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
LOG_PATH = sys.argv[2] if len(sys.argv) > 2 else "hermes-proxy.jsonl"


def _parse_call(text: str):
    candidates = [text]
    if text.startswith("{{"):
        candidates += [text[1:], text[1:-1]]
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "name" in value:
            return value
    return None


def convert(message: dict) -> tuple[dict, int]:
    content = message.get("content") or ""
    calls = []
    for raw in TOOL_CALL.findall(content):
        parsed = _parse_call(raw.strip())
        if parsed is None:
            continue
        arguments = parsed.get("arguments", {})
        calls.append({
            "id": "call_" + uuid.uuid4().hex[:24],
            "type": "function",
            "function": {"name": parsed["name"], "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments)},
        })
    if calls:
        rest = TOOL_CALL.sub("", content).strip()
        message = dict(message, content=rest or None, tool_calls=calls)
    return message, len(calls)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _forward(self, method: str, body: bytes | None):
        request = urllib.request.Request(UPSTREAM + self.path, data=body, method=method, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=3600) as response:
            return response.status, response.read()

    def do_GET(self):
        status, payload = self._forward("GET", None)
        self._send(status, payload)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if "max_completion_tokens" in body and "max_tokens" not in body:
            body["max_tokens"] = body.pop("max_completion_tokens")
        status, payload = self._forward("POST", json.dumps(body).encode())
        parsed_calls = 0
        if status == 200 and self.path.endswith("/chat/completions") and body.get("tools"):
            data = json.loads(payload)
            for choice in data.get("choices", []):
                choice["message"], parsed_calls = convert(choice["message"])
                if parsed_calls:
                    choice["finish_reason"] = "tool_calls"
            payload = json.dumps(data).encode()
        with open(LOG_PATH, "a", encoding="utf-8") as log:
            log.write(json.dumps({"request": body, "status": status, "response": json.loads(payload), "parsed_tool_calls": parsed_calls}) + "\n")
        self._send(status, payload)

    def _send(self, status: int, payload: bytes):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8081), Handler).serve_forever()
