#!/usr/bin/env python3
"""#662: offline FinOps preflight for a quiet development checkout.

This command deliberately cannot dispatch GitHub Actions, read billing or grant
merge/release authority. The output is a locally generated diagnostic receipt
with exact source SHA and exit codes, not protected evidence or a CI success.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

def local_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def test_commands(mode: str) -> list[tuple[str, list[str]]]:
    if mode not in ("quick", "full"):
        raise ValueError("mode must be quick or full")
    py = sys.executable
    steps = [
        ("workflow_policy_and_retention",
         [py, "scripts/sync_workflow_inventory.py", "--check"]),
    ]
    if mode == "quick":
        steps.append((
            "focused_workflow_policy_tests",
            [py, "-m", "unittest", "discover", "-s", "reference/tests",
             "-t", "reference", "-p", "test_github_actions_workflow_policy.py", "-v"],
        ))
    else:
        steps.extend([
            ("complete_reference_regression",
             [py, "-m", "unittest", "discover", "-s", "reference/tests",
              "-t", "reference", "-p", "test_*.py"]),
            ("repository_compatibility_tests",
             [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]),
        ])
    return steps


def run_preflight(mode: str, allow_dirty: bool = False) -> dict[str, Any]:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        raise ValueError(
            "offline preflight must not run on GitHub-hosted Actions"
        )
    commit_sha = local_git("rev-parse", "HEAD")
    branch = local_git("branch", "--show-current") or "(detached)"
    status = local_git("status", "--porcelain")
    if len(commit_sha) != 40 or any(c not in "0123456789abcdef" for c in commit_sha):
        raise ValueError("cannot establish exact 40-character source SHA")
    if status and not allow_dirty:
        raise ValueError("worktree is dirty; commit locally or use --allow-dirty")
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "profile": "local-finops-validation",
        "mode": mode,
        "repo_head_sha": commit_sha,
        "branch": branch,
        "worktree_clean": not bool(status),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "github_actions_dispatches": 0,
        "billed_minutes_known": False,
        "external_qualification": False,
        "branch_protection_verified": False,
        "authority_effect": "none",
        "status": "not_completed",
        "steps": [],
    }
    for name, command in test_commands(mode):
        started = time.monotonic()
        # Diagnostic output is printed locally only on failure. Never store
        # stdout/stderr in a receipt that could accidentally be committed.
        # Stop at the first failed step.
        try:
            proc = subprocess.run(
                command, cwd=ROOT, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=1800,
            )
            code = proc.returncode
            if code != 0:
                print(f"{name}: local command failed with exit {code}", file=sys.stderr)
                print(proc.stderr[-2500:], file=sys.stderr)
                print(proc.stdout[-2500:], file=sys.stderr)
        except subprocess.TimeoutExpired:
            code = 124
            print(f"{name}: local command timed out", file=sys.stderr)
        report["steps"].append({
            "name": name,
            "exit_code": code,
            "duration_seconds": round(time.monotonic() - started, 3),
        })
        if code != 0:
            report["status"] = "failed"
            break
    else:
        report["status"] = "passed_local_only"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("quick", "full"), default="quick")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--output", type=Path,
                        default=Path(tempfile.gettempdir()) / "agent-memory-finops-preflight.json")
    args = parser.parse_args()
    try:
        report = run_preflight(args.mode, args.allow_dirty)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("Preflight refused: " + str(error), file=sys.stderr)
        return 2
    # Default output is outside the checkout, reducing risk of accidentally
    # committing a generated receipt and treating it as authoritative.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f'{report["status"]}; revision={report["repo_head_sha"]}; '
          f'mode={args.mode}; steps={len(report["steps"])}; '
          f'local receipt={args.output}')
    return 0 if report["status"] == "passed_local_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
