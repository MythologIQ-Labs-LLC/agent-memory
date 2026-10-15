"""Same-host determinism probe for the Hindsight chunk-only comparator (#640, #810). Diagnostic only.

It produces no score and no benchmark row. It answers one question: where does Hindsight's
ranking-order variation come from? For each selected LongMemEval question on the session plane
(corpus built by the frozen ``run_longmemeval.corpus``), it:

1. ingests the corpus into bank A with the frozen bank config, then recalls the question
   ``--repeats`` times (query-time determinism on one index);
2. ingests the same corpus again into a fresh bank B and recalls once (ingest-time determinism);
3. records each recall's mapped corpus order and Hindsight's own ``trace`` (per-arm ranks and
   RRF scores), so that a divergence can be attributed to an arm or to tied fused scores.

The server, model pins, bank configuration, ``top_k``, ``max_tokens`` and ``budget`` are exactly
those of ``longmemeval_hindsight_bridge.py``. The only addition is ``trace=True`` on a side call
used for attribution. The ranking that is compared comes from the untraced bridge call.

Usage (as the unprivileged run user, same environment as the scored run)::

  python hindsight_determinism_probe.py --input longmemeval_s_cleaned.json \
    --question-ids ids.txt --repeats 3 --out probe.json
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path

import run_longmemeval as lme
from agentmem_ref.evaluation.hindsight_bridge import CorpusDocument, HindsightRetrievalBridge
from longmemeval_hindsight_bridge import (
    EXPECTED_BANK_CONFIG, MAX_DEPTH, RECALL_BUDGET, RECALL_MAX_TOKENS, REPEAT_SEP, HindsightLongMemEval,
)


def _ranked(envelope) -> list[str]:
    out: list[str] = []
    for key in envelope.mapped_corpus_ids:
        doc_id = key.split(REPEAT_SEP, 1)[0]
        if doc_id not in out:
            out.append(doc_id)
    return out


def _ingest(runner: HindsightLongMemEval, items) -> tuple[str, HindsightRetrievalBridge]:
    bank_id = f"am-probe-{uuid.uuid4().hex}"
    runner.client.create_bank(bank_id=bank_id, **EXPECTED_BANK_CONFIG)
    bridge = HindsightRetrievalBridge(client=runner.client, bank_id=bank_id)
    bridge.qualify_bank()
    seen: dict[str, int] = {}
    for item in items:
        k = seen.get(item["id"], 0)
        seen[item["id"]] = k + 1
        if item["text"].strip():
            bridge.retain(CorpusDocument(item["id"] if k == 0 else f"{item['id']}{REPEAT_SEP}{k}", item["text"]))
    return bank_id, bridge


def _trace(runner: HindsightLongMemEval, bank_id: str, question: str) -> dict:
    response = runner.client.recall(bank_id=bank_id, query=question, max_tokens=RECALL_MAX_TOKENS,
                                     budget=RECALL_BUDGET, trace=True)
    data = response.model_dump(mode="json", exclude_none=True) if hasattr(response, "model_dump") else dict(response)
    return data.get("trace") or {}


def first_divergence(a: list[str], b: list[str]) -> int | None:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--question-ids", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    wanted = [line.strip() for line in args.question_ids.read_text().splitlines() if line.strip()]
    rows = {row["question_id"]: row for row in lme._load(args.input) if row["question_id"] in set(wanted)}
    runner = HindsightLongMemEval(Path(os.environ["HINDSIGHT_SOURCE_ROOT"]),
                                  Path(os.environ["AGENT_MEMORY_HINDSIGHT_MODEL_DIR"]))
    results = []
    try:
        for qid in wanted:
            row = rows[qid]
            items, _ = lme.corpus(row, "session")
            started = time.perf_counter()
            bank_a, bridge_a = _ingest(runner, items)
            same_bank = [_ranked(bridge_a.recall(row["question"], top_k=MAX_DEPTH, max_tokens=RECALL_MAX_TOKENS,
                                                 budget=RECALL_BUDGET)) for _ in range(args.repeats)]
            trace_a = _trace(runner, bank_a, row["question"])
            bank_b, bridge_b = _ingest(runner, items)
            fresh_bank = _ranked(bridge_b.recall(row["question"], top_k=MAX_DEPTH, max_tokens=RECALL_MAX_TOKENS,
                                                 budget=RECALL_BUDGET))
            trace_b = _trace(runner, bank_b, row["question"])
            runner.client.delete_bank(bank_a)
            runner.client.delete_bank(bank_b)
            results.append({
                "question_id": qid,
                "same_bank_orders_identical": all(order == same_bank[0] for order in same_bank),
                "same_bank_first_divergence": [first_divergence(same_bank[0], o) for o in same_bank[1:]],
                "fresh_bank_order_identical": fresh_bank == same_bank[0],
                "fresh_bank_same_set": set(fresh_bank) == set(same_bank[0]),
                "fresh_bank_first_divergence": first_divergence(same_bank[0], fresh_bank),
                "order_bank_a": same_bank[0], "order_bank_b": fresh_bank,
                "trace_bank_a": trace_a, "trace_bank_b": trace_b,
                "seconds": round(time.perf_counter() - started, 2),
            })
            print(json.dumps({k: results[-1][k] for k in ("question_id", "same_bank_orders_identical",
                                                           "fresh_bank_order_identical", "fresh_bank_first_divergence")}),
                  flush=True)
    finally:
        runner.close()
    summary = {
        "questions": len(results),
        "same_bank_all_identical": sum(r["same_bank_orders_identical"] for r in results),
        "fresh_bank_identical": sum(r["fresh_bank_order_identical"] for r in results),
        "fresh_bank_same_set": sum(r["fresh_bank_same_set"] for r in results),
        "repeats": args.repeats, "diagnostic_only": True, "authority_effect": "none",
    }
    args.out.write_text(json.dumps({"summary": summary, "results": results}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
