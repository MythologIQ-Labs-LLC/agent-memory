#!/usr/bin/env python
"""Run Agent Memory against the SWE Context Bench Lite retrieval protocol.

This remains a standalone research adapter, not an Agent Memory package API.
Issue #467 extends the original #453 binary gold-edge adapter into an RC evidence
surface that keeps candidate generation, governed final admission, ranking,
consistency, performance, and governance evidence separate.

Benchmark instance IDs remain sidecar-only and never enter retained memory text
or logical identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

from agentmem_ref.core import policy
from agentmem_ref.runtime.adapter import RecallContext
from agentmem_ref.runtime.query_driven_recall import (
    DeterministicQueryDrivenRecallPlanner,
    QueryDrivenRecallConfig,
)
from agentmem_ref.runtime.runtime_composition import ConfiguredCompositionRuntime
from agentmem_ref.runtime.runtime_config import validate_runtime_configuration

MANIFEST_SCHEMA_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = "1.1.0"
BENCHMARK_ID = "agent-memory-swe-context-bench-lite-retrieval"
UPSTREAM_REPOSITORY = "jiayuanz3/SWEContextBench"

REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_RUNTIME_CONFIG = (
    REFERENCE_ROOT
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
)
DEFAULT_EVIDENCE_PROFILE = (
    REFERENCE_ROOT
    / "fixtures"
    / "benchmarks"
    / "swe-context-bench-rc-profile-v1.json"
)

_INSTANCE_RE = re.compile(r"(?m)^\s*instance_id:\s*([^\s]+)\s*$")
_REPO_RE = re.compile(r"(?m)^\s*repo:\s*([^\s]+)\s*$")
_PROBLEM_RE = re.compile(r"(?ms)^\s*problem_statement:\s*(.+)\Z")


@dataclass(frozen=True)
class ExperienceProjection:
    instance_id: str
    repo: str
    analysis_key: str
    fragments: tuple[tuple[str, str], ...]


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _stable_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256_bytes(payload.encode("utf-8"))


def _message_text(message: object) -> str:
    if not isinstance(message, Mapping):
        return ""
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, Mapping) and item.get("type") == "text":
            text = str(item.get("text", "")).strip()
        else:
            continue
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _manual_fields(text: str) -> tuple[str, str, str] | None:
    instance = _INSTANCE_RE.search(text)
    repo = _REPO_RE.search(text)
    problem = _PROBLEM_RE.search(text)
    if not instance or not repo or not problem:
        return None
    return instance.group(1).strip(), repo.group(1).strip(), problem.group(1).strip()


def parse_experience(path: Path) -> ExperienceProjection:
    """Project public Claude session JSONL into Jin's locked redacted shape."""
    manual: tuple[str, str, str] | None = None
    summaries: list[str] = []
    final_assistant = ""
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid experience JSONL at {path}:{line_number}") from exc
        if not isinstance(row, Mapping):
            raise ValueError(f"experience JSONL row must be an object at {path}:{line_number}")

        if row.get("type") == "summary":
            summary = str(row.get("summary", "")).strip()
            if summary and summary not in summaries:
                summaries.append(summary)

        message = row.get("message")
        role = str(message.get("role", "")) if isinstance(message, Mapping) else ""
        text = _message_text(message)
        if role == "user" and manual is None and text:
            manual = _manual_fields(text)
        if role == "assistant" and text:
            final_assistant = text

    if manual is None:
        raise ValueError(f"experience {path} does not contain manual.yaml instance metadata")
    instance_id, repo, problem_statement = manual

    fragments: list[tuple[str, str]] = [("problem_statement", problem_statement)]
    fragments.extend(("summary", summary) for summary in summaries)
    if final_assistant:
        fragments.append(("final_assistant", final_assistant))

    projection = {
        "problem_statement": problem_statement,
        "summaries": summaries,
        "final_assistant": final_assistant,
    }
    return ExperienceProjection(
        instance_id=instance_id,
        repo=repo,
        analysis_key=_stable_digest(projection),
        fragments=tuple(fragments),
    )


