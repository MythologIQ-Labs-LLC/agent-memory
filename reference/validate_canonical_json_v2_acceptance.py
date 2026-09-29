from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from validate_canonical_json_v2_vectors import validate as validate_source

EXPECTED = {
    "acceptance_id": "agent-memory-canonical-json-v2-vectors-accepted-v1",
    "status": "ACCEPTED_IMPLEMENTATION_VECTOR_SOURCE",
    "source_fixture": "reference/fixtures/runtime/canonical-json-v2-vectors-v1.json",
    "source_fixture_id": "agent-memory-canonical-json-v2-vectors-v1",
    "source_fixture_git_blob_sha1": "27fe35f273230d0602f6e356eb42075485aafcf1",
    "source_head_sha": "fcdba21ec8c0fb70d78d05dd42d22fc6a43c70e6",
    "source_merge_sha": "a129896274539f979b996e6024b27c3bd579c073",
    "case_count": 44,
    "review_id": 5346919391,
    "accepted_at": "2026-09-29T02:17:59Z",
    "workflow_run": 36511351315,
}


def _git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def validate(repo_root: Path, record_path: Path) -> dict[str, object]:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    source_path = repo_root / str(record["source_fixture"])
    raw = source_path.read_bytes()
    source_result = validate_source(source_path)

    checks = {
        "acceptance_id": record.get("acceptance_id"),
        "status": record.get("status"),
        "source_fixture": record.get("source_fixture"),
        "source_fixture_id": record.get("source_fixture_id"),
        "source_fixture_git_blob_sha1": record.get("source_fixture_git_blob_sha1"),
        "source_head_sha": record.get("source_head_sha"),
        "source_merge_sha": record.get("source_merge_sha"),
        "case_count": record.get("case_count"),
        "review_id": record.get("acceptance", {}).get("review_id"),
        "accepted_at": record.get("acceptance", {}).get("accepted_at"),
        "workflow_run": record.get("acceptance", {}).get("workflow_run"),
    }
    for key, expected in EXPECTED.items():
        if checks.get(key) != expected:
            raise ValueError(f"acceptance field changed: {key}: {checks.get(key)!r} != {expected!r}")

    actual_blob = _git_blob_sha1(raw)
    if actual_blob != EXPECTED["source_fixture_git_blob_sha1"]:
        raise ValueError(f"source fixture bytes changed: {actual_blob}")
    if source_result["case_count"] != record["case_count"]:
        raise ValueError("accepted case count does not match source fixture")
    if record.get("authority_effect") != "implementation_conformance_only":
        raise ValueError("acceptance authority boundary changed")
    not_accepted = set(record.get("scope", {}).get("not_accepted", ()))
    required_exclusions = {
        "ADR-040 architecture decision",
        "persistence migration",
        "digest scheme transition",
        "Rust runtime promotion",
    }
    if not required_exclusions.issubset(not_accepted):
        raise ValueError("acceptance record no longer preserves architecture/runtime stop lines")

    return {
        "acceptance_id": record["acceptance_id"],
        "source_fixture_git_blob_sha1": actual_blob,
        "case_count": source_result["case_count"],
        "source_fixture_sha256": source_result["fixture_sha256"],
        "review_id": record["acceptance"]["review_id"],
        "accepted_at": record["acceptance"]["accepted_at"],
        "authority_effect": record["authority_effect"],
        "result": "accepted_vector_source_integrity_pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--record",
        type=Path,
        default=Path("reference/fixtures/runtime/canonical-json-v2-vectors-accepted-v1.json"),
    )
    args = parser.parse_args()
    result = validate(args.repo_root.resolve(), args.record)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
