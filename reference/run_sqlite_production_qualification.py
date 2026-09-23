#!/usr/bin/env python
"""Emit bounded RC1 qualification evidence for the SQLite canonical substrate.

This is operational characterization plus structural invariants. It does not
turn benchmark latency into authority, and it does not claim distributed or
multi-host durability. The output is exact-revision bound so a later runtime or
SQLite environment must earn its own evidence.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.restart_runtime import (
    CapabilityBinding,
    RuntimeCheckpointConflict,
    RuntimeProfile,
)
from agentmem_ref.runtime_config import validate_runtime_configuration
from agentmem_ref.sqlite_composition import SQLiteConfiguredCompositionRuntime
from agentmem_ref.sqlite_runtime import (
    SQLITE_DURABILITY_PROFILE,
    SQLITE_TRANSACTION_PROTOCOL,
    SQLiteRestartSafeRuntime,
)
from agentmem_ref.sqlite_substrate import (
    SQLITE_SOURCE_RIGHTS,
    SQLITE_SUBSTRATE_PROFILE,
    SQLITE_SUBSTRATE_SCHEMA_VERSION,
    SQLiteTemporalGraph,
)
from agentmem_ref.substrate import Fact


SCHEMA_VERSION = "1.0.0"
QUALIFICATION_ID = "agent-memory-sqlite-production-substrate"
TENANT = "tenant:sqlite-qualification"
PROJECT = "project:sqlite-qualification"


def _binding() -> CapabilityBinding:
    return CapabilityBinding(
        component_id="reference-governed-memory",
        component_version="1.0.0",
        capability_id="governed-memory-core",
        capability_version="1.0.0",
        maturity="reference_qualified",
        evidence_ref="evidence:reference-runtime-core-v1",
    )


def _profile() -> RuntimeProfile:
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="sqlite-single-host-rc1",
        profile_version="1.0.0",
        bindings=(_binding(),),
    )


def _proposal(index: int, *, target: str | None = None) -> policy.Proposal:
    memory_ref = target or f"memory:qualification:{index}"
    return policy.Proposal(
        proposal_id=f"proposal:qualification:{index}",
        actor_id="agent:sqlite-qualification",
        charter_version="charter-v1",
        target_reference=memory_ref,
        target_class=policy.M2,
        scope=TENANT,
        operation="promotion",
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=(f"evidence:qualification:{index}", "session:qualification"),
        tenant_ref=TENANT,
        isolation_domain_refs=(TENANT, PROJECT),
        required_isolation_domain_refs=(PROJECT,),
        project_ref=PROJECT,
        purpose="sqlite-production-qualification",
    )


def _context() -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, PROJECT),
        principal_ref="agent:sqlite-qualification",
        project_ref=PROJECT,
        purpose="sqlite-production-qualification",
    )


def _ms(start_ns: int, end_ns: int) -> float:
    return round((end_ns - start_ns) / 1_000_000.0, 6)


def _latency_summary(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    rows = sorted(values)

    def percentile(fraction: float) -> float:
        index = min(len(rows) - 1, max(0, int(round((len(rows) - 1) * fraction))))
        return round(rows[index], 6)

    return {
        "count": len(rows),
        "min_ms": round(rows[0], 6),
        "p50_ms": percentile(0.50),
        "p95_ms": percentile(0.95),
        "max_ms": round(rows[-1], 6),
    }


def _storage_bytes(database_path: Path) -> int:
    return sum(
        path.stat().st_size
        for path in database_path.parent.glob(database_path.name + "*")
        if path.is_file()
    )


def _rollback_probe(root: Path) -> bool:
    graph = SQLiteTemporalGraph(root / "rollback.sqlite3")
    try:
        try:
            with graph.transaction():
                graph.write_fact(
                    Fact(
                        uuid="fact:must-roll-back",
                        fact_text="interrupted write",
                        group_id=TENANT,
                    )
                )
                raise RuntimeError("simulated interruption")
        except RuntimeError as exc:
            if str(exc) != "simulated interruption":
                raise
        return graph.get_fact("fact:must-roll-back") is None
    finally:
        graph.close()


def _configured_authority_probe(root: Path, runtime_config_path: Path) -> dict:
    config_value = json.loads(runtime_config_path.read_text(encoding="utf-8"))
    plan = validate_runtime_configuration(config_value)
    runtime = SQLiteConfiguredCompositionRuntime.create(root, tenant=TENANT, plan=plan)
    try:
        retained = runtime.retain(
            _proposal(9000, target="memory:authority-probe"),
            "authority probe value",
        )
        if not retained.committed or not retained.fact_uuid:
            raise RuntimeError("configured SQLite authority probe did not commit")
        result = runtime.multi_route_recall(
            "authority probe",
            _context(),
            logical_memory_refs=("memory:authority-probe",),
        )
        route_effects = sorted(
            {hit.authority_effect for hits in result.route_hits.values() for hit in hits}
        )
        return {
            "runtime_authority_effect": result.authority_effect,
            "route_authority_effects": route_effects,
            "admitted": retained.fact_uuid in result.admitted,
            "passes": result.authority_effect == "none" and route_effects in ([], ["none"]),
        }
    finally:
        runtime.close()


def run_qualification(
    *,
    root: Path,
    runtime_config_path: Path,
    agent_memory_revision: str,
    write_count: int = 40,
    read_count: int = 80,
) -> dict:
    if len(agent_memory_revision) != 40:
        raise ValueError("agent_memory_revision must be an exact 40-hex commit")
    if write_count < 1 or read_count < 1:
        raise ValueError("write_count and read_count must be positive")

    runtime_root = root / "runtime"
    profile = _profile()
    init_start = time.perf_counter_ns()
    runtime = SQLiteRestartSafeRuntime.create(runtime_root, tenant=TENANT, profile=profile)
    init_end = time.perf_counter_ns()

    database_path = runtime.database_path
    identity = runtime.substrate.operational_identity()
    initial_storage = _storage_bytes(database_path)
    write_latencies: list[float] = []
    retained_ids: list[str] = []

    for index in range(write_count):
        started = time.perf_counter_ns()
        result = runtime.commit_proposal(
            _proposal(index),
            f"qualification durable value {index}",
        )
        ended = time.perf_counter_ns()
        if not result.committed or not result.fact_uuid:
            raise RuntimeError(f"qualification write did not commit: {index}")
        write_latencies.append(_ms(started, ended))
        retained_ids.append(result.fact_uuid)

    storage_after_writes = _storage_bytes(database_path)
    generation_before_restart = runtime.recovery_evidence.generation
    substrate_digest_before_restart = runtime.substrate.state_digest()
    runtime.close()

    recovery_start = time.perf_counter_ns()
    recovered = SQLiteRestartSafeRuntime.recover(runtime_root, profile=profile)
    recovery_end = time.perf_counter_ns()
    recovered.substrate.integrity_check()
    read_latencies: list[float] = []
    read_hits = 0
    for index in range(read_count):
        target = index % write_count
        started = time.perf_counter_ns()
        result = recovered.adapter.governed_recall(
            f"qualification durable value {target}",
            _context(),
        )
        ended = time.perf_counter_ns()
        read_latencies.append(_ms(started, ended))
        if retained_ids[target] in result.admitted:
            read_hits += 1

    substrate_digest_after_restart = recovered.substrate.state_digest()

    # Two recovered writers start from one generation. The second must fail
    # after the first commits a newer generation.
    stale_writer = SQLiteRestartSafeRuntime.recover(runtime_root, profile=profile)
    winner = recovered.commit_proposal(
        _proposal(write_count, target="memory:stale-writer-winner"),
        "winner value",
    )
    if not winner.committed:
        raise RuntimeError("stale-writer winner did not commit")
    stale_writer_refused = False
    try:
        stale_writer.commit_proposal(
            _proposal(write_count + 1, target="memory:stale-writer-loser"),
            "loser value",
        )
    except RuntimeCheckpointConflict:
        stale_writer_refused = True
    finally:
        stale_writer.close()

    backup_path = root / "backup" / "agent-memory.sqlite3"
    backup_start = time.perf_counter_ns()
    recovered.backup_to(backup_path)
    backup_end = time.perf_counter_ns()
    recovered.close()

    backup = SQLiteTemporalGraph(backup_path)
    try:
        backup.integrity_check()
        backup_restore_ok = all(backup.get_fact(fact_ref) is not None for fact_ref in retained_ids)
        backup_fact_count = len(tuple(backup.all_facts()))
    finally:
        backup.close()

    rollback_ok = _rollback_probe(root)
    authority_probe = _configured_authority_probe(root / "configured", runtime_config_path)

    invariants = {
        "exact_revision_bound": len(agent_memory_revision) == 40,
        "journal_mode_wal": identity["journal_mode"] == "wal",
        "synchronous_full": identity["synchronous"] == "2",
        "restart_digest_stable": substrate_digest_before_restart == substrate_digest_after_restart,
        "restart_generation_preserved": generation_before_restart >= 1,
        "governed_read_hit_rate_complete": read_hits == read_count,
        "stale_writer_refused": stale_writer_refused,
        "interrupted_transaction_rolled_back": rollback_ok,
        "backup_restored": backup_restore_ok,
        "retrieval_authority_effect_none": bool(authority_probe["passes"]),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "agent_memory_revision": agent_memory_revision,
        "claim": "production_credible_single_host_canonical_substrate_rc1",
        "non_claims": [
            "not a distributed database qualification",
            "not a multi-host consensus or network-partition proof",
            "not a universal Agent Memory storage mandate",
            "latency measurements are bounded diagnostics, not service-level objectives",
        ],
        "runtime_identity": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "sqlite_library_version": identity["sqlite_version"],
            "source_rights": SQLITE_SOURCE_RIGHTS,
        },
        "profile": {
            "substrate_profile": SQLITE_SUBSTRATE_PROFILE,
            "substrate_schema_version": SQLITE_SUBSTRATE_SCHEMA_VERSION,
            "durability_profile": SQLITE_DURABILITY_PROFILE,
            "transaction_protocol": SQLITE_TRANSACTION_PROTOCOL,
            "journal_mode": identity["journal_mode"],
            "synchronous": identity["synchronous"],
            "deployment_topology": "single_host_local_filesystem",
        },
        "configuration": {
            "write_count": write_count,
            "read_count": read_count,
            "runtime_config_sha256": __import__("hashlib").sha256(
                runtime_config_path.read_bytes()
            ).hexdigest(),
        },
        "operational_characterization": {
            "initialization_ms": _ms(init_start, init_end),
            "recovery_ms": _ms(recovery_start, recovery_end),
            "durable_write_latency": _latency_summary(write_latencies),
            "governed_read_latency": _latency_summary(read_latencies),
            "backup_ms": _ms(backup_start, backup_end),
            "initial_storage_bytes": initial_storage,
            "storage_after_writes_bytes": storage_after_writes,
            "storage_growth_bytes": storage_after_writes - initial_storage,
            "backup_database_bytes": backup_path.stat().st_size,
            "backup_fact_count": backup_fact_count,
        },
        "authority_probe": authority_probe,
        "structural_invariants": invariants,
        "all_structural_invariants_pass": all(invariants.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--runtime-config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--write-count", type=int, default=40)
    parser.add_argument("--read-count", type=int, default=80)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="agent-memory-sqlite-qualification-") as temp:
        report = run_qualification(
            root=Path(temp),
            runtime_config_path=Path(args.runtime_config).resolve(),
            agent_memory_revision=args.agent_memory_revision,
            write_count=args.write_count,
            read_count=args.read_count,
        )

    if not report["all_structural_invariants_pass"]:
        failed = [
            key for key, passed in report["structural_invariants"].items() if not passed
        ]
        raise SystemExit(f"SQLite qualification invariants failed: {failed}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
