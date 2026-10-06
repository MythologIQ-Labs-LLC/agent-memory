#!/usr/bin/env python3
"""Runtime Baseline identity: the one table of what a baseline record pins to source.

Every published Runtime Baseline record names identities (contract version, profile
identity, substrate constants, interpreter versions, ranking policy, candidate routes)
that must agree with the protected source at its frozen revision. This module states
that correspondence once, as data, and reads it from any git revision so the
equivalence checker and the register validator share a single definition.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTECTED = "reference/agentmem_ref"


@dataclass(frozen=True)
class IdentitySource:
    identity_path: str  # dotted path into the baseline record; integer segments allowed
    file: str  # path inside the protected surface
    kind: str  # "constant" | "numeric" | "json"
    key: str  # constant name, or dotted key for kind "json"


IDENTITY_SOURCES: tuple[IdentitySource, ...] = (
    IdentitySource("identity.public_contract_version", f"{PROTECTED}/api/contract.py", "constant", "CONTRACT_VERSION"),
    IdentitySource("identity.runtime_id", f"{PROTECTED}/_profiles/rc1-local.json", "json", "runtime.runtime_id"),
    IdentitySource("identity.runtime_version", f"{PROTECTED}/_profiles/rc1-local.json", "json", "runtime.runtime_version"),
    IdentitySource("identity.runtime_profile_id", f"{PROTECTED}/_profiles/rc1-local.json", "json", "runtime.profile_id"),
    IdentitySource("identity.runtime_profile_version", f"{PROTECTED}/_profiles/rc1-local.json", "json", "runtime.profile_version"),
    IdentitySource("identity.sqlite_substrate_schema_version", f"{PROTECTED}/state/sqlite_substrate.py", "constant", "SQLITE_SUBSTRATE_SCHEMA_VERSION"),
    IdentitySource("identity.sqlite_substrate_profile", f"{PROTECTED}/state/sqlite_substrate.py", "constant", "SQLITE_SUBSTRATE_PROFILE"),
    IdentitySource("persistence_and_durability.canonical_state_commitment.active_scheme", f"{PROTECTED}/state/sqlite_substrate.py", "constant", "BUCKETED_DIGEST_SCHEME"),
    IdentitySource("persistence_and_durability.governance_state_commitment.active_scheme", f"{PROTECTED}/state/sqlite_substrate.py", "constant", "GOVERNANCE_SCHEME"),
    IdentitySource("identity.typed_relation_schema_version", f"{PROTECTED}/state/substrate.py", "constant", "TYPED_RELATION_SCHEMA_VERSION"),
    IdentitySource("identity.query_temporal_interpreter.ref", f"{PROTECTED}/runtime/temporal_intent.py", "constant", "INTERPRETER_REF"),
    IdentitySource("identity.query_temporal_interpreter.version", f"{PROTECTED}/runtime/temporal_intent.py", "constant", "INTERPRETER_VERSION"),
    IdentitySource("identity.write_semantics_interpreter.ref", f"{PROTECTED}/runtime/proposition_semantics.py", "constant", "INTERPRETER_REF"),
    IdentitySource("identity.write_semantics_interpreter.version", f"{PROTECTED}/runtime/proposition_semantics.py", "constant", "INTERPRETER_VERSION"),
    IdentitySource("identity.write_semantics_interpreter.classifier_version", f"{PROTECTED}/runtime/proposition_semantics.py", "constant", "CLASSIFIER_VERSION"),
    IdentitySource("identity.ranking.base_policy_family", f"{PROTECTED}/runtime/ranking_policy.py", "constant", "POLICY_FAMILY"),
    IdentitySource("identity.ranking.base_lexical_policy_version", f"{PROTECTED}/runtime/ranking_policy.py", "constant", "POLICY_VERSION"),
    IdentitySource("identity.ranking.lexical_anti_laundering_guard", f"{PROTECTED}/runtime/ranking_policy.py", "constant", "LEXICAL_ANTI_LAUNDERING_GUARD"),
    IdentitySource("identity.ranking.bm25.k1", f"{PROTECTED}/runtime/ranking_policy.py", "numeric", "BM25_K1"),
    IdentitySource("identity.ranking.bm25.b", f"{PROTECTED}/runtime/ranking_policy.py", "numeric", "BM25_B"),
    IdentitySource("identity.ranking.active_policy_version", f"{PROTECTED}/runtime/temporal_order_constraints.py", "constant", "POLICY_VERSION"),
    IdentitySource("identity.ranking.unknown_basis_policy", f"{PROTECTED}/runtime/temporal_order_constraints.py", "constant", "UNKNOWN_BASIS_POLICY"),
    IdentitySource("read_semantics.candidate_routes.0", f"{PROTECTED}/runtime/runtime_composition.py", "constant", "LEXICAL_ROUTE"),
    IdentitySource("read_semantics.candidate_routes.1", f"{PROTECTED}/runtime/runtime_composition.py", "constant", "EXACT_IDENTITY_ROUTE"),
    IdentitySource("read_semantics.candidate_routes.2", f"{PROTECTED}/runtime/runtime_composition.py", "constant", "SHARED_EVIDENCE_ROUTE"),
    IdentitySource("read_semantics.candidate_routes.3", f"{PROTECTED}/runtime/vector_retrieval.py", "constant", "SEMANTIC_VECTOR_ROUTE"),
)


class IdentityError(SystemExit):
    """A source identity could not be read or does not exist."""


def git_show(root: Path, commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise IdentityError(f"cannot read {path} at revision {commit}: {result.stderr.strip()}")
    return result.stdout


def constant(source: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']", source, re.MULTILINE)
    if not match:
        raise IdentityError(f"missing string constant {name}")
    return match.group(1)


def numeric_constant(source: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s*=\s*([0-9.]+)", source, re.MULTILINE)
    if not match:
        raise IdentityError(f"missing numeric constant {name}")
    return float(match.group(1))


def git_blob_sha(content: str | bytes) -> str:
    payload = content.encode("utf-8") if isinstance(content, str) else content
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def record_value(record: Any, identity_path: str) -> Any:
    """Resolve a dotted path with integer segments against a record."""

    value = record
    for segment in identity_path.split("."):
        if isinstance(value, list):
            try:
                value = value[int(segment)]
            except (ValueError, IndexError) as exc:
                raise IdentityError(f"record has no element {segment!r} at {identity_path}") from exc
        elif isinstance(value, dict) and segment in value:
            value = value[segment]
        else:
            raise IdentityError(f"record has no value at {identity_path}")
    return value


def _read_one(text: str, source: IdentitySource) -> Any:
    if source.kind == "constant":
        return constant(text, source.key)
    if source.kind == "numeric":
        return numeric_constant(text, source.key)
    if source.kind == "json":
        return record_value(json.loads(text), source.key)
    raise IdentityError(f"unknown identity kind {source.kind!r} for {source.identity_path}")


def read_identities(
    root: Path, revision: str, sources: tuple[IdentitySource, ...] = IDENTITY_SOURCES
) -> dict[str, Any]:
    """Read every identity from the protected surface at ``revision``."""

    texts: dict[str, str] = {}
    values: dict[str, Any] = {}
    for source in sources:
        if source.file not in texts:
            texts[source.file] = git_show(root, revision, source.file)
        values[source.identity_path] = _read_one(texts[source.file], source)
    return values


def record_identities(
    record: dict, sources: tuple[IdentitySource, ...] = IDENTITY_SOURCES
) -> dict[str, Any]:
    """The record's own values at every identity path, numeric paths coerced to float."""

    values: dict[str, Any] = {}
    for source in sources:
        value = record_value(record, source.identity_path)
        values[source.identity_path] = float(value) if source.kind == "numeric" else value
    return values
