#!/usr/bin/env python3
"""Derive the GitHub Actions estate from the workflow YAML (#662 Phases 2-4).

One reader serves three consumers: the policy test (``derive_policy`` must equal
``data/github-actions-workflow-policy.json``), the inventory sync (``sync_inventory``
rewrites the mechanical fields of ``data/github-actions-workflow-inventory.json`` and its
summary counts; the judgment fields are never touched) and the ``--report`` table that #662
asks for. Everything is a pure function of the YAML; nothing reads run history.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = Path(".github/workflows")
POLICY = Path("data/github-actions-workflow-policy.json")
INVENTORY = Path("data/github-actions-workflow-inventory.json")
CONCURRENCY_GROUP = "${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}"
CANCEL_SUPERSEDED = "${{ github.event_name == 'pull_request' }}"
FULL_SUITE_START = "reference/tests"
DEFAULT_PATTERN = "test_*.py"


def load_workflow(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if True in data:  # YAML 1.1 reads the bare key ``on`` as a boolean
        data["on"] = data.pop(True)
    return data


def trigger_shape(on: Any) -> tuple[str | None, str | None, list[str]]:
    """Return (pull_request, push, other triggers) in the policy vocabulary."""
    if isinstance(on, str):
        on = {on: None}
    if isinstance(on, list):
        on = {name: None for name in on}
    pull = on.get("pull_request", "absent")
    push = on.get("push", "absent")
    pull_shape = None if pull == "absent" else ("paths" if isinstance(pull, dict) and pull.get("paths") else "unfiltered")
    push_shape = None
    if push != "absent":
        branches = push.get("branches") if isinstance(push, dict) else None
        scoped = "main" if branches == ["main"] else "unrestricted"
        push_shape = f"{scoped}_paths" if isinstance(push, dict) and push.get("paths") else scoped
    others = sorted(name for name in on if name not in ("pull_request", "push"))
    return pull_shape, push_shape, others


def concurrency_kind(workflow: dict[str, Any]) -> str:
    block = workflow.get("concurrency")
    if not isinstance(block, dict) or not block.get("group"):
        return "none"
    cancel = block.get("cancel-in-progress")
    if block["group"] == CONCURRENCY_GROUP and cancel == CANCEL_SUPERSEDED:
        return "cancel_superseded"
    if cancel is False:
        return "complete_every_run"
    return "other"


def discover_options(tokens: list[str]) -> dict[str, str | None]:
    options = {"-s": None, "-t": None, "-p": None}
    aliases = {"--start-directory": "-s", "--top-level-directory": "-t", "--pattern": "-p"}
    for index, token in enumerate(tokens[:-1]):
        key = aliases.get(token, token)
        if key in options:
            options[key] = tokens[index + 1]
    return options


def full_suite_lines(script: str) -> int:
    """Count ``unittest discover`` invocations that run the whole reference suite."""
    count = 0
    for line in script.splitlines():
        if "unittest" not in line or "discover" not in line:
            continue
        try:
            tokens = shlex.split(line.strip().lstrip("\\"))
        except ValueError:
            tokens = line.split()
        if "discover" not in tokens:
            continue
        options = discover_options(tokens[tokens.index("discover") + 1 :])
        if options["-s"] == FULL_SUITE_START and options["-p"] in (None, DEFAULT_PATTERN):
            count += 1
    return count


def job_shape(job: dict[str, Any]) -> dict[str, Any]:
    passes = sum(full_suite_lines(str(step.get("run", ""))) for step in job.get("steps", []))
    return {"timeout_minutes": job.get("timeout-minutes"), "full_suite_passes": passes}


def workflow_policy(workflow: dict[str, Any]) -> dict[str, Any]:
    pull, push, others = trigger_shape(workflow["on"])
    return {
        "pull_request": pull,
        "push": push,
        "other_triggers": others,
        "concurrency": concurrency_kind(workflow),
        "jobs": {job_id: job_shape(job) for job_id, job in workflow["jobs"].items()},
    }


def workflow_paths(root: Path) -> list[Path]:
    return sorted((root / WORKFLOWS).glob("*.yml"))


def derive_policy(root: Path) -> dict[str, Any]:
    workflows = {path.name: workflow_policy(load_workflow(path)) for path in workflow_paths(root)}
    return {"schema_version": 1, "governing_issue": "#662", "concurrency_group": CONCURRENCY_GROUP, "workflows": workflows}


def mechanical_fields(workflow: dict[str, Any]) -> dict[str, Any]:
    """The inventory record fields that follow from the YAML alone."""
    pull, push, others = trigger_shape(workflow["on"])
    block = workflow.get("concurrency") if isinstance(workflow.get("concurrency"), dict) else {}
    timeouts = sorted({job["timeout-minutes"] for job in workflow["jobs"].values() if "timeout-minutes" in job})
    has_paths = pull == "paths" or (push or "").endswith("_paths")
    scope = "paths" if has_paths else ("branches" if push and push.startswith("main") else "repository-wide-or-unscoped")
    return {
        "triggers": sorted(([] if pull is None else ["pull_request"]) + ([] if push is None else ["push"]) + others),
        "pathScope": scope,
        "timeoutState": {"explicit": bool(timeouts), "valuesMinutes": timeouts},
        "concurrencyState": {"configured": bool(block.get("group")), "cancelInProgress": block.get("cancel-in-progress") is True or block.get("cancel-in-progress") == CANCEL_SUPERSEDED},
    }


def artifact_retention_fields(workflow: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Exact upload-artifact step inventory, not an evidence deletion decision.

    Artifacts used as cited qualifications remain subject to independent
    retention policy. This only records explicit step settings and reports
    missing ones; it never assigns a default to protected evidence.
    """
    uploads = []
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if not str(step.get("uses", "")).startswith("actions/upload-artifact@"):
                continue
            options = step.get("with") or {}
            duration = options.get("retention-days")
            if duration is not None:
                if type(duration) is not int or duration < 1 or duration > 400:
                    raise ValueError("unsupported artifact retention-days")
            uploads.append(duration)
    return (
        {
            "producesArtifacts": bool(uploads),
            "retentionDays": sorted({days for days in uploads if days is not None}),
        },
        sum(days is None for days in uploads),
    )


