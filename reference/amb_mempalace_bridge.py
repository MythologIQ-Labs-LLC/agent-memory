"""MemPalace (default local path) provider for the pinned AMB harness (#810). Candidate adapter.

It registers ``mempalace-local`` in the frozen vectorize-io/agent-memory-benchmark REGISTRY at
runtime, as the other AMB bridges do. AMB keeps dataset loading, ``RetrievalMode`` and scoring.

The product path is the same as the LongMemEval MemPalace bridge
(``longmemeval_mempalace_bridge.py``, MemPalace 3.11.0 at ``602d796c``). The adapter talks to
MemPalace's own MCP stdio server and calls ``mempalace_add_drawer`` once per AMB document, with the
verbatim content and an opaque uuid5 ``source_file``. It then calls one
``mempalace_search(query, limit=k)`` per case, where ``k`` is AMB's per-case ``retrieval_limit``.
That bridge's verified helpers are reused: credential refusal, the installed-package tree hash, the
model directory check, the clean child environment, and drawer-to-document mapping through
product metadata only. The MCP server is started from the pinned MemPalace interpreter
(``MEMPALACE_PYTHON``), so AMB's environment does not need MemPalace installed.

MemPalace is a personal memory: one palace per person. Each AMB ``user_id`` therefore gets its
own palace and server, which is how cross-user isolation is achieved. No belief id, scope tag,
context marker, timestamp, gold label or query category is given to MemPalace. No LLM is
reachable on this path.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from longmemeval_mempalace_bridge import (
    CHROMA_MODEL_SUBDIR, DEFAULT_CALL_TIMEOUT, MEMPALACE_TAG_COMMIT, MEMPALACE_VERSION, ROOM,
    DrawerMap, McpStdioServer, child_environment, ranked_doc_ids, refuse_credentials,
    verify_model_dir,
)

AMB_REVISION = "03c1d0f1d27da63034f0931121c858faba512383"
AMB_PROVIDER_KEY = "mempalace-local"
BRIDGE_VERSION = "0.1.0-candidate"
WING = "amb"
ID_NAMESPACE = uuid.UUID("5c7e1a90-2b3d-5f41-8e6a-810000000a3b")


def opaque_key(doc_id: str) -> str:
    return f"item-{uuid.uuid5(ID_NAMESPACE, str(doc_id))}"


class _PinnedInterpreterServer(McpStdioServer):
    """The frozen ``McpStdioServer``, started from MemPalace's own pinned interpreter."""

    def __init__(self, python: str, palace: Path, env, cwd: Path, stderr_path: Path,
                 timeout: float = DEFAULT_CALL_TIMEOUT) -> None:
        self._stderr = open(stderr_path, "wb")
        self.proc = subprocess.Popen(
            [python, "-s", "-m", "mempalace.mcp_server", "--palace", str(palace)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr, env=dict(env), cwd=str(cwd))
        self.timeout = timeout
        self._buffer = bytearray()
        self._next_id = 0
        self.non_json_lines = 0


def frozen_configuration() -> dict[str, Any]:
    return {
        "provider_key": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION,
        "product": f"MemPalace {MEMPALACE_VERSION} @ {MEMPALACE_TAG_COMMIT}, own MCP stdio server, default local config",
        "add": "mempalace_add_drawer(wing='amb', room='history', content=document.content, source_file=uuid5 key)",
        "search": "mempalace_search(query, limit=k), k = AMB per-case retrieval_limit",
        "isolation": "one palace + server per AMB user_id",
        "identity_mapping": "drawer_id/also_in/source_path returned by the product -> AMB document id",
        "not_supplied": ["belief ids", "scope tags", "document.context", "timestamps", "gold", "query category"],
        "llm": "none reachable", "embedding_threads": "1",
    }


def install_amb_mempalace_provider(amb_root: str | Path) -> type:
    checkout = Path(amb_root).resolve()
    if str(checkout / "src") not in sys.path:
        sys.path.insert(0, str(checkout / "src"))
    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.memory.base import MemoryProvider  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    class MemPalaceLocalAMBProvider(MemoryProvider):
        name = AMB_PROVIDER_KEY
        description = (f"MemPalace {MEMPALACE_VERSION} default local path through its own MCP tools "
                       "(chroma + MiniLM ONNX, BM25 hybrid rerank), one palace per user; #810 candidate.")
        kind = "local"
        provider = "mempalace"
        variant = f"oss-{MEMPALACE_VERSION}-mcp-default"
        link = "https://github.com/MemPalace/mempalace"
        logo = None
        concurrency = 1
        supports_filters = False

        def __init__(self) -> None:
            self._servers: dict[str, tuple[Any, DrawerMap]] = {}
            self._root: Path | None = None

        def prepare(self, store_dir: Path, unit_ids: set[str] | None = None, reset: bool = True) -> None:
            refuse_credentials(os.environ)
            self._python = os.environ["MEMPALACE_PYTHON"]
            self._model_dir = Path(os.environ["MEMPALACE_BENCH_MODEL_DIR"]).resolve(strict=True)
            self._model_identity = verify_model_dir(self._model_dir)
            # The pinned install lives in MemPalace's own interpreter; verify its tree hash there,
            # with the same function the LongMemEval bridge uses.
            check = subprocess.run(
                [self._python, "-s", "-c",
                 "import json, sys; sys.path.insert(0, sys.argv[1]); "
                 "from longmemeval_mempalace_bridge import verify_installed_package; "
                 "print(json.dumps(verify_installed_package()))", str(Path(__file__).resolve().parent)],
                capture_output=True, text=True, check=True, env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
            self.install_identity = json.loads(check.stdout.strip().splitlines()[-1])
            self._root = Path(store_dir)
            if reset:
                shutil.rmtree(self._root, ignore_errors=True)
            self._root.mkdir(parents=True, exist_ok=True)
            self._servers = {}

        def _server(self, user_id: str) -> tuple[Any, DrawerMap]:
            if user_id not in self._servers:
                udir = self._root / f"user-{uuid.uuid5(ID_NAMESPACE, user_id).hex[:12]}"
                (udir / "home" / CHROMA_MODEL_SUBDIR).parent.mkdir(parents=True)
                (udir / "home" / CHROMA_MODEL_SUBDIR).symlink_to(self._model_dir, target_is_directory=True)
                (udir / "config").mkdir()
                server = _PinnedInterpreterServer(self._python, udir / "palace",
                                                  child_environment(udir, "1", os.environ.get("PYTHONHASHSEED")),
                                                  cwd=udir, stderr_path=udir / "server-stderr.log")
                server.initialize()
                self._servers[user_id] = (server, DrawerMap())
            return self._servers[user_id]

        def ingest(self, documents: list[Document]) -> None:
            for document in documents:
                server, drawers = self._server(str(document.user_id))
                key = opaque_key(document.id)
                payload, is_error = server.call("mempalace_add_drawer", wing=WING, room=ROOM,
                                                content=str(document.content), source_file=key)
                if is_error or payload.get("success") is not True or not payload.get("drawer_id"):
                    raise RuntimeError(f"MemPalace did not file AMB document {document.id!r}: {str(payload)[:300]}")
                drawers.record(payload["drawer_id"], str(document.id), key)

        def retrieve(self, query: str, k: int = 10, user_id: str | None = None,
                     query_timestamp: str | None = None) -> tuple[list[Document], dict | None]:
            uid = str(user_id)
            if uid not in self._servers:
                return [], {"provider": AMB_PROVIDER_KEY, "note": "no palace for this user (nothing ingested)"}
            server, drawers = self._servers[uid]
            started = time.perf_counter()
            result, is_error = server.call("mempalace_search", query=str(query), limit=max(1, int(k)))
            seconds = time.perf_counter() - started
            if is_error or "error" in result:
                raise RuntimeError(f"mempalace_search failed: {str(result.get('error') or result)[:300]}")
            hits = result.get("results") or []
            ranked, unmapped, stats = ranked_doc_ids(hits, drawers)
            ranked = ranked[: max(0, int(k))]
            text = {}
            for hit in hits:
                for ref in [hit, *(hit.get("also_in") or [])] if isinstance(hit, dict) else []:
                    for doc in drawers.resolve(ref.get("drawer_id"), ref.get("source_path")) or []:
                        text.setdefault(doc, str(hit.get("text") or hit.get("content") or ""))
            documents = [Document(id=doc, content=text.get(doc, ""), user_id=uid, source_ids=[doc]) for doc in ranked]
            return documents, {"provider": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION,
                               "search_seconds": round(seconds, 4), "limit": max(1, int(k)),
                               "hit_count": len(hits), "hit_stats": stats, "unmapped": unmapped,
                               "total_before_filter": result.get("total_before_filter")}

        def cleanup(self) -> None:
            for server, _ in self._servers.values():
                server.close()
            self._servers = {}

    REGISTRY[AMB_PROVIDER_KEY] = MemPalaceLocalAMBProvider
    return MemPalaceLocalAMBProvider
