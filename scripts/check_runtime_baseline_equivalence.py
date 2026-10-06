#!/usr/bin/env python3
"""Check a candidate checkout against the current Runtime Baseline.

The baseline register (``reports/runtime/baseline-register.json``) names the current
baseline; its source boundary names the protected paths and the explicit non-runtime
exclusions. The outcome is one of three states:

* ``PASS``: the candidate's protected surface is byte-equal to the frozen revision.
* ``TRANSITION``: the register declares a successor and the candidate's protected
  surface equals the frozen surface plus exactly the blobs the declaration pins; every
  declared identity delta holds at both ends and no undeclared identity moved.
* failure (exit 1): anything else, with the first failing check named.

A transition is a pinned identity, not a relaxation: the candidate's protected tree is a
function of the frozen revision and the declaration. Published records are never edited;
a successor is a new record, boundary and register entry (docs/67).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime_baseline_identity import (  # noqa: E402
    IDENTITY_SOURCES,
    IdentitySource,
    read_identities,
    record_identities,
    record_value,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER = Path("reports/runtime/baseline-register.json")
DECLARATION_SCHEMA = Path("schemas/runtime-baseline-declaration.schema.json")

STATE_PASS = "PASS"
STATE_TRANSITION = "TRANSITION"
STATE_FAIL = "FAIL"
EXIT_CODES = {STATE_PASS: 0, STATE_TRANSITION: 0, STATE_FAIL: 1}

ENTRY_KEYS = {
    "baseline_id",
    "record",
    "record_blob",
    "source_boundary",
    "source_boundary_blob",
    "public_gauntlet_manifest",
    "qualification",
    "published_commit",
}


@dataclass(frozen=True)
class Outcome:
    state: str
    baseline_id: str
    frozen_revision: str
    message: str


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def _read_json(root: Path, path: Path | str, label: str) -> Any:
    try:
        return json.loads((root / path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"unable to load {label} {path}: {exc}") from exc


def load_register(root: Path, path: Path | str = DEFAULT_REGISTER) -> dict[str, Any]:
    value = _read_json(root, path, "runtime baseline register")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise SystemExit("runtime baseline register must be an object with schema_version 1")
    baselines = value.get("baselines")
    if not isinstance(baselines, list) or not baselines:
        raise SystemExit("runtime baseline register must list at least one baseline")
    seen: set[str] = set()
    for entry in baselines:
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            raise SystemExit(f"runtime baseline register entry must carry exactly {sorted(ENTRY_KEYS)}")
        if not isinstance(entry["baseline_id"], str) or entry["baseline_id"] in seen:
            raise SystemExit("runtime baseline register entries must carry unique baseline_id strings")
        seen.add(entry["baseline_id"])
        for key in ("record_blob", "source_boundary_blob"):
            if not _is_sha(entry[key]):
                raise SystemExit(f"runtime baseline register {key} must be an exact lowercase 40-hex blob")
        qualification = entry["qualification"]
        if not isinstance(qualification, dict) or set(qualification) != {"path", "pointer", "blob"}:
            raise SystemExit("runtime baseline register qualification must carry path, pointer and blob")
        if not _is_sha(qualification["blob"]):
            raise SystemExit("runtime baseline register qualification.blob must be an exact lowercase 40-hex blob")
        published = entry["published_commit"]
        if published is not None and not _is_sha(published):
            raise SystemExit("runtime baseline register published_commit must be null or an exact lowercase 40-hex commit")
    declared = value.get("declared_successor")
    if declared is not None:
        if not isinstance(declared, dict) or set(declared) != {"baseline_id", "declaration"}:
            raise SystemExit("runtime baseline register declared_successor must carry baseline_id and declaration")
    return value


def current_entry(register: dict[str, Any]) -> dict[str, Any]:
    return register["baselines"][-1]


def load_boundary(root: Path, path: Path | str) -> dict[str, Any]:
    value = _read_json(root, path, "runtime source boundary")
    if not isinstance(value, dict):
        raise SystemExit("runtime source boundary root must be an object")
    if value.get("baseline_mutation") is not False:
        raise SystemExit("runtime source boundary must explicitly state baseline_mutation=false")
    if value.get("authority_effect") != "none":
        raise SystemExit("runtime source boundary must retain authority_effect=none")
    frozen = value.get("frozen_revision")
    if not _is_sha(frozen):
        raise SystemExit("runtime source boundary frozen_revision must be exact lowercase 40-hex")
    protected = value.get("protected_paths")
    if not isinstance(protected, list) or not protected or not all(isinstance(item, str) and item for item in protected):
        raise SystemExit("runtime source boundary protected_paths must be a non-empty string list")
    excluded = value.get("excluded_non_runtime_paths")
    if not isinstance(excluded, list):
        raise SystemExit("runtime source boundary excluded_non_runtime_paths must be a list")
    for item in excluded:
        if not isinstance(item, dict) or not isinstance(item.get("pathspec"), str):
            raise SystemExit("each excluded_non_runtime_paths entry requires a pathspec")
        pathspec = item["pathspec"]
        if not pathspec.startswith(":(exclude)"):
            raise SystemExit(f"excluded pathspec must be a Git exclude pathspec: {pathspec}")
    return value


def require_commit(root: Path, revision: str, label: str) -> None:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit(f"{label} commit is unavailable: {revision}: {result.stderr.strip()}")


def diff_pathspecs(boundary: dict[str, Any]) -> list[str]:
    pathspecs = [str(item) for item in boundary["protected_paths"]]
    pathspecs.extend(str(item["pathspec"]) for item in boundary["excluded_non_runtime_paths"])
    return pathspecs


def changed_paths(root: Path, boundary: dict[str, Any], candidate: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", str(boundary["frozen_revision"]), candidate, "--", *diff_pathspecs(boundary)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit("unable to compare candidate checkout with the Runtime Baseline: " + result.stderr.strip())
    return sorted(line for line in result.stdout.splitlines() if line)


def candidate_blob(root: Path, candidate: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{candidate}:{path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        return None
    return result.stdout.strip()


def load_declaration(root: Path, path: Path | str, schema_path: Path | str = DECLARATION_SCHEMA) -> dict[str, Any]:
    import jsonschema

    declaration = _read_json(root, path, "runtime baseline declaration")
    schema = _read_json(root, schema_path, "runtime baseline declaration schema")
    try:
        jsonschema.Draft202012Validator(schema).validate(declaration)
    except jsonschema.ValidationError as exc:
        raise SystemExit(f"runtime baseline declaration {path} is invalid: {exc.message}") from exc
    paths = [item["path"] for item in declaration["declared_changes"]]
    if len(set(paths)) != len(paths):
        raise SystemExit(f"runtime baseline declaration {path} lists a path twice")
    return declaration


def qualification_block(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    qualification = entry["qualification"]
    document = _read_json(root, qualification["path"], "runtime baseline qualification")
    pointer = qualification["pointer"]
    block = record_value(document, pointer) if pointer else document
    if not isinstance(block, dict) or block.get("status") not in {"pending", "complete"}:
        raise SystemExit(f"runtime baseline qualification for {entry['baseline_id']} must carry status pending or complete")
    return block


def declaration_open_failures(
    root: Path, register: dict[str, Any], record: dict[str, Any], declaration: dict[str, Any]
) -> list[str]:
    """Checks a declaration must pass before anything about the candidate is read."""

    entry = current_entry(register)
    successor = declaration["baseline_id"]
    failures: list[str] = []
    if qualification_block(root, entry)["status"] == "pending" or entry["published_commit"] is None:
        failures.append(
            f"declared successor {successor} cannot open while {entry['baseline_id']} qualification is pending or unpinned"
        )
    if declaration["predecessor_baseline_id"] != entry["baseline_id"]:
        failures.append(
            f"declared successor {successor} names predecessor {declaration['predecessor_baseline_id']} "
            f"but the current baseline is {entry['baseline_id']}"
        )
    if any(item["baseline_id"] == successor for item in register["baselines"]):
        failures.append(f"declared successor {successor} is already a published baseline")
    for delta in declaration["identity_deltas"]:
        path = delta["identity_path"]
        try:
            current = record_value(record, path)
        except SystemExit:
            failures.append(f"declared delta {path}: the predecessor record has no such identity")
            continue
        if _normalise(current) != _normalise(delta["from"]):
            failures.append(f"declared delta {path}: predecessor value is {current!r}, declaration says from={delta['from']!r}")
    return failures


def _normalise(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return value


def verify_declaration(
    root: Path,
    frozen: str,
    candidate: str,
    record: dict[str, Any],
    register: dict[str, Any],
    declaration: dict[str, Any],
    changed: list[str],
    sources: tuple[IdentitySource, ...],
) -> list[str]:
    failures = declaration_open_failures(root, register, record, declaration)
    declared = {item["path"]: item["blob"] for item in declaration["declared_changes"]}
    for path in changed:
        if path not in declared:
            failures.append(f"undeclared protected change: {path}")
    for path in sorted(declared):
        if path not in changed:
            failures.append(f"declared change absent from candidate: {path}")
    for path in sorted(declared):
        if path not in changed:
            continue
        actual = candidate_blob(root, candidate, path)
        if actual != declared[path]:
            failures.append(f"declared blob mismatch for {path}: declared {declared[path]}, candidate {actual}")
    known = {source.identity_path for source in sources}
    deltas = {delta["identity_path"]: delta for delta in declaration["identity_deltas"]}
    for path in deltas:
        if path not in known:
            failures.append(f"declared delta {path}: not an identity-table path")
    frozen_values = read_identities(root, frozen, sources)
    candidate_values = read_identities(root, candidate, sources)
    for path, delta in deltas.items():
        if path not in known:
            continue
        if _normalise(frozen_values[path]) != _normalise(delta["from"]):
            failures.append(f"declared delta {path}: frozen source value is {frozen_values[path]!r}, declaration says from={delta['from']!r}")
        if _normalise(candidate_values[path]) != _normalise(delta["to"]):
            failures.append(f"declared delta {path}: candidate value is {candidate_values[path]!r}, declaration says to={delta['to']!r}")
    for path in sorted(known):
        if path in deltas:
            continue
        if _normalise(frozen_values[path]) != _normalise(candidate_values[path]):
            failures.append(f"undeclared identity {path} changed: frozen={frozen_values[path]!r}, candidate={candidate_values[path]!r}")
    pyproject_declared = "pyproject.toml" in declared
    if pyproject_declared and declaration["pyproject_change"] is None:
        failures.append("pyproject.toml declared without pyproject_change")
    if not pyproject_declared and declaration["pyproject_change"] is not None:
        failures.append("pyproject_change given but pyproject.toml is not declared")
    return failures


def check(
    root: Path,
    register_path: Path | str,
    candidate: str,
    *,
    pinned_only: bool = False,
    identity_sources: tuple[IdentitySource, ...] = IDENTITY_SOURCES,
) -> Outcome:
    register = load_register(root, register_path)
    entry = current_entry(register)
    boundary = load_boundary(root, entry["source_boundary"])
    frozen = str(boundary["frozen_revision"])
    baseline_id = str(entry["baseline_id"])
    require_commit(root, frozen, "frozen runtime")
    require_commit(root, candidate, "candidate")

    changed = changed_paths(root, boundary, candidate)
    exclusions = ", ".join(str(item["path"]) for item in boundary["excluded_non_runtime_paths"]) or "none"
    if not changed:
        return Outcome(
            STATE_PASS,
            baseline_id,
            frozen,
            f"Runtime Baseline equivalence: {STATE_PASS}; baseline={baseline_id}; frozen={frozen}; "
            f"candidate={candidate}; explicit non-runtime exclusions={exclusions}",
        )

    declared_successor = register.get("declared_successor")
    if declared_successor is None:
        return Outcome(
            STATE_FAIL,
            baseline_id,
            frozen,
            f"candidate {candidate} changes the protected Runtime Baseline source surface relative to {frozen} "
            f"and the register declares no successor: {', '.join(changed)}",
        )

    declaration = load_declaration(root, declared_successor["declaration"])
    if declaration["baseline_id"] != declared_successor["baseline_id"]:
        return Outcome(
            STATE_FAIL,
            baseline_id,
            frozen,
            f"register declares successor {declared_successor['baseline_id']} but {declared_successor['declaration']} "
            f"declares {declaration['baseline_id']}",
        )
    record = _read_json(root, entry["record"], "runtime baseline record")
    failures = verify_declaration(root, frozen, candidate, record, register, declaration, changed, identity_sources)
    if failures:
        return Outcome(STATE_FAIL, baseline_id, frozen, "\n".join(failures))

    successor = declaration["baseline_id"]
    if pinned_only:
        return Outcome(
            STATE_FAIL,
            baseline_id,
            frozen,
            f"candidate {candidate} is in a declared transition to {successor}; this check requires a pinned baseline",
        )
    deltas = ", ".join(
        f"{delta['identity_path']} {delta['from']}->{delta['to']}" for delta in declaration["identity_deltas"]
    ) or "none"
    return Outcome(
        STATE_TRANSITION,
        baseline_id,
        frozen,
        f"Runtime Baseline equivalence: {STATE_TRANSITION}; baseline={baseline_id}; "
        f"declared_successor={successor} (issue #{declaration['issue']}); "
        f"protected surface = frozen {frozen} + {len(declaration['declared_changes'])} declared blobs; "
        f"deltas={deltas}; candidate={candidate}",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--candidate",
        default="HEAD",
        help="candidate commit/ref to compare with the current baseline (default: HEAD)",
    )
    parser.add_argument(
        "--register",
        type=Path,
        default=DEFAULT_REGISTER,
        help="runtime baseline register (default: reports/runtime/baseline-register.json)",
    )
    parser.add_argument(
        "--pinned-only",
        action="store_true",
        help="exit 1 on a declared transition; for callers whose evidence claims an exact revision",
    )
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    register = args.register if not args.register.is_absolute() else args.register.relative_to(root)
    outcome = check(root, register, args.candidate, pinned_only=args.pinned_only)
    if outcome.state == STATE_FAIL:
        raise SystemExit(outcome.message)
    print(outcome.message)
    return EXIT_CODES[outcome.state]


if __name__ == "__main__":
    raise SystemExit(main())
