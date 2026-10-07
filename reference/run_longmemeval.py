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
import codecs
import copy
import hashlib
import importlib
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
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

from benchmark_ranking_variants import VARIANTS, apply_ranking_variant
from agentmem_ref import AgentMemory
from cross_fact_mechanism_off import limited_refs, mechanism, refusal_counts


UPSTREAM_REPOSITORY = "xiaowu0162/LongMemEval"
UPSTREAM_REVISION = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
UPSTREAM_DATASET = "huggingface.co/datasets/xiaowu0162/longmemeval-cleaned"
PROFILE_ID = "agent-memory-longmemeval-retrieval-currentness-v1"
SCHEMA_VERSION = "2.1.0"  # 2.1.0 (#568): streaming input, measured peak RSS; result semantics unchanged
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


def _tokens(text: str) -> frozenset[str]:
    return frozenset(token.lower() for token in _TOKEN_RE.findall(text) if len(token) > 1)


REQUIRED_FIELDS = frozenset(
    {
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
)
READ_CHUNK_BYTES = 1 << 20
# A single question larger than this (in decoded characters) is refused rather than
# buffered without bound. LongMemEval_S questions are ~0.6 MB and _M ~6 MB.
MAX_QUESTION_CHARS = 1 << 28
_JSON_WHITESPACE = " \t\n\r"


class InputStream:
    """One bounded-memory pass over a LongMemEval JSON array (#568).

    The input is read as raw bytes in chunks. Every byte read is fed to a SHA-256
    digest, so the input identity is the digest of the source bytes themselves,
    never of a parsed or re-serialized form. The bytes are decoded incrementally
    as strict UTF-8, and each top-level array element is decoded by the standard
    library ``json.JSONDecoder``, the same decoder ``json.loads`` uses. Only the
    element being decoded and at most one unread chunk are resident.

    The accepted grammar is exactly a single JSON array with optional JSON
    whitespace around it. A byte-order mark, a non-array top-level value,
    malformed or truncated elements, a missing separator, a trailing comma, and
    any content after the closing bracket all fail closed.
    """

    def __init__(self, path: Path, *, chunk_bytes: int = READ_CHUNK_BYTES) -> None:
        self.path = path
        self.chunk_bytes = chunk_bytes
        self.digest = hashlib.sha256()
        self.bytes_read = 0
        self.complete = False

    def __iter__(self) -> Iterator[Any]:
        decoder = json.JSONDecoder()
        text = codecs.getincrementaldecoder("utf-8")(errors="strict")
        with self.path.open("rb") as handle:
            buffer = ""
            pos = 0
            eof = False

            def fill(size: int) -> bool:
                nonlocal buffer, pos, eof
                if eof:
                    return False
                raw = handle.read(size)
                self.digest.update(raw)
                self.bytes_read += len(raw)
                if not raw:
                    eof = True
                buffer = buffer[pos:] + text.decode(raw, final=eof)
                pos = 0
                return not eof

            def peek() -> str:
                # next non-whitespace character, or "" at end of input
                nonlocal pos
                while True:
                    while pos < len(buffer) and buffer[pos] in _JSON_WHITESPACE:
                        pos += 1
                    if pos < len(buffer):
                        return buffer[pos]
                    if not fill(self.chunk_bytes):
                        return ""

            while not buffer and fill(self.chunk_bytes):
                pass
            if buffer.startswith("\ufeff"):
                raise ValueError("LongMemEval input starts with a UTF-8 byte-order mark; JSON input must not")
            if peek() != "[":
                raise ValueError("LongMemEval input must be a non-empty JSON list")
            pos += 1
            index = 0
            if peek() == "]":
                pos += 1
            else:
                while True:
                    if peek() == "":
                        raise ValueError(f"LongMemEval input truncated before element {index}")
                    want = self.chunk_bytes
                    while True:
                        try:
                            value, end = decoder.raw_decode(buffer, pos)
                            break
                        except json.JSONDecodeError as exc:
                            if len(buffer) - pos > MAX_QUESTION_CHARS:
                                raise ValueError(
                                    f"LongMemEval element {index} exceeds {MAX_QUESTION_CHARS} characters without completing"
                                ) from exc
                            if not fill(want):
                                raise ValueError(f"LongMemEval element {index} is malformed or truncated: {exc}") from exc
                            want = min(want * 2, 1 << 26)
                    pos = end
                    yield value
                    index += 1
                    separator = peek()
                    if separator == ",":
                        pos += 1
                        continue
                    if separator == "]":
                        pos += 1
                        break
                    if separator == "":
                        raise ValueError(f"LongMemEval input truncated after element {index - 1}")
                    raise ValueError(f"LongMemEval input expected ',' or ']' after element {index - 1}, found {separator!r}")
            if peek() != "":
                raise ValueError("LongMemEval input has unexpected content after the closing ']'")
        size = self.path.stat().st_size
        if self.bytes_read != size:
            raise ValueError(f"LongMemEval input changed while reading: read {self.bytes_read} of {size} bytes")
        self.complete = True

    def hexdigest(self) -> str:
        if not self.complete:
            raise ValueError("input digest requested before the whole input was consumed")
        return self.digest.hexdigest()


def _validate_row(index: int, raw: Any, seen: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"row {index} must be an object")
    missing = REQUIRED_FIELDS.difference(raw)
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
    return dict(raw)


def iter_questions(stream: InputStream) -> Iterator[dict[str, Any]]:
    """Validated questions in source order; validation is identical to the former whole-file loader."""

    seen: set[str] = set()
    count = 0
    for index, raw in enumerate(stream):
        yield _validate_row(index, raw, seen)
        count += 1
    if count == 0:
        raise ValueError("LongMemEval input must be a non-empty JSON list")


def _load(path: Path) -> list[dict[str, Any]]:
    """Materialize a (small) input. Benchmark runs stream instead; see ``run``."""

    return list(iter_questions(InputStream(path)))


def _question_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    session_ids = [str(item) for item in row["haystack_session_ids"]]
    return {
        "question_id": row["question_id"],
        "abstention": is_abstention(row),
        "no_user_target": not is_abstention(row) and not has_user_target(row),
        "duplicate_session_ids": len(set(session_ids)) != len(session_ids),
    }


def _scan(path: Path) -> tuple[list[dict[str, Any]], InputStream]:
    """Pass 1: validate every question and hash every byte, retaining only per-question summaries."""

    stream = InputStream(path)
    summaries = [_question_summary(row) for row in iter_questions(stream)]
    return summaries, stream


def _selected_questions(
    path: Path, selected: Sequence[str], expected_sha256: str, passes: list[dict[str, Any]], label: str
) -> Iterator[dict[str, Any]]:
    """A later pass: yield the selected questions in source order, one resident at a time.

    Rows were validated in pass 1; this pass re-hashes the bytes and fails closed if
    they differ from pass 1, so every pass evaluates the same input identity.
    """

    wanted = set(selected)
    stream = InputStream(path)
    yielded: list[str] = []
    for raw in stream:
        question_id = raw.get("question_id") if isinstance(raw, dict) else None
        if question_id in wanted:
            yielded.append(str(question_id))
            yield dict(raw)
    digest = stream.hexdigest()
    if digest != expected_sha256:
        raise ValueError(f"input bytes changed between passes ({label}): {digest} != {expected_sha256}")
    if yielded != [str(item) for item in selected]:
        raise ValueError(f"pass {label} did not reproduce the selected question order")
    passes.append({"pass": label, "bytes_read": stream.bytes_read, "sha256": digest})


def _peak_rss_mb() -> float | None:
    try:
        import resource
    except ImportError:  # pragma: no cover - non-POSIX
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024, 1)


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


