from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, Sequence

from canonical_json_v2_candidate import CanonicalJsonV2Error, canonical_bytes_v2


SUBSTRATE_SCHEME_V2 = "bmerkle-v2"
GOVERNANCE_SCHEME_V2 = "gsect-v2"
DIGEST_BUCKETS = 256
GOVERNANCE_BUCKETS = 256
GOVERNANCE_MAP_SECTIONS = (
    "current_fact_by_memory",
    "fact_memory",
    "fact_scope",
    "state_version",
    "tombstones",
)
GOVERNANCE_LOG_SECTIONS = ("events",)
GOVERNANCE_CHAIN_START = ""


class MigrationPreflightError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


@dataclass(frozen=True)
class CandidateCommitments:
    substrate_commitment: str
    governance_commitment: str
    logical_state_digest: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_digest(value: Any) -> str:
    try:
        return _sha256(canonical_bytes_v2(value))
    except CanonicalJsonV2Error as exc:
        raise MigrationPreflightError("candidate_value_domain_invalid", exc.reason) from exc


def validate_candidate_value_domain(value: Any) -> None:
    """Validate the complete candidate value recursively by canonicalizing it.

    This produces no durable state. The resulting bytes are discarded intentionally;
    phase 2 is a value-domain gate, not a commitment side effect.
    """

    try:
        canonical_bytes_v2(value)
    except CanonicalJsonV2Error as exc:
        raise MigrationPreflightError("candidate_value_domain_invalid", exc.reason) from exc


def _substrate_bucket(table: str, key: str) -> int:
    material = f"{table}\x00{key}".encode("utf-8")
    return int(hashlib.sha256(material).hexdigest()[:8], 16) % DIGEST_BUCKETS


def _substrate_row_hash(table: str, payload: Mapping[str, Any]) -> str:
    return _canonical_digest({"table": table, "row": dict(payload)})


def _bucket_digest(row_hashes: Sequence[str]) -> str:
    return _canonical_digest(sorted(row_hashes))


def compute_substrate_v2(
    *,
    episodes: Sequence[Mapping[str, Any]],
    facts: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    schema_version: str,
    relation_schema_version: str,
    id_counter: int,
) -> str:
    rows: list[tuple[int, str]] = []
    for table, values, key_name in (
        ("episodes", episodes, "uuid"),
        ("facts", facts, "uuid"),
        ("typed_relations", relations, "relation_id"),
    ):
        for payload in values:
            key = str(payload[key_name])
            rows.append((_substrate_bucket(table, key), _substrate_row_hash(table, payload)))

    buckets: list[list[str]] = [[] for _ in range(DIGEST_BUCKETS)]
    for bucket, row_hash in rows:
        buckets[bucket].append(row_hash)
    bucket_digests = [_bucket_digest(values) for values in buckets]

    material = {
        "scheme": SUBSTRATE_SCHEME_V2,
        "schema_version": schema_version,
        "relation_schema_version": relation_schema_version,
        "id_counter": int(id_counter),
        "buckets": bucket_digests,
    }
    return f"{SUBSTRATE_SCHEME_V2}:" + _canonical_digest(material)


def _governance_bucket(section: str, key: str) -> int:
    material = f"{section}\x00{key}".encode("utf-8")
    return int(hashlib.sha256(material).hexdigest()[:8], 16) % GOVERNANCE_BUCKETS


def _text_hash(*parts: str) -> str:
    return _canonical_digest(list(parts))


def _governance_entry_hash(section: str, key: str, value_json: str) -> str:
    return _text_hash("entry", section, key, value_json)


def _governance_chain(section: str, seq: int, previous: str, value_json: str) -> str:
    return _text_hash("log", section, str(seq), previous, _sha256(value_json.encode("utf-8")))


def _governance_map_root(section: str, bucket_digests: Sequence[str]) -> str:
    return _canonical_digest({"section": section, "buckets": list(bucket_digests)})


