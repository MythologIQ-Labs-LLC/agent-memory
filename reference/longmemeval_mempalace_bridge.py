"""MemPalace v3.11.0 default-local retrieval comparator for the LongMemEval profile.

Candidate adapter, NOT an accepted lane. Registers ``mempalace_default_local`` on the
frozen ``reference/run_longmemeval.py`` external-backend seam; selection, gold and
scoring are the runner's, unchanged.

Product surface: the MemPalace MCP server an agent talks to (``python -m
mempalace.mcp_server --palace DIR``, stdio JSON-RPC), driven through its two public
memory tools and nothing else:

* ``mempalace_add_drawer(wing, room, content, source_file)`` -- "File verbatim content
  into the palace" -- once per non-blank frozen corpus item;
* ``mempalace_search(query, limit=50)`` -- the agent's search tool, which calls the
  documented Python API ``mempalace.searcher.search_memories`` with the server's
  defaults (hybrid vector + BM25 rerank, closet boost, cross-source fold).

This deliberately does NOT reuse MemPalace's ``benchmarks/longmemeval_bench.py``: its
"raw" mode writes into a bare ChromaDB collection and never calls the package, so it
would measure ChromaDB rather than MemPalace.

Product defaults are kept: ChromaDB backend, ``minilm`` embedder (ChromaDB's ONNX
all-MiniLM-L6-v2, the fallback when no config names a model), ``chunk_size`` 800,
hybrid weights 0.6/0.4, MCP ``max_distance`` 1.5, query sanitizer. No LLM is reachable
from these tools; the adapter refuses to start when an LLM or embedding-API credential is
present, and the server child gets a clean environment.

Identity mapping: each corpus occurrence is filed with ``source_file`` set to an opaque
key ``uuid5(namespace, doc_id[, NUL k])``; the benchmark id string (which encodes the
upstream gold label as ``answer``/``noans``), the answer and ``has_answer`` never reach
the product. ``add_drawer`` returns the drawer id (a content hash of wing/room/content),
so identical content filed twice returns ``already_exists`` with the same drawer id; the
adapter maps a drawer id to every corpus id whose add returned it, in corpus order.
Ranked ids come only from the ``drawer_id`` (and ``also_in`` refs) of returned hits, and
each hit's ``source_path`` must be a key the adapter filed under that drawer.

Isolation: every question gets a fresh directory holding its palace, config dir
(``MEMPALACE_CONFIG_DIR``: write-ahead log, update-check state) and HOME (locks, legacy
paths; the pinned model cache is symlinked in read-only use), and a fresh server
process, which is shut down and the directory deleted after the single search.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import select
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

BACKEND = "mempalace_default_local"
BRIDGE_ID = "reference/longmemeval_mempalace_bridge.py"
BRIDGE_VERSION = "0.1.0-candidate"
MEMPALACE_VERSION = "3.11.0"
MEMPALACE_TAG = "v3.11.0"
MEMPALACE_TAG_COMMIT = "602d796c699cabba2971982cd9dccbbf46abfe79"
MEMPALACE_REPOSITORY = "https://github.com/MemPalace/mempalace"
# sha256 over sorted "relpath NUL sha256(file)" lines of the ``mempalace`` package tree
# (``__pycache__``/``.pyc`` excluded); identical for the v3.11.0 checkout and the
# non-editable install built from it.
MEMPALACE_PACKAGE_TREE_SHA256 = "5bdf5b112e1790c0089e22d5f9f71e4432b771c8eeaad7cd729e1371a27f192c"
MEMPALACE_PACKAGE_FILE_COUNT = 169

# Default ``minilm`` embedder: ChromaDB's ONNXMiniLM_L6_V2 archive (not a Hugging Face
# download). The archive hash equals chromadb's own ``_MODEL_SHA256`` pin.
MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_SOURCE_URL = "https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz"
MODEL_UPSTREAM = "sentence-transformers/all-MiniLM-L6-v2 (ONNX export distributed by ChromaDB)"
MODEL_FILE_SHA256 = {
    "onnx.tar.gz": "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3",
    "onnx/config.json": "b567c7d5a55b636c95186aaf993f9a8920842b7e05a9e703e68b23cab2c3a670",
    "onnx/model.onnx": "4f148ba8ae9c2c7fbee4af2b132db8d06c6a6545b47fc83bbb98c3d22b8393e6",
    "onnx/special_tokens_map.json": "b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3",
    "onnx/tokenizer.json": "da0e79933b9ed51798a3ae27893d3c5fa4a201126cef75586296df9b4d2c62a0",
    "onnx/tokenizer_config.json": "7702051bbc4953b94d47fa1d61b42ed4cbb3c71b501a8dd7183a823f8bea1f20",
    "onnx/vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
}
CHROMA_MODEL_SUBDIR = Path(".cache") / "chroma" / "onnx_models" / MODEL_NAME

MAX_DEPTH = 50
WING = "longmemeval"
ROOM = "history"
ID_NAMESPACE = uuid.UUID("3d0b6a52-7c41-5e2f-9b8d-81000000a5e1")
PROTOCOL_VERSION = "2025-03-26"
DEFAULT_CALL_TIMEOUT = 600.0
_FORBIDDEN_ENV = (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "MEMPALACE_EMBEDDING_API_KEY", "MEMPALACE_EMBEDDING_API_URL", "MEMPALACE_LLM_API_KEY",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
)


# ---------------------------------------------------------------- pure helpers

def validate_corpus_ids(items) -> list:
    """Upstream LongMemEval indexes a repeated haystack session once per occurrence under
    the same id (the runner validates that repeats carry identical content). Accept that,
    refuse anything else: empty/non-string ids or one id with different texts."""
    ids, texts = [], {}
    for item in items:
        doc_id, text = item.get("id"), item.get("text")
        if not isinstance(doc_id, str) or not doc_id or not isinstance(text, str):
            raise ValueError("benchmark corpus items need non-empty string ids and string text")
        if texts.setdefault(doc_id, text) != text:
            raise ValueError(f"benchmark corpus id {doc_id!r} repeats with different text")
        ids.append(doc_id)
    return ids


def opaque_key(doc_id: str, occurrence: int = 0) -> str:
    """The ``source_file`` value filed for one corpus occurrence; never the benchmark id."""
    name = doc_id if occurrence == 0 else f"{doc_id}\x00{occurrence}"
    return f"lme-{uuid.uuid5(ID_NAMESPACE, name).hex}"


def occurrence_keys(ids: Sequence[str]) -> list:
    """One opaque key per corpus occurrence; the k-th repeat of an id gets a distinct key."""
    seen: dict[str, int] = {}
    out = []
    for doc_id in ids:
        k = seen.get(doc_id, 0)
        seen[doc_id] = k + 1
        out.append(opaque_key(doc_id, k))
    return out


class DrawerMap:
    """drawer id -> corpus ids (corpus order) and the source keys filed under it, built only
    from what ``mempalace_add_drawer`` returned."""

    def __init__(self) -> None:
        self.doc_ids: dict[str, list[str]] = {}
        self.keys: dict[str, set[str]] = {}

    def record(self, drawer_id: str, doc_id: str, key: str) -> None:
        targets = self.doc_ids.setdefault(drawer_id, [])
        if doc_id not in targets:
            targets.append(doc_id)
        self.keys.setdefault(drawer_id, set()).add(key)

    def resolve(self, drawer_id: Any, source_path: Any) -> list[str] | None:
        if not isinstance(drawer_id, str) or drawer_id not in self.doc_ids:
            return None
        if source_path not in self.keys[drawer_id]:
            return None  # product returned a source this adapter never filed under the drawer
        return self.doc_ids[drawer_id]


def ranked_doc_ids(hits: Sequence[Any], drawers: DrawerMap) -> tuple[list[str], int, dict[str, int]]:
    """Map returned hits to benchmark ids through product metadata only, in native order.

    A hit's own drawer comes first, then any ``also_in`` copies the product folded into it.
    Several hits of one chunked drawer collapse to its first rank. Hits whose drawer id or
    source path the adapter did not file are counted as unmapped, never guessed.
    """
    ranked: list[str] = []
    seen: set[str] = set()
    unmapped = 0
    stats = {"hit_count": 0, "also_in_ref_count": 0, "duplicate_hit_count": 0}
    for hit in hits:
        stats["hit_count"] += 1
        refs = [hit] if isinstance(hit, Mapping) else [None]
        if isinstance(hit, Mapping) and isinstance(hit.get("also_in"), list):
            refs += hit["also_in"]
            stats["also_in_ref_count"] += len(hit["also_in"])
        for ref in refs:
            targets = drawers.resolve(ref.get("drawer_id"), ref.get("source_path")) if isinstance(ref, Mapping) else None
            if not targets:
                unmapped += 1
                continue
            fresh = [doc for doc in targets if doc not in seen]
            if not fresh:
                stats["duplicate_hit_count"] += 1
            for doc_id in fresh:
                ranked.append(doc_id)
                seen.add(doc_id)
    return ranked[:MAX_DEPTH], unmapped, stats


def refuse_credentials(environ: Mapping[str, str]) -> None:
    present = [name for name in _FORBIDDEN_ENV if environ.get(name)]
    model = (environ.get("MEMPALACE_EMBEDDING_MODEL") or "").strip().lower()
    if model and model != "minilm":
        present.append(f"MEMPALACE_EMBEDDING_MODEL={model}")
    if present:
        raise RuntimeError(f"refusing: credentials or non-default embedder set for a no-LLM local profile: {present}")


def tree_sha256(root: Path) -> tuple[str, int]:
    root = Path(root)
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode() + b"\0" + hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
        count += 1
    return digest.hexdigest(), count


def verify_installed_package(package_dir: Path | None = None) -> dict[str, Any]:
    """Refuse anything but the exact v3.11.0 package tree; never imports mempalace."""
    try:
        version = importlib.metadata.version("mempalace")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("mempalace is not installed") from exc
    if version != MEMPALACE_VERSION:
        raise RuntimeError(f"mempalace {version} != pinned {MEMPALACE_VERSION}")
    if package_dir is None:
        spec = importlib.util.find_spec("mempalace")
        if spec is None or not spec.submodule_search_locations:
            raise RuntimeError("mempalace package location not found")
        package_dir = Path(list(spec.submodule_search_locations)[0])
    digest, count = tree_sha256(package_dir)
    if digest != MEMPALACE_PACKAGE_TREE_SHA256 or count != MEMPALACE_PACKAGE_FILE_COUNT:
        raise RuntimeError(f"installed mempalace tree {digest} ({count} files) is not the pinned {MEMPALACE_TAG} tree")
    direct_url = None
    try:
        direct_url = json.loads(importlib.metadata.distribution("mempalace").read_text("direct_url.json") or "null")
    except (OSError, ValueError):
        pass
    editable = bool(((direct_url or {}).get("dir_info") or {}).get("editable"))
    return {"version": version, "package_dir": str(package_dir), "package_tree_sha256": digest,
            "package_file_count": count, "editable": editable,
            "install_url": (direct_url or {}).get("url")}


def verify_source_checkout(source_root: Path) -> str:
    head = subprocess.run(["git", "-C", str(source_root), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    if head != MEMPALACE_TAG_COMMIT:
        raise RuntimeError(f"source checkout HEAD {head} != pinned {MEMPALACE_TAG} commit {MEMPALACE_TAG_COMMIT}")
    dirty = subprocess.run(["git", "-C", str(source_root), "status", "--porcelain", "--", "mempalace"],
                           check=True, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise RuntimeError("source checkout has local changes under mempalace/")
    return head


def verify_model_dir(model_dir: Path) -> dict[str, Any]:
    """Hash-verify the pre-staged ChromaDB MiniLM cache directory (``.../all-MiniLM-L6-v2``)."""
    model_dir = Path(model_dir).resolve(strict=True)
    for rel, expected in MODEL_FILE_SHA256.items():
        actual = hashlib.sha256((model_dir / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"model file {rel} sha256 {actual} != pinned {expected}")
    return {"embedder": "minilm (mempalace default)", "model": MODEL_NAME, "source_url": MODEL_SOURCE_URL,
            "upstream": MODEL_UPSTREAM, "files_sha256": dict(MODEL_FILE_SHA256),
            "tokenizer": "chromadb truncation/padding 256 tokens", "runtime": "onnxruntime CPUExecutionProvider"}


def child_environment(question_dir: Path, threads: str, hashseed: str | None) -> dict[str, str]:
    """A clean environment: nothing of the caller's leaks into the product process."""
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(question_dir / "home"),
        "MEMPALACE_CONFIG_DIR": str(question_dir / "config"),
        "MEMPALACE_EMBEDDING_THREADS": threads,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "ANONYMIZED_TELEMETRY": "False",
        "LANG": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
    }
    if hashseed is not None:
        env["PYTHONHASHSEED"] = hashseed
    return env


