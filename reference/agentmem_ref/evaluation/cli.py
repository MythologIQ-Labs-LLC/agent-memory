"""CLI helpers for benchmark profile discovery and common evidence utilities."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .contract import compare_runs, load_run, run_digest
from .registry import list_profiles


def list_report() -> dict[str, Any]:
    profiles = list_profiles()
    return {
        "schema_version": "1.0.0",
        "command": "benchmark_list",
        "profile_count": len(profiles),
        "profiles": profiles,
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
        "schema_version": "1.0.0",
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


def execute(command: str, *, report: str | None = None, baseline: str | None = None, candidate: str | None = None) -> dict[str, Any]:
    if command == "list":
        return list_report()
    if command == "validate":
        if not report:
            raise ValueError("benchmark validate requires a report path")
        return validate_report(report)
    if command == "compare":
        if not baseline or not candidate:
            raise ValueError("benchmark compare requires baseline and candidate paths")
        return compare_report(baseline, candidate)
    raise ValueError(f"unsupported benchmark command: {command}")


def emit(value: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(value, indent=2, sort_keys=True))
        return

    command = value.get("command")
    if command == "benchmark_list":
        print(f"Benchmark profiles: {value['profile_count']}")
        for profile in value["profiles"]:
            dimensions = ", ".join(profile["dimensions"])
            print(
                f"- {profile['profile_id']} [{profile['implementation_status']}] "
                f"issue #{profile['owning_issue']}"
            )
            print(f"  runner: {profile['runner']}")
            print(f"  evidence: {profile['external_evidence_status']}")
            for item in profile.get("external_evidence", ()):
                print(f"    - {item['variant']}: {item['status']}")
            print(f"  dimensions: {dimensions}")
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
        description="Discover Memory Evaluation profiles and validate or compare benchmark evidence.",
    )
    commands = parser.add_subparsers(dest="benchmark_command", required=True)
    listing = commands.add_parser("list", help="list repository-owned benchmark profiles")
    listing.add_argument("--json", action="store_true", help="emit machine-readable JSON")
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
        "schema_version": "1.0.0",
        "command": f"benchmark_{command}",
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
        )
    except (KeyError, TypeError, ValueError) as exc:
        return _failure(args.benchmark_command, exc, json_output=args.json)
    emit(value, json_output=args.json)
    return 0