def compute_governance_v2(
    *,
    maps: Mapping[str, Mapping[str, Any]],
    logs: Mapping[str, Sequence[Any]],
    residual: Mapping[str, Any],
) -> str:
    map_roots: dict[str, str] = {}
    for section in GOVERNANCE_MAP_SECTIONS:
        values = maps.get(section)
        if values is None:
            raise MigrationPreflightError("candidate_governance_shape_invalid", f"missing map section {section}")
        buckets: list[list[str]] = [[] for _ in range(GOVERNANCE_BUCKETS)]
        for raw_key, value in values.items():
            key = str(raw_key)
            try:
                value_json = canonical_bytes_v2(value).decode("utf-8")
            except CanonicalJsonV2Error as exc:
                raise MigrationPreflightError("candidate_value_domain_invalid", exc.reason) from exc
            bucket = _governance_bucket(section, key)
            buckets[bucket].append(_governance_entry_hash(section, key, value_json))
        digests = [_bucket_digest(values) for values in buckets]
        map_roots[section] = _governance_map_root(section, digests)

    log_heads: dict[str, dict[str, Any]] = {}
    for section in GOVERNANCE_LOG_SECTIONS:
        values = logs.get(section)
        if values is None:
            raise MigrationPreflightError("candidate_governance_shape_invalid", f"missing log section {section}")
        count = 0
        head = GOVERNANCE_CHAIN_START
        for value in values:
            count += 1
            try:
                value_json = canonical_bytes_v2(value).decode("utf-8")
            except CanonicalJsonV2Error as exc:
                raise MigrationPreflightError("candidate_value_domain_invalid", exc.reason) from exc
            head = _governance_chain(section, count, head, value_json)
        log_heads[section] = {"count": count, "head": head}

    residual_digest = _canonical_digest(dict(residual))
    material = {
        "scheme": GOVERNANCE_SCHEME_V2,
        "maps": {name: map_roots[name] for name in GOVERNANCE_MAP_SECTIONS},
        "logs": {name: log_heads[name] for name in GOVERNANCE_LOG_SECTIONS},
        "residual": residual_digest,
    }
    return f"{GOVERNANCE_SCHEME_V2}:" + _canonical_digest(material)


def logical_state_digest(
    *,
    substrate_state: Mapping[str, Any],
    governance_state: Mapping[str, Any],
) -> str:
    return "sha256:" + _canonical_digest(
        {
            "substrate": dict(substrate_state),
            "governance": dict(governance_state),
        }
    )


def compute_candidate_commitments(
    *,
    substrate_state: Mapping[str, Any],
    governance_maps: Mapping[str, Mapping[str, Any]],
    governance_logs: Mapping[str, Sequence[Any]],
    governance_residual: Mapping[str, Any],
) -> CandidateCommitments:
    validate_candidate_value_domain(substrate_state)
    validate_candidate_value_domain(governance_maps)
    validate_candidate_value_domain(governance_logs)
    validate_candidate_value_domain(governance_residual)

    substrate = compute_substrate_v2(
        episodes=substrate_state["episodes"],
        facts=substrate_state["facts"],
        relations=substrate_state["relations"],
        schema_version=str(substrate_state["schema_version"]),
        relation_schema_version=str(substrate_state["relation_schema_version"]),
        id_counter=int(substrate_state["id_counter"]),
    )
    governance = compute_governance_v2(
        maps=governance_maps,
        logs=governance_logs,
        residual=governance_residual,
    )
    governance_logical = {
        "maps": {key: dict(value) for key, value in governance_maps.items()},
        "logs": {key: list(value) for key, value in governance_logs.items()},
        "residual": dict(governance_residual),
    }
    logical = logical_state_digest(
        substrate_state=substrate_state,
        governance_state=governance_logical,
    )
    return CandidateCommitments(
        substrate_commitment=substrate,
        governance_commitment=governance,
        logical_state_digest=logical,
    )
