"""JSON-lines worker that runs the pinned Hindsight chunk-only setup for the AMB provider (#640, #810).

It is started by ``amb_hindsight_bridge.py`` with the pinned Hindsight interpreter. It reuses the
verified setup of ``longmemeval_hindsight_bridge.HindsightLongMemEval``: the pinned checkout,
model snapshot identity, an in-process ``HindsightServer`` with ``llm_provider="none"``, and
embedded pg0. It also reuses ``HindsightRetrievalBridge``, which qualifies the bank config,
retains synchronously, and maps identity through opaque sha256 document ids.

There is one bank per AMB user. Requests and replies are single JSON lines on stdin/stdout:

* ``{"op": "retain", "user": U, "doc_id": D, "text": T}`` -> ``{"ok": true, "native_id": ...}``
* ``{"op": "recall", "user": U, "query": Q, "k": K}`` -> ``{"ok": true, "ranked": [...], "raw": {...}}``
* ``{"op": "close"}``

Everything is logged to stderr. stdout carries only replies.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from pathlib import Path

from agentmem_ref.evaluation.hindsight_bridge import CorpusDocument, HindsightRetrievalBridge
from longmemeval_hindsight_bridge import EXPECTED_BANK_CONFIG, RECALL_BUDGET, RECALL_MAX_TOKENS, HindsightLongMemEval


def main() -> int:
    out = sys.stdout
    sys.stdout = sys.stderr  # anything the product prints goes to stderr
    runner = HindsightLongMemEval(Path(os.environ["HINDSIGHT_SOURCE_ROOT"]),
                                  Path(os.environ["AGENT_MEMORY_HINDSIGHT_MODEL_DIR"]))
    banks: dict[str, HindsightRetrievalBridge] = {}
    bank_sha: dict[str, str] = {}
    out.write(json.dumps({"ok": True, "ready": True, "cold_start_seconds": runner.cold_start_seconds,
                          "model_identity": runner.model_identity, "source": str(runner.source)}) + "\n")
    out.flush()
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            request = json.loads(line)
            try:
                if request["op"] == "close":
                    break
                user = str(request["user"])
                if request["op"] == "retain":
                    if user not in banks:
                        bank_id = f"am-amb-{uuid.uuid4().hex}"
                        runner.client.create_bank(bank_id=bank_id, **EXPECTED_BANK_CONFIG)
                        banks[user] = HindsightRetrievalBridge(client=runner.client, bank_id=bank_id)
                        bank_sha[user] = banks[user].qualify_bank()
                    native = banks[user].retain(CorpusDocument(str(request["doc_id"]), str(request["text"])))
                    reply = {"ok": True, "native_id": native, "bank_config_sha256": bank_sha[user]}
                elif request["op"] == "recall":
                    if user not in banks:
                        reply = {"ok": True, "ranked": [], "raw": {"note": "no bank for this user"}}
                    else:
                        envelope = banks[user].recall(str(request["query"]), top_k=int(request["k"]),
                                                      max_tokens=RECALL_MAX_TOKENS, budget=RECALL_BUDGET)
                        ranked = list(dict.fromkeys(envelope.mapped_corpus_ids))[: int(request["k"])]
                        reply = {"ok": True, "ranked": ranked,
                                 "raw": {"provider_result_count": len(envelope.raw_native_results),
                                         "repeated_native_document_ids": list(envelope.repeated_native_document_ids),
                                         "requested_top_k": envelope.requested_top_k,
                                         "max_tokens": envelope.provider_max_tokens, "budget": envelope.provider_budget}}
                else:
                    reply = {"ok": False, "error": f"unknown op {request['op']!r}"}
            except Exception as exc:  # reported to the provider, which fails the run
                reply = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2000:]}
            out.write(json.dumps(reply) + "\n")
            out.flush()
    finally:
        for bridge in banks.values():
            try:
                runner.client.delete_bank(bridge.bank_id)
            except Exception:  # noqa: BLE001  (disposable data)
                pass
        runner.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
