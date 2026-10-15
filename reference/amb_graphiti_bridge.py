"""Graphiti OSS (temporal knowledge-graph memory) provider for the pinned AMB harness (#812).

Candidate adapter, NOT an accepted lane. It registers ``graphiti-local`` in the frozen
vectorize-io/agent-memory-benchmark REGISTRY at runtime, without modifying AMB source, in the
same way as the Agent Memory and Mem0 bridges. AMB keeps dataset loading, ``RetrievalMode`` and
``PrecisionMemBenchDataset.score_retrieval``.

What is measured is Graphiti's own product path, through its public API only:

* ``Graphiti.add_episode(...)`` once per AMB document. Graphiti's LLM extracts entities and
  fact edges, deduplicates them against the graph, and sets temporal validity and invalidation.
  This is Graphiti's defining behaviour, so an LLM is required. Here it is a small local model,
  served over Graphiti's documented OpenAI-compatible local path (``OpenAIGenericClient`` +
  ``OpenAIEmbedder`` + ``OpenAIRerankerClient``, README "Using Graphiti with OpenAI-compatible
  providers and local LLMs"), behind ``graphiti_llamacpp_shim.py``.
* ``Graphiti.search(query, group_ids=[user], num_results=k)``, Graphiti's documented primary
  retrieval. It is hybrid: BM25 over facts plus cosine over fact embeddings, fused with RRF.
  It returns fact edges.

Identity mapping is provenance-only. Each episode is named by an opaque uuid5 of the AMB document
id, and the returned ``AddEpisodeResults.episode.uuid`` is mapped back to that id. A returned
fact edge maps to beliefs only through its ``episodes`` list (the episodes Graphiti records as
the fact's sources). AMB credits the first resolvable ``source_id`` of each returned document,
so a fact supported by several episodes is emitted as one document per supporting episode, in
Graphiti's order. The list is then cut to AMB's per-case budget ``k``. Facts whose episodes do not
map are counted and passed through, unchanged, to AMB's own resolver.

No belief id, scope tag, ``context`` marker, gold label or query category is given to Graphiti.
The bridge refuses to start if an inference credential is present, and it points every client at
the loopback shim, so no hosted inference is reachable.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import os
import re
import shutil
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AMB_REVISION = "03c1d0f1d27da63034f0931121c858faba512383"
AMB_PROVIDER_KEY = "graphiti-local"
BRIDGE_VERSION = "0.1.0-candidate"
GRAPHITI_PACKAGE = "graphiti-core"
GRAPHITI_VERSION = "0.31.1"
GRAPHITI_REPOSITORY = "https://github.com/getzep/graphiti"
GRAPHITI_TAG = "v0.31.1"
FALKORDBLITE_VERSION = "0.10.0"
LLM_MODEL = "qwen2.5-3b-instruct-q4_k_m"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768
LLM_TEMPERATURE = 0.0  # declared deviation from Graphiti's default 1.0, for reproducibility
SEMAPHORE_LIMIT = "1"  # Graphiti's documented concurrency knob; one local inference slot
EPISODE_SOURCE_DESCRIPTION = "user memory"
ID_NAMESPACE = uuid.UUID("0b5f4a5e-6c1d-5d2e-9f3a-812000000812")
_FORBIDDEN_ENV = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
                  "GROQ_API_KEY", "VOYAGE_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
_LOOPBACK = re.compile(r"^http://(127\.0\.0\.1|localhost):\d+/v1/?$")
_INERT_KEY = "local-no-hosted-inference"


def episode_name(doc_id: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, str(doc_id)))


def group_id_for(user_id: str | None) -> str:
    """Graphiti group ids allow letters, digits, ``-`` and ``_`` only."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(user_id or "default-user"))


def parse_reference_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise ValueError("AMB document has no timestamp; Graphiti needs a reference time")


def expand_edges(edges: list[Any], doc_by_episode: dict[str, str], k: int) -> tuple[list[tuple[Any, str | None]], int]:
    """(edge, doc_id) pairs in Graphiti's order, one per supporting episode, cut to k."""
    pairs: list[tuple[Any, str | None]] = []
    unmapped = 0
    for edge in edges:
        mapped = [doc_by_episode[e] for e in (getattr(edge, "episodes", None) or []) if e in doc_by_episode]
        if not mapped:
            unmapped += 1
            pairs.append((edge, None))
        for doc_id in dict.fromkeys(mapped):
            pairs.append((edge, doc_id))
    return pairs[: max(0, k)], unmapped


