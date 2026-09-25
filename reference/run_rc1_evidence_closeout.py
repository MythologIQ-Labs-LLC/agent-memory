#!/usr/bin/env python
"""Emit a revision-bound RC1 evidence closeout manifest.

The manifest intentionally keeps product usability, retrieval quality, performance,
governance, recovery, external benchmark comparability, and harvest status separate.
It is release evidence, not a universal health score.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA_VERSION = "1.0.1"
ARTIFACT_ID = "agent-memory-rc1-evidence-closeout"
CONTRACT_VERSION = "1.2.0"
RUNTIME_PROFILE = "sqlite_single_host_v1"


def _require_revision(value: str) -> str:
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError("agent_memory_revision must be exact lowercase 40-hex")
    return value


def build_manifest(agent_memory_revision: str) -> dict:
    revision = _require_revision(agent_memory_revision)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "agent_memory_revision": revision,
        "contract_version": CONTRACT_VERSION,
        "runtime_profile": RUNTIME_PROFILE,
        "status_model": ["complete", "bounded", "active_open", "external_blocked", "not_claimed"],
        "product_usability": {
            "status": "bounded",
            "evidence": [
                {"issue": 477, "pull_request": 478, "claim": "developer facade and supported SQLite open/recovery path"},
                {"issue": 479, "pull_request": 480, "claim": "deterministic end-to-end cognitive-memory lifecycle"},
            ],
            "limitations": [
                "single-host SQLite RC profile",
                "not production 1.0 readiness",
            ],
        },
        "quality": {
            "status": "bounded",
            "evidence": [
                {"issue": 465, "pull_request": 466, "claim": "continuous retrieval and memory regression contract"},
                {"issue": 467, "pull_request": 469, "claim": "real 99-query / 100-gold-edge SWE-ContextBench runner compatibility"},
            ],
            "limitations": [
                "repository-owned deterministic fixtures are not a substitute for a protocol-comparable external benchmark run",
                "no external SWE-ContextBench result is claimed here",
            ],
        },
        "performance": {
            "status": "bounded",
            "evidence": [
                {"issue": 427, "pull_request": 452, "claim": "bounded single-host SQLite substrate qualification"},
                {"issue": 465, "pull_request": 466, "claim": "benchmark performance fields remain separately reported"},
            ],
            "limitations": [
                "no distributed or multi-host SQLite claim",
                "no universal latency or resource envelope is claimed",
            ],
        },
        "governance": {
            "status": "bounded",
            "evidence": [
                {"issue": 463, "pull_request": 464, "claim": "metabolism signals remain proposals/evidence rather than authority"},
                {"issue": 440, "pull_request": 476, "claim": "Agent Manifest 0.12.0 and TRACE 0.10.0 exact-version qualification"},
                {"issue": 479, "pull_request": 480, "claim": "wrong-scope refusal and confidence non-authority in product scenario"},
            ],
            "limitations": [
                "external peer verification never creates Agent Memory mutation or recall-admission authority",
                "checkpoint acceptance does not establish appended-operation semantics",
            ],
        },
        "runtime_recovery": {
            "status": "bounded",
            "evidence": [
                {"issue": 427, "pull_request": 452, "claim": "SQLite single-host durability qualification"},
                {"issue": 479, "pull_request": 480, "claim": "correction, forgetting, history, tombstone and configuration recovery across restart"},
            ],
            "limitations": [
                "bounded to the qualified single-host runtime profile",
            ],
        },
        "external_benchmark": {
            "status": "external_blocked",
            "issue": 467,
            "protocol_runner_ready": True,
            "required_external_inputs": [
                "exact frozen redacted past-task projection",
                "exact batch and distractor selection",
                "consistency-query identity when explicitly selected",
            ],
            "comparability": "not_yet_protocol_comparable",
            "claim": "runner readiness is complete; measurement is not",
        },
        "harvest_closeout": {
            "status": "active_open",
            "issue": 470,
            "claim": "planned native-harvest sequence is complete, exhaustive ancestry and source-rights closeout is actively continuing",
            "dependency_effect": "does_not_block_repository_owned_rc_evidence_packaging",
            "external_dependency_required": False,
        },
        "known_limitations": [
            "RC evidence is bounded to the current qualified single-host profile",
            "no external SWE-ContextBench comparison is claimed until exact frozen inputs and provenance are available",
            "exhaustive ancestry harvesting remains open and active under issue 470",
            "physical permanent-deletion completion is not established by the reversible pruning path used in the RC product scenario",
            "answer-generation quality is not inferred from retrieval-only evidence",
            "no learned retrieval controller owns governance, durable commit, deletion, tenancy, or recall admission",
        ],
        "non_claims": [
            "production_1_0_readiness",
            "distributed_sqlite_durability",
            "protocol_comparable_external_benchmark_result",
            "exhaustive_ancestry_harvest_completion",
            "aggregate_memory_health_score",
            "external_peer_authority",
        ],
    }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.agent_memory_revision)
    Path(args.output).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
