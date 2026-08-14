"""Normalize the first executable #275 code-reality comparator.

The comparator intentionally measures a tiny deterministic ground-truth fixture
instead of importing either product's benchmark vocabulary. CodeGenome and
Graphify remain authoritative for their own output semantics; this module only
records whether the pinned runtimes reproduce the fixture facts we asked them
to expose.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_LINE = re.compile(r"^line (\d+):(\d+)$")

CODEGENOME_COMMIT = "d2578729a46d495369bd7613845002d50cf20f4c"
GRAPHIFY_COMMIT = "7fe58b0b0f3873be9a21c30106b8b8527c353aa6"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _codegenome_start_lines(payload: list[dict[str, Any]]) -> set[int]:
    lines: set[int] = set()
    for item in payload:
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


def _graphify_call_facts(payload: dict[str, Any]) -> set[tuple[str, str, str]]:
    nodes = {node["id"]: node for node in payload.get("nodes", []) if "id" in node}
    facts: set[tuple[str, str, str]] = set()
    for edge in payload.get("edges", []):
        if edge.get("relation") != "calls":
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


def run_code_reality_comparator(
    *,
    agent_memory_commit: str,
    fixture_dir: Path,
    codegenome_main_downstream: Path,
    codegenome_main_upstream: Path,
    codegenome_decoy_downstream: Path,
    graphify_graph: Path,
) -> dict[str, Any]:
    if not _HEX40.fullmatch(agent_memory_commit):
        raise ValueError("agent_memory_commit must be an exact lowercase 40-hex commit")

    main_downstream = _codegenome_start_lines(_load(codegenome_main_downstream))
    main_upstream = _codegenome_start_lines(_load(codegenome_main_upstream))
    decoy_downstream = _codegenome_start_lines(_load(codegenome_decoy_downstream))
    graphify = _load(graphify_graph)
    graphify_calls = _graphify_call_facts(graphify)

    # Ground truth from reference/fixtures/code-reality:
    # main.rs: leaf L3, middle L7, top L11
    # decoy.rs: middle L7, decoy_leaf L21
    codegenome_checks = {
        "main_downstream_contains_target_middle": 7 in main_downstream,
        "main_downstream_contains_leaf": 3 in main_downstream,
        "main_downstream_excludes_upstream_top": 11 not in main_downstream,
        "main_downstream_excludes_decoy_leaf": 21 not in main_downstream,
        "main_upstream_contains_target_middle": 7 in main_upstream,
        "main_upstream_contains_top": 11 in main_upstream,
        "main_upstream_excludes_downstream_leaf": 3 not in main_upstream,
        "main_upstream_excludes_decoy_leaf": 21 not in main_upstream,
        "decoy_downstream_contains_target_middle": 7 in decoy_downstream,
        "decoy_downstream_contains_decoy_leaf": 21 in decoy_downstream,
        "decoy_downstream_excludes_main_leaf": 3 not in decoy_downstream,
    }

    expected_graphify_calls = {
        ("main.rs", "middle", "leaf"),
        ("main.rs", "top", "middle"),
        ("decoy.rs", "middle", "decoy_leaf"),
    }
    graphify_checks = {
        "main_middle_calls_leaf": ("main.rs", "middle", "leaf") in graphify_calls,
        "main_top_calls_middle": ("main.rs", "top", "middle") in graphify_calls,
        "decoy_middle_calls_decoy_leaf": ("decoy.rs", "middle", "decoy_leaf") in graphify_calls,
        "no_unexpected_fixture_call_edges": graphify_calls.issubset(expected_graphify_calls),
    }

    codegenome_passed = all(codegenome_checks.values())
    graphify_passed = all(graphify_checks.values())

    return {
        "schema_version": "0.1.0",
        "program": "issue-275-code-reality-comparator",
        "agent_memory_commit": agent_memory_commit,
        "fixture_digest": _sha256_files(list(fixture_dir.glob("*.rs"))),
        "implementations": {
            "codegenome": {
                "repository": "MythologIQ-Labs-LLC/CodeGenome",
                "commit": CODEGENOME_COMMIT,
                "license": "MIT",
                "execution": "real pinned Rust CLI over the shared fixture",
                "checks": codegenome_checks,
                "passed": codegenome_passed,
                "observed_start_lines": {
                    "main_downstream": sorted(main_downstream),
                    "main_upstream": sorted(main_upstream),
                    "decoy_downstream": sorted(decoy_downstream),
                },
                "claim_boundary": "This slice measures file-bound target resolution and directional impact on a known call chain; it does not establish complete code-reality correctness or Agent Memory conformance.",
            },
            "graphify": {
                "repository": "Graphify-Labs/graphify",
                "commit": GRAPHIFY_COMMIT,
                "license": "Apache-2.0",
                "execution": "real pinned Python/tree-sitter extractor over the shared fixture",
                "checks": graphify_checks,
                "passed": graphify_passed,
                "observed_call_facts": [
                    {"source_file": file, "source": source, "target": target}
                    for file, source, target in sorted(graphify_calls)
                ],
                "claim_boundary": "This slice measures deterministic Rust call-edge extraction only; no Graphify benchmark, semantic-media pass, hosted service, or LLM-assisted capability is evaluated.",
            },
        },
        "matched_result": {
            "codegenome_ground_truth_passed": codegenome_passed,
            "graphify_ground_truth_passed": graphify_passed,
            "both_reproduce_requested_fixture_facts": codegenome_passed and graphify_passed,
            "winner": None,
        },
        "governance_observations": {
            "product_specific_identity_not_promoted_to_agent_memory": True,
            "runtime_result_not_authority": True,
            "raw_outputs_preserved_separately": True,
            "scalar_product_ranking_created": False,
        },
        "limitations": [
            "The fixture is intentionally tiny and deterministic.",
            "CodeGenome and Graphify expose different query surfaces; this report compares shared ground-truth facts rather than forcing identical output schemas.",
            "GitNexus is not executed in this slice because the reviewed pin is PolyForm Noncommercial 1.0.0 and remains a source-analysis comparator unless separate rights analysis justifies runtime use.",
            "Correction, incremental rebuild, confidence-fusion dependence, and larger multi-language cases remain later #275 slices.",
        ],
    }