def frozen_configuration(base_url: str) -> dict[str, Any]:
    return {
        "provider_key": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION,
        "package": f"{GRAPHITI_PACKAGE}[falkordblite]=={GRAPHITI_VERSION}", "tag": GRAPHITI_TAG,
        "graph_store": f"embedded FalkorDB Lite (falkordblite=={FALKORDBLITE_VERSION}), fresh file per run",
        "llm": {"client": "OpenAIGenericClient (structured_output_mode=json_schema, Graphiti default)",
                "model": LLM_MODEL, "small_model": LLM_MODEL, "temperature": LLM_TEMPERATURE,
                "temperature_note": "Graphiti default is 1.0; 0 declared before execution for reproducibility",
                "base_url": base_url},
        "embedder": {"client": "OpenAIEmbedder", "model": EMBED_MODEL, "embedding_dim": EMBED_DIM, "base_url": base_url},
        "cross_encoder": "OpenAIRerankerClient(config=<same local LLM config>) (constructed; unused by the default search recipe)",
        "add": "add_episode(name=uuid5(doc_id), episode_body=document.content, source=EpisodeType.text, "
               f"source_description='{EPISODE_SOURCE_DESCRIPTION}', reference_time=document.timestamp, group_id=user)",
        "search": "search(query, group_ids=[user], num_results=k) (Graphiti default hybrid edge search, RRF)",
        "identity_mapping": "edge.episodes -> episode uuid -> AMB document id; one document per supporting episode; cut to k",
        "concurrency": {"amb": 1, "SEMAPHORE_LIMIT": SEMAPHORE_LIMIT},
        "telemetry": "GRAPHITI_TELEMETRY_ENABLED=false",
        "not_supplied_to_graphiti": ["belief ids", "scope tags", "document.context", "gold", "query category"],
    }