def _load_related(path: Path) -> tuple[str, str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"related task {path} must contain a JSON object")
    instance_id = str(value.get("instance_id", "")).strip()
    repo = str(value.get("repo", "")).strip()
    problem = str(value.get("problem_statement", "")).strip()
    if not instance_id or not repo or not problem:
        raise ValueError(f"related task {path} requires instance_id, repo, and problem_statement")
    return instance_id, repo, problem


def _manifest(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported SWE Context Bench manifest")
    if not isinstance(value.get("experiences"), list) or not value["experiences"]:
        raise ValueError("manifest requires experiences")
    if not isinstance(value.get("queries"), list) or not value["queries"]:
        raise ValueError("manifest requires queries")
    return value


def _evidence_profile(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != "1.0.0":
        raise ValueError("unsupported SWE Context Bench RC evidence profile")
    if not str(value.get("profile_id", "")).strip():
        raise ValueError("SWE Context Bench RC evidence profile requires profile_id")
    return value


def _project_ref(repo: str) -> str:
    return "swecb-repo:" + hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]


def _proposal(
    *,
    proposal_id: str,
    memory_ref: str,
    project_ref: str,
    evidence_refs: tuple[str, ...],
) -> policy.Proposal:
    tenant = "swe-context-bench"
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:swe-context-bench",
        charter_version="charter-v1",
        target_reference=memory_ref,
        target_class=policy.M2,
        scope=tenant,
        operation="promotion",
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=evidence_refs,
        tenant_ref=tenant,
        isolation_domain_refs=(tenant, project_ref),
        required_isolation_domain_refs=(project_ref,),
        project_ref=project_ref,
        purpose="swe-context-bench-retrieval",
    )


def _corpus_digest(runtime: ConfiguredCompositionRuntime) -> str:
    """Bind only candidate corpus, excluding read-side audit/id progress."""
    state = runtime.adapter.checkpoint_substrate().export_checkpoint_state()
    return _stable_digest({"episodes": state.get("episodes", []), "facts": state.get("facts", [])})


def _dedupe_experiences(fact_refs: Sequence[str], sidecar: Mapping[str, str]) -> list[str]:
    result: list[str] = []
    for fact_ref in fact_refs:
        instance = sidecar.get(fact_ref)
        if instance and instance not in result:
            result.append(instance)
    return result


def _mean(values: Sequence[float]) -> float:
    return 0.0 if not values else round(sum(values) / len(values), 6)


def _median(values: Sequence[float]) -> float:
    return 0.0 if not values else round(float(statistics.median(values)), 6)


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return round((2.0 * precision * recall) / (precision + recall), 6)


def _ndcg_at(rank: int | None, k: int) -> float:
    if rank is None or rank < 1 or rank > k:
        return 0.0
    return 1.0 / math.log2(rank + 1)


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 1.0
    return len(left_set & right_set) / len(union)


def _mean_pairwise_jaccard(runs: Sequence[Sequence[str]]) -> float | None:
    if len(runs) < 2:
        return None
    scores = [_jaccard(left, right) for left, right in combinations(runs, 2)]
    return round(sum(scores) / len(scores), 6)


def _consistency_related_ids(
    manifest: Mapping[str, Any],
    *,
    limit: int,
) -> tuple[str, ...]:
    explicit = manifest.get("consistency_related_instance_ids")
    if explicit is not None:
        if not isinstance(explicit, list) or any(not str(value).strip() for value in explicit):
            raise ValueError("consistency_related_instance_ids must be a list of non-empty values")
        return tuple(dict.fromkeys(str(value).strip() for value in explicit))

    result: list[str] = []
    for row in manifest["queries"]:
        if not isinstance(row, Mapping):
            continue
        related = str(row.get("related_instance_id", "")).strip()
        if related and related not in result:
            result.append(related)
        if len(result) >= limit:
            break
    return tuple(result)