def sync_inventory(inventory: dict[str, Any], root: Path) -> dict[str, Any]:
    synced = json.loads(json.dumps(inventory))
    by_path = {path.as_posix(): path for path in (p.relative_to(root) for p in workflow_paths(root))}
    counts: dict[str, int] = {}
    missing_timeout = 0
    missing_retention = 0
    supersedable_without = 0
    for record in synced["records"]:
        workflow = load_workflow(root / by_path[record["path"]])
        fields = mechanical_fields(workflow)
        record.update(fields)
        artifact_state, missing_step_retention = artifact_retention_fields(workflow)
        record["artifactState"] = artifact_state
        missing_retention += missing_step_retention
        for name in fields["triggers"]:
            counts[name] = counts.get(name, 0) + 1
        missing_timeout += not fields["timeoutState"]["explicit"]
        if {"pull_request", "push"} & set(fields["triggers"]) and not fields["concurrencyState"]["configured"]:
            supersedable_without += 1
    summary = synced["inventorySummary"]
    summary["triggerCounts"] = dict(sorted(counts.items()))
    summary["missingExplicitTimeoutCount"] = missing_timeout
    summary["artifactUploadWithoutExplicitRetentionCount"] = missing_retention
    summary["supersedablePrOrPushWithoutConcurrencyCount"] = supersedable_without
    return synced


def report_rows(root: Path, revision: str | None) -> dict[str, dict[str, Any]]:
    """One row per workflow at the working tree or at a git revision."""
    rows = {}
    for path in workflow_paths(root):
        if revision is None:
            workflow = load_workflow(path)
        else:
            shown = subprocess.run(["git", "show", f"{revision}:{path.relative_to(root).as_posix()}"], cwd=root, capture_output=True, text=True)
            if shown.returncode:
                continue
            workflow = yaml.safe_load(shown.stdout)
            if True in workflow:
                workflow["on"] = workflow.pop(True)
        policy = workflow_policy(workflow)
        timeouts = ",".join(str(job["timeout_minutes"]) for job in policy["jobs"].values())
        rows[path.name] = {"pull_request": policy["pull_request"], "push": policy["push"], "concurrency": policy["concurrency"], "timeouts": timeouts}
    return rows


