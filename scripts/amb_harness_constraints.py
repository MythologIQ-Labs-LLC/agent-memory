#!/usr/bin/env python3
"""Derive pip constraints for the frozen AMB harness from its own ``uv.lock`` (#640).

The frozen AMB revision declares a broad, mostly unpinned dependency set in
``pyproject.toml`` (``hindsight-all>=0.4``, ``cognee>=0.5.4``, ``mem0ai>=1.0.5`` ...)
but ships the exact resolution it was developed against in ``uv.lock``. Installing the
harness with ``pip install -e <checkout>`` alone asks pip to re-resolve that set from
scratch, which exhausts pip's backtracking budget (``resolution-too-deep``) before a
single benchmark query runs. Installing under the harness's own lock keeps the harness
environment the harness authors froze, and makes the install deterministic.

Only two kinds of pin are ever lifted from the lock, and both are declared here rather
than discovered at install time:

* packages this repository pins itself in ``pyproject.toml`` (the lock's versions were
  resolved without Agent Memory present and are not harness facts);
* a lane row's explicit comparator pin (for example ``mem0ai==2.2.1`` for the #640 Mem0
  OSS row) together with the locked pins that pin contradicts, each named with its
  reason. The resolver then fails loudly if anything else would have to move.

Nothing here executes a benchmark or produces a score. The emitted provenance sidecar is
copied into the run's execution identity so a result can be tied to the exact lock blob,
the pins lifted, and the ``uv`` release that exported it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*==")

# Lane-row pins and the locked pins each one contradicts. The lock resolved mem0ai 1.0.5;
# the #640 comparator row freezes mem0ai 2.2.1, which requires posthog>=7.14.0 while the
# lock carries posthog 7.9.10. Nothing else in the lock conflicts with that pin (verified
# by resolving the trimmed set with both uv and pip on CPython 3.12).
ROW_PINS: dict[str, dict[str, object]] = {
    "mem0-explicit": {
        "pins": ["mem0ai==2.2.1"],
        "lift": {
            "mem0ai": "replaced by the lane row pin mem0ai==2.2.1 (lock: 1.0.5)",
            "posthog": "mem0ai 2.2.1 requires posthog>=7.14.0; the lock carries 7.9.10 (telemetry client only; MEM0_TELEMETRY=false)",
        },
    },
}


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(line: str) -> str | None:
    match = REQUIREMENT_NAME.match(line)
    return canonical(match.group(1)) if match else None


def repository_pinned_packages(pyproject: Path = REPO_ROOT / "pyproject.toml") -> list[str]:
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    names = []
    for requirement in project.get("dependencies", []):
        match = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
        if match:
            names.append(canonical(match.group(1)))
    return names


def export_lock(amb_root: Path, uv: str = "uv") -> str:
    """Export the harness lock as a requirements listing with pins only (no project, no hashes)."""
    command = [
        uv,
        "export",
        "--frozen",
        "--format",
        "requirements-txt",
        "--no-hashes",
        "--no-emit-project",
        "--no-header",
        "--quiet",
    ]
    completed = subprocess.run(command, cwd=amb_root, capture_output=True, text=True, check=True)
    return completed.stdout


def trim_constraints(exported: str, *, drop: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    """Return the constraint lines with ``drop`` packages removed and the locked pins actually dropped.

    A package named in ``drop`` that the lock never carried (for example ``rfc8785``) is
    simply absent from the second value; the provenance records it as ``locked: null``.
    """
    """Return the constraint lines with ``drop`` packages removed and the pins actually dropped."""
    kept: list[str] = []
    dropped: dict[str, str] = {}
    wanted = {canonical(name) for name in drop}
    for raw in exported.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name = requirement_name(line)
        if name is None:
            raise ValueError(f"unexpected line in uv export output (constraints must be exact pins): {line!r}")
        if name in wanted:
            dropped[name] = line
            continue
        kept.append(line)
    return kept, dropped


def build(amb_root: Path, memory: str | None, *, uv: str = "uv") -> tuple[list[str], dict[str, object]]:
    lock_path = amb_root / "uv.lock"
    if not lock_path.is_file():
        raise FileNotFoundError(f"frozen AMB checkout has no uv.lock: {lock_path}")
    row = ROW_PINS.get(memory or "", {"pins": [], "lift": {}})
    repo_pins = repository_pinned_packages()
    drop: dict[str, str] = {name: "pinned by this repository's pyproject.toml" for name in repo_pins}
    drop.update(row["lift"])  # type: ignore[arg-type]
    exported = export_lock(amb_root, uv=uv)
    kept, dropped = trim_constraints(exported, drop=drop)
    lines = kept + [f"{pin}  # lane row pin ({memory})" for pin in row["pins"]]  # type: ignore[union-attr]
    uv_version = subprocess.run([uv, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    provenance = {
        "source": "uv.lock of the frozen AMB checkout, exported with uv and installed as pip constraints",
        "uv_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "uv_lock_git_blob": subprocess.run(["git", "hash-object", "uv.lock"], cwd=amb_root, capture_output=True, text=True, check=True).stdout.strip(),
        "uv_version": uv_version,
        "memory": memory,
        "row_pins": list(row["pins"]),  # type: ignore[arg-type]
        "lifted_pins": {name: {"locked": dropped.get(name), "reason": reason} for name, reason in drop.items()},
        "constraint_count": len(kept),
        "authority_effect": "none",
    }
    return lines, provenance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--amb-root", required=True, type=Path, help="frozen AMB checkout")
    parser.add_argument("--memory", default=None, help="AMB provider key; selects the lane row pins to apply")
    parser.add_argument("--output", required=True, type=Path, help="constraints file to write")
    parser.add_argument("--provenance", type=Path, default=None, help="JSON sidecar describing the derivation")
    parser.add_argument("--uv", default=shutil.which("uv") or "uv")
    args = parser.parse_args(argv)
    lines, provenance = build(args.amb_root.resolve(), args.memory, uv=args.uv)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    provenance["constraints_sha256"] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    if args.provenance:
        args.provenance.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(provenance, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
