"""Deterministic RC retrieval-quality benchmark for issue #435.

This harness compares the lexical compatibility path with Agent Memory's
composed multi-route recall over identical retained state. Retrieval usefulness
and governance safety are reported separately. The benchmark is intentionally
synthetic and does not claim LoCoMo, LongMemEval, or answer-quality parity.

Issue #456 optionally injects Agent Memory's native semantic/vector candidate
route into the same benchmark. Issue #461 optionally adds a relation-bearing
fixture and a controlled typed-graph lane over the same retained corpus. The
graph lane is reported separately from the older multi-route baseline so new
retrieval depth does not rewrite historical evidence.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from ..core import policy
from ..runtime.adapter import RecallContext
from ..runtime.recall_control import (
    ControlledRecallPlanner,
    GraphTraversalSpec,
    NativeTypedGraphCandidateRetriever,
    TYPED_GRAPH_ROUTE,
)
from ..runtime.runtime_composition import ConfiguredCompositionRuntime
from ..runtime.runtime_config import validate_runtime_configuration
from ..runtime.vector_retrieval import NativeVectorCandidateRetriever, SEMANTIC_VECTOR_ROUTE
from ..state.substrate import TypedRelation

SCHEMA_VERSION = "1.0.0"
BENCHMARK_ID = "agent-memory-rc-retrieval-quality"


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _validate_fixture(fixture: Mapping[str, Any]) -> None:
    if fixture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported retrieval benchmark fixture schema")
    if fixture.get("benchmark_id") != BENCHMARK_ID:
        raise ValueError("unexpected retrieval benchmark id")
    if not fixture.get("benchmark_version"):
        raise ValueError("retrieval benchmark fixture requires benchmark_version")
    if not fixture.get("tenant_ref") or not fixture.get("default_project_ref"):
        raise ValueError("retrieval benchmark fixture requires tenant and project")
    memories = fixture.get("memories")
    cases = fixture.get("cases")
    if not isinstance(memories, list) or not memories:
        raise ValueError("retrieval benchmark requires memories")
    if not isinstance(cases, list) or not cases:
        raise ValueError("retrieval benchmark requires cases")

    refs: set[str] = set()
    for item in memories:
        if not isinstance(item, Mapping):
            raise ValueError("benchmark memory must be a mapping")
        memory_ref = str(item.get("memory_ref", ""))
        if not memory_ref or memory_ref in refs:
            raise ValueError("benchmark memory refs must be non-empty and unique")
        refs.add(memory_ref)
        if not item.get("fact_text") or not item.get("project_ref"):
            raise ValueError(f"benchmark memory {memory_ref} is incomplete")
        evidence_refs = item.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ValueError(f"benchmark memory {memory_ref} requires evidence_refs")

    relations = fixture.get("relations", [])
    if not isinstance(relations, list):
        raise ValueError("benchmark relations must be a list")
    relation_ids: set[str] = set()
    for relation in relations:
        if not isinstance(relation, Mapping):
            raise ValueError("benchmark relation must be a mapping")
        relation_id = str(relation.get("relation_id", ""))
        source = str(relation.get("source_memory_ref", ""))
        target = str(relation.get("target_memory_ref", ""))
        relation_type = str(relation.get("relation_type", ""))
        if not relation_id or relation_id in relation_ids:
            raise ValueError("benchmark relation ids must be non-empty and unique")
        relation_ids.add(relation_id)
        if source not in refs or target not in refs:
            raise ValueError(f"benchmark relation {relation_id} references unknown memory")
        if not relation_type:
            raise ValueError(f"benchmark relation {relation_id} requires relation_type")
        evidence_refs = relation.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            raise ValueError(f"benchmark relation {relation_id} evidence_refs must be a list")
        weight = float(relation.get("retrieval_weight", 1.0))
        if weight < 0.0 or weight > 1.0:
            raise ValueError(f"benchmark relation {relation_id} retrieval_weight is out of range")

    graph_profile = fixture.get("graph_profile", {})
    if graph_profile and not isinstance(graph_profile, Mapping):
        raise ValueError("benchmark graph_profile must be a mapping")

    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("benchmark case must be a mapping")
        case_id = str(case.get("case_id", ""))
        if not case_id or case_id in case_ids:
            raise ValueError("benchmark case ids must be non-empty and unique")
        case_ids.add(case_id)
        relevant = set(case.get("relevant_memory_refs", []))
        forbidden = set(case.get("forbidden_memory_refs", []))
        seeds = set(case.get("logical_memory_refs", []))
        unknown = (relevant | forbidden | seeds) - refs
        if unknown:
            raise ValueError(f"benchmark case {case_id} references unknown memories: {sorted(unknown)}")
        if relevant & forbidden:
            raise ValueError(f"benchmark case {case_id} cannot mark a memory relevant and forbidden")


def _proposal(
    *,
    proposal_id: str,
    memory_ref: str,
    tenant_ref: str,
    project_ref: str,
    purpose: str,
    evidence_refs: tuple[str, ...],
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:rc-retrieval-benchmark",
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
        purpose=purpose,
    )


def _logical_result(
    *,
    candidates: list[str],
    admitted: list[str],
    refusals: Mapping[str, str],
    ranked: list[str],
    fact_to_memory: Mapping[str, str],
) -> dict[str, Any]:
    def logical(values: list[str]) -> list[str]:
        return [fact_to_memory.get(value, f"unknown-fact:{value}") for value in values]

    return {
        "candidates": logical(candidates),
        "admitted": logical(admitted),
        "ranked_admitted": logical(ranked),
        "refusals": {
            fact_to_memory.get(candidate, f"unknown-fact:{candidate}"): reason
            for candidate, reason in sorted(refusals.items())
        },
    }


def _case_metrics(result: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    relevant = set(case["relevant_memory_refs"])
    forbidden = set(case.get("forbidden_memory_refs", []))
    candidates = list(result["candidates"])
    admitted = list(result["admitted"])
    ranked = list(result["ranked_admitted"])

    candidate_relevant = relevant.intersection(candidates)
    admitted_relevant = relevant.intersection(admitted)
    first_relevant_rank = next(
        (index for index, ref in enumerate(ranked, start=1) if ref in relevant),
        None,
    )
    forbidden_admitted = sorted(forbidden.intersection(admitted))
    forbidden_ranked = sorted(forbidden.intersection(ranked))
    return {
        "relevant_total": len(relevant),
        "candidate_relevant_found": len(candidate_relevant),
        "admitted_relevant_found": len(admitted_relevant),
        "candidate_total": len(candidates),
        "admitted_total": len(admitted),
        "candidate_recall": _ratio(len(candidate_relevant), len(relevant)),
        "admitted_recall": _ratio(len(admitted_relevant), len(relevant)),
        "admitted_precision": _ratio(len(admitted_relevant), len(admitted)),
        "first_relevant_rank": first_relevant_rank,
        "reciprocal_rank": 0.0 if first_relevant_rank is None else round(1.0 / first_relevant_rank, 6),
        "candidate_noise": len([ref for ref in candidates if ref not in relevant]),
        "forbidden_admitted": forbidden_admitted,
        "forbidden_ranked": forbidden_ranked,
    }


def _aggregate(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    relevant_total = sum(row["metrics"]["relevant_total"] for row in case_rows)
    candidate_relevant = sum(row["metrics"]["candidate_relevant_found"] for row in case_rows)
    admitted_relevant = sum(row["metrics"]["admitted_relevant_found"] for row in case_rows)
    candidate_total = sum(row["metrics"]["candidate_total"] for row in case_rows)
    admitted_total = sum(row["metrics"]["admitted_total"] for row in case_rows)
    reciprocal_rank_sum = sum(float(row["metrics"]["reciprocal_rank"]) for row in case_rows)
    forbidden_admitted = sum(len(row["metrics"]["forbidden_admitted"]) for row in case_rows)
    forbidden_ranked = sum(len(row["metrics"]["forbidden_ranked"]) for row in case_rows)
    return {
        "case_count": len(case_rows),
        "relevant_total": relevant_total,
        "candidate_total": candidate_total,
        "admitted_total": admitted_total,
        "candidate_recall": _ratio(candidate_relevant, relevant_total),
        "admitted_recall": _ratio(admitted_relevant, relevant_total),
        "admitted_precision": _ratio(admitted_relevant, admitted_total),
        "mean_reciprocal_rank": _ratio(int(round(reciprocal_rank_sum * 1_000_000)), len(case_rows) * 1_000_000),
        "candidate_noise": sum(row["metrics"]["candidate_noise"] for row in case_rows),
        "forbidden_admission_failures": forbidden_admitted,
        "forbidden_ranked_failures": forbidden_ranked,
    }


def _vector_profile(
    vector_retriever: NativeVectorCandidateRetriever | None,
    *,
    candidate_limit: int,
) -> dict[str, Any] | None:
    if vector_retriever is None:
        return None
    spec = vector_retriever.spec
    return {
        "route_id": SEMANTIC_VECTOR_ROUTE,
        "representation_ref": spec.representation_ref,
        "representation_version": spec.representation_version,
        "representation_config_digest": spec.config_digest,
        "vector_dimension": spec.dimensions,
        "similarity_metric": "cosine",
        "minimum_similarity": vector_retriever.minimum_similarity,
        "candidate_limit": candidate_limit,
        "rebuild_posture": spec.rebuild_posture,
        "deterministic_rebuild": spec.deterministic_rebuild,
        "authority_effect": "none",
    }


def _graph_spec(fixture: Mapping[str, Any]) -> GraphTraversalSpec:
    value = fixture.get("graph_profile", {})
    if not isinstance(value, Mapping):
        raise ValueError("benchmark graph_profile must be a mapping")
    return GraphTraversalSpec(
        max_depth=int(value.get("max_depth", 2)),
        max_fanout=int(value.get("max_fanout", 8)),
        relation_types=tuple(str(item) for item in value.get("relation_types", [])),
        direction=str(value.get("direction", "outgoing")),
        min_path_score=float(value.get("min_path_score", 0.0)),
    )


def _graph_profile(spec: GraphTraversalSpec) -> dict[str, Any]:
    return {
        "route_id": TYPED_GRAPH_ROUTE,
        "max_depth": spec.max_depth,
        "max_fanout": spec.max_fanout,
        "relation_types": list(spec.relation_types),
        "direction": spec.direction,
        "minimum_path_score": spec.min_path_score,
        "candidate_limit_policy": "deterministic_controller_bounded_max_24",
        "authority_effect": "none",
    }


def run_benchmark(
    *,
    fixture_path: Path,
    runtime_config_path: Path,
    agent_memory_revision: str,
    vector_retriever: NativeVectorCandidateRetriever | None = None,
) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    _validate_fixture(fixture)
    config_value = json.loads(runtime_config_path.read_text(encoding="utf-8"))
    plan = validate_runtime_configuration(config_value)

    tenant_ref = str(fixture["tenant_ref"])
    default_project_ref = str(fixture["default_project_ref"])
    purpose = str(fixture.get("purpose", "retrieval-quality-evaluation"))
    relation_values = list(fixture.get("relations", []))

    with tempfile.TemporaryDirectory(prefix="agent-memory-retrieval-benchmark-") as root:
        runtime = ConfiguredCompositionRuntime.create(
            Path(root),
            tenant=tenant_ref,
            plan=plan,
            vector_retriever=vector_retriever,
        )
        vector_profile = _vector_profile(
            vector_retriever,
            candidate_limit=runtime.recall_planner.vector_candidate_limit,
        )
        memory_to_fact: dict[str, str] = {}
        fact_to_memory: dict[str, str] = {}

        for index, item in enumerate(fixture["memories"], start=1):
            memory_ref = str(item["memory_ref"])
            outcome = runtime.retain(
                _proposal(
                    proposal_id=f"benchmark-proposal-{index:03d}",
                    memory_ref=memory_ref,
                    tenant_ref=tenant_ref,
                    project_ref=str(item["project_ref"]),
                    purpose=purpose,
                    evidence_refs=tuple(str(value) for value in item["evidence_refs"]),
                ),
                str(item["fact_text"]),
            )
            if not outcome.committed or not outcome.fact_uuid:
                raise RuntimeError(f"benchmark memory did not commit: {memory_ref}")
            memory_to_fact[memory_ref] = outcome.fact_uuid
            fact_to_memory[outcome.fact_uuid] = memory_ref

        substrate = runtime.adapter.checkpoint_substrate()
        for item in fixture["memories"]:
            if not item.get("invalidate_after_retain", False):
                continue
            fact_ref = memory_to_fact[str(item["memory_ref"])]
            substrate.invalidate_fact(
                fact_ref,
                invalid_at="2026-09-23T13:00:00Z",
                expired_at="2026-09-23T13:00:01Z",
            )

        graph_retriever: NativeTypedGraphCandidateRetriever | None = None
        graph_profile: dict[str, Any] | None = None
        if relation_values:
            for relation in relation_values:
                substrate.write_relation(
                    TypedRelation(
                        relation_id=str(relation["relation_id"]),
                        source_uuid=memory_to_fact[str(relation["source_memory_ref"])],
                        target_uuid=memory_to_fact[str(relation["target_memory_ref"])],
                        relation_type=str(relation["relation_type"]),
                        group_id=tenant_ref,
                        evidence_refs=tuple(str(item) for item in relation.get("evidence_refs", [])),
                        retrieval_weight=float(relation.get("retrieval_weight", 1.0)),
                        valid_at=str(relation.get("valid_at", "2026-09-23T12:00:00Z")),
                        created_at=str(relation.get("created_at", "2026-09-23T12:00:00Z")),
                    )
                )
            spec = _graph_spec(fixture)
            graph_retriever = NativeTypedGraphCandidateRetriever(spec)
            graph_profile = _graph_profile(spec)

        controlled_planner = (
            ControlledRecallPlanner(
                runtime.adapter,
                vector_retriever=vector_retriever,
                graph_retriever=graph_retriever,
            )
            if graph_retriever is not None
            else None
        )

        lexical_rows: list[dict[str, Any]] = []
        multi_rows: list[dict[str, Any]] = []
        controlled_rows: list[dict[str, Any]] = []
        route_contributions: Counter[str] = Counter()
        unique_gain_by_route: Counter[str] = Counter()
        controlled_route_contributions: Counter[str] = Counter()
        controlled_unique_gain_over_multi: Counter[str] = Counter()
        authority_effect_violations = 0
        controlled_authority_effect_violations = 0

        for case in fixture["cases"]:
            project_ref = str(case.get("project_ref", default_project_ref))
            context = RecallContext(
                target_domain_refs=(tenant_ref, project_ref),
                principal_ref="agent:rc-retrieval-benchmark",
                project_ref=project_ref,
                purpose=purpose,
            )
            query = str(case["query"])
            logical_refs = tuple(str(value) for value in case.get("logical_memory_refs", []))

            lexical = runtime.recall(query, context)
            lexical_result = _logical_result(
                candidates=list(lexical.candidates),
                admitted=list(lexical.admitted),
                refusals=lexical.refusals,
                ranked=list(lexical.admitted),
                fact_to_memory=fact_to_memory,
            )
            lexical_metrics = _case_metrics(lexical_result, case)
            lexical_rows.append(
                {
                    "case_id": case["case_id"],
                    "result": lexical_result,
                    "metrics": lexical_metrics,
                }
            )

            multi = runtime.multi_route_recall(
                query,
                context,
                logical_memory_refs=logical_refs,
            )
            multi_result = _logical_result(
                candidates=list(multi.candidates),
                admitted=list(multi.admitted),
                refusals=multi.refusals,
                ranked=list(multi.ranked_admitted),
                fact_to_memory=fact_to_memory,
            )
            multi_metrics = _case_metrics(multi_result, case)

            logical_provenance: dict[str, list[dict[str, Any]]] = {}
            for candidate_ref, hits in sorted(multi.route_hits.items()):
                logical_ref = fact_to_memory.get(candidate_ref, f"unknown-fact:{candidate_ref}")
                logical_provenance[logical_ref] = [hit.to_dict() for hit in hits]
                for hit in hits:
                    route_contributions[hit.route_id] += 1
                    if hit.authority_effect != "none":
                        authority_effect_violations += 1
            if multi.authority_effect != "none":
                authority_effect_violations += 1

            lexical_relevant = set(case["relevant_memory_refs"]).intersection(lexical_result["admitted"])
            multi_relevant = set(case["relevant_memory_refs"]).intersection(multi_result["admitted"])
            for gained_ref in sorted(multi_relevant - lexical_relevant):
                for hit in logical_provenance.get(gained_ref, []):
                    unique_gain_by_route[str(hit["route_id"])] += 1

            multi_rows.append(
                {
                    "case_id": case["case_id"],
                    "result": multi_result,
                    "metrics": multi_metrics,
                    "routes_executed": list(multi.routes_executed),
                    "route_provenance": logical_provenance,
                }
            )

            if controlled_planner is not None:
                controlled = controlled_planner.recall(
                    query,
                    context,
                    logical_memory_refs=logical_refs,
                )
                controlled_result = _logical_result(
                    candidates=list(controlled.candidates),
                    admitted=list(controlled.admitted),
                    refusals=controlled.recall.refusals,
                    ranked=list(controlled.ranked_admitted),
                    fact_to_memory=fact_to_memory,
                )
                controlled_metrics = _case_metrics(controlled_result, case)
                controlled_provenance: dict[str, list[dict[str, Any]]] = {}
                for candidate_ref, hits in sorted(controlled.recall.route_hits.items()):
                    logical_ref = fact_to_memory.get(candidate_ref, f"unknown-fact:{candidate_ref}")
                    controlled_provenance[logical_ref] = [hit.to_dict() for hit in hits]
                    for hit in hits:
                        controlled_route_contributions[hit.route_id] += 1
                        if hit.authority_effect != "none":
                            controlled_authority_effect_violations += 1
                if controlled.authority_effect != "none":
                    controlled_authority_effect_violations += 1

                graph_paths: dict[str, dict[str, Any]] = {}
                for candidate_ref, hit in sorted(controlled.graph_candidate_hits.items()):
                    logical_ref = fact_to_memory.get(candidate_ref, f"unknown-fact:{candidate_ref}")
                    graph_paths[logical_ref] = {
                        "seed_memory_ref": fact_to_memory.get(
                            hit.seed_candidate_ref,
                            f"unknown-fact:{hit.seed_candidate_ref}",
                        ),
                        "path_memory_refs": [
                            fact_to_memory.get(value, f"unknown-fact:{value}")
                            for value in hit.path_refs
                        ],
                        "relation_ids": list(hit.relation_ids),
                        "relation_types": list(hit.relation_types),
                        "relation_evidence_refs": list(hit.relation_evidence_refs),
                        "relation_weights": list(hit.relation_weights),
                        "path_score": hit.path_score,
                        "hop_count": hit.hop_count,
                        "authority_effect": hit.authority_effect,
                    }
                    if hit.authority_effect != "none":
                        controlled_authority_effect_violations += 1

                controlled_relevant = set(case["relevant_memory_refs"]).intersection(
                    controlled_result["admitted"]
                )
                for gained_ref in sorted(controlled_relevant - multi_relevant):
                    for hit in controlled_provenance.get(gained_ref, []):
                        controlled_unique_gain_over_multi[str(hit["route_id"])] += 1

                controlled_rows.append(
                    {
                        "case_id": case["case_id"],
                        "result": controlled_result,
                        "metrics": controlled_metrics,
                        "routes_executed": list(controlled.recall.routes_executed),
                        "route_candidate_counts": dict(sorted(controlled.route_candidate_counts.items())),
                        "route_provenance": controlled_provenance,
                        "typed_graph_paths": graph_paths,
                    }
                )

    lexical_aggregate = _aggregate(lexical_rows)
    multi_aggregate = _aggregate(multi_rows)
    systems: dict[str, Any] = {
        "lexical_only": {
            "cases": lexical_rows,
            "aggregate": lexical_aggregate,
        },
        "multi_route": {
            "cases": multi_rows,
            "aggregate": multi_aggregate,
            "route_contribution_counts": dict(sorted(route_contributions.items())),
            "unique_recall_gain_by_route": dict(sorted(unique_gain_by_route.items())),
        },
    }
    comparison: dict[str, Any] = {
        "candidate_recall_delta": round(
            multi_aggregate["candidate_recall"] - lexical_aggregate["candidate_recall"], 6
        ),
        "admitted_recall_delta": round(
            multi_aggregate["admitted_recall"] - lexical_aggregate["admitted_recall"], 6
        ),
        "admitted_precision_delta": round(
            multi_aggregate["admitted_precision"] - lexical_aggregate["admitted_precision"], 6
        ),
        "mean_reciprocal_rank_delta": round(
            multi_aggregate["mean_reciprocal_rank"] - lexical_aggregate["mean_reciprocal_rank"], 6
        ),
        "candidate_amplification": multi_aggregate["candidate_total"] - lexical_aggregate["candidate_total"],
    }
    governance: dict[str, Any] = {
        "lexical_forbidden_admission_failures": lexical_aggregate["forbidden_admission_failures"],
        "multi_route_forbidden_admission_failures": multi_aggregate["forbidden_admission_failures"],
        "multi_route_forbidden_ranked_failures": multi_aggregate["forbidden_ranked_failures"],
        "route_authority_effect_violations": authority_effect_violations,
    }

    if controlled_rows:
        controlled_aggregate = _aggregate(controlled_rows)
        systems["controlled_typed_graph"] = {
            "cases": controlled_rows,
            "aggregate": controlled_aggregate,
            "route_contribution_counts": dict(sorted(controlled_route_contributions.items())),
            "unique_recall_gain_over_multi_route_by_route": dict(
                sorted(controlled_unique_gain_over_multi.items())
            ),
        }
        comparison["typed_graph_candidate_recall_delta_over_multi_route"] = round(
            controlled_aggregate["candidate_recall"] - multi_aggregate["candidate_recall"], 6
        )
        comparison["typed_graph_admitted_recall_delta_over_multi_route"] = round(
            controlled_aggregate["admitted_recall"] - multi_aggregate["admitted_recall"], 6
        )
        comparison["typed_graph_candidate_amplification_over_multi_route"] = (
            controlled_aggregate["candidate_total"] - multi_aggregate["candidate_total"]
        )
        governance["controlled_typed_graph_forbidden_admission_failures"] = controlled_aggregate[
            "forbidden_admission_failures"
        ]
        governance["controlled_typed_graph_forbidden_ranked_failures"] = controlled_aggregate[
            "forbidden_ranked_failures"
        ]
        governance["controlled_typed_graph_authority_effect_violations"] = (
            controlled_authority_effect_violations
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "benchmark_version": fixture["benchmark_version"],
        "agent_memory_revision": agent_memory_revision,
        "fixture": {
            "path": str(fixture_path),
            "sha256": sha256_file(fixture_path),
            "memory_count": len(fixture["memories"]),
            "relation_count": len(relation_values),
            "case_count": len(fixture["cases"]),
        },
        "runtime_configuration": {
            "path": str(runtime_config_path),
            "sha256": sha256_file(runtime_config_path),
        },
        "vector_route": vector_profile,
        "typed_graph_route": graph_profile,
        "systems": systems,
        "comparison": comparison,
        "governance": governance,
        "limitations": list(fixture.get("limitations", [])),
    }
    return report