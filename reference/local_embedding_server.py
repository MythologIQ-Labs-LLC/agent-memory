"""Loopback OpenAI-compatible embedding endpoint backed by a pinned fastembed ONNX model.

Some competitors (Letta) take their embedder from any OpenAI-compatible endpoint. This serves
exactly one local model so they can run with no hosted API and no key. It implements only
POST /v1/embeddings and GET /v1/models; vectors are returned as fastembed produces them.

Usage: python local_embedding_server.py --model BAAI/bge-small-en-v1.5 --cache-dir D --url-file F
"""
from __future__ import annotations

import argparse, hashlib, json, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--url-file", required=True)
    ap.add_argument("--port", type=int, default=0)
    a = ap.parse_args()

    from fastembed import TextEmbedding
    import fastembed
    emb = TextEmbedding(model_name=a.model, cache_dir=a.cache_dir)
    dims = len(next(iter(emb.embed(["x"]))))
    onnx = sorted(Path(a.cache_dir).rglob("*.onnx"))
    identity = {"model": a.model, "dims": dims, "fastembed": fastembed.__version__,
                "onnx_files": {str(p.relative_to(a.cache_dir)): hashlib.sha256(p.read_bytes()).hexdigest() for p in onnx}}
    lock, stats = threading.Lock(), {"requests": 0, "inputs": 0}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            if self.path.rstrip("/") == "/v1/models":
                return self._send(200, {"object": "list", "data": [{"id": a.model, "object": "model", "owned_by": "local"}]})
            if self.path == "/identity":
                return self._send(200, dict(identity, **stats))
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path.rstrip("/") != "/v1/embeddings":
                return self._send(404, {"error": "not found"})
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            inputs = body.get("input")
            inputs = [inputs] if isinstance(inputs, str) else list(inputs or [])
            if not all(isinstance(x, str) for x in inputs):
                return self._send(400, {"error": "only string inputs are supported"})
            with lock:
                vecs = [list(map(float, v)) for v in emb.embed(inputs)]
                stats["requests"] += 1; stats["inputs"] += len(inputs)
            self._send(200, {"object": "list", "model": a.model,
                             "data": [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vecs)],
                             "usage": {"prompt_tokens": 0, "total_tokens": 0}})

    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    Path(a.url_file).write_text(json.dumps({"url": f"http://127.0.0.1:{srv.server_address[1]}/v1", "identity": identity, "pid": os.getpid()}))
    srv.serve_forever()


if __name__ == "__main__":
    main()
