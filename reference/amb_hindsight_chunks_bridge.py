"""Hindsight OSS v0.10.2 chunk-retrieval provider for the AMB harness, query-only tier (#640/#810).

Candidate comparator, not an accepted lane. The provider talks to a separately launched pinned
Hindsight server (reference/hindsight_local_server.py) over loopback with the pinned 0.10.2
Python client, through the #751 HindsightRetrievalBridge:

* one fresh bank per AMB user, created with the frozen chunk-retrieval switches and verified via
  get_bank_config before any ingest; no retain mission (no LLM runs, so none could apply);
* each AMB document is retained synchronously as one document whose native id is
  sha256(document id); the benchmark id never reaches the product;
* ``supports_filters = False``: the provider sees only the query text, exactly like the Agent
  Memory, Mem0-explicit and BM25 providers (protocol tier A). AMB's own ``hindsight`` provider,
  which receives the dataset's structured retrieval_filter and a benchmark retain mission, is a
  different tier and is not this row.

Recall is token-bounded in Hindsight; ``max_tokens`` is set high enough not to truncate below
AMB's requested k, and the ranked list is projected to k.
"""
from __future__ import annotations

import hashlib, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

AMB_PROVIDER_KEY = "hindsight-chunks-local"
BRIDGE_VERSION = "0.1.0-candidate"
RECALL_MAX_TOKENS = 65536
RECALL_BUDGET = "mid"
DEFAULT_USER_ID = "test-user"


def install_amb_hindsight_chunks_provider(amb_root: str | Path) -> type:
    checkout = Path(amb_root).resolve()
    if str(checkout / "src") not in sys.path:
        sys.path.insert(0, str(checkout / "src"))
    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.memory.base import MemoryProvider  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    class HindsightChunksAMBProvider(MemoryProvider):
        name = AMB_PROVIDER_KEY
        description = "Hindsight OSS 0.10.2 self-hosted, llm_provider=none, chunk retain, local ONNX e5-small, query-only"
        kind = "local"
        provider = "hindsight"
        variant = "oss-0.10.2-chunks-no-llm-query-only"
        link = "https://github.com/vectorize-io/hindsight"
        logo = None
        concurrency = 1
        supports_filters = False

        def __init__(self) -> None:
            self._client = None
            self._bridges: dict[str, Any] = {}
            self._run = None
            # The pinned client binds its aiohttp session to the loop it first runs on, and AMB
            # may call the provider from different threads: every client call, including
            # construction, runs on this one worker thread.
            self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hindsight-client")

        def _on_worker(self, fn, *args, **kwargs):
            return self._worker.submit(fn, *args, **kwargs).result()

        def prepare(self, store_dir: Path, unit_ids: set[str] | None = None, reset: bool = True) -> None:
            info = json.loads(Path(os.environ["AGENT_MEMORY_HINDSIGHT_URL_FILE"]).read_text())
            client_dir = os.environ["AGENT_MEMORY_HINDSIGHT_CLIENT_DIR"]  # pinned 0.10.2 client source
            if client_dir not in sys.path:
                sys.path.insert(0, client_dir)
            from hindsight_client import Hindsight  # noqa: PLC0415
            import hindsight_client  # noqa: PLC0415
            if not str(Path(hindsight_client.__file__).resolve()).startswith(str(Path(client_dir).resolve())):
                raise RuntimeError("pinned Hindsight client was not loaded")
            self._client = self._on_worker(Hindsight, base_url=info["url"], max_attempts=1)
            self._bridges = {}
            self._run = hashlib.sha256(f"{store_dir}{time.time()}".encode()).hexdigest()[:12]

        def _bridge(self, user_id: str | None):
            from agentmem_ref.evaluation.hindsight_bridge import EXPECTED_BANK_CONFIG, HindsightRetrievalBridge  # noqa: PLC0415
            uid = str(user_id) if user_id is not None else DEFAULT_USER_ID
            if uid not in self._bridges:
                bank_id = f"amb-{self._run}-{hashlib.sha256(uid.encode()).hexdigest()[:16]}"
                self._on_worker(self._client.create_bank, bank_id=bank_id, **EXPECTED_BANK_CONFIG)
                bridge = HindsightRetrievalBridge(client=self._client, bank_id=bank_id)
                self._on_worker(bridge.qualify_bank)
                self._bridges[uid] = bridge
            return self._bridges[uid]

        def ingest(self, documents: list[Document]) -> None:
            from agentmem_ref.evaluation.hindsight_bridge import CorpusDocument  # noqa: PLC0415
            for document in documents:
                bridge = self._bridge(document.user_id)
                self._on_worker(bridge.retain, CorpusDocument(str(document.id), str(document.content)))

        def retrieve(self, query: str, k: int = 10, user_id: str | None = None,
                     query_timestamp: str | None = None) -> tuple[list[Document], dict | None]:
            uid = str(user_id) if user_id is not None else DEFAULT_USER_ID
            bridge = self._bridge(uid)
            if bridge.ingest_count == 0:
                return [], {"provider": AMB_PROVIDER_KEY, "returned_count": 0, "empty_bank": True}
            env = self._on_worker(bridge.recall, str(query), top_k=max(1, int(k)), max_tokens=RECALL_MAX_TOKENS, budget=RECALL_BUDGET)
            docs = [Document(id=cid, content="", user_id=uid, source_ids=[cid]) for cid in env.mapped_corpus_ids]
            raw = {"provider": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION, "returned_count": len(docs),
                   "provider_result_count": len(env.raw_native_results),
                   "repeated_native_document_count": len(env.repeated_native_document_ids),
                   "bank_config_sha256": bridge.identity()["verified_bank_config_sha256"],
                   "recall": {"max_tokens": RECALL_MAX_TOKENS, "budget": RECALL_BUDGET, "projection_top_k": int(k)},
                   "query_timestamp_received": query_timestamp, "inference": "none", "authority_effect": "none"}
            return docs, raw

    REGISTRY[AMB_PROVIDER_KEY] = HindsightChunksAMBProvider
    return HindsightChunksAMBProvider