class _Loop:
    """One event loop for the process; Graphiti's driver and clients bind to it."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()


def install_amb_graphiti_provider(amb_root: str | Path) -> type:
    checkout = Path(amb_root).resolve()
    if str(checkout / "src") not in sys.path:
        sys.path.insert(0, str(checkout / "src"))
    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.memory.base import MemoryProvider  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    class GraphitiLocalAMBProvider(MemoryProvider):
        name = AMB_PROVIDER_KEY
        description = (f"Graphiti OSS {GRAPHITI_VERSION} temporal knowledge graph, embedded FalkorDB Lite, "
                       f"local {LLM_MODEL} + {EMBED_MODEL} via llama.cpp; #812 candidate configuration.")
        kind = "local"
        provider = "graphiti"
        variant = f"oss-{GRAPHITI_VERSION}-local-llm"
        link = GRAPHITI_REPOSITORY
        logo = None
        concurrency = 1
        supports_filters = False

        def __init__(self) -> None:
            self._graphiti: Any = None
            self._loop: _Loop | None = None
            self._doc_by_episode: dict[str, str] = {}
            self._ingest_log: list[dict[str, Any]] = []

        def prepare(self, store_dir: Path, unit_ids: set[str] | None = None, reset: bool = True) -> None:
            present = [k for k in _FORBIDDEN_ENV if os.environ.get(k)]
            if present:
                raise RuntimeError(f"refusing: inference credentials present for a local-only lane: {present}")
            base_url = os.environ.get("GRAPHITI_LOCAL_BASE_URL", "")
            if not _LOOPBACK.match(base_url):
                raise RuntimeError("GRAPHITI_LOCAL_BASE_URL must be a loopback http://127.0.0.1:<port>/v1 endpoint")
            version = importlib.metadata.version(GRAPHITI_PACKAGE)
            if version != GRAPHITI_VERSION:
                raise RuntimeError(f"{GRAPHITI_PACKAGE} {version} != pinned {GRAPHITI_VERSION}")
            os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"
            os.environ["SEMAPHORE_LIMIT"] = SEMAPHORE_LIMIT
            store = Path(store_dir)
            if reset:
                shutil.rmtree(store, ignore_errors=True)
            store.mkdir(parents=True, exist_ok=True)
            self._base_url = base_url
            self._loop = _Loop()
            self._graphiti = self._loop.run(self._build(store, base_url))
            self._doc_by_episode = {}
            self._ingest_log = []

        async def _build(self, store: Path, base_url: str) -> Any:
            from graphiti_core import Graphiti  # noqa: PLC0415
            from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient  # noqa: PLC0415
            from graphiti_core.driver.falkordb_driver import FalkorDriver  # noqa: PLC0415
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig  # noqa: PLC0415
            from graphiti_core.llm_client.config import LLMConfig  # noqa: PLC0415
            from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient  # noqa: PLC0415
            from redislite.async_falkordb_client import AsyncFalkorDB  # type: ignore[import-not-found]  # noqa: PLC0415

            llm_config = LLMConfig(api_key=_INERT_KEY, model=LLM_MODEL, small_model=LLM_MODEL,
                                   base_url=base_url, temperature=LLM_TEMPERATURE)
            llm_client = OpenAIGenericClient(config=llm_config)
            graphiti = Graphiti(
                graph_driver=FalkorDriver(falkor_db=AsyncFalkorDB(dbfilename=str(store / "graphiti.db"))),
                llm_client=llm_client,
                embedder=OpenAIEmbedder(config=OpenAIEmbedderConfig(
                    api_key=_INERT_KEY, embedding_model=EMBED_MODEL, embedding_dim=EMBED_DIM, base_url=base_url)),
                cross_encoder=OpenAIRerankerClient(config=llm_config),
            )
            await graphiti.build_indices_and_constraints()
            return graphiti

        def _require(self) -> Any:
            if self._graphiti is None or self._loop is None:
                raise RuntimeError("Graphiti provider must be prepared before use")
            return self._graphiti

        def ingest(self, documents: list[Document]) -> None:
            graphiti = self._require()
            from graphiti_core.nodes import EpisodeType  # noqa: PLC0415

            for document in documents:
                started = time.perf_counter()
                result = self._loop.run(graphiti.add_episode(
                    name=episode_name(document.id), episode_body=str(document.content),
                    source_description=EPISODE_SOURCE_DESCRIPTION,
                    reference_time=parse_reference_time(document.timestamp),
                    source=EpisodeType.text, group_id=group_id_for(document.user_id)))
                self._doc_by_episode[str(result.episode.uuid)] = str(document.id)
                self._ingest_log.append({"doc_id": str(document.id), "episode_uuid": str(result.episode.uuid),
                                         "nodes": len(result.nodes), "edges": len(result.edges),
                                         "invalidated_edges": sum(1 for e in result.edges if getattr(e, "invalid_at", None)),
                                         "seconds": round(time.perf_counter() - started, 3)})
                print(f"graphiti-ingest {len(self._ingest_log)}/{len(documents)} {self._ingest_log[-1]}",
                      file=sys.stderr, flush=True)

        def retrieve(self, query: str, k: int = 10, user_id: str | None = None,
                     query_timestamp: str | None = None) -> tuple[list[Document], dict | None]:
            graphiti = self._require()
            started = time.perf_counter()
            edges = self._loop.run(graphiti.search(str(query), group_ids=[group_id_for(user_id)], num_results=max(0, int(k))))
            seconds = time.perf_counter() - started
            pairs, unmapped = expand_edges(edges, self._doc_by_episode, int(k))
            documents = [Document(id=doc_id or f"graphiti-edge:{edge.uuid}", content=str(edge.fact),
                                  user_id=user_id, source_ids=[doc_id] if doc_id else [])
                         for edge, doc_id in pairs]
            raw = {
                "provider": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION, "amb_revision": AMB_REVISION,
                "graphiti_version": GRAPHITI_VERSION, "num_results": max(0, int(k)), "search_seconds": round(seconds, 4),
                "edges": [{"uuid": str(e.uuid), "fact": str(e.fact), "episodes": list(e.episodes or []),
                           "valid_at": str(e.valid_at) if e.valid_at else None,
                           "invalid_at": str(e.invalid_at) if e.invalid_at else None,
                           "expired_at": str(e.expired_at) if getattr(e, "expired_at", None) else None}
                          for e in edges],
                "unmapped_edge_count": unmapped, "returned_document_count": len(documents),
            }
            return documents, raw

        def cleanup(self) -> None:
            if self._graphiti is not None and self._loop is not None:
                self._loop.run(self._graphiti.close())
            self._graphiti = None

        def ingest_log(self) -> list[dict[str, Any]]:
            return list(self._ingest_log)

    REGISTRY[AMB_PROVIDER_KEY] = GraphitiLocalAMBProvider
    return GraphitiLocalAMBProvider
