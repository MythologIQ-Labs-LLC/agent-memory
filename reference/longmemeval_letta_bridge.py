"""Letta archival-memory retrieval comparator for the LongMemEval profile (#810 cycle 2).

Candidate adapter, NOT an accepted lane. Registers ``letta_archival_local`` on the frozen
``reference/run_longmemeval.py`` external-backend seam; scoring, selection and gold are the
runner's, unchanged.

Boundary: Letta 0.16.8's own REST API on a loopback server running in its own environment
(Postgres + pgvector, migrated by Letta's Alembic history). Per question the adapter creates a
fresh agent, inserts each corpus item with ``POST /v1/agents/{id}/archival-memory`` (Letta stores
one passage per call and embeds it with the agent's embedding config), retrieves with
``GET /v1/agents/{id}/archival-memory/search`` (top_k=50), then deletes the agent. No agent
loop, no LLM call; the llm_config Letta's schema requires is never invoked. This measures
Letta's archival memory retrieval, not its self-editing agent memory.

Identity mapping: Letta sees only item text. Ranked ids come only from the passage ids its
insert call returned. Letta refuses passages above its archival token limit (8192 by default);
such refusals are counted per question and the item is simply absent, never split or
truncated by the adapter.

This module is stdlib-only so the runner's environment never imports Letta.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

BACKEND = "letta_archival_local"
BRIDGE_ID = "reference/longmemeval_letta_bridge.py"
BRIDGE_VERSION = "0.1.0-candidate"
LETTA_VERSION = "0.16.8"
LETTA_REPOSITORY = "https://github.com/letta-ai/letta"
LETTA_TAG_COMMIT = "1131535716e8a31c9a437f8695e25ac98f203a24"
MAX_DEPTH = 50


def validate_corpus_ids(items) -> list:
    """Repeated haystack sessions share one id with identical text (the runner checks this);
    refuse empty/non-string ids or one id with different texts."""
    ids, texts = [], {}
    for item in items:
        doc_id, text = item.get("id"), item.get("text")
        if not isinstance(doc_id, str) or not doc_id or not isinstance(text, str):
            raise ValueError("benchmark corpus items need non-empty string ids and string text")
        if texts.setdefault(doc_id, text) != text:
            raise ValueError(f"benchmark corpus id {doc_id!r} repeats with different text")
        ids.append(doc_id)
    return ids


class LettaArchivalLongMemEval:
    def __init__(self, letta_url: str, embed_url_file: Path):
        self.base = letta_url.rstrip("/") + "/v1"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback only
        emb = json.loads(Path(embed_url_file).read_text())
        self.embedding = emb["identity"]
        self.embedding_config = {"embedding_endpoint_type": "openai", "embedding_endpoint": emb["url"],
                                 "embedding_model": emb["identity"]["model"], "embedding_dim": emb["identity"]["dims"],
                                 "embedding_chunk_size": 300}
        self.llm_config = {"model": "unused", "model_endpoint_type": "openai",
                           "model_endpoint": "http://127.0.0.1:9/v1", "context_window": 8192}
        version = self._call("GET", "/health/").get("version")
        if version != LETTA_VERSION:
            raise RuntimeError(f"letta server {version} != pinned {LETTA_VERSION}")
        self.calls = 0

    def _call(self, method: str, path: str, body: Any = None) -> Any:
        req = urllib.request.Request(self.base + path, method=method, headers={"content-type": "application/json"},
                                     data=None if body is None else json.dumps(body).encode())
        with self.opener.open(req, timeout=600) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else None

    def __call__(self, question: str, items: Sequence[Mapping[str, str]],
                 row_index: int, row: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(question, str) or not question:
            raise ValueError("question must be nonempty")
        ids = validate_corpus_ids(items)
        if not items:
            return {"ranked": [], "unmapped_result_count": 0, "capability": "retrieval_only"}
        agent = self._call("POST", "/agents/", {"name": f"lme-q{row_index}-{uuid.uuid4().hex[:8]}",
                                                "include_base_tools": False, "memory_blocks": [],
                                                "llm_config": self.llm_config, "embedding_config": self.embedding_config})
        aid = agent["id"]
        by_passage: dict[str, str] = {}
        refused, skipped, passages = [], 0, 0
        try:
            start = time.perf_counter()
            for doc_id, item in zip(ids, items):
                if not item["text"].strip():
                    skipped += 1
                    continue
                try:
                    out = self._call("POST", f"/agents/{aid}/archival-memory", {"text": item["text"]})
                except urllib.error.HTTPError as exc:
                    if exc.code in (400, 413, 422):
                        refused.append({"code": exc.code, "detail": exc.read()[:200].decode("utf-8", "replace")})
                        continue
                    raise
                for p in out:
                    by_passage[p["id"]] = doc_id
                    passages += 1
            ingest_seconds = time.perf_counter() - start
            start = time.perf_counter()
            query = urllib.parse.urlencode({"query": question, "top_k": MAX_DEPTH})
            res = self._call("GET", f"/agents/{aid}/archival-memory/search?{query}")
            recall_seconds = time.perf_counter() - start
        finally:
            self._call("DELETE", f"/agents/{aid}")
        ranked, unmapped = [], 0
        for r in res["results"]:
            doc_id = by_passage.get(r["id"])
            if doc_id is None:
                unmapped += 1
            elif doc_id not in ranked:
                ranked.append(doc_id)
        self.calls += 1
        return {"ranked": ranked, "unmapped_result_count": unmapped, "returned_entry_count": res["count"],
                "passages_inserted": passages, "ingestion_refusals": len(refused), "refusal_samples": refused[:3],
                "skipped_blank_items": skipped, "ingest_seconds": ingest_seconds, "recall_seconds": recall_seconds,
                "capability": "retrieval_only", "question_isolated": True, "llm_calls": 0}


def identity() -> dict[str, Any]:
    return {
        "system_id": "letta", "system_kind": "external_memory",
        "system_revision": f"{LETTA_VERSION}@{LETTA_TAG_COMMIT}",
        "adapter_id": BRIDGE_ID, "adapter_revision": BRIDGE_VERSION,
        "boundary": "Letta server REST archival memory (create_passage / search_archival_memory), local embeddings, no LLM; retrieval only",
        "configuration": {
            "package": f"letta[server,sqlite,postgres]=={LETTA_VERSION} (dependencies resolved with exclude-newer 2026-05-15)",
            "repository": LETTA_REPOSITORY, "database": "PostgreSQL 18.1 + pgvector 0.8.5, Letta init.sql + alembic upgrade head",
            "embedding": "OpenAI-compatible loopback endpoint serving fastembed BAAI/bge-small-en-v1.5 (ONNX, 384-d)",
            "llm": "none invoked (agent llm_config points at a closed loopback port)",
            "search": {"top_k": MAX_DEPTH, "tags": None, "date_filters": None},
            "identity_mapping": "passage id returned by create_passage -> doc id; ids never in text",
            "isolation": "fresh agent (own archive) per question, deleted afterwards",
            "oversize_items": "Letta refuses passages above archival_memory_token_limit; counted, not split",
            "gold_access": "none", "qualification": "candidate until independent review",
        },
        "authority_effect": "none",
    }


def install_longmemeval_letta_backend(register) -> str:
    url = os.environ.get("LETTA_BENCH_URL", "http://127.0.0.1:8283")
    embed = os.environ.get("LETTA_BENCH_EMBED_URL_FILE")
    if not embed:
        raise RuntimeError("Set LETTA_BENCH_EMBED_URL_FILE to the local embedding server's url file")
    register(BACKEND, LettaArchivalLongMemEval(url, Path(embed)), identity=identity())
    return BACKEND
