#!/usr/bin/env python
"""Qualify cMCP 0.5.0 as an Agent Memory external-evidence peer.

This is deliberately additive to the historical cMCP 0.4.0 comparator. It
executes the released 0.5.0 package, binds normalized records to that exact peer,
and probes security-semantic changes that matter at the Agent Memory boundary.
A peer verifier remains evidence only and never becomes memory authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import rfc8785
from cmcp_runtime.audit.keys import SigningKey
from cmcp_runtime.audit.trace_claim import (
    AttestationReportInfo,
    CallGraphSummary,
    CallSummary,
    PolicyBundleInfo,
    ToolCatalogInfo,
    generate_trace_claim,
)
from cmcp_runtime.catalog.loader import load_catalog
from cmcp_runtime.errors import ConfigError
from cmcp_runtime.policy.bundle import _canonical_bundle_hash
from cmcp_verify import ApprovedHashes, verify_trace_claim

from agentmem_ref.cmcp_external_evidence import normalize_cmcp_claim_for_source

CMCP_PACKAGE = "cmcp-runtime==0.5.0"
CMCP_RELEASE = "v0.5.0"
CMCP_SOURCE_COMMIT = "d03b9af504535d3d43f192bc6d9eff89b8afd12f"
CMCP_VERIFIER_ID = "cmcp-verify==0.5.0"
TRACE_PACKAGE = "agentrust-trace==0.10.0"
AGENT_MANIFEST_PACKAGE = "agent-manifest==0.12.0"
POLICY_HASH = "sha256:" + "a" * 64
CATALOG_HASH = "sha256:" + "b" * 64
AUDIT_ROOT = "c" * 64
AUDIT_TIP = "d" * 64


def _require_revision(value: str) -> str:
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError("agent_memory_commit must be exact lowercase 40-hex")
    return value


def _verification_dict(result) -> dict:
    return {
        "status": result.status.value,
        "verified_fields": list(result.verified_fields),
        "unverified_fields": list(result.unverified_fields),
        "failure_reason": result.failure_reason.value if result.failure_reason else None,
        "attestation_age_seconds": result.attestation_age_seconds,
        "is_attestation_fresh": result.is_attestation_fresh,
        "details": dict(result.details),
    }


def _claim(mode: str = "enforce") -> tuple[dict, SigningKey]:
    key = SigningKey()
    now = datetime.now(tz=UTC)
    claim = generate_trace_claim(
        session_id=f"agent-memory-cmcp-050-{mode}",
        signing_key=key,
        attestation_report=AttestationReportInfo(
            provider="software-only",
            measurement="sha256:" + "0" * 64,
            report_data="",
            attestation_generated_at=now.isoformat(),
            attestation_validity_seconds=3600,
        ),
        policy_bundle=PolicyBundleInfo(
            hash=POLICY_HASH,
            enforcement_mode={"enforce": "enforcing", "advisory": "advisory", "silent": "silent"}[mode],
            policy_version="cmcp-policy-v050",
        ),
        tool_catalog=ToolCatalogInfo(hash=CATALOG_HASH, drift_detected=False),
        call_summary=CallSummary(
            tool_calls_total=2,
            tool_calls_allowed=2,
            tool_calls_denied=0,
            tool_calls_faulted=0,
            tools_invoked=["records.read", "network.send"],
            session_max_sensitivity="restricted",
            call_graph_summary=CallGraphSummary(
                compliance_domains_touched=["hipaa_phi", "external"],
                cross_boundary_events=[
                    {
                        "source_domain": "hipaa_phi",
                        "destination_domain": "external",
                        "tool_name": "network.send",
                    }
                ],
                edges_represent="temporal_adjacency",
            ),
        ),
        audit_chain_root=AUDIT_ROOT,
        audit_chain_tip=AUDIT_TIP,
        audit_chain_length=2,
    )
    return claim.model_dump(exclude_none=True), key


def _verify(claim: dict, key: SigningKey, *, policy_hash: str = POLICY_HASH):
    return verify_trace_claim(
        claim,
        ApprovedHashes(policy_bundle_hash=policy_hash, tool_catalog_hash=CATALOG_HASH),
        max_attestation_age_seconds=3600,
        trusted_public_key_hex=key.public_key_hex,
    )


def _normalize(claim: dict, projected: dict) -> tuple[dict, dict]:
    return normalize_cmcp_claim_for_source(
        claim,
        projected,
        observed_at=datetime.now(tz=UTC).isoformat(),
        source_version=CMCP_PACKAGE,
        source_release_ref=CMCP_SOURCE_COMMIT,
        verifier_id=CMCP_VERIFIER_ID,
    )


def _catalog_probe() -> dict:
    definition = {
        "description": "Retrieve a bounded benchmark record",
        "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}},
    }
    canonical_definition = json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()
    entry = {
        "tool_name": "records.read",
        "server": {
            "display_name": "Benchmark Records",
            "url": "https://records.example.invalid/mcp",
            "tls_fingerprint": "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "transport": "http-sse",
            "rotation_mode": "cert-pinned",
        },
        "approved_definition": definition,
        "definition_hash": "sha256:" + hashlib.sha256(canonical_definition).hexdigest(),
        "compliance_domain": "hipaa_phi",
        "requires_baa": True,
        "sensitivity_level": "restricted",
        "added_at": "2026-09-24T00:00:00Z",
        "approved_by": "agent-memory-qualification",
    }
    with tempfile.TemporaryDirectory(prefix="cmcp-050-catalog-") as temporary:
        path = Path(temporary) / "catalog.json"
        path.write_text(json.dumps([entry]), encoding="utf-8")
        catalog = load_catalog(str(path))
        loaded = catalog.require("records.read")

        custom = copy.deepcopy(entry)
        custom["compliance_domain"] = "clinical_research"
        path.write_text(json.dumps([custom]), encoding="utf-8")
        undeclared_failed_closed = False
        try:
            load_catalog(str(path))
        except ConfigError:
            undeclared_failed_closed = True
        custom_catalog = load_catalog(
            str(path), extra_compliance_domains=frozenset({"clinical_research"})
        )
        custom_loaded = custom_catalog.require("records.read")

    return {
        "cert_pinned_rotation_mode_reachable": loaded.server.rotation_mode == "cert-pinned",
        "builtin_regulated_domain_accepted": loaded.compliance_domain == "hipaa_phi",
        "undeclared_custom_domain_fails_closed": undeclared_failed_closed,
        "declared_custom_domain_accepted": custom_loaded.compliance_domain == "clinical_research",
    }


def _policy_hash_probe() -> dict:
    manifest_a = {
        "version": "1.2.0",
        "authored_at": "2026-09-24T00:00:00Z",
        "author_identity": "Renée <renee@example.invalid>",
        "commit_sha": "1" * 40,
        "approval_chain": [],
    }
    manifest_b = {
        "commit_sha": "1" * 40,
        "approval_chain": [],
        "author_identity": "Renée <renee@example.invalid>",
        "authored_at": "2026-09-24T00:00:00Z",
        "version": "1.2.0",
    }
    policy_files_a = {"b.cedar": "permit(principal, action, resource);", "a.cedar": "forbid(principal, action, resource);"}
    policy_files_b = {"a.cedar": policy_files_a["a.cedar"], "b.cedar": policy_files_a["b.cedar"]}
    schema = '{"Example": {"type": "Record", "attributes": {}}}'
    first = _canonical_bundle_hash(manifest_a, policy_files_a, schema)
    second = _canonical_bundle_hash(manifest_b, policy_files_b, schema)

    policy_hashes = {
        name: hashlib.sha256(content.encode()).hexdigest()
        for name, content in sorted(policy_files_a.items())
    }
    manual = hashlib.sha256(
        rfc8785.dumps(
            {
                "manifest": manifest_a,
                "policy_files": policy_hashes,
                "schema_hash": hashlib.sha256(schema.encode()).hexdigest(),
            }
        )
    ).hexdigest()
    return {
        "order_independent": first == second,
        "matches_independent_rfc8785_projection": first == manual,
        "hash": "sha256:" + first,
        "non_ascii_identity_exercised": True,
    }


def run(agent_memory_commit: str) -> dict:
    revision = _require_revision(agent_memory_commit)
    installed = {
        "cmcp-runtime": importlib.metadata.version("cmcp-runtime"),
        "agentrust-trace": importlib.metadata.version("agentrust-trace"),
        "agent-manifest": importlib.metadata.version("agent-manifest"),
    }
    expected = {
        "cmcp-runtime": "0.5.0",
        "agentrust-trace": "0.10.0",
        "agent-manifest": "0.12.0",
    }
    if installed != expected:
        raise RuntimeError(f"wrong qualification environment: installed={installed} expected={expected}")

    claim, key = _claim("enforce")
    projected = _verification_dict(_verify(claim, key))
    enforcement, attestation = _normalize(claim, projected)

    mismatch = _verification_dict(
        _verify(claim, key, policy_hash="sha256:" + "f" * 64)
    )
    mismatch_enforcement, _ = _normalize(claim, mismatch)

    signed_graph = claim["gateway"]["call_summary"]["call_graph_summary"]
    normalized_render = json.dumps([enforcement, attestation], sort_keys=True)
    catalog = _catalog_probe()
    policy_hash = _policy_hash_probe()

    checks = {
        "runtime_claim_reports_050": claim["gateway"]["gateway_version"] == "0.5.0",
        "released_verifier_executes": projected["status"] in {"verified", "partially_verified"},
        "software_only_not_promoted_to_hardware": attestation["verification"]["status"] == "unknown",
        "normalized_source_is_exact_050": (
            enforcement["source"]["version"] == CMCP_PACKAGE
            and enforcement["source"]["release_ref"] == CMCP_SOURCE_COMMIT
        ),
        "policy_hash_mismatch_fails_enforcement": (
            mismatch["failure_reason"] == "POLICY_HASH_MISMATCH"
            and mismatch_enforcement["applicability"]["status"] == "invalid"
        ),
        "regulated_domains_present_in_signed_peer_claim": (
            signed_graph["compliance_domains_touched"] == ["hipaa_phi", "external"]
            and len(signed_graph["cross_boundary_events"]) == 1
        ),
        "regulated_domain_detail_not_silently_promoted_into_agent_memory_record": (
            "hipaa_phi" not in normalized_render and "network.send" not in normalized_render
        ),
        "cert_pinned_rotation_reachable": catalog["cert_pinned_rotation_mode_reachable"],
        "builtin_regulated_domain_accepted": catalog["builtin_regulated_domain_accepted"],
        "undeclared_custom_domain_fails_closed": catalog["undeclared_custom_domain_fails_closed"],
        "declared_custom_domain_accepted": catalog["declared_custom_domain_accepted"],
        "rfc8785_policy_hash_order_independent": policy_hash["order_independent"],
        "rfc8785_policy_hash_matches_independent_projection": policy_hash["matches_independent_rfc8785_projection"],
        "external_verifier_has_no_authority_effect": enforcement["interpretation"]["authority_effect"] == "none",
    }

    report = {
        "schema_version": "1.0.0",
        "qualification": "cmcp-0.5.0-agent-memory-external-evidence",
        "agent_memory_commit": revision,
        "peer": {
            "release": CMCP_RELEASE,
            "source_commit": CMCP_SOURCE_COMMIT,
            "runtime_package": CMCP_PACKAGE,
            "verifier_id": CMCP_VERIFIER_ID,
            "trace_package": TRACE_PACKAGE,
            "agent_manifest_package": AGENT_MANIFEST_PACKAGE,
            "installed": installed,
        },
        "verification": projected,
        "normalized": {"enforcement": enforcement, "attestation": attestation},
        "regulated_domain_probe": {
            "signed_claim_graph": signed_graph,
            "agent_memory_disposition": "preserve as peer claim integrity only; no field-level compliance-domain authority imported by this adapter",
        },
        "catalog_probe": catalog,
        "policy_hash_probe": policy_hash,
        "checks": checks,
        "passed": all(checks.values()),
        "non_claims": [
            "cmcp_verification_is_not_agent_memory_authority",
            "signed_compliance_domain_is_not_memory_access_authority",
            "signed_cross_boundary_event_is_not_execution_witness",
            "software_only_claim_is_not_hardware_attestation",
            "cert_pinned_reachability_is_not_certificate_chain_verification",
            "peer_policy_hash_integrity_is_not_pama_satisfaction",
        ],
    }
    if not report["passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise AssertionError(f"cMCP 0.5.0 qualification failed: {failed}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(args.agent_memory_commit)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