TEMPORAL_METADATA_MODES = ("none", "host_declared", "source_observed_at")
RANKING_VARIANTS = tuple(VARIANTS)
# Evaluation-only configuration of the Agent Memory adapter, recorded in every report.
SEMANTIC_RETRIEVAL_MODES = ("off", "required")
RECALL_CONTROL_MODES = ("off", "shadow")
_AGENT_MEMORY_CONFIGURATION: dict[str, str] = {
    "temporal_metadata": "none",
    "ranking_variant": "default",
    "budget": "none",
    "semantic_retrieval": "off",
    "recall_control": "off",
}
# The facade's semantic-route posture, recorded once per run when the route is required (#669).
_SEMANTIC_POSTURE: dict[str, Any] = {}
_DATE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})(?:\s*\([A-Za-z]{3}\))?\s*(\d{2}):(\d{2})")


def _iso_date(value: str) -> str | None:
    """LongMemEval ``YYYY/MM/DD (Day) HH:MM`` to ISO-8601 UTC; ``None`` when unparseable."""

    match = _DATE.match(str(value).strip())
    if not match:
        return None
    year, month, day, hour, minute = match.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:00Z"


def _parse_budget(value: str | int | None) -> str:
    if value is None or str(value) == "none":
        return "none"
    budget = int(value)
    if budget < 1:
        raise ValueError("agent memory budget must be none or an integer >= 1")
    return str(budget)


