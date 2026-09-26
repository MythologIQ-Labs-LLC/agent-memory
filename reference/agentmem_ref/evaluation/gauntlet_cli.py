"""Public CLI for the Agent Memory Gauntlet orchestration layer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .gauntlet_contract import GauntletContractError, manifest_digest
from .gauntlet_orchestrator import load_adapter_manifest, run_gauntlet
from .gauntlet_profiles import get_gauntlet_profile, list_gauntlet_profiles


def _list_report() -> dict[str, Any]:
    profiles = list_gauntlet_profiles()
    return {
        "schema_version": "0.1.0",
        "command": "gauntlet_list",
        "profile_count": len(profiles),
        "profiles": profiles,
        "authority_effect": "none",
    }


def _inspect_report(profile_id: str) -> dict[str, Any]:
    profile = get_gauntlet_profile(profile_id)
    return {
        "schema_version": "0.1.0",
        "command": "gauntlet_inspect",
        "profile": profile,
        "authority_effect": "none",
    }


def _validate_adapter_report(path: str | Path) -> dict[str, Any]:
    manifest = load_adapter_manifest(path)
    return {
        "schema_version": "0.1.0",
        "command": "gauntlet_validate_adapter",
        "valid": True,
        "path": str(path),
        "system": manifest["system"],
        "adapter": manifest["adapter"],
        "transport": manifest["transport"],
        "capabilities": manifest["capabilities"],
        "manifest_digest_sha256": manifest_digest(manifest),
        "authority_effect": "none",
    }


def execute(
    command: str,
    *,
    profile_id: str | None = None,
    manifest_path: str | None = None,
    output_dir: str | None = None,
    allow_external_process: bool = False,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    if command == "list":
        return _list_report()
    if command == "inspect":
        if not profile_id:
            raise ValueError("gauntlet inspect requires a profile id")
        return _inspect_report(profile_id)
    if command == "validate-adapter":
        if not manifest_path:
            raise ValueError("gauntlet validate-adapter requires a manifest path")
        return _validate_adapter_report(manifest_path)
    if command == "run":
        if not profile_id or not manifest_path:
            raise ValueError("gauntlet run requires --profile and --system")
        return run_gauntlet(
            manifest_path,
            profile_id,
            output_dir=output_dir or "./gauntlet-runs",
            allow_external_process=allow_external_process,
            timeout_seconds=timeout_seconds,
        )
    raise ValueError(f"unsupported gauntlet command: {command}")


def emit(value: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(value, indent=2, sort_keys=True))
        return

    command = value.get("command")
    if command == "gauntlet_list":
        print(f"Gauntlet profiles: {value['profile_count']}")
        for profile in value["profiles"]:
            print(f"- {profile['profile_id']} [{profile['kind']}]")
            print(f"  {profile['description']}")
        print("Authority effect: none")
        return
    if command == "gauntlet_inspect":
        profile = value["profile"]
        print(f"Profile: {profile['profile_id']} [{profile['kind']}]")
        print(profile["description"])
        print("Required capabilities:")
        for capability, support in sorted(profile["requirements"]["requires"].items()):
            print(f"  - {capability}: {', '.join(support)}")
        print("Authority effect: none")
        return
    if command == "gauntlet_validate_adapter":
        print("Gauntlet adapter: valid")
        print(f"System: {value['system']['id']} @ {value['system']['revision']}")
        print(f"Adapter: {value['adapter']['id']} @ {value['adapter']['revision']}")
        print(f"Transport: {value['transport']['kind']}")
        print(f"Digest: {value['manifest_digest_sha256']}")
        print("Authority effect: none")
        return

    if "profile" in value and "negotiation" in value and "run_id" in value:
        print(f"Gauntlet run: {value['run_id']}")
        print(f"Profile: {value['profile']['profile_id']}")
        print(f"System: {value['system']['id']} @ {value['system']['revision']}")
        print(f"Negotiation: {value['negotiation']['outcome']}")
        print(f"Execution: {value['status']}")
        if value.get("failure"):
            failure = value["failure"]
            print(f"Failure: {failure['source']} / {failure['code']}: {failure['message']}")
        normalized = value.get("artifacts", {}).get("normalized_run")
        if normalized:
            print(f"Normalized evidence: {normalized['path']}")
        print("Authority effect: none")
        return

    raise ValueError("unsupported Gauntlet output shape")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-memory gauntlet",
        description=(
            "Qualify system-neutral memory adapters through capability-negotiated "
            "Agent Memory Gauntlet profiles."
        ),
    )
    commands = parser.add_subparsers(dest="gauntlet_command", required=True)

    listing = commands.add_parser("list", help="list executable Gauntlet profiles")
    listing.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    inspect = commands.add_parser("inspect", help="inspect one Gauntlet profile")
    inspect.add_argument("profile", help="Gauntlet profile id")
    inspect.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    validate = commands.add_parser(
        "validate-adapter", help="validate one Gauntlet system-adapter manifest without executing it"
    )
    validate.add_argument("manifest", help="path to the adapter manifest JSON")
    validate.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    run = commands.add_parser("run", help="execute one system against one Gauntlet profile")
    run.add_argument("--system", required=True, help="path to the adapter manifest JSON")
    run.add_argument("--profile", required=True, help="Gauntlet profile id")
    run.add_argument(
        "--output-dir",
        default="./gauntlet-runs",
        help="root directory for reconstructable run evidence (default: ./gauntlet-runs)",
    )
    run.add_argument(
        "--allow-external-process",
        action="store_true",
        help="explicitly permit execution of a stdio adapter startup command",
    )
    run.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="stdio response timeout per operation (default: 10)",
    )
    run.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def _failure(command: str, exc: Exception, *, json_output: bool) -> int:
    value = {
        "schema_version": "0.1.0",
        "command": f"gauntlet_{command.replace('-', '_')}",
        "valid": False,
        "status": "invalid",
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
    command = args.gauntlet_command
    try:
        value = execute(
            command,
            profile_id=getattr(args, "profile", None),
            manifest_path=getattr(args, "manifest", None) or getattr(args, "system", None),
            output_dir=getattr(args, "output_dir", None),
            allow_external_process=bool(getattr(args, "allow_external_process", False)),
            timeout_seconds=float(getattr(args, "timeout_seconds", 10.0)),
        )
    except (GauntletContractError, KeyError, TypeError, ValueError) as exc:
        return _failure(command, exc, json_output=bool(getattr(args, "json", False)))
    emit(value, json_output=bool(getattr(args, "json", False)))
    if command == "run" and value.get("status") != "complete":
        return 1
    return 0


__all__ = ["execute", "emit", "main"]
