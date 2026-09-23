"""SWE Context Bench Lite retrieval adapter for Agent Memory.

This harness is intentionally narrower than a coding-agent benchmark. It asks
whether a natural-language related task retrieves the known gold prior
experience from an immutable same-repository corpus, matching the first
retrieval-only protocol used by Bicameral issue #1307.

Benchmark instance IDs are kept in a sidecar mapping only. Canonical memory
identity is derived from the redacted experience content, so the benchmark
cannot win by matching the gold identifier as text.

The upstream fixture is external input and is not bundled here.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..core import policy
from ..runtime.adapter import RecallContext
from ..runtime.query_driven_recall import (
    DeterministicQueryDrivenRecallPlanner,
    QueryDrivenRecallConfig,
)
from ..runtime.runtime_composition import ConfiguredCompositionRuntime
from ..runtime.runtime_config import validate_runtime_configuration

SCHEMA_VERSION = "1.0.0"
BENCHMARK_ID = "agent-memory-swe-context-bench-lite-retrieval"
UPSTREAM_REPOSITORY = "jiayuanz3/SWEContextBench"

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


def _extract_manual_fields(text: str) -> tuple[str, str, str] | None:
    instance = _INSTANCE_RE.search(text)
    repo = _REPO_RE.search(text)
    problem = _PROBLEM_RE.search(text)
    if not instance or not repo or not problem:
        return None
    return instance.group(1).strip(), repo.group(1).strip(), problem.group(1).strip()


def parse_experience(path: Path) -> ExperienceProjection:
    """Project the public Claude session JSONL into the locked redacted shape.

    Retained text contains the issue/problem statement, all ``type: summary``
    rows, and the final assistant text message. File-history snapshots, thinking,
    tool calls/results, UUIDs, benchmark instance IDs, and raw JSONL are omitted.
    """
    rows: list[Mapping[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid experience JSONL at {path}:{line_number}") from exc
        if not isinstance(value, Mapping):
            raise ValueError(f"experience JSONL row must be an object at {path}:{line_number}")
        rows.append(value)

    manual: tuple[str, str, str] | None = None
    summaries: list[str] = []
    final_assistant = ""
    for row in rows:
        if row.get("type") == "summary":
            summary = str(row.get("summary", "")).strip()
            if summary and summary not in summaries:
                summaries.append(summary)
        message = row.get("message")
        role = str(message.get("role", "")) if isinstance(message, Mapping) else ""
        text = _message_text(message)
        if role == "user" and manual is None and text:
            manual = _extract_manual_fields(text)
        if role == "assistant" and text:
            final_assistant = text

    if manual is None:
        raise ValueError(f"experience {path} does not contain manual.yaml instance metadata")
    instance_id, repo, problem_statement = manual

    fragments: list[tuple[str, str]] = [("problem_statement", problem_statement)]
    fragments.extend(("summary", summary) for summary in summaries)
    if final_assistant:
        fragments.append(("final_assistant", final_assistant))

    canonical_projection = {
        "problem_statement": problem_statement,
        "summaries": summaries,
        "final_assistant": final_assistant,
    }
    analysis_key = _stable_digest(canonical_projection)
    return ExperienceProjection(
        instance_id=instance_id,
        repo=repo,
        analysis_key=analysis_key,
        fragments=tuple(fragments),
    )


def _load_related_problem(path: Path) -> tuple[str, str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"related task {path} must contain a JSON object")
    instance_id = str(value.get("instance_id", "")).strip()
    repo = str(value.get("repo", "")).strip()
    problem_statement = str(value.get("problem_statement", "")).strip()
    if not instance_id or not repo or not problem_statement:
        raise ValueError(f"related task {path} requires instance_id, repo, and problem_statement")
    return instance_id, repo, problem_statement


def _validate_manifest(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("SWE Context Bench manifest must be a JSON object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported SWE Context Bench manifest schema")
    experiences = value.get("experiences")
    queries = value.get("queries")
    if not isinstance(experiences, list) or not experiences:
        raise ValueError("manifest requires experiences")
    if not isinstance(queries, list) or not queries:
        raise ValueError("manifest requires queries")
    return value


def _project_ref(repo: str) -> str:
    digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
    return f"swecb-repo:{digest}"


def _proposal(
    *,
    proposal_id: str,
    memory_ref: str,
    tenant_ref: str,
    project_ref: str,
    evidence_refs: tuple[str, ...],
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:swe-context-bench",
        charter_version="charter-v1",
        target_reference=memory_ref,
        target_class=policy.M2,
        scope=tenant_ref,
        operation="promotion",
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=evidence_refs,
        tenant_ref=tenant_ref,
        isolation_domain_refs=(tenant_ref, project_ref),
        required_isolation_domain_refs=(project_ref,),
        project_ref=project_ref,
        purpose="swe-context-bench-retrieval",
    )


def _corpus_digest(runtime: ConfiguredCompositionRuntime) -> str:
    """Digest retrieval corpus only, excluding read-side governance/audit IDs."""
    substrate = runtime.adapter.checkpoint_substrate()
    state = substrate.export_checkpoint_state()
    corpus = {
        "episodes": state.get("episodes", []),
        "facts": state.get("facts", []),
    }
    return _stable_digest(corpus)


def _dedupe_experiences(
    fact_refs: Sequence[str],
    fact_to_instance: Mapping[str, str],
) -> list[str]:
    output: list[str] = []
    for fact_ref in fact_refs:
        instance_id = fact_to_instance.get(fact_ref)
        if instance_id and instance_id not in output:
            output.append(instance_id)
    return output


def _mean(values: Sequence[float]) -> float:
    return 0.0 if not values else round(sum(values) / len(values), 6)


def run_benchmark(
    *,
    manifest_path: Path,
    benchmark_root: Path,
    runtime_config_path: Path,
    agent_memory_revision: str,
    lexical_anchor_limit: int = 3,
) -> dict[str, Any]:
    if not agent_memory_revision:
        raise ValueError("agent_memory_revision is required")
    manifest = _validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    plan = validate_runtime_configuration(json.loads(runtime_config_path.read_text(encoding="utf-8")))
    tenant_ref = "swe-context-bench"

    declared_experiences: dict[str, Mapping[str, Any]] = {}
    experience_by_repo: dict[str, list[tuple[ExperienceProjection, Path]]] = defaultdict(list)
    input_hashes: dict[str, str] = {}
    for raw in manifest["experiences"]:
        if not isinstance(raw, Mapping):
            raise ValueError("experience manifest row must be an object")
        declared_id = str(raw.get("instance_id", "")).strip()
        declared_repo = str(raw.get("repo", "")).strip()
        relative_path = str(raw.get("path", "")).strip()
        if not declared_id or not declared_repo or not relative_path:
            raise ValueError("experience row requires instance_id, repo, and path")
        if declared_id in declared_experiences:
            raise ValueError(f"duplicate experience instance_id: {declared_id}")
        path = (benchmark_root / relative_path).resolve()
        projection = parse_experience(path)
        if projection.instance_id != declared_id or projection.repo != declared_repo:
            raise ValueError(
                f"experience sidecar mismatch for {relative_path}: "
                f"declared {declared_id}/{declared_repo}, "
                f"parsed {projection.instance_id}/{projection.repo}"
            )
        declared_experiences[declared_id] = raw
        experience_by_repo[declared_repo].append((projection, path))
        input_hashes[relative_path] = sha256_file(path)

    rows: list[dict[str, Any]] = []
    repo_build_seconds: dict[str, float] = {}
    route_authority_effect_violations = 0
    corpus_mutation_failures = 0

    with tempfile.TemporaryDirectory(prefix="agent-memory-swe-context-") as temp_root:
        runtimes: dict[str, ConfiguredCompositionRuntime] = {}
        planners: dict[str, DeterministicQueryDrivenRecallPlanner] = {}
        fact_maps: dict[str, dict[str, str]] = {}
        analysis_keys: dict[str, str] = {}

        for repo, experiences in sorted(experience_by_repo.items()):
            runtime = ConfiguredCompositionRuntime.create(
                Path(temp_root) / hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16],
                tenant=tenant_ref,
                plan=plan,
            )
            project_ref = _project_ref(repo)
            fact_to_instance: dict[str, str] = {}
            started = time.perf_counter()
            for projection, _path in experiences:
                analysis_keys[projection.instance_id] = projection.analysis_key
                experience_ref = f"swecb:experience:{projection.analysis_key}"
                for fragment_index, (kind, text) in enumerate(projection.fragments, start=1):
                    fragment_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    memory_ref = f"swecb:{projection.analysis_key}:{kind}:{fragment_index}"
                    result = runtime.retain(
                        _proposal(
                            proposal_id=f"swecb-proposal:{fragment_digest}",
                            memory_ref=memory_ref,
                            tenant_ref=tenant_ref,
                            project_ref=project_ref,
                            evidence_refs=(experience_ref, f"swecb:fragment:{fragment_digest}"),
                        ),
                        text,
                    )
                    if not result.committed or not result.fact_uuid:
                        raise RuntimeError(f"failed to retain SWE experience fragment {kind}")
                    fact_to_instance[result.fact_uuid] = projection.instance_id
            repo_build_seconds[repo] = round(time.perf_counter() - started, 6)
            runtimes[repo] = runtime
            planners[repo] = DeterministicQueryDrivenRecallPlanner(
                runtime.adapter,
                config=QueryDrivenRecallConfig(lexical_anchor_limit=lexical_anchor_limit),
            )
            fact_maps[repo] = fact_to_instance

        for raw in manifest["queries"]:
            if not isinstance(raw, Mapping):
                raise ValueError("query manifest row must be an object")
            declared_related = str(raw.get("related_instance_id", "")).strip()
            declared_repo = str(raw.get("repo", "")).strip()
            relative_path = str(raw.get("path", "")).strip()
            gold = str(raw.get("gold_experience_instance_id", "")).strip()
            if not declared_related or not declared_repo or not relative_path or not gold:
                raise ValueError(
                    "query row requires related_instance_id, repo, path, and gold_experience_instance_id"
                )
            if gold not in declared_experiences:
                raise ValueError(f"query gold experience is not in corpus: {gold}")
            if str(declared_experiences[gold].get("repo", "")) != declared_repo:
                raise ValueError(f"gold experience {gold} is not in query repo {declared_repo}")
            if declared_repo not in runtimes:
                raise ValueError(f"query repo has no experience corpus: {declared_repo}")

            path = (benchmark_root / relative_path).resolve()
            related_id, related_repo, problem_statement = _load_related_problem(path)
            input_hashes[relative_path] = sha256_file(path)
            if related_id != declared_related or related_repo != declared_repo:
                raise ValueError(
                    f"query sidecar mismatch for {relative_path}: "
                    f"declared {declared_related}/{declared_repo}, parsed {related_id}/{related_repo}"
                )

            runtime = runtimes[declared_repo]
            fact_to_instance = fact_maps[declared_repo]
            project_ref = _project_ref(declared_repo)
            context = RecallContext(
                target_domain_refs=(tenant_ref, project_ref),
                principal_ref="agent:swe-context-bench",
                project_ref=project_ref,
                purpose="swe-context-bench-retrieval",
            )
            before = _corpus_digest(runtime)

            lexical_started = time.perf_counter()
            lexical = runtime.recall(problem_statement, context)
            lexical_seconds = time.perf_counter() - lexical_started
            after_lexical = _corpus_digest(runtime)

            multi_started = time.perf_counter()
            multi = planners[declared_repo].recall(problem_statement, context)
            multi_seconds = time.perf_counter() - multi_started
            after_multi = _corpus_digest(runtime)

            corpus_unchanged = before == after_lexical == after_multi
            if not corpus_unchanged:
                corpus_mutation_failures += 1

            lexical_experiences = _dedupe_experiences(lexical.admitted, fact_to_instance)
            multi_experiences = _dedupe_experiences(multi.ranked_admitted, fact_to_instance)
            lexical_hit = gold in lexical_experiences
            multi_hit = gold in multi_experiences
            gold_rank = (
                multi_experiences.index(gold) + 1 if multi_hit else None
            )

            for hits in multi.route_hits.values():
                for hit in hits:
                    if hit.authority_effect != "none":
                        route_authority_effect_violations += 1
            if multi.authority_effect != "none":
                route_authority_effect_violations += 1

            rows.append(
                {
                    "related_instance_id": declared_related,
                    "repo": declared_repo,
                    "gold_experience_instance_id": gold,
                    "gold_analysis_key": analysis_keys[gold],
                    "corpus_immutable": corpus_unchanged,
                    "lexical_only": {
                        "hit": lexical_hit,
                        "retrieved_experience_ids": lexical_experiences,
                        "candidate_count": len(lexical.candidates),
                        "admitted_count": len(lexical.admitted),
                        "query_seconds": round(lexical_seconds, 6),
                    },
                    "agent_memory": {
                        "hit": multi_hit,
                        "gold_rank_diagnostic": gold_rank,
                        "retrieved_experience_ids": multi_experiences,
                        "candidate_count": len(multi.candidates),
                        "admitted_count": len(multi.admitted),
                        "routes_executed": list(multi.routes_executed),
                        "query_seconds": round(multi_seconds, 6),
                    },
                }
            )

    hit_count = sum(1 for row in rows if row["agent_memory"]["hit"])
    lexical_hit_count = sum(1 for row in rows if row["lexical_only"]["hit"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "score_protocol": "binary_gold_edge_recovery",
        "agent_memory_revision": agent_memory_revision,
        "upstream": {
            "repository": str(manifest.get("upstream_repository", UPSTREAM_REPOSITORY)),
            "revision": str(manifest.get("upstream_revision", "unbound")),
            "fixture": str(manifest.get("fixture", "SWEContextBench Lite")),
        },
        "inputs": {
            "manifest_sha256": sha256_file(manifest_path),
            "runtime_config_sha256": sha256_file(runtime_config_path),
            "file_sha256": dict(sorted(input_hashes.items())),
            "lexical_anchor_limit": lexical_anchor_limit,
        },
        "corpus": {
            "experience_count": len(declared_experiences),
            "repo_count": len(experience_by_repo),
            "instance_ids_in_memory_text": False,
            "identity": "content-derived analysis_key; benchmark instance_id held in sidecar only",
            "experience_projection": "problem_statement + every summary row + final assistant text",
            "build_seconds_by_repo": repo_build_seconds,
        },
        "queries": rows,
        "aggregate": {
            "query_count": len(rows),
            "hit_count": hit_count,
            "hit_rate": 0.0 if not rows else round(hit_count / len(rows), 6),
            "lexical_only_hit_count": lexical_hit_count,
            "lexical_only_hit_rate": 0.0 if not rows else round(lexical_hit_count / len(rows), 6),
            "mean_query_seconds": _mean([float(row["agent_memory"]["query_seconds"]) for row in rows]),
            "mean_candidate_count": _mean([float(row["agent_memory"]["candidate_count"]) for row in rows]),
            "mean_admitted_count": _mean([float(row["agent_memory"]["admitted_count"]) for row in rows]),
        },
        "governance": {
            "corpus_mutation_failures": corpus_mutation_failures,
            "route_authority_effect_violations": route_authority_effect_violations,
        },
        "claim_boundary": {
            "measures": "retrieval of the gold prior experience from a natural-language related task",
            "does_not_measure": [
                "Jev-style typed atom extraction quality",
                "downstream SWE-bench task resolution",
                "answer generation quality",
                "conflict-detector precision/recall",
                "production distributed storage",
            ],
            "conflict_arm": "not implemented; all benchmark experiences are retained as the external reviewed corpus",
            "ranking": "gold rank is diagnostic only; primary score is binary hit rate",
        },
    }
    return report
