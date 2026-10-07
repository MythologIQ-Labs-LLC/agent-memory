#!/usr/bin/env python3
"""Formal AgentMemBench / MESA baseline for Agent Memory (#694).

This runner does not re-express the upstream workloads. It imports the pinned
upstream harness module ``agentmembench/evaluation/unified_benchmark.py`` from a
verified checkout of ``mazaiying/AgentMemBench`` and calls its own phase
functions (``run_warmup``, ``load_records``, ``run_retrieval``, ``run_conflict``,
``run_isolation``, ``run_deletion``, ``run_concurrency``, ``run_scale``) with the
upstream default arguments. Agent Memory participates only through the upstream
five-method adapter protocol (``reset/add/search/delete/close``).

What is bound before execution (``--freeze``):

* the upstream revision, harness SHA-256, dataset SHA-256 and the SHA-256 of the
  published ``results/formal/SHA256SUMS``;
* this runner's own SHA-256 and the frozen protocol manifest;
* the workload arguments, which must equal the upstream defaults;
* the frozen reader/judge identity for the LLM-judged retrieval metric.

Retrieval judging (M2 ``recall_at_k``) is separable. The upstream judge reads
only ``(query, reference answer, retrieved memories)``, so the formal run stores
what Agent Memory retrieved, and ``--judge`` applies the frozen judge later
through the upstream ``judge_retrievals`` function. When no authorized judge is
provisioned the judged metric is recorded as ``blocked``. It is never coerced to
zero: the upstream judge maps transport failures to ``hit: false``, so running it
without an endpoint would publish a false 0.0.

Observation only: the adapter records a per-search trace (candidates, admitted
order, returned prefix, ranking evidence) and, after each phase, reads the
write-time interpretation of the conflict-phase facts. Neither read changes
what was stored, admitted, ranked or returned. Both feed the M4 failure-stage
classifier (``classify_conflict_case``), which is frozen with the protocol.

MemDialogue is derived from WildChat-4.8M by the Allen Institute for AI and is
distributed under ODC-By 1.0. Repository policy for this dataset is
``linked_only``: the committed report stores dataset references and hashes for
retrieved items, never record text. The full retrieved text is written only to
the uncommitted ``--raw-output`` file that the judge step reads.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REFERENCE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = REFERENCE_ROOT.parent
if str(REFERENCE_ROOT) not in sys.path:
    sys.path.insert(0, str(REFERENCE_ROOT))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api import contract  # noqa: E402
from agentmem_ref.runtime import proposition_semantics  # noqa: E402

FREEZE_PATH = REFERENCE_ROOT / "fixtures" / "benchmarks" / "agentmembench" / "mesa-formal-v1-freeze.json"
PROFILE_ID = "agent-memory-agentmembench-mesa-formal-v1"
REPORT_SCHEMA = "agent-memory-mesa-formal-report-1.0.0"
CLASSIFIER_VERSION = "mesa-m4-stage-classifier-1.0.0"
DIAGNOSTICS_VERSION = "mesa-m2-deterministic-diagnostics-1.0.0"
SYSTEM_NAME = "agent_memory"

# Failure stages in pipeline order. The first unmet condition is the primary stage.
STAGES = (
    "write_admission",
    "candidate_generation",
    "admission",
    "write_interpretation",
    "identity_slot_resolution",
    "conflict_supersession_reasoning",
    "temporal_applicability_currentness",
    "ranking_fusion",
)
# Stages in the #694 taxonomy that this workload cannot exercise: the evaluator is
# exact casefolded token containment, and every template is an ordinary sentence.
NOT_EXERCISED_STAGES = {
    "answer_evaluator_layer": "the upstream conflict evaluator is casefolded token containment over top-1",
    "unsupported_semantic_capability": "reported inside write_interpretation: an unknown proposition does "
    "not distinguish an extraction miss from an unsupported construction",
}


# Hashing / verification ----------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_freeze(path: Path = FREEZE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(cwd: Path, *args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=True, timeout=30
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def verify_upstream(freeze: Mapping[str, Any], upstream_root: Path) -> dict[str, Any]:
    """Every upstream digest the freeze binds, recomputed. Any mismatch is fatal."""

    up = freeze["upstream"]
    observed = {
        "revision": _git(upstream_root, "rev-parse", "HEAD"),
        "worktree_dirty": bool(_git(upstream_root, "status", "--porcelain")),
        "harness_sha256": sha256_file(upstream_root / up["harness"]),
        "dataset_sha256": sha256_file(upstream_root / up["dataset"]),
        "formal_results_sha256sums_sha256": sha256_file(upstream_root / up["formal_results_manifest"]),
    }
    expected = {
        "revision": up["revision"],
        "worktree_dirty": False,
        "harness_sha256": up["harness_sha256"],
        "dataset_sha256": up["dataset_sha256"],
        "formal_results_sha256sums_sha256": up["formal_results_sha256sums_sha256"],
    }
    mismatches = {key: {"expected": expected[key], "observed": observed[key]}
                  for key in expected if observed[key] != expected[key]}
    if mismatches:
        raise SystemExit(f"upstream does not match the freeze: {json.dumps(mismatches, indent=2)}")
    return observed


def verify_self(freeze: Mapping[str, Any]) -> str:
    digest = sha256_file(Path(__file__).resolve())
    if digest != freeze["runner"]["sha256"]:
        raise SystemExit(
            f"runner digest {digest} differs from the frozen {freeze['runner']['sha256']}; "
            "a changed runner is a new protocol identity, not the frozen one"
        )
    return digest


def import_upstream(upstream_root: Path):
    """Import the pinned upstream harness module by path, after digest verification."""

    root = str(upstream_root.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module("agentmembench.evaluation.unified_benchmark")


# Adapter -------------------------------------------------------------------------


class AgentMemoryFormalAdapter:
    """Agent Memory behind the upstream ``Adapter`` protocol.

    One governed runtime per ``reset``, opened through the public facade under one
    tenant. Each upstream ``user_id`` is its own governed scope and isolation
    domain, so user separation is enforced by canonical recall admission rather
    than by an adapter-side filter. ``search(query, user_id, limit)`` is
    ``AgentMemory.recall`` with the contract-1.4.0 return budget ``k = limit`` and
    returns the stored text of the ``returned`` prefix. ``delete`` is the facade
    default ``forget`` (governed tombstone). No temporal metadata, reference time,
    temporal intent, logical identity or other caller-declared hint is supplied:
    the runtime receives exactly what the benchmark supplies.
    """

    name = SYSTEM_NAME
    tenant = "tenant:agentmembench"
    trace_user_prefixes = ("conflict_",)

    def __init__(self) -> None:
        self._temporary: tempfile.TemporaryDirectory | None = None
        self._memory: AgentMemory | None = None
        self.phase_label = "init"
        self.traces: dict[str, list[dict[str, Any]]] = {}
        self.write_semantics: dict[str, dict[str, Any]] = {}
        self.tallies: dict[str, Counter] = {}
        self._targets: dict[str, tuple[str, str]] = {}
        self._texts: dict[str, str] = {}
        self._writes_by_user: dict[str, list[dict[str, Any]]] = {}
        self._counter = 0
        self.reset()

    # upstream protocol --------------------------------------------------------

    def reset(self) -> None:
        self._snapshot_write_semantics()
        self.close()
        self._temporary = tempfile.TemporaryDirectory(prefix="agent-memory-mesa-")
        self._memory = AgentMemory.open(
            self._temporary.name,
            tenant=self.tenant,
            actor_id="agent:benchmark",
            scope="benchmark:agentmembench",
            purpose="AgentMemBench MESA formal evaluation",
        )
        self._targets = {}
        self._texts = {}
        self._writes_by_user = {}
        self._counter = 0

    def add(self, text: str, user_id: str) -> list[str]:
        assert self._memory is not None
        target = f"memory:agentmembench:{self._counter}"
        self._counter += 1
        result = self._memory.remember(target, text, overrides=self._overrides(user_id))
        committed = bool(result.get("committed") and result.get("fact_uuid"))
        tally = self._tally()
        tally["remember_calls"] += 1
        if self._traced(user_id):
            self._writes_by_user.setdefault(user_id, []).append({
                "phase": self.phase_label,
                "target": target,
                "text": text,
                "committed": committed,
                "fact_uuid": str(result.get("fact_uuid")) if committed else None,
                "refusal": None if committed else str(result.get("refusal") or result.get("outcome")),
            })
        if not committed:
            tally["remember_refused:" + str(result.get("refusal") or result.get("outcome"))] += 1
            return []
        tally["remember_committed"] += 1
        fact_uuid = str(result["fact_uuid"])
        self._targets[target] = (user_id, fact_uuid)
        self._texts[fact_uuid] = text
        return [target]

    def search(self, query: str, user_id: str, limit: int) -> list[str]:
        assert self._memory is not None
        scope = self._scope(user_id)
        recalled = self._memory.recall(
            query, target_domain_refs=[self.tenant, scope], project_ref=scope, budget=limit
        )
        tally = self._tally()
        tally["recall_calls"] += 1
        tally["candidates"] += len(recalled["candidates"])
        tally["admitted"] += len(recalled["admitted"])
        tally["returned"] += len(recalled["returned"])
        for candidate in recalled["candidates"]:
            if candidate not in recalled["admitted"]:
                decision = recalled["admissions"].get(candidate, {})
                tally["refused:" + str(decision.get("refusal") or decision.get("reason_code") or "not_admitted")] += 1
        if self._traced(user_id):
            self.traces.setdefault(self.phase_label, []).append(self._trace(query, user_id, limit, recalled))
        return [self._texts[uuid] for uuid in recalled["returned"] if uuid in self._texts]

    def delete(self, memory_ids: list[str]) -> None:
        assert self._memory is not None
        tally = self._tally()
        for target in memory_ids:
            user_id, _ = self._targets[target]
            result = self._memory.forget(target, overrides=self._overrides(user_id))
            tally["forget_calls"] += 1
            tally["forget_committed"] += int(bool(result.get("committed")))

    def close(self) -> None:
        if self._memory is not None:
            self._memory.close()
            self._memory = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    # observation (never alters stored, admitted, ranked or returned state) ------

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

    def _traced(self, user_id: str) -> bool:
        return user_id.startswith(self.trace_user_prefixes)

    def _tally(self) -> Counter:
        return self.tallies.setdefault(self.phase_label, Counter())

    @staticmethod
    def _ranking_digest(evidence: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if not evidence:
            return None
        intent = evidence.get("query_temporal_intent") or {}
        return {
            "rank_position": evidence.get("rank_position"),
            "base_rank_position": evidence.get("base_rank_position"),
            "lexical_relevance_score": evidence.get("lexical_relevance_score"),
            "route_scores": evidence.get("route_scores"),
            "temporal_applicability": evidence.get("temporal_applicability"),
            "temporal_applicability_basis": evidence.get("temporal_applicability_basis"),
            "constraint_applied": evidence.get("constraint_applied"),
            "constraint_refusal_reason": evidence.get("constraint_refusal_reason"),
            "ordered_before_next_by": evidence.get("ordered_before_next_by"),
            "policy_id": evidence.get("policy_id"),
            "policy_version": evidence.get("policy_version"),
            "query_intent_mode": intent.get("mode"),
            "query_intent_basis": intent.get("intent_basis"),
            "query_intent_evidence": intent.get("evidence"),
        }

    def _trace(self, query: str, user_id: str, limit: int, recalled: Mapping[str, Any]) -> dict[str, Any]:
        admissions = recalled["admissions"]
        return {
            "user_id": user_id,
            "query": query,
            "limit": limit,
            "candidates": list(recalled["candidates"]),
            "admitted": list(recalled["admitted"]),
            "returned": list(recalled["returned"]),
            "decisions": {
                candidate: {
                    "outcome": decision.get("outcome"),
                    "reason_code": decision.get("reason_code"),
                    "refusal": decision.get("refusal"),
                    "routes": [hit.get("route_id") for hit in decision.get("route_provenance", ())],
                    "ranking": self._ranking_digest(decision.get("ranking_evidence")),
                }
                for candidate, decision in admissions.items()
            },
            "writes": list(self._writes_by_user.get(user_id, ())),
        }

    def _snapshot_write_semantics(self) -> None:
        """Read write-time interpretation of traced facts before the runtime is discarded."""

        if self._memory is None:
            return
        for user_id, writes in self._writes_by_user.items():
            envelope = {
                "contract_version": contract.CONTRACT_VERSION,
                "target_domain_refs": [self.tenant, self._scope(user_id)],
                "principal_ref": "agent:benchmark",
                "project_ref": self._scope(user_id),
                "purpose": "AgentMemBench MESA formal evaluation",
            }
            context = contract.recall_context_from_envelope(contract.validate_recall_context(envelope))
            for write in writes:
                if write["fact_uuid"]:
                    value = self._memory.runtime.adapter.write_semantics(write["fact_uuid"], context)
                    self.write_semantics[f"{write['phase']}:{write['fact_uuid']}"] = value


# M4 failure-stage classification (frozen) -------------------------------------------


def _slot(semantics: Mapping[str, Any] | None) -> Any:
    if not semantics:
        return None
    return proposition_semantics.write_slot(semantics)


def classify_conflict_case(
    index: int,
    old_token: str,
    new_token: str,
    trace: Mapping[str, Any],
    semantics: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any]:
    """Stage-classify one upstream conflict pair (``CLASSIFIER_VERSION``).

    The pipeline conditions a *currentness-correct* answer needs, in order:

    1. both writes committed (``write_admission``);
    2. the new fact is a candidate (``candidate_generation``);
    3. the new fact is admitted (``admission``);
    4. both writes have a known proposition (``write_interpretation``);
    5. both propositions share one slot (``identity_slot_resolution``);
    6. the new write carries a state-change relation to the old fact
       (``conflict_supersession_reasoning``);
    7. temporal applicability or a currentness constraint separates the two facts
       (``temporal_applicability_currentness``);
    8. the new fact is ranked first (``ranking_fusion``).

    ``unmet_stages`` lists every unmet condition. For a miss, ``primary_stage`` is the
    first unmet one. A hit whose ranking did not rest on condition 7 is reported
    as ``win_basis = lexical_ordering``, because it is correct for a reason that is
    not currentness.
    """

    writes = trace.get("writes", [])
    by_text = {}
    for write in writes:
        if old_token.casefold() in write["text"].casefold():
            by_text["old"] = write
        elif new_token.casefold() in write["text"].casefold():
            by_text["new"] = write
    old_w, new_w = by_text.get("old"), by_text.get("new")
    old_uuid = old_w["fact_uuid"] if old_w else None
    new_uuid = new_w["fact_uuid"] if new_w else None
    returned = trace.get("returned", [])
    top = returned[0] if returned else None
    if top is not None and top == new_uuid:
        outcome = "new_fact"
    elif top is not None and top == old_uuid:
        outcome = "stale"
    else:
        outcome = "neither"
    old_sem = semantics.get(old_uuid) if old_uuid else None
    new_sem = semantics.get(new_uuid) if new_uuid else None
    decisions = trace.get("decisions", {})
    old_rank = (decisions.get(old_uuid) or {}).get("ranking") or {}
    new_rank = (decisions.get(new_uuid) or {}).get("ranking") or {}
    relation = None
    for item in (new_sem or {}).get("relations", ()):
        if item.get("other_fact_uuid") == old_uuid:
            relation = item
            break
    old_known = ((old_sem or {}).get("proposition") or {}).get("status") == "known"
    new_known = ((new_sem or {}).get("proposition") or {}).get("status") == "known"
    same_slot = old_known and new_known and _slot(old_sem) is not None and _slot(old_sem) == _slot(new_sem)
    currentness_separates = bool(
        new_rank.get("constraint_applied") or old_rank.get("constraint_applied")
        or (new_rank.get("temporal_applicability") not in (None, "unknown_temporal_basis")
            and new_rank.get("temporal_applicability") != old_rank.get("temporal_applicability"))
    )
    conditions = {
        "write_admission": bool(old_w and new_w and old_w["committed"] and new_w["committed"]),
        "candidate_generation": new_uuid is not None and new_uuid in trace.get("candidates", ()),
        "admission": new_uuid is not None and new_uuid in trace.get("admitted", ()),
        "write_interpretation": old_known and new_known,
        "identity_slot_resolution": same_slot,
        "conflict_supersession_reasoning": bool(relation and relation.get("classification") == "state_change_candidate"),
        "temporal_applicability_currentness": currentness_separates,
        "ranking_fusion": outcome == "new_fact",
    }
    unmet = [stage for stage in STAGES if not conditions[stage]]
    record: dict[str, Any] = {
        "index": index,
        "outcome": outcome,
        "old_fact_uuid": old_uuid,
        "new_fact_uuid": new_uuid,
        "conditions": conditions,
        "unmet_stages": unmet,
        "primary_stage": None if outcome == "new_fact" else (unmet[0] if unmet else "unclassified"),
        "win_basis": None,
        "relation": None if relation is None else {
            "classification": relation.get("classification"),
            "basis": relation.get("basis"),
            "has_proposal": "proposal" in relation,
        },
        "same_slot_unretained_count": (new_sem or {}).get("unresolved_cardinality_unknown_count", 0),
        "old_proposition": (old_sem or {}).get("proposition"),
        "new_proposition": (new_sem or {}).get("proposition"),
        "new_proposal_ineligible_reasons": (new_sem or {}).get("proposal_ineligible_reasons"),
        "new_markers": (new_sem or {}).get("markers"),
        "old_ranking": old_rank or None,
        "new_ranking": new_rank or None,
        "top_ordered_before_next_by": ((decisions.get(top) or {}).get("ranking") or {}).get("ordered_before_next_by")
        if top else None,
    }
    if outcome == "new_fact":
        record["win_basis"] = "currentness_mechanism" if currentness_separates else "lexical_ordering"
    return record


def classify_conflict_phase(upstream, pairs: int, traces: Sequence[Mapping[str, Any]],
                            semantics: Mapping[str, Mapping[str, Any] | None]) -> dict[str, Any]:
    by_user = {trace["user_id"]: trace for trace in traces}
    cases = []
    for index in range(pairs):
        category, *_ = upstream.CONFLICT_TEMPLATES[index % len(upstream.CONFLICT_TEMPLATES)]
        trace = by_user.get(f"conflict_{index:05d}", {})
        case = classify_conflict_case(
            index, f"OLD_{category}_{index:04d}", f"NEW_{category}_{index:04d}", trace, semantics
        )
        case["category"] = category
        cases.append(case)
    primary = Counter(case["primary_stage"] for case in cases if case["primary_stage"])
    unmet = Counter(stage for case in cases for stage in case["unmet_stages"])
    by_category: dict[str, Counter] = {}
    for case in cases:
        by_category.setdefault(case["category"], Counter())[case["outcome"]] += 1
    return {
        "classifier_version": CLASSIFIER_VERSION,
        "stages": list(STAGES),
        "not_exercised_stages": NOT_EXERCISED_STAGES,
        "outcomes": dict(Counter(case["outcome"] for case in cases)),
        "outcomes_by_category": {key: dict(value) for key, value in sorted(by_category.items())},
        "primary_stage_counts": dict(primary),
        "unmet_stage_counts": dict(unmet),
        "win_basis_counts": dict(Counter(case["win_basis"] for case in cases if case["win_basis"])),
        "cases": cases,
    }


# M2 deterministic diagnostics (frozen; never the judged metric) ---------------------


def retrieval_diagnostics(details: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Deterministic, judge-free retrieval diagnostics over upstream-shaped details.

    ``answer_substring_hit``: the casefolded reference answer occurs in a retrieved
    item. This is a diagnostic only. A paraphrased reference answer is a miss here,
    which the semantic judge may count as a hit.
    ``source_text_hit``: the record's own memory text is retrieved verbatim. It is
    comparable only for systems that store text verbatim, so it is not a
    cross-system metric.
    """

    if not details:
        return {"records": 0}
    answer_hits, source_hits = [], []
    by_type: dict[str, list[bool]] = {}
    for row in details:
        retrieved = [str(item) for item in row.get("retrieved", ())]
        answer = str(row.get("reference_answer", "")).casefold().strip()
        answer_hit = bool(answer) and any(answer in item.casefold() for item in retrieved)
        answer_hits.append(answer_hit)
        source_hits.append(str(row.get("memory", "")) in retrieved)
        by_type.setdefault(str(row.get("event_type")), []).append(answer_hit)
    n = len(details)
    return {
        "diagnostics_version": DIAGNOSTICS_VERSION,
        "records": n,
        "answer_substring_hit_rate": sum(answer_hits) / n,
        "answer_substring_hit_rate_by_event_type": {k: sum(v) / len(v) for k, v in sorted(by_type.items())},
        "source_text_hit_rate": sum(source_hits) / n,
        "empty_retrieval_rate": sum(1 for row in details if not row.get("retrieved")) / n,
    }


