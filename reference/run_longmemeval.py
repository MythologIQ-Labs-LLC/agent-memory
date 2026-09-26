#!/usr/bin/env python3
"""Run bounded LongMemEval retrieval/currentness evaluation for Agent Memory.

This profile measures retrieval and memory selection only. It does not run the
upstream model-judged answer-quality evaluator and therefore must not be reported
as an official LongMemEval QA score.

Corpus construction, gold labelling, question exclusion, and the recall/NDCG
arithmetic replicate the bound upstream revision exactly:

* ``src/retrieval/run_retrieval.py::process_item_flat_index`` (user turns only;
  ``answer`` session ids relabelled ``noans`` when no user turn has an answer);
* ``src/retrieval/eval_utils.py`` (``evaluate_retrieval``, ``ndcg``, ``dcg``,
  ``evaluate_retrieval_turn2session``);
* ``run_retrieval.py::main`` averaging, which skips ``_abs`` questions and
  questions with no user-side ``has_answer`` target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from benchmark_ranking_variants import VARIANTS, apply_ranking_variant
from agentmem_ref import AgentMemory


UPSTREAM_REPOSITORY = "xiaowu0162/LongMemEval"
UPSTREAM_REVISION = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
UPSTREAM_DATASET = "huggingface.co/datasets/xiaowu0162/longmemeval-cleaned"
PROFILE_ID = "agent-memory-longmemeval-retrieval-currentness-v1"
SCHEMA_VERSION = "2.0.0"
DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "longmemeval" / "synthetic.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
KS = (1, 3, 5, 10, 30, 50)
HEADLINE = {
    "session": ("recall_all@5", "ndcg_any@5", "recall_all@10", "ndcg_any@10"),
    "turn": ("recall_all@5", "ndcg_any@5", "recall_all@10", "ndcg_any@10", "recall_all@50", "ndcg_any@50"),
}
REPORTED_RANK_DEPTH = max(KS)
DEFAULT_SUBSET_SEED = "agent-memory-longmemeval-subset-v1"
BACKENDS = ("no_memory", "lexical_overlap", "agent_memory")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_DATE_RE = re.compile(r"(\d{4})[/-](\d{2})[/-](\d{2})(?:\D+(\d{2}):(\d{2}))?")


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
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise ValueError(f"row {index} must be an object")
        missing = required.difference(raw)
        if missing:
            raise ValueError(f"row {index} missing fields: {sorted(missing)}")
        question_id = str(raw["question_id"])
        if question_id in seen:
            raise ValueError(f"row {index} duplicates question_id {question_id!r}")
        seen.add(question_id)
        session_ids = [str(item) for item in raw["haystack_session_ids"]]
        if not (len(session_ids) == len(raw["haystack_dates"]) == len(raw["haystack_sessions"])):
            raise ValueError(f"row {index} haystack arrays must have equal length")
        seen_sessions: dict[str, str] = {}
        for session_id, session in zip(session_ids, raw["haystack_sessions"]):
            content = json.dumps(session, sort_keys=True)
            if seen_sessions.setdefault(session_id, content) != content:
                raise ValueError(f"row {index} reuses session id {session_id!r} for different content")
        if not set(str(item) for item in raw["answer_session_ids"]).issubset(session_ids):
            raise ValueError(f"row {index} answer_session_ids must be present in haystack_session_ids")
        rows.append(dict(raw))
    return rows


def _subset(
    dataset: Sequence[Mapping[str, Any]], *, size: int | None, seed: str
) -> tuple[list[Mapping[str, Any]], dict[str, Any]]:
    if size is None:
        return list(dataset), {"method": "all", "size": len(dataset)}
    if size < 1:
        raise ValueError("subset size must be >= 1")

    def key(row: Mapping[str, Any]) -> str:
        return hashlib.sha256(f"{seed}\x00{row['question_id']}".encode("utf-8")).hexdigest()

    chosen = set(id(row) for row in sorted(dataset, key=key)[:size])
    selected = [row for row in dataset if id(row) in chosen]
    return selected, {
        "method": "sha256(seed || NUL || question_id) ascending; first N; source order preserved",
        "seed": seed,
        "size": len(selected),
        "source_question_count": len(dataset),
    }


def is_abstention(row: Mapping[str, Any]) -> bool:
    """Upstream rule: ``'_abs' in question_id``."""
    return "_abs" in str(row["question_id"])


def has_user_target(row: Mapping[str, Any]) -> bool:
    """Upstream rule: at least one user turn anywhere carries ``has_answer``."""
    return any(
        bool(turn.get("has_answer"))
        for session in row["haystack_sessions"]
        for turn in session
        if turn.get("role") == "user"
    )


def corpus(row: Mapping[str, Any], granularity: str) -> tuple[list[dict[str, str]], list[str]]:
    """Replicate upstream ``process_item_flat_index`` and ``correct_docs``."""
    items: list[dict[str, str]] = []
    for session_id, date, session in zip(
        row["haystack_session_ids"], row["haystack_dates"], row["haystack_sessions"]
    ):
        session_id = str(session_id)
        user_turns = [(index, turn) for index, turn in enumerate(session) if turn.get("role") == "user"]
        if granularity == "session":
            item_id = session_id
            if "answer" in session_id and not any(bool(turn.get("has_answer")) for _, turn in user_turns):
                item_id = session_id.replace("answer", "noans")
            text = " ".join(str(turn.get("content", "")) for _, turn in user_turns)
            items.append({"id": item_id, "text": text, "date": str(date)})
        elif granularity == "turn":
            for turn_index, turn in user_turns:
                item_id = f"{session_id}_{turn_index + 1}"
                if "answer" in session_id and not bool(turn.get("has_answer")):
                    item_id = item_id.replace("answer", "noans")
                items.append({"id": item_id, "text": str(turn.get("content", "")), "date": str(date)})
        else:
            raise ValueError(f"unknown granularity {granularity!r}")
    gold = sorted(set(item["id"] for item in items if "answer" in item["id"]))
    return items, gold


def _dcg(relevances: Sequence[float], k: int) -> float:
    values = list(relevances)[:k]
    if not values:
        return 0.0
    return values[0] + sum(value / math.log2(position) for position, value in enumerate(values[1:], start=2))


def _ndcg(ranked: Sequence[str], gold: set[str], corpus_ids: Sequence[str], k: int) -> float:
    ideal = _dcg(sorted((1.0 if doc in gold else 0.0 for doc in corpus_ids), reverse=True), k)
    if ideal == 0:
        return 0.0
    return _dcg([1.0 if doc in gold else 0.0 for doc in ranked[:k]], k) / ideal


def evaluate_retrieval(
    ranked: Sequence[str], gold: Sequence[str], corpus_ids: Sequence[str], k: int
) -> tuple[float, float, float]:
    """Upstream ``evaluate_retrieval`` over ranked corpus ids instead of indices."""
    recalled = set(ranked[:k])
    gold_set = set(gold)
    recall_any = float(any(doc in recalled for doc in gold))
    recall_all = float(all(doc in recalled for doc in gold))
    return recall_any, recall_all, _ndcg(ranked, gold_set, corpus_ids, k)


def _strip_turn_id(doc_id: str) -> str:
    return "_".join(doc_id.split("_")[:-1])


def evaluate_retrieval_turn2session(
    ranked: Sequence[str], gold: Sequence[str], corpus_ids: Sequence[str], k: int
) -> tuple[float, float, float]:
    """Upstream ``evaluate_retrieval_turn2session`` over ranked corpus ids."""
    session_gold = sorted(set(_strip_turn_id(doc) for doc in gold))
    session_corpus = [_strip_turn_id(doc) for doc in corpus_ids]
    session_ranked = [_strip_turn_id(doc) for doc in ranked]
    effective_k = k
    while effective_k <= len(session_corpus) and len(set(session_ranked[:effective_k])) < k:
        effective_k += 1
    return evaluate_retrieval(session_ranked, session_gold, session_corpus, effective_k)


def _parse_date(value: str) -> tuple[int, ...] | None:
    match = _DATE_RE.search(value)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def _latest_gold_first(ranked: Sequence[str], gold: Sequence[str], dates: Mapping[str, str]) -> bool | None:
    """Profile-local currentness diagnostic; not an upstream metric.

    True when the most recently dated gold item is retrieved ahead of every
    older gold item. ``None`` when not applicable (fewer than two dated gold
    items with distinct dates).
    """
    dated = [(parsed, doc) for doc in gold if (parsed := _parse_date(dates.get(doc, ""))) is not None]
    if len(dated) < 2 or len({parsed for parsed, _ in dated}) < 2:
        return None
    latest_date = max(parsed for parsed, _ in dated)
    latest = {doc for parsed, doc in dated if parsed == latest_date}
    positions = {doc: index for index, doc in enumerate(ranked)}
    if not any(doc in positions for doc in latest):
        return False
    best_latest = min(positions[doc] for doc in latest if doc in positions)
    older = [positions[doc] for parsed, doc in dated if parsed != latest_date and doc in positions]
    return all(best_latest < position for position in older)


def _score_row(ranked: Sequence[str], gold: Sequence[str], corpus_ids: Sequence[str], granularity: str) -> dict[str, Any]:
    metrics: dict[str, dict[str, float]] = {granularity: {}}
    if granularity == "turn":
        metrics["turn_to_session"] = {}
    for k in KS:
        recall_any, recall_all, ndcg_any = evaluate_retrieval(ranked, gold, corpus_ids, k)
        metrics[granularity].update(
            {f"recall_any@{k}": recall_any, f"recall_all@{k}": recall_all, f"ndcg_any@{k}": ndcg_any}
        )
        if granularity == "turn":
            recall_any, recall_all, ndcg_any = evaluate_retrieval_turn2session(ranked, gold, corpus_ids, k)
            metrics["turn_to_session"].update(
                {f"recall_any@{k}": recall_any, f"recall_all@{k}": recall_all, f"ndcg_any@{k}": ndcg_any}
            )
    return metrics


def _lexical_rank(question: str, items: Sequence[Mapping[str, str]]) -> list[str]:
    query = _tokens(question)
    scored: list[tuple[int, float, str]] = []
    for item in items:
        item_tokens = _tokens(item["text"])
        overlap = len(query.intersection(item_tokens))
        if overlap == 0:
            continue
        union = len(query.union(item_tokens))
        scored.append((overlap, overlap / union if union else 0.0, item["id"]))
    scored.sort(key=lambda entry: (-entry[0], -entry[1], entry[2]))
    return [entry[2] for entry in scored]


TEMPORAL_METADATA_MODES = ("none", "host_declared")
RANKING_VARIANTS = tuple(VARIANTS)
# Evaluation-only configuration of the Agent Memory adapter, recorded in every report.
_AGENT_MEMORY_CONFIGURATION: dict[str, str] = {"temporal_metadata": "none", "ranking_variant": "default"}
_DATE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})(?:\s*\([A-Za-z]{3}\))?\s*(\d{2}):(\d{2})")


def _iso_date(value: str) -> str | None:
    """LongMemEval ``YYYY/MM/DD (Day) HH:MM`` to ISO-8601 UTC; ``None`` when unparseable."""

    match = _DATE.match(str(value).strip())
    if not match:
        return None
    year, month, day, hour, minute = match.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:00Z"


def configure_agent_memory(*, temporal_metadata: str = "none", ranking_variant: str = "default") -> dict[str, str]:
    """Select how the Agent Memory adapter uses the host-visible temporal information.

    ``temporal_metadata = none`` (default, frozen comparability): only question and
    session text reach Agent Memory. ``host_declared``: the adapter declares each
    session's date as ``observed_at`` on write and the question date as the recall
    ``reference_time``, which a host that knows when conversations happened could do.
    No validity interval is declared (a session date is not a validity claim), and no
    temporal intent is declared: intent is still interpreted from the question text.

    ``ranking_variant`` selects an evaluated alternative of the post-admission policy
    for ablation only; ``default`` is the runtime's shipped policy.
    """

    if temporal_metadata not in TEMPORAL_METADATA_MODES:
        raise ValueError(f"unknown temporal_metadata {temporal_metadata!r}")
    apply_ranking_variant(ranking_variant)
    _AGENT_MEMORY_CONFIGURATION.update(temporal_metadata=temporal_metadata, ranking_variant=ranking_variant)
    return dict(_AGENT_MEMORY_CONFIGURATION)


def _no_memory(question: str, items: Sequence[Mapping[str, str]], row_index: int, row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"ranked": []}


def _lexical(question: str, items: Sequence[Mapping[str, str]], row_index: int, row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"ranked": _lexical_rank(question, items)}


def _agent_memory(question: str, items: Sequence[Mapping[str, str]], row_index: int, row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Public facade only: governed retain, then candidate generation + admission.

    Benchmark item ids never enter Agent Memory. Target references are opaque
    positional handles; ids are recovered only from admitted fact UUIDs.
    """
    ingestion_failures: list[str] = []
    host_declared = _AGENT_MEMORY_CONFIGURATION["temporal_metadata"] == "host_declared"
    with tempfile.TemporaryDirectory(prefix="agent-memory-longmemeval-") as temporary:
        with AgentMemory.open(
            temporary,
            tenant=f"tenant:longmemeval:{row_index}",
            actor_id="agent:benchmark",
            scope=f"benchmark:longmemeval:{row_index}",
            purpose="LongMemEval retrieval evaluation",
        ) as memory:
            uuid_to_item: dict[str, str] = {}
            started = time.perf_counter()
            for item_index, item in enumerate(items):
                declared = {}
                if host_declared:
                    observed = _iso_date(item.get("date", ""))
                    if observed is not None:
                        declared["observed_at"] = observed
                retained = memory.remember(f"memory:longmemeval:{row_index}:{item_index}", item["text"], **declared)
                if not retained.get("committed") or not retained.get("fact_uuid"):
                    ingestion_failures.append(str(retained.get("refusal") or "not_committed"))
                    continue
                uuid_to_item[str(retained["fact_uuid"])] = item["id"]
            ingest_seconds = time.perf_counter() - started
            started = time.perf_counter()
            reference_time = _iso_date(str((row or {}).get("question_date", ""))) if host_declared else None
            recalled = memory.recall(question, reference_time=reference_time)
            recall_seconds = time.perf_counter() - started
    unmapped_admitted = [value for value in recalled["admitted"] if value not in uuid_to_item]
    refusals: dict[str, int] = {}
    for candidate, decision in recalled["admissions"].items():
        if candidate in recalled["admitted"]:
            continue
        reason = str(decision.get("refusal") or "not_admitted")
        refusals[reason] = refusals.get(reason, 0) + 1
    return {
        "ranked": [uuid_to_item[value] for value in recalled["admitted"] if value in uuid_to_item],
        "candidate_count": len(recalled["candidates"]),
        "admitted_count": len(recalled["admitted"]),
        "refusal_reasons": dict(sorted(refusals.items())),
        "unmapped_admitted_count": len(unmapped_admitted),
        "ingestion_failures": ingestion_failures,
        "ingest_seconds": round(ingest_seconds, 6),
        "recall_seconds": round(recall_seconds, 6),
    }


