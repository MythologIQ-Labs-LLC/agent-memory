from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


def _collect_numeric_schema_nodes(value: Any, path: tuple[str, ...] = ()) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        raw_type = value.get("type")
        values = raw_type if isinstance(raw_type, list) else [raw_type]
        if any(item in {"number", "integer"} for item in values):
            found.append("/" + "/".join(path) if path else "/")
        for key, child in value.items():
            found.extend(_collect_numeric_schema_nodes(child, (*path, str(key))))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_collect_numeric_schema_nodes(child, (*path, str(index))))
    return found


def _extension_state_contract(adapter_source: str) -> bool:
    tree = ast.parse(adapter_source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        target = node.target
        if not (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and target.attr == "extension_state"
        ):
            continue
        annotation = ast.unparse(node.annotation)
        return annotation.replace(" ", "") == "dict[str,dict]"
    return False


def _dataclass_field_is_plain_dict(source: str, class_name: str, field_name: str) -> bool:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if isinstance(statement.target, ast.Name) and statement.target.id == field_name:
                return ast.unparse(statement.annotation).replace(" ", "") == "dict"
    return False


def _restart_exports_extension_state(restart_source: str) -> bool:
    tree = ast.parse(restart_source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key in node.keys:
            if isinstance(key, ast.Constant) and key.value == "extension_state":
                return True
    return False


def qualify(repo_root: Path) -> dict[str, object]:
    schema_path = repo_root / "schemas" / "runtime-configuration.schema.json"
    adapter_path = repo_root / "reference" / "agentmem_ref" / "runtime" / "adapter.py"
    restart_path = repo_root / "reference" / "agentmem_ref" / "runtime" / "restart_runtime.py"
    substrate_model_path = repo_root / "reference" / "agentmem_ref" / "state" / "substrate.py"
    sqlite_path = repo_root / "reference" / "agentmem_ref" / "state" / "sqlite_substrate.py"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    numeric_nodes = _collect_numeric_schema_nodes(schema)
    adapter_source = adapter_path.read_text(encoding="utf-8")
    restart_source = restart_path.read_text(encoding="utf-8")
    substrate_model_source = substrate_model_path.read_text(encoding="utf-8")
    sqlite_source = sqlite_path.read_text(encoding="utf-8")

    extension_contract = _extension_state_contract(adapter_source)
    restart_exports = _restart_exports_extension_state(restart_source)
    restart_uses_python_canonical_bytes = (
        'json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)' in restart_source
    )
    fact_attributes_open = _dataclass_field_is_plain_dict(substrate_model_source, "Fact", "attributes")
    relation_attributes_open = _dataclass_field_is_plain_dict(substrate_model_source, "TypedRelation", "attributes")
    relation_weight_float = "retrieval_weight: float = 1.0" in substrate_model_source
    relation_weight_finite = "math.isfinite(self.retrieval_weight)" in substrate_model_source

    bmerkle_scheme = 'BUCKETED_DIGEST_SCHEME = "bmerkle-v1"' in sqlite_source
    bmerkle_hashes_facts = '_row_hash("facts", asdict(fact))' in sqlite_source
    bmerkle_hashes_relations = '_row_hash("typed_relations", asdict(relation))' in sqlite_source
    gsect_scheme = 'GOVERNANCE_SCHEME = "gsect-v1"' in sqlite_source
    gsect_residual_python_json = "value_json = _json_text(residual)" in sqlite_source
    gsect_root_binds_residual = 'hashlib.sha256(self._residual_json.encode("utf-8")).hexdigest()' in sqlite_source
    restart_residual_exports_extension = '"extension_state": {' in restart_source

    if numeric_nodes:
        raise RuntimeError(f"runtime configuration schema contains numeric domains: {numeric_nodes}")
    if not extension_contract:
        raise RuntimeError("extension_state no longer has the expected opaque dict[str, dict] contract")
    if not restart_exports:
        raise RuntimeError("restart runtime no longer exports extension_state")
    if not restart_uses_python_canonical_bytes:
        raise RuntimeError("restart runtime canonical byte helper changed; re-qualify reachability")
    if not (fact_attributes_open and relation_attributes_open):
        raise RuntimeError("Fact/TypedRelation attributes are no longer plain dict domains; re-qualify")
    if not (relation_weight_float and relation_weight_finite):
        raise RuntimeError("TypedRelation retrieval_weight contract changed; re-qualify")
    if not (bmerkle_scheme and bmerkle_hashes_facts and bmerkle_hashes_relations):
        raise RuntimeError("bmerkle-v1 row commitment structure changed; re-qualify")
    if not (gsect_scheme and gsect_residual_python_json and gsect_root_binds_residual and restart_residual_exports_extension):
        raise RuntimeError("gsect-v1 residual/extension commitment structure changed; re-qualify")

    return {
        "schema_version": 2,
        "qualification": "canonicalization_value_domain_and_scheme_reachability",
        "runtime_configuration": {
            "schema": "schemas/runtime-configuration.schema.json",
            "numeric_schema_nodes": numeric_nodes,
            "numeric_reachability": "proven_absent_by_schema_v1",
            "migration_consequence": "no_numeric_v2_migration_required_under_schema_v1",
        },
        "bmerkle_v1": {
            "canonicalizer": "legacy_python_sorted_json",
            "commits_fact_rows": True,
            "commits_typed_relation_rows": True,
            "retrieval_weight": {
                "type": "float",
                "finite_required": True,
                "numeric_reachability": "proven_active",
            },
            "fact_attributes": {
                "contract": "dict",
                "numeric_reachability": "permitted_by_contract",
                "non_finite_reachability": "permitted_by_contract",
            },
            "typed_relation_attributes": {
                "contract": "dict",
                "numeric_reachability": "permitted_by_contract",
                "non_finite_reachability": "permitted_by_contract",
            },
            "migration_consequence": "successor_scheme_required_if_row_canonicalization_changes",
        },
        "gsect_v1": {
            "canonicalizer": "legacy_python_sorted_json_for_section_values_and_residual",
            "residual_committed_by_root": True,
            "extension_state_in_residual": True,
            "extension_state_contract": "dict[str, dict]",
            "numeric_reachability": "permitted_by_contract_not_currently_proven_active",
            "non_finite_reachability": "permitted_by_contract_not_currently_proven_active",
            "migration_consequence": "successor_scheme_required_if_residual_canonicalization_changes",
        },
        "restart_extension_state": {
            "adapter_contract": "dict[str, dict]",
            "persisted_by_restart": True,
            "canonicalizer": "legacy_python_sorted_json",
            "numeric_reachability": "permitted_by_contract_not_currently_proven_active",
            "reason": "opaque JSON-able extension dictionaries have no schema/type restriction excluding finite or non-finite floats",
        },
        "interpretation": {
            "runtime_config_v2_migration_required_for_numeric_defect": False,
            "bmerkle_v2_required_if_ADR_040_accepted": True,
            "gsect_v2_required_if_ADR_040_changes_governance_residual_bytes": True,
            "restart_envelope_must_bind_scheme_explicitly": True,
            "existing_rfc8785_jcs_domains_are_separate": True,
        },
        "authority_effect": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = qualify(args.repo_root.resolve())
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
