"""Hindsight OSS v0.10.2 credential-free chunk-retrieval comparator for LongMemEval (#640).

Candidate adapter, NOT an accepted lane. Registers ``hindsight_chunks_onnx`` on the frozen
``reference/run_longmemeval.py`` external-backend seam; selection, gold and scoring are the
runner's, unchanged.

Product posture is exactly the #751 H3 self-hosted smoke: pinned clean source checkout
(5fc4ce2, v0.10.2), in-process ``HindsightServer`` with ``llm_provider=none`` and no key,
embedded PostgreSQL (pg0, loopback), local ONNX ``intfloat/multilingual-e5-small`` at a
hash-verified immutable revision, bank switches ``retain_extraction_mode=chunks``,
observations/temporal/graph/reranking off, text search on.

Per question: a fresh bank is created with those switches, verified through
``get_bank_config`` before any ingest (``HindsightRetrievalBridge.qualify_bank``), every
non-empty frozen corpus item is retained synchronously as one document whose native id is
``sha256(doc_id)`` (the benchmark id never reaches the product), the question is recalled
once, and the bank is deleted. Hindsight bounds recall by tokens, not k: ``max_tokens`` is
set high enough that it never truncates below the shared 50-deep projection.
"""
from __future__ import annotations

import atexit
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

from agentmem_ref.evaluation.hindsight_bridge import (
    EXPECTED_BANK_CONFIG, HINDSIGHT_RELEASE, HINDSIGHT_SOURCE_REVISION,
    CorpusDocument, HindsightRetrievalBridge,
)

BACKEND = "hindsight_chunks_onnx"
BRIDGE_ID = "reference/longmemeval_hindsight_bridge.py"
BRIDGE_VERSION = "0.1.0-candidate"
MAX_DEPTH = 50
RECALL_MAX_TOKENS = 65536
RECALL_BUDGET = "mid"  # product default


class HindsightLongMemEval:
    def __init__(self, source_dir: Path, model_dir: Path):
        from agentmem_ref.evaluation.hindsight_model_snapshot import snapshot_identity
        from agentmem_ref.evaluation.hindsight_selfhosted_smoke import (
            isolated_environment, verify_pinned_checkout,
        )
        self.source = verify_pinned_checkout(source_dir)
        self.model_identity = snapshot_identity(model_dir.resolve(strict=True))
        os.environ.update(isolated_environment(model_dir.resolve(strict=True)))
        import importlib.metadata
        if importlib.metadata.version("hindsight-all") != HINDSIGHT_RELEASE:
            raise RuntimeError("installed Hindsight release differs from pinned 0.10.2")
        import hindsight
        Path(hindsight.__file__).resolve().relative_to(self.source)  # editable from the pinned checkout
        from hindsight import HindsightServer
        from hindsight_client import Hindsight
        self.work = tempfile.mkdtemp(prefix="am-hindsight-lme-")
        os.chdir(self.work)  # pg0 data lives under the working directory
        self.server = HindsightServer(db_url="pg0", llm_provider="none", llm_api_key="",
                                      host="127.0.0.1", mcp_enabled=False, log_level="warning")
        if self.server.llm_provider != "none" or self.server.llm_api_key != "":
            raise RuntimeError("server has a non-frozen LLM provider or credential")
        started = time.perf_counter()
        self.server.start(timeout=float(os.environ.get("AGENT_MEMORY_HINDSIGHT_START_TIMEOUT", "600")))
        self.cold_start_seconds = time.perf_counter() - started
        self.client = Hindsight(base_url=self.server.url, max_attempts=1)
        atexit.register(self.close)
        self.calls = 0

    def close(self) -> None:
        if getattr(self, "_closed", False):
            return
        self._closed = True
        try:
            self.client.close()
        finally:
            try:
                self.server.stop()
            except RuntimeError as exc:  # pg0 stop during interpreter shutdown; data dir is disposable
                if "after shutdown" not in str(exc):
                    raise

    def __call__(self, question: str, items: Sequence[Mapping[str, str]],
                 row_index: int, row: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(question, str) or not question:
            raise ValueError("question must be nonempty")
        ids = [item.get("id") for item in items]
        if any(not isinstance(s, str) or not s for s in ids) or len(ids) != len(set(ids)):
            raise ValueError("benchmark corpus item IDs must be unique strings")
        bank_id = f"am-lme-{uuid.uuid4().hex}"
        self.client.create_bank(bank_id=bank_id, **EXPECTED_BANK_CONFIG)
        try:
            bridge = HindsightRetrievalBridge(client=self.client, bank_id=bank_id)
            config_sha = bridge.qualify_bank()
            skipped = 0
            start = time.perf_counter()
            for item in items:
                if not item["text"].strip():
                    skipped += 1  # the bridge refuses empty text; never synthesize it
                    continue
                bridge.retain(CorpusDocument(item["id"], item["text"]))
            ingest_seconds = time.perf_counter() - start
            start = time.perf_counter()
            envelope = bridge.recall(question, top_k=MAX_DEPTH, max_tokens=RECALL_MAX_TOKENS, budget=RECALL_BUDGET)
            recall_seconds = time.perf_counter() - start
        finally:
            self.client.delete_bank(bank_id)
        self.calls += 1
        return {"ranked": list(envelope.mapped_corpus_ids), "unmapped_result_count": 0,
                "provider_result_count": len(envelope.raw_native_results),
                "repeated_native_document_count": len(envelope.repeated_native_document_ids),
                "retained_count": bridge.ingest_count, "skipped_blank_items": skipped,
                "bank_config_sha256": config_sha,
                "ingest_seconds": ingest_seconds, "recall_seconds": recall_seconds,
                "capability": "retrieval_only", "question_isolated": True, "llm_calls": 0}


def identity(model_identity: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "system_id": "hindsight", "system_kind": "external_memory",
        "system_revision": f"{HINDSIGHT_RELEASE}@{HINDSIGHT_SOURCE_REVISION}",
        "adapter_id": BRIDGE_ID, "adapter_revision": BRIDGE_VERSION,
        "boundary": "Hindsight OSS public retain/recall client, self-hosted, llm_provider=none, chunk retain; retrieval only",
        "configuration": {
            "bank": dict(EXPECTED_BANK_CONFIG), "reranker_provider": "rrf (bank reranking off)",
            "embeddings": dict(model_identity or {}),
            "recall": {"max_tokens": RECALL_MAX_TOKENS, "budget": RECALL_BUDGET, "projection_top_k": MAX_DEPTH},
            "retain": "one synchronous document per frozen item; native id sha256(doc_id); no timestamp passed",
            "isolation": "fresh bank per question, deleted after recall; one server per process",
            "gold_access": "none", "qualification": "candidate until independent review",
            "limitation": "measures Hindsight as a credential-free chunk retrieval memory, not its LLM-extraction/observation mode",
        },
        "authority_effect": "none",
    }


def install_longmemeval_hindsight_backend(register) -> str:
    source = os.environ.get("HINDSIGHT_SOURCE_ROOT")
    model = os.environ.get("AGENT_MEMORY_HINDSIGHT_MODEL_DIR")
    if not source or not model:
        raise RuntimeError("Set HINDSIGHT_SOURCE_ROOT and AGENT_MEMORY_HINDSIGHT_MODEL_DIR")
    adapter = HindsightLongMemEval(Path(source), Path(model))
    register(BACKEND, adapter, identity=identity(adapter.model_identity))
    return BACKEND
