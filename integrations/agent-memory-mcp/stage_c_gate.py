"""Development Stage C acceptance gate over a populated real-MCP quality probe.

This is an author-visible diagnostic, not calibrated abstention or a blind Gate 2
qualification. The same real-MCP probe queries an 18-record fictional store;
labels are joined only after retrieval. No new retrieval policy is introduced.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any


def assess(report: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on missing observation fields, retrieval regressions or false assurances."""
    rows = report.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Stage C requires a nonempty real-MCP probe report")
    checks: list[dict[str, Any]] = []
    seen = set()
    counts = {"answerable": 0, "no_answer": 0, "unanswerable_abstained": 0,
              "answerable_complete": 0}
    for row in rows:
        task_id = row.get("id")
        if not isinstance(task_id, str) or not task_id or task_id in seen:
            raise ValueError("Stage C requires unique, nonempty task IDs")
        seen.add(task_id)
        mcp = row.get("mcp") or {}
        total = mcp.get("required_total")
        if type(total) is not int or total < 0:
            raise ValueError("Stage C requires post-retrieval task labels")
        assessment = row.get("mcp_evidence_assessment")
        reason = row.get("mcp_evidence_assessment_reason")
        common = (
            row.get("mcp_profile") == "all_returned"
            and row.get("mcp_answer_generated") is False
            and row.get("mcp_answerability_verified") is False
            and row.get("mcp_selection_policy_version") is None
            and isinstance(row.get("mcp_keys"), list)
            and row.get("mcp_evidence_count") == len(row["mcp_keys"])
        )
        if total:
            counts["answerable"] += 1
            complete = mcp.get("required_complete") is True
            counts["answerable_complete"] += int(complete)
            passed = common and complete and assessment == "unverified" and reason == "answer_entailment_not_checked"
            goal = "complete required sources retained; still unverified"
        else:
            counts["no_answer"] += 1
            abstained = assessment == "insufficient_evidence" and (
                isinstance(reason, str) and bool(reason)
            )
            counts["unanswerable_abstained"] += int(abstained)
            passed = common and abstained
            goal = "populated-store no-answer flagged insufficient"
        checks.append({"task_id": task_id, "goal": goal, "passed": passed,
                       "assessment": assessment, "assessment_reason": reason,
                       "required_complete": mcp.get("required_complete"),
                       "returned_items": len(row.get("mcp_keys") or [])})
    if counts["answerable"] == 0 or counts["no_answer"] == 0:
        raise ValueError("Stage C requires both answerable and no-answer control tasks")
    return {"status": "PASS" if all(c["passed"] for c in checks) else "BLOCKED",
            "qualification": "author-visible populated-store diagnostic; not blind or calibrated",
            "counts": counts, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--from-report", type=Path,
                        help="evaluate a prior probe receipt; omit to execute fresh stdio MCP")
    options = parser.parse_args()
    if options.from_report:
        report = json.loads(options.from_report.read_text(encoding="utf-8"))
    else:
        # Lazy import: pure gate contract can be unit-tested without MCP SDK.
        from quality_probe import CASES, run
        cases = json.loads(CASES.read_text(encoding="utf-8"))
        report = asyncio.run(run(cases, k=5, selectivity=False))
    outcome = assess(report)
    output = {"schema": "agent-memory-stage-c-populated-store/0.1.0",
              "source_probe_schema": report.get("schema"), **outcome}
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": outcome["status"], "counts": outcome["counts"],
                      "failed": [c["task_id"] for c in outcome["checks"] if not c["passed"]]},
                     indent=2))
    return 0 if outcome["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
