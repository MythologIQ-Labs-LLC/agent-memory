"""Hindsight OSS chunk-only (no LLM) provider for the pinned AMB harness (#640, #810). Candidate adapter.

It registers ``hindsight-chunks-local`` in the frozen AMB REGISTRY at runtime. This is the same
Hindsight configuration as the LongMemEval chunk-only lane:

* Hindsight 0.10.2 at ``5fc4ce2``;
* ``llm_provider="none"``;
* bank ``retain_extraction_mode=chunks``, with observations, temporal, graph and reranking off
  and text search on;
* local ONNX e5-small;
* recall budget ``mid`` and ``max_tokens`` 65536.

It is not AMB's own ``hindsight`` provider, which uses Hindsight's LLM extraction, and not
Hindsight's published 66/77 row, which used LLM ingestion and structured filters. The product
runs in its pinned interpreter through ``hindsight_amb_worker.py``. That worker reuses the
verified LongMemEval setup and its strict bank qualification. This provider only speaks
JSON-lines to it, so AMB's environment needs no Hindsight packages.

There is one bank per AMB ``user_id``. Each document is retained verbatim under an opaque
sha256 document id. ``recall(query, top_k=k)`` uses AMB's per-case ``retrieval_limit``. Belief
ids, scope tags, context markers, timestamps, gold labels and query categories are never given
to Hindsight.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

AMB_REVISION = "03c1d0f1d27da63034f0931121c858faba512383"
AMB_PROVIDER_KEY = "hindsight-chunks-local"
BRIDGE_VERSION = "0.1.0-candidate"
_FORBIDDEN_ENV = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY",
                  "HINDSIGHT_API_LLM_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
WORKER = Path(__file__).resolve().parent / "hindsight_amb_worker.py"


def frozen_configuration() -> dict[str, Any]:
    return {
        "provider_key": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION,
        "product": "Hindsight OSS 0.10.2 @ 5fc4ce2 (pinned checkout), in-process HindsightServer, llm_provider=none, pg0",
        "bank": "retain_extraction_mode=chunks; observations/temporal/graph/reranking off; text search on (qualified per bank)",
        "embedder": "local ONNX intfloat/multilingual-e5-small @ 03415a4 (manifest-verified snapshot)",
        "retain": "one synchronous retain per AMB document, verbatim text, opaque sha256 document_id",
        "recall": "recall(query, top_k=k, max_tokens=65536, budget='mid'), k = AMB per-case retrieval_limit",
        "isolation": "one bank per AMB user_id",
        "not_supplied": ["belief ids", "scope tags", "document.context", "timestamps", "gold", "query category"],
        "not": "AMB's built-in LLM-extraction hindsight provider, nor Hindsight's published 66/77 (LLM ingestion + filters)",
    }


def install_amb_hindsight_provider(amb_root: str | Path) -> type:
    checkout = Path(amb_root).resolve()
    if str(checkout / "src") not in sys.path:
        sys.path.insert(0, str(checkout / "src"))
    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.memory.base import MemoryProvider  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    class HindsightChunksLocalAMBProvider(MemoryProvider):
        name = AMB_PROVIDER_KEY
        description = ("Hindsight OSS 0.10.2 chunk-only retrieval (llm_provider=none, local ONNX e5-small, "
                       "RRF of dense + text search); not Hindsight's LLM modes; #640/#810 candidate.")
        kind = "local"
        provider = "hindsight"
        variant = "oss-0.10.2-chunks-no-llm"
        link = "https://github.com/vectorize-io/hindsight"
        logo = None
        concurrency = 1
        supports_filters = False

        def __init__(self) -> None:
            self._proc: subprocess.Popen | None = None
            self._texts: dict[str, str] = {}

        def _call(self, request: dict) -> dict:
            assert self._proc is not None and self._proc.stdin and self._proc.stdout
            self._proc.stdin.write(json.dumps(request) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError(f"Hindsight worker exited (code {self._proc.poll()})")
            reply = json.loads(line)
            if not reply.get("ok"):
                raise RuntimeError(f"Hindsight worker error: {reply.get('error')}\n{reply.get('trace', '')}")
            return reply

        def prepare(self, store_dir: Path, unit_ids: set[str] | None = None, reset: bool = True) -> None:
            present = [k for k in _FORBIDDEN_ENV if os.environ.get(k)]
            if present:
                raise RuntimeError(f"refusing: credentials present for a no-LLM local profile: {present}")
            store = Path(store_dir)
            store.mkdir(parents=True, exist_ok=True)
            env = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "PYTHONHASHSEED", "HF_HUB_OFFLINE",
                                                     "HINDSIGHT_SOURCE_ROOT", "AGENT_MEMORY_HINDSIGHT_MODEL_DIR")
                   if key in os.environ}
            env["PYTHONPATH"] = str(WORKER.parent)
            # Embedded pg0 refuses to run as root, so a root caller must name an unprivileged user.
            run_as = os.environ.get("HINDSIGHT_RUN_AS") if os.geteuid() == 0 else None
            if os.geteuid() == 0 and not run_as:
                raise RuntimeError("running as root: set HINDSIGHT_RUN_AS to an unprivileged user for pg0")
            if run_as:
                import pwd  # noqa: PLC0415
                env["HOME"] = pwd.getpwnam(run_as).pw_dir
            # pg0 keys its instance by name under $HOME/.pg0; a separate HOME keeps this run's
            # embedded PostgreSQL apart from any other Hindsight run on the host.
            if os.environ.get("HINDSIGHT_WORKER_HOME"):
                env["HOME"] = os.environ["HINDSIGHT_WORKER_HOME"]
            self._stderr = open(store / "hindsight-worker.stderr.log", "ab")
            self._proc = subprocess.Popen([os.environ["HINDSIGHT_PYTHON"], str(WORKER)], stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, stderr=self._stderr, text=True, env=env,
                                          cwd="/tmp", user=run_as, group=None, extra_groups=[] if run_as else None)
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError(f"Hindsight worker failed to start (code {self._proc.poll()}); see {store}/hindsight-worker.stderr.log")
            self.ready = json.loads(line)
            self._texts = {}

        def ingest(self, documents: list[Document]) -> None:
            for document in documents:
                self._call({"op": "retain", "user": str(document.user_id), "doc_id": str(document.id),
                            "text": str(document.content)})
                self._texts[str(document.id)] = str(document.content)

        def retrieve(self, query: str, k: int = 10, user_id: str | None = None,
                     query_timestamp: str | None = None) -> tuple[list[Document], dict | None]:
            started = time.perf_counter()
            reply = self._call({"op": "recall", "user": str(user_id), "query": str(query), "k": max(1, int(k))})
            ranked = reply["ranked"][: max(0, int(k))]
            documents = [Document(id=doc, content=self._texts.get(doc, ""), user_id=user_id, source_ids=[doc])
                         for doc in ranked]
            return documents, {"provider": AMB_PROVIDER_KEY, "bridge_version": BRIDGE_VERSION,
                               "seconds": round(time.perf_counter() - started, 4), **reply["raw"]}

        def cleanup(self) -> None:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._call({"op": "close"})
                except Exception:  # noqa: BLE001
                    pass
                self._proc.wait(timeout=120)
            self._proc = None

    REGISTRY[AMB_PROVIDER_KEY] = HindsightChunksLocalAMBProvider
    return HindsightChunksLocalAMBProvider
