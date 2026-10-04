#!/usr/bin/env python3
"""Verify Runtime Baseline v1 identities against its exact frozen revision (#638)."""

from __future__ import annotations

import hashlib
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


def exact_sha(label: str, value: str) -> None:
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise SystemExit(f"{label} must be an exact lowercase 40-hex SHA")


def require_commit(label: str, revision: str) -> None:
    exact_sha(label, revision)
    exists = subprocess.run(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=ROOT)
    if exists.returncode:
        raise SystemExit(f"{label} is unavailable: {revision}")


def git_blob_sha(content: str) -> str:
    payload = content.encode("utf-8")
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def require_frozen_runtime_equivalence(frozen: str, candidate: str) -> None:
    """Refuse a claimed baseline qualification if installed runtime/package code drifted."""

    diff = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            frozen,
            candidate,
            "--",
            "reference/agentmem_ref",
            "pyproject.toml",
        ],
        cwd=ROOT,
    )
    if diff.returncode == 1:
        raise SystemExit(
            "qualified checkout differs from frozen Runtime Baseline v1 under "
            "reference/agentmem_ref or pyproject.toml"
        )
    if diff.returncode != 0:
        raise SystemExit("unable to compare qualified checkout to frozen runtime revision")


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    commit = data["runtime_revision"]["commit"]
    require_commit("runtime revision", commit)

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

    dogfood = data["dogfood"]
    if dogfood["status"] != "completed":
        raise SystemExit("Runtime Baseline v1 cannot close before #637 dogfood is completed")
    if dogfood["required_before_issue_638_close"] is not True:
        raise SystemExit("#637 dogfood must remain recorded as a required #638 close gate")
    if dogfood["authority_effect"] != "none":
        raise SystemExit("dogfood evidence must have authority_effect none")
    if dogfood["evidence_class"] != "baseline_or_probe":
        raise SystemExit("#637 dogfood must remain baseline_or_probe usability evidence")
    dogfood_commit = dogfood["merge_commit"]
    dogfood_head = dogfood["verified_head"]
    require_commit("dogfood merge commit", dogfood_commit)
    require_commit("dogfood verified head", dogfood_head)
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", commit, dogfood_commit], cwd=ROOT)
    if ancestry.returncode:
        raise SystemExit("dogfood merge commit must descend from the frozen runtime revision")
    git_show(dogfood_commit, dogfood["golden_evidence"])
    git_show(dogfood_commit, "docs/GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md")

    public_gauntlet = data["qualification_evidence"]["public_gauntlet_baseline_qualification"]
    if public_gauntlet["status"] != "complete":
        raise SystemExit("Runtime Baseline public Gauntlet qualification must be complete")
    if public_gauntlet["transport"] != "stdio":
        raise SystemExit("Runtime Baseline public Gauntlet qualification must use stdio")
    if public_gauntlet["evidence_class"] != "baseline_or_probe":
        raise SystemExit("Runtime Baseline public Gauntlet evidence must remain baseline_or_probe")
    if public_gauntlet["authority_effect"] != "none":
        raise SystemExit("Runtime Baseline public Gauntlet evidence must have authority_effect none")
    if public_gauntlet["profile_id"] != "gauntlet-orchestration-retrieval-probe-v1":
        raise SystemExit("unexpected Runtime Baseline public Gauntlet profile")
    if int(public_gauntlet["workflow_run"]) <= 0 or int(public_gauntlet["artifact_id"]) <= 0:
        raise SystemExit("Runtime Baseline public Gauntlet workflow/artifact IDs must be positive")
    digest = str(public_gauntlet["artifact_digest"])
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise SystemExit("Runtime Baseline public Gauntlet artifact digest must be exact sha256")
    verified_head = public_gauntlet["verified_head"]
    require_commit("Runtime Baseline public Gauntlet verified head", verified_head)
    if subprocess.run(["git", "merge-base", "--is-ancestor", commit, verified_head], cwd=ROOT).returncode:
        raise SystemExit("public Gauntlet verified head must descend from the frozen runtime revision")
    require_frozen_runtime_equivalence(commit, verified_head)

    manifest_path = public_gauntlet["manifest"]
    adapter_path = public_gauntlet["adapter_source"]
    qualified_manifest = json.loads(git_show(verified_head, manifest_path))
    adapter_source = git_show(verified_head, adapter_path)
    expect("public Gauntlet system revision", qualified_manifest["system"]["revision"], public_gauntlet["system_revision"])
    expect("public Gauntlet adapter revision", qualified_manifest["adapter"]["revision"], public_gauntlet["adapter_revision"])
    expect("public Gauntlet transport", qualified_manifest["transport"]["kind"], public_gauntlet["transport"])
    expect("public Gauntlet baseline id", qualified_manifest["metadata"]["baseline_id"], data["baseline_id"])
    expected_system_revision = f"git-commit:{commit}"
    expect("public Gauntlet frozen runtime binding", public_gauntlet["system_revision"], expected_system_revision)
    actual_adapter_revision = f"git-blob:{git_blob_sha(adapter_source)}"
    expect("public Gauntlet exact adapter blob", public_gauntlet["adapter_revision"], actual_adapter_revision)
    if int(public_gauntlet["sample_count"]) != 3:
        raise SystemExit("public Gauntlet orchestration probe must record its three-query sample count")
    if not 0.0 <= float(public_gauntlet["exact_top1"]) <= 1.0:
        raise SystemExit("public Gauntlet exact_top1 must be a bounded observed metric")

    print(
        f"Runtime Baseline v1 identities match frozen revision {commit}; "
        f"#637 dogfood is evidence-bound at {dogfood_commit}; "
        f"public baseline qualification is bound at workflow {public_gauntlet['workflow_run']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
