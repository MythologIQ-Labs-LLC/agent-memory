#!/usr/bin/env python3
"""Run bounded LongMemEval retrieval/currentness evaluation for Agent Memory.

This profile measures retrieval and memory selection only. It does not run the
upstream model-judged answer-quality evaluator and therefore must not be reported
as an official LongMemEval QA score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from agentmem_ref import AgentMemory


UPSTREAM_REPOSITORY = "xiaowu0162/LongMemEval"
UPSTREAM_REVISION = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
PROFILE_ID = "agent-memory-longmemeval-retrieval-currentness-v1"
SCHEMA_VERSION = "1.0.0"
DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "longmemeval" / "synthetic.json"
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tokens(text: str) -> frozenset[str]:
    return frozenset(token.lower() for token in _TOKEN_RE.findall(text) if len(token) > 1)


def _load(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError("LongMemEval input must be a non-empty JSON list")
    required = {
        "question_id",
        "question_type",
        "question",
        "answer",
        "question_date",
        "haystack_session_ids",
        "haystack_dates",
        "haystack_sessions",
        "answer_session_ids",
    }
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise ValueError(f"row {index} must be an object")
        missing = required.difference(raw)
        if missing:
            raise ValueError(f"row {index} missing fields: {sorted(missing)}")
        session_ids = list(raw["haystack_session_ids"])
        dates = list(raw["haystack_dates"])
        sessions = list(raw["haystack_sessions"])
        if not (len(session_ids) == len(dates) == len(sessions)):
            raise ValueError(f"row {index} haystack arrays must have equal length")
        if len(set(session_ids)) != len(session_ids):
            raise ValueError(f"row {index} session ids must be unique")
        gold = set(str(item) for item in raw["answer_session_ids"])
        if not gold.issubset(set(str(item) for item in session_ids)):
            raise ValueError(f"row {index} answer_session_ids must be present in haystack_session_ids")
        rows.append(dict(raw))
    return rows


def _session_text(session: Sequence[Mapping[str, Any]], date: str) -> str:
    parts = [f"date {date}"]
    for turn in session:
        parts.append(f"{turn.get('role', 'unknown')}: {turn.get('content', '')}")
    return "\n".join(parts)


def _items(row: Mapping[str, Any], granularity: str) -> tuple[list[dict[str, str]], set[str]]:
    items: list[dict[str, str]] = []
    gold: set[str] = set()
    answer_sessions = set(str(value) for value in row["answer_session_ids"])
    for session_id, date, session in zip(
        row["haystack_session_ids"], row["haystack_dates"], row["haystack_sessions"]
    ):
        session_id = str(session_id)
        if granularity == "session":
            items.append({"id": session_id, "text": _session_text(session, str(date))})
            if session_id in answer_sessions:
                gold.add(session_id)
            continue
        for turn_index, turn in enumerate(session):
            item_id = f"{session_id}#turn:{turn_index}"
            text = f"date {date}\n{turn.get('role', 'unknown')}: {turn.get('content', '')}"
            items.append({"id": item_id, "text": text})
            if bool(turn.get("has_answer", False)):
                gold.add(item_id)
    return items, gold


def _lexical_rank(question: str, items: Sequence[Mapping[str, str]]) -> list[str]:
    query = _tokens(question)
    scored: list[tuple[int, float, str]] = []
    for item in items:
        item_tokens = _tokens(item["text"])
        overlap = len(query.intersection(item_tokens))
        if overlap == 0:
            continue
        union = len(query.union(item_tokens))
        jaccard = 0.0 if union == 0 else overlap / union
        scored.append((overlap, jaccard, item["id"]))
    scored.sort(key=lambda entry: (-entry[0], -entry[1], entry[2]))
    return [entry[2] for entry in scored]


def _ndcg_any(ranked: Sequence[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    for index, item_id in enumerate(ranked[:k], start=1):
        if item_id in gold:
            return round(1.0 / math.log2(index + 1), 6)
    return 0.0


def _recall_all(ranked: Sequence[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    return 1.0 if gold.issubset(set(ranked[:k])) else 0.0


def _metrics(rows: Sequence[Mapping[str, Any]], *, granularity: str) -> dict[str, Any]:
    non_abstention = [row for row in rows if row["gold"]]
    abstention = [row for row in rows if not row["gold"]]
    ks = (5, 10) if granularity == "session" else (5, 10, 50)
    metrics: dict[str, Any] = {
        "evaluated_question_count": len(non_abstention),
        "abstention_question_count": len(abstention),
    }
    for k in ks:
        metrics[f"recall_all@{k}"] = round(
            sum(_recall_all(row["ranked"], set(row["gold"]), k) for row in non_abstention)
            / len(non_abstention),
            6,
        ) if non_abstention else 0.0
        metrics[f"ndcg_any@{k}"] = round(
            sum(_ndcg_any(row["ranked"], set(row["gold"]), k) for row in non_abstention)
            / len(non_abstention),
            6,
        ) if non_abstention else 0.0
    metrics["abstention_retrieved_any_rate"] = round(
        sum(bool(row["ranked"]) for row in abstention) / len(abstention), 6
    ) if abstention else 0.0
    return metrics


def _baseline_rows(dataset: Sequence[Mapping[str, Any]], granularity: str, backend: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in dataset:
        items, gold = _items(row, granularity)
        ranked = [] if backend == "no_memory" else _lexical_rank(str(row["question"]), items)
        results.append(
            {
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "gold": sorted(gold),
                "ranked": ranked,
            }
        )
    return results


def _agent_memory_rows(dataset: Sequence[Mapping[str, Any]], granularity: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row_index, row in enumerate(dataset):
        items, gold = _items(row, granularity)
        with tempfile.TemporaryDirectory(prefix="agent-memory-longmemeval-") as temporary:
            with AgentMemory.open(
                temporary,
                tenant=f"tenant:longmemeval:{row_index}",
                actor_id="agent:benchmark",
                scope=f"benchmark:longmemeval:{row_index}",
                purpose="LongMemEval retrieval evaluation",
            ) as memory:
                uuid_to_item: dict[str, str] = {}
                for item_index, item in enumerate(items):
                    retained = memory.remember(
                        f"memory:longmemeval:{row_index}:{item_index}",
                        item["text"],
                    )
                    if not retained.get("committed") or not retained.get("fact_uuid"):
                        raise RuntimeError(f"failed to retain LongMemEval item {item['id']}")
                    uuid_to_item[str(retained["fact_uuid"])] = item["id"]
                recalled = memory.recall(str(row["question"]))
                candidates = [uuid_to_item[value] for value in recalled["candidates"] if value in uuid_to_item]
                admitted = [uuid_to_item[value] for value in recalled["admitted"] if value in uuid_to_item]
                refused = len(candidates) - len(admitted)
                results.append(
                    {
                        "question_id": row["question_id"],
                        "question_type": row["question_type"],
                        "gold": sorted(gold),
                        "ranked": admitted,
                        "candidate_count": len(candidates),
                        "refused_candidate_count": refused,
                    }
                )
    return results


def _by_type(rows: Sequence[Mapping[str, Any]], granularity: str) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["question_type"]), []).append(row)
    return {key: _metrics(value, granularity=granularity) for key, value in sorted(grouped.items())}


def run(
    input_path: Path,
    *,
    corpus_class: str,
    max_questions: int | None = None,
    include_agent_memory: bool = True,
) -> dict[str, Any]:
    dataset = _load(input_path)
    if max_questions is not None:
        if max_questions < 1:
            raise ValueError("max_questions must be >= 1")
        dataset = dataset[:max_questions]

    planes: dict[str, Any] = {}
    for granularity in ("session", "turn"):
        backends: dict[str, Any] = {}
        for backend in ("no_memory", "lexical_overlap"):
            rows = _baseline_rows(dataset, granularity, backend)
            backends[backend] = {
                "metrics": _metrics(rows, granularity=granularity),
                "by_question_type": _by_type(rows, granularity),
                "rows": rows,
                "authority_effect": "none",
            }
        if include_agent_memory:
            rows = _agent_memory_rows(dataset, granularity)
            backends["agent_memory"] = {
                "metrics": _metrics(rows, granularity=granularity),
                "by_question_type": _by_type(rows, granularity),
                "rows": rows,
                "authority_effect": "none",
                "boundary": "candidate generation followed by canonical governed admission",
            }
        planes[granularity] = {"backends": backends}

    knowledge_update = [row for row in dataset if str(row["question_type"]) == "knowledge-update"]
    return {
        "schema_version": SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "revision": UPSTREAM_REVISION,
            "license": "MIT",
        },
        "input": {
            "sha256": _sha256(input_path),
            "corpus_class": corpus_class,
            "question_count": len(dataset),
        },
        "planes": planes,
        "currentness_slice": {
            "knowledge_update_question_count": len(knowledge_update),
            "interpretation": "knowledge-update is reported as a retrieval/currentness slice; answer correctness is not inferred",
        },
        "comparability": {
            "official_longmemeval_qa_score": "not_computed",
            "status": "bounded-retrieval-profile" if corpus_class != "synthetic" else "synthetic-smoke-only",
            "reason": "upstream QA scoring uses a separate model-dependent answer evaluator; this profile measures retrieval/currentness only",
        },
        "claim_boundary": {
            "abstention_excluded_from_retrieval_recall_denominator": True,
            "answer_generation_quality_measured": False,
            "benchmark_score_is_authority": False,
            "aggregate_memory_health_score": "not_defined",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--corpus-class", choices=("synthetic", "external_frozen"), default="synthetic")
    parser.add_argument("--max-questions", type=int)
    parser.add_argument("--without-agent-memory", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(
        args.input.resolve(),
        corpus_class=args.corpus_class,
        max_questions=args.max_questions,
        include_agent_memory=not args.without_agent_memory,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
