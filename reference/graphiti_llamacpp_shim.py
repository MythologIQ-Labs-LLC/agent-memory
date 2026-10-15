"""OpenAI-compatible shim in front of two local llama-cpp-python servers, for the Graphiti comparator (#812).

Graphiti's documented local path is ``OpenAIGenericClient`` + ``OpenAIEmbedder`` against an
OpenAI-compatible ``/v1`` endpoint (README, "Using Graphiti with OpenAI-compatible providers and
local LLMs"). llama-cpp-python 0.3.16 serves one model per process and accepts structured output
only as ``{"type": "json_object", "schema": S}``, whereas Graphiti's default
``structured_output_mode="json_schema"`` sends OpenAI's ``{"type": "json_schema",
"json_schema": {"schema": S}}``. This shim:

* routes ``/v1/chat/completions`` to the LLM server and ``/v1/embeddings`` to the embedding server;
* rewrites ``json_schema`` into the server's own schema-constrained form, so the same schema is
  enforced by grammar-constrained decoding (what vLLM, Ollama and llama.cpp's native server do
  for ``json_schema``);
* sends a list embedding input one item per request (the server fails on multi-input batches
  for this model) and returns the vectors in input order;
* changes nothing else in any request or response, and appends every call (request, response,
  status, wall time) to a JSONL log for model-usage accounting.

Usage: ``python graphiti_llamacpp_shim.py PORT LLM_URL EMBED_URL LOG_PATH``.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()


def translate(body: dict) -> tuple[dict, bool]:
    """Return the request with ``json_schema`` mapped to llama-cpp's ``json_object`` + ``schema``."""
    fmt = body.get("response_format")
    if isinstance(fmt, dict) and fmt.get("type") == "json_schema":
        schema = (fmt.get("json_schema") or {}).get("schema")
        body = dict(body, response_format={"type": "json_object", "schema": schema} if schema else {"type": "json_object"})
        return body, True
    return body, False


def make_handler(llm_url: str, embed_url: str, log_path: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def _upstream(self) -> str:
            return embed_url if self.path.rstrip("/").endswith("/embeddings") else llm_url

        def _forward(self, method: str, data: bytes | None) -> tuple[int, bytes]:
            request = urllib.request.Request(self._upstream() + self.path, data=data, method=method,
                                             headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=7200) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as exc:
                return exc.code, exc.read()

        def do_GET(self):
            status, payload = self._forward("GET", None)
            self._send(status, payload)

        def _embed_each(self, body: dict) -> tuple[int, bytes]:
            """llama-cpp-python 0.3.16 fails (``llama_decode returned -1``) on multi-input batches
            for the non-causal nomic-bert model, so a list input is sent one item per request and
            reassembled in input order. Each vector is what a single-input call returns."""
            data, prompt_tokens = [], 0
            for index, text in enumerate(body["input"]):
                status, payload = self._forward("POST", json.dumps(dict(body, input=text)).encode())
                if status != 200:
                    return status, payload
                parsed = json.loads(payload)
                data.append(dict(parsed["data"][0], index=index))
                prompt_tokens += (parsed.get("usage") or {}).get("prompt_tokens", 0)
            return 200, json.dumps({"object": "list", "data": data, "model": body.get("model"),
                                    "usage": {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens}}).encode()

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            body, translated = translate(body)
            started = time.time()
            if self.path.rstrip("/").endswith("/embeddings") and isinstance(body.get("input"), list):
                status, payload = self._embed_each(body)
            else:
                status, payload = self._forward("POST", json.dumps(body).encode())
            entry = {"path": self.path, "status": status, "translated_json_schema": translated,
                     "wall_seconds": round(time.time() - started, 3), "started_unix": round(started, 3)}
            try:
                parsed = json.loads(payload)
            except ValueError:
                parsed = payload.decode("utf-8", "replace")
            if self.path.rstrip("/").endswith("/embeddings"):
                entry.update(inputs=len(body.get("input") or []) if isinstance(body.get("input"), list) else 1,
                             usage=parsed.get("usage") if isinstance(parsed, dict) else None)
            else:
                entry.update(request=body, response=parsed)
            with LOCK, open(log_path, "a", encoding="utf-8") as log:
                log.write(json.dumps(entry) + "\n")
            self._send(status, payload)

        def _send(self, status: int, payload: bytes):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


if __name__ == "__main__":
    port, llm, embed, log = int(sys.argv[1]), sys.argv[2].rstrip("/"), sys.argv[3].rstrip("/"), sys.argv[4]
    ThreadingHTTPServer(("127.0.0.1", port), make_handler(llm, embed, log)).serve_forever()
