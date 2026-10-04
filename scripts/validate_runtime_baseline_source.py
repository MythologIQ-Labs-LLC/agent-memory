#!/usr/bin/env python3
"""Verify Runtime Baseline v1 identities against its exact frozen revision (#638)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports" / "runtime" / "baseline-v1.json"


def git_show(commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit(f"cannot read {path} at frozen revision {commit}: {result.stderr.strip()}")
    return result.stdout


def constant(source: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']", source, re.MULTILINE)
    if not match:
        raise SystemExit(f"missing string constant {name}")
    return match.group(1)


def numeric_constant(source: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s*=\s*([0-9.]+)", source, re.MULTILINE)
    if not match:
        raise SystemExit(f"missing numeric constant {name}")
    return float(match.group(1))


def expect(label: str, actual, expected) -> None:
    if actual != expected:
        raise SystemExit(f"{label} mismatch: frozen source={actual!r}, manifest={expected!r}")


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    commit = data["runtime_revision"]["commit"]
    check = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT)
    if check.returncode:
        raise SystemExit(f"frozen runtime revision is unavailable: {commit}")

    identity = data["identity"]
    ranking = identity["ranking"]

    contract = git_show(commit, "reference/agentmem_ref/api/contract.py")
    expect("public contract", constant(contract, "CONTRACT_VERSION"), identity["public_contract_version"])

    profile = json.loads(git_show(commit, "reference/agentmem_ref/_profiles/rc1-local.json"))
    runtime = profile["runtime"]
    expect("runtime id", runtime["runtime_id"], identity["runtime_id"])
    expect("runtime version", runtime["runtime_version"], identity["runtime_version"])
    expect("runtime profile id", runtime["profile_id"], identity["runtime_profile_id"])
    expect("runtime profile version", runtime["profile_version"], identity["runtime_profile_version"])

    sqlite = git_show(commit, "reference/agentmem_ref/state/sqlite_substrate.py")
    expect("SQLite schema", constant(sqlite, "SQLITE_SUBSTRATE_SCHEMA_VERSION"), identity["sqlite_substrate_schema_version"])
    expect("SQLite profile", constant(sqlite, "SQLITE_SUBSTRATE_PROFILE"), identity["sqlite_substrate_profile"])
    expect("canonical commitment", constant(sqlite, "BUCKETED_DIGEST_SCHEME"), data["persistence_and_durability"]["canonical_state_commitment"]["active_scheme"])
    expect("governance commitment", constant(sqlite, "GOVERNANCE_SCHEME"), data["persistence_and_durability"]["governance_state_commitment"]["active_scheme"])

    substrate = git_show(commit, "reference/agentmem_ref/state/substrate.py")
    expect("typed relation schema", constant(substrate, "TYPED_RELATION_SCHEMA_VERSION"), identity["typed_relation_schema_version"])

    temporal = git_show(commit, "reference/agentmem_ref/runtime/temporal_intent.py")
    expect("query interpreter ref", constant(temporal, "INTERPRETER_REF"), identity["query_temporal_interpreter"]["ref"])
    expect("query interpreter version", constant(temporal, "INTERPRETER_VERSION"), identity["query_temporal_interpreter"]["version"])

    write = git_show(commit, "reference/agentmem_ref/runtime/proposition_semantics.py")
    expect("write interpreter ref", constant(write, "INTERPRETER_REF"), identity["write_semantics_interpreter"]["ref"])
    expect("write interpreter version", constant(write, "INTERPRETER_VERSION"), identity["write_semantics_interpreter"]["version"])
    expect("write classifier version", constant(write, "CLASSIFIER_VERSION"), identity["write_semantics_interpreter"]["classifier_version"])

    base_ranking = git_show(commit, "reference/agentmem_ref/runtime/ranking_policy.py")
    expect("ranking family", constant(base_ranking, "POLICY_FAMILY"), ranking["base_policy_family"])
    expect("base lexical policy", constant(base_ranking, "POLICY_VERSION"), ranking["base_lexical_policy_version"])
    expect("lexical anti-laundering guard", constant(base_ranking, "LEXICAL_ANTI_LAUNDERING_GUARD"), ranking["lexical_anti_laundering_guard"])
    expect("BM25 k1", numeric_constant(base_ranking, "BM25_K1"), float(ranking["bm25"]["k1"]))
    expect("BM25 b", numeric_constant(base_ranking, "BM25_B"), float(ranking["bm25"]["b"]))

    constrained = git_show(commit, "reference/agentmem_ref/runtime/temporal_order_constraints.py")
    expect("active ranking policy", constant(constrained, "POLICY_VERSION"), ranking["active_policy_version"])
    expect("unknown-basis policy", constant(constrained, "UNKNOWN_BASIS_POLICY"), ranking["unknown_basis_policy"])

    composition = git_show(commit, "reference/agentmem_ref/runtime/runtime_composition.py")
    vector = git_show(commit, "reference/agentmem_ref/runtime/vector_retrieval.py")
    source_routes = [
        constant(composition, "LEXICAL_ROUTE"),
        constant(composition, "EXACT_IDENTITY_ROUTE"),
        constant(composition, "SHARED_EVIDENCE_ROUTE"),
        constant(vector, "SEMANTIC_VECTOR_ROUTE"),
    ]
    expect("candidate routes", source_routes, data["read_semantics"]["candidate_routes"])

    if data["production_1_0"]:
        raise SystemExit("baseline source may not claim production 1.0")
    if data["dogfood"]["status"] != "pending":
        raise SystemExit("first baseline slice must retain pending #637 dogfood status")
    print(f"Runtime Baseline v1 identities match frozen revision {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
