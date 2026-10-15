"""Which Hindsight arm surfaces the evidence Agent Memory ranks too low? (#819 diagnostic, #640/#810)

This is a diagnostic only. It produces no score and changes no runtime code. For each selected
LongMemEval session-plane question, it does the following:

1. Ingests the corpus, built by the frozen ``run_longmemeval.corpus``, into a fresh Hindsight
   chunk-only bank. The configuration, ``max_tokens`` and ``budget`` are exactly those of the
   comparator lane.
2. Recalls the question once with ``trace=True``.
3. Records, for every evidence session (the evaluator's own gold), three ranks:
   * Hindsight's final document rank;
   * the best rank of any of its chunks in the **semantic** arm (local e5-small);
   * the best rank of any of its chunks in the **bm25** text-search arm.
4. Reads Agent Memory's document rank from the frozen baseline rows (``--am-rows``) as well.

The committed output (``--summary``) contains only aggregate counts. Per-question detail goes to
``--detail``, which is a local file, because it names evidence sessions. Gold is used only to
attribute what happened. It never reaches any system.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import time
import uuid
from collections import Counter
from pathlib import Path

import run_longmemeval as lme
from agentmem_ref.evaluation.hindsight_bridge import CorpusDocument, HindsightRetrievalBridge, _native_document_id
from longmemeval_hindsight_bridge import (
    EXPECTED_BANK_CONFIG, RECALL_BUDGET, RECALL_MAX_TOKENS, REPEAT_SEP, HindsightLongMemEval,
)


def _model(obj):
    return obj.model_dump(mode="json", exclude_none=True) if hasattr(obj, "model_dump") else obj


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--question-ids", type=Path, required=True)
    parser.add_argument("--am-rows", type=Path, required=True, help="frozen controls report (.json.gz) with agent_memory session rows")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--detail", type=Path, required=True)
    args = parser.parse_args()
    wanted = [line.strip() for line in args.question_ids.read_text().splitlines() if line.strip()]
    rows = {row["question_id"]: row for row in lme._load(args.input) if row["question_id"] in set(wanted)}
    with gzip.open(args.am_rows, "rt", encoding="utf-8") as handle:
        am = {r["question_id"]: r for r in json.load(handle)["planes"]["session"]["backends"]["agent_memory"]["rows"]}
    runner = HindsightLongMemEval(Path(os.environ["HINDSIGHT_SOURCE_ROOT"]), Path(os.environ["AGENT_MEMORY_HINDSIGHT_MODEL_DIR"]))
    detail = []
    try:
        for qid in wanted:
            row = rows[qid]
            items, gold = lme.corpus(row, "session")
            bank_id = f"am-attr-{uuid.uuid4().hex}"
            runner.client.create_bank(bank_id=bank_id, **EXPECTED_BANK_CONFIG)
            bridge = HindsightRetrievalBridge(client=runner.client, bank_id=bank_id)
            bridge.qualify_bank()
            native_to_doc: dict[str, str] = {}
            seen: dict[str, int] = {}
            for item in items:
                k = seen.get(item["id"], 0)
                seen[item["id"]] = k + 1
                if item["text"].strip():
                    key = item["id"] if k == 0 else f"{item['id']}{REPEAT_SEP}{k}"
                    bridge.retain(CorpusDocument(key, item["text"]))
                    native_to_doc[_native_document_id(key)] = item["id"]
            started = time.perf_counter()
            response = _model(runner.client.recall(bank_id=bank_id, query=row["question"], max_tokens=RECALL_MAX_TOKENS,
                                                   budget=RECALL_BUDGET, trace=True))
            seconds = time.perf_counter() - started
            runner.client.delete_bank(bank_id)
            unit_doc = {}
            for result in response.get("results") or []:
                doc = native_to_doc.get(str(result.get("document_id")))
                if doc:
                    unit_doc[str(result.get("id"))] = doc
            final: list[str] = []
            for result in response.get("results") or []:
                doc = unit_doc.get(str(result.get("id")))
                if doc and doc not in final:
                    final.append(doc)
            arm_best: dict[str, dict[str, int]] = {"semantic": {}, "bm25": {}}
            trace = response.get("trace") or {}
            for method in trace.get("retrieval_results") or []:
                name = method.get("method_name")
                if name not in arm_best:
                    continue
                for hit in method.get("results") or []:
                    doc = unit_doc.get(str(hit.get("node_id")))
                    if doc is not None:
                        arm_best[name][doc] = min(arm_best[name].get(doc, 10**9), int(hit["rank"]))
            am_ranked = am[qid]["ranked_top"] if qid in am else []
            for g in gold:
                detail.append({
                    "question_id": qid, "question_type": row.get("question_type"), "evidence_count": len(gold),
                    "hindsight_doc_rank": final.index(g) + 1 if g in final else None,
                    "semantic_best_chunk_rank": arm_best["semantic"].get(g),
                    "bm25_best_chunk_rank": arm_best["bm25"].get(g),
                    "agent_memory_doc_rank": am_ranked.index(g) + 1 if g in am_ranked else None,
                    "recall_seconds": round(seconds, 3),
                })
            print(json.dumps({"question_id": qid, "evidence": len(gold), "mapped_units": len(unit_doc)}), flush=True)
    finally:
        runner.close()
    args.detail.write_text(json.dumps(detail, indent=1) + "\n", encoding="utf-8")

    def bucket(rank):
        return "absent" if rank is None else "1-5" if rank <= 5 else "6-10" if rank <= 10 else "11-30" if rank <= 30 else ">30"

    rescued = [d for d in detail if d["hindsight_doc_rank"] and d["hindsight_doc_rank"] <= 5
               and (d["agent_memory_doc_rank"] is None or d["agent_memory_doc_rank"] > 5)]
    def lead(d):
        s, b = d["semantic_best_chunk_rank"], d["bm25_best_chunk_rank"]
        if s is None and b is None:
            return "neither_arm"
        if b is None or (s is not None and s < b):
            return "semantic_ranks_higher"
        if s is None or b < s:
            return "bm25_ranks_higher"
        return "tie"
    summary = {
        "diagnostic_only": True, "authority_effect": "none", "questions": len(wanted), "evidence_sessions": len(detail),
        "evidence_sessions_hindsight_top5_agent_memory_below5": len(rescued),
        "for_those": {
            "which_arm_ranks_them_higher": dict(Counter(lead(d) for d in rescued)),
            "semantic_arm_rank_bucket": dict(Counter(bucket(d["semantic_best_chunk_rank"]) for d in rescued)),
            "bm25_arm_rank_bucket": dict(Counter(bucket(d["bm25_best_chunk_rank"]) for d in rescued)),
            "agent_memory_rank_bucket": dict(Counter(bucket(d["agent_memory_doc_rank"]) for d in rescued)),
        },
        "all_evidence_sessions": {
            "semantic_arm_rank_bucket": dict(Counter(bucket(d["semantic_best_chunk_rank"]) for d in detail)),
            "bm25_arm_rank_bucket": dict(Counter(bucket(d["bm25_best_chunk_rank"]) for d in detail)),
            "hindsight_doc_rank_bucket": dict(Counter(bucket(d["hindsight_doc_rank"]) for d in detail)),
            "agent_memory_doc_rank_bucket": dict(Counter(bucket(d["agent_memory_doc_rank"]) for d in detail)),
        },
        "note": "Ranks are best chunk rank per arm before RRF; Hindsight final rank is the document rank after RRF. "
                "Per-question detail is withheld (it names evidence sessions).",
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["for_those"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
