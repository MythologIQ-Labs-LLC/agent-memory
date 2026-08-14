"""Provider-neutral CodeGenome/Graphify qualification normalizer for #300.

The module preserves provider-native outputs as separate artifacts and normalizes
only the tiny factual surface shared by the qualification fixture. It does not
rank products and cannot grant Agent Memory authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .qualification import (
    AdapterResult,
    QualificationRuntime,
    QualificationSubject,
    qualification_from_adapter_results,
)

CODEGENOME_COMMIT = "d2578729a46d495369bd7613845002d50cf20f4c"
GRAPHIFY_RELEASE = "v0.9.43"
GRAPHIFY_COMMIT = "7281f27eac568f77f50910f59f84543458f5dfd1"
PROFILE_ID = "code-graph-traversal-currentness"
PROFILE_VERSION = "1.0.0"

_LINE = re.compile(r"^line (\d+):(\d+)$")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def fixture_digest(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: str(item)):
        digest.update(str(path).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _codegenome_start_lines(path: Path) -> set[int]:
    payload = _load(path)
    if not isinstance(payload, list):
        raise ValueError(f"CodeGenome query output must be a list: {path}")
    lines: set[int] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        location = item.get("node")
        if not isinstance(location, str):
            continue
        match = _LINE.fullmatch(location)
        if match:
            lines.add(int(match.group(1)))
    return lines


def _clean_label(label: str) -> str:
    value = label.strip()
    if value.startswith("."):
        value = value[1:]
    if value.endswith("()"):
        value = value[:-2]
    return value


def _graphify_call_facts(path: Path) -> set[tuple[str, str, str]]:
    payload = _load(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Graphify graph output must be an object: {path}")
    nodes = {node.get("id"): node for node in payload.get("nodes", []) if isinstance(node, dict) and node.get("id")}
    facts: set[tuple[str, str, str]] = set()
    for edge in payload.get("edges", []):
        if not isinstance(edge, dict) or edge.get("relation") != "calls":
            continue
        source = nodes.get(edge.get("source"))
        target = nodes.get(edge.get("target"))
        if not source or not target:
            continue
        source_file = str(edge.get("source_file") or source.get("source_file") or "")
        facts.add(
            (
                Path(source_file).name,
                _clean_label(str(source.get("label", ""))),
                _clean_label(str(target.get("label", ""))),
            )
        )
    return facts


def _checks(mapping: dict[str, bool], evidence_ref: str) -> tuple[tuple[str, bool, str], ...]:
    return tuple((name, passed, evidence_ref) for name, passed in mapping.items())


def _runtime(agent_memory_commit: str, all_fixture_paths: list[Path]) -> QualificationRuntime:
    configuration = {
        "profile": f"{PROFILE_ID}@{PROFILE_VERSION}",
        "codegenome": CODEGENOME_COMMIT,
        "graphify": f"{GRAPHIFY_RELEASE}@{GRAPHIFY_COMMIT}",
        "update_posture": "full_rebuild",
    }
    configuration_digest = sha256_bytes(
        json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return QualificationRuntime(
        configuration_digest=configuration_digest,
        fixture_id="component-qualification-code-graph-v1-v2",
        fixture_digest=fixture_digest(all_fixture_paths),
        dependency_refs=(
            f"CodeGenome@{CODEGENOME_COMMIT}",
            f"Graphify@{GRAPHIFY_RELEASE}:{GRAPHIFY_COMMIT}",
        ),
        runtime_refs=(f"agent-memory@{agent_memory_commit}", "python:3.12", "rust:stable"),
    )


def build_qualification_report(
    *,
    agent_memory_commit: str,
    fixture_paths: list[Path],
    codegenome_v1_main_downstream: Path,
    codegenome_v1_main_upstream: Path,
    codegenome_v1_decoy_downstream: Path,
    codegenome_v2_main_downstream: Path,
    codegenome_v2_main_upstream: Path,
    codegenome_v2_decoy_downstream: Path,
    graphify_v1: Path,
    graphify_v2: Path,
) -> dict[str, Any]:
    runtime = _runtime(agent_memory_commit, fixture_paths)

    cg_v1_down = _codegenome_start_lines(codegenome_v1_main_downstream)
    cg_v1_up = _codegenome_start_lines(codegenome_v1_main_upstream)
    cg_v1_decoy = _codegenome_start_lines(codegenome_v1_decoy_downstream)
    cg_v2_down = _codegenome_start_lines(codegenome_v2_main_downstream)
    cg_v2_up = _codegenome_start_lines(codegenome_v2_main_upstream)
    cg_v2_decoy = _codegenome_start_lines(codegenome_v2_decoy_downstream)

    codegenome_checks = {
        "v1_main_target_identity": 5 in cg_v1_down,
        "v1_main_downstream_leaf": 1 in cg_v1_down,
        "v1_main_downstream_excludes_top": 9 not in cg_v1_down,
        "v1_main_downstream_excludes_decoy_leaf": 12 not in cg_v1_down,
        "v1_main_upstream_top": 9 in cg_v1_up,
        "v1_main_upstream_excludes_leaf": 1 not in cg_v1_up,
        "v1_decoy_downstream_decoy_leaf": 12 in cg_v1_decoy,
        "v1_decoy_excludes_main_leaf": 1 not in cg_v1_decoy,
        "v2_main_target_identity": 5 in cg_v2_down,
        "v2_main_downstream_replacement_leaf": 13 in cg_v2_down,
        "v2_main_downstream_excludes_old_leaf": 1 not in cg_v2_down,
        "v2_main_downstream_excludes_decoy_leaf": 12 not in cg_v2_down,
        "v2_main_upstream_top": 9 in cg_v2_up,
        "v2_main_upstream_excludes_replacement_leaf": 13 not in cg_v2_up,
        "v2_decoy_downstream_decoy_leaf": 12 in cg_v2_decoy,
        "v2_decoy_excludes_replacement_leaf": 13 not in cg_v2_decoy,
        "full_rebuild_currentness": 1 in cg_v1_down and 1 not in cg_v2_down and 13 in cg_v2_down,
    }

    graphify_v1_facts = _graphify_call_facts(graphify_v1)
    graphify_v2_facts = _graphify_call_facts(graphify_v2)
    graphify_checks = {
        "v1_main_middle_calls_leaf": ("main.rs", "middle", "leaf") in graphify_v1_facts,
        "v1_main_top_calls_middle": ("main.rs", "top", "middle") in graphify_v1_facts,
        "v1_decoy_middle_calls_decoy_leaf": ("decoy.rs", "middle", "decoy_leaf") in graphify_v1_facts,
        "v2_main_middle_calls_replacement_leaf": ("main.rs", "middle", "replacement_leaf") in graphify_v2_facts,
        "v2_main_top_calls_middle": ("main.rs", "top", "middle") in graphify_v2_facts,
        "v2_decoy_middle_calls_decoy_leaf": ("decoy.rs", "middle", "decoy_leaf") in graphify_v2_facts,
        "v2_excludes_old_main_edge": ("main.rs", "middle", "leaf") not in graphify_v2_facts,
        "full_rebuild_currentness": (
            ("main.rs", "middle", "leaf") in graphify_v1_facts
            and ("main.rs", "middle", "leaf") not in graphify_v2_facts
            and ("main.rs", "middle", "replacement_leaf") in graphify_v2_facts
        ),
    }

    cg_subject = QualificationSubject(
        component_id="codegenome",
        component_version=CODEGENOME_COMMIT,
        implementation_ref=f"MythologIQ-Labs-LLC/CodeGenome@{CODEGENOME_COMMIT}",
        capability_id="code_graph_traversal",
        capability_version="1.0",
        adapter_id="codegenome-cli",
        adapter_version="1.0.0",
        qualification_profile_id=PROFILE_ID,
        qualification_profile_version=PROFILE_VERSION,
    )
    graphify_subject = QualificationSubject(
        component_id="graphify",
        component_version=GRAPHIFY_RELEASE,
        implementation_ref=f"Graphify-Labs/graphify@{GRAPHIFY_COMMIT}",
        capability_id="code_graph_traversal",
        capability_version="1.0",
        adapter_id="graphify-cli",
        adapter_version="1.0.0",
        qualification_profile_id=PROFILE_ID,
        qualification_profile_version=PROFILE_VERSION,
    )

    cg_raw = (
        codegenome_v1_main_downstream,
        codegenome_v1_main_upstream,
        codegenome_v1_decoy_downstream,
        codegenome_v2_main_downstream,
        codegenome_v2_main_upstream,
        codegenome_v2_decoy_downstream,
    )
    graphify_raw = (graphify_v1, graphify_v2)

    cg_result = AdapterResult(
        subject=cg_subject,
        operation="code_graph_traversal_v1_v2_full_rebuild",
        runtime_identity=f"CodeGenome@{CODEGENOME_COMMIT}",
        input_refs=("fixture:v1", "fixture:v2"),
        raw_provider_refs=tuple(str(path) for path in cg_raw),
        normalized_refs=("normalized:codegenome-code-graph",),
        currentness="v1_historical_v2_current_full_rebuild",
        failure_result="none",
        trace_ref="qualification:codegenome",
    )
    graphify_result = AdapterResult(
        subject=graphify_subject,
        operation="code_graph_traversal_v1_v2_full_rebuild",
        runtime_identity=f"Graphify@{GRAPHIFY_RELEASE}:{GRAPHIFY_COMMIT}",
        input_refs=("fixture:v1", "fixture:v2"),
        raw_provider_refs=tuple(str(path) for path in graphify_raw),
        normalized_refs=("normalized:graphify-code-graph",),
        currentness="v1_historical_v2_current_full_rebuild",
        failure_result="none",
        trace_ref="qualification:graphify",
    )

    cg_passed = all(codegenome_checks.values())
    graphify_passed = all(graphify_checks.values())
    cg_record = qualification_from_adapter_results(
        subject=cg_subject,
        runtime=runtime,
        license_id="MIT",
        license_ref=f"MythologIQ-Labs-LLC/CodeGenome/LICENSE@{CODEGENOME_COMMIT}",
        use_posture="runtime_allowed",
        results=(cg_result,),
        checks=_checks(codegenome_checks, "normalized:codegenome-code-graph"),
        artifact_digests=tuple(sha256_file(path) for path in cg_raw),
        maturity_before="runtime_wired",
        profile_maturity_ceiling="evidence_proven",
        earned_maturity="runtime_wired" if not cg_passed else "evidence_proven",
        limitations=("Currentness in this slice is proven through explicit full rebuild, not incremental update.",),
    )
    graphify_record = qualification_from_adapter_results(
        subject=graphify_subject,
        runtime=runtime,
        license_id="Apache-2.0",
        license_ref=f"Graphify-Labs/graphify/LICENSE@{GRAPHIFY_COMMIT}",
        use_posture="runtime_allowed",
        results=(graphify_result,),
        checks=_checks(graphify_checks, "normalized:graphify-code-graph"),
        artifact_digests=tuple(sha256_file(path) for path in graphify_raw),
        maturity_before="runtime_wired",
        profile_maturity_ceiling="evidence_proven",
        earned_maturity="runtime_wired" if not graphify_passed else "evidence_proven",
        limitations=("Currentness in this slice is proven through explicit full rebuild, not incremental update.",),
    )

    return {
        "schema_version": "1.0.0",
        "profile": {"id": PROFILE_ID, "version": PROFILE_VERSION},
        "update_posture": "full_rebuild",
        "providers": {
            "codegenome": {
                "checks": codegenome_checks,
                "v1_start_lines": {
                    "main_downstream": sorted(cg_v1_down),
                    "main_upstream": sorted(cg_v1_up),
                    "decoy_downstream": sorted(cg_v1_decoy),
                },
                "v2_start_lines": {
                    "main_downstream": sorted(cg_v2_down),
                    "main_upstream": sorted(cg_v2_up),
                    "decoy_downstream": sorted(cg_v2_decoy),
                },
                "qualification": cg_record.to_dict(),
                "passed": cg_passed,
            },
            "graphify": {
                "checks": graphify_checks,
                "v1_call_facts": [list(item) for item in sorted(graphify_v1_facts)],
                "v2_call_facts": [list(item) for item in sorted(graphify_v2_facts)],
                "qualification": graphify_record.to_dict(),
                "passed": graphify_passed,
            },
        },
        "matched_result": {
            "both_passed": cg_passed and graphify_passed,
            "winner": None,
            "authority_effect": "none",
            "unrelated_capabilities_promoted": [],
        },
    }
