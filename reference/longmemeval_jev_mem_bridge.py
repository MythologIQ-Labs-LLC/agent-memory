"""Jev-Mem OSS retrieval-only comparator for Agent Memory LongMemEval (#817).

This is a real system adapter, NOT a benchmark result or an accepted frozen lane.
Use the existing run_longmemeval.py scorer unchanged. Requires an isolated checkout of
libingzheren/Jev-Mem pinned to UPSTREAM_SHA, with local Laya and embeddings available.
No answer model, grader or benchmark gold enters the adapter.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

UPSTREAM_REPO = "https://github.com/libingzheren/Jev-Mem"
UPSTREAM_SHA = "7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44"
CONFIG_BLOB_SHA = "ae526c67ccadbdbcbca84f2c1459990809a963f9"
BACKEND = "jev_mem_laya"
BRIDGE_ID = "reference/longmemeval_jev_mem_bridge.py"
BRIDGE_VERSION = "0.1.0-candidate"
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
        ids = [item.get("id") for item in items]
        if any(not isinstance(s, str) or not s for s in ids) or len(ids) != len(set(ids)):
            raise ValueError("benchmark corpus item IDs must be unique strings")
        if any(not isinstance(item.get("text"), str) or not isinstance(item.get("date"), str)
               for item in items):
            raise ValueError("missing benchmark text/date; never synthesize missing source data")

        # Import the reviewed public Jev-Mem classes, not Agent Memory's own
        # graph, embedding, retrieval or answer routines.
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        from memory.jev_mem_config import JevMemConfig
        from memory.memory_builder import MemoryBuilder
        from memory.query_engine import QueryEngine
        from memory.longmemeval_jev import parse_date

        config = JevMemConfig.load(self.config)
        if not (config.write_enabled and config.read_enabled and
                config.decision_backend == "laya" and not config.jev_mock and
                not config.fallback_to_magma):
            raise RuntimeError("Jev-Mem Laya write+read without MAGMA fallback required")

        with tempfile.TemporaryDirectory(prefix="am-jev-lme-") as scratch:
            builder = None
            try:
                start = time.perf_counter()
                builder = MemoryBuilder(scratch, embedding_model="minilm",
                                        jev_config=config, llm_enabled=False)
                for item in items:
                    if not item["text"].strip():
                        continue
                    builder.build(item["text"], timestamp=parse_date(item["date"]),
                                  metadata={"doc_id": item["id"], "original_text": item["text"],
                                            "source": "agent-memory-frozen-item"})
                ingest_seconds = time.perf_counter() - start
                graph_nodes = list(builder.trg.graph_db.nodes.values())
                fallbacks = sum(
                    getattr(node, "attributes", {}).get("jev_mem", {}).get("controller") == "magma_fallback"
                    for node in graph_nodes
                )
                if fallbacks:
                    raise RuntimeError(f"Not a Jev-Mem run: {fallbacks} MAGMA fallback nodes")
                engine = QueryEngine(builder.trg, builder.node_index, jev_config=config,
                                     jev_client=builder.jev, llm_controller=None)
                start = time.perf_counter()
                context, _ = engine.query(question, top_k=MAX_DEPTH)
                recall_seconds = time.perf_counter() - start
                ranked, unmapped = ranked_doc_ids(context.anchor_nodes, set(ids))
                self.calls += 1
                return {"ranked": ranked, "unmapped_result_count": unmapped,
                        "ingest_seconds": ingest_seconds, "recall_seconds": recall_seconds,
                        "system_nodes": len(graph_nodes), "jev_fallback_nodes": fallbacks,
                        "capability": "retrieval_only", "question_isolated": True,
                        "system_one": "Laya local", "system_two_calls": 0,
                        "source_revision": UPSTREAM_SHA}
            finally:
                if builder is not None:
                    builder.jev.close()


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
