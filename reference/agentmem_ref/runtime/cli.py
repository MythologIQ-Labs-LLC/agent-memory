"""Installed command surface for the Agent Memory reference runtime."""

from __future__ import annotations

import argparse
import json
import sys

from .discovery import DiscoveryInputError
from .doctor import (
    DiagnosticInputError,
    diagnose,
    discover_configuration_file,
    validate_configuration_file,
)
from .runtime_config import RuntimeConfigurationError


def _emit(value: dict, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    if value.get("command") == "config_validate":
        print("Configuration: valid")
        print(f"Digest: {value['configuration_digest']}")
        print(f"Entry mode: {value['entry_mode']}")
        print(
            "Canonical owner: "
            f"{value['canonical_owner_component_id']} / {value['canonical_owner_capability_id']}"
        )
        print(f"Routes: {value['route_count']}")
        print(f"Required projections: {', '.join(value['required_projection_ids']) or 'none'}")
        print("Authority effect: none")
        return
    if value.get("command") == "discover":
        print(f"Entry mode: {value['entry_mode']}")
        print(f"Configured components: {len(value['configured_subjects']['components'])}")
        print(f"Configured governance peers: {len(value['configured_subjects']['governance_peers'])}")
        print(f"Declared probes: {value['probe_count']}")
        print(f"Startability from declared probes: {value['startability']}")
        for result in value["results"]:
            print(
                f"- {result['probe_id']}: {result['subject_id']} "
                f"{result['probe_kind']} -> {result['status']}"
            )
        print("Configuration mutated: false")
        print("Authority effect: none")
        return
    print(f"Configuration: {value['configuration']['status']}")
    print(f"Durable state: {value['durable_state']['status']}")
    print(f"Recovery: {value['recovery']['status']}")
    print(f"Currentness: {value['currentness']['status']}")
    print(f"Provider availability: {value['provider_availability']['status']}")
    print(f"Configuration startable: {str(value['configuration_startable']).lower()}")
    print(f"Operational readiness: {value['operational_readiness']}")
    print("Authority effect: none")


def _failure(command: str, exc: Exception, *, json_output: bool) -> int:
    value = {
        "schema_version": "1.0.0",
        "command": command,
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-memory",
        description="Validate, discover, diagnose, and evaluate the Agent Memory reference runtime.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    config = subcommands.add_parser("config", help="runtime configuration operations")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    validate = config_sub.add_parser("validate", help="validate one portable runtime configuration")
    validate.add_argument("--config", required=True, help="path to a JSON serialization of the runtime contract")
    validate.add_argument("--qualifications", help="path to normalized independent qualification bindings")
    validate.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    discover = subcommands.add_parser(
        "discover",
        help="observe explicitly declared existing-stack signals without mutating configuration",
    )
    discover.add_argument("--config", required=True, help="path to a JSON serialization of the runtime contract")
    discover.add_argument("--probes", required=True, help="path to an explicit read-only provider probe manifest")
    discover.add_argument("--qualifications", help="path to normalized independent qualification bindings")
    discover.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    doctor = subcommands.add_parser("doctor", help="diagnose configuration and bounded durable-state recovery")
    doctor.add_argument("--config", required=True, help="path to a JSON serialization of the runtime contract")
    doctor.add_argument("--qualifications", help="path to normalized independent qualification bindings")
    doctor.add_argument("--state-dir", help="Agent Memory bounded reference state directory to inspect/recover")
    doctor.add_argument("--probe", action="store_true", help="execute explicitly declared read-only provider probes")
    doctor.add_argument("--probes", help="path to an explicit read-only provider probe manifest")
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    benchmark = subcommands.add_parser(
        "benchmark",
        help="discover profiles and validate or compare Memory Evaluation evidence",
    )
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command", required=True)

    benchmark_list = benchmark_sub.add_parser(
        "list",
        help="list repository-owned benchmark profiles",
    )
    benchmark_list.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    benchmark_validate = benchmark_sub.add_parser(
        "validate",
        help="validate one common memory-benchmark run manifest",
    )
    benchmark_validate.add_argument("report", help="path to a memory-benchmark run JSON report")
    benchmark_validate.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    benchmark_compare = benchmark_sub.add_parser(
        "compare",
        help="compare two compatible common memory-benchmark run manifests",
    )
    benchmark_compare.add_argument("baseline", help="path to the baseline run JSON report")
    benchmark_compare.add_argument("candidate", help="path to the candidate run JSON report")
    benchmark_compare.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    json_output = bool(getattr(args, "json", False))
    try:
        if args.command == "config" and args.config_command == "validate":
            value = validate_configuration_file(
                args.config,
                qualification_path=args.qualifications,
            )
            _emit(value, json_output=json_output)
            return 0
        if args.command == "discover":
            value = discover_configuration_file(
                args.config,
                probe_path=args.probes,
                qualification_path=args.qualifications,
            )
            _emit(value, json_output=json_output)
            if value["startability"] == "blocked_by_required_probe":
                return 1
            return 0
        if args.command == "doctor":
            if args.probes and not args.probe:
                raise DiagnosticInputError("doctor --probes requires --probe")
            value = diagnose(
                args.config,
                qualification_path=args.qualifications,
                state_dir=args.state_dir,
                probe_path=args.probes,
                probe=args.probe,
            )
            _emit(value, json_output=json_output)
            if value["recovery"].get("status") == "failed_closed":
                return 1
            if value["currentness"].get("status") == "degraded":
                return 1
            if value["provider_availability"].get("startability") == "blocked_by_required_probe":
                return 1
            return 0
        if args.command == "benchmark":
            from ..evaluation.cli import emit as emit_benchmark
            from ..evaluation.cli import execute as execute_benchmark

            value = execute_benchmark(
                args.benchmark_command,
                report=getattr(args, "report", None),
                baseline=getattr(args, "baseline", None),
                candidate=getattr(args, "candidate", None),
            )
            emit_benchmark(value, json_output=json_output)
            return 0
    except (
        DiagnosticInputError,
        DiscoveryInputError,
        RuntimeConfigurationError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return _failure(args.command, exc, json_output=json_output)
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