def configure_agent_memory(
    *,
    temporal_metadata: str = "none",
    ranking_variant: str = "default",
    budget: str | int | None = "none",
    semantic_retrieval: str = "off",
    recall_control: str = "off",
) -> dict[str, str]:
    """Select how the Agent Memory adapter uses the host-visible temporal information.

    ``temporal_metadata = none`` (default, frozen comparability): only question and
    session text reach Agent Memory. ``host_declared``: the adapter declares each
    session's date as ``observed_at`` on write and the question date as the recall
    ``reference_time``, which a host that knows when conversations happened could do.
    ``source_observed_at`` (#594 adapted profile): the session date is declared as
    ``observed_at`` on write and nothing else changes; recall receives no
    ``reference_time``. No validity interval is declared (a session date is not a
    validity claim), and no temporal intent is declared: intent is still interpreted
    from the question text.

    ``ranking_variant`` selects an evaluated alternative of the post-admission policy
    for ablation only; ``default`` is the runtime's shipped policy.

    ``budget`` (contract 1.4.0, #670) is the facade return budget ``k`` the adapter
    declares on every recall, or ``none``: the adapter ranks ``returned``, which equals
    ``admitted`` when unbudgeted, so an unbudgeted run is byte-for-byte the pre-1.4.0 run.

    ``semantic_retrieval`` (#669) is the facade's ``semantic_retrieval`` mode: ``off``
    (the shipped default) or ``required`` (the pinned local representation provider must
    load, or every question fails as a runtime error). ``auto`` is not offered: a lane row
    must not silently fall back to the lexical posture.

    ``recall_control`` (contract 1.5.0, #644 plan-644-lanes-v4 L2) is the facade's
    ``recall_control`` mode: ``off`` (the shipped default; the facade opens exactly as before)
    or ``shadow`` (retrieval unchanged; each question records the controller's telemetry
    block without ``usage.elapsed_ms``). Shadow combined with a required semantic route is
    refused: that pairing is not a frozen lane row.
    """

    if temporal_metadata not in TEMPORAL_METADATA_MODES:
        raise ValueError(f"unknown temporal_metadata {temporal_metadata!r}")
    if semantic_retrieval not in SEMANTIC_RETRIEVAL_MODES:
        raise ValueError(f"semantic_retrieval must be one of {SEMANTIC_RETRIEVAL_MODES}, got {semantic_retrieval!r}")
    if recall_control not in RECALL_CONTROL_MODES:
        raise ValueError(f"recall_control must be one of {RECALL_CONTROL_MODES}, got {recall_control!r}")
    if recall_control != "off" and semantic_retrieval != "off":
        raise ValueError("recall_control shadow is not combined with a required semantic route")
    apply_ranking_variant(ranking_variant)
    _SEMANTIC_POSTURE.clear()
    _AGENT_MEMORY_CONFIGURATION.update(
        temporal_metadata=temporal_metadata,
        ranking_variant=ranking_variant,
        budget=_parse_budget(budget),
        semantic_retrieval=semantic_retrieval,
        recall_control=recall_control,
    )
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
    declare_observed = _AGENT_MEMORY_CONFIGURATION["temporal_metadata"] in {"host_declared", "source_observed_at"}
    observed_mapped = observed_unmapped = 0
    semantic = _AGENT_MEMORY_CONFIGURATION["semantic_retrieval"]
    # An `off` run opens the facade exactly as before #669 (the shipped default).
    open_kwargs = {} if semantic == "off" else {"semantic_retrieval": semantic}
    shadow = _AGENT_MEMORY_CONFIGURATION["recall_control"] == "shadow"
    # An `off` run passes no recall_control keyword: the facade default applies (#644 L6).
    if shadow:
        open_kwargs["recall_control"] = "shadow"
    with tempfile.TemporaryDirectory(prefix="agent-memory-longmemeval-") as temporary:
        with AgentMemory.open(
            temporary,
            tenant=f"tenant:longmemeval:{row_index}",
            actor_id="agent:benchmark",
            scope=f"benchmark:longmemeval:{row_index}",
            purpose="LongMemEval retrieval evaluation",
            **open_kwargs,
        ) as memory:
            uuid_to_item: dict[str, str] = {}
            started = time.perf_counter()
            for item_index, item in enumerate(items):
                declared = {}
                if declare_observed:
                    observed = _iso_date(item.get("date", ""))
                    if observed is not None:
                        declared["observed_at"] = observed
                        observed_mapped += 1
                    else:
                        observed_unmapped += 1
                retained = memory.remember(f"memory:longmemeval:{row_index}:{item_index}", item["text"], **declared)
                if not retained.get("committed") or not retained.get("fact_uuid"):
                    ingestion_failures.append(str(retained.get("refusal") or "not_committed"))
                    continue
                uuid_to_item[str(retained["fact_uuid"])] = item["id"]
            ingest_seconds = time.perf_counter() - started
            started = time.perf_counter()
            reference_time = _iso_date(str((row or {}).get("question_date", ""))) if host_declared else None
            budget = _AGENT_MEMORY_CONFIGURATION["budget"]
            # An unbudgeted run calls the facade exactly as before contract 1.4.0.
            recall_kwargs = {} if budget == "none" else {"budget": int(budget)}
            recalled = memory.recall(question, reference_time=reference_time, **recall_kwargs)
            recall_seconds = time.perf_counter() - started
            # plan-671-evidence-v5 E2/A4: the mechanism-off recompute is one more read of the
            # same store, after the on recall and outside every timed span; it runs only when
            # the on recall limited a candidate (otherwise off equals on by C3 off-equivalence).
            limited = limited_refs(recalled)
            recalled_off = None
            if limited:
                with mechanism("off"):
                    recalled_off = memory.recall(question, reference_time=reference_time, **recall_kwargs)
            if semantic != "off" and not _SEMANTIC_POSTURE:
                _SEMANTIC_POSTURE.update(_recorded_semantic_posture(memory.semantic_retrieval_posture()))
    unmapped_admitted = [value for value in recalled["admitted"] if value not in uuid_to_item]
    refusals: dict[str, int] = {}
    for candidate, decision in recalled["admissions"].items():
        if candidate in recalled["admitted"]:
            continue
        reason = str(decision.get("refusal") or "not_admitted")
        refusals[reason] = refusals.get(reason, 0) + 1
    extra = {"observed_at_mapped_count": observed_mapped, "observed_at_unmapped_count": observed_unmapped} if declare_observed else {}
    if shadow:
        extra["recall_control"] = recorded_recall_control(recalled.get("recall_control"))
    extra["cross_fact"] = {
        "limited_count": len(limited),
        "limited_item_ids": [uuid_to_item.get(value) for value in limited],
        "refusal_counts": refusal_counts(recalled),
        "ranked_top_mechanism_off": None
        if recalled_off is None
        else [uuid_to_item[value] for value in recalled_off["returned"] if value in uuid_to_item][:REPORTED_RANK_DEPTH],
    }
    if semantic != "off":
        # Gold-blind trace: item ids only. Gold is joined after scoring (_semantic_route_diagnostics).
        extra["_semantic_trace"] = {
            "admitted": [uuid_to_item[value] for value in recalled["admitted"] if value in uuid_to_item],
            "semantic_only": sorted(
                uuid_to_item[value]
                for value in recalled["admitted"]
                if value in uuid_to_item and _routes(recalled, value) == {SEMANTIC_ROUTE_ID}
            ),
        }
    return {
        **extra,
        "ranked": [uuid_to_item[value] for value in recalled["returned"] if value in uuid_to_item],
        "return_policy": dict(recalled.get("return_policy") or {}),
        "candidate_count": len(recalled["candidates"]),
        "admitted_count": len(recalled["admitted"]),
        "refusal_reasons": dict(sorted(refusals.items())),
        "unmapped_admitted_count": len(unmapped_admitted),
        "ingestion_failures": ingestion_failures,
        "ingest_seconds": round(ingest_seconds, 6),
        "recall_seconds": round(recall_seconds, 6),
    }


