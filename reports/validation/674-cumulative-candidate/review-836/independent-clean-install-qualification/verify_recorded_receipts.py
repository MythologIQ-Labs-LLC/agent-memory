#!/usr/bin/env python3
"""Independently validate the recorded #837 clean-install consumer receipts.

Pure standard library. Checks semantic positive and *negative* outcomes rather
than trusting the original lifecycle runner's per-step "ok" flag, which only
records whether a step function raised. This verifier does not execute a wheel,
re-run a test, validate Git provenance, or grant v7 acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPORTS = {
    "report-wheel.json": "3.13.",
    "report-sdist.json": "3.13.",
    "report-py3.12.json": "3.12.",
    "report-py3.11.json": "3.11.",
}
STEPS = (
    "open_remember_recall_history_posture",
    "correct_parks_without_evidence_commits_with_qualified_evidence",
    "forget_reversible_tombstones_and_withholds",
    "permanent_forget_without_evidence_refused",
    "close_reopen_same_process",
    "process_restart_recall_and_deletion_persist",
    "recreate_deleted_id_old_content_does_not_reappear",
    "cross_tenant_open_same_state",
    "cross_project_same_tenant_isolation",
    "interrupted_recovery_and_integrity_negatives",
    "package_resources",
)


def require(condition: bool, path: Path, message: str) -> None:
    if not condition:
        raise AssertionError(f"{path.name}: {message}")


def check(path: Path, version_prefix: str) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    require(str(report.get("python", "")).startswith(version_prefix), path, "wrong Python version")
    require("/site-packages/agentmem_ref/" in str(report.get("agentmem_ref")), path, "not an installed package import")
    require(report.get("cwd") == "/tmp", path, "checkout execution environment")
    steps = report.get("steps")
    require(isinstance(steps, list) and [s.get("step") for s in steps] == list(STEPS), path,
            "missing/reordered/duplicate lifecycle stages")
    require(all(s.get("ok") is True for s in steps), path, "runner reported a failed stage")
    result = {s["step"]: s.get("result", {}) for s in steps}
    require(report.get("final_state_ok") is True, path, "final live memory not recovered")
    n = 0

    def must(ok: bool, label: str) -> None:
        nonlocal n
        require(bool(ok), path, label)
        n += 1

    initial = result[STEPS[0]]
    must(initial.get("contract_version") == "1.8.0", "installed contract mismatch")
    must(initial.get("admitted") == 1 and initial.get("returned") == 1
         and initial.get("history_version") == 1, "initial authorized recall absent")
    correction = result[STEPS[1]]
    must(correction.get("parked_outcome") == "require_review"
         and correction.get("corrected_outcome") == "allow_with_ledger"
         and correction.get("history_version") == 2, "governed correction")
    forget = result[STEPS[2]]
    must(forget.get("tombstoned") is True and forget.get("public_events") == 0
         and forget.get("deleted_ids_in_public_history") is False
         and forget.get("admitted_after_forget") == [], "deleted content leaked")
    permanent = result[STEPS[3]]
    must(permanent.get("outcome") == "require_external_verification"
         and permanent.get("m2_still_current") is True, "permanent delete without evidence was accepted")
    reopened = result[STEPS[4]]
    must(reopened.get("m2_admitted_after_reopen") is True
         and reopened.get("m1_tombstoned_after_reopen") is True
         and reopened.get("m1_admitted_after_reopen") == [], "reopen lifecycle")
    restarted = result[STEPS[5]]
    must(isinstance(restarted.get("m2"), list) and len(restarted["m2"]) == 1
         and restarted.get("m1") == [] and restarted.get("m1_tombstoned") is True,
         "separate-process restart")
    recreated = result[STEPS[6]]
    must(recreated.get("recreate_committed") is True
         and recreated.get("new_admitted") is True
         and recreated.get("old_generation_reappears") is False
         and recreated.get("history_version") == 1, "deleted generation reappeared")
    tenant = result[STEPS[7]]
    must(tenant.get("opened") is False and str(tenant.get("refused", "")).startswith("RuntimeRecoveryError"),
         "cross-tenant open unexpectedly succeeded")
    project = result[STEPS[8]]
    must(project.get("admitted") == [] and project.get("candidates") == []
         and project.get("correct_committed") is False
         and project.get("correct_refusal") == "fact_not_found"
         and project.get("history_visible_version") == 0
         and project.get("history_current") is None
         and isinstance(project.get("alpha_m2_still"), list)
         and len(project["alpha_m2_still"]) == 1
         and project.get("alpha_m2_version") == 1, "cross-project isolation")
    recovery = result[STEPS[9]]
    must(str(recovery.get("binding_only", "")).startswith("refused:")
         and recovery.get("binding_only_sqlite_created") is False, "incomplete first open allowed")
    must(isinstance(recovery.get("config_removed"), dict)
         and recovery["config_removed"].get("opened") is True, "packaged config recovery failed")
    must(str(recovery.get("truncated_db", "")).startswith("refused:"),
         "truncated database unexpectedly opened")
    must(int(recovery.get("row_tampered_rows", 0)) > 0
         and str(recovery.get("row_tampered", "")).startswith("refused:"),
         "tampered fact opened without rejection")
    packaged = result[STEPS[10]]
    must(packaged.get("source_schemas_dir_exists") is False
         and packaged.get("packaged_schemas") == 74
         and packaged.get("contract_version") == "1.8.0", "installed package resources")
    # The original runner's posture().get("configuration_binding_scheme")
    # returned None: it queried the wrong envelope level. Check the separate
    # installed CLI doctor log for sqlite_transaction, not this null field.
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.root
    observations = {}
    for filename, prefix in REPORTS.items():
        path = root / "lifecycle" / filename
        observations[filename] = check(path, prefix)
    cli = (root / "cli-smoke.txt").read_text(encoding="utf-8")
    require(cli.count('"configuration_binding_scheme": "sqlite_transaction"') >= 2,
            root / "cli-smoke.txt", "installed CLI doctor did not show SQLite binding on wheel and sdist")
    print(json.dumps({"status": "recorded_receipts_verified", "assertions_per_report": observations,
                      "report_count": len(observations), "execution_origin": "posthoc_read_only",
                      "acceptance_effect": "none"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