def tool_payload(response: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    """Unwrap an MCP ``tools/call`` response into (tool result dict, isError)."""
    if "error" in response:
        raise RuntimeError(f"MCP error: {response['error']}")
    result = response.get("result") or {}
    content = result.get("content") or []
    if not content or content[0].get("type") != "text":
        raise RuntimeError("MCP tool result carries no text content")
    payload = json.loads(content[0]["text"])
    if not isinstance(payload, dict):
        raise RuntimeError("MCP tool result is not an object")
    return payload, bool(result.get("isError"))


# ---------------------------------------------------------------- product process

class McpStdioServer:
    """One ``python -m mempalace.mcp_server --palace DIR`` child spoken to over stdio."""

    def __init__(self, palace: Path, env: Mapping[str, str], cwd: Path, stderr_path: Path,
                 timeout: float = DEFAULT_CALL_TIMEOUT) -> None:
        self._stderr = open(stderr_path, "wb")
        self.proc = subprocess.Popen(
            [sys.executable, "-s", "-m", "mempalace.mcp_server", "--palace", str(palace)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
            env=dict(env), cwd=str(cwd))
        self.timeout = timeout
        self._buffer = bytearray()
        self._next_id = 0
        self.non_json_lines = 0

    def _readline(self) -> bytes:
        deadline = time.monotonic() + self.timeout
        fd = self.proc.stdout.fileno()
        while b"\n" not in self._buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("MemPalace MCP server did not answer in time")
            ready, _, _ = select.select([fd], [], [], remaining)
            if ready:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    raise RuntimeError(f"MemPalace MCP server exited (rc={self.proc.poll()})")
                self._buffer += chunk
        line, _, rest = bytes(self._buffer).partition(b"\n")
        self._buffer = bytearray(rest)
        return line

    def _send(self, message: Mapping[str, Any]) -> None:
        self.proc.stdin.write(json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
        self._next_id += 1
        req_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": dict(params)})
        while True:
            line = self._readline().strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                self.non_json_lines += 1
                continue
            if isinstance(message, dict) and message.get("id") == req_id:
                return message

    def initialize(self) -> dict[str, Any]:
        response = self.request("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                               "clientInfo": {"name": "agent-memory-longmemeval", "version": BRIDGE_VERSION}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        info = (response.get("result") or {}).get("serverInfo") or {}
        if info.get("name") != "mempalace" or info.get("version") != MEMPALACE_VERSION:
            raise RuntimeError(f"unexpected MCP server identity {info}")
        return info

    def call(self, name: str, **arguments: Any) -> tuple[dict[str, Any], bool]:
        return tool_payload(self.request("tools/call", {"name": name, "arguments": arguments}))

    def close(self) -> int | None:
        try:
            if self.proc.stdin and not self.proc.stdin.closed:
                self.proc.stdin.close()  # stdin EOF is the server's documented shutdown
            self.proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        finally:
            self._stderr.close()
            if self.proc.stdout:
                self.proc.stdout.close()
        return self.proc.returncode


# ---------------------------------------------------------------- retriever

class MemPalaceLongMemEval:
    def __init__(self, root: Path, model_dir: Path, source_root: Path | None = None,
                 threads: str = "1", keep: bool = False):
        refuse_credentials(os.environ)
        self.install = verify_installed_package()  # editable or not, the tree hash must match
        self.source_commit = verify_source_checkout(source_root) if source_root else None
        self.model_dir = Path(model_dir).resolve(strict=True)
        self.model_identity = verify_model_dir(self.model_dir)
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.threads = threads
        self.keep = keep
        self.hashseed = os.environ.get("PYTHONHASHSEED")
        self.calls = 0

    def _question_dir(self, row_index: int) -> Path:
        qdir = self.root / f"q{row_index:05d}-{uuid.uuid4().hex[:12]}"
        (qdir / "home" / CHROMA_MODEL_SUBDIR).parent.mkdir(parents=True)
        (qdir / "home" / CHROMA_MODEL_SUBDIR).symlink_to(self.model_dir, target_is_directory=True)
        (qdir / "config").mkdir()
        return qdir

    def __call__(self, question: str, items: Sequence[Mapping[str, str]],
                 row_index: int, row: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(question, str) or not question:
            raise ValueError("question must be nonempty")
        ids = validate_corpus_ids(items)
        if not items:
            return {"ranked": [], "unmapped_result_count": 0, "capability": "retrieval_only"}
        keys = occurrence_keys(ids)
        qdir = self._question_dir(row_index)
        server = McpStdioServer(qdir / "palace", child_environment(qdir, self.threads, self.hashseed),
                                cwd=qdir, stderr_path=qdir / "server-stderr.log")
        try:
            started = time.perf_counter()
            server.initialize()
            startup_seconds = time.perf_counter() - started
            drawers = DrawerMap()
            skipped = already = chunked = 0
            failures: list[dict[str, str]] = []
            started = time.perf_counter()
            for item, doc_id, key in zip(items, ids, keys):
                if not item["text"].strip():
                    skipped += 1  # the product refuses empty content; never synthesize it
                    continue
                payload, is_error = server.call("mempalace_add_drawer", wing=WING, room=ROOM,
                                                content=item["text"], source_file=key)
                if is_error or payload.get("success") is not True or not payload.get("drawer_id"):
                    failures.append({"id": doc_id, "error": str(payload.get("error") or payload)[:300]})
                    continue
                if payload.get("reason") == "already_exists":
                    already += 1
                elif int(payload.get("chunks") or 1) > 1:
                    chunked += 1
                drawers.record(payload["drawer_id"], doc_id, key)
            ingest_seconds = time.perf_counter() - started
            started = time.perf_counter()
            result, is_error = server.call("mempalace_search", query=question, limit=MAX_DEPTH)
            recall_seconds = time.perf_counter() - started
            if is_error or "error" in result:
                raise RuntimeError(f"mempalace_search failed: {str(result.get('error') or result)[:300]}")
            hits = result.get("results") or []
            ranked, unmapped, stats = ranked_doc_ids(hits, drawers)
        finally:
            rc = server.close()
            stderr_tail = (qdir / "server-stderr.log").read_bytes()[-2000:].decode("utf-8", "replace")
            if not self.keep:
                shutil.rmtree(qdir, ignore_errors=True)
        self.calls += 1
        return {"ranked": ranked, "unmapped_result_count": unmapped,
                "provider_result_count": len(hits), "provider_hit_stats": stats,
                "total_before_filter": result.get("total_before_filter"),
                "query_sanitized": bool(result.get("query_sanitized")),
                "distinct_results_truncated": bool(result.get("distinct_results_truncated")),
                "filed_drawer_count": len(drawers.doc_ids), "already_exists_count": already,
                "chunked_item_count": chunked, "skipped_blank_items": skipped,
                "ingestion_failures": failures, "server_exit_code": rc,
                "server_non_json_stdout_lines": server.non_json_lines,
                "server_stderr_tail": stderr_tail if (rc not in (0, None) or failures) else None,
                "startup_seconds": startup_seconds, "ingest_seconds": ingest_seconds,
                "recall_seconds": recall_seconds, "capability": "retrieval_only",
                "question_isolated": True, "llm_calls": 0}


def identity(install: Mapping[str, Any] | None = None, model_identity: Mapping[str, Any] | None = None,
             threads: str = "1", source_commit: str | None = None) -> dict[str, Any]:
    return {
        "system_id": "mempalace", "system_kind": "external_memory",
        "system_revision": f"{MEMPALACE_VERSION}@{MEMPALACE_TAG_COMMIT}",
        "adapter_id": BRIDGE_ID, "adapter_revision": BRIDGE_VERSION,
        "boundary": "MemPalace MCP stdio server, public mempalace_add_drawer / mempalace_search tools, "
                    "product defaults, local ONNX MiniLM embeddings, no LLM; retrieval only",
        "configuration": {
            "repository": MEMPALACE_REPOSITORY, "tag": MEMPALACE_TAG, "tag_commit": MEMPALACE_TAG_COMMIT,
            "source_checkout_verified": source_commit,
            "install": dict(install or {}), "package_tree_sha256": MEMPALACE_PACKAGE_TREE_SHA256,
            "server": "python -s -m mempalace.mcp_server --palace <per-question dir> (stdio JSON-RPC)",
            "ingest": {"tool": "mempalace_add_drawer", "wing": WING, "room": ROOM,
                       "content": "frozen corpus item text, verbatim, one call per non-blank occurrence",
                       "source_file": "opaque uuid5(namespace, doc_id[, NUL k]) key; ids never in text",
                       "product_defaults": "chunk_size 800 chars, no overlap, for content above it; drawer id = "
                                           "hash(wing|room|content), identical content returns already_exists; "
                                           "no closets, no room classification, no entity extraction on this path"},
            "search": {"tool": "mempalace_search", "limit": MAX_DEPTH,
                       "product_defaults": "candidate_strategy vector, vector pool limit*4, hybrid rerank "
                                           "0.6 vector + 0.4 BM25 (min-max over pool), closet boost (inert: no "
                                           "closets filed), max_distance 1.5, query sanitizer (passthrough <=200 "
                                           "chars), identical >=100-char hits folded across sources into also_in"},
            "embeddings": dict(model_identity or {}), "backend": "chroma (default)",
            "embedding_threads": threads,
            "llm": "none: no LLM on the add_drawer/search path; credentials refused; child env is clean",
            "isolation": "fresh palace + config dir + HOME + server process per question; deleted after recall",
            "ranked_ids": "returned hit drawer_id (+ also_in refs) mapped via add_drawer results; source_path checked",
            "gold_access": "none", "qualification": "candidate until independent review",
            "not_used": "benchmarks/longmemeval_bench.py (its raw mode bypasses the package and measures ChromaDB)",
        },
        "authority_effect": "none",
    }


def install_longmemeval_mempalace_backend(register) -> str:
    root = os.environ.get("MEMPALACE_BENCH_ROOT")
    model = os.environ.get("MEMPALACE_BENCH_MODEL_DIR")
    if not root or not model:
        raise RuntimeError("Set MEMPALACE_BENCH_ROOT (disposable directory) and MEMPALACE_BENCH_MODEL_DIR "
                           "(pinned ChromaDB all-MiniLM-L6-v2 cache directory)")
    source = os.environ.get("MEMPALACE_SOURCE_ROOT")
    threads = os.environ.get("MEMPALACE_BENCH_EMBEDDING_THREADS", "1")
    adapter = MemPalaceLongMemEval(Path(root), Path(model), Path(source) if source else None, threads=threads,
                                   keep=os.environ.get("MEMPALACE_BENCH_KEEP") == "1")
    register(BACKEND, adapter, identity=identity(adapter.install, adapter.model_identity, threads,
                                                 adapter.source_commit))
    return BACKEND
