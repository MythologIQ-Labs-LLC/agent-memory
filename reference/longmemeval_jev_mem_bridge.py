"""Jev-Mem OSS retrieval-only comparator for Agent Memory LongMemEval (#817).

This is a real system adapter, NOT a benchmark result or an accepted frozen lane.
Use the existing run_longmemeval.py scorer unchanged. Requires an isolated checkout of
libingzheren/Jev-Mem pinned to UPSTREAM_SHA, with local Laya and embeddings available.
No answer model, grader or benchmark gold enters the adapter.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

UPSTREAM_REPO = "https://github.com/libingzheren/Jev-Mem"
UPSTREAM_SHA = "7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44"
CONFIG_BLOB_SHA = "ae526c67ccadbdbcbca84f2c1459990809a963f9"
BACKEND = "jev_mem_laya"
BRIDGE_ID = "reference/longmemeval_jev_mem_bridge.py"
BRIDGE_VERSION = "0.2.1-candidate"
MAX_DEPTH = 50


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE, timeout=12,
    ).strip()


def verify_upstream(root: Path) -> dict[str, Any]:
    """Fail closed on wrong source/config or uncommitted source modifications."""
    if not root.is_dir():
        raise RuntimeError("Jev-Mem checkout does not exist")
    head = _git(root, "rev-parse", "HEAD")
    if head != UPSTREAM_SHA:
        raise RuntimeError(f"Jev-Mem revision mismatch: {head} != {UPSTREAM_SHA}")
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Jev-Mem checkout has local modifications")
    config_path = root / "config" / "laya_mem.json"
    if _git(root, "hash-object", str(config_path)) != CONFIG_BLOB_SHA:
        raise RuntimeError("Jev-Mem Laya configuration is not the reviewed source blob")
    return {"upstream": UPSTREAM_REPO, "source_revision": head,
            "config_blob": CONFIG_BLOB_SHA, "model_revision_qualified": False}


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


def ranked_doc_ids(anchor_nodes: Sequence[Any], allowed_ids: set[str]) -> tuple[list[str], int]:
    """Read benchmark IDs solely from returned graph-node attributes, never text matching."""
    ids: list[str] = []
    seen: set[str] = set()
    unmapped = 0
    for node in anchor_nodes:
        attributes = getattr(node, "attributes", None)
        doc_id = attributes.get("doc_id") if isinstance(attributes, Mapping) else None
        if not isinstance(doc_id, str) or doc_id not in allowed_ids:
            unmapped += 1
        elif doc_id not in seen:
            ids.append(doc_id)
            seen.add(doc_id)
    return ids[:MAX_DEPTH], unmapped


class DecisionCounter:
    """Jev-Mem audit sink that counts System-One decisions; it never alters them.

    Passed as ``JevClient(audit=...)`` so every ``jev_decision`` (Laya call or
    per-client cache hit) and every ``jev_fallback`` is observable per question.
    """

    def __init__(self) -> None:
        self.decisions: dict[str, dict[str, int]] = {}
        self.fallbacks: list[dict[str, Any]] = []
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self.other_events: dict[str, int] = {}

    def emit(self, event: str, **values: Any) -> None:
        if event == "jev_decision":
            bucket = self.decisions.setdefault(str(values.get("operation")), {})
            source = str(values.get("source"))
            bucket[source] = bucket.get(source, 0) + 1
            for name in self.usage:
                self.usage[name] += int((values.get("usage") or {}).get(name, 0) or 0)
        elif event == "jev_fallback":
            self.fallbacks.append({"operation": values.get("operation"), "reason": values.get("reason")})
        else:
            self.other_events[event] = self.other_events.get(event, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        model_calls = sum(n for ops in self.decisions.values()
                          for source, n in ops.items() if source != "cache")
        return {"decisions_by_operation": {k: dict(v) for k, v in sorted(self.decisions.items())},
                "model_decisions": model_calls, "fallback_events": list(self.fallbacks),
                "usage": dict(self.usage), "events": dict(sorted(self.other_events.items()))}


_LAYA_LOCK = threading.Lock()
_LAYA_AGENTS: dict[tuple, Any] = {}


def share_laya_weights() -> None:
    """Load each Laya checkpoint once per process instead of once per question.

    ``laya.Agent`` holds only load-time state (weights, tokenizer, temperatures),
    so reuse cannot change a decision. Each question still gets a fresh
    ``JevClient`` (and decision cache), graph, vector store and scratch directory.
    """
    laya = importlib.import_module("laya")
    if getattr(laya.load, "_agent_memory_shared", False):
        return
    original = laya.load

    def load(model_id_or_path="convaiinnovations/laya", device=None, token=None, subfolder=None):
        key = (model_id_or_path, device, subfolder)
        with _LAYA_LOCK:
            if key not in _LAYA_AGENTS:
                _LAYA_AGENTS[key] = original(model_id_or_path, device=device, token=token, subfolder=subfolder)
            return _LAYA_AGENTS[key]

    load._agent_memory_shared = True
    laya.load = load


class JevMemLayaLongMemEval:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.posture = verify_upstream(self.root)
        # The environment identity must record HF revisions and weights hashes in
        # the execution manifest. These variables do not magically pin upstream HF
        # downloads. Until verified by the executor, results remain CANDIDATE.
        self.config = self.root / "config" / "laya_mem.json"
        self.calls = 0

    def __call__(self, question: str, items: Sequence[Mapping[str, str]],
                 row_index: int, row: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(question, str) or not question:
            raise ValueError("question must be nonempty")
        if not items:
            return {"ranked": [], "unmapped_result_count": 0,
                    "capability": "retrieval_only", "source_revision": UPSTREAM_SHA}
        ids = validate_corpus_ids(items)  # repeats ingest as separate nodes; ranking dedupes by doc_id
        if any(not isinstance(item.get("text"), str) or not isinstance(item.get("date"), str)
               for item in items):
            raise ValueError("missing benchmark text/date; never synthesize missing source data")

        # Import the reviewed public Jev-Mem classes, not Agent Memory's own
        # graph, embedding, retrieval or answer routines.
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        from memory.jev_client import JevClient
        from memory.jev_mem_config import JevMemConfig
        from memory.memory_builder import MemoryBuilder
        from memory.query_engine import QueryEngine
        from memory.longmemeval_jev import parse_date

        config = JevMemConfig.load(self.config)
        if not (config.write_enabled and config.read_enabled and
                config.decision_backend == "laya" and not config.jev_mock and
                not config.fallback_to_magma):
            raise RuntimeError("Jev-Mem Laya write+read without MAGMA fallback required")
        share_laya_weights()

        with tempfile.TemporaryDirectory(prefix="am-jev-lme-") as scratch:
            builder = None
            client = None
            write_log, read_log = DecisionCounter(), DecisionCounter()
            try:
                client = JevClient(config, audit=write_log)
                start = time.perf_counter()
                builder = MemoryBuilder(scratch, embedding_model="minilm", jev_config=config,
                                        jev_client=client, llm_enabled=False)
                skipped_blank = 0
                rejected = 0
                for item in items:
                    if not item["text"].strip():
                        skipped_blank += 1  # Jev-Mem refuses empty text; never synthesize it
                        continue
                    node = builder.build(item["text"], timestamp=parse_date(item["date"]),
                                         metadata={"doc_id": item["id"], "original_text": item["text"],
                                                   "source": "agent-memory-frozen-item"})
                    if node is None:
                        rejected += 1
                ingest_seconds = time.perf_counter() - start
                graph_nodes = list(builder.trg.graph_db.nodes.values())
                fallbacks = sum(
                    getattr(node, "attributes", {}).get("jev_mem", {}).get("controller") == "magma_fallback"
                    for node in graph_nodes
                )
                if fallbacks or write_log.fallbacks:
                    raise RuntimeError(f"Not a Jev-Mem run: {fallbacks} MAGMA fallback nodes, "
                                       f"{len(write_log.fallbacks)} write fallback events")
                client.audit = read_log
                engine = QueryEngine(builder.trg, builder.node_index, jev_config=config,
                                     jev_client=client, llm_controller=None)
                start = time.perf_counter()
                context, _ = engine.query(question, top_k=MAX_DEPTH)
                recall_seconds = time.perf_counter() - start
                meta = dict(getattr(context, "metadata", {}) or {})
                if meta.get("controller") != "jev-mem" or meta.get("decision_backend") != "laya":
                    raise RuntimeError(f"Not a Jev-Mem read: controller={meta.get('controller')!r}")
                if read_log.fallbacks or meta.get("fallback_events"):
                    raise RuntimeError("Not a Jev-Mem run: read fallback events recorded")
                ranked, unmapped = ranked_doc_ids(context.anchor_nodes, set(ids))
                self.calls += 1
                return {"ranked": ranked, "unmapped_result_count": unmapped,
                        "ingest_seconds": ingest_seconds, "recall_seconds": recall_seconds,
                        "system_nodes": len(graph_nodes), "jev_fallback_nodes": fallbacks,
                        "system_links": int(builder.trg.stats.get("links_created", 0)),
                        "skipped_blank_items": skipped_blank, "rejected_items": rejected,
                        "laya_write": write_log.snapshot(), "laya_read": read_log.snapshot(),
                        "jev_read": {key: meta.get(key) for key in (
                            "controller", "decision_backend", "jev_calls", "jev_cache_hits", "llm_calls",
                            "nodes_visited", "edges_examined", "retrieval_depth", "depth_limit",
                            "stopping_decision", "top_k_returned", "graph_budgets", "graph_budget_used")},
                        "capability": "retrieval_only", "question_isolated": True,
                        "system_one": "Laya local", "system_two_calls": 0,
                        "source_revision": UPSTREAM_SHA}
            finally:
                if client is not None:
                    client.close()


def identity() -> dict[str, Any]:
    return {
        "system_id": "jev-mem", "system_kind": "external_memory",
        "system_revision": UPSTREAM_SHA,
        "adapter_id": BRIDGE_ID, "adapter_revision": BRIDGE_VERSION,
        "boundary": "Jev-Mem Laya local System-One graph retrieval via public MemoryBuilder / QueryEngine; no answer QA",
        "configuration": {
            "upstream": UPSTREAM_REPO, "config_blob": CONFIG_BLOB_SHA,
            "decision_backend": "laya", "embedding_model": "minilm",
            "fallback_to_magma": False, "scorer": "unchanged run_longmemeval.py",
            "retrieval_top_k": MAX_DEPTH, "question_isolated": True,
            "laya_weights": "loaded once per process; fresh JevClient, decision cache and graph per question",
            "gold_access": "none", "models_provenance": "REQUIRED before accepted comparison",
            "qualification": "candidate until real model+dataset evidence and independent review",
        },
        "authority_effect": "none",
    }


def install_longmemeval_jev_mem_backend(register) -> str:
    root = os.environ.get("JEV_MEM_SOURCE_ROOT")
    if not root:
        raise RuntimeError("Set JEV_MEM_SOURCE_ROOT to the exact upstream Jev-Mem checkout")
    adapter = JevMemLayaLongMemEval(Path(root))
    register(BACKEND, adapter, identity=identity())
    return BACKEND
