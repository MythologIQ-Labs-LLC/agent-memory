"""CLI helpers for benchmark integration discovery, validation, and common evidence utilities.

Commands:

* ``list``                 repository-owned benchmark integrations (descriptor projections);
* ``inspect``              one committed integration with its resolved Gauntlet relationship;
* ``validate-integration`` one descriptor file, without executing anything it names;
* ``validate``             one common memory-benchmark run manifest;
* ``compare``              two compatible run manifests, fail-closed;
* ``lanes``                frozen same-harness comparator lanes;
* ``validate-lane``        one lane freeze file, cross-checked against the registry, no execution.

Every report retains ``authority_effect: none``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .._paths import REPO_ROOT
from .benchmark_integration import BenchmarkIntegrationError, integration_digest, load_integration
from .contract import compare_runs, load_run, run_digest
from .registry import (
    check_evidence_binding,
    get_integration,
    list_profiles,
    profile_view,
    resolve_gauntlet_relationship,
)
from .same_harness_lane import SameHarnessLaneError, lane_digest, list_lanes, load_lane, resolve_lane

SCHEMA_VERSION = "1.1.0"


def list_report() -> dict[str, Any]:
    profiles = list_profiles()
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "benchmark_list",
        "profile_count": len(profiles),
        "profiles": profiles,
        "authority_effect": "none",
    }


def _integration_report(command: str, descriptor: dict[str, Any], *, path: str | None) -> dict[str, Any]:
    relationship = resolve_gauntlet_relationship(descriptor)
    evidence = check_evidence_binding(descriptor, repo_root=REPO_ROOT)
    identity_findings: list[str] = []
    inputs = descriptor["input_contract"]
    if inputs["known_input_sha256"] is None and not inputs["input_may_be_absent_before_execution"]:
        identity_findings.append("committed input without known digest")
    if inputs["known_input_sha256"] is None:
        identity_findings.append(
            "no static input digest: comparability is established per run from benchmark.input_sha256 in each result"
        )
    if descriptor["benchmark"]["source_revision"] == "unbound":
        identity_findings.append("source revision is manifest-bound per run, not static")
    for row in evidence:
        if not row["bound"]:
            identity_findings.append(f"evidence {row['variant']}: {row.get('error', 'unbound')}")
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "valid": True,
        "path": path,
        "integration_id": descriptor["integration_id"],
        "integration_digest_sha256": integration_digest(descriptor),
        "contract_version": descriptor["contract_version"],
        "admission_state": descriptor["admission_state"],
        "benchmark": descriptor["benchmark"],
        "provenance_class": descriptor["benchmark"]["provenance_class"],
        "invocation_surface": descriptor["system_requirements"]["invocation_surface"],
        "external_system_entry": descriptor["system_requirements"]["external_system_entry"],
        "credentials": descriptor["provider_requirements"]["credentials"],
        "runner": descriptor["native_protocol"]["runner"],
        "gauntlet": relationship,
        "evidence_binding": evidence,
        "identity_findings": identity_findings,
        "mapped_dimensions": sorted({m["dimension"] for m in descriptor["normalization"]["mappings"]}),
        "unmapped_dimensions": descriptor["normalization"]["unmapped_dimensions"],
        "negative_control_count": len(descriptor["evaluator_integrity"]["negative_controls"]),
        "executed": False,
        "descriptor": descriptor,
        "authority_effect": "none",
    }


def inspect_report(integration_id: str) -> dict[str, Any]:
    descriptor = get_integration(integration_id)
    report = _integration_report("benchmark_inspect", descriptor, path=None)
    report["profile"] = profile_view(descriptor)
    return report


def validate_integration_report(path: str | Path) -> dict[str, Any]:
    descriptor = load_integration(path)
    return _integration_report("benchmark_validate_integration", descriptor, path=str(path))


def _lane_summary(lane: dict[str, Any]) -> dict[str, Any]:
    return {
        "lane_id": lane["lane_id"],
        "status": lane["status"],
        "owning_issue": lane["owning_issue"],
        "frozen_on": lane["frozen_on"],
        "benchmark_integration": lane["benchmark_integration"],
        "harness_revision": lane["harness"]["revision"],
        "dataset": f"{lane['dataset']['harness_dataset']}/{lane['dataset']['split']}",
        "input_sha256": lane["dataset"]["input_sha256"],
        "evaluator_mode": lane["evaluator"]["mode"],
        "llm_calls": lane["evaluator"]["llm_calls"],
        "rows": [
            {"row_id": row["row_id"], "system_id": row["system_id"], "role": row["role"], "status": row["status"], "provider_key": row["provider_key"]}
            for row in lane["systems"]
        ],
        "lane_digest_sha256": lane_digest(lane),
    }


def lanes_report() -> dict[str, Any]:
    lanes = list_lanes()
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "benchmark_lanes",
        "lane_count": len(lanes),
        "lanes": [_lane_summary(lane) for lane in lanes],
        "executed": False,
        "authority_effect": "none",
    }


def validate_lane_report(path: str | Path) -> dict[str, Any]:
    lane = load_lane(path)
    resolution = resolve_lane(lane)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "benchmark_validate_lane",
        "valid": True,
        "path": str(path),
        "lane_id": lane["lane_id"],
        "status": lane["status"],
        "lane_digest_sha256": resolution["lane_digest_sha256"],
        "resolution": resolution,
        "summary": _lane_summary(lane),
        "findings": list(lane.get("findings", [])),
        "executed": False,
        "lane": lane,
        "authority_effect": "none",
    }


def validate_report(path: str | Path) -> dict[str, Any]:
    document = load_run(path)
    measured_dimensions = [
        dimension_id
        for dimension_id, dimension in document["dimensions"].items()
        if dimension["status"] in {"measured", "partial"}
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "benchmark_validate",
        "valid": True,
        "path": str(path),
        "run_id": document["run_id"],
        "run_status": document["status"],
        "benchmark": document["benchmark"],
        "system": document["system"],
        "measured_dimensions": measured_dimensions,
        "run_digest_sha256": run_digest(document),
        "authority_effect": "none",
    }


def compare_report(baseline_path: str | Path, candidate_path: str | Path) -> dict[str, Any]:
    baseline = load_run(baseline_path)
    candidate = load_run(candidate_path)
    comparison = compare_runs(baseline, candidate)
    comparison["command"] = "benchmark_compare"
    comparison["baseline_path"] = str(baseline_path)
    comparison["candidate_path"] = str(candidate_path)
    return comparison


def execute(
    command: str,
    *,
    report: str | None = None,
    baseline: str | None = None,
    candidate: str | None = None,
    integration: str | None = None,
    manifest: str | None = None,
    lane: str | None = None,
) -> dict[str, Any]:
    if command == "list":
        return list_report()
    if command == "lanes":
        return lanes_report()
    if command == "validate-lane":
        if not lane:
            raise ValueError("benchmark validate-lane requires a lane path")
        return validate_lane_report(lane)
    if command == "inspect":
        if not integration:
            raise ValueError("benchmark inspect requires an integration id")
        return inspect_report(integration)
    if command == "validate-integration":
        if not manifest:
            raise ValueError("benchmark validate-integration requires a descriptor path")
        return validate_integration_report(manifest)
    if command == "validate":
        if not report:
            raise ValueError("benchmark validate requires a report path")
        return validate_report(report)
    if command == "compare":
        if not baseline or not candidate:
            raise ValueError("benchmark compare requires baseline and candidate paths")
        return compare_report(baseline, candidate)
    raise ValueError(f"unsupported benchmark command: {command}")


def _emit_integration(value: dict[str, Any], *, title: str) -> None:
    print(title)
    print(f"Integration: {value['integration_id']} [{value['admission_state']}] contract {value['contract_version']}")
    benchmark = value["benchmark"]
    print(f"Benchmark: {benchmark['id']} ({benchmark['name']}) @ {benchmark['source_revision']}")
    print(f"Provenance class: {value['provenance_class']}")
    runner = value["runner"]
    print(f"Runner: {runner['entry_point']} [{runner['kind']}]")
    print(f"System invocation: {value['invocation_surface']} / external entry: {value['external_system_entry']}")
    print(f"Credentials: {value['credentials']}")
    gauntlet = value["gauntlet"]
    print(f"Gauntlet: {gauntlet['relationship']} ({gauntlet['status']})" + (f" -> {gauntlet['profile_id']}" if gauntlet.get("profile_id") else ""))
    print(f"Mapped dimensions: {', '.join(value['mapped_dimensions']) or 'none'}")
    for dimension, reason in sorted(value["unmapped_dimensions"].items()):
        print(f"  unmapped {dimension}: {reason}")
    print(f"Negative controls declared: {value['negative_control_count']}")
    for row in value["evidence_binding"]:
        state = "bound" if row["bound"] else f"UNBOUND ({row.get('error')})"
        print(f"  evidence {row['variant']}: {state}")
    for finding in value["identity_findings"]:
        print(f"  identity: {finding}")
    print(f"Descriptor digest: {value['integration_digest_sha256']}")
    print("Executed: no")
    print("Authority effect: none")


def emit(value: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(value, indent=2, sort_keys=True))
        return

    command = value.get("command")
    if command == "benchmark_list":
        print(f"Benchmark integrations: {value['profile_count']}")
        for profile in value["profiles"]:
            dimensions = ", ".join(profile["dimensions"])
            print(
                f"- {profile['profile_id']} [{profile['provenance_class']}; {profile['admission_state']}] "
                f"issue #{profile['owning_issue']}"
            )
            print(f"  runner: {profile['runner']} ({profile['runner_kind']})")
            print(f"  system entry: {profile['invocation_surface']} / {profile['external_system_entry']}")
            print(f"  evidence: {profile['external_evidence_status']}")
            for item in profile.get("external_evidence", ()):
                print(f"    - {item['variant']}: {item['status']}")
            gauntlet = profile["gauntlet"]
            print(f"  gauntlet: {gauntlet['relationship']}" + (f" -> {gauntlet['profile_id']}" if gauntlet.get("profile_id") else ""))
            print(f"  dimensions: {dimensions or 'none'}")
        print("Authority effect: none")
        return

    if command == "benchmark_inspect":
        _emit_integration(value, title="Benchmark integration")
        return

    if command == "benchmark_validate_integration":
        _emit_integration(value, title="Benchmark integration descriptor: valid")
        return

    if command in {"benchmark_lanes", "benchmark_validate_lane"}:
        lanes = value["lanes"] if command == "benchmark_lanes" else [value["summary"]]
        print("Same-harness lanes: " + (str(value["lane_count"]) if command == "benchmark_lanes" else "valid"))
        for lane in lanes:
            print(f"- {lane['lane_id']} [{lane['status']}] issue #{lane['owning_issue']} frozen {lane['frozen_on']}")
            print(f"  integration: {lane['benchmark_integration']} @ {lane['harness_revision']}")
            print(f"  dataset: {lane['dataset']} input {lane['input_sha256']}")
            print(f"  evaluator: {lane['evaluator_mode']} (llm_calls={str(lane['llm_calls']).lower()})")
            for row in lane["rows"]:
                print(f"    {row['role']:<10} {row['system_id']:<14} [{row['status']}] provider {row['provider_key']}")
            print(f"  freeze digest: {lane['lane_digest_sha256']}")
        if command == "benchmark_validate_lane":
            for finding in value["findings"]:
                print(f"  finding: {finding}")
        print("Executed: no")
        print("Authority effect: none")
        return

    if command == "benchmark_validate":
        print("Benchmark report: valid")
        print(f"Run: {value['run_id']} ({value['run_status']})")
        print(f"Benchmark: {value['benchmark']['id']} @ {value['benchmark']['source_revision']}")
        print(f"System: {value['system']['id']} @ {value['system']['revision']}")
        print(f"Measured dimensions: {', '.join(value['measured_dimensions']) or 'none'}")
        print(f"Digest: {value['run_digest_sha256']}")
        print("Authority effect: none")
        return

    if command == "benchmark_compare":
        print("Benchmark comparison: comparable")
        identity = value["comparison_identity"]
        print(f"Benchmark: {identity['benchmark_id']} @ {identity['source_revision']}")
        print(f"Baseline: {value['baseline']['system']['id']} ({value['baseline']['run_id']})")
        print(f"Candidate: {value['candidate']['system']['id']} ({value['candidate']['run_id']})")
        for dimension_id, rows in value["dimensions"].items():
            comparable = [row for row in rows if row.get("comparison_state") in {"comparable", "comparable_non_numeric"}]
            if not comparable:
                continue
            print(f"{dimension_id}:")
            for row in comparable:
                if "delta" in row:
                    print(
                        f"  {row['metric_id']}: {row['baseline_value']} -> {row['candidate_value']} "
                        f"(delta {row['delta']:+g}, {row['outcome']})"
                    )
                else:
                    print(
                        f"  {row['metric_id']}: {row['baseline_value']!r} -> "
                        f"{row['candidate_value']!r} ({row['outcome']})"
                    )
        print("Authority effect: none")
        return

    raise ValueError(f"unsupported benchmark output command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-memory benchmark",
        description=(
            "Discover and validate Memory Evaluation benchmark integrations and validate or "
            "compare benchmark evidence. Nothing here executes a benchmark."
        ),
    )
    commands = parser.add_subparsers(dest="benchmark_command", required=True)
    listing = commands.add_parser("list", help="list repository-owned benchmark integrations")
    listing.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    inspect = commands.add_parser("inspect", help="inspect one committed benchmark integration")
    inspect.add_argument("integration", help="benchmark integration id (see list)")
    inspect.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    validate_integration = commands.add_parser(
        "validate-integration",
        help="validate one benchmark integration descriptor without executing it",
    )
    validate_integration.add_argument("manifest", help="path to a memory-benchmark-integration JSON descriptor")
    validate_integration.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    lanes = commands.add_parser("lanes", help="list frozen same-harness comparator lanes")
    lanes.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    validate_lane = commands.add_parser("validate-lane", help="validate one same-harness lane freeze without executing it")
    validate_lane.add_argument("lane", help="path to a same-harness-lane JSON file")
    validate_lane.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    validate = commands.add_parser("validate", help="validate one common memory-benchmark run manifest")
    validate.add_argument("report", help="path to a memory-benchmark run JSON report")
    validate.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    compare = commands.add_parser("compare", help="compare two compatible common memory-benchmark run manifests")
    compare.add_argument("baseline", help="path to the baseline run JSON report")
    compare.add_argument("candidate", help="path to the candidate run JSON report")
    compare.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def _failure(command: str, exc: Exception, *, json_output: bool) -> int:
    value = {
        "schema_version": SCHEMA_VERSION,
        "command": f"benchmark_{command.replace('-', '_')}",
        "valid": False,
        "status": "refused",
        "error": str(exc),
        "authority_effect": "none",
    }
    if json_output:
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        print(f"Refused: {exc}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        value = execute(
            args.benchmark_command,
            report=getattr(args, "report", None),
            baseline=getattr(args, "baseline", None),
            candidate=getattr(args, "candidate", None),
            integration=getattr(args, "integration", None),
            manifest=getattr(args, "manifest", None),
            lane=getattr(args, "lane", None),
        )
    except (BenchmarkIntegrationError, SameHarnessLaneError, KeyError, TypeError, ValueError) as exc:
        return _failure(args.benchmark_command, exc, json_output=args.json)
    emit(value, json_output=args.json)
    return 0
