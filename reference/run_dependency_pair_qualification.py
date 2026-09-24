#!/usr/bin/env python
"""Qualify the exact Agent Manifest + TRACE dependency pair for #440.

This gate is intentionally non-skippable. If either package is absent or at the
wrong version, the process fails before reporting qualification evidence.

The external packages remain evidence/interoperability peers. Their successful
verification does not create Agent Memory recall, lifecycle, or mutation
authority.
"""

from __future__ import annotations

import argparse
import copy
import importlib.metadata
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema

from agent_manifest._memory_delta import (
    MemoryCheckpoint,
    memory_merkletree,
    verify_delta,
)
from agentrust_trace import generate_key, sign_record, validate_json, verify_record


AGENT_MANIFEST_VERSION = "0.12.0"
AGENT_MANIFEST_TAG = "python-v0.12.0"
AGENT_MANIFEST_TAG_OBJECT = "ed11fef5d02c7d8a6d57b24c7b92509342522445"
AGENT_MANIFEST_SOURCE_COMMIT = "9478b56cc349bef01441db4e17e61849c8d69d6f"

TRACE_VERSION = "0.10.0"
TRACE_TAG = "v0.10.0"
TRACE_TAG_OBJECT = "d7a9310395e135e2b5ca52b09fc79e74af6c1ce2"
TRACE_SOURCE_COMMIT = "3a561d84d752794b9afa994ce16ed35c24ac0acb"


def _agent_manifest_checks() -> dict[str, object]:
    approved_at = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)
    before_ops = [
        {"op": "PUT", "key": "alpha", "value": 1},
        {"op": "PUT", "key": "beta", "value": 2},
    ]
    appended = {"op": "DEL", "key": "alpha"}
    after_ops = [*before_ops, appended]

    previous = MemoryCheckpoint.from_ops(
        before_ops,
        "kv",
        seq=7,
        approved_at=approved_at,
        ttl_seconds=3600,
        max_delta_fraction=1.0,
    )
    current = MemoryCheckpoint.from_ops(
        after_ops,
        "kv",
        seq=8,
        approved_at=approved_at,
        ttl_seconds=3600,
        max_delta_fraction=1.0,
    )
    tree = memory_merkletree(after_ops, "kv")
    proof = tree.consistency_proof(previous.tree_size)

    accepted = verify_delta(
        previous,
        current,
        [appended],
        proof,
        now=approved_at + timedelta(seconds=5),
    )
    if not accepted.accepted or accepted.reason != "accepted":
        raise AssertionError(f"0.12.0 normal delta rejected: {accepted!r}")

    # 0.12.0 limitation, deliberately executable rather than softened in prose:
    # verify_delta accepts an `ops` argument but does not bind those supplied
    # operation bytes to the checkpoint advance. Upstream main fixed this later
    # with representation-aware verify_consistency_append(). Agent Memory must
    # therefore keep operation semantics in its own signed evidence and MUST NOT
    # infer them from a 0.12.0 accepted checkpoint verdict.
    mismatched_ops = [{"op": "PUT", "key": "not-alpha", "value": "different"}]
    mismatched = verify_delta(
        previous,
        current,
        mismatched_ops,
        proof,
        now=approved_at + timedelta(seconds=5),
    )
    if not mismatched.accepted or mismatched.reason != "accepted":
        raise AssertionError(
            "expected exact 0.12.0 operation-binding limitation was not observed; "
            "the dependency contract may have changed"
        )

    return {
        "normal_checkpoint_advance": "accepted",
        "supplied_operation_argument_bound": False,
        "mismatched_supplied_operation_verdict": mismatched.reason,
        "agent_memory_interpretation": (
            "checkpoint_integrity_evidence_only; operation semantics remain bound "
            "by Agent Memory portable evidence"
        ),
        "authority_effect": "none",
    }


def _trace_record() -> tuple[dict, object]:
    key = generate_key()
    record = {
        "eat_profile": "tag:agentrust-io.com,2026:trace-v0.2",
        "iat": int(time.time()),
        "subject": "spiffe://example.test/agent/dependency-pair-qualification",
        "model": {"provider": "example", "model_id": "qualification-model"},
        "runtime": {
            "platform": "software-only",
            "measurement": "sha256:" + "0" * 64,
        },
        "policy": {
            "bundle_hash": "sha256:" + "b" * 64,
            "enforcement_mode": "enforce",
        },
        "data_class": "internal",
        "build_provenance": {
            "slsa_level": 1,
            "digest": "sha256:" + "e" * 64,
        },
        "appraisal": {
            "status": "none",
            "verifier": "https://verifier.example.test",
        },
    }
    return sign_record(record, key), key.public_key()


