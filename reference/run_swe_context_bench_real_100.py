#!/usr/bin/env python
"""Run the protocol-faithful SWE-ContextBench Lite 99-query / 100-edge evaluation.

This wrapper closes two gaps in the original binary-edge adapter without creating a
second retrieval engine:

* one related issue may name multiple gold past tasks; and
* each evaluation batch may bind an explicit candidate corpus instead of silently
  exposing every declared same-repository experience.

The canonical retrieval work is still delegated to ``run_swe_context_bench``. This
module validates the real-run manifest, executes each frozen batch once, and scores
all gold edges against the returned candidate and governed-admission sets.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import run_swe_context_bench as base


REAL_MANIFEST_SCHEMA_VERSION = "2.0.0"
REAL_REPORT_SCHEMA_VERSION = "1.0.0"
REAL_BENCHMARK_ID = "agent-memory-swe-context-bench-lite-real-100-edge"
PUBLIC_CORPUS_CLASS = "external_public_lite"
PUBLIC_QUERY_COUNT = 99
PUBLIC_GOLD_EDGE_COUNT = 100
PUBLIC_EXPERIENCE_COUNT = 300
PUBLIC_CONSISTENCY_QUERY_COUNT = 10
SELECTION_PROTOCOL = "gold_plus_up_to_2_same_repo_non_gold"


def _round_ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 6)


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return round((2.0 * precision * recall) / (precision + recall), 6)


def _ndcg_for_gold_set(ranked: Sequence[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    dcg = 0.0
    for rank, instance_id in enumerate(ranked[:k], start=1):
        if instance_id in gold:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_hits = min(len(gold), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return 0.0 if idcg == 0 else dcg / idcg


def _validate_real_manifest(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != REAL_MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported real 100-edge manifest")

    experiences = value.get("experiences")
    queries = value.get("queries")
    batches = value.get("batches")
    if not isinstance(experiences, list) or not experiences:
        raise ValueError("real manifest requires experiences")
    if not isinstance(queries, list) or not queries:
        raise ValueError("real manifest requires queries")
    if not isinstance(batches, list) or not batches:
        raise ValueError("real manifest requires batches")

    declared: dict[str, Mapping[str, Any]] = {}
    for row in experiences:
        if not isinstance(row, Mapping):
            raise ValueError("experience manifest row must be an object")
        instance_id = str(row.get("instance_id", "")).strip()
        repo = str(row.get("repo", "")).strip()
        path = str(row.get("path", "")).strip()
        if not instance_id or not repo or not path:
            raise ValueError("experience row requires instance_id, repo, and path")
        if instance_id in declared:
            raise ValueError(f"duplicate experience instance_id: {instance_id}")
        declared[instance_id] = row

    batch_by_id: dict[str, Mapping[str, Any]] = {}
    for row in batches:
        if not isinstance(row, Mapping):
            raise ValueError("batch manifest row must be an object")
        batch_id = str(row.get("batch_id", "")).strip()
        ids = row.get("experience_instance_ids")
        if not batch_id or not isinstance(ids, list) or not ids:
            raise ValueError("batch requires batch_id and experience_instance_ids")
        if batch_id in batch_by_id:
            raise ValueError(f"duplicate batch_id: {batch_id}")
        normalized_ids = [str(instance_id).strip() for instance_id in ids]
        if any(not instance_id for instance_id in normalized_ids):
            raise ValueError(f"batch {batch_id} contains an empty experience id")
        if len(normalized_ids) != len(set(normalized_ids)):
            raise ValueError(f"batch {batch_id} contains duplicate experience ids")
        missing = sorted(set(normalized_ids) - set(declared))
        if missing:
            raise ValueError(f"batch {batch_id} references undeclared experiences: {missing}")
        batch_by_id[batch_id] = row

    related_ids: set[str] = set()
    gold_edge_count = 0
    multi_gold_query_count = 0
    for row in queries:
        if not isinstance(row, Mapping):
            raise ValueError("query manifest row must be an object")
        related = str(row.get("related_instance_id", "")).strip()
        repo = str(row.get("repo", "")).strip()
        path = str(row.get("path", "")).strip()
        batch_id = str(row.get("batch_id", "")).strip()
        golds = row.get("gold_experience_instance_ids")
        if not related or not repo or not path or not batch_id:
            raise ValueError("query row requires related_instance_id, repo, path, and batch_id")
        if related in related_ids:
            raise ValueError(f"duplicate related_instance_id: {related}")
        related_ids.add(related)
        if batch_id not in batch_by_id:
            raise ValueError(f"query {related} references unknown batch {batch_id}")
        if not isinstance(golds, list) or not golds:
            raise ValueError(f"query {related} requires gold_experience_instance_ids")
        normalized_golds = [str(instance_id).strip() for instance_id in golds]
        if any(not instance_id for instance_id in normalized_golds):
            raise ValueError(f"query {related} contains an empty gold id")
        if len(normalized_golds) != len(set(normalized_golds)):
            raise ValueError(f"query {related} contains duplicate gold ids")
        gold_edge_count += len(normalized_golds)
        multi_gold_query_count += int(len(normalized_golds) > 1)

        batch_ids = {str(instance_id).strip() for instance_id in batch_by_id[batch_id]["experience_instance_ids"]}
        for gold in normalized_golds:
            if gold not in declared:
                raise ValueError(f"query {related} references undeclared gold experience {gold}")
            if str(declared[gold].get("repo", "")).strip() != repo:
                raise ValueError(f"query {related} gold experience {gold} is not same-repository")
            if gold not in batch_ids:
                raise ValueError(f"query {related} gold experience {gold} is absent from batch {batch_id}")

        visible_same_repo = [
            instance_id
            for instance_id in batch_ids
            if str(declared[instance_id].get("repo", "")).strip() == repo
        ]
        if not visible_same_repo:
            raise ValueError(f"query {related} has no same-repository batch corpus")

    consistency_ids = value.get("consistency_related_instance_ids", [])
    if not isinstance(consistency_ids, list):
        raise ValueError("consistency_related_instance_ids must be a list")
    normalized_consistency = [str(instance_id).strip() for instance_id in consistency_ids]
    if any(not instance_id for instance_id in normalized_consistency):
        raise ValueError("consistency_related_instance_ids contains an empty value")
    if len(normalized_consistency) != len(set(normalized_consistency)):
        raise ValueError("consistency_related_instance_ids contains duplicates")
    missing_consistency = sorted(set(normalized_consistency) - related_ids)
    if missing_consistency:
        raise ValueError(f"consistency queries are not declared: {missing_consistency}")

    corpus_class = str(value.get("corpus_class", "")).strip()
    if corpus_class == PUBLIC_CORPUS_CLASS:
        if len(experiences) != PUBLIC_EXPERIENCE_COUNT:
            raise ValueError(f"public Lite run requires exactly {PUBLIC_EXPERIENCE_COUNT} experiences")
        if len(queries) != PUBLIC_QUERY_COUNT:
            raise ValueError(f"public Lite run requires exactly {PUBLIC_QUERY_COUNT} unique queries")
        if gold_edge_count != PUBLIC_GOLD_EDGE_COUNT:
            raise ValueError(f"public Lite run requires exactly {PUBLIC_GOLD_EDGE_COUNT} gold edges")
        if multi_gold_query_count != 1:
            raise ValueError("public Lite run requires exactly one multi-gold query")
        if len(normalized_consistency) != PUBLIC_CONSISTENCY_QUERY_COUNT:
            raise ValueError(
                f"public Lite run requires exactly {PUBLIC_CONSISTENCY_QUERY_COUNT} consistency queries"
            )
        if str(value.get("selection_protocol", "")).strip() != SELECTION_PROTOCOL:
            raise ValueError(f"public Lite run requires selection_protocol={SELECTION_PROTOCOL}")

    return value


def _quality_metrics(scored_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
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

    for row in scored_rows:
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
        ndcg_1.append(_ndcg_for_gold_set(admitted, gold, 1))
        ndcg_3.append(_ndcg_for_gold_set(admitted, gold, 3))

    candidate_recall = _round_ratio(candidate_gold_hits, gold_edge_count)
    final_recall = _round_ratio(final_gold_hits, gold_edge_count)
    final_precision = _round_ratio(final_gold_hits, admitted_total)
    return {
        "query_count": len(scored_rows),
        "gold_edge_count": gold_edge_count,
        "candidate_gold_hit_count": candidate_gold_hits,
        "candidate_recall": candidate_recall,
        "candidate_experience_total": candidate_total,
        "candidate_noise_count": candidate_noise,
        "final_gold_hit_count": final_gold_hits,
        "final_admitted_recall": final_recall,
        "final_admitted_precision": final_precision,
        "final_admitted_f1": _f1(final_precision, final_recall),
        "final_admitted_experience_total": admitted_total,
        "false_admission_count": false_admissions,
        "false_refusal_count": false_refusals,
        "ndcg_at_1": round(sum(ndcg_1) / len(ndcg_1), 6) if ndcg_1 else 0.0,
        "ndcg_at_3": round(sum(ndcg_3) / len(ndcg_3), 6) if ndcg_3 else 0.0,
        "published_compatible_gold_board_named_recall": final_recall,
    }


def _manifest_input_hashes(manifest: Mapping[str, Any], benchmark_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for collection in (manifest["experiences"], manifest["queries"]):
        for row in collection:
            relative = str(row["path"])
            result[relative] = base.sha256_file((benchmark_root / relative).resolve())
    return dict(sorted(result.items()))


def run_real_100_edge_benchmark(
    *,
    manifest_path: Path,
    benchmark_root: Path,
    runtime_config_path: Path,
    agent_memory_revision: str,
    evidence_profile_path: Path = base.DEFAULT_EVIDENCE_PROFILE,
    lexical_anchor_limit: int = 3,
    consistency_repeat_count: int = 5,
) -> dict[str, Any]:
    if not agent_memory_revision:
        raise ValueError("agent_memory_revision is required")
    manifest = _validate_real_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))

    experience_by_id = {
        str(row["instance_id"]): row
        for row in manifest["experiences"]
    }
    query_by_batch: dict[str, list[Mapping[str, Any]]] = {}
    for row in manifest["queries"]:
        query_by_batch.setdefault(str(row["batch_id"]), []).append(row)

    scored_rows: list[dict[str, Any]] = []
    child_manifest_hashes: dict[str, str] = {}
    corpus_build_seconds = 0.0
    query_seconds: list[float] = []
    corpus_mutations = 0
    authority_violations = 0
    consistency_scores: list[float] = []
    consistency_ids = set(str(value) for value in manifest.get("consistency_related_instance_ids", []))

    with tempfile.TemporaryDirectory(prefix="agent-memory-swe-real-100-") as temp_root:
        temp = Path(temp_root)
        for batch in manifest["batches"]:
            batch_id = str(batch["batch_id"])
            batch_queries = query_by_batch.get(batch_id, [])
            if not batch_queries:
                raise ValueError(f"batch {batch_id} has no assigned queries")
            subset_experiences = [
                experience_by_id[str(instance_id)]
                for instance_id in batch["experience_instance_ids"]
            ]
            child_manifest = {
                "schema_version": base.MANIFEST_SCHEMA_VERSION,
                "upstream_repository": manifest.get("upstream_repository", base.UPSTREAM_REPOSITORY),
                "upstream_revision": manifest.get("upstream_revision", "unbound"),
                "fixture": f"real-100-edge batch {batch_id}",
                "corpus_class": manifest.get("corpus_class", "external"),
                "experiences": subset_experiences,
                "queries": [
                    {
                        "related_instance_id": row["related_instance_id"],
                        "repo": row["repo"],
                        "path": row["path"],
                        "gold_experience_instance_id": row["gold_experience_instance_ids"][0],
                    }
                    for row in batch_queries
                ],
                "consistency_related_instance_ids": [
                    row["related_instance_id"]
                    for row in batch_queries
                    if str(row["related_instance_id"]) in consistency_ids
                ],
            }
            child_path = temp / f"{batch_id}.json"
            child_path.write_text(json.dumps(child_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            child_report = base.run_benchmark(
                manifest_path=child_path,
                benchmark_root=benchmark_root,
                runtime_config_path=runtime_config_path,
                agent_memory_revision=agent_memory_revision,
                lexical_anchor_limit=lexical_anchor_limit,
                evidence_profile_path=evidence_profile_path,
                consistency_repeat_count=consistency_repeat_count,
                consistency_query_limit=len(child_manifest["consistency_related_instance_ids"]),
            )
            child_manifest_hashes[batch_id] = child_report["inputs"]["manifest_sha256"]
            corpus_build_seconds += float(child_report["performance"]["corpus_build_seconds_total"])
            corpus_mutations += int(child_report["governance"]["corpus_mutation_failures"])
            authority_violations += int(child_report["governance"]["route_authority_effect_violations"])

            query_lookup = {
                str(row["related_instance_id"]): row
                for row in batch_queries
            }
            for child_row in child_report["queries"]:
                related = str(child_row["related_instance_id"])
                source = query_lookup[related]
                agent_memory = child_row["agent_memory"]
                scored_rows.append(
                    {
                        "related_instance_id": related,
                        "repo": source["repo"],
                        "batch_id": batch_id,
                        "gold_experience_instance_ids": list(source["gold_experience_instance_ids"]),
                        "candidate_experience_ids": list(agent_memory["candidate_experience_ids"]),
                        "retrieved_experience_ids": list(agent_memory["retrieved_experience_ids"]),
                        "query_seconds": agent_memory["query_seconds"],
                        "corpus_immutable": child_row["corpus_immutable"],
                        "consistency": child_row["consistency"],
                    }
                )
                query_seconds.append(float(agent_memory["query_seconds"]))
                if related in consistency_ids:
                    score = child_row["consistency"]["mean_pairwise_jaccard"]
                    if score is not None:
                        consistency_scores.append(float(score))

    quality = _quality_metrics(scored_rows)
    public_shape_valid = (
        str(manifest.get("corpus_class", "")) == PUBLIC_CORPUS_CLASS
        and quality["query_count"] == PUBLIC_QUERY_COUNT
        and quality["gold_edge_count"] == PUBLIC_GOLD_EDGE_COUNT
        and len(manifest["experiences"]) == PUBLIC_EXPERIENCE_COUNT
    )
    provenance_status = str(manifest.get("fixture_provenance_status", "unbound"))
    selection_status = str(manifest.get("selection_provenance_status", "unbound"))
    comparable = (
        public_shape_valid
        and provenance_status == "exact_external_redacted_projection"
        and selection_status == "exact_external_batch_selection"
    )

    return {
        "schema_version": REAL_REPORT_SCHEMA_VERSION,
        "benchmark_id": REAL_BENCHMARK_ID,
        "agent_memory_revision": agent_memory_revision,
        "score_protocol": "swe_context_bench_lite_99_query_100_gold_edge_v2",
        "corpus": {
            "class": manifest.get("corpus_class", "external"),
            "experience_count": len(manifest["experiences"]),
            "batch_count": len(manifest["batches"]),
            "selection_protocol": manifest.get("selection_protocol", "unbound"),
        },
        "quality": quality,
        "consistency": {
            "query_count": len(consistency_scores),
            "repeat_count": consistency_repeat_count,
            "mean_pairwise_jaccard": (
                round(sum(consistency_scores) / len(consistency_scores), 6)
                if consistency_scores
                else None
            ),
            "persisted_restart_claimed": False,
        },
        "performance": {
            "corpus_build_seconds_total": round(corpus_build_seconds, 6),
            "successful_scored_query_count": len(query_seconds),
            "median_successful_scored_query_ms": (
                round(float(statistics.median(query_seconds)) * 1000.0, 3)
                if query_seconds
                else 0.0
            ),
            "timing_semantics": "batch corpus construction plus first scored Agent Memory query pass per unique related issue",
            "token_or_model_call_counts": "not_exposed_by_this_runner",
        },
        "governance": {
            "corpus_mutation_failures": corpus_mutations,
            "route_authority_effect_violations": authority_violations,
            "authority_effect": "none" if authority_violations == 0 else "violation",
            "ir_false_admission_count": quality["false_admission_count"],
            "ir_false_refusal_count": quality["false_refusal_count"],
            "ir_errors_are_not_governance_failures": True,
        },
        "inputs": {
            "manifest_sha256": base.sha256_file(manifest_path),
            "runtime_config_sha256": base.sha256_file(runtime_config_path),
            "evidence_profile_sha256": base.sha256_file(evidence_profile_path),
            "file_sha256": _manifest_input_hashes(manifest, benchmark_root),
            "batch_manifest_sha256": dict(sorted(child_manifest_hashes.items())),
        },
        "comparability": {
            "public_99_query_100_edge_shape_valid": public_shape_valid,
            "fixture_provenance_status": provenance_status,
            "selection_provenance_status": selection_status,
            "external_reference_status": (
                "protocol-comparable-inputs-bound" if comparable else "not-yet-comparable-input-provenance"
            ),
        },
        "queries": scored_rows,
        "claim_boundary": {
            "multi_gold_scoring": "gold recall and false refusal are edge-level over all declared gold past tasks",
            "precision": "admitted boards not in the query gold set are IR false admissions, not governance violations",
            "ranking": "nDCG uses binary relevance with an ideal ranking that accounts for multiple gold boards",
            "batching": "candidate corpus membership is frozen explicitly by batch in the real-run manifest",
            "no_new_retrieval_engine": True,
            "aggregate_health_score": "not_defined",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--benchmark-root", required=True, type=Path)
    parser.add_argument("--runtime-config", type=Path, default=base.DEFAULT_RUNTIME_CONFIG)
    parser.add_argument("--evidence-profile", type=Path, default=base.DEFAULT_EVIDENCE_PROFILE)
    parser.add_argument("--agent-memory-revision")
    parser.add_argument("--lexical-anchor-limit", type=int, default=3)
    parser.add_argument("--consistency-repeat-count", type=int, default=5)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = _validate_real_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    if args.validate_only:
        result: Mapping[str, Any] = {
            "valid": True,
            "schema_version": manifest["schema_version"],
            "corpus_class": manifest.get("corpus_class", "external"),
            "experience_count": len(manifest["experiences"]),
            "query_count": len(manifest["queries"]),
            "gold_edge_count": sum(len(row["gold_experience_instance_ids"]) for row in manifest["queries"]),
            "batch_count": len(manifest["batches"]),
        }
    else:
        if not args.agent_memory_revision:
            parser.error("--agent-memory-revision is required unless --validate-only is used")
        result = run_real_100_edge_benchmark(
            manifest_path=args.manifest,
            benchmark_root=args.benchmark_root,
            runtime_config_path=args.runtime_config,
            evidence_profile_path=args.evidence_profile,
            agent_memory_revision=args.agent_memory_revision,
            lexical_anchor_limit=args.lexical_anchor_limit,
            consistency_repeat_count=args.consistency_repeat_count,
        )

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