RETRIEVERS: dict[str, Callable[[str, Sequence[Mapping[str, str]], int], dict[str, Any]]] = {
    "no_memory": _no_memory,
    "lexical_overlap": _lexical,
    "agent_memory": _agent_memory,
}


def _mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _aggregate(rows: Sequence[Mapping[str, Any]], granularity: str) -> dict[str, Any]:
    scored = [row for row in rows if row["status"] == "scored"]
    abstention = [row for row in rows if row["status"] == "excluded_abstention"]
    no_target = [row for row in rows if row["status"] == "excluded_no_user_target"]
    planes = [granularity] + (["turn_to_session"] if granularity == "turn" else [])
    metrics: dict[str, Any] = {}
    for plane in planes:
        names = sorted(scored[0]["metrics"][plane]) if scored else []
        metrics[plane] = {name: _mean([row["metrics"][plane][name] for row in scored]) for name in names}
    return {
        "evaluated_question_count": len(scored),
        "excluded_abstention_count": len(abstention),
        "excluded_no_user_target_count": len(no_target),
        "headline": {name: metrics.get(granularity, {}).get(name, 0.0) for name in HEADLINE[granularity]},
        "metrics": metrics,
        "abstention_diagnostic": {
            "upstream_metric": False,
            "question_count": len(abstention),
            "returned_any_rate": _mean([1.0 if row["returned_count"] else 0.0 for row in abstention]),
            "mean_returned_count": _mean([float(row["returned_count"]) for row in abstention]),
        },
    }


