"""Gate 2 Phase 5 task-level harness: an answer-producing reader over evidence that reaches it
through the REAL stdio MCP ``memory_find`` tool, against the same reader over an indexed SQLite
FTS5 baseline at equal ``k`` and equal full-text capacity.

This is NOT a benchmark score, NOT blinded, and the readers are NOT agents:

* ``extractive`` is a deterministic plumbing reader (the evidence sentence sharing most content
  terms with the question; abstains when none shares any). It proves the harness, nothing else.
* ``onnx-squad`` is a small open extractive question-answering model (DistilBERT fine-tuned on
  SQuAD 1.1, pinned ONNX export, CPU, no paid inference). It answers with a span of the delivered
  evidence and abstains when no evidence is delivered or its span confidence is below a fixed
  threshold declared before any run (``ABSTAIN_BELOW``) and never tuned on a cohort. SQuAD 1.1
  readers cannot express "no answer" natively, so abstention here is a confidence proxy.

Both arms receive only the text the retrieval arm delivered (MCP: the resolved ``content`` of
each evidence item; FTS5: the full text of each returned record). The reader never sees gold,
keys or the corpus. Gold answers are joined after the reader has answered.

Run from the repository root with the Agent Memory package and ``mcp>=2,<3`` installed:
  python integrations/agent-memory-mcp/task_eval.py --cases CASES.json --out OUT.json \
      [--selectivity] [--answerer extractive|onnx-squad --model-dir DIR] [--max-items 5]
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import statistics
import sys
import tempfile
import time
from typing import Any, Callable, Sequence

from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parent
SERVER = HERE / "server.py"
_spec = importlib.util.spec_from_file_location("am_mcp_quality_probe", HERE / "quality_probe.py")
assert _spec and _spec.loader
quality = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(quality)

ABSTAIN_BELOW = 0.20  # declared before the first run; never adjusted afterwards
MAX_ANSWER_TOKENS = 30
MAX_SEQUENCE_TOKENS = 384
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

# An answerer maps (question, delivered texts) -> (answer or None, confidence or None).
Answerer = Callable[[str, Sequence[str]], tuple[str | None, float | None]]


def extractive_answerer(question: str, texts: Sequence[str]) -> tuple[str | None, float | None]:
    """Deterministic plumbing reader: the sentence with the most shared content terms."""
    terms = set(quality.lexical_terms(question))
    best, best_overlap = None, 0
    for text in texts:
        for sentence in _SENTENCE_END.split(text.strip()):
            overlap = len(terms & set(quality.lexical_terms(sentence)))
            if overlap > best_overlap:
                best, best_overlap = sentence.strip(), overlap
    if best is None:
        return None, None
    return best, best_overlap / max(1, len(terms))


class OnnxSquadAnswerer:
    """DistilBERT-SQuAD (pinned ONNX export) over the delivered evidence, CPU only."""

    def __init__(self, model_dir: Path):
        import numpy as np  # noqa: F401  (import check)
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.model_dir = model_dir
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(MAX_SEQUENCE_TOKENS, strategy="only_second")
        self.session = ort.InferenceSession(str(model_dir / "model_quantized.onnx"),
                                            providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}
        self.digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(model_dir.iterdir()) if p.is_file() and p.name != "SHA256SUMS"}

    def __call__(self, question: str, texts: Sequence[str]) -> tuple[str | None, float | None]:
        import numpy as np
        if not texts:
            return None, None
        context = "\n".join(t.strip() for t in texts if t.strip())
        encoding = self.tokenizer.encode(question, context)
        ids = np.asarray([encoding.ids], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": np.asarray([encoding.attention_mask], dtype=np.int64)}
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.asarray([encoding.type_ids], dtype=np.int64)
        start_logits, end_logits = (np.asarray(o[0], dtype=np.float64) for o in self.session.run(None, feeds))
        context_positions = [i for i, seq in enumerate(encoding.sequence_ids) if seq == 1]
        if not context_positions:
            return None, None
        mask = np.full(len(encoding.ids), -1e9)
        mask[context_positions] = 0.0
        start_p = _softmax(start_logits + mask)
        end_p = _softmax(end_logits + mask)
        best, best_score = None, -1.0
        for s in context_positions:
            for e in range(s, min(s + MAX_ANSWER_TOKENS, len(encoding.ids))):
                if encoding.sequence_ids[e] != 1:
                    break
                score = float(start_p[s] * end_p[e])
                if score > best_score:
                    best, best_score = (s, e), score
        if best is None or best_score < ABSTAIN_BELOW:
            return None, best_score if best is not None else None
        start_char = encoding.offsets[best[0]][0]
        end_char = encoding.offsets[best[1]][1]
        return context[start_char:end_char].strip(), best_score


def _softmax(values):
    import numpy as np
    shifted = values - values.max()
    weights = np.exp(shifted)
    return weights / weights.sum()


def judge(answer: str | None, gold: Sequence[str] | None) -> dict:
    """Join gold after answering. ``gold`` None means the question has no answer in the corpus."""
    if gold is None:
        return {"answerable": False, "abstained": answer is None, "correct": answer is None,
                "false_answer": answer is not None}
    if answer is None:
        return {"answerable": True, "abstained": True, "correct": False, "false_answer": False}
    folded = answer.casefold()
    return {"answerable": True, "abstained": False, "correct": any(g.casefold() in folded for g in gold),
            "false_answer": False}


def aggregate(rows: list[dict], arm: str) -> dict:
    verdicts = [r[arm]["verdict"] for r in rows]
    answerable = [v for v in verdicts if v["answerable"]]
    unanswerable = [v for v in verdicts if not v["answerable"]]
    latencies = [r[arm]["elapsed_ms"] for r in rows]
    return {
        "answerable_total": len(answerable),
        "answerable_correct": sum(v["correct"] for v in answerable),
        "answerable_abstained": sum(v["abstained"] for v in answerable),
        "answerable_wrong": sum((not v["correct"]) and (not v["abstained"]) for v in answerable),
        "unanswerable_total": len(unanswerable),
        "unanswerable_abstained": sum(v["abstained"] for v in unanswerable),
        "unanswerable_false_answer": sum(v["false_answer"] for v in unanswerable),
        "required_evidence_complete": sum(r[arm]["evidence"]["required_complete"] is True for r in rows),
        "unexpected_evidence_items": sum(r[arm]["evidence"]["unexpected_evidence_items"] for r in rows),
        "delivered_chars_total": sum(r[arm]["delivered_chars"] for r in rows),
        "retrieval_p50_ms": statistics.median(latencies) if latencies else None,
    }


def validate_task_cases(data: dict) -> None:
    quality.validate_cases(data)
    for task in data["tasks"]:
        gold = task.get("gold")
        if task["required"]:
            if not (isinstance(gold, list) and gold and all(isinstance(g, str) and g.strip() for g in gold)):
                raise ValueError(f"{task['id']}: an answerable task needs a nonempty list of gold strings")
        elif gold is not None:
            raise ValueError(f"{task['id']}: a no-answer task must carry gold null")


async def run(cases: dict, answerer: Answerer, *, k: int, selectivity: bool, answerer_name: str) -> dict:
    validate_task_cases(cases)
    sizes = sorted((len(r["text"]) for r in cases["records"]), reverse=True)
    if sizes and (sizes[0] > 1200 or sum(sizes[:k]) > 5000 or any(not r["text"].isascii() for r in cases["records"])):
        raise ValueError("corpus no longer fits equal full-text capacity for both arms")
    by_key = {r["key"]: r["text"] for r in cases["records"]}
    fts = quality.build_fts(cases["records"])
    rows = []
    with tempfile.TemporaryDirectory(prefix="am-mcp-task-eval-") as temp:
        env = {
            "AGENT_MEMORY_MCP_ROOT": str(Path(temp) / "store"),
            "AGENT_MEMORY_MCP_TENANT": cases["tenant"],
            "AGENT_MEMORY_MCP_ACTOR": "agent:task-eval",
            "AGENT_MEMORY_MCP_SCOPE": cases["scope"],
            "PATH": os.environ.get("PATH", ""),
        }
        params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)
        async with Client(params) as client:
            for record in cases["records"]:
                saved = await client.call_tool("memory_remember", {"key": record["key"], "text": record["text"]})
                if saved.is_error or not (saved.structured_content or {}).get("committed"):
                    raise RuntimeError(f"failed governed write for {record['key']}: {saved!r}")
            for task in cases["tasks"]:
                question, gold = task["question"], task.get("gold")
                start = time.perf_counter()
                result = await client.call_tool("memory_find", {
                    "question": question, "max_items": k, "experimental_selectivity": selectivity})
                mcp_ms = (time.perf_counter() - start) * 1000
                if result.is_error or not isinstance(result.structured_content, dict):
                    raise RuntimeError(f"failed MCP read for {task['id']}: {result!r}")
                content = result.structured_content
                if content.get("answer_generated") is not False:
                    raise AssertionError("MCP provider must not claim to answer questions")
                evidence = content.get("evidence") or []
                mcp_keys = [e.get("memory_ref") if isinstance(e.get("memory_ref"), str) else "<unattributed>"
                            for e in evidence]
                mcp_texts = [e["content"] for e in evidence if isinstance(e.get("content"), str)]
                mcp_answer, mcp_conf = answerer(question, mcp_texts)
                start = time.perf_counter()
                fts_keys = quality.fts_find(fts, question, k)
                fts_ms = (time.perf_counter() - start) * 1000
                fts_texts = [by_key[key] for key in fts_keys]
                fts_answer, fts_conf = answerer(question, fts_texts)
                rows.append({
                    "id": task["id"], "question": question, "gold": gold, "required": task["required"],
                    "mcp": {
                        "keys": mcp_keys, "answer": mcp_answer, "confidence": mcp_conf,
                        "verdict": judge(mcp_answer, gold), "elapsed_ms": mcp_ms,
                        "delivered_chars": sum(len(t) for t in mcp_texts),
                        "evidence": quality.score(mcp_keys, task["required"], task["forbidden"]),
                        "selection_assessment": content.get("selection_assessment"),
                        "profile": content.get("profile"),
                    },
                    "fts5": {
                        "keys": fts_keys, "answer": fts_answer, "confidence": fts_conf,
                        "verdict": judge(fts_answer, gold), "elapsed_ms": fts_ms,
                        "delivered_chars": sum(len(t) for t in fts_texts),
                        "evidence": quality.score(fts_keys, task["required"], task["forbidden"]),
                    },
                })
    fts.close()
    return {
        "schema": "mcp-gate2-task-eval/0.1.0",
        "qualification": "author-visible task-level diagnostic; NOT blinded, NOT a benchmark, reader is NOT an agent",
        "answerer": answerer_name,
        "abstain_below": ABSTAIN_BELOW if answerer_name == "onnx-squad" else None,
        "reader_files_sha256": getattr(answerer, "digests", None),
        "provider": f"real stdio MCP memory_find experimental_selectivity={selectivity}",
        "selectivity": selectivity,
        "comparator": "indexed SQLite FTS5 unicode61 bm25 OR terms over the same texts; same reader",
        "budget": {"max_items": k},
        "dataset": {"records": len(cases["records"]), "tasks": len(cases["tasks"]),
                    "cases_sha256": hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()},
        "summary": {"mcp": aggregate(rows, "mcp"), "fts5": aggregate(rows, "fts5")},
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--selectivity", action="store_true")
    parser.add_argument("--answerer", choices=("extractive", "onnx-squad"), default="extractive")
    parser.add_argument("--model-dir", type=Path, default=None)
    args = parser.parse_args()
    if type(args.max_items) is not int or not 1 <= args.max_items <= 8:
        raise SystemExit("--max-items must be 1..8 (the MCP provider's bound)")
    if args.answerer == "onnx-squad":
        if args.model_dir is None:
            raise SystemExit("--model-dir is required for onnx-squad")
        answerer: Answerer = OnnxSquadAnswerer(args.model_dir)
    else:
        answerer = extractive_answerer
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    report = asyncio.run(run(cases, answerer, k=args.max_items, selectivity=args.selectivity,
                             answerer_name=args.answerer))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
