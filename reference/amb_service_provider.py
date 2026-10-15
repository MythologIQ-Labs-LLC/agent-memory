"""Query-only AMB providers backed by a competitor running in its own environment (#810 cycle 2).

Some products cannot share AMB's pinned environment (conflicting langchain/cognee pins). Each
runs as a loopback JSON service (reference/competitor_service.py) in its own venv; this module
registers a thin AMB provider per service. The provider forwards AMB's documents and query text
unchanged and maps results back only through the ids the service returns. supports_filters is
False: the same query-only tier as agent-memory, mem0-explicit and bm25.

AGENT_MEMORY_AMB_SERVICES="name=url-file[,name=url-file...]" selects the services to register.
"""
from __future__ import annotations

import json, os, sys, urllib.request
from pathlib import Path


def _call(url: str, path: str, payload: dict, timeout: float = 86400.0) -> dict:
    req = urllib.request.Request(url.rstrip("/") + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback only, never the egress proxy
    with opener.open(req, timeout=timeout) as resp:
        out = json.loads(resp.read().decode())
    if out.get("error"):
        raise RuntimeError(f"competitor service error on {path}: {out['error']}")
    return out


def install_amb_service_providers(amb_root: str | Path) -> list[str]:
    spec = os.environ.get("AGENT_MEMORY_AMB_SERVICES", "")
    if not spec:
        return []
    checkout = Path(amb_root).resolve()
    if str(checkout / "src") not in sys.path:
        sys.path.insert(0, str(checkout / "src"))
    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.memory.base import MemoryProvider  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    names = []
    for item in spec.split(","):
        name, url_file = item.split("=", 1)

        class ServiceProvider(MemoryProvider):
            supports_filters = False
            kind = "local"
            concurrency = 1
            logo = None
            _url_file = url_file

            def __init__(self) -> None:
                info = json.loads(Path(self._url_file).read_text())
                self._url = info["url"]
                self._identity = info.get("identity", {})

            def prepare(self, store_dir: Path, unit_ids: set[str] | None = None, reset: bool = True) -> None:
                _call(self._url, "/prepare", {"store_dir": str(store_dir), "reset": bool(reset)})

            def ingest(self, documents: list[Document]) -> None:
                docs = [{"id": str(d.id), "text": str(d.content), "user_id": d.user_id, "timestamp": d.timestamp} for d in documents]
                _call(self._url, "/ingest", {"documents": docs})

            def retrieve(self, query: str, k: int = 10, user_id: str | None = None,
                         query_timestamp: str | None = None) -> tuple[list[Document], dict | None]:
                out = _call(self._url, "/retrieve", {"query": str(query), "k": int(k), "user_id": user_id})
                docs = [Document(id=i, content="", user_id=user_id, source_ids=[i]) for i in out["ranked_ids"]]
                raw = {k2: v for k2, v in out.items() if k2 != "ranked_ids"}
                raw.update({"provider": self.name, "returned_count": len(docs), "authority_effect": "none"})
                return docs, raw

        ServiceProvider.__name__ = f"Service_{name.replace('-', '_')}"
        ServiceProvider.name = name
        ServiceProvider.description = f"{name} via loopback competitor service (own pinned environment), query-only"
        ServiceProvider.provider = name.split("-")[0]
        ServiceProvider.variant = name
        ServiceProvider.link = None
        REGISTRY[name] = ServiceProvider
        names.append(name)
    return names
