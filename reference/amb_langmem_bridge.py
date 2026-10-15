"""LangMem provider for the pinned AMB harness (#813, #810). Candidate adapter.

This registers ``langmem-local`` in the frozen AMB REGISTRY. LangMem runs in its own pinned
interpreter behind ``langmem_amb_worker.py``, using LangMem's documented store-backed memory
manager over a LangGraph ``InMemoryStore`` with a vector index. Each AMB document goes to the
manager as one user message, and each case runs one ``manager.search(query, limit=k)``.

* **Capability tier:** an LLM at ingestion (local Qwen2.5-3B). This is the same tier as Graphiti
  and is reported as a separate row from the no-LLM systems.
* **Provenance:** inferred per ``invoke`` call (see the worker docstring).
* **Not supplied:** belief ids, scope tags, context markers, timestamps, gold labels or query
  categories.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

AMB_PROVIDER_KEY = "langmem-local"
BRIDGE_VERSION = "0.1.0-candidate"
LANGMEM_COMMIT = "48e3c11f5bb527282c7d5339c6a87a0b35abccfc"
WORKER = Path(__file__).resolve().parent / "langmem_amb_worker.py"
_FORBIDDEN_ENV = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY",
                  "LANGSMITH_API_KEY", "LANGCHAIN_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
_LOOPBACK = re.compile(r"^http://(127\.0\.0\.1|localhost):\d+/v1/?$")


def frozen_configuration() -> dict[str, Any]:
    return {
        "provider_key": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION,
        "product": f"langmem 0.0.30 @ {LANGMEM_COMMIT} (MIT); langchain 1.4.6, langgraph 1.2.15, trustcall 0.0.39",
        "manager": "create_memory_store_manager(model, namespace=('memories','{langgraph_user_id}'), store=InMemoryStore(index=768-d)) with LangMem defaults",
        "storage": "LangGraph InMemoryStore with vector index (not persistent)",
        "llm": "ChatOpenAI(qwen2.5-3b-instruct-q4_k_m, temperature 0) via llamacpp_hermes_tools_shim (Hermes tool calls -> OpenAI tool_calls)",
        "embeddings": "OpenAIEmbeddings(nomic-embed-text, check_embedding_ctx_length=False), 768-d",
        "ingest": "one manager.invoke per AMB document as a user message, per AMB user_id namespace",
        "search": "manager.search(query, limit=k), k = AMB per-case retrieval_limit",
        "identity_mapping": "memories created/changed during a document's invoke are attributed to it (LangMem keeps no provenance)",
        "tracing": "LANGSMITH_TRACING=false; no LangSmith key",
        "not_supplied": ["belief ids", "scope tags", "document.context", "timestamps", "gold", "query category"],
    }


def install_amb_langmem_provider(amb_root: str | Path) -> type:
    checkout = Path(amb_root).resolve()
    if str(checkout / "src") not in sys.path:
        sys.path.insert(0, str(checkout / "src"))
    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.memory.base import MemoryProvider  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    class LangMemLocalAMBProvider(MemoryProvider):
        name = AMB_PROVIDER_KEY
        description = "LangMem store-backed memory manager (local Qwen2.5-3B, nomic embeddings, InMemoryStore); #813 candidate."
        kind = "local"
        provider = "langmem"
        variant = "oss-0.0.30-local-llm"
        link = "https://github.com/langchain-ai/langmem"
        logo = None
        concurrency = 1
        supports_filters = False

        def __init__(self) -> None:
            self._proc: subprocess.Popen | None = None
            self._ingest_log: list[dict] = []

        def _call(self, request: dict) -> dict:
            assert self._proc is not None and self._proc.stdin and self._proc.stdout
            self._proc.stdin.write(json.dumps(request) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError(f"LangMem worker exited (code {self._proc.poll()})")
            reply = json.loads(line)
            if not reply.get("ok"):
                raise RuntimeError(f"LangMem worker error: {reply.get('error')}\n{reply.get('trace', '')}")
            return reply

        def prepare(self, store_dir: Path, unit_ids: set[str] | None = None, reset: bool = True) -> None:
            present = [k for k in _FORBIDDEN_ENV if os.environ.get(k)]
            if present:
                raise RuntimeError(f"refusing: hosted inference credentials present: {present}")
            base_url = os.environ.get("LANGMEM_LOCAL_BASE_URL", "")
            if not _LOOPBACK.match(base_url):
                raise RuntimeError("LANGMEM_LOCAL_BASE_URL must be a loopback http://127.0.0.1:<port>/v1 endpoint")
            store = Path(store_dir)
            store.mkdir(parents=True, exist_ok=True)
            env = {"PATH": "/usr/bin:/bin", "HOME": str(store), "LANGMEM_LOCAL_BASE_URL": base_url,
                   "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false", "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "0"),
                   "PYTHONPATH": str(WORKER.parent)}
            self._stderr = open(store / "langmem-worker.stderr.log", "ab")
            self._proc = subprocess.Popen([os.environ["LANGMEM_PYTHON"], "-s", str(WORKER)], stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, stderr=self._stderr, text=True, env=env, cwd=str(store))
            if not self._proc.stdout.readline():
                raise RuntimeError(f"LangMem worker failed to start; see {store}/langmem-worker.stderr.log")
            self._ingest_log = []

        def ingest(self, documents: list[Document]) -> None:
            for document in documents:
                reply = self._call({"op": "retain", "user": str(document.user_id), "doc_id": str(document.id),
                                    "text": str(document.content)})
                self._ingest_log.append({"doc_id": str(document.id), **{k: reply[k] for k in ("memories_changed", "memories_total", "seconds")}})
                print(f"langmem-ingest {len(self._ingest_log)}/{len(documents)} {self._ingest_log[-1]}", file=sys.stderr, flush=True)

        def retrieve(self, query: str, k: int = 10, user_id: str | None = None,
                     query_timestamp: str | None = None) -> tuple[list[Document], dict | None]:
            started = time.perf_counter()
            reply = self._call({"op": "recall", "user": str(user_id), "query": str(query), "k": max(1, int(k))})
            documents = [Document(id=doc, content=str(content or ""), user_id=user_id, source_ids=[doc])
                         for doc, content in reply["ranked"][: max(0, int(k))]]
            return documents, {"provider": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION,
                               "seconds": round(time.perf_counter() - started, 4), **reply["raw"]}

        def cleanup(self) -> None:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.stdin.write(json.dumps({"op": "close"}) + "\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=120)
            self._proc = None

        def ingest_log(self) -> list[dict]:
            return list(self._ingest_log)

    REGISTRY[AMB_PROVIDER_KEY] = LangMemLocalAMBProvider
    return LangMemLocalAMBProvider
