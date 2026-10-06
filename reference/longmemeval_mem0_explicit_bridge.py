"""Mem0 OSS explicit-memory backend for the LongMemEval retrieval profile (#640, lane v2).

This is the comparator configuration of the frozen same-harness lane
``longmemeval-s-retrieval-parity-v1``. It registers Mem0 OSS ``2.2.1`` as an external
backend of ``reference/run_longmemeval.py`` through the runner's system-neutral
registration seam, so Mem0 is scored by exactly the evaluator, input, selection, gold
identity, and exclusions that score the Agent Memory control and the lexical baseline.

The Mem0 configuration is the one lane v1 (``reference/amb_mem0_explicit_bridge.py``)
froze and executed: explicit memory (``infer=False`` on every add, the constructed LLM
replaced by a fail-closed guard), local ``multi-qa-MiniLM-L6-cos-v1`` embeddings at a
pinned Hugging Face revision, local on-disk Qdrant, base-package install posture (no
fastembed keyword search, no spaCy lemmatizer). Only the vector-store collection name and
the per-question namespace rule are specific to this profile.

Isolation: the LongMemEval retrieval protocol evaluates every question against its own
haystack (upstream ``process_item_flat_index`` builds a flat index per question). The
runner evaluates the same question once per plane (session, turn), so this backend gives
every retriever call its own Mem0 ``user_id`` namespace and searches with that filter.
Benchmark item ids are stored as ``metadata.doc_id`` only; they never enter memory text.

External benchmark output remains evidence, never memory authority.
"""

from __future__ import annotations

import atexit
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_REFERENCE_ROOT = Path(__file__).resolve().parent
if str(_REFERENCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_REFERENCE_ROOT))

from amb_mem0_explicit_bridge import (  # noqa: E402  (the lane v1 configuration this lane reuses verbatim)
    EMBEDDER_HF_REPO,
    EMBEDDER_HF_REVISION,
    EMBEDDER_PROVIDER,
    EMBEDDING_DIMS,
    MEM0_LICENSE,
    MEM0_PACKAGE,
    MEM0_REPOSITORY,
    MEM0_TAG,
    MEM0_TAG_COMMIT,
    MEM0_VERSION,
    OPTIONAL_COMPONENTS,
    SEARCH_RERANK,
    SEARCH_THRESHOLD,
    VECTOR_STORE_PROVIDER,
    _NoInferenceGuard,
    frozen_mem0_config,
    verify_mem0_version,
)

LANE_ID = "longmemeval-s-retrieval-parity-v1"
BACKEND_NAME = "mem0_explicit"
SYSTEM_ID = "mem0-oss"
BRIDGE_VERSION = "0.1.0"
ADAPTER_ID = "reference/longmemeval_mem0_explicit_bridge.py"
VECTOR_STORE_COLLECTION = "lme640_mem0_explicit"
# The runner scores rankings at k in {1, 3, 5, 10, 30, 50} and reports the top 50; a
# ranking bounded at the deepest scored k cannot change any scored metric.
SEARCH_TOP_K = 50
# Exact releases resolved by the accepted lane v1 Mem0 row (workflow run 37351804149).
# Lane v2 has no harness lock to inherit, so the retrieval stack is pinned to those
# releases explicitly; any other resolution is a different frozen row.
DEPENDENCY_PINS = (
    f"{MEM0_PACKAGE}=={MEM0_VERSION}",
    "qdrant-client==1.17.0",
    "sentence-transformers==5.2.3",
    "torch==2.10.0",
)
_RECORDED_PACKAGES = ("mem0ai", "qdrant-client", "sentence-transformers", "torch", "openai", "posthog")


def frozen_mem0_lane_config(store_dir: str | Path) -> dict[str, Any]:
    """Lane v1's exact Mem0 configuration with this profile's collection name."""

    config = frozen_mem0_config(store_dir)
    config["vector_store"]["config"]["collection_name"] = VECTOR_STORE_COLLECTION
    return config


