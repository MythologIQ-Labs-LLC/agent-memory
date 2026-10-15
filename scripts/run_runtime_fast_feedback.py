#!/usr/bin/env python3
"""Bounded local feedback on existing Agent Memory conformance tests.

This is an engineer diagnostic, NOT hidden-cohort evaluation, full-suite
acceptance, or Runtime Baseline qualification. It cannot trigger CI itself.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Each named group is small, existing, source-controlled unit/conformance tests.
# It does not contain benchmark gold or hidden holdout cases.
SUITES = {
    "retrieval": (
        "test_query_driven_recall.py",
        "test_multi_route_recall.py",
    ),
    "temporal": (
        "test_cross_fact_currentness.py",
        "test_api_history_posture.py",
    ),
    "governance": (
        "test_scope_governance.py",
        "test_deletion_authority.py",
    ),
}


def _git(root: Path, *parts: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *parts],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def selected_suites(focus: str) -> list[str]:
    if focus == "all":
        return [suite for group in SUITES.values() for suite in group]
    return list(SUITES[focus])


def _record_suite(root: Path, name: str, timeout: float) -> dict[str, Any]:
    argv = [
        sys.executable, "-m", "unittest", "discover",
        "-s", "reference/tests", "-t", "reference", "-p", name, "-v",
    ]
    started = time.monotonic()
    try:
        # Kill the test's process group on POSIX, not merely unittest's parent.
        # A timed-out test may have launched children that would otherwise keep
        # monopolizing the same CPU used by live competitor evaluations.
        with subprocess.Popen(
            argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=os.name == "posix",
        ) as proc:
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                stdout, stderr = proc.communicate()
                return {
                    "suite": name,
                    "status": "timed_out",
                    "exit_code": None,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "command": argv,
                    "stdout_tail": stdout[-3000:],
                    "stderr_tail": (stderr[-5000:] + "\ntime budget exhausted").strip(),
                }
        return {
            "suite": name,
            "status": "passed" if proc.returncode == 0 else "failed",
            "exit_code": proc.returncode,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "command": argv,
            "stdout_tail": stdout[-3000:],
            "stderr_tail": stderr[-6000:],
        }
    except OSError as exc:
        return {
            "suite": name,
            "status": "runner_error",
            "exit_code": None,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "command": argv,
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }


def run(
    root: Path,
    focus: str,
    max_total_seconds: float,
    max_suite_seconds: float,
) -> dict[str, Any]:
    """Run every selected suite within the total budget; fail closed on skips."""
    root = root.resolve()
    if max_total_seconds <= 0 or max_suite_seconds <= 0:
        raise ValueError("budgets must be positive")
    if not (root / "reference" / "tests").is_dir():
        raise ValueError("expected reference/tests directory absent")
    sha = _git(root, "rev-parse", "HEAD")
    dirty = _git(root, "status", "--porcelain")
    suites = selected_suites(focus)
    missing = [s for s in suites if not (root / "reference" / "tests" / s).is_file()]
    if missing:
        raise ValueError("selected test modules absent: " + ", ".join(missing))
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    for name in suites:
        remaining = max_total_seconds - (time.monotonic() - started)
        if remaining <= 0:
            results.append({"suite": name, "status": "budget_exhausted", "exit_code": None})
            continue
        results.append(_record_suite(root, name, min(max_suite_seconds, remaining)))
    passed = sum(row["status"] == "passed" for row in results)
    clean = dirty == "" and sha is not None
    return {
        "schema": "agent-memory-runtime-fast-feedback/1",
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "revision": sha,
        "git_clean": clean,
        "git_provenance_available": sha is not None and dirty is not None,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "focus": focus,
        "suite_budget_seconds": max_suite_seconds,
        "total_budget_seconds": max_total_seconds,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "suites": results,
        "passed_suites": passed,
        "selected_suites": len(suites),
        "status": "passed" if passed == len(suites) else "failed_or_incomplete",
        "qualification_effect": "none",
        "hidden_holdout_consumed": False,
        "comparison_eligible": False,
        "runtime_baseline_activated": False,
        "limitations": [
            "Developer feedback only; not full regression or independent review",
            "Test source and runtime are from the current worktree, not independent",
            "Does not execute AMB, LongMemEval, competitor inference, or unseen cohorts",
            "Does not enforce a network sandbox on spawned tests",
            "Passing tests do not authorize release, policy promotion, or baseline succession",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--focus", choices=[*SUITES, "all"], default="retrieval")
    p.add_argument("--max-total-seconds", type=float, default=180.0)
    p.add_argument("--max-suite-seconds", type=float, default=60.0)
    p.add_argument("--output", type=Path, default=None, help="optional local JSON receipt path")
    args = p.parse_args(argv)
    try:
        result = run(args.root, args.focus, args.max_total_seconds, args.max_suite_seconds)
    except ValueError as exc:
        p.error(str(exc))
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Local execution receipt only: do not write into the benchmark scorecard.
        args.output.write_text(serialized, encoding="utf-8")
    else:
        sys.stdout.write(serialized)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
