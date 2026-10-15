"""Cognee OSS local (GLiNER, no LLM) retrieval comparator for the LongMemEval profile (#811).

Candidate adapter, NOT an accepted lane. Registers ``cognee_gliner_local`` on the frozen
``reference/run_longmemeval.py`` external-backend seam; scoring, selection and gold are
the runner's, unchanged.

Public surface only: ``cognee.remember(DataItem...)`` to ingest the frozen corpus items and
``cognee.recall(question, top_k=50)`` to retrieve. With no LLM key Cognee extracts its graph
with the bundled local GLiNER model and embeds locally (README "Run locally without an LLM").

Identity mapping: each item is ingested as ``DataItem(text, data_id=uuid5(NS, doc_id),
literal_text=True)``. Cognee sees only the item text and an opaque UUID, never the benchmark
id string (which encodes upstream gold labels as ``answer``/``noans``), the question's
answer, or ``has_answer``. Ranked ids come only from returned ``metadata.data_id``.

Isolation: before every question the adapter runs Cognee's documented reset
(``prune.prune_data()`` + ``prune.prune_system(metadata=True)``) and uses a fresh dataset.
"""
from __future__ import annotations

import asyncio
import importlib.metadata
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

BACKEND = "cognee_gliner_local"
BRIDGE_ID = "reference/longmemeval_cognee_bridge.py"
BRIDGE_VERSION = "0.1.0-candidate"
COGNEE_VERSION = "1.6.4"
COGNEE_REPOSITORY = "https://github.com/topoteretes/cognee"
COGNEE_TAG_COMMIT = "f154b32a9e544dac73e7ddf2010327cf9988edcd"
MAX_DEPTH = 50
ID_NAMESPACE = uuid.UUID("6f1d0c2a-8e1b-5c55-9a54-81100000a811")
_FORBIDDEN_ENV = ("OPENAI_API_KEY", "LLM_API_KEY", "ANTHROPIC_API_KEY", "EMBEDDING_API_KEY",
                  "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")


def opaque_id(doc_id: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, doc_id)


def ranked_doc_ids(entries: Sequence[Any], by_uuid: Mapping[str, Sequence[str]]) -> tuple[list[str], int, dict[str, int]]:
    """Map returned entries to benchmark ids via metadata.data_id only; keep native order.

    A data_id shared by several benchmark items (never expected: ids are unique UUIDs) would
    expand in corpus order. Entries without a known data_id are counted, never guessed.
    """
    ranked: list[str] = []
    seen: set[str] = set()
    unmapped = 0
    kinds: dict[str, int] = {}
    for entry in entries:
        kind = f"{getattr(entry, 'search_type', None)}:{getattr(entry, 'kind', None)}"
        kinds[kind] = kinds.get(kind, 0) + 1
        metadata = getattr(entry, "metadata", None)
        data_id = metadata.get("data_id") if isinstance(metadata, Mapping) else None
        targets = by_uuid.get(str(data_id)) if data_id is not None else None
        if not targets:
            unmapped += 1
            continue
        for doc_id in targets:
            if doc_id not in seen:
                ranked.append(doc_id)
                seen.add(doc_id)
    return ranked[:MAX_DEPTH], unmapped, kinds


class _Loop:
    """One event loop for the process; Cognee's engines bind to the loop that created them."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def run(self, coro, timeout: float | None = None):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)


class CogneeLocalLongMemEval:
    def __init__(self, root: Path):
        present = [name for name in _FORBIDDEN_ENV if os.environ.get(name)]
        if present:
            raise RuntimeError(f"refusing: credentials present for a no-LLM local profile: {present}")
        version = importlib.metadata.version("cognee")
        if version != COGNEE_VERSION:
            raise RuntimeError(f"cognee {version} != pinned {COGNEE_VERSION}")
        import cognee  # noqa: F401  (import after the credential check)
        self.cognee = cognee
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        cognee.config.system_root_directory(str(self.root / "system"))
        cognee.config.data_root_directory(str(self.root / "data"))
        self.loop = _Loop()
        self.calls = 0

    async def _question(self, question: str, items: Sequence[Mapping[str, str]], dataset: str):
        from cognee.tasks.ingestion.data_item import DataItem
        cognee = self.cognee
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
        data = [DataItem(data=item["text"], data_id=opaque_id(item["id"]), literal_text=True)
                for item in items if item["text"].strip()]
        start = time.perf_counter()
        remembered = await cognee.remember(data, dataset_name=dataset)
        ingest_seconds = time.perf_counter() - start
        start = time.perf_counter()
        results = await cognee.recall(question, datasets=[dataset], top_k=MAX_DEPTH)
        recall_seconds = time.perf_counter() - start
        return remembered, results, ingest_seconds, recall_seconds, len(items) - len(data)

    def __call__(self, question: str, items: Sequence[Mapping[str, str]],
                 row_index: int, row: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(question, str) or not question:
            raise ValueError("question must be nonempty")
        ids = [item.get("id") for item in items]
        if any(not isinstance(s, str) or not s for s in ids) or len(ids) != len(set(ids)):
            raise ValueError("benchmark corpus item IDs must be unique strings")
        if not items:
            return {"ranked": [], "unmapped_result_count": 0, "capability": "retrieval_only"}
        by_uuid: dict[str, list[str]] = {}
        for doc_id in ids:
            by_uuid.setdefault(str(opaque_id(doc_id)), []).append(doc_id)
        dataset = f"lme_q{row_index}_{uuid.uuid4().hex[:8]}"
        remembered, results, ingest_seconds, recall_seconds, skipped = self.loop.run(
            self._question(question, items, dataset))
        status = getattr(remembered, "status", None) if remembered is not None else None
        ranked, unmapped, kinds = ranked_doc_ids(results or [], by_uuid)
        self.calls += 1
        return {"ranked": ranked, "unmapped_result_count": unmapped,
                "returned_entry_count": len(results or []), "returned_entry_kinds": kinds,
                "remember_status": str(status) if status is not None else None,
                "ingest_seconds": ingest_seconds, "recall_seconds": recall_seconds,
                "skipped_blank_items": skipped, "capability": "retrieval_only",
                "question_isolated": True, "llm_calls": 0}


def identity() -> dict[str, Any]:
    return {
        "system_id": "cognee", "system_kind": "external_memory",
        "system_revision": f"{COGNEE_VERSION}@{COGNEE_TAG_COMMIT}",
        "adapter_id": BRIDGE_ID, "adapter_revision": BRIDGE_VERSION,
        "boundary": "Cognee OSS public remember/recall, local GLiNER extraction + local embeddings, no LLM; retrieval only",
        "configuration": {
            "package": f"cognee[gliner]=={COGNEE_VERSION}", "repository": COGNEE_REPOSITORY,
            "llm": "none (no key; LLM-dependent stages skip per upstream README)",
            "recall": {"top_k": MAX_DEPTH, "query_type": "default (auto_route)"},
            "remember": "product defaults (self_improvement default) per question dataset",
            "identity_mapping": "DataItem.data_id = uuid5(namespace, doc_id); ids never in text",
            "isolation": "prune_data + prune_system(metadata=True) before every question",
            "gold_access": "none", "qualification": "candidate until independent review",
        },
        "authority_effect": "none",
    }


def install_longmemeval_cognee_backend(register) -> str:
    root = os.environ.get("COGNEE_BENCH_ROOT")
    if not root:
        raise RuntimeError("Set COGNEE_BENCH_ROOT to a disposable directory")
    register(BACKEND, CogneeLocalLongMemEval(Path(root)), identity=identity())
    return BACKEND
