#!/usr/bin/env python
"""Run pull-and-run SWE-ContextBench Lite retrieval comparisons.

This harness intentionally reuses the existing Agent Memory SWE-ContextBench
runners. It adds simple bounded baselines around the same manifest/input contract
without creating a second Agent Memory retrieval implementation.

Supported manifest schemas:

* 1.0.0: repository smoke/synthetic and ordinary single-gold manifests handled by
  ``run_swe_context_bench``.
* 2.0.0: frozen multi-gold/batched manifests handled by
  ``run_swe_context_bench_real_100``.

The default invocation uses the repository's credential-free synthetic fixture.
That proves harness behavior only. It is not an external protocol-comparable
SWE-ContextBench result.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import run_swe_context_bench as base
import run_swe_context_bench_real_100 as real100


HARNESS_SCHEMA_VERSION = "1.0.0"
HARNESS_ID = "agent-memory-swe-context-bench-lite-comparison-harness"
REFERENCE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = REFERENCE_ROOT.parent
DEFAULT_BENCHMARK_ROOT = REFERENCE_ROOT / "fixtures" / "benchmarks" / "swe-context-bench"
DEFAULT_MANIFEST = DEFAULT_BENCHMARK_ROOT / "manifest.json"
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class ExperienceDocument:
    instance_id: str
    repo: str
    text: str
    tokens: frozenset[str]


@dataclass(frozen=True)
class QueryCase:
    related_instance_id: str
    repo: str
    problem_statement: str
    gold_experience_instance_ids: tuple[str, ...]
    visible_experience_instance_ids: tuple[str, ...]


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(token.lower() for token in _TOKEN_RE.findall(text) if len(token) > 1)


def _load_query(path: Path) -> tuple[str, str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"query {path} must contain a JSON object")
    instance_id = str(value.get("instance_id", "")).strip()
    repo = str(value.get("repo", "")).strip()
    problem = str(value.get("problem_statement", "")).strip()
    if not instance_id or not repo or not problem:
        raise ValueError(f"query {path} requires instance_id, repo, and problem_statement")
    return instance_id, repo, problem


def _load_manifest(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("SWE-ContextBench manifest must be a JSON object")
    schema_version = str(value.get("schema_version", ""))
    if schema_version == base.MANIFEST_SCHEMA_VERSION:
        return base._manifest(value)
    if schema_version == real100.REAL_MANIFEST_SCHEMA_VERSION:
        return real100._validate_real_manifest(value)
    raise ValueError(f"unsupported SWE-ContextBench manifest schema: {schema_version or '<missing>'}")


def _experience_documents(
    manifest: Mapping[str, Any],
    benchmark_root: Path,
) -> tuple[dict[str, ExperienceDocument], dict[str, str]]:
    documents: dict[str, ExperienceDocument] = {}
    file_hashes: dict[str, str] = {}
    for row in manifest["experiences"]:
        instance_id = str(row["instance_id"])
        repo = str(row["repo"])
        relative = str(row["path"])
        path = (benchmark_root / relative).resolve()
        projection = base.parse_experience(path)
        if (projection.instance_id, projection.repo) != (instance_id, repo):
            raise ValueError(f"experience sidecar mismatch for {relative}")
        text = "\n".join(fragment for _kind, fragment in projection.fragments)
        documents[instance_id] = ExperienceDocument(
            instance_id=instance_id,
            repo=repo,
            text=text,
            tokens=_tokenize(text),
        )
        file_hashes[relative] = base.sha256_file(path)
    return documents, file_hashes


def _query_cases(
    manifest: Mapping[str, Any],
    benchmark_root: Path,
    documents: Mapping[str, ExperienceDocument],
) -> tuple[list[QueryCase], dict[str, str]]:
    query_hashes: dict[str, str] = {}
    cases: list[QueryCase] = []
    schema_version = str(manifest["schema_version"])

    batch_members: dict[str, tuple[str, ...]] = {}
    if schema_version == real100.REAL_MANIFEST_SCHEMA_VERSION:
        batch_members = {
            str(row["batch_id"]): tuple(str(value) for value in row["experience_instance_ids"])
            for row in manifest["batches"]
        }

    for row in manifest["queries"]:
        related = str(row["related_instance_id"])
        repo = str(row["repo"])
        relative = str(row["path"])
        path = (benchmark_root / relative).resolve()
        parsed_related, parsed_repo, problem = _load_query(path)
        if (parsed_related, parsed_repo) != (related, repo):
            raise ValueError(f"query sidecar mismatch for {relative}")
        query_hashes[relative] = base.sha256_file(path)

        if schema_version == real100.REAL_MANIFEST_SCHEMA_VERSION:
            gold = tuple(str(value) for value in row["gold_experience_instance_ids"])
            batch_id = str(row["batch_id"])
            visible = tuple(
                instance_id
                for instance_id in batch_members[batch_id]
                if documents[instance_id].repo == repo
            )
        else:
            gold = (str(row["gold_experience_instance_id"]),)
            visible = tuple(
                instance_id
                for instance_id, document in documents.items()
                if document.repo == repo
            )

        cases.append(
            QueryCase(
                related_instance_id=related,
                repo=repo,
                problem_statement=problem,
                gold_experience_instance_ids=gold,
                visible_experience_instance_ids=visible,
            )
        )
    return cases, query_hashes


def _lexical_rank(
    query: QueryCase,
    documents: Mapping[str, ExperienceDocument],
    *,
    top_k: int,
) -> list[str]:
    query_tokens = _tokenize(query.problem_statement)
    scored: list[tuple[int, float, str]] = []
    for instance_id in query.visible_experience_instance_ids:
        document = documents[instance_id]
        overlap = len(query_tokens.intersection(document.tokens))
        if overlap == 0:
            continue
        union = len(query_tokens.union(document.tokens))
        jaccard = 0.0 if union == 0 else overlap / union
        scored.append((overlap, jaccard, instance_id))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [instance_id for _overlap, _jaccard, instance_id in scored[:top_k]]


def _ndcg(ranked: Sequence[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    dcg = 0.0
    for rank, instance_id in enumerate(ranked[:k], start=1):
        if instance_id in gold:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_hits = min(len(gold), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return 0.0 if idcg == 0 else dcg / idcg


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return round((2.0 * precision * recall) / (precision + recall), 6)


def _quality(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    gold_edge_count = 0
    candidate_gold_hits = 0
    final_gold_hits = 0
    candidate_total = 0
    candidate_noise = 0
    admitted_total = 0
    false_admissions = 0
    false_refusals = 0
    ndcg_1: list[float] = []
    ndcg_3: list[float] = []

    for row in rows:
        gold = set(str(value) for value in row["gold_experience_instance_ids"])
        candidates = list(row["candidate_experience_ids"])
        admitted = list(row["retrieved_experience_ids"])
        gold_edge_count += len(gold)
        candidate_gold_hits += len(gold.intersection(candidates))
        final_gold_hits += len(gold.intersection(admitted))
        candidate_total += len(candidates)
        candidate_noise += sum(instance_id not in gold for instance_id in candidates)
        admitted_total += len(admitted)
        false_admissions += sum(instance_id not in gold for instance_id in admitted)
        false_refusals += len(gold.difference(admitted))
        ndcg_1.append(_ndcg(admitted, gold, 1))
        ndcg_3.append(_ndcg(admitted, gold, 3))

    candidate_recall = 0.0 if gold_edge_count == 0 else round(candidate_gold_hits / gold_edge_count, 6)
    final_recall = 0.0 if gold_edge_count == 0 else round(final_gold_hits / gold_edge_count, 6)
    precision = 0.0 if admitted_total == 0 else round(final_gold_hits / admitted_total, 6)
    return {
        "query_count": len(rows),
        "gold_edge_count": gold_edge_count,
        "candidate_gold_hit_count": candidate_gold_hits,
        "candidate_recall": candidate_recall,
        "candidate_experience_total": candidate_total,
        "candidate_noise_count": candidate_noise,
        "final_gold_hit_count": final_gold_hits,
        "final_admitted_recall": final_recall,
        "final_admitted_precision": precision,
        "final_admitted_f1": _f1(precision, final_recall),
        "final_admitted_experience_total": admitted_total,
        "false_admission_count": false_admissions,
        "false_refusal_count": false_refusals,
        "ndcg_at_1": round(sum(ndcg_1) / len(ndcg_1), 6) if ndcg_1 else 0.0,
        "ndcg_at_3": round(sum(ndcg_3) / len(ndcg_3), 6) if ndcg_3 else 0.0,
    }


def _baseline_rows(
    cases: Sequence[QueryCase],
    documents: Mapping[str, ExperienceDocument],
    *,
    backend: str,
    lexical_top_k: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if backend == "no_memory":
            ranked: list[str] = []
        elif backend == "lexical_overlap":
            ranked = _lexical_rank(case, documents, top_k=lexical_top_k)
        else:
            raise ValueError(f"unknown baseline backend: {backend}")
        rows.append(
            {
                "related_instance_id": case.related_instance_id,
                "repo": case.repo,
                "gold_experience_instance_ids": list(case.gold_experience_instance_ids),
                "candidate_experience_ids": ranked,
                "retrieved_experience_ids": ranked,
            }
        )
    return rows


def _resolve_revision(explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    env_value = os.environ.get("AGENT_MEMORY_REVISION", "").strip()
    if env_value:
        return env_value
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(
            "could not determine Agent Memory revision; pass --agent-memory-revision"
        ) from exc
    revision = completed.stdout.strip()
    if not revision:
        raise ValueError("git rev-parse returned an empty Agent Memory revision")
    return revision


def _run_agent_memory(
    *,
    manifest: Mapping[str, Any],
    manifest_path: Path,
    benchmark_root: Path,
    runtime_config_path: Path,
    evidence_profile_path: Path,
    agent_memory_revision: str,
    lexical_anchor_limit: int,
    consistency_repeat_count: int,
) -> Mapping[str, Any]:
    if str(manifest["schema_version"]) == real100.REAL_MANIFEST_SCHEMA_VERSION:
        return real100.run_real_100_edge_benchmark(
            manifest_path=manifest_path,
            benchmark_root=benchmark_root,
            runtime_config_path=runtime_config_path,
            evidence_profile_path=evidence_profile_path,
            agent_memory_revision=agent_memory_revision,
            lexical_anchor_limit=lexical_anchor_limit,
            consistency_repeat_count=consistency_repeat_count,
        )
    return base.run_benchmark(
        manifest_path=manifest_path,
        benchmark_root=benchmark_root,
        runtime_config_path=runtime_config_path,
        evidence_profile_path=evidence_profile_path,
        agent_memory_revision=agent_memory_revision,
        lexical_anchor_limit=lexical_anchor_limit,
        consistency_repeat_count=consistency_repeat_count,
    )


def _delta(left: Mapping[str, Any], right: Mapping[str, Any], key: str) -> float:
    return round(float(left[key]) - float(right[key]), 6)


def run_harness(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    benchmark_root: Path = DEFAULT_BENCHMARK_ROOT,
    runtime_config_path: Path = base.DEFAULT_RUNTIME_CONFIG,
    evidence_profile_path: Path = base.DEFAULT_EVIDENCE_PROFILE,
    agent_memory_revision: str,
    lexical_top_k: int = 3,
    lexical_anchor_limit: int = 3,
    consistency_repeat_count: int = 5,
) -> dict[str, Any]:
    if lexical_top_k < 1:
        raise ValueError("lexical_top_k must be >= 1")
    manifest = _load_manifest(manifest_path)
    documents, experience_hashes = _experience_documents(manifest, benchmark_root)
    cases, query_hashes = _query_cases(manifest, benchmark_root, documents)

    no_memory_rows = _baseline_rows(
        cases,
        documents,
        backend="no_memory",
        lexical_top_k=lexical_top_k,
    )
    lexical_rows = _baseline_rows(
        cases,
        documents,
        backend="lexical_overlap",
        lexical_top_k=lexical_top_k,
    )
    no_memory_quality = _quality(no_memory_rows)
    lexical_quality = _quality(lexical_rows)

    agent_report = _run_agent_memory(
        manifest=manifest,
        manifest_path=manifest_path,
        benchmark_root=benchmark_root,
        runtime_config_path=runtime_config_path,
        evidence_profile_path=evidence_profile_path,
        agent_memory_revision=agent_memory_revision,
        lexical_anchor_limit=lexical_anchor_limit,
        consistency_repeat_count=consistency_repeat_count,
    )
    agent_quality = agent_report["quality"]
    corpus_class = str(
        manifest.get("corpus_class", agent_report.get("corpus", {}).get("class", "unclassified"))
    )

    input_hashes = dict(sorted({**experience_hashes, **query_hashes}.items()))
    if str(manifest["schema_version"]) == real100.REAL_MANIFEST_SCHEMA_VERSION:
        external_status = str(
            agent_report.get("comparability", {}).get(
                "external_reference_status", "not-yet-comparable-input-provenance"
            )
        )
    else:
        external_status = str(
            agent_report.get("comparability", {}).get(
                "external_reference_status", "protocol-compatibility-not-yet-certified"
            )
        )

    return {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "harness_id": HARNESS_ID,
        "agent_memory_revision": agent_memory_revision,
        "upstream": {
            "repository": manifest.get("upstream_repository", base.UPSTREAM_REPOSITORY),
            "revision": manifest.get("upstream_revision", "unbound"),
            "fixture": manifest.get("fixture", "SWEContextBench Lite"),
            "manifest_schema_version": manifest["schema_version"],
            "corpus_class": corpus_class,
        },
        "inputs": {
            "manifest_sha256": base.sha256_file(manifest_path),
            "runtime_config_sha256": base.sha256_file(runtime_config_path),
            "evidence_profile_sha256": base.sha256_file(evidence_profile_path),
            "file_sha256": input_hashes,
            "document_projection": "problem_statement + every summary row + final assistant text",
        },
        "backends": {
            "no_memory": {
                "kind": "zero-memory retrieval baseline",
                "config": {"returns": "no prior experiences"},
                "quality": no_memory_quality,
                "queries": no_memory_rows,
                "authority_effect": "none",
            },
            "lexical_overlap": {
                "kind": "deterministic credential-free retrieval baseline",
                "config": {
                    "top_k": lexical_top_k,
                    "tokenization": "lowercase alphanumeric/underscore tokens length > 1",
                    "score": "token-overlap count, then Jaccard, then instance id",
                    "scope": "same repository and frozen batch when manifest schema 2.0.0",
                },
                "quality": lexical_quality,
                "queries": lexical_rows,
                "authority_effect": "none",
            },
            "agent_memory": {
                "kind": "canonical governed Agent Memory SWE-ContextBench runner",
                "config": {
                    "lexical_anchor_limit": lexical_anchor_limit,
                    "consistency_repeat_count": consistency_repeat_count,
                },
                "quality": agent_quality,
                "performance": agent_report.get("performance", {}),
                "consistency": agent_report.get("consistency", {}),
                "governance": agent_report.get("governance", {}),
                "comparability": agent_report.get("comparability", {}),
                "runner_benchmark_id": agent_report.get("benchmark_id"),
                "authority_effect": agent_report.get("governance", {}).get("authority_effect", "unknown"),
            },
        },
        "comparison": {
            "agent_memory_minus_no_memory": {
                "final_admitted_recall": _delta(agent_quality, no_memory_quality, "final_admitted_recall"),
                "final_admitted_precision": _delta(agent_quality, no_memory_quality, "final_admitted_precision"),
                "final_admitted_f1": _delta(agent_quality, no_memory_quality, "final_admitted_f1"),
                "ndcg_at_1": _delta(agent_quality, no_memory_quality, "ndcg_at_1"),
            },
            "agent_memory_minus_lexical_overlap": {
                "final_admitted_recall": _delta(agent_quality, lexical_quality, "final_admitted_recall"),
                "final_admitted_precision": _delta(agent_quality, lexical_quality, "final_admitted_precision"),
                "final_admitted_f1": _delta(agent_quality, lexical_quality, "final_admitted_f1"),
                "ndcg_at_1": _delta(agent_quality, lexical_quality, "ndcg_at_1"),
            },
            "aggregate_health_score": "not_defined",
        },
        "comparability": {
            "external_reference_status": external_status,
            "synthetic_fixture": corpus_class == "synthetic",
            "rule": (
                "a harness run is externally comparable only when the canonical Agent Memory runner "
                "reports protocol-comparable frozen input provenance; repository synthetic smoke runs "
                "never become external benchmark results"
            ),
        },
        "claim_boundary": {
            "measures": [
                "prior-experience retrieval/context selection under a shared frozen manifest",
                "no-memory versus deterministic lexical versus governed Agent Memory retrieval",
                "quality dimensions reported by the canonical SWE-ContextBench metric contract",
            ],
            "does_not_measure": [
                "downstream coding-agent patch correctness",
                "official SWE-bench task resolution",
                "answer-generation quality",
                "general memory-system quality outside the frozen retrieval task",
            ],
            "benchmark_score_is_authority": False,
            "backend_identity_is_memory_doctrine": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--runtime-config", type=Path, default=base.DEFAULT_RUNTIME_CONFIG)
    parser.add_argument("--evidence-profile", type=Path, default=base.DEFAULT_EVIDENCE_PROFILE)
    parser.add_argument("--agent-memory-revision")
    parser.add_argument("--lexical-top-k", type=int, default=3)
    parser.add_argument("--lexical-anchor-limit", type=int, default=3)
    parser.add_argument("--consistency-repeat-count", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        revision = _resolve_revision(args.agent_memory_revision)
        result = run_harness(
            manifest_path=args.manifest.resolve(),
            benchmark_root=args.benchmark_root.resolve(),
            runtime_config_path=args.runtime_config.resolve(),
            evidence_profile_path=args.evidence_profile.resolve(),
            agent_memory_revision=revision,
            lexical_top_k=args.lexical_top_k,
            lexical_anchor_limit=args.lexical_anchor_limit,
            consistency_repeat_count=args.consistency_repeat_count,
        )
    except ValueError as exc:
        parser.error(str(exc))

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