def frozen_configuration() -> dict[str, Any]:
    """Machine-readable description of the frozen configuration (bound into the lane record)."""

    return {
        "backend": BACKEND_NAME,
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
            "mode": "local path, on_disk=true, fresh per run, one collection for the whole run",
            "collection": VECTOR_STORE_COLLECTION,
        },
        "isolation": "one Mem0 user_id namespace per retriever call (per question and plane); search is filtered to that namespace",
        "add": {
            "call": "Memory.add([{'role': 'user', 'content': <item text>}], user_id=<namespace>, metadata={'doc_id': <item id>, 'source_date': <session date>}, infer=False)",
            "content_rule": "item text verbatim (session: user turns joined by one space; turn: one user turn); ids, dates and gold never enter memory text",
        },
        "search": {
            "call": f"Memory.search(question, top_k={SEARCH_TOP_K}, filters={{'user_id': <namespace>}})",
            "top_k": SEARCH_TOP_K,
            "top_k_rule": "the deepest scored k; bounding the ranking there cannot change any scored metric",
            "threshold": SEARCH_THRESHOLD,
            "rerank": SEARCH_RERANK,
        },
        "identity_mapping": "benchmark item id stored as metadata.doc_id at ingest and read back from each result; results without doc_id are counted as unmapped and dropped from the ranking",
        "optional_components": OPTIONAL_COMPONENTS,
        "dependency_pins": list(DEPENDENCY_PINS),
        "concurrency": 1,
        "telemetry": "MEM0_TELEMETRY=false; MEM0_DIR inside the disposable store",
    }


