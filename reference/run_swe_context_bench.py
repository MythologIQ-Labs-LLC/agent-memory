#!/usr/bin/env python
"""Run Agent Memory against the SWE Context Bench Lite retrieval protocol.

This is a standalone research adapter, not an Agent Memory package API. It
measures binary recovery of the gold prior experience from a natural-language
related task. Benchmark instance IDs remain sidecar-only and never enter the
retained memory text or identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
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

SCHEMA_VERSION = "1.0.0"
BENCHMARK_ID = "agent-memory-swe-context-bench-lite-retrieval"
UPSTREAM_REPOSITORY = "jiayuanz3/SWEContextBench"

REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_RUNTIME_CONFIG = (
    REFERENCE_ROOT
    / "fixtures"
    / "runtime-configuration"
    / "reference-composed-runtime.json"
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
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported SWE Context Bench manifest")
    if not isinstance(value.get("experiences"), list) or not value["experiences"]:
        raise ValueError("manifest requires experiences")
    if not isinstance(value.get("queries"), list) or not value["queries"]:
        raise ValueError("manifest requires queries")
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
    manifest = _manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    plan = validate_runtime_configuration(json.loads(runtime_config_path.read_text(encoding="utf-8")))

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
            multi_instances = _dedupe_experiences(multi.ranked_admitted, sidecars[repo])
            hit = gold in multi_instances
            for hits in multi.route_hits.values():
                authority_violations += sum(hit_row.authority_effect != "none" for hit_row in hits)
            authority_violations += int(multi.authority_effect != "none")

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
                        "hit": hit,
                        "gold_rank_diagnostic": multi_instances.index(gold) + 1 if hit else None,
                        "retrieved_experience_ids": multi_instances,
                        "candidate_count": len(multi.candidates),
                        "admitted_count": len(multi.admitted),
                        "routes_executed": list(multi.routes_executed),
                        "query_seconds": round(multi_seconds, 6),
                    },
                }
            )

    hits = sum(1 for row in query_rows if row["agent_memory"]["hit"])
    lexical_hits = sum(1 for row in query_rows if row["lexical_only"]["hit"])
    count = len(query_rows)
    return {
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
            "experience_count": len(declared),
            "repo_count": len(by_repo),
            "instance_ids_in_memory_text": False,
            "identity": "content-derived analysis_key; benchmark instance_id held in sidecar only",
            "experience_projection": "problem_statement + every summary row + final assistant text",
            "build_seconds_by_repo": build_seconds,
        },
        "queries": query_rows,
        "aggregate": {
            "query_count": count,
            "hit_count": hits,
            "hit_rate": 0.0 if not count else round(hits / count, 6),
            "lexical_only_hit_count": lexical_hits,
            "lexical_only_hit_rate": 0.0 if not count else round(lexical_hits / count, 6),
            "mean_query_seconds": _mean([float(row["agent_memory"]["query_seconds"]) for row in query_rows]),
            "mean_candidate_count": _mean([float(row["agent_memory"]["candidate_count"]) for row in query_rows]),
            "mean_admitted_count": _mean([float(row["agent_memory"]["admitted_count"]) for row in query_rows]),
        },
        "governance": {
            "corpus_mutation_failures": corpus_mutations,
            "route_authority_effect_violations": authority_violations,
        },
        "claim_boundary": {
            "measures": "retrieval of the gold prior experience from a natural-language related task",
            "does_not_measure": [
                "Jev-style typed atom extraction quality",
                "downstream SWE-bench task resolution",
                "answer generation quality",
                "conflict-detector precision/recall",
            ],
            "conflict_arm": "not implemented; all benchmark experiences are retained as the external reviewed corpus",
            "ranking": "gold rank is diagnostic only; primary score is binary hit rate",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--benchmark-root", required=True)
    parser.add_argument("--runtime-config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--lexical-anchor-limit", type=int, default=3)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_benchmark(
        manifest_path=Path(args.manifest).resolve(),
        benchmark_root=Path(args.benchmark_root).resolve(),
        runtime_config_path=Path(args.runtime_config).resolve(),
        agent_memory_revision=args.agent_memory_revision,
        lexical_anchor_limit=args.lexical_anchor_limit,
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
