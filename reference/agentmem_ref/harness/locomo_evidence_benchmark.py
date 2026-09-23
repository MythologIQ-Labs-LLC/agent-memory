"""LoCoMo evidence-retrieval diagnostic for Agent Memory issue #437.

This module evaluates the memory/retrieval layer directly against LoCoMo's
annotated dialogue evidence identifiers. It does *not* generate answers, use an
LLM judge, or claim the official LoCoMo question-answering score.

The upstream dataset is an external input and is never bundled by this module.
The initial compatibility target is snap-research/locomo commit
3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376, whose repository license is
Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0).
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..core import policy
from ..runtime.adapter import RecallContext
from ..runtime.query_driven_recall import (
    DeterministicQueryDrivenRecallPlanner,
    QueryDrivenRecallConfig,
)
from ..runtime.runtime_composition import ConfiguredCompositionRuntime
from ..runtime.runtime_config import validate_runtime_configuration


SCHEMA_VERSION = "1.0.0"
BENCHMARK_ID = "agent-memory-locomo-evidence-retrieval"
UPSTREAM_REPOSITORY = "snap-research/locomo"
UPSTREAM_COMMIT = "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376"
UPSTREAM_DATASET_PATH = "data/locomo10.json"
UPSTREAM_LICENSE = "CC-BY-NC-4.0"
DEFAULT_K_VALUES = (1, 5, 10, 20)
_DIA_ID = re.compile(r"D\d+:\d+")
_SESSION_KEY = re.compile(r"^session_(\d+)$")


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_evidence_ids(raw_values: Sequence[object]) -> tuple[str, ...]:
    """Normalize LoCoMo evidence cells without guessing missing identifiers.

    The public dataset contains occasional cells such as ``"D8:6; D9:17"``.
    Extracting only the documented dialogue-id grammar handles those rows while
    refusing to manufacture IDs from arbitrary text.
    """
    normalized: list[str] = []
    for value in raw_values:
        for match in _DIA_ID.findall(str(value)):
            if match not in normalized:
                normalized.append(match)
    return tuple(normalized)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _mean(values: Iterable[float]) -> float:
    rows = list(values)
    if not rows:
        return 0.0
    return round(sum(rows) / len(rows), 6)


def _validate_dataset(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("LoCoMo dataset must be a non-empty JSON list")
    samples: list[Mapping[str, Any]] = []
    for index, sample in enumerate(value):
        if not isinstance(sample, Mapping):
            raise ValueError(f"LoCoMo sample {index} must be a mapping")
        if not isinstance(sample.get("conversation"), Mapping):
            raise ValueError(f"LoCoMo sample {index} is missing conversation")
        if not isinstance(sample.get("qa"), list):
            raise ValueError(f"LoCoMo sample {index} is missing qa")
        samples.append(sample)
    return samples


def _selected_samples(
    samples: Sequence[Mapping[str, Any]],
    sample_indexes: Sequence[int] | None,
) -> list[tuple[int, Mapping[str, Any]]]:
    if sample_indexes is None:
        return list(enumerate(samples))
    selected: list[tuple[int, Mapping[str, Any]]] = []
    for index in sample_indexes:
        if index < 0 or index >= len(samples):
            raise ValueError(f"LoCoMo sample index out of range: {index}")
        selected.append((index, samples[index]))
    return selected


def _session_rows(conversation: Mapping[str, Any]) -> list[tuple[int, str, list[Mapping[str, Any]]]]:
    rows: list[tuple[int, str, list[Mapping[str, Any]]]] = []
    for key, raw_turns in conversation.items():
        match = _SESSION_KEY.match(str(key))
        if not match:
            continue
        if not isinstance(raw_turns, list):
            raise ValueError(f"LoCoMo {key} must be a list")
        turns: list[Mapping[str, Any]] = []
        for turn in raw_turns:
            if not isinstance(turn, Mapping):
                raise ValueError(f"LoCoMo {key} contains a non-mapping turn")
            turns.append(turn)
        number = int(match.group(1))
        date_time = str(conversation.get(f"session_{number}_date_time", ""))
        rows.append((number, date_time, turns))
    rows.sort(key=lambda item: item[0])
    return rows


def _turn_projection(date_time: str, turn: Mapping[str, Any]) -> str:
    speaker = str(turn.get("speaker", "")).strip()
    text = str(turn.get("text", "")).strip()
    caption = str(turn.get("blip_caption", "")).strip()
    parts = []
    if date_time:
        parts.append(f"session date: {date_time}")
    if speaker:
        parts.append(f"speaker: {speaker}")
    if text:
        parts.append(text)
    if caption:
        parts.append(f"image caption: {caption}")
    return " | ".join(parts)


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
        actor_id="agent:locomo-evidence-benchmark",
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
        purpose="locomo-evidence-retrieval",
    )


def _ranked_dialog_ids(fact_refs: Sequence[str], fact_to_dialog: Mapping[str, str]) -> list[str]:
    output: list[str] = []
    for fact_ref in fact_refs:
        dialog_ref = fact_to_dialog.get(fact_ref)
        if dialog_ref and dialog_ref not in output:
            output.append(dialog_ref)
    return output


def _question_metrics(
    ranked_dialog_ids: Sequence[str],
    evidence_ids: Sequence[str],
    k_values: Sequence[int],
) -> dict[str, Any]:
    relevant = set(evidence_ids)
    first_rank = next(
        (rank for rank, dialog_id in enumerate(ranked_dialog_ids, start=1) if dialog_id in relevant),
        None,
    )
    by_k: dict[str, dict[str, Any]] = {}
    for k in k_values:
        top = list(ranked_dialog_ids[:k])
        hits = relevant.intersection(top)
        by_k[str(k)] = {
            "hits": len(hits),
            "recall": _ratio(len(hits), len(relevant)),
            "precision": _ratio(len(hits), len(top)),
            "all_evidence_hit": relevant.issubset(set(top)),
        }
    return {
        "evidence_count": len(relevant),
        "first_relevant_rank": first_rank,
        "reciprocal_rank": 0.0 if first_rank is None else round(1.0 / first_rank, 6),
        "at_k": by_k,
    }


def _aggregate(rows: Sequence[Mapping[str, Any]], k_values: Sequence[int]) -> dict[str, Any]:
    if not rows:
        return {
            "question_count": 0,
            "evidence_count": 0,
            "mean_reciprocal_rank": 0.0,
            "mean_candidates": 0.0,
            "mean_admitted": 0.0,
            "at_k": {str(k): {"micro_recall": 0.0, "macro_recall": 0.0, "macro_precision": 0.0, "all_evidence_hit_rate": 0.0} for k in k_values},
        }

    total_evidence = sum(int(row["metrics"]["evidence_count"]) for row in rows)
    by_k: dict[str, dict[str, Any]] = {}
    for k in k_values:
        key = str(k)
        total_hits = sum(int(row["metrics"]["at_k"][key]["hits"]) for row in rows)
        by_k[key] = {
            "micro_recall": _ratio(total_hits, total_evidence),
            "macro_recall": _mean(float(row["metrics"]["at_k"][key]["recall"]) for row in rows),
            "macro_precision": _mean(float(row["metrics"]["at_k"][key]["precision"]) for row in rows),
            "all_evidence_hit_rate": _mean(1.0 if row["metrics"]["at_k"][key]["all_evidence_hit"] else 0.0 for row in rows),
        }
    return {
        "question_count": len(rows),
        "evidence_count": total_evidence,
        "mean_reciprocal_rank": _mean(float(row["metrics"]["reciprocal_rank"]) for row in rows),
        "mean_candidates": _mean(float(row["candidate_count"]) for row in rows),
        "mean_admitted": _mean(float(row["admitted_count"]) for row in rows),
        "at_k": by_k,
    }


def _category_aggregates(rows: Sequence[Mapping[str, Any]], k_values: Sequence[int]) -> dict[str, Any]:
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["category"])].append(row)
    return {str(category): _aggregate(items, k_values) for category, items in sorted(grouped.items())}


def run_benchmark(
    *,
    dataset_path: Path,
    runtime_config_path: Path,
    agent_memory_revision: str,
    upstream_commit: str = UPSTREAM_COMMIT,
    sample_indexes: Sequence[int] | None = None,
    categories: Sequence[int] | None = (1, 2, 3, 4),
    max_questions_per_sample: int | None = None,
    lexical_anchor_limit: int = 3,
    k_values: Sequence[int] = DEFAULT_K_VALUES,
) -> dict[str, Any]:
    if not agent_memory_revision:
        raise ValueError("agent_memory_revision is required")
    if max_questions_per_sample is not None and max_questions_per_sample <= 0:
        raise ValueError("max_questions_per_sample must be positive")
    normalized_k = tuple(sorted(set(int(value) for value in k_values)))
    if not normalized_k or normalized_k[0] <= 0:
        raise ValueError("k_values must contain positive integers")

    dataset_value = json.loads(dataset_path.read_text(encoding="utf-8"))
    samples = _validate_dataset(dataset_value)
    config_value = json.loads(runtime_config_path.read_text(encoding="utf-8"))
    plan = validate_runtime_configuration(config_value)
    selected_categories = None if categories is None else set(int(value) for value in categories)

    lexical_rows: list[dict[str, Any]] = []
    multi_rows: list[dict[str, Any]] = []
    empty_evidence_rows = 0
    build_seconds = 0.0
    lexical_query_seconds = 0.0
    multi_query_seconds = 0.0
    route_contributions: Counter[str] = Counter()
    unique_gain_by_route: Counter[str] = Counter()
    authority_effect_violations = 0
    refusal_count = 0

    for sample_index, sample in _selected_samples(samples, sample_indexes):
        sample_id = str(sample.get("sample_id", f"sample-{sample_index}"))
        tenant_ref = f"locomo-benchmark:{sample_index}"
        project_ref = f"locomo-sample:{sample_id}"

        with tempfile.TemporaryDirectory(prefix=f"agent-memory-locomo-{sample_index}-") as root:
            runtime = ConfiguredCompositionRuntime.create(
                Path(root),
                tenant=tenant_ref,
                plan=plan,
            )
            query_planner = DeterministicQueryDrivenRecallPlanner(
                runtime.adapter,
                config=QueryDrivenRecallConfig(lexical_anchor_limit=lexical_anchor_limit),
            )
            fact_to_dialog: dict[str, str] = {}

            build_start = time.perf_counter()
            conversation = sample["conversation"]
            for session_number, date_time, turns in _session_rows(conversation):
                session_ref = f"locomo:{sample_id}:session:{session_number}"
                for turn_number, turn in enumerate(turns, start=1):
                    dialog_id = str(turn.get("dia_id", "")).strip()
                    if not dialog_id:
                        raise ValueError(
                            f"LoCoMo sample {sample_id} session {session_number} turn {turn_number} lacks dia_id"
                        )
                    memory_ref = f"locomo:{sample_id}:dialog:{dialog_id}"
                    dialog_ref = f"locomo:{sample_id}:evidence:{dialog_id}"
                    outcome = runtime.retain(
                        _proposal(
                            proposal_id=f"locomo:{sample_id}:proposal:{dialog_id}",
                            memory_ref=memory_ref,
                            tenant_ref=tenant_ref,
                            project_ref=project_ref,
                            evidence_refs=(dialog_ref, session_ref),
                        ),
                        _turn_projection(date_time, turn),
                    )
                    if not outcome.committed or not outcome.fact_uuid:
                        raise RuntimeError(f"LoCoMo turn did not commit: {sample_id}/{dialog_id}")
                    fact_to_dialog[outcome.fact_uuid] = dialog_id
            build_seconds += time.perf_counter() - build_start

            questions_seen = 0
            for question_index, qa in enumerate(sample["qa"]):
                if not isinstance(qa, Mapping):
                    raise ValueError(f"LoCoMo sample {sample_id} qa row {question_index} must be a mapping")
                category = int(qa.get("category", 0))
                if selected_categories is not None and category not in selected_categories:
                    continue
                raw_evidence = qa.get("evidence", [])
                if not isinstance(raw_evidence, list):
                    raise ValueError(f"LoCoMo sample {sample_id} qa evidence must be a list")
                evidence_ids = normalize_evidence_ids(raw_evidence)
                if not evidence_ids:
                    empty_evidence_rows += 1
                    continue
                if max_questions_per_sample is not None and questions_seen >= max_questions_per_sample:
                    break
                questions_seen += 1

                question = str(qa.get("question", "")).strip()
                if not question:
                    raise ValueError(f"LoCoMo sample {sample_id} qa row {question_index} lacks question")
                context = RecallContext(
                    target_domain_refs=(tenant_ref, project_ref),
                    principal_ref="agent:locomo-evidence-benchmark",
                    project_ref=project_ref,
                    purpose="locomo-evidence-retrieval",
                )

                lexical_start = time.perf_counter()
                lexical = runtime.recall(question, context)
                lexical_query_seconds += time.perf_counter() - lexical_start
                lexical_ranked = _ranked_dialog_ids(lexical.admitted, fact_to_dialog)
                lexical_metrics = _question_metrics(lexical_ranked, evidence_ids, normalized_k)
                lexical_row = {
                    "sample_index": sample_index,
                    "sample_id": sample_id,
                    "question_index": question_index,
                    "category": category,
                    "question": question,
                    "raw_evidence": list(raw_evidence),
                    "normalized_evidence": list(evidence_ids),
                    "ranked_dialog_ids": lexical_ranked,
                    "candidate_count": len(lexical.candidates),
                    "admitted_count": len(lexical.admitted),
                    "refusal_count": len(lexical.refusals),
                    "metrics": lexical_metrics,
                }
                lexical_rows.append(lexical_row)

                multi_start = time.perf_counter()
                multi = query_planner.recall(question, context)
                multi_query_seconds += time.perf_counter() - multi_start
                multi_ranked = _ranked_dialog_ids(multi.ranked_admitted, fact_to_dialog)
                multi_metrics = _question_metrics(multi_ranked, evidence_ids, normalized_k)
                refusal_count += len(multi.refusals)

                provenance_by_dialog: dict[str, list[dict[str, Any]]] = {}
                for fact_ref, hits in multi.route_hits.items():
                    dialog_id = fact_to_dialog.get(fact_ref)
                    if not dialog_id:
                        continue
                    provenance_by_dialog[dialog_id] = [hit.to_dict() for hit in hits]
                    for hit in hits:
                        route_contributions[hit.route_id] += 1
                        if hit.authority_effect != "none":
                            authority_effect_violations += 1
                if multi.authority_effect != "none":
                    authority_effect_violations += 1

                max_k = normalized_k[-1]
                lexical_evidence = set(lexical_ranked[:max_k]).intersection(evidence_ids)
                multi_evidence = set(multi_ranked[:max_k]).intersection(evidence_ids)
                for gained in sorted(multi_evidence - lexical_evidence):
                    for hit in provenance_by_dialog.get(gained, []):
                        unique_gain_by_route[hit["route_id"]] += 1

                multi_rows.append(
                    {
                        "sample_index": sample_index,
                        "sample_id": sample_id,
                        "question_index": question_index,
                        "category": category,
                        "question": question,
                        "raw_evidence": list(raw_evidence),
                        "normalized_evidence": list(evidence_ids),
                        "ranked_dialog_ids": multi_ranked,
                        "candidate_count": len(multi.candidates),
                        "admitted_count": len(multi.admitted),
                        "refusal_count": len(multi.refusals),
                        "routes_executed": list(multi.routes_executed),
                        "route_provenance": provenance_by_dialog,
                        "metrics": multi_metrics,
                    }
                )

    lexical_aggregate = _aggregate(lexical_rows, normalized_k)
    multi_aggregate = _aggregate(multi_rows, normalized_k)
    max_k = str(normalized_k[-1])
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "evaluation_kind": "retrieval_evidence_diagnostic_not_official_qa_score",
        "agent_memory_revision": agent_memory_revision,
        "dataset": {
            "path": str(dataset_path),
            "sha256": sha256_file(dataset_path),
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": upstream_commit,
            "upstream_dataset_path": UPSTREAM_DATASET_PATH,
            "upstream_license": UPSTREAM_LICENSE,
            "redistributed_by_agent_memory": False,
        },
        "runtime_configuration": {
            "path": str(runtime_config_path),
            "sha256": sha256_file(runtime_config_path),
        },
        "configuration": {
            "sample_indexes": None if sample_indexes is None else list(sample_indexes),
            "categories": None if categories is None else list(categories),
            "max_questions_per_sample": max_questions_per_sample,
            "lexical_anchor_limit": lexical_anchor_limit,
            "k_values": list(normalized_k),
        },
        "lexical_only": {
            "aggregate": lexical_aggregate,
            "by_category": _category_aggregates(lexical_rows, normalized_k),
            "questions": lexical_rows,
        },
        "query_driven_multi_route": {
            "aggregate": multi_aggregate,
            "by_category": _category_aggregates(multi_rows, normalized_k),
            "questions": multi_rows,
            "route_contribution_counts": dict(sorted(route_contributions.items())),
            "unique_evidence_gain_by_route_at_max_k": dict(sorted(unique_gain_by_route.items())),
        },
        "comparison": {
            "evidence_micro_recall_delta_at_max_k": round(
                multi_aggregate["at_k"][max_k]["micro_recall"]
                - lexical_aggregate["at_k"][max_k]["micro_recall"],
                6,
            ),
            "mean_reciprocal_rank_delta": round(
                multi_aggregate["mean_reciprocal_rank"] - lexical_aggregate["mean_reciprocal_rank"],
                6,
            ),
        },
        "governance": {
            "query_driven_refusal_count": refusal_count,
            "route_authority_effect_violations": authority_effect_violations,
        },
        "timing_diagnostic_seconds": {
            "memory_build": round(build_seconds, 6),
            "lexical_queries": round(lexical_query_seconds, 6),
            "query_driven_queries": round(multi_query_seconds, 6),
            "not_comparable_to_jev_mem_paper_timing": True,
        },
        "excluded_empty_evidence_questions": empty_evidence_rows,
        "limitations": [
            "retrieval evidence diagnostic only; no answer generation or LLM-as-a-judge",
            "not the official LoCoMo QA score and not directly comparable to Jev-Mem's reported 0.777 answer score",
            "query-driven relational expansion is a deterministic baseline rather than learned/System-One route control",
            "session provenance connects turns from the same source session and can amplify irrelevant candidates",
            "timing includes Python reference-runtime overhead and uses a different protocol from published Jev-Mem timing",
        ],
    }