SEMANTIC_ROUTE_ID = "semantic_vector"


def recorded_recall_control(block: Mapping[str, Any] | None) -> dict[str, Any]:
    """The deterministic part of the facade's shadow telemetry: ``usage.elapsed_ms`` removed."""

    if not isinstance(block, Mapping):
        raise RuntimeError("recall_control shadow returned no recall_control block")
    record = json.loads(json.dumps(block))
    record.setdefault("usage", {}).pop("elapsed_ms", None)
    return record


def recall_control_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate shadow telemetry (plan-644-lanes-v4 L2): counts only, never authority."""

    stops: dict[str, int] = {}
    statuses: dict[str, int] = {}
    truncating: dict[str, int] = {}
    for record in records:
        reason = str((record.get("actual_stop") or {}).get("actual_stop_reason"))
        stops[reason] = stops.get(reason, 0) + 1
        status = str((record.get("response") or {}).get("decision_status"))
        statuses[status] = statuses.get(status, 0) + 1
        for route, delta in sorted((record.get("shadow_delta") or {}).items()):
            if delta.get("would_truncate") is True:
                truncating[route] = truncating.get(route, 0) + 1
    return {
        "questions_with_telemetry": len(records),
        "actual_stop_reason_counts": dict(sorted(stops.items())),
        "decision_status_counts": dict(sorted(statuses.items())),
        "would_truncate_question_counts": dict(sorted(truncating.items())),
        "authority_effect": "none",
    }


def cross_fact_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate the per-question ``cross_fact`` records (plan-671-evidence-v5 E2): counts only."""

    refusals: dict[str, int] = {}
    for record in records:
        for reason, count in (record.get("refusal_counts") or {}).items():
            refusals[str(reason)] = refusals.get(str(reason), 0) + int(count)
    return {
        "questions_with_record": len(records),
        "questions_with_limited": sum(1 for record in records if record.get("limited_count", 0) > 0),
        "limited_total": sum(int(record.get("limited_count", 0)) for record in records),
        "refusal_counts": dict(sorted(refusals.items())),
        "authority_effect": "none",
    }