def render_report(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> str:
    lines = ["| workflow | pull_request | push | concurrency | timeouts |", "| --- | --- | --- | --- | --- |"]
    for name in sorted(set(before) | set(after)):
        old, new = before.get(name, {}), after.get(name, {})
        cells = [f"{old.get(key)} → {new.get(key)}" if old.get(key) != new.get(key) else str(new.get(key)) for key in ("pull_request", "push", "concurrency", "timeouts")]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def dump(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def trigger_budget_envelope(policy: dict[str, Any]) -> dict[str, Any]:
    """Pure configuration fan-out, deliberately NOT billed-minute accounting.

    Unfiltered PR workflows start on any PR, path-filtered ones *might* start,
    main-push workflows start on a main push, and workflow_dispatch starts only
    when deliberately requested. Run counts cannot predict a bill: matrices,
    cache, runner tier, cancellation, rounding and real execution time matter.
    """
    workflows = policy["workflows"]
    mandatory = sorted(name for name, x in workflows.items()
                       if x["pull_request"] == "unfiltered")
    conditional = sorted(name for name, x in workflows.items()
                         if x["pull_request"] == "paths")
    main_push = sorted(name for name, x in workflows.items()
                       if x["push"] in ("main", "main_paths"))
    manual_only = sorted(name for name, x in workflows.items()
                         if x["pull_request"] is None and x["push"] is None
                         and "workflow_dispatch" in x["other_triggers"])
    return {
        "schema_version": "1.0.0",
        "provenance": "committed_workflow_configuration_only",
        "authoritative_billing_minutes": None,
        "calculated_dollar_savings": None,
        "unfiltered_pr_workflow_starts_per_head": len(mandatory),
        "potential_path_scoped_pr_workflows_per_head": len(conditional),
        "potential_all_pr_workflows_per_head": len(mandatory) + len(conditional),
        "main_push_workflows": len(main_push),
        "manual_only_workflows": len(manual_only),
        "unfiltered_pr_workflow_names": mandatory,
        "manual_only_workflow_names": manual_only,
        "discretionary_benchmarks_not_automatically_triggered": [
            name for name in manual_only if name in {
                "long-horizon-memory-benchmark.yml",
                "memory-metabolism-benchmark.yml",
                "operational-memory-benchmark.yml",
                "precedent-candidate-retrieval.yml",
                "retrieval-quality-benchmark.yml",
                "semantic-representation.yml",
            }
        ],
        "qualification_caveat": (
            "Check required status contexts before changing protected checks; "
            "external billing usage, actual runtime and cache consumption unknown"
        ),
        "branch_staging": (
            "Unopened non-main feature branch pushes do not start these "
            "pull_request or main-scoped push workflows"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--check", action="store_true", help="exit 1 when the inventory's mechanical fields differ from the YAML")
    parser.add_argument("--write", action="store_true", help="rewrite the inventory's mechanical fields and summary counts")
    parser.add_argument("--emit-policy", action="store_true", help="print the policy derived from the YAML")
    parser.add_argument("--finops-report", action="store_true", help="print trigger-only fan-out, not GitHub billed minutes")
    parser.add_argument("--report", action="store_true", help="print the before/after trigger table")
    parser.add_argument("--before", default=None, help="git revision for the 'before' side of --report (default: HEAD)")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.finops_report:
        print(json.dumps(trigger_budget_envelope(derive_policy(root)), indent=2))
    if args.emit_policy:
        print(json.dumps(derive_policy(root), indent=2))
    if args.report:
        print(render_report(report_rows(root, args.before or "HEAD"), report_rows(root, None)))
    inventory = json.loads((root / INVENTORY).read_text(encoding="utf-8"))
    synced = sync_inventory(inventory, root)
    if args.write:
        dump(root / INVENTORY, synced)
    if args.check and synced != inventory:
        print("inventory mechanical fields differ from the workflow YAML; run --write", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