def _retrieval_metrics(query_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    query_count = len(query_rows)
    candidate_hits = 0
    final_hits = 0
    candidate_total = 0
    candidate_noise = 0
    admitted_total = 0
    false_admissions = 0
    false_refusals = 0
    ndcg_1: list[float] = []
    ndcg_3: list[float] = []

    for row in query_rows:
        gold = str(row["gold_experience_instance_id"])
        result = row["agent_memory"]
        candidates = list(result["candidate_experience_ids"])
        admitted = list(result["retrieved_experience_ids"])
        rank = result["gold_rank_diagnostic"]

        candidate_hit = gold in candidates
        final_hit = gold in admitted
        candidate_hits += int(candidate_hit)
        final_hits += int(final_hit)
        candidate_total += len(candidates)
        candidate_noise += sum(instance != gold for instance in candidates)
        admitted_total += len(admitted)
        false_admissions += sum(instance != gold for instance in admitted)
        false_refusals += int(not final_hit)
        ndcg_1.append(_ndcg_at(rank, 1))
        ndcg_3.append(_ndcg_at(rank, 3))

    candidate_recall = 0.0 if not query_count else round(candidate_hits / query_count, 6)
    final_recall = 0.0 if not query_count else round(final_hits / query_count, 6)
    final_precision = 0.0 if not admitted_total else round(final_hits / admitted_total, 6)

    return {
        "query_count": query_count,
        "candidate_gold_hit_count": candidate_hits,
        "candidate_recall": candidate_recall,
        "candidate_experience_total": candidate_total,
        "candidate_noise_count": candidate_noise,
        "final_gold_hit_count": final_hits,
        "final_admitted_recall": final_recall,
        "final_admitted_precision": final_precision,
        "final_admitted_f1": _f1(final_precision, final_recall),
        "final_admitted_experience_total": admitted_total,
        "false_admission_count": false_admissions,
        "false_refusal_count": false_refusals,
        "ndcg_at_1": _mean(ndcg_1),
        "ndcg_at_3": _mean(ndcg_3),
        "published_compatible_gold_board_named_recall": final_recall,
    }


def run_benchmark(
    *,
    manifest_path: Path,
    benchmark_root: Path,
    runtime_config_path: Path,
    agent_memory_revision: str,
    lexical_anchor_limit: int = 3,
    evidence_profile_path: Path = DEFAULT_EVIDENCE_PROFILE,
    consistency_repeat_count: int = 5,
    consistency_query_limit: int = 10,
) -> dict[str, Any]:
    if not agent_memory_revision:
        raise ValueError("agent_memory_revision is required")
    if consistency_repeat_count < 1:
        raise ValueError("consistency_repeat_count must be >= 1")
    if consistency_query_limit < 0:
        raise ValueError("consistency_query_limit must be non-negative")

    manifest = _manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    profile = _evidence_profile(json.loads(evidence_profile_path.read_text(encoding="utf-8")))
    plan = validate_runtime_configuration(json.loads(runtime_config_path.read_text(encoding="utf-8")))
    consistency_ids = _consistency_related_ids(manifest, limit=consistency_query_limit)

    declared: dict[str, Mapping[str, Any]] = {}
    by_repo: dict[str, list[ExperienceProjection]] = defaultdict(list)
    input_hashes: dict[str, str] = {}
    for row in manifest["experiences"]:
        if not isinstance(row, Mapping):
            raise ValueError("experience manifest row must be an object")
        instance_id = str(row.get("instance_id", "")).strip()
        repo = str(row.get("repo", "")).strip()
        relative = str(row.get("path", "")).strip()
        if not instance_id or not repo or not relative:
            raise ValueError("experience row requires instance_id, repo, and path")
        if instance_id in declared:
            raise ValueError(f"duplicate experience instance_id: {instance_id}")
        path = (benchmark_root / relative).resolve()
        projected = parse_experience(path)
        if (projected.instance_id, projected.repo) != (instance_id, repo):
            raise ValueError(f"experience sidecar mismatch for {relative}")
        declared[instance_id] = row
        by_repo[repo].append(projected)
        input_hashes[relative] = sha256_file(path)

    query_rows: list[dict[str, Any]] = []
    build_seconds: dict[str, float] = {}
    corpus_mutations = 0
    authority_violations = 0

    with tempfile.TemporaryDirectory(prefix="agent-memory-swe-context-") as root:
        runtimes: dict[str, ConfiguredCompositionRuntime] = {}
        planners: dict[str, DeterministicQueryDrivenRecallPlanner] = {}
        sidecars: dict[str, dict[str, str]] = {}
        analysis_keys: dict[str, str] = {}

        for repo, experiences in sorted(by_repo.items()):
            runtime = ConfiguredCompositionRuntime.create(
                Path(root) / hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16],
                tenant="swe-context-bench",
                plan=plan,
            )
            project_ref = _project_ref(repo)
            fact_sidecar: dict[str, str] = {}
            started = time.perf_counter()
            for experience in experiences:
                analysis_keys[experience.instance_id] = experience.analysis_key
                shared_ref = f"swecb:experience:{experience.analysis_key}"
                for index, (kind, text) in enumerate(experience.fragments, start=1):
                    fragment_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    result = runtime.retain(
                        _proposal(
                            proposal_id=f"swecb-proposal:{experience.analysis_key}:{fragment_digest}",
                            memory_ref=f"swecb:{experience.analysis_key}:{kind}:{index}",
                            project_ref=project_ref,
                            evidence_refs=(shared_ref, f"swecb:fragment:{fragment_digest}"),
                        ),
                        text,
                    )
                    if not result.committed or not result.fact_uuid:
                        raise RuntimeError(f"failed to retain SWE experience fragment {kind}")
                    fact_sidecar[result.fact_uuid] = experience.instance_id
            build_seconds[repo] = round(time.perf_counter() - started, 6)
            runtimes[repo] = runtime
            planners[repo] = DeterministicQueryDrivenRecallPlanner(
                runtime.adapter,
                config=QueryDrivenRecallConfig(lexical_anchor_limit=lexical_anchor_limit),
            )
            sidecars[repo] = fact_sidecar

        for row in manifest["queries"]:
            if not isinstance(row, Mapping):
                raise ValueError("query manifest row must be an object")
            related = str(row.get("related_instance_id", "")).strip()
            repo = str(row.get("repo", "")).strip()
            relative = str(row.get("path", "")).strip()
            gold = str(row.get("gold_experience_instance_id", "")).strip()
            if not related or not repo or not relative or not gold:
                raise ValueError("query row is incomplete")
            if gold not in declared or str(declared[gold].get("repo", "")) != repo:
                raise ValueError(f"gold experience {gold} is not in the same-repo corpus")
            if repo not in runtimes:
                raise ValueError(f"query repo has no experience corpus: {repo}")

            path = (benchmark_root / relative).resolve()
            parsed_related, parsed_repo, problem = _load_related(path)
            input_hashes[relative] = sha256_file(path)
            if (parsed_related, parsed_repo) != (related, repo):
                raise ValueError(f"query sidecar mismatch for {relative}")

            runtime = runtimes[repo]
            project_ref = _project_ref(repo)
            context = RecallContext(
                target_domain_refs=("swe-context-bench", project_ref),
                principal_ref="agent:swe-context-bench",
                project_ref=project_ref,
                purpose="swe-context-bench-retrieval",
            )
            before = _corpus_digest(runtime)

            start = time.perf_counter()
            lexical = runtime.recall(problem, context)
            lexical_seconds = time.perf_counter() - start
            after_lexical = _corpus_digest(runtime)

            start = time.perf_counter()
            multi = planners[repo].recall(problem, context)
            multi_seconds = time.perf_counter() - start
            after_multi = _corpus_digest(runtime)

            immutable = before == after_lexical == after_multi
            if not immutable:
                corpus_mutations += 1

            lexical_instances = _dedupe_experiences(lexical.admitted, sidecars[repo])
            candidate_instances = _dedupe_experiences(multi.candidates, sidecars[repo])
            multi_instances = _dedupe_experiences(multi.ranked_admitted, sidecars[repo])
            hit = gold in multi_instances
            for hits in multi.route_hits.values():
                authority_violations += sum(hit_row.authority_effect != "none" for hit_row in hits)
            authority_violations += int(multi.authority_effect != "none")

            consistency_runs: list[list[str]] = [multi_instances]
            consistency_query_seconds: list[float] = [multi_seconds]
            if related in consistency_ids:
                for _repeat_index in range(1, consistency_repeat_count):
                    repeat_before = _corpus_digest(runtime)
                    repeat_start = time.perf_counter()
                    repeated = planners[repo].recall(problem, context)
                    repeat_seconds = time.perf_counter() - repeat_start
                    repeat_after = _corpus_digest(runtime)
                    if repeat_before != repeat_after:
                        corpus_mutations += 1
                        immutable = False

                    repeated_instances = _dedupe_experiences(
                        repeated.ranked_admitted,
                        sidecars[repo],
                    )
                    consistency_runs.append(repeated_instances)
                    consistency_query_seconds.append(repeat_seconds)
                    for hits in repeated.route_hits.values():
                        authority_violations += sum(
                            hit_row.authority_effect != "none" for hit_row in hits
                        )
                    authority_violations += int(repeated.authority_effect != "none")

            query_rows.append(
                {
                    "related_instance_id": related,
                    "repo": repo,
                    "gold_experience_instance_id": gold,
                    "gold_analysis_key": analysis_keys[gold],
                    "corpus_immutable": immutable,
                    "lexical_only": {
                        "hit": gold in lexical_instances,
                        "retrieved_experience_ids": lexical_instances,
                        "candidate_count": len(lexical.candidates),
                        "admitted_count": len(lexical.admitted),
                        "query_seconds": round(lexical_seconds, 6),
                    },
                    "agent_memory": {
                        "candidate_hit": gold in candidate_instances,
                        "candidate_experience_ids": candidate_instances,
                        "hit": hit,
                        "gold_rank_diagnostic": multi_instances.index(gold) + 1 if hit else None,
                        "retrieved_experience_ids": multi_instances,
                        "candidate_count": len(multi.candidates),
                        "admitted_count": len(multi.admitted),
                        "routes_executed": list(multi.routes_executed),
                        "query_seconds": round(multi_seconds, 6),
                    },
                    "consistency": {
                        "included": related in consistency_ids,
                        "repeat_count": len(consistency_runs) if related in consistency_ids else 1,
                        "admitted_experience_id_sets": (
                            consistency_runs if related in consistency_ids else [multi_instances]
                        ),
                        "mean_pairwise_jaccard": (
                            _mean_pairwise_jaccard(consistency_runs)
                            if related in consistency_ids
                            else None
                        ),
                        "repeat_query_seconds": (
                            [round(value, 6) for value in consistency_query_seconds]
                            if related in consistency_ids
                            else [round(multi_seconds, 6)]
                        ),
                    },
                }
            )

    hits = sum(1 for row in query_rows if row["agent_memory"]["hit"])
    lexical_hits = sum(1 for row in query_rows if row["lexical_only"]["hit"])
    count = len(query_rows)
    quality = _retrieval_metrics(query_rows)
    consistency_rows = [
        row for row in query_rows
        if row["consistency"]["included"]
    ]
    consistency_scores = [
        float(row["consistency"]["mean_pairwise_jaccard"])
        for row in consistency_rows
        if row["consistency"]["mean_pairwise_jaccard"] is not None
    ]
    query_seconds = [float(row["agent_memory"]["query_seconds"]) for row in query_rows]
    corpus_class = str(manifest.get("corpus_class", "unclassified")).strip() or "unclassified"
    synthetic_fixture = corpus_class == "synthetic"
    external_comparison_status = (
        "not-comparable-synthetic-fixture"
        if synthetic_fixture
        else "protocol-compatibility-not-yet-certified"
    )

    route_profile = {
        "planner": "deterministic_query_driven_recall",
        "lexical_anchor_limit": lexical_anchor_limit,
        "candidate_routes": "runtime-reported-per-query",
        "final_admission": "canonical governed recall admission",
        "authority_effect": "none",
    }
    scoring_semantics = {
        "gold_unit": "prior experience / board",
        "candidate_recall": "fraction of gold edges whose gold experience is present before final admission",
        "final_admitted_recall": "fraction of gold edges whose gold experience is named after final admission",
        "final_admitted_precision": "gold experiences named divided by all final admitted experience names",
        "false_admission": "final admitted experience name that is not the query gold; IR error, not a governance authority violation",
        "false_refusal": "gold experience not named after final admission",
        "ndcg": "single-relevant-item nDCG over final admitted experience ranking",
    }
    consistency_semantics = {
        "selection": (
            "manifest consistency_related_instance_ids when supplied; otherwise first "
            f"{consistency_query_limit} unique related_instance_id values in manifest order"
        ),
        "repeat_count": consistency_repeat_count,
        "unit": "deduplicated final admitted experience-id set",
        "metric": "mean pairwise Jaccard",
        "same_runtime": True,
        "persisted_restart_claimed": False,
    }

    comparability_payload = {
        "benchmark_profile_id": str(profile["profile_id"]),
        "corpus_class": corpus_class,
        "fixture_identity": str(manifest.get("fixture", "SWEContextBench Lite")),
        "manifest_sha256": sha256_file(manifest_path),
        "runtime_config_sha256": sha256_file(runtime_config_path),
        "route_profile": route_profile,
        "scoring_semantics": scoring_semantics,
        "consistency_semantics": consistency_semantics,
    }

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "score_protocol": "swe_context_bench_lite_gold_edge_retrieval_v1",
        "agent_memory_revision": agent_memory_revision,
        "benchmark_profile": {
            "profile_id": profile["profile_id"],
            "sha256": sha256_file(evidence_profile_path),
            "source": profile.get("source", {}),
            "public_protocol": profile.get("public_protocol", {}),
            "external_reference_results": profile.get("external_reference_results", {}),
            "agent_memory_directional_goals": profile.get("agent_memory_directional_goals", {}),
            "historical_agent_memory": profile.get("historical_agent_memory", {}),
            "aggregate_health_score": profile.get("aggregate_health_score", "not_defined"),
        },
        "upstream": {
            "repository": str(manifest.get("upstream_repository", UPSTREAM_REPOSITORY)),
            "revision": str(manifest.get("upstream_revision", "unbound")),
            "fixture": str(manifest.get("fixture", "SWEContextBench Lite")),
            "corpus_class": corpus_class,
        },
        "inputs": {
            "manifest_sha256": sha256_file(manifest_path),
            "runtime_config_sha256": sha256_file(runtime_config_path),
            "evidence_profile_sha256": sha256_file(evidence_profile_path),
            "file_sha256": dict(sorted(input_hashes.items())),
            "lexical_anchor_limit": lexical_anchor_limit,
            "consistency_repeat_count": consistency_repeat_count,
            "consistency_related_instance_ids": list(consistency_ids),
        },
        "corpus": {
            "experience_count": len(declared),
            "repo_count": len(by_repo),
            "instance_ids_in_memory_text": False,
            "identity": "content-derived analysis_key; benchmark instance_id held in sidecar only",
            "experience_projection": "problem_statement + every summary row + final assistant text",
            "build_seconds_by_repo": build_seconds,
            "build_seconds_total": round(sum(build_seconds.values()), 6),
            "synthetic_fixture": synthetic_fixture,
        },
        "metric_contract": {
            "candidate_generation": [
                "candidate_recall",
                "candidate_experience_total",
                "candidate_noise_count",
            ],
            "final_governed_admission": [
                "final_admitted_recall",
                "final_admitted_precision",
                "final_admitted_f1",
                "false_admission_count",
                "false_refusal_count",
                "ndcg_at_1",
                "ndcg_at_3",
            ],
            "governance_failures_are_ir_errors": False,
            "aggregate_health_score": "not_defined",
        },
        "queries": query_rows,
        "quality": quality,
        "aggregate": {
            "query_count": count,
            "hit_count": hits,
            "hit_rate": 0.0 if not count else round(hits / count, 6),
            "lexical_only_hit_count": lexical_hits,
            "lexical_only_hit_rate": 0.0 if not count else round(lexical_hits / count, 6),
            "mean_query_seconds": _mean(query_seconds),
            "median_query_seconds": _median(query_seconds),
            "median_query_ms": round(_median(query_seconds) * 1000.0, 3),
            "mean_candidate_count": _mean(
                [float(row["agent_memory"]["candidate_count"]) for row in query_rows]
            ),
            "mean_admitted_count": _mean(
                [float(row["agent_memory"]["admitted_count"]) for row in query_rows]
            ),
        },
        "consistency": {
            "query_count": len(consistency_rows),
            "repeat_count": consistency_repeat_count,
            "mean_pairwise_jaccard": _mean(consistency_scores) if consistency_scores else None,
            "metric": "mean pairwise Jaccard over final admitted experience-id sets",
            "persisted_restart_claimed": False,
        },
        "performance": {
            "corpus_build_seconds_total": round(sum(build_seconds.values()), 6),
            "corpus_build_seconds_by_repo": build_seconds,
            "successful_scored_query_count": count,
            "median_successful_scored_query_seconds": _median(query_seconds),
            "median_successful_scored_query_ms": round(_median(query_seconds) * 1000.0, 3),
            "timing_semantics": (
                "wall-clock perf_counter for local corpus construction and first scored "
                "Agent Memory query pass; consistency repeats are reported per query but "
                "excluded from the scored-query median"
            ),
            "token_or_model_call_counts": "not_exposed_by_this_runner",
        },
        "governance": {
            "corpus_mutation_failures": corpus_mutations,
            "route_authority_effect_violations": authority_violations,
            "ir_false_admission_count": quality["false_admission_count"],
            "ir_false_refusal_count": quality["false_refusal_count"],
            "authority_effect": "none" if authority_violations == 0 else "violation-detected",
        },
        "comparability": {
            "signature": _stable_digest(comparability_payload),
            "bound_fields": comparability_payload,
            "external_reference_status": external_comparison_status,
            "rule": (
                "reports are comparable only when profile/corpus/fixture/manifest/config/"
                "route/scoring/consistency denominator fields are compatible; otherwise "
                "classify not-comparable"
            ),
        },
        "claim_boundary": {
            "measures": [
                "retrieval of the gold prior experience from a natural-language related task",
                "candidate versus governed final-admission retrieval quality",
                "final admitted ranking quality",
                "same-runtime repeated retrieval-set consistency",
                "bounded local corpus-build/query timing",
                "retrieval governance evidence",
            ],
            "does_not_measure": [
                "Jev-style typed atom extraction quality",
                "downstream SWE-bench task resolution or patch correctness",
                "answer generation quality",
                "conflict-detector precision/recall",
                "production distributed storage",
                "persisted-restart consistency in this runner",
            ],
            "conflict_arm": "not implemented; all benchmark experiences are retained as the external reviewed corpus",
            "ranking": "gold rank remains diagnostic and now also feeds single-relevant-item nDCG@1/@3",
            "synthetic_fixture_cannot_substitute_for_public_corpus": synthetic_fixture,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--benchmark-root", required=True)
    parser.add_argument("--runtime-config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--evidence-profile", default=str(DEFAULT_EVIDENCE_PROFILE))
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--lexical-anchor-limit", type=int, default=3)
    parser.add_argument("--consistency-repeat-count", type=int, default=5)
    parser.add_argument("--consistency-query-limit", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_benchmark(
        manifest_path=Path(args.manifest).resolve(),
        benchmark_root=Path(args.benchmark_root).resolve(),
        runtime_config_path=Path(args.runtime_config).resolve(),
        evidence_profile_path=Path(args.evidence_profile).resolve(),
        agent_memory_revision=args.agent_memory_revision,
        lexical_anchor_limit=args.lexical_anchor_limit,
        consistency_repeat_count=args.consistency_repeat_count,
        consistency_query_limit=args.consistency_query_limit,
    )
    governance = report["governance"]
    if governance["corpus_mutation_failures"] != 0:
        raise SystemExit("SWE Context benchmark detected candidate-corpus mutation during query evaluation")
    if governance["route_authority_effect_violations"] != 0:
        raise SystemExit("SWE Context benchmark detected retrieval authority leakage")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