def _routes(recalled: Mapping[str, Any], fact_uuid: str) -> set[str]:
    decision = recalled["admissions"].get(fact_uuid) or {}
    return {str(hit.get("route_id")) for hit in decision.get("route_provenance") or ()}


def _recorded_semantic_posture(posture: Mapping[str, Any]) -> dict[str, Any]:
    """The run-stable part of the facade posture (store row counts vary per question)."""

    representation = posture.get("representation") or {}
    return {
        "status": posture.get("status"),
        "mode": posture.get("mode"),
        "representation_ref": representation.get("representation_ref"),
        "representation_version": representation.get("representation_version"),
        "config_digest": representation.get("config_digest"),
        "dimensions": representation.get("dimensions"),
        "minimum_similarity": posture.get("minimum_similarity"),
        "candidate_limit": posture.get("candidate_limit"),
    }


def _semantic_route_diagnostics(trace: Mapping[str, Any], gold: Sequence[str]) -> dict[str, Any]:
    """Per-question route diagnostics (#669 D2), computed after scoring from a gold-blind trace."""

    admitted = list(trace["admitted"])
    semantic_only = set(trace["semantic_only"])
    gold_set = set(gold)
    first_rank = {}
    for rank, item in enumerate(admitted, start=1):
        first_rank.setdefault(item, rank)
    return {
        "admitted_count": len(admitted),
        "semantic_only_admitted_count": len(semantic_only),
        "gold_reached_only_by_semantic": sorted(gold_set & semantic_only),
        "gold_admitted_rank": {item: first_rank.get(item) for item in sorted(gold_set)},
    }


