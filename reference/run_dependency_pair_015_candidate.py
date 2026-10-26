#!/usr/bin/env python3
"""#826 isolated candidate preflight for Agent Manifest 0.15 / TRACE 0.11.

Does not alter the accepted #440 comparator or frozen package pins. This is
candidate evidence only, not a product or dependency-upgrade acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import importlib.metadata
import json
from pathlib import Path
import time
from typing import Any, Callable

EXPECTED = {"agent-manifest": "0.15.0", "agentrust-trace": "0.11.0"}
REPRESENTATION = "kv"


def require_exact_versions(version: Callable[[str], str] = importlib.metadata.version) -> dict[str, str]:
    installed = {name: version(name) for name in EXPECTED}
    if installed != EXPECTED:
        raise RuntimeError(f"unqualified dependency pair: expected {EXPECTED}, installed {installed}")
    return installed


def probe_manifest_delta(checkpoint: Any, merkletree: Any, verify: Callable[..., Any]) -> dict[str, Any]:
    """Test the actual 0.15 append binding with four negative controls."""
    at = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    initial = [
        {"op": "PUT", "key": "alpha", "value": 1},
        {"op": "PUT", "key": "beta", "value": 2},
    ]
    appended = {"op": "DEL", "key": "alpha"}
    full = [*initial, appended]
    prev = checkpoint.from_ops(initial, REPRESENTATION, seq=7, approved_at=at,
                               ttl_seconds=3600, max_delta_fraction=1.0)
    new = checkpoint.from_ops(full, REPRESENTATION, seq=8, approved_at=at,
                              ttl_seconds=3600, max_delta_fraction=1.0)
    proof = merkletree(full, REPRESENTATION).consistency_proof(prev.tree_size)

    def call(ops: list[dict], evidence: list) -> Any:
        return verify(prev, new, ops, evidence, representation=REPRESENTATION,
                      now=at + timedelta(seconds=5))

    cases = {
        "valid_single_append": call([appended], proof),
        "wrong_appended_operation": call([{"op": "PUT", "key": "wrong", "value": 9}], proof),
        "empty_append": call([], proof),
        "whole_log_instead_of_append": call(full, proof),
        "missing_consistency_proof": call([appended], []),
    }
    if not cases["valid_single_append"].accepted or cases["valid_single_append"].reason != "accepted":
        raise AssertionError("0.15.0 rejected the valid append; this candidate is not qualified")
    for name in ("wrong_appended_operation", "empty_append", "whole_log_instead_of_append",
                 "missing_consistency_proof"):
        value = cases[name]
        if value.accepted or value.reason != "drift":
            raise AssertionError(f"0.15.0 did not reject {name} as drift: {value!r}")
    return {
        "representation": REPRESENTATION,
        "valid_append": "accepted",
        "negative_controls": {name: "drift" for name in cases if name != "valid_single_append"},
        "supplied_operation_bytes_checked": True,
        "operation_metadata_outside_leaf_encoder_authenticated": False,
        "authority_effect": "none",
    }


def probe_trace(sign_record: Callable, generate_key: Callable,
                validate_json: Callable, verify_record: Callable) -> dict[str, Any]:
    """Run 0.11 signed-record path, without claiming citation resolution."""
    key = generate_key()
    record = {
        "eat_profile": "tag:agentrust-io.com,2026:trace-v0.2",
        "iat": int(time.time()),
        "subject": "spiffe://example.test/agent/dependency-migration",
        "model": {"provider": "example", "model_id": "migration-probe"},
        "runtime": {"platform": "software-only", "measurement": "sha256:" + "0" * 64},
        "policy": {"bundle_hash": "sha256:" + "b" * 64,
                   "enforcement_mode": "declared"},
        "data_class": "internal",
        "build_provenance": {"slsa_level": 1, "digest": "sha256:" + "e" * 64},
        "appraisal": {"status": "none", "verifier": "https://verifier.example.test"},
    }
    signed = sign_record(record, key)
    validate_json(signed)
    verdict = verify_record(signed, public_key_or_jwk=key.public_key())
    if verdict is None or getattr(verdict, "revocation", None) is None:
        raise AssertionError("TRACE verification did not report explicit revocation state")
    if getattr(verdict, "citations", None) is None:
        raise AssertionError("TRACE 0.11 citation result is missing")
    return {
        "signed_record_verified": True,
        "revocation_state_reported": True,
        "citation_resolver_supplied": False,
        "citation_bytes_authenticated": False,
        "policy_enforcement_claimed": False,
        "authority_effect": "none",
    }


def run(revision: str) -> dict[str, Any]:
    installed = require_exact_versions()
    from agent_manifest._memory_delta import MemoryCheckpoint, memory_merkletree, verify_delta
    from agentrust_trace import generate_key, sign_record, validate_json, verify_record
    manifest = probe_manifest_delta(MemoryCheckpoint, memory_merkletree, verify_delta)
    trace = probe_trace(sign_record, generate_key, validate_json, verify_record)
    return {
        "schema_version": "1.0.0",
        "artifact_type": "agent-memory-unaccepted-dependency-migration-preflight",
        "issue": 826,
        "source_revision": revision,
        "installed_versions": installed,
        "checks": {"agent_manifest": manifest, "trace": trace},
        "accepted_baseline_modified": False,
        "accepted_comparator_modified": False,
        "authority_effect": "none",
        "disposition": "candidate_preflight_only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-revision", required=True, help="Exact Agent Memory SHA")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if len(args.source_revision) != 40 or any(c not in "0123456789abcdef" for c in args.source_revision):
        parser.error("--source-revision requires a lowercase 40-character commit SHA")
    report = run(args.source_revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
