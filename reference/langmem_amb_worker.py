"""JSON-lines worker running LangMem's store-backed memory manager for the AMB provider (#813, #810).

This worker runs in LangMem's own pinned interpreter. The product path is LangMem's documented
one: ``create_memory_store_manager(model, namespace=("memories", "{langgraph_user_id}"),
store=...)`` with LangMem defaults (``Memory`` schema, default instructions, inserts on, deletes
off, ``query_limit`` 5). LangMem's LLM reads each message, searches the existing memories, and
creates or updates memories in the store.

* **Underlying storage:** LangGraph ``InMemoryStore`` with a vector index (LangMem's documented
  quick-start store). It is not persistent.
* **LLM:** local Qwen2.5-3B via ``ChatOpenAI``, at temperature 0, behind
  ``llamacpp_hermes_tools_shim.py``.
* **Embeddings:** local ``nomic-embed-text`` via ``OpenAIEmbeddings`` (raw strings, no tiktoken
  chunking), 768 dimensions.

LangMem records no source provenance on a memory. Each document is processed by its own
``invoke`` call, and every memory created or changed during that call is attributed to that
document. A memory that later documents update accumulates their ids in order. This is a stated
limitation of the mapping, not a LangMem feature.

Protocol, one JSON line per request and reply:

* ``{"op": "retain", "user", "doc_id", "text"}``
* ``{"op": "recall", "user", "query", "k"}``
* ``{"op": "close"}``
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback

LLM_MODEL = "qwen2.5-3b-instruct-q4_k_m"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768
_INERT_KEY = "local-no-hosted-inference"


def main() -> int:
    out = sys.stdout
    sys.stdout = sys.stderr
    base_url = os.environ["LANGMEM_LOCAL_BASE_URL"]
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langgraph.store.memory import InMemoryStore
    from langmem import create_memory_store_manager

    model = ChatOpenAI(model=LLM_MODEL, base_url=base_url, api_key=_INERT_KEY, temperature=0, max_retries=0, timeout=3600)
    embeddings = OpenAIEmbeddings(model=EMBED_MODEL, base_url=base_url, api_key=_INERT_KEY,
                                  check_embedding_ctx_length=False, max_retries=0)
    store = InMemoryStore(index={"dims": EMBED_DIM, "embed": embeddings})
    manager = create_memory_store_manager(model, namespace=("memories", "{langgraph_user_id}"), store=store)
    provenance: dict[tuple, list[str]] = {}
    out.write(json.dumps({"ok": True, "ready": True}) + "\n")
    out.flush()

    def snapshot(user: str) -> dict[str, str]:
        return {item.key: json.dumps(item.value, sort_keys=True)
                for item in store.search(("memories", user), limit=100000)}

    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        if request.get("op") == "close":
            break
        try:
            user = str(request["user"])
            config = {"configurable": {"langgraph_user_id": user}}
            if request["op"] == "retain":
                before = snapshot(user)
                started = time.perf_counter()
                manager.invoke({"messages": [{"role": "user", "content": str(request["text"])}]}, config=config)
                after = snapshot(user)
                changed = [key for key, value in after.items() if before.get(key) != value]
                for key in changed:
                    docs = provenance.setdefault((user, key), [])
                    if request["doc_id"] not in docs:
                        docs.append(str(request["doc_id"]))
                reply = {"ok": True, "memories_changed": len(changed), "memories_total": len(after),
                         "seconds": round(time.perf_counter() - started, 3)}
            elif request["op"] == "recall":
                k = int(request["k"])
                items = manager.search(query=str(request["query"]), limit=k, config=config)
                ranked, memories = [], []
                for item in items:
                    docs = provenance.get((user, item.key), [])
                    memories.append({"key": item.key, "score": getattr(item, "score", None),
                                     "content": (item.value or {}).get("content") if isinstance(item.value, dict) else str(item.value),
                                     "docs": docs})
                    ranked.extend((doc, (item.value or {}).get("content", "") if isinstance(item.value, dict) else str(item.value))
                                  for doc in docs)
                reply = {"ok": True, "ranked": ranked[:k], "raw": {"memories": memories, "returned_memories": len(items)}}
            else:
                reply = {"ok": False, "error": f"unknown op {request['op']!r}"}
        except Exception as exc:  # reported; the provider fails the run
            reply = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-3000:]}
        out.write(json.dumps(reply) + "\n")
        out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
