#!/usr/bin/env python3
"""Run the repository-owned temporal/currentness qualification gauntlet (#580).

Evidence class: repository-owned conformance / falsification evidence. Not independent
external validation; a pass does not accept ADR-039.

Single configuration::

    PYTHONPATH=reference python reference/run_temporal_currentness_gauntlet.py --output report.json

Frozen baseline matrix (default + ablations + negative-control mutants + cross-process)::

    PYTHONPATH=reference python reference/run_temporal_currentness_gauntlet.py --matrix OUTDIR

Every configuration runs in its own process, because ranking variants and mutants are
installed process-wide. ``default`` leaves the shipped runtime untouched.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent
ROOT = REFERENCE.parent
sys.path.insert(0, str(REFERENCE))

from agentmem_ref.evaluation import temporal_currentness as tc  # noqa: E402
from benchmark_ranking_variants import VARIANTS, apply_ranking_variant  # noqa: E402

DEFAULT_FIXTURE = REFERENCE / "fixtures" / "benchmarks" / "temporal-currentness" / "temporal-currentness-gauntlet-v1.json"
TRANSFORMS = ("none", "inferred_only", "transaction_only")
# The reviewed pre-#550 runtime boundary this baseline is frozen against.
BASELINE_BOUNDARY = "0bace49c42228bb93e2c7bbcef3c0110bb880cbb"
EVALUATION_ONLY_PATHS = {
    "reference/agentmem_ref/evaluation/temporal_currentness.py",
}

# name -> (ranking variant, transform, mutant, diagnostics, PYTHONHASHSEED, purpose)
MATRIX = {
    "baseline": ("default", "none", None, True, "0", "shipped runtime, policy as on main"),
    "baseline-seed1": ("default", "none", None, False, "1", "cross-process reproduction of the baseline"),
    "universal_newer_first": ("universal_newer_first", "none", None, False, "0", "ablation: policy 2.x newer-first among ties, every intent"),
    "no_temporal_preference": ("no_temporal_preference", "none", None, False, "0", "ablation: no temporal stage"),
    "inferred_only": ("default", "inferred_only", None, False, "0", "ablation: explicit caller intent removed, text inference only"),
    "transaction_only": ("default", "transaction_only", None, False, "0", "ablation: declared valid/observation clocks removed"),
    "mutant-invent_currency": ("default", "none", "invent_currency", False, "0", "negative control: unknown basis reported applicable"),
    "mutant-ignore_validity": ("default", "none", "ignore_validity", False, "0", "negative control: declared validity ignored"),
}


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def provenance(fixture: Path) -> dict:
    from agentmem_ref.runtime import runtime_composition, temporal_intent

    return {
        "agent_memory_revision": _git("rev-parse", "HEAD"),
        "agent_memory_worktree_dirty": bool(_git("status", "--porcelain", "--", "reference/agentmem_ref")),
        "python": platform.python_version(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "ranking_policy": runtime_composition.MULTI_ROUTE_RANKING_POLICY.identity(),
        "temporal_interpreter": {"ref": temporal_intent.INTERPRETER_REF, "version": temporal_intent.INTERPRETER_VERSION},
        "fixture_path": str(fixture.relative_to(ROOT)) if fixture.is_relative_to(ROOT) else fixture.name,
        "fixture_sha256": tc.suite_digest(fixture),
        "evaluator_version": tc.EVALUATOR_VERSION,
        "baseline_boundary": BASELINE_BOUNDARY,
        # Runtime files that differ from the boundary (evaluation-only files excluded).
        # Empty means the measured runtime is exactly the pre-#550 runtime.
        "runtime_changes_since_boundary": sorted(
            path for path in _git("diff", "--name-only", BASELINE_BOUNDARY, "--", "reference/agentmem_ref").splitlines()
            if path and path not in EVALUATION_ONLY_PATHS
        ),
    }


def run_one(fixture: Path, *, variant: str, transform: str, mutant: str | None, diagnostics: bool) -> dict:
    applied = apply_ranking_variant(variant)
    if mutant:
        tc.install_mutant(mutant)
    suite = tc.load_suite(fixture)
    started = time.perf_counter()
    result = tc.run_suite(suite, transform=None if transform == "none" else transform, diagnostics=diagnostics)
    return {
        "report_schema_version": tc.REPORT_SCHEMA_VERSION,
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "evidence_class": suite["evidence_class"],
        "external_validation": False,
        "claim_boundary": suite["claim_boundary"],
        "configuration": {"ranking_variant": variant, "ranking_overrides": applied, "transform": transform,
                          "mutant": mutant, "diagnostics": diagnostics},
        "provenance": provenance(fixture),
        "counts": {"cases": len(suite["cases"]), "probes": len(result["rows"]),
                   "assertions": sum(len(r["assertions"]) for r in result["rows"])},
        "wall_seconds": round(time.perf_counter() - started, 3),
        "metrics": result["metrics"],
        "order_digests": tc.order_digests(result["rows"]),
        "diagnostics": result["diagnostics"],
        "fixture_negative_controls": result["fixture_negative_controls"],
        "incidental_target_passes": result["incidental_target_passes"],
        "rows": result["rows"],
    }


def _write(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_matrix(fixture: Path, out_dir: Path) -> dict:
    reports = {}
    for name, (variant, transform, mutant, diagnostics, seed, _) in MATRIX.items():
        target = out_dir / f"{name}.json"
        command = [sys.executable, str(Path(__file__).resolve()), "--fixtures", str(fixture), "--output", str(target),
                   "--ranking-variant", variant, "--transform", transform]
        if mutant:
            command += ["--mutant", mutant]
        if not diagnostics:
            command.append("--no-diagnostics")
        subprocess.run(command, check=True, env={**os.environ, "PYTHONHASHSEED": seed})
        reports[name] = json.loads(target.read_text(encoding="utf-8"))
    summary = summarize(reports)
    _write(out_dir / "summary.json", summary)
    return summary


def _metric_values(report: dict) -> dict:
    out = {}
    for name, entry in report["metrics"].items():
        if entry.get("kind") == "not_measurable":
            out[name] = entry["status"]
        elif name == "restart_reproduction_rate":
            out[name] = entry["value"]
        else:
            out[name] = {level: entry[level]["value"] for level in tc.LEVELS}
    return out


def _unit_table(report: dict) -> dict:
    return {"/".join(key): status for key, status in tc.units(report["rows"]).items()}


def _classes(report: dict) -> dict:
    out: dict = {}
    for finding in report["diagnostics"]:
        entry = out.setdefault(finding["failure_class"], {"units": 0, "probes": set(), "levels": set(), "statuses": set()})
        entry["units"] += 1
        entry["probes"].add(f"{finding['case_id']}/{finding['probe_id']}")
        entry["levels"].add(finding["level"])
        entry["statuses"].add(finding["status"])
    return {cls: {k: sorted(v) if isinstance(v, set) else v for k, v in entry.items()} for cls, entry in sorted(out.items())}


def summarize(reports: dict) -> dict:
    base = reports["baseline"]
    base_units = _unit_table(base)
    seed1 = reports["baseline-seed1"]["order_digests"]
    cross = [key for key, digest in base["order_digests"].items() if seed1.get(key) != digest]
    comparisons = {}
    for name, report in reports.items():
        if name in {"baseline", "baseline-seed1"}:
            continue
        other = _unit_table(report)
        changed = {key: {"baseline": base_units[key], name: other.get(key)} for key in sorted(base_units) if other.get(key) != base_units[key]}
        comparisons[name] = {
            "purpose": MATRIX[name][5],
            "metrics": _metric_values(report),
            "units_changed_vs_baseline": len(changed),
            "units_regressed": sorted(k for k, v in changed.items() if v["baseline"] == "pass"),
            "units_improved": sorted(k for k, v in changed.items() if v[name] == "pass"),
            "changed": changed,
        }
    return {
        "suite_id": base["suite_id"], "suite_version": base["suite_version"],
        "evidence_class": base["evidence_class"], "external_validation": False,
        "claim_boundary": base["claim_boundary"],
        "baseline_provenance": base["provenance"],
        "baseline_metrics": _metric_values(base),
        "baseline_incidental_target_passes": base["incidental_target_passes"],
        "baseline_failure_classes": _classes(base),
        "cross_process_order_reproduction": {
            "seeds": ["0", "1"], "probes": len(base["order_digests"]),
            "reproduced": len(base["order_digests"]) - len(cross),
            "rate": round((len(base["order_digests"]) - len(cross)) / len(base["order_digests"]), 4),
            "not_reproduced": cross,
        },
        "ablations_and_negative_controls": comparisons,
        "configurations": {name: MATRIX[name][5] for name in reports},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ranking-variant", choices=tuple(VARIANTS), default="default")
    parser.add_argument("--transform", choices=TRANSFORMS, default="none")
    parser.add_argument("--mutant", choices=tc.MUTANTS)
    parser.add_argument("--no-diagnostics", action="store_true")
    parser.add_argument("--matrix", type=Path, help="run the frozen baseline matrix into this directory")
    args = parser.parse_args()
    fixture = args.fixtures.resolve()
    if args.matrix:
        summary = run_matrix(fixture, args.matrix)
        print(json.dumps({"baseline_metrics": summary["baseline_metrics"],
                          "cross_process": summary["cross_process_order_reproduction"]}, indent=2))
        return 0
    report = run_one(fixture, variant=args.ranking_variant, transform=args.transform, mutant=args.mutant,
                     diagnostics=not args.no_diagnostics)
    if args.output:
        _write(args.output, report)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