def judge_agreement(details: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Agreement of the substring diagnostic with recorded judge hits (upstream systems)."""

    pairs = [(bool(row.get("hit")), bool(row.get("_answer_hit"))) for row in details if "hit" in row]
    if not pairs:
        return None
    agree = sum(1 for judged, diag in pairs if judged == diag)
    return {
        "records": len(pairs),
        "agreement": agree / len(pairs),
        "judged_hit_diag_miss": sum(1 for judged, diag in pairs if judged and not diag) / len(pairs),
        "judged_miss_diag_hit": sum(1 for judged, diag in pairs if diag and not judged) / len(pairs),
    }


def upstream_reference_diagnostics(upstream_root: Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    """The same diagnostics over the published seed-2027 retrieval details of each upstream system."""

    out: dict[str, Any] = {}
    for system, relpath in freeze["upstream"]["formal_retrieval_files"].items():
        data = json.loads((upstream_root / relpath).read_text(encoding="utf-8"))
        details = data["phases"]["retrieval"]["details"]
        diag = retrieval_diagnostics(details)
        for row in details:
            answer = str(row.get("reference_answer", "")).casefold().strip()
            row["_answer_hit"] = bool(answer) and any(answer in str(i).casefold() for i in row.get("retrieved", ()))
        out[system] = {
            "file": relpath,
            "published_recall_at_k": data["phases"]["retrieval"]["recall_at_k"],
            "source_ids_sha256": sha256_text("\n".join(str(row["source_id"]) for row in details)),
            "diagnostics": diag,
            "diagnostic_vs_published_judge": judge_agreement(details),
        }
    return out


# Linked-only projection of retrieval details ----------------------------------------


def linked_only_details(details: Sequence[Mapping[str, Any]], records: Sequence[Mapping[str, Any]]) -> list[dict]:
    """Retrieval details with every dataset text replaced by a reference and digest."""

    text_index = {record["text"]: idx for idx, record in enumerate(records)}
    out = []
    for row in details:
        out.append({
            "index": row["index"],
            "event_type": row["event_type"],
            "source_id": row["source_id"],
            "hit": row.get("hit"),
            "retrieved": [
                {"selected_record_index": text_index.get(item), "sha256": sha256_text(str(item))}
                for item in row.get("retrieved", ())
            ],
            "write_latency_ms": row.get("write_latency_ms"),
            "read_latency_ms": row.get("read_latency_ms"),
        })
    return out


# Environment ---------------------------------------------------------------------------


def hardware_snapshot() -> dict[str, Any]:
    cpu = None
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    mem_kb = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                mem_kb = int(line.split()[1])
    except OSError:
        pass
    return {
        "cpu_model": cpu,
        "logical_cpus": os.cpu_count(),
        "mem_total_gb": round(mem_kb / 1024 / 1024, 1) if mem_kb else None,
        "gpu": "none used (Agent Memory write/read path has no model dependency)",
        "machine": platform.machine(),
    }


def agent_memory_identity() -> dict[str, Any]:
    register = json.loads((REPO_ROOT / "reports" / "runtime" / "baseline-register.json").read_text())
    status = _git(REPO_ROOT, "status", "--porcelain", "--untracked-files=no")
    from importlib import metadata

    packages = {}
    for name in ("numpy", "openai", "qdrant-client", "httpx", "jsonschema", "cryptography", "rfc8785"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "agent_memory_revision": _git(REPO_ROOT, "rev-parse", "HEAD"),
        "agent_memory_worktree_dirty": None if status is None else bool(status),
        "runtime_baseline_register_current": register.get("current"),
        "public_contract_version": contract.CONTRACT_VERSION,
        "python": sys.version.split()[0],
        "packages": packages,
    }


# Orchestration ---------------------------------------------------------------------------


def _upstream_config(upstream, freeze: Mapping[str, Any], output_dir: Path):
    judge = freeze["judge"]
    return upstream.Config(
        llm_base_url=judge["base_url"],
        llm_model=judge["model"],
        embedding_base_url="not_used",
        embedding_model="not_used",
        embedding_dims=0,
        qdrant_url="not_used",
        neo4j_uri="not_used",
        letta_url="not_used",
        output_dir=output_dir,
        history_dir=output_dir / "history",
        top_k=freeze["arguments"]["top_k"],
        seed=freeze["arguments"]["seed"],
    )


def run_formal(upstream_root: Path, output_dir: Path, *, phases: Sequence[str] | None = None,
               freeze: Mapping[str, Any] | None = None, verify: bool = True) -> tuple[dict, dict]:
    """Execute the frozen protocol; returns (committed_report, raw_report)."""

    freeze = freeze or load_freeze()
    upstream_obs = verify_upstream(freeze, upstream_root) if verify else {"verification": "skipped"}
    runner_sha = verify_self(freeze) if verify else None
    upstream = import_upstream(upstream_root)
    args = dict(freeze["arguments"])
    phases = list(phases or freeze["phases"])
    config = _upstream_config(upstream, freeze, output_dir)
    captured: list[list[dict]] = []

    async def capture_without_judging(_config, rows, concurrency: int = 32):  # noqa: ARG001
        # Judging is deferred to the frozen judge (--judge). The upstream judge maps
        # transport failure to hit=false, so an unprovisioned judge would fabricate 0.0.
        captured.append([dict(row) for row in rows])
        return [False] * len(rows)

    upstream.judge_retrievals = capture_without_judging
    adapter = AgentMemoryFormalAdapter()
    started = datetime.now(timezone.utc)
    output: dict[str, Any] = {
        "schema_version": "unified-benchmark-v2",
        "run_id": freeze["run_id"],
        "system": SYSTEM_NAME,
        "collection": upstream.normalize_collection(f"amb_kdd27_{SYSTEM_NAME}_{freeze['run_id']}"),
        "config": {**asdict(config), "output_dir": str(config.output_dir), "history_dir": str(config.history_dir)},
        "arguments": {**args, "system": SYSTEM_NAME, "phases": ",".join(phases), "run_id": freeze["run_id"]},
        "environment": upstream.environment_snapshot(),
        "phases": {},
    }
    phase_wall: dict[str, float] = {}
    records: list[dict] = []
    try:
        adapter.phase_label = "warmup"
        upstream.run_warmup(adapter, args["warmup_writes"])
        for phase in phases:
            adapter.phase_label = phase
            t0 = time.perf_counter()
            if phase == "retrieval":
                records = upstream.load_records(upstream_root / freeze["upstream"]["dataset"],
                                                args["retrieval_records"], args["seed"])
                output["phases"]["retrieval"] = upstream.run_retrieval(adapter, config, records, args["group_size"])
            elif phase == "conflict":
                output["phases"]["conflict"] = upstream.run_conflict(adapter, args["conflict_pairs"])
            elif phase == "isolation":
                output["phases"]["isolation"] = upstream.run_isolation(adapter, args["isolation_users"],
                                                                       args["isolation_facts"])
            elif phase == "deletion":
                output["phases"]["deletion"] = upstream.run_deletion(adapter, args["deletion_records"])
            elif phase == "concurrency":
                output["phases"]["concurrency"] = upstream.run_concurrency(
                    adapter, args["concurrency_records"], [int(v) for v in args["workers"].split(",")])
            elif phase == "scale":
                output["phases"]["scale"] = upstream.run_scale(
                    adapter, [int(v) for v in args["scales"].split(",")], args["scale_read_queries"])
            else:
                raise ValueError(f"unknown phase {phase!r}")
            phase_wall[phase] = round(time.perf_counter() - t0, 3)
        adapter.phase_label = "teardown"
        adapter.reset()  # snapshots write semantics of the last traced phase
    finally:
        adapter.close()
    finished = datetime.now(timezone.utc)

    retrieval = output["phases"].get("retrieval")
    if retrieval is not None:
        # The capture returned placeholder False values; strip every field derived from them.
        for key in ("recall_at_k", "recall_at_k_95ci", "omission_rate", "recall_by_event_type"):
            retrieval.pop(key, None)
        for row in retrieval["details"]:
            row["hit"] = None
        retrieval["judge_status"] = "not_judged_in_execution_run"
    raw = json.loads(json.dumps(output, default=str))

    semantics = {}
    for key, value in adapter.write_semantics.items():
        phase, uuid = key.split(":", 1)
        if phase == "conflict":
            semantics[uuid] = value
    agent_memory_ext: dict[str, Any] = {
        "profile_id": PROFILE_ID,
        "report_schema": REPORT_SCHEMA,
        "freeze": {
            "path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
            "sha256": sha256_file(FREEZE_PATH),
            "runner_sha256": runner_sha,
        },
        "upstream_verification": upstream_obs,
        "identity": agent_memory_identity(),
        "hardware": hardware_snapshot(),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "phase_wall_seconds": phase_wall,
        "adapter_tallies": {phase: dict(counter) for phase, counter in adapter.tallies.items()},
        "judge": {**freeze["judge"], "status": "blocked_pending_authorized_credential",
                  "recall_at_k": None},
    }
    if retrieval is not None:
        details = retrieval["details"]
        agent_memory_ext["selection"] = {
            "records": len(records),
            "source_ids_sha256": sha256_text("\n".join(str(r["source_id"]) for r in records)),
        }
        agent_memory_ext["retrieval_diagnostics"] = retrieval_diagnostics(details)
    if "conflict" in output["phases"]:
        agent_memory_ext["m4_failure_classification"] = classify_conflict_phase(
            upstream, args["conflict_pairs"], adapter.traces.get("conflict", []), semantics)
    output["agent_memory"] = agent_memory_ext
    raw["agent_memory"] = agent_memory_ext
    committed = json.loads(json.dumps(output, default=str))
    if retrieval is not None:
        committed["phases"]["retrieval"]["details"] = linked_only_details(retrieval["details"], records)
        committed["phases"]["retrieval"]["details_projection"] = "linked_only: dataset text replaced by " \
            "selected_record_index + sha256; reconstruct from the pinned dataset with upstream load_records"
    return committed, raw


def judge_raw_report(upstream_root: Path, raw: dict, freeze: Mapping[str, Any], base_url: str) -> dict:
    """Apply the frozen judge to a raw report's retrieval details via upstream ``judge_retrievals``."""

    upstream = import_upstream(upstream_root)
    config = _upstream_config(upstream, {**freeze, "judge": {**freeze["judge"], "base_url": base_url}},
                              Path(tempfile.gettempdir()))
    details = raw["phases"]["retrieval"]["details"]
    rows = [{"query": d["query"], "answer": d["reference_answer"], "retrieved": d["retrieved"]} for d in details]
    hits = asyncio.run(upstream.judge_retrievals(config, rows))
    return {
        "judge": {**freeze["judge"], "base_url": base_url},
        "recall_at_k": sum(hits) / len(hits),
        "recall_at_k_95ci": upstream.bootstrap_mean_ci(hits),
        "hits": [bool(h) for h in hits],
        "note": "upstream judge maps transport failure to false; verify endpoint health before accepting",
    }


def build_freeze_digest_fields(upstream_root: Path) -> dict[str, str]:
    """Helper for authoring the freeze file (prints the digests the freeze must carry)."""

    return {
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "harness_sha256": sha256_file(upstream_root / "agentmembench/evaluation/unified_benchmark.py"),
        "dataset_sha256": sha256_file(upstream_root / "data/memdialogue_v2.jsonl"),
        "formal_results_sha256sums_sha256": sha256_file(upstream_root / "results/formal/SHA256SUMS"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="committed (linked-only) report path")
    parser.add_argument("--raw-output", type=Path, help="uncommitted raw report with retrieved text")
    parser.add_argument("--reference-diagnostics", type=Path,
                        help="write deterministic diagnostics over the published upstream retrieval files")
    parser.add_argument("--judge", type=Path, help="raw report to judge with the frozen judge identity")
    parser.add_argument("--judge-base-url")
    parser.add_argument("--print-digests", action="store_true")
    args = parser.parse_args()
    freeze = load_freeze()
    if args.print_digests:
        print(json.dumps(build_freeze_digest_fields(args.upstream_root), indent=2))
        return 0
    if args.reference_diagnostics:
        verify_upstream(freeze, args.upstream_root)
        diag = upstream_reference_diagnostics(args.upstream_root, freeze)
        args.reference_diagnostics.write_text(json.dumps(diag, indent=2, sort_keys=True) + "\n")
        return 0
    if args.judge:
        if not args.judge_base_url:
            raise SystemExit("--judge requires --judge-base-url for the authorized, frozen judge endpoint")
        result = judge_raw_report(args.upstream_root, json.loads(args.judge.read_text()), freeze, args.judge_base_url)
        print(json.dumps({k: v for k, v in result.items() if k != "hits"}, indent=2))
        return 0
    committed, raw = run_formal(args.upstream_root, (args.output or Path("mesa-out.json")).parent)
    if args.raw_output:
        args.raw_output.write_text(json.dumps(raw, indent=2, sort_keys=True, default=str) + "\n")
    rendered = json.dumps(committed, indent=2, sort_keys=True, default=str) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