def _currentness(rows: Sequence[Mapping[str, Any]], granularity: str) -> dict[str, Any]:
    update_rows = [row for row in rows if str(row["question_type"]) == "knowledge-update"]
    applicable = [row for row in update_rows if row["status"] == "scored" and row["latest_gold_first"] is not None]
    return {
        "knowledge_update": _aggregate(update_rows, granularity),
        "latest_gold_ranked_first": {
            "upstream_metric": False,
            "definition": "among scored knowledge-update questions with gold items on >=2 distinct dates, "
            "fraction where the most recently dated gold item is returned ahead of every older gold item",
            "applicable_question_count": len(applicable),
            "rate": _mean([1.0 if row["latest_gold_first"] else 0.0 for row in applicable]),
        },
    }


def score_record(
    row: Mapping[str, Any],
    granularity: str,
    ranked: Sequence[str],
    *,
    runtime_error: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Score one question's returned ranking with the replicated upstream evaluator."""
    items, gold = corpus(row, granularity)
    corpus_ids = [item["id"] for item in items]
    corpus_set = set(corpus_ids)
    dates = {item["id"]: item["date"] for item in items}
    ranked = list(ranked)
    if is_abstention(row):
        status = "excluded_abstention"
    elif not has_user_target(row):
        status = "excluded_no_user_target"
    else:
        status = "scored"
    record: dict[str, Any] = {
        "question_id": row["question_id"],
        "question_type": row["question_type"],
        "status": status,
        "corpus_size": len(items),
        "gold": gold,
        "returned_count": len(ranked),
        "out_of_corpus_returned_count": sum(1 for doc in ranked if doc not in corpus_set),
        "ranked_top": ranked[:REPORTED_RANK_DEPTH],
        "metrics": _score_row(ranked, gold, corpus_ids, granularity),
        "latest_gold_first": _latest_gold_first(ranked, gold, dates),
        "runtime_error": runtime_error,
    }
    record.update(extra or {})
    return record


def summarize(records: Sequence[Mapping[str, Any]], granularity: str) -> dict[str, Any]:
    by_type: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        by_type.setdefault(str(record["question_type"]), []).append(record)
    return {
        "aggregate": _aggregate(records, granularity),
        "by_question_type": {key: _aggregate(value, granularity) for key, value in sorted(by_type.items())},
        "currentness": _currentness(records, granularity),
        "failures": {
            "runtime_failure_count": sum(1 for record in records if record.get("runtime_error")),
            "ingestion_failure_count": sum(len(record.get("ingestion_failures", ())) for record in records),
            "out_of_corpus_returned_count": sum(record["out_of_corpus_returned_count"] for record in records),
        },
    }


def _evaluate_backend(dataset: Sequence[Mapping[str, Any]], granularity: str, backend: str) -> dict[str, Any]:
    retriever = RETRIEVERS[backend]
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for row_index, row in enumerate(dataset):
        items, _ = corpus(row, granularity)
        try:
            outcome = retriever(str(row["question"]), items, row_index, row)
            error = None
        except Exception as exc:  # recorded, never hidden; the question scores as a miss
            outcome = {"ranked": []}
            error = f"{type(exc).__name__}: {exc}"
        ranked = list(outcome.pop("ranked"))
        rows.append(score_record(row, granularity, ranked, runtime_error=error, extra=outcome))
    elapsed = time.perf_counter() - started

    result: dict[str, Any] = {
        **summarize(rows, granularity),
        "timing": {"wall_seconds": round(elapsed, 3)},
        "authority_effect": "none",
        "rows": rows,
    }
    if backend == "agent_memory":
        result["boundary"] = "public AgentMemory facade: governed commit; candidate generation followed by canonical governed admission"
        result["governance"] = {
            "candidate_count_total": sum(row.get("candidate_count", 0) for row in rows),
            "admitted_count_total": sum(row.get("admitted_count", 0) for row in rows),
            "refused_candidate_count_total": sum(sum(row.get("refusal_reasons", {}).values()) for row in rows),
            "unmapped_admitted_count_total": sum(row.get("unmapped_admitted_count", 0) for row in rows),
        }
        result["timing"].update(
            {
                "ingest_seconds_total": round(sum(row.get("ingest_seconds", 0.0) for row in rows), 3),
                "recall_seconds_total": round(sum(row.get("recall_seconds", 0.0) for row in rows), 3),
                "recall_seconds_max": round(max((row.get("recall_seconds", 0.0) for row in rows), default=0.0), 6),
            }
        )
    return result


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _environment() -> dict[str, Any]:
    from importlib import metadata

    try:
        package_version = metadata.version("agent-memory-reference")
    except metadata.PackageNotFoundError:
        package_version = None
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {
        "agent_memory_revision": _git("rev-parse", "HEAD"),
        "agent_memory_worktree_dirty": None if status is None else bool(status),
        "agent_memory_package_version": package_version,
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
    }


def run(
    input_path: Path,
    *,
    corpus_class: str,
    max_questions: int | None = None,
    subset_size: int | None = None,
    subset_seed: str = DEFAULT_SUBSET_SEED,
    granularities: Sequence[str] = ("session", "turn"),
    backends: Sequence[str] = BACKENDS,
    include_agent_memory: bool = True,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    dataset = _load(input_path)
    if max_questions is not None and subset_size is not None:
        raise ValueError("use either max_questions or subset_size, not both")
    if max_questions is not None:
        if max_questions < 1:
            raise ValueError("max_questions must be >= 1")
        selection = {"method": "source-order prefix", "size": min(max_questions, len(dataset)), "source_question_count": len(dataset)}
        dataset = dataset[:max_questions]
    else:
        dataset, selection = _subset(dataset, size=subset_size, seed=subset_seed)
    selection["question_ids_sha256"] = hashlib.sha256(
        "\n".join(str(row["question_id"]) for row in dataset).encode("utf-8")
    ).hexdigest()
    selected_backends = [name for name in backends if include_agent_memory or name != "agent_memory"]
    for name in selected_backends:
        if name not in RETRIEVERS:
            raise ValueError(f"unknown backend {name!r}")

    planes: dict[str, Any] = {}
    for granularity in granularities:
        planes[granularity] = {
            "backends": {backend: _evaluate_backend(dataset, granularity, backend) for backend in selected_backends}
        }

    finished_at = datetime.now(timezone.utc)
    return {
        "schema_version": SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "revision": UPSTREAM_REVISION,
            "license": "MIT",
            "dataset_distribution": UPSTREAM_DATASET,
            "replicated_semantics": [
                "src/retrieval/run_retrieval.py::process_item_flat_index",
                "src/retrieval/run_retrieval.py::main (abstention and no-target exclusion)",
                "src/retrieval/eval_utils.py::evaluate_retrieval",
                "src/retrieval/eval_utils.py::evaluate_retrieval_turn2session",
            ],
        },
        "input": {
            "path_name": input_path.name,
            "sha256": _sha256(input_path),
            "size_bytes": input_path.stat().st_size,
            "corpus_class": corpus_class,
            "question_count": len(dataset),
            "abstention_question_count": sum(1 for row in dataset if is_abstention(row)),
            "no_user_target_question_count": sum(
                1 for row in dataset if not is_abstention(row) and not has_user_target(row)
            ),
            "duplicate_session_id_question_count": sum(
                1 for row in dataset if len(set(map(str, row["haystack_session_ids"]))) != len(row["haystack_session_ids"])
            ),
            "duplicate_session_id_note": "upstream indexes each repeated haystack session as its own corpus item under "
            "the same id; this profile does the same (repeats must carry identical content)",
            "selection": selection,
        },
        "execution": {
            **_environment(),
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "wall_seconds": round((finished_at - started_at).total_seconds(), 3),
            "backends": selected_backends,
            "granularities": list(granularities),
            "agent_memory_configuration": dict(_AGENT_MEMORY_CONFIGURATION),
            "resource_consumption": "not_measured",
        },
        "planes": planes,
        "comparability": {
            "official_longmemeval_qa_score": "not_computed",
            "status": "bounded-retrieval-profile" if corpus_class != "synthetic" else "synthetic-smoke-only",
            "reason": "upstream QA scoring uses a separate model-dependent answer evaluator; this profile measures retrieval/currentness only",
            "retriever_note": "no_memory and lexical_overlap are profile-local baselines; upstream flat-bm25/dense retrievers are not reproduced here",
        },
        "claim_boundary": {
            "abstention_excluded_from_retrieval_recall_denominator": True,
            "answer_generation_quality_measured": False,
            "benchmark_score_is_authority": False,
            "aggregate_memory_health_score": "not_defined",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--corpus-class", choices=("synthetic", "external_frozen"), default="synthetic")
    parser.add_argument("--max-questions", type=int, help="source-order prefix (debugging only)")
    parser.add_argument("--subset-size", type=int, help="deterministic hash-ordered subset")
    parser.add_argument("--subset-seed", default=DEFAULT_SUBSET_SEED)
    parser.add_argument("--granularity", choices=("session", "turn"), action="append")
    parser.add_argument("--backend", choices=BACKENDS, action="append")
    parser.add_argument("--without-agent-memory", action="store_true")
    parser.add_argument("--omit-rows", action="store_true", help="drop per-question rows from the written report")
    parser.add_argument("--agent-memory-temporal-metadata", choices=TEMPORAL_METADATA_MODES, default="none")
    parser.add_argument("--agent-memory-ranking-variant", choices=RANKING_VARIANTS, default="default")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    configure_agent_memory(
        temporal_metadata=args.agent_memory_temporal_metadata,
        ranking_variant=args.agent_memory_ranking_variant,
    )
    report = run(
        args.input.resolve(),
        corpus_class=args.corpus_class,
        max_questions=args.max_questions,
        subset_size=args.subset_size,
        subset_seed=args.subset_seed,
        granularities=tuple(args.granularity or ("session", "turn")),
        backends=tuple(args.backend or BACKENDS),
        include_agent_memory=not args.without_agent_memory,
    )
    if args.omit_rows:
        for plane in report["planes"].values():
            for backend in plane["backends"].values():
                backend.pop("rows", None)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
