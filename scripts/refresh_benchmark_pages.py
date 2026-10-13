#!/usr/bin/env python3
"""Refresh benchmark reports as a governed, local-only evidence projection.

This command never executes a benchmark, calls a vendor, accepts evidence,
modifies source runs, or grants agent authority. No GitHub Actions required.

  python scripts/refresh_benchmark_pages.py --write
  python scripts/refresh_benchmark_pages.py --check

--write is used after an evidence-recording commit; --check fails closed on
stale/invalid derived data. Never run --write as a silent remedy for a
failed evidence-qualification gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STATUS = ROOT / "reports/benchmarks/ui/refresh-status.json"
GENERATED = (
    "reports/benchmarks/scorecards/scorecards.json",
    "reports/benchmarks/scorecards/scorecards.md",
    "reports/benchmarks/ui/catalog.json",
    "reports/benchmarks/ui/frontier-leaderboards.json",
    "reports/benchmarks/ui/historical-amb-v6.json",
)
SOURCE_PATHS = (
    "reports/benchmarks/dashboard/current.json",
    "reports/benchmarks/replays/594-post-550-semantic-qualification/phase-b-score-v1.json",
)
COMMANDS = (
    ("scripts/build_benchmark_scorecards.py", (), ("--check",)),
    ("scripts/build_benchmark_ui_catalog.py", (), ("--check",)),
    ("scripts/build_benchmark_frontier_leaderboards.py", ("--write",), ("--check",)),
    ("scripts/build_789_historical_ui.py", ("--write",), ("--check",)),
)


class RefreshError(RuntimeError):
    pass


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_hash(path: Path) -> str:
    return _digest(path.read_bytes())


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def source_inventory(root: Path) -> dict[str, str]:
    """Hash raw/declared evidence without making its presence an acceptance."""
    sources = set()
    for rel in SOURCE_PATHS:
        sources.add(root / rel)
    for sub in ("amb", "longmemeval", "replays", "dashboard"):
        folder = root / "reports/benchmarks" / sub
        if folder.exists():
            sources.update(folder.rglob("*.json"))
    for folder in (root / "reference/agentmem_ref/evaluation/lanes",):
        if folder.exists():
            sources.update(folder.rglob("*.json"))
    objective = root / "data/benchmark-frontier-objectives.json"
    if objective.exists():
        sources.add(objective)
    if not (root / "reports/benchmarks/normalized").is_dir():
        raise RefreshError("missing normalized evidence directory")
    # SOURCE_PATHS are mandatory, while dataset-specific folders may be absent.
    for rel in SOURCE_PATHS:
        if not (root / rel).is_file():
            raise RefreshError("missing declared source: " + rel)
    return {_relative(path, root): _file_hash(path) for path in sorted(sources)
            if path.is_file()}


def registered_evidence() -> set[str]:
    from scripts.build_benchmark_scorecards import SOURCES
    return {str(path).replace("\\", "/") for _, path in SOURCES}


def compute_status(root: Path = ROOT, *, registered: set[str] | None = None) -> dict:
    """Snapshot dependency and output fingerprints; never make ranking decisions."""
    inventory = source_inventory(root)
    registered = registered_evidence() if registered is None else registered
    candidates = sorted(path for path in inventory
                        if path.endswith("/evidence.json") and
                        path.startswith(("reports/benchmarks/amb/", "reports/benchmarks/longmemeval/")) and
                        path not in registered)
    for rel in GENERATED:
        if not (root / rel).is_file():
            raise RefreshError("derived output missing: " + rel)
    catalog = _json(root / "reports/benchmarks/ui/catalog.json")
    frontier = _json(root / "reports/benchmarks/ui/frontier-leaderboards.json")
    historical = _json(root / "reports/benchmarks/ui/historical-amb-v6.json")
    if catalog.get("authority_effect") != "none" or frontier.get("authority_effect") != "none":
        raise RefreshError("derived projection unexpectedly claims authority")
    if frontier.get("aggregate_score") is not None:
        raise RefreshError("aggregated competitive scoring forbidden")
    if historical.get("evidence_status") != "historical_source_bound_not_promoted" or historical.get("eligible_for_frontier_rankings") is not False:
        raise RefreshError("historical evidence was promoted without acceptance")
    if frontier.get("snapshot_id") != catalog.get("snapshot", {}).get("id"):
        raise RefreshError("frontier does not reference the catalog snapshot")
    peer_ids = frontier.get("external_competitors", {}).get("same_harness_measured", [])
    if not isinstance(peer_ids, list):
        raise RefreshError("invalid external system population")
    return {
        "schema_version": "benchmark-refresh-status/1",
        "mode": "local_evidence_projection_no_ci",
        "authority_effect": "none",
        "accepted_evidence_only_in_rankings": True,
        "catalog_snapshot_id": frontier["snapshot_id"],
        "source_digest": _digest(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")),
        "source_count": len(inventory),
        "source_sha256": inventory,
        "derived_sha256": {rel: _file_hash(root / rel) for rel in GENERATED},
        "registered_source_count": len(registered),
        "unregistered_source_evidence": candidates,
        "unregistered_source_count": len(candidates),
        "measured_external_system_ids": sorted(set(peer_ids)),
        "publication_state": "repository_projection_only",
        "note": (
            "Computed from the current checked-out repository evidence; this record is "
            "not a live remote-state check or evidence acceptance. Unregistered raw "
            "candidates remain unranked until source qualification/registration."
        ),
    }


def _run(root: Path, script: str, args: tuple[str, ...]) -> None:
    argv = [sys.executable, str(root / script), *args]
    subprocess.run(argv, cwd=root, check=True)


def refresh(root: Path = ROOT, *, check: bool = False, registered: set[str] | None = None) -> dict:
    """One ordered transaction. No partial generated file is publication evidence."""
    if check:
        for name, _, check_args in COMMANDS:
            _run(root, name, check_args)
        expected = compute_status(root, registered=registered)
        status = root / "reports/benchmarks/ui/refresh-status.json"
        if not status.is_file() or _json(status) != expected:
            raise RefreshError("benchmark refresh manifest stale; record a governed refresh")
        return expected
    # build_benchmark_scorecards.py and build_benchmark_ui_catalog.py write by default
    for name, write_args, _ in COMMANDS:
        _run(root, name, write_args)
    expected = compute_status(root, registered=registered)
    status = root / "reports/benchmarks/ui/refresh-status.json"
    status.parent.mkdir(parents=True, exist_ok=True)
    status.write_text(json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    # Fail if any step's committed projection disagrees; auto-hook must not commit.
    for name, _, check_args in COMMANDS:
        _run(root, name, check_args)
    if _json(status) != compute_status(root, registered=registered):
        raise RefreshError("non-deterministic refresh; refusing publication")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        out = refresh(check=args.check)
    except (RefreshError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("benchmark refresh BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"status": "current" if args.check else "refreshed",
                      "snapshot": out["catalog_snapshot_id"],
                      "source_count": out["source_count"],
                      "unregistered_source_count": out["unregistered_source_count"],
                      "external_systems": out["measured_external_system_ids"],
                      "git_actions_used": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
