"""Loopback JSON service hosting one competitor memory system for the AMB service provider.

Usage: python competitor_service.py --system {cognee-local,langmem-local} --url-file F [system options]
Endpoints: POST /prepare {store_dir, reset}; POST /ingest {documents:[{id,text,user_id,timestamp}]};
POST /retrieve {query,k,user_id} -> {ranked_ids:[...], ...diagnostics}. Runs single-threaded.
The service never sees AMB's gold, assertions or scope filters, only document text, ids and queries.
"""
from __future__ import annotations

import argparse, hashlib, json, os, sys, time, traceback, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class CogneeLocal:
    """Cognee 1.6.4 local GLiNER path; same public calls as longmemeval_cognee_bridge."""
    def __init__(self, a):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from longmemeval_cognee_bridge import CogneeLocalLongMemEval, identity, occurrence_ids, ranked_doc_ids
        self.impl = CogneeLocalLongMemEval(Path(a.root))
        self.occurrence_ids, self.ranked_doc_ids = occurrence_ids, ranked_doc_ids
        self.identity = identity()
        self.by_uuid, self.datasets = {}, {}

    def prepare(self, store_dir, reset):
        cognee = self.impl.cognee
        async def _p():
            await cognee.prune.prune_data(); await cognee.prune.prune_system(metadata=True)
        self.impl.loop.run(_p())
        self.by_uuid, self.datasets = {}, {}

    def ingest(self, documents):
        from cognee.tasks.ingestion.data_item import DataItem
        groups = {}
        for d in documents:
            groups.setdefault(d["user_id"] or "test-user", []).append(d)
        out = {"ingest_seconds": {}}
        for user, docs in groups.items():
            ds = self.datasets.setdefault(user, f"amb_{hashlib.sha256(user.encode()).hexdigest()[:12]}")
            native = self.occurrence_ids([d["id"] for d in docs])
            for n, d in zip(native, docs):
                self.by_uuid[str(n)] = [d["id"]]
            items = [DataItem(data=d["text"], data_id=n, literal_text=True) for d, n in zip(docs, native) if d["text"].strip()]
            t = time.perf_counter()
            self.impl.loop.run(self.impl.cognee.remember(items, dataset_name=ds))
            out["ingest_seconds"][user] = round(time.perf_counter() - t, 3)
        return out

    def retrieve(self, query, k, user_id):
        ds = self.datasets.get(user_id or "test-user")
        if ds is None:
            return {"ranked_ids": [], "empty_user": True}
        t = time.perf_counter()
        res = self.impl.loop.run(self.impl.cognee.recall(query, datasets=[ds], top_k=k))
        ranked, unmapped, kinds = self.ranked_doc_ids(res or [], self.by_uuid)
        return {"ranked_ids": ranked[:k], "unmapped_result_count": unmapped, "returned_entry_kinds": kinds,
                "recall_seconds": round(time.perf_counter() - t, 3), "llm_calls": 0}


class LangMemLocal:
    """LangMem memory store manager (LLM extraction + consolidation) over a LangGraph store.

    Each AMB document is shown to LangMem's manager as one user message; the manager decides
    what to insert/update in the user's namespace. Provenance: memories created or updated while
    processing a document are attributed to that document (store diff), the only way to map
    LangMem's own memories back to benchmark ids without changing its behaviour.
    """
    def __init__(self, a):
        from fastembed import TextEmbedding
        from langchain_openai import ChatOpenAI
        from langgraph.store.memory import InMemoryStore
        from langmem import create_memory_store_manager
        self.embedder = TextEmbedding(model_name=a.embed_model, cache_dir=a.embed_cache)
        dims = len(next(iter(self.embedder.embed(["x"]))))
        self.embed = lambda texts: [list(map(float, v)) for v in self.embedder.embed(list(texts))]
        self.InMemoryStore, self.dims = InMemoryStore, dims
        self.llm = ChatOpenAI(model=a.llm_model, base_url=a.llm_base_url, api_key="local-no-key", temperature=0, max_retries=0, timeout=3600)
        self.create = create_memory_store_manager
        self.identity = {"langmem": "0.0.30", "llm": a.llm_model, "embed_model": a.embed_model, "dims": dims}
        self.prepare(None, True)

    def prepare(self, store_dir, reset):
        self.store = self.InMemoryStore(index={"dims": self.dims, "embed": self.embed})
        self.manager = self.create(self.llm, namespace=("memories", "{langgraph_user_id}"), store=self.store)
        self.prov, self.stats = {}, {"llm_failures": [], "documents": 0, "memories_written": 0}

    def _snapshot(self, user):
        return {it.key: json.dumps(it.value, sort_keys=True) for it in self.store.search(("memories", user), limit=10000)}

    def ingest(self, documents):
        for d in documents:
            user = d["user_id"] or "test-user"
            before = self._snapshot(user)
            try:
                self.manager.invoke({"messages": [{"role": "user", "content": d["text"]}]},
                                    config={"configurable": {"langgraph_user_id": user}})
            except Exception as exc:  # recorded; the document simply produced no memory
                self.stats["llm_failures"].append({"doc": d["id"], "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
            after = self._snapshot(user)
            changed = [k for k, v in after.items() if before.get(k) != v]
            for key in changed:
                self.prov.setdefault((user, key), [])
                if d["id"] not in self.prov[(user, key)]:
                    self.prov[(user, key)].append(d["id"])
            self.stats["documents"] += 1
            self.stats["memories_written"] += len(changed)
        return dict(self.stats, memories_total=sum(1 for _ in self.prov))

    def retrieve(self, query, k, user_id):
        user = user_id or "test-user"
        t = time.perf_counter()
        hits = self.store.search(("memories", user), query=query, limit=k)
        ranked, unmapped = [], 0
        for h in hits:
            ids = self.prov.get((user, h.key))
            if not ids:
                unmapped += 1
                continue
            for i in ids:
                if i not in ranked:
                    ranked.append(i)
        return {"ranked_ids": ranked[:k], "memory_hits": len(hits), "unmapped_result_count": unmapped,
                "recall_seconds": round(time.perf_counter() - t, 3), "llm_failures_so_far": len(self.stats["llm_failures"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True, choices=["cognee-local", "langmem-local"])
    ap.add_argument("--url-file", required=True)
    ap.add_argument("--root", default="/tmp/competitor-store")
    ap.add_argument("--llm-model"); ap.add_argument("--llm-base-url")
    ap.add_argument("--embed-model", default="BAAI/bge-small-en-v1.5"); ap.add_argument("--embed-cache")
    a = ap.parse_args()
    system = (CogneeLocal if a.system == "cognee-local" else LangMemLocal)(a)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            try:
                if self.path == "/prepare": out = system.prepare(body.get("store_dir"), body.get("reset", True)) or {}
                elif self.path == "/ingest": out = system.ingest(body["documents"])
                elif self.path == "/retrieve": out = system.retrieve(body["query"], body["k"], body.get("user_id"))
                else: out = {"error": f"unknown path {self.path}"}
            except Exception as exc:
                out = {"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-2000:]}
            data = json.dumps(out).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    srv = HTTPServer(("127.0.0.1", 0), H)
    Path(a.url_file).write_text(json.dumps({"url": f"http://127.0.0.1:{srv.server_address[1]}", "system": a.system,
                                            "identity": getattr(system, "identity", {}), "pid": os.getpid()}))
    srv.serve_forever()


if __name__ == "__main__":
    main()