def _git_blob(path: Path) -> str:
    try:
        return subprocess.run(
            ["git", "hash-object", str(path)], capture_output=True, text=True, check=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _package_version(name: str) -> str | None:
    from importlib import metadata

    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def optional_component_posture() -> dict[str, bool]:
    return {
        "fastembed_installed": importlib.util.find_spec("fastembed") is not None,
        "spacy_installed": importlib.util.find_spec("spacy") is not None,
    }


def verify_install_posture() -> dict[str, Any]:
    """Fail closed unless the imported Mem0 is the frozen release with the frozen extras posture."""

    import mem0  # noqa: PLC0415  (lazy: Mem0 is optional for the other backends)

    version = verify_mem0_version(mem0)
    posture = optional_component_posture()
    if posture["fastembed_installed"]:
        raise RuntimeError("frozen Mem0 row forbids the fastembed extra (it switches Mem0 to hybrid BM25 retrieval)")
    if posture["spacy_installed"]:
        raise RuntimeError("frozen Mem0 row forbids the spaCy extra (it changes Mem0's text normalization)")
    return {"mem0ai": version, **posture}


class Mem0ExplicitLongMemEvalBackend:
    """One Mem0 instance per run; one namespace per retriever call."""

    def __init__(self, store_dir: str | Path | None = None) -> None:
        self._owned_store = store_dir is None
        self._store_dir = Path(store_dir) if store_dir is not None else Path(tempfile.mkdtemp(prefix="longmemeval-mem0-"))
        self._memory: Any = None
        self._calls = 0
        self._posture: dict[str, Any] | None = None

    @property
    def store_dir(self) -> Path:
        return self._store_dir

    def open(self) -> dict[str, Any]:
        shutil.rmtree(self._store_dir, ignore_errors=True)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MEM0_TELEMETRY", "false")
        os.environ["MEM0_DIR"] = str(self._store_dir / "mem0-home")
        self._posture = verify_install_posture()
        import mem0  # noqa: PLC0415

        memory = mem0.Memory.from_config(frozen_mem0_lane_config(self._store_dir))
        memory.llm = _NoInferenceGuard()
        self._memory = memory
        self._calls = 0
        return dict(self._posture)

    def close(self) -> None:
        memory, self._memory = self._memory, None
        client = getattr(getattr(memory, "vector_store", None), "client", None)
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # noqa: BLE001  (best-effort release of the local Qdrant handle)
                pass
        if self._owned_store:
            shutil.rmtree(self._store_dir, ignore_errors=True)

    def _require_memory(self) -> Any:
        if self._memory is None:
            raise RuntimeError("Mem0 explicit-memory backend must be opened before use")
        return self._memory

    def retrieve(
        self,
        question: str,
        items: Sequence[Mapping[str, str]],
        row_index: int,
        row: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        memory = self._require_memory()
        self._calls += 1
        namespace = f"lme-{row_index}-{self._calls}"
        ingestion_failures: list[str] = []
        started = time.perf_counter()
        for item in items:
            result = memory.add(
                [{"role": "user", "content": str(item["text"])}],
                user_id=namespace,
                metadata={"doc_id": str(item["id"]), "source_date": str(item.get("date", "")), "lme_bridge": BRIDGE_VERSION},
                infer=False,
            )
            rows = result.get("results", result) if isinstance(result, dict) else result
            added = [entry for entry in (rows or []) if isinstance(entry, dict) and entry.get("event") == "ADD"]
            if not added:
                ingestion_failures.append(f"no ADD event for item {len(ingestion_failures)}: {result!r}"[:200])
        ingest_seconds = time.perf_counter() - started
        started = time.perf_counter()
        response = memory.search(str(question), top_k=SEARCH_TOP_K, filters={"user_id": namespace})
        recall_seconds = time.perf_counter() - started
        results = response.get("results", []) if isinstance(response, dict) else list(response or [])
        ranked: list[str] = []
        unmapped = 0
        for entry in results:
            metadata = (entry.get("metadata") or {}) if isinstance(entry, dict) else {}
            doc_id = metadata.get("doc_id")
            if not doc_id:
                unmapped += 1
                continue
            ranked.append(str(doc_id))
        return {
            "ranked": ranked,
            "mem0_namespace": namespace,
            "search_top_k": SEARCH_TOP_K,
            "mem0_result_count": len(results),
            "unmapped_result_count": unmapped,
            "ingestion_failures": ingestion_failures,
            "ingest_seconds": round(ingest_seconds, 6),
            "recall_seconds": round(recall_seconds, 6),
        }


def identity(posture: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The identity recorded under ``execution.external_backends`` for this backend."""

    return {
        "system_id": SYSTEM_ID,
        "system_kind": "external_memory",
        "system_revision": MEM0_TAG_COMMIT,
        "system_identity": f"{MEM0_REPOSITORY} {MEM0_TAG} ({MEM0_PACKAGE}=={MEM0_VERSION}, {MEM0_LICENSE})",
        "adapter_id": ADAPTER_ID,
        "adapter_revision": _git_blob(Path(__file__).resolve()),
        "bridge_version": BRIDGE_VERSION,
        "lane_id": LANE_ID,
        "boundary": "Mem0 OSS public Memory.add/Memory.search surface; explicit memory, no inference, no governed admission path",
        "configuration": frozen_configuration(),
        "resolved_packages": {name: _package_version(name) for name in _RECORDED_PACKAGES},
        "install_posture": dict(posture or {}),
        "inference": "none",
        "authority_effect": "none",
    }


def install_longmemeval_mem0_explicit_backend(
    register: Callable[..., dict[str, Any]], *, store_dir: str | Path | None = None
) -> str:
    """Entry for ``run_longmemeval.py --external-backend longmemeval_mem0_explicit_bridge:install_longmemeval_mem0_explicit_backend``.

    Opens the Mem0 store (verifying the frozen release and extras posture first) and
    registers ``mem0_explicit`` with its full identity. Returns the backend name.
    """

    backend = Mem0ExplicitLongMemEvalBackend(store_dir)
    posture = backend.open()
    atexit.register(backend.close)
    register(BACKEND_NAME, backend.retrieve, identity=identity(posture))
    return BACKEND_NAME


__all__ = [
    "LANE_ID",
    "BACKEND_NAME",
    "SYSTEM_ID",
    "BRIDGE_VERSION",
    "ADAPTER_ID",
    "VECTOR_STORE_COLLECTION",
    "SEARCH_TOP_K",
    "DEPENDENCY_PINS",
    "MEM0_VERSION",
    "MEM0_TAG_COMMIT",
    "EMBEDDER_HF_REPO",
    "EMBEDDER_HF_REVISION",
    "Mem0ExplicitLongMemEvalBackend",
    "frozen_mem0_lane_config",
    "frozen_configuration",
    "verify_install_posture",
    "optional_component_posture",
    "identity",
    "install_longmemeval_mem0_explicit_backend",
]
