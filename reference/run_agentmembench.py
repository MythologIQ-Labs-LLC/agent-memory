#!/usr/bin/env python3
"""Run the AgentMemBench / MemDialogue operational profile against Agent Memory.

The workload phases re-express the deterministic phases of the bound upstream
harness ``agentmembench/evaluation/unified_benchmark.py`` (MIT) with identical
workload strings, parameters, and metric formulas, behind the upstream
five-method adapter protocol (``reset/add/search/delete/close``):

* ``load_records`` stratified, source-unique sampling (requires numpy, as upstream);
* conflict (temporal consistency), isolation, deletion, concurrency, scale.

Upstream's retrieval ``recall_at_k`` is an LLM-judged metric. This profile does
not run a judge; it reports a deterministic, profile-local
``exact_source_recall@k`` instead and records the judged metric as not run.

MemDialogue is a derived database of WildChat-4.8M distributed under ODC-By 1.0.
"MemDialogue is derived from WildChat-4.8M by the Allen Institute for AI."
The dataset is not vendored; a run binds the supplied file's SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from benchmark_ranking_variants import VARIANTS, apply_ranking_variant
from agentmem_ref import AgentMemory


UPSTREAM_REPOSITORY = "mazaiying/AgentMemBench"
UPSTREAM_REVISION = "186c9a54edd47aae42d8b6990520f8e902b60303"
UPSTREAM_HARNESS = "agentmembench/evaluation/unified_benchmark.py"
UPSTREAM_HARNESS_SHA256 = "d0d407129aa506f6eacbf6df19a26c1a9ddd000aa0bfb931cb4e4ae984e594df"
UPSTREAM_DATASET = "data/memdialogue_v2.jsonl"
UPSTREAM_DATASET_SHA256 = "33632710ae6495b95724df455ff6f9947d231ee68ebc0ef10eb8291fd55ca2a6"
DATA_LICENSE = "ODC-By-1.0"
DATA_ATTRIBUTION = "MemDialogue is derived from WildChat-4.8M by the Allen Institute for AI."
PROFILE_ID = "agent-memory-agentmembench-memdialogue-operational-v1"
SCHEMA_VERSION = "1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "agentmembench" / "synthetic.jsonl"
PHASES = ("retrieval", "conflict", "isolation", "deletion", "concurrency", "scale")
BACKENDS = ("no_memory", "lexical_overlap", "agent_memory")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class Adapter(Protocol):
    """Upstream ``unified_benchmark.Adapter`` protocol."""

    name: str

    def reset(self) -> None: ...
    def add(self, text: str, user_id: str) -> list[str]: ...
    def search(self, query: str, user_id: str, limit: int) -> list[str]: ...
    def delete(self, memory_ids: list[str]) -> None: ...
    def close(self) -> None: ...


# Statistics ------------------------------------------------------------------


def _numpy():
    try:
        import numpy
    except ImportError:  # pragma: no cover - exercised only without numpy
        return None
    return numpy


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear interpolation, identical to ``numpy.percentile`` default."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def latency_summary(values: Sequence[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "mean_ms": statistics.fmean(values) if values else None,
        "p50_ms": percentile(values, 50),
        "p95_ms": percentile(values, 95),
        "p99_ms": percentile(values, 99),
    }


def bootstrap_mean_ci(values: Sequence[float], seed: int = 2027, samples: int = 2000) -> list[float] | None:
    """Upstream ``bootstrap_mean_ci``; ``None`` when numpy is unavailable or no values."""
    np = _numpy()
    if not values or np is None:
        return None
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    estimates = np.empty(samples)
    for index in range(samples):
        estimates[index] = rng.choice(array, size=len(array), replace=True).mean()
    return [float(np.percentile(estimates, 2.5)), float(np.percentile(estimates, 97.5))]


# Input -----------------------------------------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(path: Path, limit: int, seed: int) -> list[dict[str, Any]]:
    """Upstream ``load_records``: source-unique, event-type-stratified, seeded."""
    np = _numpy()
    if np is None:
        raise RuntimeError("upstream-compatible record sampling requires numpy")
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_sources: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            source = str(row.get("source_id") or row.get("session_id") or "")
            if source and source in seen_sources:
                continue
            if source:
                seen_sources.add(source)
            event = row.get("memory_event") or row["memory_events"][0]
            by_type[event["event_type"]].append(
                {
                    "text": event["raw_text"],
                    "query": event["query"],
                    "answer": event["ground_truth"],
                    "event_type": event["event_type"],
                    "source_id": source,
                }
            )
    if not by_type:
        raise ValueError(f"No records found in {path}")
    rng = np.random.default_rng(seed)
    for values in by_type.values():
        rng.shuffle(values)
    event_types = sorted(by_type)
    base, remainder = divmod(limit, len(event_types))
    selected: list[dict[str, Any]] = []
    for index, event_type in enumerate(event_types):
        quota = base + int(index < remainder)
        selected.extend(by_type[event_type][:quota])
    if len(selected) < limit:
        already = {item["source_id"] for item in selected}
        remaining = [item for values in by_type.values() for item in values if item["source_id"] not in already]
        rng.shuffle(remaining)
        selected.extend(remaining[: limit - len(selected)])
    if len(selected) < limit:
        raise ValueError(
            f"Requested {limit} source-unique records, but {path} contains {len(selected)} after stratification"
        )
    rng.shuffle(selected)
    return selected


# Backends --------------------------------------------------------------------


def _tokens(text: str) -> frozenset[str]:
    return frozenset(token.lower() for token in _TOKEN_RE.findall(text) if len(token) > 1)


class NoMemoryAdapter:
    name = "no_memory"

    def reset(self) -> None:
        pass

    def add(self, text: str, user_id: str) -> list[str]:
        return []

    def search(self, query: str, user_id: str, limit: int) -> list[str]:
        return []

    def delete(self, memory_ids: list[str]) -> None:
        pass

    def close(self) -> None:
        pass

    def governance(self) -> None:
        return None


class LexicalOverlapAdapter:
    """Deterministic per-user token-overlap store; mirrors upstream per-user filtering."""

    name = "lexical_overlap"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._items: dict[str, tuple[str, str]] = {}
        self._counter = 0

    def add(self, text: str, user_id: str) -> list[str]:
        memory_id = f"lex:{self._counter}"
        self._counter += 1
        self._items[memory_id] = (user_id, text)
        return [memory_id]

    def search(self, query: str, user_id: str, limit: int) -> list[str]:
        terms = _tokens(query)
        scored = []
        for order, (memory_id, (owner, text)) in enumerate(self._items.items()):
            if owner != user_id:
                continue
            item_tokens = _tokens(text)
            overlap = len(terms & item_tokens)
            if overlap:
                union = len(terms | item_tokens)
                scored.append((-overlap, -(overlap / union if union else 0.0), order, text))
        scored.sort()
        return [entry[3] for entry in scored[:limit]]

    def delete(self, memory_ids: list[str]) -> None:
        for memory_id in memory_ids:
            self._items.pop(memory_id, None)

    def close(self) -> None:
        pass

    def governance(self) -> None:
        return None


class AgentMemoryAdapter:
    """Public ``AgentMemory`` facade behind the upstream adapter protocol.

    One governed runtime per ``reset`` under a single tenant. Each upstream
    ``user_id`` becomes its own governed scope / isolation domain, so user
    separation is enforced by canonical recall admission, not by the adapter.
    Deletion uses the facade default (governed tombstone).
    """

    name = "agent_memory"
    tenant = "tenant:agentmembench"

    def __init__(self) -> None:
        self._temporary: tempfile.TemporaryDirectory | None = None
        self._memory: AgentMemory | None = None
        self._stats = self._fresh_stats()
        self.reset()

    @staticmethod
    def _fresh_stats() -> dict[str, Any]:
        return {
            "remember_calls": 0,
            "remember_committed": 0,
            "remember_refusals": {},
            "recall_calls": 0,
            "candidate_count": 0,
            "candidate_scopes": {},
            "admitted_count": 0,
            "refusal_reasons": {},
            "forget_calls": 0,
            "forget_committed": 0,
            "forget_outcomes": {},
        }

    def _scope(self, user_id: str) -> str:
        return f"user:{user_id}"

    def _overrides(self, user_id: str) -> dict[str, Any]:
        scope = self._scope(user_id)
        domains = [self.tenant, scope]
        return {
            "scope": scope,
            "isolation_domain_refs": domains,
            "required_isolation_domain_refs": domains,
            "project_ref": scope,
        }

    def reset(self) -> None:
        self.close()
        self._temporary = tempfile.TemporaryDirectory(prefix="agent-memory-agentmembench-")
        self._memory = AgentMemory.open(
            self._temporary.name,
            tenant=self.tenant,
            actor_id="agent:benchmark",
            scope="benchmark:agentmembench",
            purpose="AgentMemBench operational evaluation",
        )
        self._targets: dict[str, tuple[str, str]] = {}
        self._texts: dict[str, str] = {}
        self._counter = 0

    @staticmethod
    def _tally(bucket: dict[str, int], key: str) -> None:
        bucket[key] = bucket.get(key, 0) + 1

    def add(self, text: str, user_id: str) -> list[str]:
        assert self._memory is not None
        target = f"memory:agentmembench:{self._counter}"
        self._counter += 1
        self._stats["remember_calls"] += 1
        result = self._memory.remember(target, text, overrides=self._overrides(user_id))
        if not result.get("committed") or not result.get("fact_uuid"):
            self._tally(self._stats["remember_refusals"], str(result.get("refusal") or result.get("outcome")))
            return []
        self._stats["remember_committed"] += 1
        self._targets[target] = (user_id, str(result["fact_uuid"]))
        self._texts[str(result["fact_uuid"])] = text
        return [target]

    def search(self, query: str, user_id: str, limit: int) -> list[str]:
        assert self._memory is not None
        scope = self._scope(user_id)
        recalled = self._memory.recall(query, target_domain_refs=[self.tenant, scope], project_ref=scope)
        self._stats["recall_calls"] += 1
        self._stats["candidate_count"] += len(recalled["candidates"])
        # Contract 1.3.0 (#548) declares candidates domain-eligible; older contracts
        # exposed every retrieval match, so candidate counts are compared per scope.
        self._tally(
            self._stats["candidate_scopes"],
            str((recalled.get("candidate_policy") or {}).get("candidate_scope", "retrieval_candidates")),
        )
        self._stats["admitted_count"] += len(recalled["admitted"])
        for candidate, decision in recalled["admissions"].items():
            if candidate not in recalled["admitted"]:
                self._tally(self._stats["refusal_reasons"], str(decision.get("refusal") or "not_admitted"))
        return [self._texts[uuid] for uuid in recalled["admitted"] if uuid in self._texts][:limit]

    def delete(self, memory_ids: list[str]) -> None:
        assert self._memory is not None
        for target in memory_ids:
            user_id, _ = self._targets[target]
            self._stats["forget_calls"] += 1
            result = self._memory.forget(target, overrides=self._overrides(user_id))
            self._stats["forget_committed"] += int(bool(result.get("committed")))
            self._tally(self._stats["forget_outcomes"], str(result.get("outcome") or result.get("refusal")))

    def close(self) -> None:
        if self._memory is not None:
            self._memory.close()
            self._memory = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    def governance(self) -> dict[str, Any]:
        stats = json.loads(json.dumps(self._stats))
        self._stats = self._fresh_stats()
        return stats


ADAPTERS: dict[str, Callable[[], Any]] = {
    "no_memory": NoMemoryAdapter,
    "lexical_overlap": LexicalOverlapAdapter,
    "agent_memory": AgentMemoryAdapter,
}


# Phases ----------------------------------------------------------------------


def run_retrieval(adapter: Adapter, records: list[dict[str, Any]], group_size: int, top_k: int) -> dict[str, Any]:
    """Upstream write/read workload; deterministic exact-source recall instead of the LLM judge."""
    adapter.reset()
    write_latencies: list[float] = []
    write_success = 0
    for index, record in enumerate(records):
        started = time.perf_counter()
        ids = adapter.add(record["text"], f"user_{index // group_size:05d}")
        write_latencies.append((time.perf_counter() - started) * 1000)
        write_success += int(bool(ids))

    read_latencies: list[float] = []
    hits: list[bool] = []
    by_type: dict[str, list[bool]] = defaultdict(list)
    details = []
    for index, record in enumerate(records):
        started = time.perf_counter()
        retrieved = adapter.search(record["query"], f"user_{index // group_size:05d}", top_k)
        read_latencies.append((time.perf_counter() - started) * 1000)
        hit = record["text"] in retrieved
        hits.append(hit)
        by_type[record["event_type"]].append(hit)
        details.append(
            {
                "index": index,
                "event_type": record["event_type"],
                "source_id": record["source_id"],
                "exact_source_hit": hit,
                "retrieved_count": len(retrieved),
            }
        )
    return {
        "records": len(records),
        "group_size": group_size,
        "top_k": top_k,
        "write_success_rate": write_success / len(records),
        "exact_source_recall_at_k": sum(hits) / len(hits),
        "exact_source_recall_at_k_95ci": bootstrap_mean_ci(hits),
        "exact_source_recall_by_event_type": {key: sum(v) / len(v) for key, v in sorted(by_type.items())},
        "upstream_llm_judged_recall_at_k": "not_run",
        "metric_note": "exact_source_hit = the record's own memory text is among the top-k results for its query "
        "within its user group; profile-local and not the upstream LLM-judged recall",
        "write_latency": latency_summary(write_latencies),
        "read_latency": latency_summary(read_latencies),
        "details": details,
    }


CONFLICT_TEMPLATES = (
    ("location", "The user currently lives in {old}.", "The user has moved and now lives in {new}.", "Where does the user currently live?"),
    ("role", "The user works as a {old}.", "The user changed jobs and now works as a {new}.", "What is the user's current job?"),
    ("preference", "The user prefers {old}.", "The user's preference changed; they now prefer {new}.", "What does the user currently prefer?"),
    ("status", "The project status is {old}.", "The project status has changed to {new}.", "What is the project's current status?"),
    ("numeric", "The project budget is {old} dollars.", "The updated project budget is {new} dollars.", "What is the current project budget?"),
)


def run_conflict(adapter: Adapter, pairs: int) -> dict[str, Any]:
    adapter.reset()
    new_hits = stale_hits = dual_hits = 0
    write_latencies: list[float] = []
    read_latencies: list[float] = []
    for index in range(pairs):
        category, old_t, new_t, query = CONFLICT_TEMPLATES[index % len(CONFLICT_TEMPLATES)]
        old = f"OLD_{category}_{index:04d}"
        new = f"NEW_{category}_{index:04d}"
        user_id = f"conflict_{index:05d}"
        for text in (old_t.format(old=old), new_t.format(new=new)):
            started = time.perf_counter()
            adapter.add(text, user_id)
            write_latencies.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        retrieved = "\n".join(adapter.search(query, user_id, 1))
        read_latencies.append((time.perf_counter() - started) * 1000)
        has_new = new.casefold() in retrieved.casefold()
        has_old = old.casefold() in retrieved.casefold()
        new_hits += int(has_new)
        stale_hits += int(has_old and not has_new)
        dual_hits += int(has_old and has_new)
    return {
        "pairs": pairs,
        "new_fact_rate": new_hits / pairs,
        "staleness_rate": stale_hits / pairs,
        "dual_version_rate": dual_hits / pairs,
        "write_latency": latency_summary(write_latencies),
        "read_latency": latency_summary(read_latencies),
    }


def run_isolation(adapter: Adapter, users: int, facts_per_user: int) -> dict[str, Any]:
    adapter.reset()
    canaries: dict[str, str] = {}
    for user_index in range(users):
        user_id = f"isolation_{user_index:05d}"
        canary = f"PRIVATE_CANARY_{user_index:05d}"
        canaries[user_id] = canary
        for fact_index in range(facts_per_user):
            adapter.add(f"The user's private project code is {canary}_{fact_index:02d}.", user_id)
    leaks = 0
    queries = 0
    for user_index in range(users):
        requester = f"isolation_{user_index:05d}"
        target = f"isolation_{(user_index + 1) % users:05d}"
        retrieved = "\n".join(adapter.search("What is the private project code?", requester, 5))
        leaks += int(canaries[target].casefold() in retrieved.casefold())
        queries += 1
    return {
        "users": users,
        "facts_per_user": facts_per_user,
        "cross_user_queries": queries,
        "cross_user_leak_rate": leaks / queries,
    }


def run_deletion(adapter: Adapter, records: int) -> dict[str, Any]:
    adapter.reset()
    visible_before = absent_after = visible_then_absent = 0
    for index in range(records):
        user_id = f"delete_{index:05d}"
        canary = f"ERASURE_CANARY_{index:05d}"
        memory_ids = adapter.add(f"The user's private erasure test code is {canary}.", user_id)
        before = "\n".join(adapter.search("What is the erasure test code?", user_id, 5))
        was_visible = canary.casefold() in before.casefold()
        if was_visible:
            visible_before += 1
        adapter.delete(memory_ids)
        after = "\n".join(adapter.search("What is the erasure test code?", user_id, 5))
        is_absent = canary.casefold() not in after.casefold()
        if is_absent:
            absent_after += 1
        if was_visible and is_absent:
            visible_then_absent += 1
    return {
        "records": records,
        "pre_delete_visibility_rate": visible_before / records,
        "post_delete_absence_rate": absent_after / records,
        "audited_deletion_rate": visible_then_absent / visible_before if visible_before else None,
    }


def run_concurrency(adapter: Adapter, records: int, workers: list[int]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for worker_count in workers:
        adapter.reset()
        latencies: list[float] = []
        operation_successes = 0
        materializations = 0
        errors: list[str] = []

        def write_one(index: int) -> tuple[float, bool, bool, str | None]:
            started = time.perf_counter()
            try:
                ids = adapter.add(
                    f"The user has benchmark preference TOKEN_{worker_count}_{index:06d}.",
                    f"throughput_{index:06d}",
                )
                return (time.perf_counter() - started) * 1000, True, bool(ids), None
            except Exception as error:
                return (time.perf_counter() - started) * 1000, False, False, f"{type(error).__name__}: {error}"

        wall_started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = [pool.submit(write_one, index) for index in range(records)]
            for future in as_completed(futures):
                latency, operation_success, materialized, error = future.result()
                latencies.append(latency)
                operation_successes += int(operation_success)
                materializations += int(materialized)
                if error is not None and len(errors) < 20:
                    errors.append(error)
        wall_seconds = time.perf_counter() - wall_started
        results[str(worker_count)] = {
            "records": records,
            "workers": worker_count,
            "operation_success_rate": operation_successes / records,
            "materialization_rate": materializations / records,
            "error_count": records - operation_successes,
            "error_examples": sorted(set(errors))[:5],
            "throughput_ops_s": records / wall_seconds,
            "latency": latency_summary(latencies),
        }
    return results


def run_scale(adapter: Adapter, scales: list[int], read_queries: int) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for scale in scales:
        adapter.reset()
        write_latencies: list[float] = []
        memory_ids: list[list[str]] = []
        for index in range(scale):
            token = f"SCALE_TOKEN_{scale}_{index:07d}"
            started = time.perf_counter()
            ids = adapter.add(f"The user's scale-test project code is {token}.", f"scale_user_{index:07d}")
            write_latencies.append((time.perf_counter() - started) * 1000)
            memory_ids.append(ids)
        count = min(read_queries, scale)
        # upstream: numpy.linspace(0, scale - 1, num=count, dtype=int)
        query_indices = [int((scale - 1) * step / (count - 1)) if count > 1 else 0 for step in range(count)]
        read_latencies: list[float] = []
        hits: list[bool] = []
        for index in query_indices:
            token = f"SCALE_TOKEN_{scale}_{index:07d}"
            started = time.perf_counter()
            retrieved = "\n".join(
                adapter.search("What is the scale-test project code?", f"scale_user_{index:07d}", 3)
            )
            read_latencies.append((time.perf_counter() - started) * 1000)
            hits.append(token.casefold() in retrieved.casefold())
        results[str(scale)] = {
            "stored_records": scale,
            "write_success_rate": sum(bool(ids) for ids in memory_ids) / scale,
            "recall_at_3": sum(hits) / len(hits),
            "recall_at_3_95ci": bootstrap_mean_ci(hits),
            "write_latency": latency_summary(write_latencies),
            "read_latency": latency_summary(read_latencies),
        }
    return results


def run_warmup(adapter: Adapter, writes: int) -> None:
    if writes <= 0:
        return
    adapter.reset()
    for index in range(writes):
        adapter.add(f"The user prefers warmup token WARMUP_{index:04d}.", "warmup_user")
    adapter.search("What warmup token does the user prefer?", "warmup_user", 3)
    adapter.reset()


# Orchestration ---------------------------------------------------------------


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
    np = _numpy()
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {
        "agent_memory_revision": _git("rev-parse", "HEAD"),
        "agent_memory_worktree_dirty": None if status is None else bool(status),
        "agent_memory_package_version": package_version,
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "numpy": getattr(np, "__version__", None),
    }


def _run_backend(backend: str, phases: Sequence[str], records: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
    adapter = ADAPTERS[backend]()
    output: dict[str, Any] = {"phases": {}, "governance": {}, "phase_errors": {}, "phase_wall_seconds": {}}
    started = time.perf_counter()
    try:
        run_warmup(adapter, params["warmup_writes"])
        adapter.governance()
        runners: dict[str, Callable[[], dict[str, Any]]] = {
            "retrieval": lambda: run_retrieval(adapter, records, params["group_size"], params["top_k"]),
            "conflict": lambda: run_conflict(adapter, params["conflict_pairs"]),
            "isolation": lambda: run_isolation(adapter, params["isolation_users"], params["isolation_facts"]),
            "deletion": lambda: run_deletion(adapter, params["deletion_records"]),
            "concurrency": lambda: run_concurrency(adapter, params["concurrency_records"], params["workers"]),
            "scale": lambda: run_scale(adapter, params["scales"], params["scale_read_queries"]),
        }
        for phase in phases:
            phase_started = time.perf_counter()
            try:
                output["phases"][phase] = runners[phase]()
            except Exception as exc:  # recorded, never hidden
                output["phase_errors"][phase] = f"{type(exc).__name__}: {exc}"
            output["phase_wall_seconds"][phase] = round(time.perf_counter() - phase_started, 3)
            governance = adapter.governance()
            if governance is not None:
                output["governance"][phase] = governance
    finally:
        adapter.close()
    output["wall_seconds"] = round(time.perf_counter() - started, 3)
    output["authority_effect"] = "none"
    if backend == "agent_memory":
        output["boundary"] = (
            "public AgentMemory facade; one tenant, one governed scope per upstream user_id; "
            "candidate generation followed by canonical governed admission; deletion = governed tombstone"
        )
    return output


def run(
    input_path: Path,
    *,
    corpus_class: str,
    backends: Sequence[str] = BACKENDS,
    phases: Sequence[str] = PHASES,
    retrieval_records: int = 1000,
    group_size: int = 10,
    conflict_pairs: int = 250,
    isolation_users: int = 100,
    isolation_facts: int = 5,
    deletion_records: int = 200,
    concurrency_records: int = 200,
    workers: Sequence[int] = (1, 4, 8, 16),
    scales: Sequence[int] = (100, 1000),
    scale_read_queries: int = 200,
    top_k: int = 5,
    seed: int = 2027,
    warmup_writes: int = 5,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    for phase in phases:
        if phase not in PHASES:
            raise ValueError(f"unknown phase {phase!r}")
    for backend in backends:
        if backend not in ADAPTERS:
            raise ValueError(f"unknown backend {backend!r}")
    params = {
        "retrieval_records": retrieval_records,
        "group_size": group_size,
        "conflict_pairs": conflict_pairs,
        "isolation_users": isolation_users,
        "isolation_facts": isolation_facts,
        "deletion_records": deletion_records,
        "concurrency_records": concurrency_records,
        "workers": list(workers),
        "scales": list(scales),
        "scale_read_queries": scale_read_queries,
        "top_k": top_k,
        "seed": seed,
        "warmup_writes": warmup_writes,
    }
    records = load_records(input_path, retrieval_records, seed) if "retrieval" in phases else []
    input_sha = _sha256(input_path)
    results = {backend: _run_backend(backend, phases, records, params) for backend in backends}
    finished_at = datetime.now(timezone.utc)
    return {
        "schema_version": SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "revision": UPSTREAM_REVISION,
            "code_license": "MIT",
            "harness": UPSTREAM_HARNESS,
            "harness_sha256": UPSTREAM_HARNESS_SHA256,
            "dataset": UPSTREAM_DATASET,
            "dataset_sha256": UPSTREAM_DATASET_SHA256,
            "data_license": DATA_LICENSE,
            "data_attribution": DATA_ATTRIBUTION,
        },
        "input": {
            "path_name": input_path.name,
            "sha256": input_sha,
            "size_bytes": input_path.stat().st_size,
            "matches_upstream_release": input_sha == UPSTREAM_DATASET_SHA256,
            "corpus_class": corpus_class,
            "selection": {
                "method": "upstream load_records: source-unique, event-type-stratified, numpy default_rng(seed)",
                "seed": seed,
                "records": len(records),
                "source_ids_sha256": hashlib.sha256(
                    "\n".join(record["source_id"] for record in records).encode("utf-8")
                ).hexdigest(),
            },
        },
        "parameters": params,
        "execution": {
            **_environment(),
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "wall_seconds": round((finished_at - started_at).total_seconds(), 3),
            "backends": list(backends),
            "phases": list(phases),
            "agent_memory_ranking_variant": _RANKING_VARIANT[0],
            "resource_consumption": "not_measured",
        },
        "backends": results,
        "dimensions": {
            "write_efficiency": "phases.retrieval.write_latency / write_success_rate",
            "retrieval_quality": "phases.retrieval.exact_source_recall_at_k (deterministic, profile-local)",
            "temporal_consistency": "phases.conflict",
            "isolation": "phases.isolation.cross_user_leak_rate",
            "deletion": "phases.deletion.audited_deletion_rate",
            "concurrency": "phases.concurrency",
            "scale": "phases.scale",
            "llm_portability": "not_exercised: no LLM backend is part of this profile",
            "governance": "governance (Agent Memory refusal/outcome tallies per phase)",
        },
        "comparability": {
            "status": "bounded-operational-profile" if corpus_class != "synthetic" else "synthetic-smoke-only",
            "upstream_llm_judged_retrieval": "not_run",
            "latency_note": "local in-process latency; not comparable to upstream service-backed latency",
            "reference_systems": "upstream Mem0/Graphiti/LangMem/Letta/Naive RAG results are not reproduced here",
        },
        "claim_boundary": {
            "benchmark_score_is_authority": False,
            "aggregate_memory_health_score": "not_defined",
            "answer_generation_quality_measured": False,
        },
    }


def _int_list(value: str) -> list[int]:
    return [int(part) for part in value.split(",") if part.strip()]


def _peak_rss_mb() -> float | None:
    try:
        import resource
    except ImportError:  # pragma: no cover - non-POSIX
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024, 1)


_RANKING_VARIANT = ["default"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--corpus-class", choices=("synthetic", "external_frozen"), default="synthetic")
    parser.add_argument("--backend", choices=BACKENDS, action="append")
    parser.add_argument("--phases", default=",".join(PHASES))
    parser.add_argument("--retrieval-records", type=int, default=1000)
    parser.add_argument("--group-size", type=int, default=10)
    parser.add_argument("--conflict-pairs", type=int, default=250)
    parser.add_argument("--isolation-users", type=int, default=100)
    parser.add_argument("--isolation-facts", type=int, default=5)
    parser.add_argument("--deletion-records", type=int, default=200)
    parser.add_argument("--concurrency-records", type=int, default=200)
    parser.add_argument("--workers", default="1,4,8,16")
    parser.add_argument("--scales", default="100,1000")
    parser.add_argument("--scale-read-queries", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--warmup-writes", type=int, default=5)
    parser.add_argument("--omit-details", action="store_true")
    parser.add_argument("--agent-memory-ranking-variant", choices=tuple(VARIANTS), default="default")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    apply_ranking_variant(args.agent_memory_ranking_variant)
    _RANKING_VARIANT[0] = args.agent_memory_ranking_variant
    report = run(
        args.input.resolve(),
        corpus_class=args.corpus_class,
        backends=tuple(args.backend or BACKENDS),
        phases=tuple(part.strip() for part in args.phases.split(",") if part.strip()),
        retrieval_records=args.retrieval_records,
        group_size=args.group_size,
        conflict_pairs=args.conflict_pairs,
        isolation_users=args.isolation_users,
        isolation_facts=args.isolation_facts,
        deletion_records=args.deletion_records,
        concurrency_records=args.concurrency_records,
        workers=_int_list(args.workers),
        scales=_int_list(args.scales),
        scale_read_queries=args.scale_read_queries,
        top_k=args.top_k,
        seed=args.seed,
        warmup_writes=args.warmup_writes,
    )
    report["execution"]["resource_consumption"] = {"peak_rss_mb_process": _peak_rss_mb()}
    if args.omit_details:
        for backend in report["backends"].values():
            backend["phases"].get("retrieval", {}).pop("details", None)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
