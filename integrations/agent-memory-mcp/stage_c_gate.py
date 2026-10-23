"""Fail-closed Stage C development gate for real MCP populated-store task receipts.

This checks host-visible evidence-insufficiency metadata against the *complete*
fictional development manifest after retrieval. It is not a model correctness,
blinded holdout or production qualification gate. This module does not import MCP
at load time, so its admission rules can be independently unit-tested.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

PROBE_SCHEMA = "mcp-gate2-retrieval-probe/0.1.0"
GATE_SCHEMA = "agent-memory-stage-c-populated-store/0.2.0"


def assess(report: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Check every frozen task with no missing/extra rows, no optimistic defaults.

    The manifest is loaded only by the host after the MCP calls. These gold
    annotations must never become model tool arguments or evidence.
    """
    if not isinstance(report, dict) or report.get("schema") != PROBE_SCHEMA:
        raise ValueError("Stage C requires a current quality probe receipt")
    if report.get("selectivity") is not False or not str(report.get("provider", "")).startswith(
        "real stdio MCP / governed SQLite /"
    ):
        raise ValueError("Stage C requires the default real-stdio-MCP provider")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("records"), list):
        raise ValueError("Stage C requires a fixed populated-store manifest")
    records = manifest["records"]
    tasks = manifest.get("tasks")
    if not records or not isinstance(tasks, list) or not tasks:
        raise ValueError("Stage C requires records and a task cohort")
    task_map = {t["id"]: t for t in tasks if isinstance(t, dict) and isinstance(t.get("id"), str)}
    if len(task_map) != len(tasks):
        raise ValueError("Stage C manifest has malformed or duplicate task IDs")
    if report.get("dataset") != {"records": len(records), "tasks": len(tasks)}:
        raise ValueError("Stage C corpus size or task-count mismatch")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != len(tasks):
        raise ValueError("Stage C requires the full task cohort, not selected successes")
    row_ids = [r.get("id") for r in rows if isinstance(r, dict)]
    if len(row_ids) != len(rows) or len(set(row_ids)) != len(rows) or set(row_ids) != set(task_map):
        raise ValueError("Stage C task IDs missing, duplicated, or substituted")

    checks: list[dict[str, Any]] = []
    counts = {"answerable": 0, "no_answer": 0, "unanswerable_abstained": 0,
              "answerable_complete": 0}
    for row in rows:
        task_id = row["id"]
        task = task_map[task_id]
        required, forbidden = task.get("required"), task.get("forbidden")
        if not isinstance(required, list) or not isinstance(forbidden, list):
            raise ValueError("Stage C task annotations are malformed")
        if (row.get("question") != task.get("question") or row.get("gold") != required
                or row.get("forbidden") != forbidden):
            raise ValueError(f"Stage C manifest annotations drifted for {task_id}")
        mcp = row.get("mcp")
        if not isinstance(mcp, dict) or mcp.get("required_total") != len(required):
            raise ValueError(f"Stage C requires truthful post-retrieval labels: {task_id}")
        keys = row.get("mcp_keys")
        full_keys = row.get("mcp_full_text_keys")
        if (not isinstance(keys, list) or not isinstance(full_keys, list)
                or not all(isinstance(k, str) for k in keys + full_keys)
                or not set(full_keys).issubset(keys)):
            raise ValueError(f"Stage C requires attributed full-text evidence: {task_id}")
        assessment, reason = row.get("mcp_evidence_assessment"), row.get("mcp_evidence_assessment_reason")
        common = (
            row.get("mcp_profile") == "all_returned"
            and row.get("mcp_answer_generated") is False
            and row.get("mcp_answerability_verified") is False
            and row.get("mcp_selection_policy_version") is None
            and type(row.get("mcp_evidence_count")) is int
            and row["mcp_evidence_count"] == len(keys)
        )
        if required:
            counts["answerable"] += 1
            full = set(required).issubset(full_keys)
            complete = full and mcp.get("required_complete") is True
            counts["answerable_complete"] += int(complete)
            passed = (common and complete and assessment == "unverified"
                      and reason == "answer_entailment_not_checked")
            goal = "required full-text evidence preserved; answer not verified"
        else:
            counts["no_answer"] += 1
            if mcp.get("required_complete") is not None:
                raise ValueError(f"Stage C no-answer incorrectly scored as complete: {task_id}")
            abstained = assessment == "insufficient_evidence" and isinstance(reason, str) and bool(reason)
            counts["unanswerable_abstained"] += int(abstained)
            passed = common and abstained
            goal = "populated-store unanswerable question marked insufficient"
        checks.append({"task_id": task_id, "goal": goal, "passed": bool(passed),
                       "assessment": assessment, "assessment_reason": reason,
                       "required_complete": mcp.get("required_complete"),
                       "returned_items": len(keys)})
    if counts["answerable"] == 0 or counts["no_answer"] == 0:
        raise ValueError("Stage C requires both positive and negative controls")
    return {"status": "PASS" if all(c["passed"] for c in checks) else "BLOCKED",
            "qualification": "author-visible populated-store development diagnostic; not calibrated",
            "counts": counts, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--from-report", type=Path,
                        help="replay a prior real-MCP receipt; omit for a fresh stdio-MCP run")
    options = parser.parse_args()
    manifest_path = Path(__file__).with_name("quality_cases_dev.json")
    manifest_bytes = manifest_path.read_bytes()
    cases = json.loads(manifest_bytes)
    if options.from_report:
        report = json.loads(options.from_report.read_text(encoding="utf-8"))
    else:
        # Lazy import keeps offline admission tests independent of MCP SDK.
        from quality_probe import run
        report = asyncio.run(run(cases, k=5, selectivity=False))
    outcome = assess(report, cases)
    output = {"schema": GATE_SCHEMA, "source_probe_schema": report["schema"],
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(), **outcome}
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": outcome["status"], "counts": outcome["counts"],
                      "failed": [c["task_id"] for c in outcome["checks"] if not c["passed"]]},
                     indent=2))
    return 0 if outcome["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