RETRIEVERS: dict[str, Callable[[str, Sequence[Mapping[str, str]], int], dict[str, Any]]] = {
    "no_memory": _no_memory,
    "lexical_overlap": _lexical,
    "agent_memory": _agent_memory,
}

# System-neutral backend registration (#640 same-harness lanes). An external memory
# system enters this profile through the same retriever contract the built-in backends
# use: it receives the question text and the corpus items ``{id, text, date}`` of one
# question, and returns a ranking of item ids. Its identity is recorded in every report
# under ``execution.external_backends`` so a normalized manifest can bind the row to an
# exact system revision and configuration instead of to this repository's revision.
EXTERNAL_BACKENDS: dict[str, dict[str, Any]] = {}
_BACKEND_NAME_RE = re.compile(r"[a-z][a-z0-9_]{1,62}")
_EXTERNAL_IDENTITY_FIELDS = (
    "system_id",
    "system_kind",
    "system_revision",
    "adapter_id",
    "adapter_revision",
    "configuration",
)
EXTERNAL_SYSTEM_KINDS = ("external_memory", "vector", "other")


def register_external_backend(
    name: str,
    retriever: Callable[..., dict[str, Any]],
    *,
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Register an external memory system as a backend of this profile.

    ``retriever(question, items, row_index, row)`` must return at least ``{"ranked":
    [item_id, ...]}``; any other keys are recorded verbatim on the question row.
    ``identity`` binds the row: ``system_id``, ``system_kind`` (one of
    ``EXTERNAL_SYSTEM_KINDS``), exact ``system_revision``, ``adapter_id``,
    ``adapter_revision`` and the frozen ``configuration`` object. Built-in backend names
    cannot be replaced, and a name cannot be registered twice. Registration carries no
    authority: the external system's output is evidence scored by the frozen evaluator.
    """

    if not isinstance(name, str) or not _BACKEND_NAME_RE.fullmatch(name):
        raise ValueError(f"external backend name must match {_BACKEND_NAME_RE.pattern!r}: {name!r}")
    if name in RETRIEVERS:
        raise ValueError(f"backend {name!r} is already registered")
    if not callable(retriever):
        raise TypeError(f"external backend {name!r} retriever must be callable")
    missing = [field for field in _EXTERNAL_IDENTITY_FIELDS if field not in identity]
    if missing:
        raise ValueError(f"external backend {name!r} identity is missing {missing}")
    if identity["system_kind"] not in EXTERNAL_SYSTEM_KINDS:
        raise ValueError(f"external backend {name!r} system_kind must be one of {EXTERNAL_SYSTEM_KINDS}")
    for field in ("system_id", "system_revision", "adapter_id", "adapter_revision"):
        if not isinstance(identity[field], str) or not identity[field]:
            raise ValueError(f"external backend {name!r} identity.{field} must be a non-empty string")
    if not isinstance(identity["configuration"], Mapping):
        raise ValueError(f"external backend {name!r} identity.configuration must be an object")
    recorded = copy.deepcopy(dict(identity))
    recorded["backend"] = name
    recorded.setdefault("authority_effect", "none")
    RETRIEVERS[name] = retriever
    EXTERNAL_BACKENDS[name] = recorded
    return copy.deepcopy(recorded)


def load_external_backends(specs: Sequence[str]) -> list[str]:
    """Import ``module:entry`` specs and call each entry with ``register_external_backend``.

    The entry returns the backend name(s) it registered. Nothing is executed beyond
    registration; the backend runs only when selected with ``--backend``.
    """

    registered: list[str] = []
    for spec in specs:
        module_name, separator, entry_name = spec.partition(":")
        if not separator or not module_name or not entry_name:
            raise ValueError(f"--external-backend expects MODULE:ENTRY, got {spec!r}")
        module = importlib.import_module(module_name)
        entry = getattr(module, entry_name, None)
        if entry is None or not callable(entry):
            raise ValueError(f"{spec!r} does not name a callable install entry")
        names = entry(register_external_backend)
        if isinstance(names, str):
            names = [names]
        for name in names or ():
            if name not in EXTERNAL_BACKENDS:
                raise ValueError(f"{spec!r} reported backend {name!r} but did not register it")
            registered.append(name)
    return registered


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


def _evaluate_backend(dataset: Iterable[Mapping[str, Any]], granularity: str, backend: str) -> dict[str, Any]:
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
        trace = outcome.pop("_semantic_trace", None)
        if trace is not None:
            outcome["semantic_route"] = _semantic_route_diagnostics(trace, corpus(row, granularity)[1])
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
            "return_budget_applied_total": sum(1 for row in rows if (row.get("return_policy") or {}).get("applied") is True),
        }
        # Every error-free agent_memory question carries a cross_fact record; an error row none.
        result["cross_fact_summary"] = cross_fact_summary([row["cross_fact"] for row in rows if "cross_fact" in row])
        if any("recall_control" in row for row in rows):
            result["recall_control_summary"] = recall_control_summary(
                [row["recall_control"] for row in rows if "recall_control" in row]
            )
        if any("semantic_route" in row for row in rows):
            traced = [row["semantic_route"] for row in rows if "semantic_route" in row]
            result["semantic_route"] = {
                "semantic_only_admitted_count_total": sum(item["semantic_only_admitted_count"] for item in traced),
                "questions_with_gold_reached_only_by_semantic": sum(
                    1 for item in traced if item["gold_reached_only_by_semantic"]
                ),
                "gold_reached_only_by_semantic_total": sum(len(item["gold_reached_only_by_semantic"]) for item in traced),
                "authority_effect": "none",
            }
    elif backend in EXTERNAL_BACKENDS:
        identity = EXTERNAL_BACKENDS[backend]
        result["boundary"] = str(identity.get("boundary") or f"external system {identity['system_id']} through its own public surface")
        result["external_system"] = {
            "system_id": identity["system_id"],
            "system_revision": identity["system_revision"],
            "unmapped_result_count_total": sum(row.get("unmapped_result_count", 0) for row in rows),
        }
    if any("ingest_seconds" in row or "recall_seconds" in row for row in rows):
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
    if max_questions is not None and subset_size is not None:
        raise ValueError("use either max_questions or subset_size, not both")
    if max_questions is not None and max_questions < 1:
        raise ValueError("max_questions must be >= 1")
    selected_backends = [name for name in backends if include_agent_memory or name != "agent_memory"]
    for name in selected_backends:
        if name not in RETRIEVERS:
            raise ValueError(f"unknown backend {name!r}")

    # Pass 1 streams and validates every question and hashes every source byte,
    # keeping only per-question summaries. Selection runs on those summaries with
    # the same rules as before; later passes stream the selected questions again,
    # one resident at a time, and must reproduce the pass-1 digest (#568).
    scan_started = time.perf_counter()
    summaries, scan = _scan(input_path)
    input_sha256 = scan.hexdigest()
    scan_seconds = time.perf_counter() - scan_started
    peak_rss_after_scan = _peak_rss_mb()
    passes: list[dict[str, Any]] = [{"pass": "scan", "bytes_read": scan.bytes_read, "sha256": input_sha256}]
    if max_questions is not None:
        selection = {"method": "source-order prefix", "size": min(max_questions, len(summaries)), "source_question_count": len(summaries)}
        chosen = summaries[:max_questions]
    else:
        chosen, selection = _subset(summaries, size=subset_size, seed=subset_seed)
    selected_ids = [str(row["question_id"]) for row in chosen]
    selection["question_ids_sha256"] = hashlib.sha256("\n".join(selected_ids).encode("utf-8")).hexdigest()

    planes: dict[str, Any] = {}
    for granularity in granularities:
        planes[granularity] = {
            "backends": {
                backend: _evaluate_backend(
                    _selected_questions(input_path, selected_ids, input_sha256, passes, f"{granularity}/{backend}"),
                    granularity,
                    backend,
                )
                for backend in selected_backends
            }
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
            "sha256": input_sha256,
            "sha256_scope": "raw source bytes, every byte read in each streaming pass; all passes must agree",
            "size_bytes": scan.bytes_read,
            "corpus_class": corpus_class,
            "source_question_count": len(summaries),
            "question_count": len(chosen),
            "abstention_question_count": sum(1 for row in chosen if row["abstention"]),
            "no_user_target_question_count": sum(1 for row in chosen if row["no_user_target"]),
            "duplicate_session_id_question_count": sum(1 for row in chosen if row["duplicate_session_ids"]),
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
            "external_backends": {
                name: copy.deepcopy(EXTERNAL_BACKENDS[name]) for name in selected_backends if name in EXTERNAL_BACKENDS
            },
            "granularities": list(granularities),
            "agent_memory_configuration": dict(_AGENT_MEMORY_CONFIGURATION),
            **({"agent_memory_semantic_posture": dict(_SEMANTIC_POSTURE)} if _SEMANTIC_POSTURE else {}),
            "resource_consumption": {
                "method": "getrusage(RUSAGE_SELF).ru_maxrss; the process high-water mark, not attributable to one backend",
                "peak_rss_mb_process": _peak_rss_mb(),
                "peak_rss_mb_after_input_scan": peak_rss_after_scan,
            },
            "input_loading": {
                "method": "streaming: incremental UTF-8 + json.JSONDecoder.raw_decode per top-level element (#568)",
                "read_chunk_bytes": READ_CHUNK_BYTES,
                "resident_questions_max": 1,
                "scan_seconds": round(scan_seconds, 3),
                "passes": passes,
            },
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
    parser.add_argument(
        "--backend",
        action="append",
        help=f"one of {', '.join(BACKENDS)} or a backend registered by --external-backend (repeatable)",
    )
    parser.add_argument(
        "--external-backend",
        action="append",
        default=[],
        metavar="MODULE:ENTRY",
        help="register an external memory system before selection; ENTRY is called with register_external_backend (#640)",
    )
    parser.add_argument("--without-agent-memory", action="store_true")
    parser.add_argument("--omit-rows", action="store_true", help="drop per-question rows from the written report")
    parser.add_argument("--agent-memory-temporal-metadata", choices=TEMPORAL_METADATA_MODES, default="none")
    parser.add_argument("--agent-memory-ranking-variant", choices=RANKING_VARIANTS, default="default")
    parser.add_argument(
        "--agent-memory-budget",
        default="none",
        help="facade return budget k declared on every Agent Memory recall (contract 1.4.0), or none (default)",
    )
    parser.add_argument(
        "--agent-memory-semantic-retrieval",
        choices=SEMANTIC_RETRIEVAL_MODES,
        default="off",
        help="facade semantic_retrieval mode (#669); only with --backend agent_memory alone; auto is refused",
    )
    parser.add_argument(
        "--agent-memory-recall-control",
        choices=RECALL_CONTROL_MODES,
        default="off",
        help="facade recall_control mode (contract 1.5.0, #644); only with --backend agent_memory alone",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.agent_memory_recall_control != "off" and (args.without_agent_memory or args.backend != ["agent_memory"]):
        parser.error("--agent-memory-recall-control shadow is accepted only with --backend agent_memory alone")
    if args.agent_memory_semantic_retrieval != "off" and (args.without_agent_memory or args.backend != ["agent_memory"]):
        parser.error("--agent-memory-semantic-retrieval required is accepted only with --backend agent_memory alone")
    load_external_backends(args.external_backend)
    configure_agent_memory(
        temporal_metadata=args.agent_memory_temporal_metadata,
        ranking_variant=args.agent_memory_ranking_variant,
        budget=args.agent_memory_budget,
        semantic_retrieval=args.agent_memory_semantic_retrieval,
        recall_control=args.agent_memory_recall_control,
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