def _trace_checks() -> dict[str, object]:
    signed, trusted_key = _trace_record()
    validate_json(signed)
    verification = verify_record(signed, public_key_or_jwk=trusted_key)

    if verification is None:
        raise AssertionError(
            "TRACE 0.10.0 verify_record must return an explicit VerificationResult"
        )
    revocation = getattr(verification, "revocation", None)
    if revocation is None:
        raise AssertionError(
            "TRACE 0.10.0 VerificationResult must expose revocation-check state"
        )

    private_jwk = copy.deepcopy(signed)
    private_jwk["cnf"]["jwk"]["d"] = (
        "nWGxne_9WmC6hEr0kuwsxERJxWl7MmkZcDusAxyuf2A"
    )
    private_rejected = False
    try:
        validate_json(private_jwk)
    except jsonschema.ValidationError:
        private_rejected = True
    if not private_rejected:
        raise AssertionError("TRACE 0.10.0 schema accepted private cnf.jwk material")

    return {
        "valid_signed_record_schema": "accepted",
        "private_cnf_jwk_rejected": True,
        "verify_record_returns_explicit_result": True,
        "revocation_state_reported": True,
        "gap_disclosure_semantics": (
            "upstream receipt-chain capability; not imported as Agent Memory memory authority"
        ),
        "authority_effect": "none",
    }


def run(agent_memory_commit: str) -> dict[str, object]:
    installed = {
        "agent-manifest": importlib.metadata.version("agent-manifest"),
        "agentrust-trace": importlib.metadata.version("agentrust-trace"),
    }
    expected = {
        "agent-manifest": AGENT_MANIFEST_VERSION,
        "agentrust-trace": TRACE_VERSION,
    }
    if installed != expected:
        raise AssertionError(
            f"dependency pair drift: expected {expected!r}, observed {installed!r}"
        )

    checks = {
        "agent_manifest": _agent_manifest_checks(),
        "trace": _trace_checks(),
    }
    executed_checks = 7

    return {
        "artifact_type": "agent-memory-dependency-pair-qualification",
        "schema_version": "1.0.0",
        "issue": 440,
        "agent_memory_commit": agent_memory_commit,
        "pair": {
            "agent_manifest": {
                "package": f"agent-manifest=={AGENT_MANIFEST_VERSION}",
                "tag": AGENT_MANIFEST_TAG,
                "tag_object": AGENT_MANIFEST_TAG_OBJECT,
                "source_commit": AGENT_MANIFEST_SOURCE_COMMIT,
            },
            "trace": {
                "package": f"agentrust-trace=={TRACE_VERSION}",
                "tag": TRACE_TAG,
                "tag_object": TRACE_TAG_OBJECT,
                "source_commit": TRACE_SOURCE_COMMIT,
            },
        },
        "execution": {
            "installed_versions": installed,
            "qualification_checks_executed": executed_checks,
            "qualification_checks_skipped": 0,
            "silent_skip_possible": False,
        },
        "checks": checks,
        "security_semantics": {
            "agent_manifest_0_12": [
                "independent hardware appraisal required for attestation_verified",
                "audit_key_sealed enforced when attestation is required",
                "timestamp and memory-baseline TTL parsing fail closed",
                "HITL approval_method is signature-bound",
                "TPM AK-chain appraisal uses shared certificate-chain verification",
                "nested omissions cannot bypass full-binding requirements",
            ],
            "trace_0_10": [
                "private cnf.jwk material rejected by schema verification path",
                "revocation-bundle verification returns explicit check state",
                "action-receipt gap disclosure is distinct from silent missing receipt",
                "canonicalization and delegation conformance coverage expanded",
            ],
        },
        "known_limitations": [
            "agent-manifest 0.12.0 checkpoint acceptance does not bind the supplied appended operation argument to the new checkpoint root",
            "TRACE gap-disclosure semantics are not Agent Memory lifecycle or mutation authority",
            "a passing external verifier establishes bounded evidence only",
        ],
        "interpretation": {
            "external_evidence_authority_effect": "none",
            "memory_authority": "Agent Memory",
            "aggregate_health_score": None,
        },
        "passed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run(args.agent_memory_commit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
