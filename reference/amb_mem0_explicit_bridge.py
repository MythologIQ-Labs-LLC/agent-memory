"""Mem0 OSS explicit-memory provider for the pinned vectorize-io/agent-memory-benchmark (AMB).

This is the #640 comparator configuration for Mem0 OSS. It deliberately does not reuse
AMB's own ``mem0`` provider at the frozen revision, because that provider:

* performs reflective LLM extraction through Gemini on every ``add`` (credentialed,
  model-dependent, and a Mem0+Gemini composition rather than Mem0 OSS alone);
* calls ``Memory.search(query, user_id=..., limit=...)``, which Mem0 2.2.1 rejects in
  favour of ``search(query, top_k=..., filters={"user_id": ...})``;
* floats the Mem0 package version (``mem0ai>=1.0.5``).

The frozen lane instead runs Mem0 ``2.2.1`` exactly, in explicit-memory mode
(``infer=False``): every benchmark document is stored verbatim, embedded locally with a
pinned sentence-transformers model, and searched through Mem0's own retrieval. No LLM is
invoked; a guard makes any LLM call fail closed. Everything the benchmark sees is Mem0's
own product behaviour on the same documents BM25 and Agent Memory receive.

The bridge registers at runtime without modifying AMB source. It imports ``mem0`` lazily
so the Agent Memory bridge keeps working when Mem0 is not installed. External benchmark
output remains evidence, never memory authority.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

AMB_REVISION = "03c1d0f1d27da63034f0931121c858faba512383"
AMB_PROVIDER_KEY = "mem0-explicit"
BRIDGE_VERSION = "0.1.0"

MEM0_PACKAGE = "mem0ai"
MEM0_VERSION = "2.2.1"
MEM0_REPOSITORY = "mem0ai/mem0"
MEM0_TAG = "v2.2.1"
MEM0_TAG_COMMIT = "94c3fe9f238f3dbf29c9ce98643bd71eb13077cd"
MEM0_LICENSE = "Apache-2.0"

EMBEDDER_PROVIDER = "huggingface"
EMBEDDER_HF_REPO = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
EMBEDDER_HF_REVISION = "b207367332321f8e44f96e224ef15bc607f4dbf0"
EMBEDDING_DIMS = 384

VECTOR_STORE_PROVIDER = "qdrant"
VECTOR_STORE_COLLECTION = "amb640_mem0_explicit"
SEARCH_THRESHOLD = 0.1  # Mem0 2.2.1 default; recorded, not tuned
SEARCH_RERANK = False
DEFAULT_USER_ID = "amb-640-default-user"

# Product-default install posture: ``pip install mem0ai==2.2.1`` with no extras. Mem0's
# optional keyword (fastembed) and lemmatizer (spaCy) components change retrieval when
# present, so their absence is part of the frozen configuration and is recorded at
# execution. A row with extras installed would be a different frozen row.
OPTIONAL_COMPONENTS = {
    "install": "pip install mem0ai==2.2.1 (base package, no extras)",
    "fastembed_bm25_keyword_search": "not installed; Mem0 logs 'BM25 keyword search disabled' and ranks by vector similarity only",
    "spacy_lemmatizer": "not installed; Mem0 skips text lemmatization",
    "graph_store": "not configured",
    "reranker": "not configured (rerank=False)",
}

# Satisfies Mem0's eager OpenAI client construction only. It is never a valid credential,
# no request can succeed with it, and the guard below makes any attempt fail closed.
_INERT_LLM_API_KEY = "explicit-memory-lane-no-inference"


class _NoInferenceGuard:
    """Replaces the constructed LLM so an inference call is an error, not a silent score."""

    def __getattr__(self, name: str) -> Any:
        def _refuse(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(
                f"Mem0 explicit-memory lane invoked LLM.{name}; the frozen lane forbids inference"
            )

        return _refuse


def frozen_mem0_config(store_dir: str | Path) -> dict[str, Any]:
    """The exact Mem0 configuration frozen for the lane. Only ``store_dir`` varies per run."""

    store = Path(store_dir)
    return {
        "llm": {
            "provider": "openai",
            "config": {"api_key": _INERT_LLM_API_KEY, "model": "unused-no-inference"},
        },
        "embedder": {
            "provider": EMBEDDER_PROVIDER,
            "config": {
                "model": EMBEDDER_HF_REPO,
                "embedding_dims": EMBEDDING_DIMS,
                "model_kwargs": {"revision": EMBEDDER_HF_REVISION},
            },
        },
        "vector_store": {
            "provider": VECTOR_STORE_PROVIDER,
            "config": {
                "collection_name": VECTOR_STORE_COLLECTION,
                "path": str(store / "qdrant"),
                "embedding_model_dims": EMBEDDING_DIMS,
                "on_disk": True,
            },
        },
        "history_db_path": str(store / "history.db"),
    }


def frozen_configuration() -> dict[str, Any]:
    """Machine-readable description of the frozen configuration (bound into the lane record)."""

    return {
        "provider_key": AMB_PROVIDER_KEY,
        "bridge_version": BRIDGE_VERSION,
        "package": f"{MEM0_PACKAGE}=={MEM0_VERSION}",
        "tag": MEM0_TAG,
        "tag_commit": MEM0_TAG_COMMIT,
        "inference": "infer=False on every add; LLM replaced by a fail-closed guard after construction",
        "embedder": {
            "provider": EMBEDDER_PROVIDER,
            "model": EMBEDDER_HF_REPO,
            "revision": EMBEDDER_HF_REVISION,
            "dims": EMBEDDING_DIMS,
        },
        "vector_store": {
            "provider": VECTOR_STORE_PROVIDER,
            "mode": "local path, on_disk=true, fresh per run",
            "collection": VECTOR_STORE_COLLECTION,
        },
        "search": {
            "call": "Memory.search(query, top_k=<case retrieval_limit>, filters={'user_id': <AMB user_id>})",
            "threshold": SEARCH_THRESHOLD,
            "rerank": SEARCH_RERANK,
        },
        "add": {
            "call": "Memory.add([{'role': 'user', 'content': <document content>}], user_id=<AMB user_id>, metadata={'doc_id': ...}, infer=False)",
            "content_rule": "document.content verbatim; structured messages, timestamps, and tags are not supplied to Mem0",
        },
        "identity_mapping": "AMB document id stored as metadata.doc_id at ingest and returned as Document.source_ids; resolution path source_id",
        "optional_components": OPTIONAL_COMPONENTS,
        "concurrency": 1,
        "telemetry": "MEM0_TELEMETRY=false; MEM0_DIR inside the disposable store",
    }


def verify_mem0_version(module: Any) -> str:
    """Fail closed unless the imported ``mem0`` is the exact frozen release."""

    actual = str(getattr(module, "__version__", "") or "")
    if actual != MEM0_VERSION:
        raise RuntimeError(f"Mem0 version mismatch: lane freezes {MEM0_PACKAGE}=={MEM0_VERSION}, found {actual!r}")
    return actual


def _document_metadata(document: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {"doc_id": str(document.id), "amb_bridge": BRIDGE_VERSION}
    timestamp = getattr(document, "timestamp", None)
    if timestamp is not None:
        metadata["source_timestamp"] = str(timestamp)
    return metadata


def install_amb_mem0_explicit_provider(amb_root: str | Path) -> type:
    """Register the Mem0 explicit-memory provider in a loaded-or-loadable AMB checkout."""

    checkout = Path(amb_root).resolve()
    src = str(checkout / "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.memory.base import MemoryProvider  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    class Mem0ExplicitAMBProvider(MemoryProvider):
        name = AMB_PROVIDER_KEY
        description = (
            f"Mem0 OSS {MEM0_VERSION} in explicit-memory mode (infer=False, no LLM), local "
            f"{EMBEDDER_HF_REPO} embeddings, local Qdrant; #640 frozen comparator configuration."
        )
        kind = "local"
        provider = "mem0"
        variant = f"oss-explicit-memory-{MEM0_VERSION}"
        link = "https://github.com/mem0ai/mem0"
        logo = None
        concurrency = 1
        supports_filters = False

        def __init__(self) -> None:
            self._memory: Any = None
            self._store_dir: Path | None = None
            self._ingested = 0
            self._mem0_version: str | None = None

        def prepare(self, store_dir: Path, unit_ids: set[str] | None = None, reset: bool = True) -> None:
            self._store_dir = Path(store_dir)
            if reset:
                shutil.rmtree(self._store_dir, ignore_errors=True)
            self._store_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("MEM0_TELEMETRY", "false")
            os.environ.setdefault("MEM0_DIR", str(self._store_dir / "mem0-home"))
            import mem0  # noqa: PLC0415  (lazy: Mem0 is optional for other providers)

            self._mem0_version = verify_mem0_version(mem0)
            memory = mem0.Memory.from_config(frozen_mem0_config(self._store_dir))
            memory.llm = _NoInferenceGuard()
            self._memory = memory
            self._ingested = 0

        def _require_memory(self) -> Any:
            if self._memory is None:
                raise RuntimeError("Mem0 explicit-memory provider must be prepared before use")
            return self._memory

        def ingest(self, documents: list[Document]) -> None:
            memory = self._require_memory()
            for document in documents:
                result = memory.add(
                    [{"role": "user", "content": str(document.content)}],
                    user_id=str(document.user_id) if document.user_id is not None else DEFAULT_USER_ID,
                    metadata=_document_metadata(document),
                    infer=False,
                )
                rows = result.get("results", result) if isinstance(result, dict) else result
                added = [row for row in (rows or []) if isinstance(row, dict) and row.get("event") == "ADD"]
                if not added:
                    raise RuntimeError(f"Mem0 did not store AMB document {document.id!r}: {result!r}")
                self._ingested += 1

        def retrieve(
            self,
            query: str,
            k: int = 10,
            user_id: str | None = None,
            query_timestamp: str | None = None,
        ) -> tuple[list[Document], dict | None]:
            memory = self._require_memory()
            uid = str(user_id) if user_id is not None else DEFAULT_USER_ID
            response = memory.search(str(query), top_k=max(0, int(k)), filters={"user_id": uid})
            rows = response.get("results", []) if isinstance(response, dict) else list(response or [])
            documents: list[Document] = []
            unmapped = 0
            for row in rows:
                metadata = row.get("metadata") or {}
                doc_id = metadata.get("doc_id")
                if not doc_id:
                    unmapped += 1
                    documents.append(Document(id=str(row.get("id")), content=str(row.get("memory", "")), user_id=uid))
                    continue
                documents.append(
                    Document(
                        id=str(doc_id),
                        content=str(row.get("memory", "")),
                        user_id=uid,
                        source_ids=[str(doc_id)],
                    )
                )
            raw = {
                "provider": AMB_PROVIDER_KEY,
                "bridge_version": BRIDGE_VERSION,
                "mem0_version": self._mem0_version,
                "amb_revision": AMB_REVISION,
                "search_top_k": max(0, int(k)),
                "search_threshold": SEARCH_THRESHOLD,
                "returned_count": len(documents),
                "unmapped_results": unmapped,
                "scores": [row.get("score") for row in rows],
                "mem0_memory_ids": [row.get("id") for row in rows],
                "query_timestamp_received": query_timestamp,
                "query_timestamp_used_as_memory_authority": False,
                "inference": "none",
                "authority_effect": "none",
            }
            return documents, raw

    REGISTRY[AMB_PROVIDER_KEY] = Mem0ExplicitAMBProvider
    return Mem0ExplicitAMBProvider


__all__ = [
    "AMB_REVISION",
    "AMB_PROVIDER_KEY",
    "BRIDGE_VERSION",
    "MEM0_PACKAGE",
    "MEM0_VERSION",
    "MEM0_TAG_COMMIT",
    "EMBEDDER_HF_REPO",
    "EMBEDDER_HF_REVISION",
    "EMBEDDING_DIMS",
    "OPTIONAL_COMPONENTS",
    "frozen_mem0_config",
    "frozen_configuration",
    "verify_mem0_version",
    "install_amb_mem0_explicit_provider",
]
